import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  testMatch: /perf\.spec\.ts/,
  timeout: 300_000,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5325', viewport: { width: 1440, height: 900 } },
  webServer: {
    command: 'uv run --project .. flight-recorder demo --dir ../.bench/ui --long 10000 --port 5325 --no-browser',
    url: 'http://127.0.0.1:5325/api/health',
    reuseExistingServer: false,
    timeout: 240_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
})
