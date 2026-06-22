-- Bổ sung kích thước riêng cho từng ô/kệ để tính sức chứa theo thể tích.

ALTER TABLE inventory_locations
    ADD COLUMN IF NOT EXISTS length_cm NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS width_cm NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS height_cm NUMERIC(10, 2);

UPDATE inventory_locations
SET length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    updated_at = NOW()
WHERE status = 'ACTIVE'
  AND purpose = 'STORAGE'
  AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$';
