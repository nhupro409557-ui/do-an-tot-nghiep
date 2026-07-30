-- Chuẩn hóa phần dữ liệu kiểm thử hàng cũ còn bị ghi bằng encoding mặc định của Windows.
UPDATE used_device_intake_requests
SET seller_name = 'Khách smoke test',
    updated_at = NOW()
WHERE request_code = 'CU-20260703-0001'
  AND seller_name = 'Kh?ch smoke test';

UPDATE used_device_listings
SET slug = regexp_replace(
        slug,
        '^i-n-tho-i-smoke-test-h-ng-c-h-ng-b-',
        'dien-thoai-smoke-test-hang-cu-hang-b-'
    ),
    updated_at = NOW()
WHERE slug LIKE 'i-n-tho-i-smoke-test-h-ng-c-h-ng-b-%';
