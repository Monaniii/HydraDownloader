"""History service.

Coordinates history repository access for completed downloads. Provides
listing with search/filtering, single delete, and full clear. No
business logic lives in routes.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.models.schemas import HistoryListResponse, HistoryRecord
from app.storage.history_repository import HistoryRepository

logger = get_logger(__name__)


class HistoryService:
    """Service for reading and managing download history."""

    def __init__(self, repo: HistoryRepository) -> None:
        self._repo = repo

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        media_type: str | None = None,
    ) -> HistoryListResponse:
        """Return a filtered, paginated list of history records."""
        rows = await self._repo.find_all(
            limit=limit,
            offset=offset,
            search=search,
            media_type=media_type,
        )
        total = await self._repo.count()
        items = [self._to_record(row) for row in rows]
        return HistoryListResponse(items=items, total=total)

    async def add(
        self,
        *,
        title: str,
        url: str,
        media_type: str = "video",
        file_path: str = "",
        size_bytes: int = 0,
        duration: int = 0,
        thumbnail: str = "",
        uploader: str = "",
        status: str = "completed",
    ) -> HistoryRecord:
        """Record a download in history.

        Defaults to a completed record; failed downloads can pass
        ``status="failed"``.
        """
        row = await self._repo.insert(
            {
                "title": title,
                "url": url,
                "type": media_type,
                "file_path": file_path,
                "size_bytes": size_bytes,
                "duration": duration,
                "thumbnail": thumbnail,
                "uploader": uploader,
                "status": status,
            }
        )
        logger.info("History record added: %s", row["id"])
        return self._to_record(row)

    async def delete(self, record_id: str) -> bool:
        """Delete a single history record. Returns True if removed."""
        return await self._repo.delete(record_id)

    async def clear(self) -> int:
        """Clear all history. Returns the number of records removed."""
        return await self._repo.clear()

    @staticmethod
    def _to_record(row: dict[str, Any]) -> HistoryRecord:
        """Convert a repository row into a HistoryRecord."""
        return HistoryRecord(
            id=row.get("id", ""),
            title=row.get("title", ""),
            url=row.get("url", ""),
            type=row.get("type", "video"),
            filePath=row.get("file_path", ""),
            sizeBytes=int(row.get("size_bytes", 0)),
            duration=int(row.get("duration", 0)),
            thumbnail=row.get("thumbnail", ""),
            uploader=row.get("uploader", ""),
            status=row.get("status", "completed"),
            createdAt=int(row.get("created_at", 0)),
            completedAt=row.get("completed_at"),
        )


# Module-level singleton wired with the database-backed repository.
from app.storage.database import database

history_service = HistoryService(HistoryRepository(database))

