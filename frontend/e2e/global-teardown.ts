import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export default function globalTeardown() {
  const teardownDir = path.dirname(fileURLToPath(import.meta.url));
  const stateFile = path.resolve(teardownDir, '../test-results/e2e-database.json');
  if (!fs.existsSync(stateFile)) return;

  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8')) as {
    databaseName: string;
  };
  if (!state.databaseName.startsWith('project_test_')) {
    throw new Error('Tên database E2E không có tiền tố an toàn.');
  }

  execFileSync(
    path.resolve(teardownDir, '../../backend/.venv/Scripts/python.exe'),
    [
      path.resolve(teardownDir, '../../backend/scripts/drop_test_database.py'),
      '--name',
      state.databaseName,
    ],
    {
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
      },
      stdio: 'inherit',
    },
  );
  fs.rmSync(stateFile, { force: true });
}
