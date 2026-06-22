-- Chuẩn hóa dãy A thành 10 kệ, mỗi kệ có 4 ô.

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
SELECT
    format('A-%s-%s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS code,
    format('Dãy A - Kệ %s - Ô %s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS name,
    'WAREHOUSE',
    'ACTIVE',
    FALSE,
    'Dãy A',
    format('Vị trí lưu hàng bán được, kệ A-%s', lpad(shelf_no::text, 2, '0')) AS description,
    'STORAGE',
    10000 + shelf_no * 100 + bin_no AS sort_order,
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

UPDATE inventory_locations loc
SET status = 'INACTIVE',
    description = COALESCE(NULLIF(loc.description, ''), 'Vị trí cũ không còn đúng quy ước dãy A 10 kệ x 4 ô'),
    updated_at = NOW()
WHERE loc.code IN ('A-01-05', 'A-01-06', 'A-01-07', 'A-01-08', 'A-01-09', 'A-01-10')
  AND NOT EXISTS (
      SELECT 1
      FROM inventory_levels levels
      WHERE levels.location_id = loc.id
        AND levels.on_hand_quantity > 0
  );
