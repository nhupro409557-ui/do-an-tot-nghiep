import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

const configDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: './e2e',
  globalTeardown: './e2e/global-teardown.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://127.0.0.1:3001',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        '..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\scripts\\run_test_server.py --port 8001',
      url: 'http://127.0.0.1:8001/health',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
        TEST_DATABASE_STATE_FILE: path.resolve(
          configDir,
          'test-results/e2e-database.json',
        ),
      },
    },
    {
      command: 'npm run dev -- --port 3001',
      url: 'http://127.0.0.1:3001',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_API_BASE_URL: 'http://127.0.0.1:8001/api',
      },
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
