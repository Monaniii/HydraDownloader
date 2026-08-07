# Developer Guide

## Repository layout

```
HydraDownloader/
├── frontend/   # Angular 20 app
├── backend/    # FastAPI app
├── electron/   # Electron main process
└── scripts/    # Dev/build tooling
```

## Prerequisites

- Node 20.19+ (Node 22 recommended)
- Python 3.12+ (Python 3.14 verified)
- FFmpeg (optional during dev; required for downloads)

## One-time setup

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Electron
cd ../electron
npm install
```

## Running in development

```bash
npm run dev          # from repo root
```

`npm run dev` starts:
1. FastAPI backend on `127.0.0.1:8000`
2. Angular dev server on `localhost:4200`
3. Electron, which launches the backend and loads the dev server

## Running pieces independently

```bash
npm run backend      # uvicorn with reload
npm run frontend     # Angular dev server
npm run electron     # Electron only (backend must be running)
```

## Backend conventions

- Add new endpoints in `backend/app/api/routes/`.
- Implement logic in `backend/app/services/`.
- Never import `yt_dlp` inside a route.
- Use `get_logger(__name__)` for logging.
- Validate inputs with Pydantic models.

## Frontend conventions

- Use standalone components.
- Prefer signals for local state; use RxJS for async streams.
- Lazy-load feature pages.
- Route all HTTP through `ApiService`.
- Handle errors via the global error handler.

## Testing

```bash
cd frontend && npm test          # Karma unit tests
cd backend && .venv\Scripts\python -m pytest   # backend tests
```

## Building for production

```bash
npm run build:frontend
# then run electron in production mode (loads built files)
