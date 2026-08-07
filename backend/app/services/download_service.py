"""Download service.

Executes downloads using the yt-dlp Python API. Builds the appropriate
yt-dlp options for video/audio/playlist downloads, wires progress
callbacks to the ProgressManager, sanitises filenames, and handles
FFmpeg-related configuration. No business logic lives in routes.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL

from app.core.errors import DownloadError, FFmpegNotFoundError
from app.core.logging import get_logger
from app.models.schemas import DownloadRequest, ProgressUpdate
from app.services.progress_manager import progress_manager
from app.services.settings_service import SettingsService

logger = get_logger(__name__)

# Characters forbidden in file names on major platforms.
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class DownloadService:
    """Prepares and runs yt-dlp downloads with progress reporting."""

    def __init__(self, settings_svc: SettingsService) -> None:
        self._settings = settings_svc

    async def prepare(self, request: DownloadRequest) -> dict[str, Any]:
        """Resolve settings and build the download options.

        Returns a dict with the resolved output dir and the yt-dlp
        options map. Raises FFmpegNotFoundError if conversion is
        required but FFmpeg is unavailable.
        """
        settings = await self._settings.get_all()

        output_dir = (
            request.output_dir
            or settings.download_dir
            or str(Path.home() / "Downloads" / "Hydra")
        )
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)

        template = request.filename_template or settings.filename_template

        opts: dict[str, Any] = {
            "outtmpl": str(outdir / template),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "continuedl": True,
            "noplaylist": request.media_type != "playlist",
        }

        if settings.proxy:
            opts["proxy"] = settings.proxy
        if settings.bandwidth_limit:
            opts["ratelimit"] = settings.bandwidth_limit
        if settings.ffmpeg_path:
            opts["ffmpeg_location"] = settings.ffmpeg_path

        needs_ffmpeg = request.media_type == "audio" or request.video_format.lower() not in (
            "",
            "best",
        )
        if needs_ffmpeg and not self._ffmpeg_available(settings.ffmpeg_path):
            raise FFmpegNotFoundError()

        return {"output_dir": str(outdir), "options": opts}

    def run(
        self,
        request: DownloadRequest,
        item_id: str,
        progress_cb: Callable[[ProgressUpdate], None],
    ) -> str:
        """Execute the download synchronously in a worker thread.

        Args:
            request: The download request.
            item_id: The queue item id used for progress tracking.
            progress_cb: Callback invoked on each progress update.

        Returns:
            The final output file path.

        Raises:
            DownloadError: If the download fails.
        """
        settings = self._settings_snapshot()
        output_dir = request.output_dir or settings.get("download_dir") or ""
        template = (
            request.filename_template
            or settings.get("filename_template")
            or "%(title)s.%(ext)s"
        )
        outdir = Path(output_dir) if output_dir else Path.home() / "Downloads" / "Hydra"
        outdir.mkdir(parents=True, exist_ok=True)

        opts: dict[str, Any] = {
            "outtmpl": str(outdir / template),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "continuedl": True,
            "noplaylist": request.media_type != "playlist",
            "progress_hooks": [lambda d: self._on_progress(d, item_id, progress_cb)],
        }

        if settings.get("proxy"):
            opts["proxy"] = settings["proxy"]
        if settings.get("bandwidth_limit"):
            opts["ratelimit"] = settings["bandwidth_limit"]

        opts["format"] = self._select_format(request, settings)

        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(str(request.url), download=True)
                filename = ydl.prepare_filename(info)
        except FFmpegNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Download failed for %s: %s", request.url, exc)
            raise DownloadError(str(exc)) from exc

        return filename

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _on_progress(self, d: dict, item_id: str, progress_cb: Callable) -> None:
        """Translate a yt-dlp progress dict into a ProgressUpdate."""
        status = d.get("status", "downloading")
        total = int(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
        downloaded = int(d.get("downloaded_bytes") or 0)
        percent = (downloaded / total * 100) if total else 0.0

        update = ProgressUpdate(
            id=item_id,
            status="completed" if status == "finished" else "downloading",
            progress=round(percent, 1),
            downloadedBytes=downloaded,
            totalBytes=total,
            speed=str(d.get("speed") or ""),
            eta=str(d.get("eta") or ""),
            title=str(d.get("info_dict", {}).get("title") or ""),
        )
        progress_cb(update)

    def _select_format(self, request: DownloadRequest, settings: dict) -> str:
        """Determine the yt-dlp format selector for the request."""
        if request.media_type == "audio":
            return "bestaudio[ext=m4a]/bestaudio"
        if request.format_id:
            return request.format_id
        vfmt = request.video_format or settings.get("default_video_quality") or "best"
        if vfmt.lower() == "mp4":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        return "bestvideo+bestaudio/best"

    def _ffmpeg_available(self, ffmpeg_path: str) -> bool:
        """Return True if FFmpeg is expected to be available."""
        if not ffmpeg_path:
            # Rely on system PATH; yt-dlp will find ffmpeg itself.
            return True
        return Path(ffmpeg_path).exists()

    def _settings_snapshot(self) -> dict[str, Any]:
        """Return a cached sync snapshot of settings for worker threads."""
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            try:
                settings = loop.run_until_complete(self._settings.get_all())
            finally:
                loop.close()
            return settings.model_dump()
        except Exception:  # noqa: BLE001
            return {}


# Module-level singleton wired with the settings service.
from app.services.settings_service import settings_service as _settings_svc

download_service = DownloadService(_settings_svc)
