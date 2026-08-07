"""Search endpoint.

Thin HTTP adapter exposing media search via the search service.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import SearchResult
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    platform: str = Query("ytsearch", description="yt-dlp search prefix"),
) -> list[SearchResult]:
    """Search for media on supported platforms."""
    return await search_service.search(q, platform=platform)
