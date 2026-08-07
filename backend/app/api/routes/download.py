"""Download endpoints.

Thin HTTP adapters that delegate to the download manager. No business
logic lives here, keeping routes as pure transport handlers. All
downloads pass through the download manager; the API never calls
yt-dlp directly.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import DownloadRequest, QueueItem
from app.services.download_manager import download_manager

router = APIRouter(prefix="/download", tags=["download"])


@router.post("/video", response_model=QueueItem)
def download_video(request: DownloadRequest) -> QueueItem:
    """Enqueue a video download."""
    req = request.model_copy(update={"media_type": "video"})
    return download_manager.enqueue(req)


@router.post("/audio", response_model=QueueItem)
def download_audio(request: DownloadRequest) -> QueueItem:
    """Enqueue an audio download."""
    req = request.model_copy(update={"media_type": "audio"})
    return download_manager.enqueue(req)


@router.post("/playlist", response_model=QueueItem)
def download_playlist(request: DownloadRequest) -> QueueItem:
    """Enqueue a playlist download."""
    req = request.model_copy(update={"media_type": "playlist"})
    return download_manager.enqueue(req)
