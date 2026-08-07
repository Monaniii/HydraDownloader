"""Repository for download history records.

Provides data-access methods for the SQLite `downloads` table. No
business logic is implemented here; that belongs in the service layer.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from app.storage.database import Database


class HistoryRepository:
    """Data access for download history records."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def insert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert a new download record and return it with an id/created_at."""
        record = dict(record)
        record.setdefault("id", uuid.uuid4().hex)
        record.setdefault("created_at", int(time.time()))
        record.setdefault("status", "completed")

        await self._db.conn.execute(
            """
            INSERT INTO downloads
                (id, title, url, type, file_path, size_bytes, duration,
                 thumbnail, uploader, status, created_at, completed_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record.get("title", ""),
                record.get("url", ""),
                record.get("type", "video"),
                record.get("file_path", ""),
                int(record.get("size_bytes", 0)),
                int(record.get("duration", 0)),
                record.get("thumbnail", ""),
                record.get("uploader", ""),
                record.get("status", "completed"),
                record["created_at"],
                record.get("completed_at"),
            ),
        )
        await self._db.conn.commit()
        return record

    async def find_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        media_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return history records with optional filtering."""
        query = "SELECT * FROM downloads"
        conditions: list[str] = []
        params: list[Any] = []

        if search:
            conditions.append("(title LIKE ? OR url LIKE ? OR uploader LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        if media_type:
            conditions.append("type = ?")
            params.append(media_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await self._db.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def find_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Return a single record by id, or None."""
        cursor = await self._db.conn.execute(
            "SELECT * FROM downloads WHERE id = ?", (record_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete(self, record_id: str) -> bool:
        """Delete a record by id. Returns True if a row was removed."""
        cursor = await self._db.conn.execute(
            "DELETE FROM downloads WHERE id = ?", (record_id,)
        )
        await self._db.conn.commit()
        return cursor.rowcount > 0

    async def clear(self) -> int:
        """Delete all history records. Returns the number removed."""
        cursor = await self._db.conn.execute("DELETE FROM downloads")
        await self._db.conn.commit()
        return cursor.rowcount

    async def count(self) -> int:
        """Return the total number of history records."""
        cursor = await self._db.conn.execute("SELECT COUNT(*) AS c FROM downloads")
        row = await cursor.fetchone()
        return int(row["c"]) if row else 0
