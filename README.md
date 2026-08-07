# Hydra Downloader

A modern, cross-platform desktop application for downloading videos and audio from
websites supported by **yt-dlp**. Built with a clean, separated architecture:

```
Angular Frontend
       ↓
     Electron
       ↓
FastAPI Backend
       ↓
    yt-dlp
       ↓
    FFmpeg
```

The Angular frontend **never** executes `yt-dlp` directly. All downloads are handled
by the FastAPI backend, which Electron launches automatically on startup.

---

## Tech Stack

| Layer      | Technology                                   |
| ---------- | -------------------------------------------- |
| Frontend   | Angular 20, Angular Material, TailwindCSS    |
| Desktop    | Electron (context isolation, secure preload) |
| Backend    | Python 3.12+, FastAPI, uvicorn               |
| Downloader | yt-dlp                                       |
| Media      | FFmpeg                                       |
| Persistence| SQLite / JSON                                |

---

## Project Structure

```
HydraDownloader/
├── frontend/     # Angular 20 app (standalone components, signals)
├── backend/      # FastAPI app (clean architecture)
├── electron/     # Electron main process + preload
├── resources/    # Static resources (icons, binaries)
├── installer/    # Installer configuration
├── scripts/      # Dev/build automation
└── docs/         # Developer & user documentation
```

---

## Prerequisites

- **Node.js** 20+ (Angular 20 requires Node 20.19+)
- **Python** 3.12+
- **FFmpeg** (auto-detected; you can also set a custom path in Settings)
- **Git**

---

## Getting Started

### 1. Install Backend Dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt      # macOS/Linux
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Install Electron Dependencies

```bash
cd electron
npm install
```

### 4. Run in Development Mode

```bash
# From the project root
npm run dev
```

This starts the FastAPI backend, the Angular dev server, and launches Electron,
which loads the Angular app and connects to the backend automatically.

---

## Verification

Once running, you can verify the backend health endpoint independently:

```bash
curl http://127.0.0.1:8000/health
# => {"status":"ok","app":"Hydra Downloader API","version":"0.1.0"}
```

The Angular dashboard shows a live backend status indicator.

---

## API Base

The backend runs at `http://127.0.0.1:8000` in development. Interactive API docs
are available at [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs).

---

## Documentation

- [Developer Guide](docs/DEVELOPER.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Contributing](docs/CONTRIBUTING.md)

---

## License

Proprietary. All rights reserved.
# HydraDownloader
