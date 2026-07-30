-- Chuẩn hóa dữ liệu kiểm thử hàng cũ từng được ghi bằng encoding mặc định của Windows.
UPDATE products
SET name = 'Điện thoại smoke test hàng cũ',
    updated_at = NOW()
WHERE sku LIKE 'SMOKE-USED-%'
  AND name IN ('?i?n tho?i smoke test h?ng c?', 'Dien thoai smoke test hang cu');

UPDATE product_variants
SET color_name = 'Đen',
    updated_at = NOW()
WHERE sku LIKE 'SMOKE-USED-%'
  AND color_name IN ('?en', 'Den');
