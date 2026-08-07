"""Analyzer service.

Responsible for extracting metadata from a supported media URL using the
yt-dlp Python API. All business logic for analysis lives here; routes
only delegate to this service.
"""
from __future__ import annotations

import re
import time
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    UnsupportedError,
)

from app.core.config import settings
from app.core.errors import (
    AgeRestrictedError,
    InvalidURLError,
    NetworkError,
    TimeoutError,
    UnavailableVideoError,
    UnsupportedSiteError,
)
from app.core.logging import get_logger
from app.models.schemas import (
    Chapter,
    Subtitle,
    VideoFormat,
    VideoInfo,
)

logger = get_logger(__name__)

# Simple heuristic to reject obviously malformed URLs before handing off
# to yt-dlp. Not a full validation — yt-dlp performs the authoritative
# site check.
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class AnalyzerService:
    """Service that extracts and structures media metadata via yt-dlp."""

    def analyze(self, url: str) -> VideoInfo:
        """Analyze a URL and return structured metadata.

        Args:
            url: The video or playlist URL to analyze.

        Raises:
            InvalidURLError: If the URL is malformed.
            UnsupportedSiteError: If yt-dlp cannot handle the site.
            UnavailableVideoError: If the media is unavailable/private.
            AgeRestrictedError: If the media is age-restricted.
            NetworkError: If a network failure occurs.
            TimeoutError: If extraction exceeds the timeout.
        """
        self._validate_url(url)
        start = time.perf_counter()
        logger.info("Analyzing URL: %s", url)

        try:
            info = self._extract(url)
        except DownloadError as exc:
            raise self._map_download_error(exc) from exc
        except Exception as exc:  # noqa: BLE001
            # Broad catch to ensure the API never crashes. Translate known
            # conditions; anything else becomes a NetworkError.
            raise NetworkError(self._clean_message(exc)) from exc
        finally:
            elapsed = time.perf_counter() - start
            logger.info("Analysis took %.2fs for %s", elapsed, url)

        logger.info("Successfully analyzed %s", url)
        return self._to_video_info(info)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _validate_url(self, url: str) -> None:
        """Basic local validation of the URL string."""
        if not url or not isinstance(url, str):
            raise InvalidURLError("A URL is required.")
        if not _URL_RE.match(url.strip()):
            raise InvalidURLError("The provided URL is invalid.")

    def _extract(self, url: str) -> dict[str, Any]:
        """Run yt-dlp extraction without downloading."""
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": False,
            "extract_flat": False,
            "socket_timeout": settings.analyze_timeout,
            "nocheckcertificate": False,
        }
        with YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=False)

    def _map_download_error(self, exc: DownloadError) -> Exception:
        """Translate a yt-dlp DownloadError into a typed AppError."""
        message = str(exc)

        if isinstance(exc.cause, UnsupportedError):
            return UnsupportedSiteError("This website is not supported.")
        if "age" in message.lower() and (
            "restrict" in message.lower() or "sign in" in message.lower()
        ):
            return AgeRestrictedError("This video is age-restricted.")
        if any(
            token in message.lower()
            for token in (
                "private video",
                "video unavailable",
                "unavailable",
                "video is private",
                "has been removed",
                "doesn't exist",
            )
        ):
            return UnavailableVideoError("The requested video is unavailable or private.")
        if "timed out" in message.lower() or "timeout" in message.lower():
            return TimeoutError("The request timed out.")
        if any(
            token in message.lower()
            for token in ("unable to download", "network", "connection", "ssl", "dns")
        ):
            return NetworkError("A network error occurred while contacting the host.")
        if "unsupported url" in message.lower():
            return UnsupportedSiteError("This website is not supported.")

        return UnavailableVideoError(self._clean_message(message))

    def _to_video_info(self, info: dict[str, Any]) -> VideoInfo:
        """Convert the raw yt-dlp dict into a structured VideoInfo."""
        is_playlist = bool(info.get("_type") == "playlist" or info.get("entries"))

        # If it's a playlist, use the first entry for display metadata.
        base = info
        if is_playlist and info.get("entries"):
            first = info["entries"][0]
            if isinstance(first, dict):
                base = first

        formats = self._extract_formats(info.get("formats"))

        return VideoInfo(
            id=str(base.get("id") or ""),
            title=str(base.get("title") or ""),
            description=str(base.get("description") or ""),
            duration=int(base.get("duration") or 0),
            durationText=str(
                base.get("duration_string")
                or self._format_duration(base.get("duration"))
                or ""
            ),
            thumbnail=str(base.get("thumbnail") or ""),
            uploader=str(base.get("uploader") or base.get("channel") or ""),
            uploaderUrl=str(base.get("uploader_url") or base.get("channel_url") or ""),
            uploadDate=str(base.get("upload_date") or base.get("release_date") or ""),
            viewCount=int(base.get("view_count") or 0),
            likeCount=int(base.get("like_count") or 0),
            webpageUrl=str(base.get("webpage_url") or info.get("webpage_url") or ""),
            channel=str(base.get("channel") or ""),
            channelId=str(base.get("channel_id") or ""),
            isPlaylist=is_playlist,
            playlistCount=int(info.get("playlist_count") or 0),
            subtitles=self._extract_subtitles(base.get("subtitles")),
            automaticCaptions=self._extract_subtitles(base.get("automatic_captions")),
            formats=formats["all"],
            audioFormats=formats["audio"],
            videoFormats=formats["video"],
            chapters=self._extract_chapters(base.get("chapters")),
        )

    def _extract_formats(self, raw_formats: Any) -> dict[str, list[VideoFormat]]:
        """Categorise raw yt-dlp formats into video/audio/combined."""
        all_formats: list[VideoFormat] = []
        seen: set[str] = set()

        for raw in raw_formats or []:
            if not isinstance(raw, dict):
                continue

            fmt = self._to_format(raw)
            # Deduplicate by format id.
            if fmt.formatId in seen:
                continue
            seen.add(fmt.formatId)

            has_video = self._has_codec(raw.get("vcodec"))
            has_audio = self._has_codec(raw.get("acodec"))

            if has_video or has_audio:
                all_formats.append(fmt)

        # Sort by resolution (height) then fps, descending.
        all_formats.sort(key=lambda f: (self._height(f.resolution), f.fps), reverse=True)

        video = [
            f
            for f in all_formats
            if not self._has_codec(f.audioCodec) and self._has_codec(f.videoCodec)
        ]
        audio = [
            f
            for f in all_formats
            if not self._has_codec(f.videoCodec) and self._has_codec(f.audioCodec)
        ]

        return {
            "all": all_formats,
            "video": video,
            "audio": audio,
        }

    def _to_format(self, raw: dict[str, Any]) -> VideoFormat:
        """Convert a raw format dict into a VideoFormat model."""
        resolution = str(raw.get("resolution") or "")
        if not resolution or resolution in ("audio only", "images"):
            height = raw.get("height")
            resolution = f"{height}p" if height else "audio"

        return VideoFormat(
            formatId=str(raw.get("format_id") or ""),
            extension=str(raw.get("ext") or raw.get("extension") or ""),
            resolution=resolution,
            fps=int(raw.get("fps") or 0),
            filesize=int(raw.get("filesize") or raw.get("filesize_approx") or 0),
            videoCodec=str(raw.get("vcodec") or ""),
            audioCodec=str(raw.get("acodec") or ""),
            note=str(raw.get("format_note") or ""),
        )

    def _extract_subtitles(self, raw: Any) -> list[Subtitle]:
        """Extract subtitle tracks from yt-dlp's subtitle dict."""
        result: list[Subtitle] = []
        if not isinstance(raw, dict):
            return result

        for lang, tracks in raw.items():
            if not isinstance(tracks, list) or not tracks:
                continue
            first = tracks[0] if isinstance(tracks[0], dict) else {}
            result.append(
                Subtitle(
                    lang=lang,
                    name=str(first.get("name") or lang),
                    url=str(first.get("url") or "") or None,
                )
            )
        return result

    def _extract_chapters(self, raw: Any) -> list[Chapter]:
        """Extract chapters from yt-dlp."""
        result: list[Chapter] = []
        if not isinstance(raw, list):
            return result

        for idx, chapter in enumerate(raw):
            if not isinstance(chapter, dict):
                continue
            result.append(
                Chapter(
                    startTime=int(chapter.get("start_time") or 0),
                    endTime=int(
                        chapter.get("end_time")
                        or (
                            raw[idx + 1].get("start_time")
                            if idx + 1 < len(raw) and isinstance(raw[idx + 1], dict)
                            else 0
                        )
                    ),
                    title=str(chapter.get("title") or ""),
                )
            )
        return result

    def _format_duration(self, seconds: Any) -> str:
        """Format a duration in seconds as HH:MM:SS."""
        try:
            total = int(seconds or 0)
        except (TypeError, ValueError):
            return ""
        if total <= 0:
            return ""
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _has_codec(codec: Any) -> bool:
        """Return True if a codec value indicates an actual stream."""
        return bool(codec) and str(codec).lower() != "none"

    @staticmethod
    def _height(resolution: str) -> int:
        """Extract the numeric height from a resolution string."""
        match = re.search(r"(\d+)", resolution)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _clean_message(exc) -> str:
        """Return a short, safe error message."""
        message = str(exc).strip()
        # Truncate very long messages for cleanliness.
        if len(message) > 300:
            message = message[:300] + "…"
        return message


# Module-level singleton for dependency injection.
analyzer_service = AnalyzerService()
