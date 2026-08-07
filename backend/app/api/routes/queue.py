"""Queue endpoints.

Thin HTTP adapters exposing queue state and control operations. All
logic is delegated to the download manager, which owns the queue and
the workers. No business logic lives in routes.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import QueueItem
from app.services.download_manager import download_manager

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=list[QueueItem])
def get_queue() -> list[QueueItem]:
    """Return the current download queue."""
    return download_manager.get_queue()


@router.get("/{item_id}", response_model=QueueItem)
def get_queue_item(item_id: str) -> QueueItem:
    """Return a single queue item by id."""
    item = download_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.delete("/{item_id}", response_model=dict)
def remove_item(item_id: str) -> dict:
    """Remove an item from the queue entirely (cancelling if active)."""
    if not download_manager.remove(item_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"removed": True, "id": item_id}


@router.post("/{item_id}/pause", response_model=QueueItem)
def pause(item_id: str) -> QueueItem:
    """Pause a queued or running download."""
    if not download_manager.pause(item_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    item = download_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.post("/{item_id}/resume", response_model=QueueItem)
def resume(item_id: str) -> QueueItem:
    """Resume a paused download."""
    if not download_manager.resume(item_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    item = download_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.post("/{item_id}/retry", response_model=QueueItem)
def retry(item_id: str) -> QueueItem:
    """Retry a failed or cancelled download."""
    if not download_manager.retry(item_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    item = download_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.delete("/cancel", response_model=QueueItem)
def cancel(item_id: str) -> QueueItem:
    """Cancel a queued or running download by id."""
    if not download_manager.cancel(item_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    item = download_manager.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item

