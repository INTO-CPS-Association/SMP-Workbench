import { app, BrowserWindow, dialog, net, protocol, session, shell } from 'electron';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const rendererProtocol = 'smp-workbench';
const rendererHost = 'app';

let backendProcess = null;
let isQuitting = false;

protocol.registerSchemesAsPrivileged([
  {
    scheme: rendererProtocol,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: false,
    },
  },
]);

function getRendererRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'frontend');
  }
  return path.join(projectRoot, 'frontend', 'dist');
}

function isSubpath(parent, child) {
  const relative = path.relative(parent, child);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

async function fileExists(filePath) {
  try {
    const stat = await fs.stat(filePath);
    return stat.isFile();
  } catch {
    return false;
  }
}

async function executableExists(filePath) {
  try {
    const stat = await fs.stat(filePath);
    return stat.isFile();
  } catch {
    return false;
  }
}

function registerRendererProtocol() {
  const rendererRoot = getRendererRoot();
  protocol.handle(rendererProtocol, async (request) => {
    const requestUrl = new URL(request.url);
    if (requestUrl.hostname !== rendererHost) {
      return new Response('Not found', { status: 404 });
    }

    const pathname = decodeURIComponent(requestUrl.pathname || '/');
    const requestedPath = pathname === '/' ? '/index.html' : pathname;
    let filePath = path.normalize(path.join(rendererRoot, requestedPath));

    if (!isSubpath(rendererRoot, filePath)) {
      return new Response('Forbidden', { status: 403 });
    }

    if (!(await fileExists(filePath))) {
      filePath = path.join(rendererRoot, 'index.html');
    }

    return net.fetch(pathToFileURL(filePath).toString());
  });
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close(() => {
        if (address && typeof address === 'object') {
          resolve(address.port);
        } else {
          reject(new Error('Unable to allocate a backend port.'));
        }
      });
    });
  });
}

async function getPackagedBackendExecutable() {
  const executable = process.platform === 'win32'
    ? 'smp-workbench-backend.exe'
    : 'smp-workbench-backend';
  const backendRoot = path.join(process.resourcesPath, 'backend');
  const candidates = [
    path.join(backendRoot, executable),
    path.join(backendRoot, 'smp-workbench-backend', executable),
  ];

  for (const candidate of candidates) {
    if (await executableExists(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    `Packaged backend executable was not found. Checked: ${candidates.join(', ')}`,
  );
}

function getDevPythonCommand() {
  if (process.env.PYTHON) {
    return process.env.PYTHON;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

async function waitForBackend(apiBaseUrl, timeoutMs = 120000) {
  const healthUrl = new URL('/api/health', apiBaseUrl);
  const deadline = Date.now() + timeoutMs;
  let lastError = null;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        return;
      }
      lastError = new Error(`Health check returned ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Backend did not become ready: ${lastError?.message ?? 'unknown error'}`);
}

async function startBackend() {
  if (process.env.SMP_WORKBENCH_BACKEND_URL) {
    const apiBaseUrl = process.env.SMP_WORKBENCH_BACKEND_URL;
    await waitForBackend(apiBaseUrl);
    return apiBaseUrl;
  }

  const port = await getFreePort();
  const apiBaseUrl = `http://127.0.0.1:${port}`;
  const command = app.isPackaged ? await getPackagedBackendExecutable() : getDevPythonCommand();
  const args = app.isPackaged
    ? ['--port', String(port)]
    : ['-m', 'backend.desktop_main', '--port', String(port)];

  try {
    backendProcess = spawn(command, args, {
      cwd: app.isPackaged ? path.dirname(command) : projectRoot,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
      },
      stdio: app.isPackaged ? 'ignore' : 'inherit',
      windowsHide: true,
    });
  } catch (error) {
    throw new Error(
      `Failed to start packaged backend at ${command}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }

  const child = backendProcess;

  await new Promise((resolve, reject) => {
    const cleanup = () => {
      child.off('error', onError);
      child.off('exit', onExit);
    };
    const onError = (error) => {
      cleanup();
      backendProcess = null;
      reject(new Error(`Failed to start packaged backend at ${command}: ${error.message}`));
    };
    const onExit = (code, signal) => {
      cleanup();
      backendProcess = null;
      reject(new Error(`Backend exited before it was ready (${signal ?? code ?? 'unknown'}).`));
    };

    child.once('error', onError);
    child.once('exit', onExit);

    waitForBackend(apiBaseUrl)
      .then(() => {
        cleanup();
        resolve();
      })
      .catch((error) => {
        cleanup();
        reject(error);
      });
  });

  child.once('exit', (code, signal) => {
    backendProcess = null;
    if (!isQuitting) {
      dialog.showErrorBox(
        'SMP Workbench backend stopped',
        `The local analysis backend exited unexpectedly (${signal ?? code ?? 'unknown'}).`,
      );
      app.quit();
    }
  });

  return apiBaseUrl;
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    return;
  }

  const child = backendProcess;
  backendProcess = null;

  if (process.platform === 'win32' && child.pid) {
    spawn('taskkill', ['/pid', String(child.pid), '/t', '/f'], { windowsHide: true });
    return;
  }

  child.kill('SIGTERM');
  setTimeout(() => {
    if (!child.killed) {
      child.kill('SIGKILL');
    }
  }, 3000).unref();
}

function configureSecurity(window) {
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  window.webContents.on('will-navigate', (event, url) => {
    const devRendererUrl = process.env.SMP_WORKBENCH_RENDERER_URL;
    const allowedPrefix = devRendererUrl ?? `${rendererProtocol}://${rendererHost}`;
    if (!url.startsWith(allowedPrefix)) {
      event.preventDefault();
    }
  });
}

async function createWindow(apiBaseUrl) {
  process.env.SMP_WORKBENCH_API_BASE_URL = apiBaseUrl;

  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 960,
    minHeight: 680,
    title: 'SMP Workbench',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      additionalArguments: [`--smp-workbench-api-base-url=${apiBaseUrl}`],
    },
  });

  configureSecurity(mainWindow);

  const devRendererUrl = process.env.SMP_WORKBENCH_RENDERER_URL;
  if (devRendererUrl) {
    await mainWindow.loadURL(devRendererUrl);
  } else {
    await mainWindow.loadURL(`${rendererProtocol}://${rendererHost}/index.html`);
  }
}

app.on('before-quit', () => {
  isQuitting = true;
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.whenReady()
  .then(async () => {
    registerRendererProtocol();
    session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => {
      callback(false);
    });

    const apiBaseUrl = await startBackend();
    await createWindow(apiBaseUrl);

    app.on('activate', async () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        await createWindow(apiBaseUrl);
      }
    });
  })
  .catch((error) => {
    dialog.showErrorBox('SMP Workbench failed to start', error instanceof Error ? error.message : String(error));
    app.quit();
  });
