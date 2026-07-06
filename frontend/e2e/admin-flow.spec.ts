import { expect, test } from '@playwright/test';
import crypto from 'node:crypto';
import * as XLSX from 'xlsx';

const adminEmail = 'e2e-admin@example.com';
const adminPassword = 'MatKhauAdminE2E123!';
const customerEmail = 'e2e-customer@example.com';
const seededProductName = 'Sản phẩm kiểm thử luồng dữ liệu E2E';
const inventoryReceiptReference = 'NK-E2E-EXCEL-001';
const inventoryImeis = ['351756051523999', '490154203237518'];
const inventorySecondaryImeis = ['352099001761481', '356938035643809'];
const inventorySerialNumbers = ['SN-E2E-001', 'SN-E2E-002'];

function createWorkbookBuffer(values: string[], sheetName: string): Buffer {
  const worksheet = XLSX.utils.aoa_to_sheet(values.map((value) => [value]));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
  return Buffer.from(XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' }));
}

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

test('admin UI: đăng nhập MFA, đọc dữ liệu và import IMEI từ Excel', async ({ page }) => {
  await signInAdmin(page);

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole('heading', { name: 'Tổng quan điều hành' }).first()).toBeVisible();

  await page.getByRole('button', { name: 'Sản phẩm' }).click();
  await expect(page.getByText(seededProductName, { exact: false }).first()).toBeVisible();

  await page.getByRole('button', { name: 'Khách hàng' }).click();
  await expect(page.getByText(customerEmail, { exact: false }).first()).toBeVisible();

  await page.getByRole('button', { name: 'PT Thanh toán' }).click();
  await expect(page.locator('body')).toContainText(/COD|MOMO|ZALOPAY|SEPAY/);

  const browserXlsxRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().toLowerCase().includes('/xlsx')) {
      browserXlsxRequests.push(request.url());
    }
  });

  await page.getByRole('button', { name: 'Nhập kho', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Quản lý nhập kho' })).toBeVisible();
  const receiptRow = page.getByRole('row').filter({ hasText: inventoryReceiptReference });
  await expect(receiptRow).toBeVisible();
  expect(browserXlsxRequests).toEqual([]);

  await receiptRow.getByRole('button', { name: 'Nhập mã' }).click();
  await expect(page.getByRole('heading', { name: 'Bổ sung IMEI/serial number' })).toBeVisible();

  const imeiFileInput = page
    .locator('label')
    .filter({ hasText: 'Import IMEI1' })
    .locator('input[type="file"]');
  await imeiFileInput.setInputFiles({
    name: 'imei-rong.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.alloc(0),
  });
  const importError = page.getByText(
    'Không thể đọc danh sách IMEI từ file. Hãy chọn file Excel, CSV hoặc TXT có ít nhất một mã.',
  );
  await expect(importError).toBeVisible();

  await imeiFileInput.setInputFiles({
    name: 'imei-e2e.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: createWorkbookBuffer(inventoryImeis, 'IMEI1'),
  });

  await expect.poll(() => browserXlsxRequests.length).toBeGreaterThan(0);
  await expect(importError).not.toBeVisible();
  await expect(page.getByPlaceholder('Dán danh sách IMEI1, mỗi máy một dòng')).toHaveValue(
    inventoryImeis.join('\n'),
  );

  const imei2FileInput = page
    .locator('label')
    .filter({ hasText: 'Import IMEI2 tùy chọn' })
    .locator('input[type="file"]');
  await imei2FileInput.setInputFiles({
    name: 'imei2-e2e.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: createWorkbookBuffer(inventorySecondaryImeis, 'IMEI2'),
  });
  await expect(page.getByPlaceholder('Dán danh sách IMEI2 nếu có, cùng thứ tự với IMEI1')).toHaveValue(
    inventorySecondaryImeis.join('\n'),
  );

  const serialFileInput = page
    .locator('label')
    .filter({ hasText: 'Import serial' })
    .locator('input[type="file"]');
  await serialFileInput.setInputFiles({
    name: 'serial-e2e.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: createWorkbookBuffer(inventorySerialNumbers, 'Serial'),
  });
  await expect(page.getByPlaceholder('Dán danh sách serial number')).toHaveValue(
    inventorySerialNumbers.join('\n'),
  );

  const submitResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/admin/inventory/receipts/${inventoryReceiptReference}/imeis`)
      && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Xác nhận danh sách mã định danh' }).click();
  expect((await submitResponse).status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Bổ sung IMEI/serial number' })).not.toBeVisible();
  await expect(receiptRow).toContainText('Chờ duyệt');

  await receiptRow.getByTitle('Xem phiếu').click();
  await expect(page.getByRole('heading', { name: 'Xem phiếu nhập kho' })).toBeVisible();
  await page.getByRole('button', { name: 'Danh sách IMEI / Serial' }).click();
  for (const identifier of [...inventoryImeis, ...inventorySecondaryImeis, ...inventorySerialNumbers]) {
    await expect(page.getByText(identifier, { exact: true })).toBeVisible();
  }
});
