-- Bổ sung dãy C theo mô hình 10 kệ x 4 ô và chuyển nguyên dòng SKU
-- khỏi các ô lưu hàng đang vượt dung lượng sang các ô mới.

INSERT INTO inventory_locations (
    code,
    name,
    location_type,
    status,
    is_default,
    zone,
    description,
    purpose,
    sort_order,
    allow_mixed_sku,
    length_cm,
    width_cm,
    height_cm,
    usable_ratio
)
SELECT
    format('C-%s-%s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')),
    format('Dãy C - Kệ %s - Ô %s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')),
    'WAREHOUSE',
    'ACTIVE',
    FALSE,
    'Dãy C',
    format('Vị trí lưu hàng bán được, kệ C-%s', lpad(shelf_no::text, 2, '0')),
    'STORAGE',
    30000 + shelf_no * 100 + bin_no,
    TRUE,
    100,
    60,
    40,
    0.75
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
    length_cm = EXCLUDED.length_cm,
    width_cm = EXCLUDED.width_cm,
    height_cm = EXCLUDED.height_cm,
    usable_ratio = EXCLUDED.usable_ratio,
    updated_at = NOW();

CREATE TEMP TABLE aisle_c_transfer_plan AS
WITH inventory_volume AS (
    SELECT
        il.id AS inventory_level_id,
        il.product_id,
        il.variant_id,
        il.location_id AS source_location_id,
        loc.code AS source_code,
        il.on_hand_quantity,
        (
            il.on_hand_quantity
            * COALESCE(
                NULLIF(
                    CASE
                        WHEN child.id IS NOT NULL
                             AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                        THEN (child.inventory_policy->>'packageLengthCm')::numeric
                        ELSE (parent.inventory_policy->>'packageLengthCm')::numeric
                    END,
                    0
                ),
                16
            )
            * COALESCE(
                NULLIF(
                    CASE
                        WHEN child.id IS NOT NULL
                             AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                        THEN (child.inventory_policy->>'packageWidthCm')::numeric
                        ELSE (parent.inventory_policy->>'packageWidthCm')::numeric
                    END,
                    0
                ),
                9
            )
            * COALESCE(
                NULLIF(
                    CASE
                        WHEN child.id IS NOT NULL
                             AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                        THEN (child.inventory_policy->>'packageHeightCm')::numeric
                        ELSE (parent.inventory_policy->>'packageHeightCm')::numeric
                    END,
                    0
                ),
                6
            )
            / GREATEST(
                COALESCE(
                    NULLIF(
                        CASE
                            WHEN child.id IS NOT NULL
                                 AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                            THEN (child.inventory_policy->>'packingRatio')::numeric
                            ELSE (parent.inventory_policy->>'packingRatio')::numeric
                        END,
                        0
                    ),
                    0.70
                ),
                0.01
            )
        ) AS item_volume_cm3,
        (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) AS usable_volume_cm3
    FROM inventory_levels il
    JOIN inventory_locations loc ON loc.id = il.location_id
    LEFT JOIN product_variants pv ON pv.id = il.variant_id
    LEFT JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
    LEFT JOIN categories child ON child.id = p.subcategory_id
    LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
    WHERE il.on_hand_quantity > 0
      AND loc.status = 'ACTIVE'
      AND loc.purpose = 'STORAGE'
      AND loc.code ~ '^[AB]-[0-9]{2}-[0-9]{2}$'
),
overloaded_locations AS (
    SELECT
        source_location_id,
        MAX(usable_volume_cm3) AS usable_volume_cm3,
        SUM(item_volume_cm3) AS used_volume_cm3,
        SUM(item_volume_cm3) - MAX(usable_volume_cm3) AS excess_volume_cm3
    FROM inventory_volume
    GROUP BY source_location_id
    HAVING SUM(item_volume_cm3) > MAX(usable_volume_cm3)
),
ranked_candidates AS (
    SELECT
        volume.*,
        overloaded.excess_volume_cm3,
        SUM(volume.item_volume_cm3) OVER (
            PARTITION BY volume.source_location_id
            ORDER BY volume.item_volume_cm3 DESC, volume.inventory_level_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS moved_volume_before
    FROM inventory_volume volume
    JOIN overloaded_locations overloaded
      ON overloaded.source_location_id = volume.source_location_id
),
selected_candidates AS (
    SELECT
        *,
        row_number() OVER (ORDER BY source_code, item_volume_cm3 DESC, inventory_level_id) AS transfer_rank
    FROM ranked_candidates
    WHERE COALESCE(moved_volume_before, 0) < excess_volume_cm3
),
available_targets AS (
    SELECT
        loc.id AS target_location_id,
        loc.code AS target_code,
        (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) AS target_usable_volume_cm3,
        row_number() OVER (ORDER BY loc.sort_order, loc.code) AS target_rank
    FROM inventory_locations loc
    LEFT JOIN inventory_levels il
      ON il.location_id = loc.id
     AND il.on_hand_quantity > 0
    WHERE loc.status = 'ACTIVE'
      AND loc.purpose = 'STORAGE'
      AND loc.code ~ '^C-[0-9]{2}-[0-9]{2}$'
    GROUP BY loc.id
    HAVING COALESCE(SUM(il.on_hand_quantity), 0) = 0
)
SELECT
    selected.inventory_level_id,
    selected.product_id,
    selected.variant_id,
    selected.source_location_id,
    selected.source_code,
    target.target_location_id,
    target.target_code,
    selected.on_hand_quantity,
    selected.item_volume_cm3
FROM selected_candidates selected
JOIN available_targets target ON target.target_rank = selected.transfer_rank
WHERE selected.item_volume_cm3 <= target.target_usable_volume_cm3;

DO $$
DECLARE
    required_transfer_count INTEGER;
    planned_transfer_count INTEGER;
BEGIN
    WITH inventory_volume AS (
        SELECT
            il.id AS inventory_level_id,
            il.location_id AS source_location_id,
            (
                il.on_hand_quantity
                * COALESCE(NULLIF(CASE WHEN child.id IS NOT NULL AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE THEN (child.inventory_policy->>'packageLengthCm')::numeric ELSE (parent.inventory_policy->>'packageLengthCm')::numeric END, 0), 16)
                * COALESCE(NULLIF(CASE WHEN child.id IS NOT NULL AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE THEN (child.inventory_policy->>'packageWidthCm')::numeric ELSE (parent.inventory_policy->>'packageWidthCm')::numeric END, 0), 9)
                * COALESCE(NULLIF(CASE WHEN child.id IS NOT NULL AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE THEN (child.inventory_policy->>'packageHeightCm')::numeric ELSE (parent.inventory_policy->>'packageHeightCm')::numeric END, 0), 6)
                / GREATEST(COALESCE(NULLIF(CASE WHEN child.id IS NOT NULL AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE THEN (child.inventory_policy->>'packingRatio')::numeric ELSE (parent.inventory_policy->>'packingRatio')::numeric END, 0), 0.70), 0.01)
            ) AS item_volume_cm3,
            (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) AS usable_volume_cm3
        FROM inventory_levels il
        JOIN inventory_locations loc ON loc.id = il.location_id
        LEFT JOIN product_variants pv ON pv.id = il.variant_id
        LEFT JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
        LEFT JOIN categories child ON child.id = p.subcategory_id
        LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
        WHERE il.on_hand_quantity > 0
          AND loc.status = 'ACTIVE'
          AND loc.purpose = 'STORAGE'
          AND loc.code ~ '^[AB]-[0-9]{2}-[0-9]{2}$'
    ),
    overloaded_locations AS (
        SELECT
            source_location_id,
            SUM(item_volume_cm3) - MAX(usable_volume_cm3) AS excess_volume_cm3
        FROM inventory_volume
        GROUP BY source_location_id
        HAVING SUM(item_volume_cm3) > MAX(usable_volume_cm3)
    ),
    ranked_candidates AS (
        SELECT
            volume.*,
            overloaded.excess_volume_cm3,
            SUM(volume.item_volume_cm3) OVER (
                PARTITION BY volume.source_location_id
                ORDER BY volume.item_volume_cm3 DESC, volume.inventory_level_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS moved_volume_before
        FROM inventory_volume volume
        JOIN overloaded_locations overloaded
          ON overloaded.source_location_id = volume.source_location_id
    )
    SELECT COUNT(*)
    INTO required_transfer_count
    FROM ranked_candidates
    WHERE COALESCE(moved_volume_before, 0) < excess_volume_cm3;

    SELECT COUNT(*) INTO planned_transfer_count FROM aisle_c_transfer_plan;

    IF planned_transfer_count <> required_transfer_count THEN
        RAISE EXCEPTION
            'Không đủ ô dãy C hoặc có dòng SKU vượt dung lượng ô: cần %, lập được %.',
            required_transfer_count,
            planned_transfer_count;
    END IF;
END
$$;

UPDATE product_imeis imei
SET location_id = plan.target_location_id,
    updated_at = NOW()
FROM aisle_c_transfer_plan plan
WHERE imei.location_id = plan.source_location_id
  AND (
        (plan.variant_id IS NULL AND imei.product_id = plan.product_id AND imei.variant_id IS NULL)
        OR imei.variant_id = plan.variant_id
  )
  AND imei.status IN ('IN_STOCK', 'PENDING_INBOUND');

UPDATE product_serial_numbers serial_number
SET location_id = plan.target_location_id,
    updated_at = NOW()
FROM aisle_c_transfer_plan plan
WHERE serial_number.location_id = plan.source_location_id
  AND (
        (plan.variant_id IS NULL AND serial_number.product_id = plan.product_id AND serial_number.variant_id IS NULL)
        OR serial_number.variant_id = plan.variant_id
  )
  AND serial_number.status IN ('IN_STOCK', 'PENDING_INBOUND');

UPDATE inventory_lots lot
SET location_id = plan.target_location_id,
    metadata = COALESCE(lot.metadata, '{}'::jsonb) || jsonb_build_object(
        'lastTransferFrom', plan.source_code,
        'lastTransferTo', plan.target_code,
        'lastTransferredAt', NOW()
    ),
    updated_at = NOW()
FROM aisle_c_transfer_plan plan
WHERE lot.location_id = plan.source_location_id
  AND lot.remaining_quantity > 0
  AND (
        (plan.variant_id IS NULL AND lot.product_id = plan.product_id AND lot.variant_id IS NULL)
        OR lot.variant_id = plan.variant_id
  );

UPDATE inventory_levels level
SET location_id = plan.target_location_id,
    updated_at = NOW()
FROM aisle_c_transfer_plan plan
WHERE level.id = plan.inventory_level_id;
