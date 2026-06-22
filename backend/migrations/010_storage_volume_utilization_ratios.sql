-- Bổ sung hệ số hao hụt để tính dung lượng kệ theo thể tích thực dùng.

ALTER TABLE inventory_locations
    ADD COLUMN IF NOT EXISTS usable_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0.75;

ALTER TABLE inventory_locations
    DROP CONSTRAINT IF EXISTS inventory_locations_usable_ratio_check;

ALTER TABLE inventory_locations
    ADD CONSTRAINT inventory_locations_usable_ratio_check
    CHECK (usable_ratio > 0 AND usable_ratio <= 1);

UPDATE inventory_locations
SET usable_ratio = CASE
        WHEN purpose = 'STORAGE' AND allow_mixed_sku THEN 0.65
        WHEN purpose = 'STORAGE' THEN 0.75
        ELSE 0.70
    END,
    updated_at = NOW()
WHERE usable_ratio IS NULL OR usable_ratio = 0.75;

UPDATE categories
SET inventory_policy = COALESCE(inventory_policy, '{}'::jsonb)
    || jsonb_build_object(
        'packingRatio',
        CASE
            WHEN code IN ('accessories', 'audio-overear', 'audio-gaming', 'may-anh', 'camera-mirrorless', 'camera-dslr', 'cameras', 'security-camera') THEN 0.60
            WHEN code IN ('audio-tws', 'audio-sport', 'adapter-gan', 'adapter-multiport', 'adapter-wireless', 'cable-usbc', 'cable-lightning', 'cable-thunderbolt', 'wearables', 'watch-fashion', 'watch-sport', 'smartband', 'kids-watch') THEN 0.65
            WHEN code IN ('laptops', 'laptop-ultrabook', 'laptop-gaming', 'laptop-workstation', 'laptop-office', 'macbook') THEN 0.75
            WHEN code IN ('tablets', 'tablet-pro', 'tablet-study', 'tablet-2in1', 'tablet-mini') THEN 0.80
            WHEN code IN ('smartphones', 'phone-flagship', 'phone-foldable', 'phone-midrange', 'dien-thoai-gaming', 'phone-budget') THEN 0.85
            ELSE 0.70
        END
    ),
    updated_at = NOW()
WHERE NOT (COALESCE(inventory_policy, '{}'::jsonb) ? 'packingRatio');
