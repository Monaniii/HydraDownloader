#!/usr/bin/env bash
# Development launcher for Hydra Downloader (macOS/Linux).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
ELECTRON_DIR="$ROOT/electron"

echo "=== Hydra Downloader | Dev Mode ==="

# 1. Start backend
PYTHON="$BACKEND_DIR/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
  PYTHON="python3"
fi
echo "Starting FastAPI backend..."
(cd "$BACKEND_DIR" && "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
BACKEND_PID=$!

# 2. Start Angular dev server
echo "Starting Angular dev server..."
(cd "$FRONTEND_DIR" && npm start) &
FRONTEND_PID=$!

# 3. Launch Electron
sleep 8
echo "Launching Electron..."
(cd "$ELECTRON_DIR" && npm start)

# Cleanup
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
