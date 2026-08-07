"""Custom exceptions for the Hydra Downloader backend.

Each exception maps to an appropriate HTTP status code so routes can
return meaningful, user-friendly errors without embedding business
logic in the HTTP layer.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class InvalidURLError(AppError):
    """Raised when the supplied URL is malformed or unusable."""

    status_code = 400
    message = "The provided URL is invalid."


class UnsupportedSiteError(AppError):
    """Raised when yt-dlp has no extractor for the given site."""

    status_code = 422
    message = "This website is not supported."


class UnavailableVideoError(AppError):
    """Raised when a video is unavailable, private, or deleted."""

    status_code = 404
    message = "The requested video is unavailable or private."


class AgeRestrictedError(AppError):
    """Raised when a video is age-restricted without authentication."""

    status_code = 403
    message = "This video is age-restricted."


class NetworkError(AppError):
    """Raised when a network-level failure prevents extraction."""

    status_code = 502
    message = "A network error occurred while contacting the host."


class TimeoutError(AppError):
    """Raised when extraction exceeds the allowed time budget."""

    status_code = 504
    message = "The request timed out."


class DownloadError(AppError):
    """Raised when a download fails."""

    status_code = 500
    message = "The download failed."


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    message = "The requested resource was not found."


class FFmpegNotFoundError(DownloadError):
    """Raised when FFmpeg is required but cannot be located."""

    status_code = 500
    message = "FFmpeg is required for this operation but was not found."


class MissingFFmpegError(FFmpegNotFoundError):
    """Alias describing a missing FFmpeg binary for conversion tasks."""

    message = "FFmpeg was not detected. It is required for this download."


class DiskFullError(DownloadError):
    """Raised when there is insufficient disk space for the download."""

    status_code = 507
    message = "Not enough disk space to complete the download."


class PermissionDeniedError(DownloadError):
    """Raised when the OS denies access to a file or directory."""

    status_code = 403
    message = "Permission denied while writing files."


class FileExistsError_(DownloadError):
    """Raised when a destination file already exists (collision)."""

    status_code = 409
    message = "The destination file already exists."


class UnsupportedFormatError(DownloadError):
    """Raised when the requested output format is not supported."""

    status_code = 422
    message = "The requested output format is not supported."


class InterruptedDownloadError(DownloadError):
    """Raised internally when a download is cancelled or interrupted."""

    status_code = 499
    message = "The download was interrupted."


class RetryableDownloadError(DownloadError):
    """Raised when a failure is transient and should be retried."""

    status_code = 500
    message = "A transient download error occurred; retrying."
