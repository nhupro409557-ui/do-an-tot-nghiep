import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';

const payableAdminEmail = 'e2e-payable-admin@example.com';
const payableAdminPassword = 'MatKhauCongNoE2E123!';
const payableReference = 'NK-E2E-CONGNO-001';

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

async function signInPayableAdmin(page: Page) {
  await page.goto('/admin/login');
  await page.locator('input[type="email"]').fill(payableAdminEmail);
  await page.locator('input[type="password"]').fill(payableAdminPassword);
  await page.locator('button[type="submit"]').click();

  await expect(page.getByRole('textbox', { name: 'Mã OTP' })).toBeVisible();
  let secret = '';
  if (await page.getByText('Secret MFA').isVisible().catch(() => false)) {
    const pageText = await page.locator('body').innerText();
    secret = pageText.match(/[A-Z2-7]{16,}/)?.[0] || '';
  }
  expect(secret).toBeTruthy();

  await page.locator('input[inputmode="numeric"]').fill(totp(secret));
  await Promise.all([
    page.waitForURL(/\/admin$/),
    page.locator('button[type="submit"]').click(),
  ]);
}

test('admin account payables: xem công nợ và ghi nhận thanh toán từ UI', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await signInPayableAdmin(page);

  await page.getByRole('button', { name: 'Công nợ NCC' }).click();
  await expect(page.getByRole('heading', { name: 'Công nợ nhà cung cấp' }).first()).toBeVisible();
  await expect(page.getByText(payableReference)).toBeVisible();
  await expect(page.getByText('2.000.000 ₫').first()).toBeVisible();

  await page.getByRole('button', { name: 'Chi tiết' }).click();
  await expect(page.getByRole('heading', { name: 'Chi tiết công nợ' })).toBeVisible();
  await expect(page.getByText('UNC-E2E-001')).toBeVisible();

  const referenceNo = `E2E-PAY-${Date.now()}`;
  const paymentResponse = page.waitForResponse((response) =>
    response.url().includes('/api/admin/account-payables/')
    && response.url().endsWith('/payments')
    && response.request().method() === 'POST',
  );
  await page.getByRole('spinbutton', { name: 'Số tiền' }).fill('300000');
  await page.getByRole('textbox', { name: 'Mã tham chiếu' }).fill(referenceNo);
  await page.getByRole('textbox', { name: 'Ghi chú' }).fill('Kiểm thử ghi nhận thanh toán từ Playwright');
  await page.getByRole('button', { name: 'Lưu thanh toán' }).click();

  expect((await paymentResponse).status()).toBe(200);
  await expect(page.getByText('1.700.000 ₫').first()).toBeVisible();
  await expect(page.getByText('800.000 ₫').first()).toBeVisible();
  await expect(page.getByText(referenceNo)).not.toBeVisible();

  await page.getByRole('button', { name: 'Chi tiết' }).click();
  await expect(page.getByText(referenceNo)).toBeVisible();
  expect(consoleErrors).toEqual([]);
});
