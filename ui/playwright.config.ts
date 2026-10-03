import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: 'e2e',
  testIgnore: /perf\.spec\.ts/,
  timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:5322', trace: 'retain-on-failure', viewport: { width: 1440, height: 900 } },
  webServer: {
    command: 'uv run --project .. flight-recorder demo --dir ../.e2e/demo --port 5322 --no-browser',
    url: 'http://127.0.0.1:5322/api/health',
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
})
