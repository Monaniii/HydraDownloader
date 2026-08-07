"""Pydantic schemas for the Hydra Downloader API.

These models define the request/response contracts and are used to
validate inbound payloads and serialise outbound data.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


# ----------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    """Payload for the `POST /analyze` endpoint."""

    url: HttpUrl = Field(..., description="The video or playlist URL to analyze.")


class VideoFormat(BaseModel):
    """A single downloadable format extracted by yt-dlp."""

    formatId: str = ""
    extension: str = ""
    resolution: str = ""
    fps: int = 0
    filesize: int = 0
    videoCodec: str = ""
    audioCodec: str = ""
    note: str = ""


class Subtitle(BaseModel):
    """A subtitle track available on the media."""

    lang: str
    name: str
    url: str | None = None


class Chapter(BaseModel):
    """A chapter with a start time and title."""

    startTime: int
    endTime: int
    title: str


class VideoInfo(BaseModel):
    """The structured metadata returned after analysis."""

    id: str = ""
    title: str = ""
    description: str = ""
    duration: int = 0
    durationText: str = ""
    thumbnail: str = ""
    uploader: str = ""
    uploaderUrl: str = ""
    uploadDate: str = ""
    viewCount: int = 0
    likeCount: int = 0
    webpageUrl: str = ""
    channel: str = ""
    channelId: str = ""
    isPlaylist: bool = False
    playlistCount: int = 0
    subtitles: list[Subtitle] = []
    automaticCaptions: list[Subtitle] = []
    formats: list[VideoFormat] = []
    audioFormats: list[VideoFormat] = []
    videoFormats: list[VideoFormat] = []
    chapters: list[Chapter] = []


# ----------------------------------------------------------------------
# Downloads & Queue
# ----------------------------------------------------------------------
DownloadType = Literal["video", "audio", "playlist"]

# The complete download lifecycle state machine. Every download must
# always be in exactly one of these states.
DownloadState = Literal[
    "QUEUED",
    "INITIALIZING",
    "ANALYZING",
    "DOWNLOADING",
    "POST_PROCESSING",
    "PAUSED",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


class DownloadRequest(BaseModel):
    """Payload for enqueueing a download."""

    # Video
    url: HttpUrl = Field(..., description="The media URL to download.")
    formatId: str = Field("", description="Specific yt-dlp format id to force.")
    outputFolder: str = Field("", description="Override the output directory.")
    embedThumbnail: bool = Field(True, description="Embed the thumbnail when supported.")
    embedMetadata: bool = Field(True, description="Embed metadata when supported.")
    subtitles: bool = Field(False, description="Download/embed subtitles.")
    playlist: bool = Field(False, description="Download the whole playlist.")

    # Audio
    audioFormat: str = Field("mp3", description="Audio container when converting.")
    audioQuality: str = Field("0", description="Audio bitrate (kbps) or '0' for best.")

    # Metadata used by the queue/worker; kept separate from the wire
    # contract so the API can accept the richer object.
    media_type: DownloadType = Field("video", description="video, audio, or playlist")
    quality: str = Field("", description="Preferred quality (e.g. '1080p' or 'best').")
    video_format: str = Field("mp4", description="Video container when converting.")
    subtitle_langs: list[str] = Field(default_factory=list)
    output_dir: str = Field("", description="Override the output directory.")
    filename_template: str = Field("", description="Override the naming template.")
    priority: int = Field(0, ge=0, le=10, description="Queue priority (0=normal).")

    def effective_output_dir(self) -> str:
        """Return the folder override, preferring the modern field name."""
        return self.outputFolder or self.output_dir


class QueueItem(BaseModel):
    """A single item in the download queue."""

    id: str
    url: str
    title: str = ""
    media_type: str = "video"
    status: str = "QUEUED"
    priority: int = 0
    progress: float = 0.0
    createdAt: int = 0
    error: str = ""
    resolution: str = ""
    filePath: str = ""
    sizeBytes: int = 0
    speed: str = ""
    eta: str = ""
    thumbnail: str = ""
    uploader: str = ""
    retries: int = 0


# ----------------------------------------------------------------------
# Progress / events
# ----------------------------------------------------------------------
class ProgressUpdate(BaseModel):
    """A progress event streamed to the frontend via WebSocket."""

    id: str
    status: str = "QUEUED"
    progress: float = 0.0
    downloadedBytes: int = 0
    totalBytes: int = 0
    speed: str = ""
    eta: str = ""
    title: str = ""
    error: str = ""
    resolution: str = ""
    fragment: int = 0
    elapsed: float = 0.0
    filename: str = ""
    retries: int = 0


class DownloadEvent(BaseModel):
    """A discrete download lifecycle event pushed to /ws/downloads.

    ``type`` is one of: queued, started, progress, paused, resumed,
    completed, cancelled, failed, retrying.
    """

    type: str = "progress"
    item: QueueItem
    progress: ProgressUpdate | None = None


# ----------------------------------------------------------------------
# History
# ----------------------------------------------------------------------
class HistoryRecord(BaseModel):
    """A completed download stored in history."""

    id: str
    title: str = ""
    url: str = ""
    type: str = "video"
    filePath: str = ""
    sizeBytes: int = 0
    duration: int = 0
    thumbnail: str = ""
    uploader: str = ""
    status: str = "completed"
    createdAt: int = 0
    completedAt: int | None = None


class HistoryListResponse(BaseModel):
    """Paged history listing."""

    items: list[HistoryRecord]
    total: int = 0


# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------
class Settings(BaseModel):
    """Application settings persisted in SQLite."""

    theme: str = "dark"
    download_dir: str = ""
    parallel_downloads: int = 2
    default_video_quality: str = "best"
    default_audio_format: str = "mp3"
    default_audio_quality: str = "best"
    filename_template: str = "%(title)s.%(ext)s"
    subtitles_enabled: bool = False
    proxy: str = ""
    bandwidth_limit: str = ""
    language: str = "en"
    auto_update: bool = True
    ffmpeg_path: str = ""
    max_retries: int = 3
    open_folder_on_complete: bool = False


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------
class SearchResult(BaseModel):
    """A single search result from yt-dlp."""

    id: str = ""
    title: str = ""
    duration: int = 0
    thumbnail: str = ""
    uploader: str = ""
    viewCount: int = 0
    url: str = ""


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Standard error payload returned by the API."""

    error: str
    detail: str = ""
