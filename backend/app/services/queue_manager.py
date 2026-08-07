"""Queue manager.

Maintains the download queue, enforces the maximum concurrency, and
orchestrates running downloads in worker threads. Supports queueing,
cancelling, pausing, resuming, and retrieving queue state. A simplified
in-memory queue is used; persistence can be layered on later.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from app.core.logging import get_logger
from app.models.schemas import DownloadRequest, ProgressUpdate, QueueItem
from app.services.download_service import DownloadService
from app.services.history_service import history_service
from app.services.progress_manager import progress_manager

logger = get_logger(__name__)


class QueueManager:
    """Priority queue with configurable concurrency for downloads."""

    def __init__(self, download_svc: DownloadService, max_concurrent: int = 2) -> None:
        self._download = download_svc
        self._max_concurrent = max_concurrent
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = 0
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the main event loop for scheduling history writes."""
        self._loop = loop

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------
    def enqueue(self, request: DownloadRequest) -> QueueItem:
        """Add a download to the queue and start processing."""
        item_id = uuid.uuid4().hex
        item: dict[str, Any] = {
            "id": item_id,
            "url": str(request.url),
            "title": "",
            "media_type": request.media_type,
            "status": "queued",
            "priority": request.priority,
            "progress": 0.0,
            "createdAt": int(time.time()),
            "error": "",
            "request": request,
            "cancel_event": threading.Event(),
            "worker": None,
        }
        with self._lock:
            self._items[item_id] = item

        logger.info("Enqueued download %s (%s)", item_id, request.url)
        self._schedule()
        return self._to_item(item)

    def cancel(self, item_id: str) -> bool:
        """Cancel a queued or running download. Returns True if found."""
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return False
            item["cancel_event"].set()
            if item["status"] in ("queued", "downloading"):
                item["status"] = "cancelled"
                self._update_progress(item)
        return True

    def pause(self, item_id: str) -> bool:
        """Pause a queued download (no-op for simplicity)."""
        with self._lock:
            item = self._items.get(item_id)
            if not item or item["status"] != "queued":
                return False
            item["status"] = "paused"
            self._update_progress(item)
        return True

    def resume(self, item_id: str) -> bool:
        """Resume a paused download by re-queueing it."""
        with self._lock:
            item = self._items.get(item_id)
            if not item or item["status"] != "paused":
                return False
            item["status"] = "queued"
            self._update_progress(item)
        self._schedule()
        return True

    def get_queue(self) -> list[QueueItem]:
        """Return the current queue as a list of QueueItems."""
        with self._lock:
            return [self._to_item(item) for item in self._items.values()]

    def get_item(self, item_id: str) -> QueueItem | None:
        """Return a single queue item, or None."""
        with self._lock:
            item = self._items.get(item_id)
            return self._to_item(item) if item else None

    # ------------------------------------------------------------------
    # Concurrency / worker orchestration
    # ------------------------------------------------------------------
    def _schedule(self) -> None:
        """Start workers for queued items up to the concurrency limit."""
        while self._running < self._max_concurrent:
            with self._lock:
                # Pick the highest-priority queued item (lower number = higher).
                candidates = [
                    item
                    for item in self._items.values()
                    if item["status"] == "queued"
                ]
                if not candidates:
                    return
                candidates.sort(key=lambda i: i["priority"])
                item = candidates[0]
                item["status"] = "downloading"
                self._running += 1

            self._update_progress(item)
            # Run the download in a thread.
            threading.Thread(
                target=self._run_worker,
                args=(item["id"],),
                daemon=True,
            ).start()

    def _run_worker(self, item_id: str) -> None:
        """Run a single download in a worker thread."""
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return

        progress_cb = lambda u: self._forward_progress(item_id, u)  # noqa: E731

        try:
            if item["cancel_event"].is_set():
                raise InterruptedError("cancelled")
            filename = self._download.run(item["request"], item_id, progress_cb)
            with self._lock:
                item["status"] = "completed"
                item["progress"] = 100.0
                item["file_path"] = filename
            self._record_history(item)
        except InterruptedError:
            with self._lock:
                item = self._items.get(item_id)
                if item:
                    item["status"] = "cancelled"
        except Exception as exc:  # noqa: BLE001
            logger.error("Worker error for %s: %s", item_id, exc)
            with self._lock:
                item = self._items.get(item_id)
                if item:
                    item["status"] = "failed"
                    item["error"] = str(exc)
        finally:
            with self._lock:
                self._running = max(0, self._running - 1)
            self._update_progress(item) if item else None
            self._schedule()

    def _record_history(self, item: dict[str, Any]) -> None:
        """Persist a completed download to history on the event loop."""
        if self._loop is None:
            return
        loop = self._loop
        request = item.get("request")
        title = item.get("title", "")
        try:
            file_path = item.get("file_path", "")
            size_bytes = Path(file_path).stat().st_size if file_path else 0
        except OSError:
            size_bytes = 0

        def _add() -> None:
            import asyncio

            try:
                asyncio.run_coroutine_threadsafe(
                    history_service.add(
                        title=title,
                        url=str(request.url) if request else item.get("url", ""),
                        media_type=item.get("media_type", "video"),
                        file_path=item.get("file_path", ""),
                        size_bytes=size_bytes,
                    ),
                    loop,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to record history for %s: %s", item["id"], exc)

        if loop.is_running():
            loop.call_soon_threadsafe(_add)
        else:
            _add()

    def _forward_progress(self, item_id: str, update: ProgressUpdate) -> None:
        """Store progress on the item and broadcast via the manager."""
        with self._lock:
            item = self._items.get(item_id)
            if item:
                item["progress"] = update.progress
                item["title"] = update.title or item["title"]
        progress_manager.update(update)

    def _update_progress(self, item: dict[str, Any]) -> None:
        """Broadcast the current state of an item as a progress update."""
        progress_manager.update(
            ProgressUpdate(
                id=item["id"],
                status=item["status"],
                progress=item["progress"],
                title=item["title"],
                error=item.get("error", ""),
            )
        )

    @staticmethod
    def _to_item(item: dict[str, Any]) -> QueueItem:
        """Convert an internal item dict into a QueueItem."""
        return QueueItem(
            id=item["id"],
            url=item["url"],
            title=item.get("title", ""),
            media_type=item.get("media_type", "video"),
            status=item["status"],
            priority=item.get("priority", 0),
            progress=item.get("progress", 0.0),
            createdAt=item.get("createdAt", 0),
            error=item.get("error", ""),
        )


# Module-level singleton wired with the download service.
from app.services.download_service import download_service as _download_svc

queue_manager = QueueManager(_download_svc)
