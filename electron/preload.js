/**
 * Preload script for Hydra Downloader.
 *
 * Exposes a minimal, secure IPC bridge to the renderer. Node integration
 * is disabled and context isolation is enabled, so the renderer can only
 * access what we explicitly expose here.
 */
'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Whitelisted IPC channels exposed to the renderer.
const VALID_INVOKE_CHANNELS = new Set([
  'app:get-version',
  'app:get-platform',
  'backend:get-status',
]);

contextBridge.exposeInMainWorld('hydra', {
  /**
   * Get application metadata.
   */
  getVersion: () => ipcRenderer.invoke('app:get-version'),
  getPlatform: () => ipcRenderer.invoke('app:get-platform'),
  getBackendStatus: () => ipcRenderer.invoke('backend:get-status'),

  /**
   * Subscribe to backend status updates pushed from the main process.
   * Returns an unsubscribe function.
   */
  onBackendStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on('backend:status-changed', listener);
    return () => ipcRenderer.removeListener('backend:status-changed', listener);
  },
});
