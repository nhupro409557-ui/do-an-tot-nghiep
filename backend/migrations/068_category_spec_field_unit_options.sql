WITH option_map(slug, field_key, options) AS (
    VALUES
        ('smartphones', 'screen_size', '6.1, 6.3, 6.5, 6.7, 6.8, 6.9'),
        ('smartphones', 'refresh_rate', '60, 90, 120, 144'),
        ('smartphones', 'brightness', '1000, 1600, 2000, 2600, 3000'),
        ('smartphones', 'ram', '4, 6, 8, 12, 16'),
        ('smartphones', 'storage', '64 GB, 128 GB, 256 GB, 512 GB, 1 TB'),
        ('smartphones', 'rear_camera', '12, 32, 48, 50, 64, 108, 200'),
        ('smartphones', 'front_camera', '8, 12, 16, 32, 50'),
        ('smartphones', 'battery', '4000, 4500, 5000, 5500, 6000'),
        ('smartphones', 'charging', '20, 25, 33, 45, 67, 80, 90, 120'),
        ('smartphones', 'dimensions', '150 x 72 x 8, 160 x 75 x 8, 163 x 78 x 9'),
        ('smartphones', 'weight', '150, 180, 200, 220, 240'),
        ('laptops', 'screen_size', '13.3, 14, 15.6, 16, 17.3'),
        ('laptops', 'refresh_rate', '60, 90, 120, 144, 165, 240'),
        ('laptops', 'ram', '8, 16, 24, 32, 64'),
        ('laptops', 'storage', '256GB SSD, 512GB SSD, 1TB SSD, 2TB SSD'),
        ('laptops', 'battery', '40, 50, 60, 70, 80, 100'),
        ('laptops', 'dimensions', '304 x 215 x 16, 356 x 250 x 20'),
        ('laptops', 'weight', '1.2, 1.4, 1.6, 2.0, 2.5'),
        ('tablets', 'screen_size', '8.7, 10.9, 11, 12.4, 12.9, 13'),
        ('tablets', 'refresh_rate', '60, 90, 120, 144'),
        ('tablets', 'ram', '4, 6, 8, 12, 16'),
        ('tablets', 'storage', '64 GB, 128 GB, 256 GB, 512 GB, 1 TB, 2 TB'),
        ('tablets', 'rear_camera', '8, 12, 13, 48, 50'),
        ('tablets', 'front_camera', '8, 12, 16, 32'),
        ('tablets', 'battery', '5000, 7040, 8000, 10000, 11200'),
        ('tablets', 'charging', '18, 20, 33, 45, 67'),
        ('tablets', 'dimensions', '248 x 179 x 7, 280 x 215 x 6'),
        ('tablets', 'weight', '450, 500, 600, 700'),
        ('wearables', 'screen_size', '1.2, 1.3, 1.4, 1.5, 1.9'),
        ('wearables', 'storage', '8, 16, 32, 64'),
        ('wearables', 'case_size', '40, 41, 43, 44, 45, 49'),
        ('wearables', 'weight', '30, 40, 50, 60, 70'),
        ('cameras', 'resolution', '2, 3, 4, 12, 20, 24, 33, 45'),
        ('cameras', 'zoom', '2, 3, 5, 10, 20, 30'),
        ('cameras', 'field_of_view', '90, 120, 130, 155, 170'),
        ('cameras', 'storage', 'microSD 32GB, microSD 64GB, microSD 128GB, SD 64GB, SD 128GB'),
        ('cameras', 'battery', '1000, 1720, 1800, 2200, 3000'),
        ('cameras', 'dimensions', '60 x 40 x 30, 100 x 70 x 60, 130 x 100 x 80'),
        ('cameras', 'weight', '150, 250, 500, 700'),
        ('accessories', 'power', '15, 20, 25, 30, 45, 65, 100, 140, 200, 240'),
        ('accessories', 'capacity', '5000, 10000, 20000, 27650'),
        ('accessories', 'battery', '500, 1000, 5000, 10000, 20000'),
        ('accessories', 'dimensions', 'Dài 1m, Dài 1.2m, Dài 1.8m, Dài 2m, Nhỏ gọn'),
        ('accessories', 'weight', '50, 100, 200, 300, 500')
),
updated_spec_fields AS (
    SELECT
        c.id,
        jsonb_agg(
            CASE
                WHEN option_map.options IS NULL THEN field.value
                WHEN NULLIF(BTRIM(field.value ->> 'options'), '') IS NOT NULL THEN field.value
                ELSE field.value || jsonb_build_object('options', option_map.options)
            END
            ORDER BY field.ordinality
        ) AS spec_fields
    FROM categories c
    CROSS JOIN LATERAL jsonb_array_elements(c.spec_fields) WITH ORDINALITY AS field(value, ordinality)
    LEFT JOIN option_map
        ON option_map.slug = c.slug
        AND option_map.field_key = field.value ->> 'key'
    WHERE c.parent_id IS NULL
        AND c.slug IN ('smartphones', 'laptops', 'tablets', 'wearables', 'cameras', 'accessories')
    GROUP BY c.id
)
UPDATE categories c
SET
    spec_fields = updated_spec_fields.spec_fields,
    updated_at = NOW()
FROM updated_spec_fields
WHERE c.id = updated_spec_fields.id
    AND c.spec_fields IS DISTINCT FROM updated_spec_fields.spec_fields;
