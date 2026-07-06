import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';

const superAdminEmail = 'e2e-super-admin@example.com';
const superAdminPassword = 'MatKhauSuperAdminE2E123!';

function base32ToBuffer(secret: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const char of secret.replace(/=+$/g, '').toUpperCase()) {
    const value = alphabet.indexOf(char);
    if (value < 0) continue;
    bits += value.toString(2).padStart(5, '0');
  }
  const bytes = bits.match(/.{1,8}/g)
    ?.filter((chunk) => chunk.length === 8)
    .map((chunk) => Number.parseInt(chunk, 2)) || [];
  return Buffer.from(bytes);
}

function totp(secret: string, now = Date.now()): string {
  const counter = Math.floor(now / 1000 / 30);
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac('sha1', base32ToBuffer(secret)).update(message).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const code = ((digest[offset] & 0x7f) << 24)
    | ((digest[offset + 1] & 0xff) << 16)
    | ((digest[offset + 2] & 0xff) << 8)
    | (digest[offset + 3] & 0xff);
  return String(code % 1_000_000).padStart(6, '0');
}

async function signInSuperAdmin(page: Page) {
  await page.goto('/admin/login');
  await page.locator('input[type="email"]').fill(superAdminEmail);
  await page.locator('input[type="password"]').fill(superAdminPassword);
  await page.locator('button[type="submit"]').click();

  await expect(page.getByRole('textbox', { name: 'Mã OTP' })).toBeVisible();
  const pageText = await page.locator('body').innerText();
  const secret = pageText.match(/[A-Z2-7]{16,}/)?.[0];
  expect(secret).toBeTruthy();

  await page.locator('input[inputmode="numeric"]').fill(totp(secret!));
  await Promise.all([
    page.waitForURL(/\/admin$/),
    page.locator('button[type="submit"]').click(),
  ]);
}

test('admin AI catalog: Super Admin xem trạng thái index và lịch sử refresh', async ({ page }) => {
  await signInSuperAdmin(page);

  const statusResponse = page.waitForResponse((response) =>
    response.url().includes('/api/admin/ai-catalog-index/status')
    && response.request().method() === 'GET',
  );
  const jobsResponse = page.waitForResponse((response) =>
    response.url().includes('/api/admin/ai-catalog-index/jobs')
    && response.request().method() === 'GET',
  );

  await page.getByRole('button', { name: 'AI catalog', exact: true }).click();
  expect((await statusResponse).status()).toBe(200);
  expect((await jobsResponse).status()).toBe(200);

  await expect(page.getByRole('heading', { name: 'AI catalog index' }).first()).toBeVisible();
  await expect(page.getByText('Markdown', { exact: true })).toBeVisible();
  await expect(page.getByText('Embedding JSON', { exact: true })).toBeVisible();
  await expect(page.getByText('PostgreSQL', { exact: true })).toBeVisible();
  await expect(page.getByText('pgvector', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Chạy refresh' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Lịch sử refresh' })).toBeVisible();
});
