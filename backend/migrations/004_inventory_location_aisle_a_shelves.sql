-- Bổ sung đủ 10 vị trí kệ cho dãy A.

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
VALUES
    ('A-01-03', 'Dãy A - Kệ 01 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10103, FALSE),
    ('A-01-04', 'Dãy A - Kệ 01 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10104, FALSE),
    ('A-01-05', 'Dãy A - Kệ 01 - Ô 05', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10105, FALSE),
    ('A-01-06', 'Dãy A - Kệ 01 - Ô 06', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10106, FALSE),
    ('A-01-07', 'Dãy A - Kệ 01 - Ô 07', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10107, FALSE),
    ('A-01-08', 'Dãy A - Kệ 01 - Ô 08', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10108, FALSE),
    ('A-01-09', 'Dãy A - Kệ 01 - Ô 09', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10109, FALSE),
    ('A-01-10', 'Dãy A - Kệ 01 - Ô 10', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10110, FALSE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();
