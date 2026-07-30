WITH storage_option_map(slug, options) AS (
    VALUES
        ('smartphones', '64 GB, 128 GB, 256 GB, 512 GB, 1 TB'),
        ('tablets', '64 GB, 128 GB, 256 GB, 512 GB, 1 TB, 2 TB')
),
updated_spec_fields AS (
    SELECT
        c.id,
        jsonb_agg(
            CASE
                WHEN storage_option_map.options IS NOT NULL
                    AND field.value ->> 'key' IN ('storage', 'rom')
                    THEN field.value || jsonb_build_object(
                        'unit', 'GB/TB',
                        'options', storage_option_map.options
                    )
                ELSE field.value
            END
            ORDER BY field.ordinality
        ) AS spec_fields
    FROM categories c
    CROSS JOIN LATERAL jsonb_array_elements(c.spec_fields) WITH ORDINALITY AS field(value, ordinality)
    LEFT JOIN storage_option_map
        ON storage_option_map.slug = c.slug
    WHERE c.parent_id IS NULL
        AND c.slug IN ('smartphones', 'tablets')
    GROUP BY c.id
)
UPDATE categories c
SET
    spec_fields = updated_spec_fields.spec_fields,
    updated_at = NOW()
FROM updated_spec_fields
WHERE c.id = updated_spec_fields.id
    AND c.spec_fields IS DISTINCT FROM updated_spec_fields.spec_fields;
