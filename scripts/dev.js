/**
 * Cross-platform development launcher for Hydra Downloader.
 *
 * Starts the FastAPI backend and the Angular dev server, then launches
 * Electron. Cleans up child processes on exit.
 */
'use strict';

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.join(__dirname, '..');
const backendDir = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');
const electronDir = path.join(root, 'electron');

const isWindows = process.platform === 'win32';

function resolvePython() {
  const candidates = isWindows
    ? [path.join(backendDir, '.venv', 'Scripts', 'python.exe')]
    : [path.join(backendDir, '.venv', 'bin', 'python')];
  return candidates.find((p) => fs.existsSync(p)) || (isWindows ? 'python' : 'python3');
}

function log(msg) {
  console.log(`[dev] ${msg}`);
}

async function main() {
  log('Starting Hydra Downloader in development mode');

  // 1. Backend
  const python = resolvePython();
  log(`Launching backend with ${python}`);
  const backend = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'], {
    cwd: backendDir,
    stdio: 'inherit',
    windowsHide: true,
  });

  // 2. Frontend
  const npmCmd = isWindows ? 'npm.cmd' : 'npm';
  log('Launching Angular dev server');
  const frontend = spawn(npmCmd, ['start'], { cwd: frontendDir, stdio: 'inherit', windowsHide: true });

  // Wait for dev server, then launch Electron
  await new Promise((r) => setTimeout(r, 8000));
  log('Launching Electron');
  const electron = spawn(npmCmd, ['start'], { cwd: electronDir, stdio: 'inherit', windowsHide: true });

  const shutdown = () => {
    log('Shutting down...');
    backend.kill();
    frontend.kill();
    electron.kill();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
