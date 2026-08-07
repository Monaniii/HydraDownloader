"""Isolated download worker.

Each download runs in its own worker thread created by the
DownloadManager. The worker is responsible for:

* Executing yt-dlp with the appropriate options
* Driving the download state machine
* Reporting granular progress via a callback
* Retrying transient failures with exponential backoff
* Handling cancellation
* Cleaning up temporary/partial files

A worker never talks to HTTP routes directly; it is configured by the
DownloadManager which acts as the engine owner.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL

from app.core.config import settings
from app.core.errors import (
    DiskFullError,
    FileExistsError_,
    InterruptedDownloadError,
    MissingFFmpegError,
    PermissionDeniedError,
    RetryableDownloadError,
    UnsupportedFormatError,
)
from app.core.logging import get_download_logger, get_logger
from app.models.schemas import DownloadEvent, DownloadRequest, ProgressUpdate, QueueItem

logger = get_logger(__name__)
download_log = get_download_logger()

# Audio formats we can convert to via FFmpeg.
_SUPPORTED_AUDIO_FORMATS = {"mp3", "flac", "aac", "ogg", "wav", "m4a"}
# Video containers we can request (mp4/mkv/webm are native; mov/avi via recode).
_SUPPORTED_VIDEO_FORMATS = {"mp4", "mkv", "webm", "mov", "avi", "best"}


class DownloadWorker:
    """Runs a single download inside an isolated thread.

    The worker is created per download and is not reused. It exposes a
    ``cancel()`` method and emits lifecycle events through the manager's
    callback.
    """

    def __init__(
        self,
        item_id: str,
        request: DownloadRequest,
        emit: Callable[[DownloadEvent], None],
    ) -> None:
        """Initialise a worker for one download.

        Args:
            item_id: Unique queue item id for this download.
            request: The validated download request.
            emit: Callback the manager uses to broadcast events.
        """
        self.item_id = item_id
        self.request = request
        self._emit = emit
        self._cancel_event = threading.Event()

        # Populated as the download progresses / completes.
        self._title = ""
        self._uploader = ""
        self._thumbnail = ""
        self._resolution = ""
        self._duration = 0
        self._filename = ""
        self._size_bytes = 0
        self.retries = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def cancel(self) -> None:
        """Request cancellation of this download."""
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._cancel_event.is_set()

    # ------------------------------------------------------------------
    # Lifecycle / state machine
    # ------------------------------------------------------------------
    def run(self) -> str:
        """Execute the download and return the final file path.

        Raises:
            DownloadError subclasses describing the failure.
        """
        try:
            self._emit_state("INITIALIZING", "started")
        except InterruptedDownloadError:
            return ""

        # Validate format support up-front.
        self._validate_supported_format()

        attempt = 0
        while True:
            if self._cancel_event.is_set():
                return self._handle_cancel()

            try:
                attempt += 1
                if attempt == 1:
                    download_log.info("Download started: %s", self.request.url)
                else:
                    download_log.info(
                        "Download attempt #%d for %s", attempt, self.request.url
                    )
                return self._single_run()
            except InterruptedDownloadError:
                return self._handle_cancel()
            except RetryableDownloadError as exc:
                self.retries = attempt
                if attempt > settings.max_retries:
                    download_log.error("Download failed after %d retries", attempt)
                    raise
                self._emit_retry(attempt)
                delay = min(
                    settings.retry_base_delay * (2 ** (attempt - 1)),
                    settings.retry_max_delay,
                )
                download_log.info(
                    "Retrying %s in %.1fs (attempt %d): %s",
                    self.request.url,
                    delay,
                    attempt,
                    exc,
                )
                if self._cancel_event.wait(delay):
                    return self._handle_cancel()
            except Exception as exc:  # noqa: BLE001
                download_log.error("Download error for %s: %s", self.request.url, exc)
                raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _single_run(self) -> str:
        """Run yt-dlp once, raising typed errors on failure."""
        opts = self._build_options()
        self._emit_state("ANALYZING", "started")

        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(str(self.request.url), download=True)
                self._filename = self._resolve_filename(ydl, info)
        except InterruptedDownloadError:
            self._cleanup_partial()
            raise
        except Exception as exc:  # noqa: BLE001
            self._cleanup_partial()
            raise self._map_error(exc) from exc

        self._capture_metadata(info)
        self._size_bytes = self._file_size(self._filename)
        self._emit_state(
            "COMPLETED",
            "completed",
            complete=True,
            filename=self._filename,
            size_bytes=self._size_bytes,
        )
        download_log.info(
            "Download completed: %s -> %s", self.request.url, self._filename
        )
        return self._filename

    def _build_options(self) -> dict[str, Any]:
        """Build the yt-dlp options dict for this request."""
        req = self.request
        output_dir = req.effective_output_dir() or str(settings.default_download_dir)
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)

        template = req.filename_template or settings.default_filename_template
        opts: dict[str, Any] = {
            "outtmpl": str(outdir / template),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "continuedl": True,
            "noplaylist": not req.media_type == "playlist",
            "progress_hooks": [self._on_progress],
            "retries": 0,  # We manage retries ourselves with backoff.
            "fragment_retries": 3,
        }

        # Audio conversion
        if req.media_type == "audio":
            target = (req.audioFormat or "mp3").lower()
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": target,
                    "preferredquality": req.audioQuality or "0",
                }
            ]
        else:
            opts["format"] = self._select_format(req)

        if req.embedThumbnail:
            opts.setdefault("postprocessors", []).append({"key": "EmbedThumbnail"})
            opts["writethumbnail"] = True
        if req.embedMetadata:
            opts["addmetadata"] = True
        if req.subtitles:
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = False

        # Global settings (proxy / bandwidth / ffmpeg path)
        proxy = getattr(settings, "proxy", "")
        bw_limit = getattr(settings, "bandwidth_limit", "")
        ffmpeg_path = getattr(settings, "ffmpeg_path", "")
        if proxy:
            opts["proxy"] = proxy
        if bw_limit:
            opts["ratelimit"] = int(bw_limit) if str(bw_limit).isdigit() else bw_limit
        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path

        return opts

    def _select_format(self, req: DownloadRequest) -> str:
        """Determine the yt-dlp format selector."""
        if req.formatId:
            return req.formatId
        vfmt = (req.video_format or "mp4").lower()
        if vfmt == "best":
            return "bestvideo+bestaudio/best"
        if vfmt == "mp4":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if vfmt == "mkv":
            return "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=mkv]/best"
        if vfmt == "webm":
            return "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best"
        # mov/avi are handled via FFmpeg recoding in post-processing.
        return "bestvideo+bestaudio/best"

    def _validate_supported_format(self) -> None:
        """Raise UnsupportedFormatError for unsupported output formats."""
        if self.request.media_type == "audio":
            fmt = (self.request.audioFormat or "mp3").lower()
            if fmt not in _SUPPORTED_AUDIO_FORMATS:
                raise UnsupportedFormatError(f"Unsupported audio format: {fmt}")
        elif self.request.media_type == "video":
            fmt = (self.request.video_format or "mp4").lower()
            if fmt not in _SUPPORTED_VIDEO_FORMATS:
                raise UnsupportedFormatError(f"Unsupported video format: {fmt}")

    def _on_progress(self, d: dict) -> None:
        """yt-dlp progress hook; raises to abort when cancelled."""
        if self._cancel_event.is_set():
            raise InterruptedDownloadError("Cancelled by user")

        status = d.get("status", "downloading")
        total = int(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
        downloaded = int(d.get("downloaded_bytes") or 0)
        percent = (downloaded / total * 100) if total else 0.0
        speed = d.get("speed") or 0
        eta = d.get("eta") or 0

        info = d.get("info_dict") or {}
        self._title = info.get("title") or self._title
        self._uploader = info.get("uploader") or info.get("channel") or self._uploader
        self._thumbnail = info.get("thumbnail") or self._thumbnail
        self._resolution = str(info.get("resolution") or self._resolution)

        fragment = d.get("fragment_index") or 0
        elapsed = d.get("elapsed") or 0.0
        filename = d.get("filename") or self._filename

        state = (
            "POST_PROCESSING"
            if status in ("finished", "post-processing")
            else "DOWNLOADING"
        )
        update = ProgressUpdate(
            id=self.item_id,
            status=state,
            progress=round(percent, 1),
            downloadedBytes=downloaded,
            totalBytes=total,
            speed=self._format_speed(speed),
            eta=self._format_eta(eta),
            title=self._title,
            resolution=self._resolution,
            fragment=fragment,
            elapsed=float(elapsed),
            filename=filename,
            retries=self.retries,
        )
        self._emit(
            DownloadEvent(
                type="progress", item=self._item_snapshot(update), progress=update
            )
        )

    def _emit_state(
        self,
        state: str,
        event_type: str,
        *,
        complete: bool = False,
        filename: str = "",
        size_bytes: int = 0,
    ) -> None:
        """Emit a state transition event on the manager."""
        update = ProgressUpdate(
            id=self.item_id,
            status=state,
            progress=100.0 if complete else self._progress_for(state),
            title=self._title,
            resolution=self._resolution,
            filename=filename,
            retries=self.retries,
        )
        if complete:
            update.totalBytes = size_bytes
            update.downloadedBytes = size_bytes
        self._emit(
            DownloadEvent(
                type=event_type, item=self._item_snapshot(update), progress=update
            )
        )

    def _emit_retry(self, attempt: int) -> None:
        """Emit a retrying event."""
        update = ProgressUpdate(
            id=self.item_id,
            status="RETRYING",
            progress=0,
            title=self._title,
            retries=attempt,
        )
        self._emit(
            DownloadEvent(
                type="retrying", item=self._item_snapshot(update), progress=update
            )
        )

    def _item_snapshot(self, update: ProgressUpdate) -> QueueItem:
        """Build a QueueItem snapshot from the current worker state."""
        return QueueItem(
            id=self.item_id,
            url=str(self.request.url),
            title=update.title or self._title,
            media_type=self.request.media_type,
            status=update.status,
            priority=self.request.priority,
            progress=update.progress,
            createdAt=int(time.time()),
            error=update.error,
            resolution=update.resolution or self._resolution,
            filePath=self._filename,
            sizeBytes=self._size_bytes or update.totalBytes,
            speed=update.speed,
            eta=update.eta,
            thumbnail=self._thumbnail,
            uploader=self._uploader,
            retries=self.retries,
        )

    # ------------------------------------------------------------------
    # Error handling and helpers
    # ------------------------------------------------------------------
    def _map_error(self, exc: Exception) -> Exception:
        """Map a yt-dlp error to a typed error."""
        message = str(exc).lower()
        if isinstance(exc, InterruptedDownloadError):
            return exc
        if "disk" in message or "space" in message.lower():
            return DiskFullError()
        if "permission" in message or "not permitted":
            return PermissionDeniedError()
        if "ffmpeg" in message or "unable to find ffmpeg":
            return MissingFFmpegError()
        if "already exists" in message or "file exists":
            return FileExistsError_()
        # Common transient errors worth retrying.
        if any(
            token in message
            for token in (
                "connection",
                "timeout",
                "temporarily",
                "404",
                "429",
                "network",
                "http error",
            )
        ):
            return RetryableDownloadError(self._clean_message(exc))
        return RetryableDownloadError(self._clean_message(exc))

    def _handle_cancel(self) -> str:
        """Perform cancellation cleanup and return an empty path."""
        self._cleanup_partial()
        download_log.info("Download cancelled: %s", self.request.url)
        update = ProgressUpdate(
            id=self.item_id,
            status="CANCELLED",
            progress=0,
            title=self._title,
        )
        self._emit(
            DownloadEvent(
                type="cancelled", item=self._item_snapshot(update), progress=update
            )
        )
        return ""

    def _cleanup_partial(self) -> None:
        """Remove partial temporary files left by an interrupted download."""
        for suffix in (".part", ".ytdl", ".temp"):
            try:
                path = f"{self._filename}{suffix}"
                if path and Path(path).exists():
                    os.remove(path)
            except OSError:
                pass

    def _resolve_filename(self, ydl: YoutubeDL, info: dict) -> str:
        """Resolve the final output file path from yt-dlp."""
        try:
            return ydl.prepare_filename(info)
        except Exception:  # noqa: BLE001
            return self._filename or ""

    def _capture_metadata(self, info: dict) -> None:
        """Populate worker metadata from yt-dlp info."""
        if not info:
            return
        self._title = info.get("title") or self._title
        self._uploader = info.get("uploader") or info.get("channel") or self._uploader
        self._thumbnail = info.get("thumbnail") or self._thumbnail
        self._duration = int(info.get("duration") or 0)
        self._resolution = str(
            info.get("resolution") or info.get("height") or self._resolution
        )

    @staticmethod
    def _file_size(path: str) -> int:
        """Return the size in bytes of the output file."""
        try:
            return Path(path).stat().st_size
        except OSError:
            return 0

    @staticmethod
    def _progress_for(state: str) -> float:
        """Return a representative progress value for a state."""
        if state in ("QUEUED", "INITIALIZING"):
            return 0.0
        if state == "ANALYZING":
            return 5.0
        if state == "DOWNLOADING":
            return 50.0
        if state == "POST_PROCESSING":
            return 90.0
        return 0.0

    @staticmethod
    def _format_speed(speed: Any) -> str:
        """Format a byte-rate into a human-readable string."""
        try:
            value = float(speed or 0)
        except (TypeError, ValueError):
            return ""
        return DownloadWorker._human_bytes(value) + "/s"

    @staticmethod
    def _format_eta(eta: Any) -> str:
        """Format an ETA (seconds) as a human string."""
        try:
            seconds = int(eta or 0)
        except (TypeError, ValueError):
            return ""
        if seconds <= 0:
            return ""
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _human_bytes(value: float) -> str:
        """Format a byte count into a compact human-readable size."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(value) < 1024.0:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024.0
        return f"{value:.1f} PB"

    @staticmethod
    def _clean_message(exc: Exception) -> str:
        """Return a short, safe error message."""
        message = str(exc).strip()
        if len(message) > 300:
            message = message[:300] + "…"
        return message
