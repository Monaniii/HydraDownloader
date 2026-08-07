# Hydra Downloader — TODO

## ✅ Phase 1: Project Initialization & Architecture Scaffolding

- [x] Create repository structure (HydraDownloader/ folder)
- [x] Build FastAPI backend skeleton (clean architecture)
- [x] Scaffold Angular 20 frontend (standalone, lazy pages, dark theme)
- [x] Electron main process (backend launch/monitor/shutdown, secure preload)
- [x] scripts/, docs/, README
- [x] Verification: app launches, health endpoint responds

## ✅ Analyze (metadata extraction via yt-dlp)

- [x] Pydantic schemas, typed errors, analyzer_service.py, POST /analyze
- [x] Backend unit tests (14 passing)
- [x] Verified end-to-end with real YouTube URL
- [x] Frontend Analyze page & models

## ✅ Phase 2: Download Manager, Queue, Progress, History, Settings, Search

### Backend
- [x] Storage layer (SQLite via aiosqlite)
  - [x] app/storage/database.py — connection + schema init
  - [x] app/storage/history_repository.py
  - [x] app/storage/settings_repository.py
- [x] Services
  - [x] settings_service.py
  - [x] download_service.py (yt-dlp execution, progress hooks, ffmpeg)
  - [x] queue_manager.py (priority, concurrency, pause/resume/cancel/retry, persistence)
  - [x] progress_manager.py (track + WebSocket broadcast)
  - [x] history_service.py
- [x] Schemas (DownloadRequest, DownloadItem, ProgressUpdate, QueueItem, Settings, HistoryRecord, Search)
- [x] WebSocket route (GET /ws/progress)
- [x] Routes: download, queue, history, settings, search
- [x] Config additions (concurrency, download defaults, ffmpeg)
- [x] Backend unit tests
- [x] Verify endpoints via curl (analyze, download, queue, history, settings, search)

### Frontend
- [x] Services: download, queue store (Signals), history, settings, ws
- [x] Wire Downloads page (queue, progress, pause/resume/cancel/retry)
- [x] Wire History page (search, filter, delete, redownload)
- [x] Wire Settings page
- [x] Wire Dashboard (recent downloads, queue preview)
- [x] Models for new DTOs
- [x] `npm run build` passes

## 🔜 Phase 3 (future)
- [ ] Packaging (installers for Win/Linux/macOS)
- [ ] Auto-update support
</content>
