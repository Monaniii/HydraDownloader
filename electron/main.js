/**
 * Electron main process for Hydra Downloader.
 *
 * Responsibilities:
 *  - Launch the FastAPI backend subprocess via BackendManager.
 *  - Create the BrowserWindow with secure settings (contextIsolation,
 *    nodeIntegration disabled, preload script).
 *  - Load either the Angular dev server (development) or built files
 *    (production).
 *  - Stop the backend gracefully when the app quits.
 */
'use strict';

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { BackendManager, BACKEND_HOST, BACKEND_PORT } = require('./backend-manager');

const isDev = !app.isPackaged;

// ----------------------------------------------------------------------
// Logging
// ----------------------------------------------------------------------
function log(level, message) {
  const line = `[${new Date().toISOString()}] [${level}] ${message}`;
  console.log(line);
}

const logger = {
  info: (m) => log('info', m),
  warn: (m) => log('warn', m),
  error: (m) => log('error', m),
};

// ----------------------------------------------------------------------
// Backend lifecycle
// ----------------------------------------------------------------------
const backendDir = path.join(__dirname, '..', 'backend');
const backend = new BackendManager({ logger, backendDir });

let backendReady = false;

async function startBackend() {
  backend.start();
  try {
    await backend.waitForReady();
    backendReady = true;
    logger.info('Backend is ready');
  } catch (err) {
    logger.error(`Backend failed to become ready: ${err.message}`);
  }
  broadcastBackendStatus();
}

function stopBackend() {
  backend.stop();
}

function broadcastBackendStatus() {
  const status = {
    running: backendReady,
    host: BACKEND_HOST,
    port: BACKEND_PORT,
  };
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('backend:status-changed', status);
  }
}

function getBackendStatus() {
  return {
    running: backendReady,
    host: BACKEND_HOST,
    port: BACKEND_PORT,
  };
}

// ----------------------------------------------------------------------
// IPC handlers
// ----------------------------------------------------------------------
ipcMain.handle('app:get-version', () => app.getVersion());
ipcMain.handle('app:get-platform', () => process.platform);
ipcMain.handle('backend:get-status', () => getBackendStatus());

// ----------------------------------------------------------------------
// Window creation
// ----------------------------------------------------------------------
function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: '#0b0f1a',
    title: 'Hydra Downloader',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.setMenuBarVisibility(false);

  if (isDev) {
    // In development, load the Angular dev server. The dev server is
    // expected to already be running via `npm start` in frontend/.
    const devUrl = process.env.HYDRA_DEV_URL || 'http://localhost:4200';
    win.loadURL(devUrl);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    const indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'frontend', 'browser', 'index.html');
    if (fs.existsSync(indexPath)) {
      win.loadFile(indexPath);
    } else {
      logger.error(`Built frontend not found at ${indexPath}`);
      win.loadURL('data:text/html,<h1>Frontend build not found</h1>');
    }
  }

  return win;
}

// ----------------------------------------------------------------------
// App lifecycle
// ----------------------------------------------------------------------
app.whenReady().then(async () => {
  logger.info('Hydra Downloader starting (dev=%s)', isDev);
  await startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  logger.info('Shutting down backend...');
  stopBackend();
});
