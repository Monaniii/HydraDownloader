"""History endpoints.

Thin HTTP adapters exposing history listing, deletion, and clearing.
All logic is delegated to the history service.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import HistoryListResponse
from app.services.history_service import history_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    type: str | None = Query(None, alias="type"),
) -> HistoryListResponse:
    """Return a filtered, paginated list of download history."""
    return await history_service.list(
        limit=limit,
        offset=offset,
        search=search,
        media_type=type,
    )


@router.delete("/{record_id}", status_code=204)
async def delete_history(record_id: str) -> None:
    """Delete a single history record."""
    if not await history_service.delete(record_id):
        raise HTTPException(status_code=404, detail="History record not found")


@router.delete("", status_code=204)
async def clear_history() -> None:
    """Clear all download history."""
    await history_service.clear()
