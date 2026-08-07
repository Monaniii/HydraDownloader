"""Search service.

Provides search across supported platforms using yt-dlp's built-in
search capabilities. Returns structured search results (title, duration,
thumbnail, uploader, views). No business logic lives in routes.
"""
from __future__ import annotations

from typing import Any

from yt_dlp import YoutubeDL

from app.core.errors import DownloadError
from app.core.logging import get_logger
from app.models.schemas import SearchResult

logger = get_logger(__name__)


class SearchService:
    """Search media on supported platforms via yt-dlp."""

    def __init__(self) -> None:
        self._opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": True,
        }

    async def search(self, query: str, platform: str = "ytsearch") -> list[SearchResult]:
        """Return up to a handful of search results for a query.

        Args:
            query: The search term(s).
            platform: The yt-dlp search prefix (e.g. ytsearch, ytsearch5).

        Returns:
            A list of SearchResult objects.
        """
        search_url = f"{platform}:{query}"
        try:
            with YoutubeDL(self._opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
        except Exception as exc:  # noqa: BLE001
            logger.error("Search failed for %r: %s", query, exc)
            raise DownloadError(f"Search failed: {exc}") from exc

        entries = info.get("entries") or []
        results: list[SearchResult] = []
        for entry in entries:
            if not entry:
                continue
            results.append(
                SearchResult(
                    id=str(entry.get("id", "")),
                    title=str(entry.get("title", "")),
                    url=str(entry.get("webpage_url") or entry.get("url") or ""),
                    duration=int(entry.get("duration", 0) or 0),
                    thumbnail=str(entry.get("thumbnail", "")),
                    uploader=str(entry.get("uploader", "")),
                    views=int(entry.get("view_count", 0) or 0),
                )
            )
        return results


# Module-level singleton.
search_service = SearchService()
