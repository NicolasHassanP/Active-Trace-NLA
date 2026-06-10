import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E config for activia-trace frontend.
 *
 * Runs against the already-running Vite dev server at http://localhost:5173.
 * `webServer` is configured with reuseExistingServer so it attaches to the
 * running instance instead of spawning a duplicate.
 *
 * Prerequisites to run the suite:
 *   - Backend stack up (docker): http://localhost:8000  (GET /health → ok)
 *   - Frontend dev server up:    http://localhost:5173
 */
export default defineConfig({
  testDir: './e2e',
  // Auth fixtures log in via the API/UI; keep tests serial-friendly but allow parallelism per file.
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list']],
  timeout: 30_000,
  expect: { timeout: 7_000 },

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    // Each test logs in fresh (auth.fixture.ts) — the backend rotates refresh
    // tokens with reuse detection, so storageState cannot be shared across
    // parallel contexts. See the fixture header for details.
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
