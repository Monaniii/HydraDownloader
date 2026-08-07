"""Unit tests for the AnalyzerService.

These tests verify the metadata transformation and error-mapping logic
without requiring network access by mocking the yt-dlp extraction.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.errors import (
    AppError,
    InvalidURLError,
    NetworkError,
    UnavailableVideoError,
    UnsupportedSiteError,
)
from app.services.analyzer_service import AnalyzerService


@pytest.fixture
def service() -> AnalyzerService:
    """Return a fresh AnalyzerService instance per test."""
    return AnalyzerService()


class TestValidateURL:
    """Tests for URL validation."""

    def test_rejects_missing_url(self, service: AnalyzerService) -> None:
        with pytest.raises(InvalidURLError):
            service._validate_url("")  # noqa: SLF001

    def test_rejects_non_http_url(self, service: AnalyzerService) -> None:
        with pytest.raises(InvalidURLError):
            service._validate_url("not-a-url")  # noqa: SLF001

    def test_accepts_http_url(self, service: AnalyzerService) -> None:
        service._validate_url("https://example.com/watch?v=abc")  # noqa: SLF001


class TestToVideoInfo:
    """Tests for converting raw yt-dlp info into VideoInfo."""

    def test_single_video_conversion(self, service: AnalyzerService) -> None:
        raw = {
            "_type": "video",
            "id": "abc123",
            "title": "Test Video",
            "duration": 125,
            "duration_string": "2:05",
            "thumbnail": "https://img.example/thumb.jpg",
            "uploader": "Test Channel",
            "view_count": 1000,
            "formats": [
                {
                    "format_id": "137",
                    "ext": "mp4",
                    "resolution": "1080p",
                    "height": 1080,
                    "fps": 30,
                    "vcodec": "avc1",
                    "acodec": "none",
                },
                {
                    "format_id": "251",
                    "ext": "webm",
                    "resolution": "audio only",
                    "vcodec": "none",
                    "acodec": "opus",
                },
            ],
        }

        info = service._to_video_info(raw)  # noqa: SLF001

        assert info.id == "abc123"
        assert info.title == "Test Video"
        assert info.duration == 125
        assert info.isPlaylist is False
        assert len(info.formats) == 2
        assert info.videoFormats[0].resolution == "1080p"
        assert info.audioFormats[0].audioCodec == "opus"

    def test_playlist_detection(self, service: AnalyzerService) -> None:
        raw = {
            "_type": "playlist",
            "title": "My Playlist",
            "playlist_count": 3,
            "entries": [
                {"id": "v1", "title": "First", "duration": 60},
                {"id": "v2", "title": "Second", "duration": 90},
            ],
        }

        info = service._to_video_info(raw)  # noqa: SLF001

        assert info.isPlaylist is True
        assert info.playlistCount == 3
        # Title comes from the first entry for display.
        assert info.title == "First"


class TestFormatDuration:
    """Tests for the duration formatter."""

    def test_seconds_only(self, service: AnalyzerService) -> None:
        assert service._format_duration(45) == "0:45"  # noqa: SLF001

    def test_minutes_and_seconds(self, service: AnalyzerService) -> None:
        assert service._format_duration(125) == "2:05"  # noqa: SLF001

    def test_hours(self, service: AnalyzerService) -> None:
        assert service._format_duration(3661) == "1:01:01"  # noqa: SLF001

    def test_none_returns_empty(self, service: AnalyzerService) -> None:
        assert service._format_duration(None) == ""  # noqa: SLF001

    def test_invalid_returns_empty(self, service: AnalyzerService) -> None:
        assert service._format_duration("abc") == ""  # noqa: SLF001


class TestMapDownloadError:
    """Tests for translating yt-dlp errors into typed AppErrors."""

    def test_unsupported_site(self, service: AnalyzerService) -> None:
        class FakeCause(Exception):
            pass

        exc = type("FakeDownloadError", (Exception,), {"cause": FakeCause()})()
        with patch("app.services.analyzer_service.UnsupportedError", FakeCause):
            mapped = service._map_download_error(exc)  # noqa: SLF001
        assert isinstance(mapped, UnsupportedSiteError)

    def test_age_restricted(self, service: AnalyzerService) -> None:
        wrapped = type("FakeDownloadError", (Exception,), {"cause": None})(
            "Sign in to confirm your age"
        )
        mapped = service._map_download_error(wrapped)  # noqa: SLF001
        assert isinstance(mapped, AppError)

    def test_unavailable_video(self, service: AnalyzerService) -> None:
        class FakeCause(Exception):
            pass

        exc = type("FakeDownloadError", (Exception,), {"cause": FakeCause()})(
            "Video unavailable"
        )
        mapped = service._map_download_error(exc)  # noqa: SLF001
        assert isinstance(mapped, UnavailableVideoError)

    def test_network_error(self, service: AnalyzerService) -> None:
        class FakeCause(Exception):
            pass

        exc = type("FakeDownloadError", (Exception,), {"cause": FakeCause()})(
            "Unable to download: connection error"
        )
        mapped = service._map_download_error(exc)  # noqa: SLF001
        assert isinstance(mapped, NetworkError)
