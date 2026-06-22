-- Điều chỉnh hệ số sử dụng/xếp hàng theo mô hình sức chứa thực tế mới.

UPDATE inventory_locations
SET usable_ratio = CASE
        WHEN purpose = 'STORAGE' AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$' THEN 0.75
        ELSE 0.70
    END,
    updated_at = NOW()
WHERE purpose = 'STORAGE'
   OR code IN ('QC-01', 'BH-01', 'ERR-01', 'RT-01');

WITH ratios(code, packing_ratio) AS (
    VALUES
        ('smartphones', 0.85),
        ('phone-flagship', 0.85),
        ('phone-foldable', 0.85),
        ('phone-midrange', 0.85),
        ('dien-thoai-gaming', 0.85),
        ('phone-budget', 0.85),
        ('tablets', 0.80),
        ('tablet-pro', 0.80),
        ('tablet-study', 0.80),
        ('tablet-2in1', 0.80),
        ('tablet-mini', 0.80),
        ('laptops', 0.80),
        ('laptop-ultrabook', 0.80),
        ('laptop-gaming', 0.80),
        ('laptop-workstation', 0.80),
        ('laptop-office', 0.80),
        ('macbook', 0.80),
        ('accessories', 0.85),
        ('adapter-gan', 0.85),
        ('adapter-multiport', 0.85),
        ('adapter-wireless', 0.85),
        ('cable-usbc', 0.85),
        ('cable-lightning', 0.85),
        ('cable-thunderbolt', 0.85),
        ('wearables', 0.85),
        ('watch-fashion', 0.85),
        ('watch-sport', 0.85),
        ('smartband', 0.85),
        ('kids-watch', 0.85),
        ('audio-tws', 0.75),
        ('audio-overear', 0.75),
        ('audio-sport', 0.75),
        ('audio-gaming', 0.75),
        ('may-anh', 0.75),
        ('camera-mirrorless', 0.75),
        ('camera-dslr', 0.75),
        ('cameras', 0.75),
        ('action-camera', 0.75),
        ('security-camera', 0.75),
        ('dashcam', 0.75)
)
UPDATE categories c
SET inventory_policy = COALESCE(c.inventory_policy, '{}'::jsonb)
    || jsonb_build_object('packingRatio', ratios.packing_ratio),
    updated_at = NOW()
FROM ratios
WHERE c.code = ratios.code;
