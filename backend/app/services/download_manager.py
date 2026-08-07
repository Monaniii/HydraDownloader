"""Download engine / manager.

The DownloadManager is the single owner of download execution. It:

* Maintains the in-memory queue dictionary
* Instantiates and tracks a DownloadWorker per download
* Enforces the maximum concurrent-download limit
* Bridges worker events to the ProgressManager and HistoryManager
* Persists queue state to SQLite via the QueueRepository

All HTTP routes delegate to this manager; no route ever talks to
yt-dlp directly.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_download_logger, get_logger
from app.models.schemas import (
    DownloadEvent,
    DownloadRequest,
    ProgressUpdate,
    QueueItem,
)
from app.services.download_worker import DownloadWorker
from app.services.history_service import history_service
from app.services.progress_manager import progress_manager
from app.storage.database import database
from app.storage.queue_repository import QueueRepository

logger = get_logger(__name__)
download_log = get_download_logger()

# Terminal states after which a worker is not restartable.
_TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}
# States that can be paused / cancelled.
_CONTROLLABLE = {
    "QUEUED",
    "INITIALIZING",
    "ANALYZING",
    "DOWNLOADING",
    "POST_PROCESSING",
}


@dataclass
class _Entry:
    """Internal state backing one queue item."""

    id: str
    request: DownloadRequest
    status: str = "QUEUED"
    title: str = ""
    uploader: str = ""
    thumbnail: str = ""
    resolution: str = ""
    file_path: str = ""
    size_bytes: int = 0
    speed: str = ""
    eta: str = ""
    progress: float = 0.0
    error: str = ""
    retries: int = 0
    created: int = 0
    worker: DownloadWorker | None = field(default=None, repr=False)
    cancel_event: threading.Event = field(default_factory=threading.Event)


class DownloadManager:
    """Central orchestration engine for all downloads."""

    def __init__(self, max_concurrent: int | None = None) -> None:
        self._max_concurrent = max_concurrent or settings.default_parallel_downloads
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._running = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._persistence = QueueRepository(database)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the main event loop for thread-safe coroutine scheduling."""
        self._loop = loop

    async def load_persisted(self) -> None:
        """Restore the queue from SQLite and requeue unfinished work."""
        rows = await self._persistence.find_all()
        for row in rows:
            entry = self._entry_from_row(row)
            if entry is None:
                continue
            with self._lock:
                self._entries[entry.id] = entry
            if entry.status not in _TERMINAL_STATES:
                entry.status = "QUEUED" if settings.auto_resume else entry.status
            download_log.info("Restored queue item %s (%s)", entry.id, entry.status)
        self._schedule()

    # ------------------------------------------------------------------
    # Queue control (called from routes)
    # ------------------------------------------------------------------
    def enqueue(self, request: DownloadRequest) -> QueueItem:
        """Add a download to the queue and start it when capacity allows."""
        entry = _Entry(
            id=uuid.uuid4().hex,
            request=request,
            created=int(time.time()),
        )
        with self._lock:
            self._entries[entry.id] = entry
        self._persist_entry(entry, insert=True)
        download_log.info("Enqueued %s (%s)", entry.id, request.url)
        self._forward(DownloadEvent(type="queued", item=self._to_item(entry)))
        self._schedule()
        return self._to_item(entry)

    def remove(self, item_id: str) -> bool:
        """Remove an item from the queue (cancelling if active)."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry:
                return False
            if entry.worker:
                entry.worker.cancel()
            self._entries.pop(item_id, None)
        self._delete_persisted(item_id)
        download_log.info("Removed queue item %s", item_id)
        return True

    def pause(self, item_id: str) -> bool:
        """Pause an active/queued download."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry or entry.status not in _CONTROLLABLE:
                return False
            entry.cancel_event.set()
            if entry.worker:
                entry.worker.cancel()
            entry.status = "PAUSED"
            self._persist_entry(entry)
            self._forward(DownloadEvent(type="paused", item=self._to_item(entry)))
            download_log.info("Paused queue item %s", item_id)
            return True

    def resume(self, item_id: str) -> bool:
        """Resume a paused download by requeueing it."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry or entry.status != "PAUSED":
                return False
            entry.status = "QUEUED"
            entry.cancel_event = threading.Event()
            entry.worker = None
            self._persist_entry(entry)
            self._forward(DownloadEvent(type="resumed", item=self._to_item(entry)))
            download_log.info("Resumed queue item %s", item_id)
        self._schedule()
        return True

    def cancel(self, item_id: str) -> bool:
        """Cancel an active or queued download."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry or entry.status in _TERMINAL_STATES:
                return False
            entry.cancel_event.set()
            if entry.worker:
                entry.worker.cancel()
            entry.worker = None
            entry.status = "CANCELLED"
            self._persist_entry(entry)
            self._forward(DownloadEvent(type="cancelled", item=self._to_item(entry)))
            download_log.info("Cancelled queue item %s", item_id)
            return True

    def retry(self, item_id: str) -> bool:
        """Retry a failed or cancelled download."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry or entry.status not in ("FAILED", "CANCELLED"):
                return False
            entry.status = "QUEUED"
            entry.cancel_event = threading.Event()
            entry.worker = None
            entry.error = ""
            self._persist_entry(entry)
            self._forward(DownloadEvent(type="retrying", item=self._to_item(entry)))
            download_log.info("Retrying queue item %s", item_id)
        self._schedule()
        return True

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get_queue(self) -> list[QueueItem]:
        """Return the current queue as a list of QueueItems."""
        with self._lock:
            items = [self._to_item(e) for e in self._entries.values()]
        items.sort(key=lambda i: (i.priority, i.createdAt))
        return items

    def get_item(self, item_id: str) -> QueueItem | None:
        """Return a single queue item, or None."""
        with self._lock:
            entry = self._entries.get(item_id)
            return self._to_item(entry) if entry else None

    def set_concurrency(self, value: int) -> None:
        """Update the maximum concurrent download count."""
        self._max_concurrent = max(1, int(value))
        self._schedule()

    # ------------------------------------------------------------------
    # Scheduling / worker orchestration
    # ------------------------------------------------------------------
    def _schedule(self) -> None:
        """Launch workers for queued entries up to the concurrency limit."""
        with self._lock:
            candidates = [
                e
                for e in self._entries.values()
                if e.status == "QUEUED" and not e.cancel_event.is_set()
            ]
        candidates.sort(key=lambda e: (e.request.priority, e.created))

        while self._running < self._max_concurrent and candidates:
            with self._lock:
                entry = candidates.pop(0)
                if entry.status != "QUEUED":
                    continue
                entry.status = "DOWNLOADING"
                self._running += 1
            self._persist_entry(entry)
            self._forward(DownloadEvent(type="started", item=self._to_item(entry)))
            self._spawn_worker(entry)

    def _spawn_worker(self, entry: _Entry) -> None:
        """Create and start a worker thread for an entry."""
        worker = DownloadWorker(entry.id, entry.request, self._on_event)
        entry.worker = worker
        threading.Thread(target=self._worker_main, args=(entry.id,), daemon=True).start()

    def _worker_main(self, item_id: str) -> None:
        """Run a worker to completion in a background thread."""
        entry = self._entries.get(item_id)
        if entry is None or entry.worker is None:
            with self._lock:
                self._running = max(0, self._running - 1)
            self._schedule()
            return

        worker = entry.worker
        try:
            filename = worker.run()
            if worker.cancelled:
                self._mark_entry(item_id, "CANCELLED", "", 0)
            elif filename:
                self._record_completion(entry, filename)
            else:
                self._mark_entry(item_id, "FAILED", entry.error or "Download failed", 0)
        except Exception as exc:  # noqa: BLE001
            logger.error("Worker failed for %s: %s", item_id, exc)
            self._mark_entry(item_id, "FAILED", str(exc), worker.retries)
            self._record_failure(entry, str(exc))
        finally:
            with self._lock:
                self._running = max(0, self._running - 1)
            self._schedule()

    # ------------------------------------------------------------------
    # Event bridge
    # ------------------------------------------------------------------
    def _on_event(self, event: DownloadEvent) -> None:
        """Receive an event from a worker and dispatch it."""
        progress_manager.emit(event)
        if event.progress:
            self._sync_entry(event)

    def _sync_entry(self, event: DownloadEvent) -> None:
        """Update the internal entry based on a progress event."""
        with self._lock:
            entry = self._entries.get(event.item.id)
            if not entry:
                return
            entry.title = event.item.title or entry.title
            entry.uploader = event.item.uploader or entry.uploader
            entry.thumbnail = event.item.thumbnail or entry.thumbnail
            entry.resolution = event.item.resolution or entry.resolution
            entry.progress = event.item.progress
            entry.speed = event.item.speed
            entry.eta = event.item.eta
            entry.retries = event.item.retries
            if entry.progress % 5 < 1:
                self._persist_entry(entry)

    # ------------------------------------------------------------------
    # Completion / history
    # ------------------------------------------------------------------
    def _record_completion(self, entry: _Entry, filename: str) -> None:
        """Mark an entry complete and write a history record."""
        entry.file_path = filename
        entry.size_bytes = self._file_size(filename)
        entry.status = "COMPLETED"
        entry.progress = 100.0
        self._persist_entry(entry)
        self._forward(
            DownloadEvent(
                type="completed",
                item=self._to_item(entry),
                progress=ProgressUpdate(
                    id=entry.id,
                    status="COMPLETED",
                    progress=100.0,
                    title=entry.title,
                    filename=filename,
                    totalBytes=entry.size_bytes,
                    downloadedBytes=entry.size_bytes,
                    resolution=entry.resolution,
                ),
            )
        )
        download_log.info("Completed %s -> %s", entry.id, filename)

        loop = self._loop
        if loop is None or not loop.is_running():
            return

        def _add_history() -> None:
            asyncio.run_coroutine_threadsafe(
                history_service.add(
                    title=entry.title,
                    url=str(entry.request.url),
                    media_type=entry.request.media_type,
                    file_path=filename,
                    size_bytes=entry.size_bytes,
                    duration=0,
                    thumbnail=entry.thumbnail,
                    uploader=entry.uploader,
                ),
                loop,
            )

        loop.call_soon_threadsafe(_add_history)

    def _record_failure(self, entry: _Entry, error: str) -> None:
        """Write a failed history record."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return

        def _add() -> None:
            asyncio.run_coroutine_threadsafe(
                history_service.add(
                    title=entry.title or "Download failed",
                    url=str(entry.request.url),
                    media_type=entry.request.media_type,
                    file_path=entry.file_path,
                    size_bytes=0,
                    status="failed",
                ),
                loop,
            )

        loop.call_soon_threadsafe(_add)

    def _mark_entry(self, item_id: str, status: str, error: str, retries: int) -> None:
        """Update an entry's status and persist."""
        with self._lock:
            entry = self._entries.get(item_id)
            if not entry:
                return
            entry.status = status
            entry.error = error
            entry.retries = retries
            self._persist_entry(entry)
            self._forward(
                DownloadEvent(type=self._event_type(status), item=self._to_item(entry))
            )

    @staticmethod
    def _event_type(status: str) -> str:
        """Map a status to its wire event type."""
        mapping = {
            "COMPLETED": "completed",
            "CANCELLED": "cancelled",
            "FAILED": "failed",
            "PAUSED": "paused",
        }
        return mapping.get(status, "progress")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist_entry(self, entry: _Entry, insert: bool = False) -> None:
        """Persist an entry to SQLite on the event loop (async)."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        row = self._entry_to_row(entry)

        async def _write() -> None:
            try:
                if insert:
                    await self._persistence.insert(row)
                else:
                    await self._persistence.update(row)
            except Exception as exc:  # noqa: BLE001
                logger.error("Queue persistence failed: %s", exc)

        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(_write(), loop=loop)
        )

    def _delete_persisted(self, item_id: str) -> None:
        """Remove an item from persisted queue storage."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return

        async def _delete() -> None:
            try:
                await self._persistence.delete(item_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("Queue delete failed: %s", exc)

        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_delete(), loop=loop))

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def _forward(self, event: DownloadEvent) -> None:
        """Broadcast an event without syncing the entry back."""
        progress_manager.emit(event)

    @staticmethod
    def _entry_to_row(entry: _Entry) -> dict[str, Any]:
        """Convert an entry to a row dict for persistence."""
        return {
            "id": entry.id,
            "url": str(entry.request.url),
            "title": entry.title,
            "media_type": entry.request.media_type,
            "status": entry.status,
            "priority": entry.request.priority,
            "progress": entry.progress,
            "created_at": entry.created,
            "error": entry.error,
            "resolution": entry.resolution,
            "file_path": entry.file_path,
            "size_bytes": entry.size_bytes,
            "speed": entry.speed,
            "eta": entry.eta,
            "thumbnail": entry.thumbnail,
            "uploader": entry.uploader,
            "retries": entry.retries,
            "request_json": entry.request.model_dump_json(),
        }

    def _entry_from_row(self, row: dict[str, Any]) -> _Entry | None:
        """Rebuild an entry from a persisted row."""
        try:
            request = DownloadRequest.model_validate_json(
                row.get("request_json") or "{}"
            )
        except Exception:  # noqa: BLE001
            logger.warning("Skipping malformed queue row %s", row.get("id"))
            return None
        return _Entry(
            id=row.get("id", ""),
            request=request,
            status=str(row.get("status", "QUEUED")),
            title=row.get("title", ""),
            uploader=row.get("uploader", ""),
            thumbnail=row.get("thumbnail", ""),
            resolution=row.get("resolution", ""),
            file_path=row.get("file_path", ""),
            size_bytes=int(row.get("size_bytes", 0)),
            speed=row.get("speed", ""),
            eta=row.get("eta", ""),
            progress=float(row.get("progress", 0)),
            error=row.get("error", ""),
            retries=int(row.get("retries", 0)),
            created=int(row.get("created_at", 0)),
        )

    def _to_item(self, entry: _Entry) -> QueueItem:
        """Convert an entry into a QueueItem."""
        return QueueItem(
            id=entry.id,
            url=str(entry.request.url),
            title=entry.title,
            media_type=entry.request.media_type,
            status=entry.status,
            priority=entry.request.priority,
            progress=entry.progress,
            createdAt=entry.created,
            error=entry.error,
            resolution=entry.resolution,
            filePath=entry.file_path,
            sizeBytes=entry.size_bytes,
            speed=entry.speed,
            eta=entry.eta,
            thumbnail=entry.thumbnail,
            uploader=entry.uploader,
            retries=entry.retries,
        )

    @staticmethod
    def _file_size(path: str) -> int:
        """Return the size in bytes of the output file."""
        try:
            return Path(path).stat().st_size
        except OSError:
            return 0


# Module-level singleton for dependency injection.
download_manager = DownloadManager()

