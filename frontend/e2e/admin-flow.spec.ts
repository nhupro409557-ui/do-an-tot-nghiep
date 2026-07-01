import { expect, test } from '@playwright/test';
import crypto from 'node:crypto';

const adminEmail = 'e2e-admin@example.com';
const adminPassword = 'MatKhauAdminE2E123!';
const customerEmail = 'e2e-customer@example.com';
const seededProductName = 'Sản phẩm kiểm thử luồng dữ liệu E2E';

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

async function signInAdmin(page: import('@playwright/test').Page) {
  await page.goto('/admin/login');
  await page.locator('input[type="email"]').fill(adminEmail);
  await page.locator('input[type="password"]').fill(adminPassword);
  await page.locator('button[type="submit"]').click();

  await expect(page.locator('text=Secret MFA')).toBeVisible();
  const pageText = await page.locator('body').innerText();
  const secret = pageText.match(/[A-Z2-7]{16,}/)?.[0];
  expect(secret).toBeTruthy();

  await page.locator('input[inputmode="numeric"]').fill(totp(secret!));
  await Promise.all([
    page.waitForURL(/\/admin$/),
    page.locator('button[type="submit"]').click(),
  ]);
}

test('admin UI: đăng nhập MFA rồi đọc dashboard, khách hàng, sản phẩm và phương thức thanh toán', async ({ page }) => {
  await signInAdmin(page);

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.locator('body')).toContainText(/Dashboard/);

  await page.locator('aside button').nth(6).click();
  await expect(page.getByText(seededProductName, { exact: false }).first()).toBeVisible();

  await page.locator('aside button').nth(7).click();
  await expect(page.getByText(customerEmail, { exact: false }).first()).toBeVisible();

  await page.locator('aside button').nth(8).click();
  await expect(page.locator('body')).toContainText(/COD|MOMO|ZALOPAY|SEPAY/);
});
