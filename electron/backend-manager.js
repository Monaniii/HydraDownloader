/**
 * BackendManager
 *
 * Responsible for launching, monitoring, and shutting down the FastAPI
 * Python backend subprocess. Failures are handled so that if the backend
 * crashes, it is restarted after a short delay.
 */
'use strict';

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');

const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 8000;
const RETRY_DELAY_MS = 3000;

class BackendManager {
  constructor({ logger, pythonPath, backendDir }) {
    this.logger = logger;
    this.pythonPath = pythonPath;
    this.backendDir = backendDir;
    this.process = null;
    this.shuttingDown = false;
    this.restartTimer = null;
  }

  /**
   * Resolve the Python interpreter path.
   */
  resolvePython() {
    if (process.env.HYDRA_PYTHON_PATH) {
      return process.env.HYDRA_PYTHON_PATH;
    }

    const venvCandidates = [
      path.join(this.backendDir, '.venv', 'Scripts', 'python.exe'),
      path.join(this.backendDir, '.venv', 'bin', 'python'),
    ];

    for (const candidate of venvCandidates) {
      if (fs.existsSync(candidate)) {
        this.logger.info(`Using Python from venv: ${candidate}`);
        return candidate;
      }
    }

    this.logger.warn('No venv Python found; falling back to system python');
    return 'python';
  }

  /**
   * Start the uvicorn backend process.
   */
  start() {
    const python = this.resolvePython();
    const args = [
      '-m',
      'uvicorn',
      'app.main:app',
      '--host',
      BACKEND_HOST,
      '--port',
      String(BACKEND_PORT),
    ];

    this.logger.info(`Launching backend: ${python} ${args.join(' ')}`);

    this.process = spawn(python, args, {
      cwd: this.backendDir,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    this.process.stdout.on('data', (chunk) => {
      this.logger.info(`[backend] ${String(chunk).trimEnd()}`);
    });

    this.process.stderr.on('data', (chunk) => {
      this.logger.warn(`[backend] ${String(chunk).trimEnd()}`);
    });

    this.process.on('exit', (code, signal) => {
      this.logger.warn(`Backend exited with code=${code} signal=${signal}`);
      this.process = null;
      if (!this.shuttingDown) {
        this.scheduleRestart();
      }
    });

    this.process.on('error', (err) => {
      this.logger.error(`Failed to start backend: ${err.message}`);
      this.process = null;
      if (!this.shuttingDown) {
        this.scheduleRestart();
      }
    });
  }

  /**
   * Schedule a restart of the backend after a delay.
   */
  scheduleRestart() {
    if (this.restartTimer || this.shuttingDown) return;
    this.logger.info(`Scheduling backend restart in ${RETRY_DELAY_MS}ms`);
    this.restartTimer = setTimeout(() => {
      this.restartTimer = null;
      this.start();
    }, RETRY_DELAY_MS);
  }

  /**
   * Wait until the backend is accepting connections.
   */
  waitForReady(timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + timeoutMs;
      const attempt = () => {
        const socket = net.createConnection({
          host: BACKEND_HOST,
          port: BACKEND_PORT,
        });
        socket.once('connect', () => {
          socket.destroy();
          resolve();
        });
        socket.once('error', () => {
          socket.destroy();
          if (Date.now() > deadline) {
            reject(new Error('Timed out waiting for backend to become ready'));
          } else {
            setTimeout(attempt, 500);
          }
        });
      };
      attempt();
    });
  }

  /**
   * Stop the backend process gracefully.
   */
  async stop() {
    this.shuttingDown = true;
    if (this.restartTimer) {
      clearTimeout(this.restartTimer);
      this.restartTimer = null;
    }
    if (this.process && !this.process.killed) {
      this.logger.info('Stopping backend...');
      this.process.kill();
      setTimeout(() => {
        if (this.process && !this.process.killed) {
          this.process.kill('SIGKILL');
        }
      }, 1500);
    }
  }
}

module.exports = { BackendManager, BACKEND_HOST, BACKEND_PORT };
