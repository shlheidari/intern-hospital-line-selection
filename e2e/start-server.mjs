// Starts a throw-away Django server with demo data for the Playwright tests.
// Uses E2E_PYTHON (default: python3, or python on Windows).
import { spawn, spawnSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cwd = join(root, 'myworld');
const python = process.env.E2E_PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3');
const database = join(root, 'e2e', '.e2e.sqlite3');
const env = { ...process.env, DEBUG: 'True', SECRET_KEY: 'e2e-only', DB_NAME: database, PYTHONWARNINGS: 'ignore' };
const port = process.env.E2E_PORT ?? '8765';

rmSync(database, { force: true });
for (const args of [['manage.py', 'migrate', '--noinput'], ['manage.py', 'seed_demo', '--students', '3']]) {
  const result = spawnSync(python, args, { cwd, env, stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
const server = spawn(python, ['manage.py', 'runserver', `127.0.0.1:${port}`, '--noreload'], { cwd, env, stdio: 'inherit' });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.kill());
server.on('exit', (code) => process.exit(code ?? 0));
