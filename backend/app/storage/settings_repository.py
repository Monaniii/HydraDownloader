"""Repository for application settings persistence.

Underscoring the separation of concerns: this module only reads and
writes key/value rows in the `settings` table. Business logic and
defaults live in the settings service.
"""
from __future__ import annotations

from typing import Any

from app.storage.database import Database


class SettingsRepository:
    """Data access for the `settings` key/value table."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_all(self) -> dict[str, str]:
        """Return all settings as a dictionary of key -> value."""
        cursor = await self._db.conn.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    async def get(self, key: str) -> str | None:
        """Return a single setting value, or None if absent."""
        cursor = await self._db.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, key: str, value: Any) -> None:
        """Upsert a single setting value."""
        await self._db.conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )
        await self._db.conn.commit()

    async def update_many(self, values: dict[str, Any]) -> None:
        """Upsert multiple settings in a single transaction."""
        for key, value in values.items():
            await self._db.conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )
        await self._db.conn.commit()
