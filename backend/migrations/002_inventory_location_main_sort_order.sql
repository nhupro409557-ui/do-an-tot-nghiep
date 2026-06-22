-- Đảm bảo kệ mặc định MAIN luôn đứng đầu danh sách kệ hàng.

UPDATE inventory_locations
SET sort_order = 0,
    zone = COALESCE(zone, 'Kho chính'),
    purpose = 'VIRTUAL',
    allow_mixed_sku = TRUE,
    updated_at = NOW()
WHERE code = 'MAIN';
