-- Bổ sung kích thước đóng gói mặc định theo danh mục để ước tính sức chứa kệ.

WITH defaults(code, length_cm, width_cm, height_cm) AS (
    VALUES
        ('smartphones', 18, 10, 6),
        ('phone-flagship', 18, 10, 6),
        ('phone-foldable', 19, 12, 7),
        ('phone-midrange', 18, 10, 6),
        ('dien-thoai-gaming', 20, 12, 7),
        ('phone-budget', 18, 10, 6),
        ('tablets', 28, 20, 7),
        ('tablet-pro', 31, 23, 7),
        ('tablet-study', 28, 20, 7),
        ('tablet-2in1', 32, 23, 8),
        ('tablet-mini', 24, 18, 6),
        ('laptops', 40, 30, 8),
        ('laptop-ultrabook', 38, 28, 7),
        ('laptop-gaming', 45, 35, 10),
        ('laptop-workstation', 46, 36, 11),
        ('laptop-office', 40, 30, 8),
        ('macbook', 39, 29, 7),
        ('accessories', 12, 8, 5),
        ('audio-tws', 10, 8, 4),
        ('audio-overear', 24, 20, 12),
        ('audio-sport', 12, 8, 5),
        ('audio-gaming', 26, 22, 12),
        ('adapter-gan', 12, 8, 5),
        ('adapter-multiport', 14, 10, 5),
        ('adapter-wireless', 12, 10, 4),
        ('cable-usbc', 10, 8, 3),
        ('cable-lightning', 10, 8, 3),
        ('cable-thunderbolt', 12, 9, 3),
        ('wearables', 12, 10, 8),
        ('watch-fashion', 12, 10, 8),
        ('watch-sport', 13, 11, 9),
        ('smartband', 11, 8, 5),
        ('kids-watch', 12, 10, 7),
        ('may-anh', 24, 18, 14),
        ('camera-mirrorless', 26, 20, 16),
        ('camera-dslr', 28, 22, 18),
        ('cameras', 16, 12, 10),
        ('action-camera', 14, 10, 8),
        ('security-camera', 18, 14, 12),
        ('dashcam', 16, 12, 8)
)
UPDATE categories c
SET inventory_policy = COALESCE(c.inventory_policy, '{}'::jsonb)
    || jsonb_build_object(
        'inheritStorageDimensions', c.parent_id IS NOT NULL,
        'packageLengthCm', defaults.length_cm,
        'packageWidthCm', defaults.width_cm,
        'packageHeightCm', defaults.height_cm
    ),
    updated_at = NOW()
FROM defaults
WHERE c.code = defaults.code;
