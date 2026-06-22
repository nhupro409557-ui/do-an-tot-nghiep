-- Bổ sung metadata kệ hàng cho database đã khởi tạo trước khi gộp migration.

ALTER TABLE inventory_locations
    ADD COLUMN IF NOT EXISTS zone VARCHAR(160),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) NOT NULL DEFAULT 'STORAGE',
    ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS allow_mixed_sku BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE inventory_locations
    DROP CONSTRAINT IF EXISTS inventory_locations_purpose_check;

ALTER TABLE inventory_locations
    ADD CONSTRAINT inventory_locations_purpose_check
    CHECK (purpose IN ('STORAGE', 'WARRANTY', 'QC', 'DAMAGED', 'RETURN', 'VIRTUAL'));

UPDATE inventory_locations
SET name = 'Kho chính',
    zone = COALESCE(zone, 'Kho chính'),
    purpose = 'VIRTUAL',
    sort_order = 0,
    allow_mixed_sku = TRUE
WHERE code = 'MAIN';

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
VALUES
    ('A-01-01', 'Dãy A - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, ưu tiên gần khu lấy hàng', 'STORAGE', 10101, FALSE),
    ('A-01-02', 'Dãy A - Kệ 01 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10102, FALSE),
    ('B-01-01', 'Dãy B - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy B', 'Vị trí lưu hàng bán được ở dãy B', 'STORAGE', 20101, TRUE),
    ('QC-01', 'Khu kiểm tra chất lượng 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Khu QC', 'Vị trí cách ly hàng chờ kiểm tra hoặc chưa đạt QC', 'QC', 90001, TRUE),
    ('BH-01', 'Khu bảo hành 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Khu bảo hành', 'Vị trí lưu hàng gửi/nhận bảo hành', 'WARRANTY', 91001, TRUE),
    ('ERR-01', 'Khu hàng lỗi 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Khu hàng lỗi', 'Vị trí lưu hàng hư hỏng, phế phẩm hoặc chờ xử lý', 'DAMAGED', 92001, TRUE),
    ('RT-01', 'Khu hàng trả 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Khu hàng trả', 'Vị trí lưu hàng khách trả trước khi phân loại', 'RETURN', 93001, TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();

UPDATE inventory_locations
SET purpose = CASE
        WHEN code LIKE 'BH-%' THEN 'WARRANTY'
        WHEN code LIKE 'QC-%' THEN 'QC'
        WHEN code LIKE 'ERR-%' THEN 'DAMAGED'
        WHEN code LIKE 'RT-%' THEN 'RETURN'
        WHEN code = 'MAIN' THEN 'VIRTUAL'
        ELSE COALESCE(NULLIF(purpose, ''), 'STORAGE')
    END,
    sort_order = CASE
        WHEN sort_order <> 0 THEN sort_order
        WHEN code ~ '^[A-Z]-[0-9]{2}-[0-9]{2}$'
            THEN ((ascii(substr(code, 1, 1)) - ascii('A') + 1) * 10000)
                + (substr(code, 3, 2)::int * 100)
                + substr(code, 6, 2)::int
        ELSE 99999
    END;

CREATE INDEX IF NOT EXISTS idx_inventory_locations_purpose_status_sort
    ON inventory_locations(purpose, status, sort_order, code);
