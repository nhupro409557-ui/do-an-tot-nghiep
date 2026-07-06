-- Gộp khái niệm khu vào dãy theo tiền tố mã kệ.
-- Các dãy nghiệp vụ dùng cùng cấu trúc: <DÃY>-<KỆ>-<Ô>.

UPDATE inventory_locations
SET name = 'Kho',
    zone = 'Kho',
    purpose = 'VIRTUAL',
    sort_order = 0,
    length_cm = NULL,
    width_cm = NULL,
    height_cm = NULL,
    updated_at = NOW()
WHERE code = 'MAIN';

UPDATE inventory_locations
SET code = 'CL-01-01',
    name = 'Dãy cách ly - Kệ 01 - Ô 01',
    zone = 'Dãy cách ly',
    purpose = 'QC',
    sort_order = 850101,
    description = 'Kệ cách ly hàng chờ kiểm tra hoặc chưa đạt QC.',
    length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    usable_ratio = COALESCE(usable_ratio, 0.75),
    status = 'ACTIVE',
    updated_at = NOW()
WHERE code = 'QC-01'
  AND NOT EXISTS (SELECT 1 FROM inventory_locations WHERE code = 'CL-01-01');

UPDATE inventory_locations
SET code = 'BH-01-01',
    name = 'Dãy bảo hành - Kệ 01 - Ô 01',
    zone = 'Dãy bảo hành',
    purpose = 'WARRANTY',
    sort_order = 910101,
    description = 'Kệ lưu hàng gửi hoặc nhận bảo hành.',
    length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    usable_ratio = COALESCE(usable_ratio, 0.75),
    status = 'ACTIVE',
    updated_at = NOW()
WHERE code = 'BH-01'
  AND NOT EXISTS (SELECT 1 FROM inventory_locations WHERE code = 'BH-01-01');

UPDATE inventory_locations
SET code = 'ERR-01-01',
    name = 'Dãy hàng lỗi - Kệ 01 - Ô 01',
    zone = 'Dãy hàng lỗi',
    purpose = 'DAMAGED',
    sort_order = 920101,
    description = 'Kệ lưu hàng lỗi chờ xử lý.',
    length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    usable_ratio = COALESCE(usable_ratio, 0.75),
    status = 'ACTIVE',
    updated_at = NOW()
WHERE code = 'ERR-01'
  AND NOT EXISTS (SELECT 1 FROM inventory_locations WHERE code = 'ERR-01-01');

UPDATE inventory_locations
SET code = 'RT-01-01',
    name = 'Dãy hàng trả - Kệ 01 - Ô 01',
    zone = 'Dãy hàng trả',
    purpose = 'RETURN',
    sort_order = 930101,
    description = 'Kệ lưu hàng khách trả chờ kiểm tra.',
    length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    usable_ratio = COALESCE(usable_ratio, 0.75),
    status = 'ACTIVE',
    updated_at = NOW()
WHERE code = 'RT-01'
  AND NOT EXISTS (SELECT 1 FROM inventory_locations WHERE code = 'RT-01-01');

INSERT INTO inventory_locations (
    code, name, location_type, status, is_default, zone,
    description, purpose, sort_order, allow_mixed_sku,
    length_cm, width_cm, height_cm, usable_ratio
)
VALUES
    ('CL-01-01', 'Dãy cách ly - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy cách ly',
     'Kệ cách ly hàng chờ kiểm tra hoặc chưa đạt QC.', 'QC', 850101, TRUE, 100, 60, 40, 0.75),
    ('BH-01-01', 'Dãy bảo hành - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy bảo hành',
     'Kệ lưu hàng gửi hoặc nhận bảo hành.', 'WARRANTY', 910101, TRUE, 100, 60, 40, 0.75),
    ('ERR-01-01', 'Dãy hàng lỗi - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy hàng lỗi',
     'Kệ lưu hàng lỗi chờ xử lý.', 'DAMAGED', 920101, TRUE, 100, 60, 40, 0.75),
    ('RT-01-01', 'Dãy hàng trả - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy hàng trả',
     'Kệ lưu hàng khách trả chờ kiểm tra.', 'RETURN', 930101, TRUE, 100, 60, 40, 0.75)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    length_cm = COALESCE(inventory_locations.length_cm, EXCLUDED.length_cm),
    width_cm = COALESCE(inventory_locations.width_cm, EXCLUDED.width_cm),
    height_cm = COALESCE(inventory_locations.height_cm, EXCLUDED.height_cm),
    usable_ratio = COALESCE(inventory_locations.usable_ratio, EXCLUDED.usable_ratio),
    updated_at = NOW();
