WITH unit_map(slug, field_key, unit) AS (
    VALUES
        ('smartphones', 'screen_size', 'inch'),
        ('smartphones', 'refresh_rate', 'Hz'),
        ('smartphones', 'brightness', 'nits'),
        ('smartphones', 'ram', 'GB'),
        ('smartphones', 'storage', 'GB/TB'),
        ('smartphones', 'rear_camera', 'MP'),
        ('smartphones', 'front_camera', 'MP'),
        ('smartphones', 'battery', 'mAh'),
        ('smartphones', 'charging', 'W'),
        ('smartphones', 'dimensions', 'mm'),
        ('smartphones', 'weight', 'g'),
        ('laptops', 'screen_size', 'inch'),
        ('laptops', 'refresh_rate', 'Hz'),
        ('laptops', 'ram', 'GB'),
        ('laptops', 'storage', 'GB/TB'),
        ('laptops', 'battery', 'Wh'),
        ('laptops', 'dimensions', 'mm'),
        ('laptops', 'weight', 'kg'),
        ('tablets', 'screen_size', 'inch'),
        ('tablets', 'refresh_rate', 'Hz'),
        ('tablets', 'ram', 'GB'),
        ('tablets', 'storage', 'GB/TB'),
        ('tablets', 'rear_camera', 'MP'),
        ('tablets', 'front_camera', 'MP'),
        ('tablets', 'battery', 'mAh'),
        ('tablets', 'charging', 'W'),
        ('tablets', 'dimensions', 'mm'),
        ('tablets', 'weight', 'g'),
        ('wearables', 'screen_size', 'inch'),
        ('wearables', 'storage', 'GB'),
        ('wearables', 'case_size', 'mm'),
        ('wearables', 'weight', 'g'),
        ('cameras', 'resolution', 'MP'),
        ('cameras', 'zoom', 'x'),
        ('cameras', 'field_of_view', 'độ'),
        ('cameras', 'storage', 'GB/TB'),
        ('cameras', 'battery', 'mAh'),
        ('cameras', 'dimensions', 'mm'),
        ('cameras', 'weight', 'g'),
        ('accessories', 'power', 'W'),
        ('accessories', 'capacity', 'mAh'),
        ('accessories', 'battery', 'mAh'),
        ('accessories', 'dimensions', 'mm'),
        ('accessories', 'weight', 'g')
),
updated_spec_fields AS (
    SELECT
        c.id,
        jsonb_agg(
            CASE
                WHEN unit_map.unit IS NULL THEN field.value
                ELSE field.value || jsonb_build_object('unit', unit_map.unit)
            END
            ORDER BY field.ordinality
        ) AS spec_fields
    FROM categories c
    CROSS JOIN LATERAL jsonb_array_elements(c.spec_fields) WITH ORDINALITY AS field(value, ordinality)
    LEFT JOIN unit_map
        ON unit_map.slug = c.slug
        AND unit_map.field_key = field.value ->> 'key'
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
