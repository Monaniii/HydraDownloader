"""Repository for queue item persistence.

Provides data-access methods for the SQLite ``queue`` table. Queue
items are serialised from and deserialised to dicts so the queue
manager can work with its own in-memory structures.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.storage.database import Database


class QueueRepository:
    """Data access for the download queue."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def insert(self, item: dict[str, Any]) -> dict[str, Any]:
        """Persist a new queue item."""
        record = dict(item)
        record.setdefault("id", uuid.uuid4().hex)
        record.setdefault("created_at", int(time.time()))
        record.setdefault("request_json", json.dumps(record.get("request", {})))

        await self._db.conn.execute(
            """
            INSERT INTO queue
                (id, url, title, media_type, status, priority, progress,
                 created_at, error, resolution, file_path, size_bytes,
                 speed, eta, thumbnail, uploader, retries, request_json)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record.get("url", ""),
                record.get("title", ""),
                record.get("media_type", "video"),
                record.get("status", "QUEUED"),
                int(record.get("priority", 0)),
                float(record.get("progress", 0)),
                record["created_at"],
                record.get("error", ""),
                record.get("resolution", ""),
                record.get("file_path", ""),
                int(record.get("size_bytes", 0)),
                record.get("speed", ""),
                record.get("eta", ""),
                record.get("thumbnail", ""),
                record.get("uploader", ""),
                int(record.get("retries", 0)),
                record["request_json"],
            ),
        )
        await self._db.conn.commit()
        return record

    async def update(self, item: dict[str, Any]) -> None:
        """Update a persisted queue item by id."""
        await self._db.conn.execute(
            """
            UPDATE queue SET
                title=?, status=?, priority=?, progress=?, error=?,
                resolution=?, file_path=?, size_bytes=?, speed=?, eta=?,
                thumbnail=?, uploader=?, retries=?
            WHERE id=?
            """,
            (
                item.get("title", ""),
                item.get("status", "QUEUED"),
                int(item.get("priority", 0)),
                float(item.get("progress", 0)),
                item.get("error", ""),
                item.get("resolution", ""),
                item.get("file_path", ""),
                int(item.get("size_bytes", 0)),
                item.get("speed", ""),
                item.get("eta", ""),
                item.get("thumbnail", ""),
                item.get("uploader", ""),
                int(item.get("retries", 0)),
                item["id"],
            ),
        )
        await self._db.conn.commit()

    async def delete(self, item_id: str) -> bool:
        """Remove a queue item by id. Returns True if removed."""
        cursor = await self._db.conn.execute(
            "DELETE FROM queue WHERE id = ?", (item_id,)
        )
        await self._db.conn.commit()
        return cursor.rowcount > 0

    async def clear(self) -> int:
        """Remove all items from the queue. Returns count removed."""
        cursor = await self._db.conn.execute("DELETE FROM queue")
        await self._db.conn.commit()
        return cursor.rowcount

    async def find_all(
        self, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Return all queue items, optionally filtered by status.

        Items are returned ordered by priority (ascending) then created_at.
        """
        query = "SELECT * FROM queue"
        params: list[Any] = []
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)
        query += " ORDER BY priority ASC, created_at ASC"
        cursor = await self._db.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def find_by_id(self, item_id: str) -> dict[str, Any] | None:
        """Return a single queue item, or None."""
        cursor = await self._db.conn.execute(
            "SELECT * FROM queue WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def count(self) -> int:
        """Return the total number of items in the queue."""
        cursor = await self._db.conn.execute("SELECT COUNT(*) AS c FROM queue")
        row = await cursor.fetchone()
        return int(row["c"]) if row else 0
