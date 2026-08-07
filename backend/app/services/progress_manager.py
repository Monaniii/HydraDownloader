"""Progress manager.

Tracks per-download state and broadcasts lifecycle events to connected
WebSocket clients. This decouples download execution (which reports raw
events) from the transport (which delivers them to the frontend).

The manager is thread-safe: events arrive from worker threads and must
be scheduled onto the main event loop so WebSocket clients receive them
correctly.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from app.models.schemas import DownloadEvent, ProgressUpdate

# A registry of connected WebSocket queues keyed by client id.
_WS_REGISTRY: dict[str, asyncio.Queue] = {}
_REGISTRY_LOCK = threading.Lock()


class ProgressManager:
    """Central store for progress events and WebSocket fan-out."""

    def __init__(self) -> None:
        self._state: dict[str, ProgressUpdate] = {}
        self._state_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the main event loop for thread-safe scheduling."""
        self._loop = loop

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------
    def emit(self, event: DownloadEvent) -> None:
        """Broadcast a download event (thread-safe).

        Also keeps the latest ProgressUpdate for the item in state so a
        newly-connected client receives the current snapshot.
        """
        if event.progress is not None:
            with self._state_lock:
                self._state[event.item.id] = event.progress
        # If only a state event (no progress payload), build one.
        else:
            update = self._update_from_item(event)
            if event.item.id:
                with self._state_lock:
                    self._state[event.item.id] = update

        loop = self._loop
        if loop is None:
            return
        if loop.is_running():
            loop.call_soon_threadsafe(self._broadcast, event)
        else:
            loop.call_soon(self._broadcast, event)

    def update(self, update: ProgressUpdate) -> None:
        """Record and broadcast a raw progress update (compat helper)."""
        event = DownloadEvent(
            type=self._infer_type(update.status),
            item=self._item_from_progress(update),
            progress=update,
        )
        self.emit(event)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def get(self, item_id: str) -> ProgressUpdate | None:
        """Return the latest progress for an item, or None."""
        with self._state_lock:
            return self._state.get(item_id)

    def get_all(self) -> list[ProgressUpdate]:
        """Return all tracked progress updates."""
        with self._state_lock:
            return list(self._state.values())

    def remove(self, item_id: str) -> None:
        """Drop an item from the progress store."""
        with self._state_lock:
            self._state.pop(item_id, None)

    # ------------------------------------------------------------------
    # WebSocket fan-out
    # ------------------------------------------------------------------
    def register(self, client_id: str) -> asyncio.Queue:
        """Register a WebSocket client and return its message queue."""
        queue: asyncio.Queue = asyncio.Queue()
        with _REGISTRY_LOCK:
            _WS_REGISTRY[client_id] = queue
        # Send current snapshots so a new client starts up to date.
        with self._state_lock:
            snapshot = list(self._state.values())
        for update in snapshot:
            event = DownloadEvent(
                type="snapshot",
                item=self._item_from_progress(update),
                progress=update,
            )
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
        return queue

    def unregister(self, client_id: str) -> None:
        """Remove a WebSocket client from the registry."""
        with _REGISTRY_LOCK:
            _WS_REGISTRY.pop(client_id, None)

    @staticmethod
    def _broadcast(event: DownloadEvent) -> None:
        """Push an event into every registered client queue."""
        with _REGISTRY_LOCK:
            targets = list(_WS_REGISTRY.values())
        for queue in targets:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _infer_type(status: str) -> str:
        """Map a ProgressUpdate status to a wire event type."""
        mapping = {
            "COMPLETED": "completed",
            "CANCELLED": "cancelled",
            "FAILED": "failed",
            "PAUSED": "paused",
            "QUEUED": "queued",
            "RETRYING": "retrying",
        }
        return mapping.get(status, "progress")

    @staticmethod
    def _update_from_item(event: DownloadEvent) -> ProgressUpdate:
        """Build a ProgressUpdate from a bare state event."""
        item = event.item
        return ProgressUpdate(
            id=item.id,
            status=item.status,
            progress=item.progress,
            downloadedBytes=item.sizeBytes,
            totalBytes=item.sizeBytes,
            title=item.title,
            resolution=item.resolution,
            error=item.error,
            retries=item.retries,
        )

    @staticmethod
    def _item_from_progress(update: ProgressUpdate) -> Any:
        """Build a minimal QueueItem for a progress update."""
        from app.models.schemas import QueueItem

        return QueueItem(
            id=update.id,
            url="",
            title=update.title,
            status=update.status,
            progress=update.progress,
            error=update.error,
            resolution=update.resolution,
            speed=update.speed,
            eta=update.eta,
            retries=update.retries,
        )


# Module-level singleton.
progress_manager = ProgressManager()

