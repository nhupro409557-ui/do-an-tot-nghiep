import { expect, test } from '@playwright/test';

const customerEmail = 'e2e-customer@example.com';
const customerPassword = 'MatKhauE2E123!';
const seededProductName = 'Sản phẩm kiểm thử luồng dữ liệu E2E';

test('database → backend → API → danh sách sản phẩm frontend', async ({ page }) => {
  await page.goto('/products');

  await expect(page.getByText(seededProductName, { exact: false }).first()).toBeVisible();
});

test('frontend → API → backend → database khi cập nhật hồ sơ', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email đăng nhập').fill(customerEmail);
  await page.getByLabel('Mật khẩu đăng nhập').fill(customerPassword);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();

  await expect(page).toHaveURL('http://127.0.0.1:3001/');
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByRole('button', { name: /Cài đặt tài khoản/ }).click();
  await page.getByRole('button', { name: /Chỉnh sửa/ }).click();

  const newDisplayName = `Khách hàng E2E ${Date.now()}`;
  await page.getByLabel('Họ tên').fill(newDisplayName);
  const profileResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/auth/me/profile') &&
      response.request().method() === 'PATCH',
  );
  await page.getByRole('button', { name: 'Lưu thông tin tài khoản' }).click();
  expect((await profileResponse).status()).toBe(200);

  await page.reload();
  await page.getByRole('button', { name: /Cài đặt tài khoản/ }).click();
  await expect(page.getByLabel('Họ tên')).toHaveValue(newDisplayName);
});

test('mobile: trang tích điểm tải huy hiệu 3D mà không tràn giao diện', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/login');
  await page.getByLabel('Email đăng nhập').fill(customerEmail);
  await page.getByLabel('Mật khẩu đăng nhập').fill(customerPassword);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL('http://127.0.0.1:3001/');
  await page.waitForLoadState('networkidle');

  consoleErrors.length = 0;
  await page.goto('/loyalty');
  await expect(page.getByRole('heading', { name: 'Smember - Khách hàng thân thiết' })).toBeVisible();
  const badgeCanvas = page.locator('canvas').first();
  await expect(badgeCanvas).toBeVisible();
  const firstFrame = await badgeCanvas.evaluate((canvas) => (canvas as HTMLCanvasElement).toDataURL());
  await page.waitForTimeout(250);
  const nextFrame = await badgeCanvas.evaluate((canvas) => (canvas as HTMLCanvasElement).toDataURL());

  expect(nextFrame).not.toBe(firstFrame);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    ),
  ).toBe(false);
  expect(consoleErrors).toEqual([]);
});
