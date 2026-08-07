"""SQLite database management for Hydra Downloader.

Provides a single connection to the SQLite database file and initialises
the schema. Uses aiosqlite for async access. All repositories share this
connection.
"""
from __future__ import annotations

import aiosqlite

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'video',
    file_path TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    duration INTEGER NOT NULL DEFAULT 0,
    thumbnail TEXT NOT NULL DEFAULT '',
    uploader TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'completed',
    created_at INTEGER NOT NULL,
    completed_at INTEGER
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS queue (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL DEFAULT 'video',
    status TEXT NOT NULL DEFAULT 'QUEUED',
    priority INTEGER NOT NULL DEFAULT 0,
    progress REAL NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    resolution TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    speed TEXT NOT NULL DEFAULT '',
    eta TEXT NOT NULL DEFAULT '',
    thumbnail TEXT NOT NULL DEFAULT '',
    uploader TEXT NOT NULL DEFAULT '',
    retries INTEGER NOT NULL DEFAULT 0,
    request_json TEXT NOT NULL DEFAULT '{}'
);
"""


class Database:
    """Wraps the async SQLite connection."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(settings.data_dir / "hydra.db")
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database connection and initialise the schema."""
        if self._conn is not None:
            return
        logger.info("Connecting to database at %s", self.db_path)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        """Return the underlying connection, raising if not connected."""
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")


# Module-level singleton.
database = Database()
