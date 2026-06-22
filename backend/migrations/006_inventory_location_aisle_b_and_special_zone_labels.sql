-- Bổ sung dãy B theo mô hình 10 kệ x 4 ô và chuẩn hóa nhãn khu đặc biệt.

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
SELECT
    format('B-%s-%s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS code,
    format('Dãy B - Kệ %s - Ô %s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS name,
    'WAREHOUSE',
    'ACTIVE',
    FALSE,
    'Dãy B',
    format('Vị trí lưu hàng bán được, kệ B-%s', lpad(shelf_no::text, 2, '0')) AS description,
    'STORAGE',
    20000 + shelf_no * 100 + bin_no AS sort_order,
    FALSE
FROM generate_series(1, 10) AS shelf_no
CROSS JOIN generate_series(1, 4) AS bin_no
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    status = 'ACTIVE',
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();

UPDATE inventory_locations
SET name = CASE code
        WHEN 'QC-01' THEN 'QC - Ô 01'
        WHEN 'BH-01' THEN 'Bảo hành - Ô 01'
        WHEN 'ERR-01' THEN 'Hàng lỗi - Ô 01'
        WHEN 'RT-01' THEN 'Hàng trả - Ô 01'
        ELSE name
    END,
    zone = CASE code
        WHEN 'QC-01' THEN 'QC'
        WHEN 'BH-01' THEN 'Bảo hành'
        WHEN 'ERR-01' THEN 'Hàng lỗi'
        WHEN 'RT-01' THEN 'Hàng trả'
        ELSE zone
    END,
    updated_at = NOW()
WHERE code IN ('QC-01', 'BH-01', 'ERR-01', 'RT-01');
