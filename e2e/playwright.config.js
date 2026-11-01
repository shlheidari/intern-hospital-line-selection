import { defineConfig } from '@playwright/test';

const port = process.env.E2E_PORT ?? '8765';

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.js',
  workers: 1, // the app keeps one working selection, so the tests share one student turn
  retries: 0,
  expect: { timeout: 10_000 }, // CI machines can be slow on a cold start
  reporter: [['list']],
  use: { baseURL: `http://127.0.0.1:${port}`, locale: 'en-US', viewport: { width: 1600, height: 1000 } },
  webServer: {
    command: 'node start-server.mjs',
    url: `http://127.0.0.1:${port}/`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
