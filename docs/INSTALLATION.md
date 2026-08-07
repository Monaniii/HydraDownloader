# Installation Guide

## Development install

Follow the steps in [README.md](../README.md#getting-started).

## Requirements

| Component | Requirement |
| --------- | ----------- |
| Node.js   | 20.19+      |
| Python    | 3.12+       |
| FFmpeg    | 6.0+ (auto-detected) |

## Configuring FFmpeg

Hydra Downloader auto-detects FFmpeg on `PATH`. If FFmpeg is installed elsewhere,
set a custom path in **Settings → FFmpeg** (Phase 2). Set the `HYDRA_FFMPEG_PATH`
environment variable to override programmatically.

## Configuring the backend

The backend reads environment variables prefixed with `HYDRA_`:

```bash
HYDRA_HOST=127.0.0.1
HYDRA_PORT=8000
HYDRA_LOG_LEVEL=INFO
```

A `.env` file placed in `backend/` is also supported.

## Production packaging

Installers for Windows, Linux, and macOS are generated via the `installer/`
tooling (Phase 4). Installers bundle the Python runtime, yt-dlp, FFmpeg, the
Angular build, and Electron so no external installation is required.
