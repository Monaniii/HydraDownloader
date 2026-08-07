# Architecture

Hydra Downloader follows a strict three-tier separation of concerns. The Angular
frontend runs inside Electron, which launches and supervises a local FastAPI
backend. The backend owns all access to `yt-dlp` and FFmpeg.

## High-level diagram

```
┌──────────────────────────────┐
│        Angular Frontend      │
│  (UI, components, services)  │
└──────────────┬───────────────┘
               │ HTTP / WebSocket
┌──────────────▼───────────────┐
│           Electron           │
│  main process + preload      │
│  launches / supervises       │
└──────────────┬───────────────┘
               │ child process
┌──────────────▼───────────────┐
│        FastAPI Backend       │
│  routers → services → repos  │
└──────────────┬───────────────┘
               │ subprocess
┌──────────────▼───────────────┐
│            yt-dlp            │
└──────────────┬───────────────┘
               │ spawns
┌──────────────▼───────────────┐
│            FFmpeg            │
└──────────────────────────────┘
```

## Backend layers (clean architecture)

```
app/
├── core/       # Config, logging, infrastructure
├── api/
│   └── routes/ # HTTP adapters (thin, no business logic)
├── services/   # Business logic (analyzer, download, queue, ...)
└── models/     # Pydantic schemas / domain models
```

- **Routes** only parse requests and delegate to services.
- **Services** implement business rules and depend on repositories/factories.
- **Core** holds cross-cutting concerns (config, logging).

## Frontend structure

```
src/app/
├── core/       # Services, interceptors, error handler, guards
├── layout/     # App shell (sidebar, toolbar)
├── pages/      # Feature pages (lazy-loaded)
└── shared/     # Reusable components, dialogs, pipes
```

## Security model

- `nodeIntegration: false`
- `contextIsolation: true`
- Secure preload exposing a minimal IPC bridge
- `sandbox: true`
- Backend input validation via Pydantic models
- Filename/path sanitisation before any filesystem write
- No arbitrary shell execution from user input
