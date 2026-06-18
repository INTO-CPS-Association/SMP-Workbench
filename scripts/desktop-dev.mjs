import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const rendererUrl = 'http://127.0.0.1:5173';
const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';
const electronCommand = path.join(
  projectRoot,
  'node_modules',
  '.bin',
  isWindows ? 'electron.cmd' : 'electron',
);

const children = new Set();
let shuttingDown = false;

function spawnChild(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: projectRoot,
    stdio: 'inherit',
    shell: false,
    windowsHide: true,
    ...options,
  });
  children.add(child);
  child.once('exit', () => children.delete(child));
  return child;
}

function shutdown(code = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  for (const child of children) {
    if (!child.killed) {
      child.kill(isWindows ? undefined : 'SIGTERM');
    }
  }

  setTimeout(() => process.exit(code), 500).unref();
}

async function waitForRenderer(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(rendererUrl);
      if (response.ok) {
        return;
      }
      lastError = new Error(`Vite returned ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Vite dev server did not start: ${lastError?.message ?? 'unknown error'}`);
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

const vite = spawnChild(npmCommand, ['--prefix', 'frontend', 'run', 'dev', '--', '--host', '127.0.0.1']);

try {
  await waitForRenderer();
  const electron = spawnChild(electronCommand, ['.'], {
    env: {
      ...process.env,
      SMP_WORKBENCH_RENDERER_URL: rendererUrl,
    },
  });
  electron.once('exit', (code) => shutdown(code ?? 0));
  vite.once('exit', (code) => {
    if (!shuttingDown) {
      shutdown(code ?? 1);
    }
  });
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  shutdown(1);
}
