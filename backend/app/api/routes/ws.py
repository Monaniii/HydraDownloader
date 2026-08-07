"""WebSocket endpoints for streaming download events.

Connects a client to the progress manager and forwards download events
(type, item, progress) in near real time. The download manager pushes
events to the progress manager; this route is a pure transport for
those events.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import DownloadEvent
from app.services.progress_manager import progress_manager

router = APIRouter(tags=["websocket"])


async def _stream(websocket: WebSocket, client_id: str) -> None:
    """Read events from the progress manager and push them to a client."""
    queue: asyncio.Queue[DownloadEvent] = progress_manager.register(client_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump())
    except WebSocketDisconnect:
        pass
    finally:
        progress_manager.unregister(client_id)


@router.websocket("/ws/downloads")
async def ws_downloads(websocket: WebSocket) -> None:
    """Stream download lifecycle/queue events to a connected client."""
    await websocket.accept()
    await _stream(websocket, uuid.uuid4().hex)


@router.websocket("/ws/progress")
async def ws_progress(websocket: WebSocket) -> None:
    """Legacy alias streaming the same events for backwards compatibility."""
    await websocket.accept()
    await _stream(websocket, uuid.uuid4().hex)

