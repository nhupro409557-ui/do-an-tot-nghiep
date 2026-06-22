-- Phân bổ tồn kho của sản phẩm đang bán từ vị trí hệ thống MAIN vào các ô lưu hàng A/B.

UPDATE inventory_locations
SET allow_mixed_sku = TRUE,
    updated_at = NOW()
WHERE status = 'ACTIVE'
  AND purpose = 'STORAGE'
  AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$';

WITH active_storage_locations AS (
    SELECT
        id,
        code,
        row_number() OVER (ORDER BY sort_order, code) AS location_rank,
        count(*) OVER () AS location_count
    FROM inventory_locations
    WHERE status = 'ACTIVE'
      AND purpose = 'STORAGE'
      AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$'
),
active_inventory AS (
    SELECT
        il.id AS inventory_level_id,
        il.product_id,
        il.variant_id,
        COALESCE(il.product_id, pv.product_id) AS resolved_product_id,
        row_number() OVER (
            ORDER BY
                COALESCE(c.sort_order, 9999),
                COALESCE(c.code, ''),
                p.name,
                COALESCE(pv.sku, p.sku, ''),
                il.id
        ) AS inventory_rank
    FROM inventory_levels il
    LEFT JOIN product_variants pv ON pv.id = il.variant_id
    JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
    LEFT JOIN categories c ON c.id = p.category_id
    WHERE il.on_hand_quantity > 0
      AND p.status = 'ACTIVE'
      AND (
          il.variant_id IS NULL
          OR (
              pv.deleted_at IS NULL
              AND COALESCE(pv.is_active, TRUE) = TRUE
              AND LOWER(COALESCE(pv.status, 'active')) = 'active'
          )
      )
),
assigned_inventory AS (
    SELECT
        ai.inventory_level_id,
        ai.product_id,
        ai.variant_id,
        asl.id AS target_location_id
    FROM active_inventory ai
    JOIN active_storage_locations asl
      ON asl.location_rank = ((ai.inventory_rank - 1) % asl.location_count) + 1
)
UPDATE inventory_levels il
SET location_id = assigned.target_location_id,
    updated_at = NOW()
FROM assigned_inventory assigned
WHERE il.id = assigned.inventory_level_id;

WITH active_storage_locations AS (
    SELECT
        id,
        row_number() OVER (ORDER BY sort_order, code) AS location_rank,
        count(*) OVER () AS location_count
    FROM inventory_locations
    WHERE status = 'ACTIVE'
      AND purpose = 'STORAGE'
      AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$'
),
active_inventory AS (
    SELECT
        il.id AS inventory_level_id,
        il.product_id,
        il.variant_id,
        row_number() OVER (
            ORDER BY
                COALESCE(c.sort_order, 9999),
                COALESCE(c.code, ''),
                p.name,
                COALESCE(pv.sku, p.sku, ''),
                il.id
        ) AS inventory_rank
    FROM inventory_levels il
    LEFT JOIN product_variants pv ON pv.id = il.variant_id
    JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
    LEFT JOIN categories c ON c.id = p.category_id
    WHERE il.on_hand_quantity > 0
      AND p.status = 'ACTIVE'
      AND (
          il.variant_id IS NULL
          OR (
              pv.deleted_at IS NULL
              AND COALESCE(pv.is_active, TRUE) = TRUE
              AND LOWER(COALESCE(pv.status, 'active')) = 'active'
          )
      )
),
assigned_inventory AS (
    SELECT
        ai.product_id,
        ai.variant_id,
        asl.id AS target_location_id
    FROM active_inventory ai
    JOIN active_storage_locations asl
      ON asl.location_rank = ((ai.inventory_rank - 1) % asl.location_count) + 1
)
UPDATE product_serial_numbers serials
SET location_id = assigned.target_location_id,
    updated_at = NOW()
FROM assigned_inventory assigned
WHERE serials.product_id = COALESCE(assigned.product_id, serials.product_id)
  AND (
      (assigned.variant_id IS NULL AND serials.variant_id IS NULL AND serials.product_id = assigned.product_id)
      OR serials.variant_id = assigned.variant_id
  )
  AND serials.status IN ('IN_STOCK', 'PENDING_INBOUND');

WITH active_storage_locations AS (
    SELECT
        id,
        row_number() OVER (ORDER BY sort_order, code) AS location_rank,
        count(*) OVER () AS location_count
    FROM inventory_locations
    WHERE status = 'ACTIVE'
      AND purpose = 'STORAGE'
      AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$'
),
active_inventory AS (
    SELECT
        il.id AS inventory_level_id,
        il.product_id,
        il.variant_id,
        row_number() OVER (
            ORDER BY
                COALESCE(c.sort_order, 9999),
                COALESCE(c.code, ''),
                p.name,
                COALESCE(pv.sku, p.sku, ''),
                il.id
        ) AS inventory_rank
    FROM inventory_levels il
    LEFT JOIN product_variants pv ON pv.id = il.variant_id
    JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
    LEFT JOIN categories c ON c.id = p.category_id
    WHERE il.on_hand_quantity > 0
      AND p.status = 'ACTIVE'
      AND (
          il.variant_id IS NULL
          OR (
              pv.deleted_at IS NULL
              AND COALESCE(pv.is_active, TRUE) = TRUE
              AND LOWER(COALESCE(pv.status, 'active')) = 'active'
          )
      )
),
assigned_inventory AS (
    SELECT
        ai.product_id,
        ai.variant_id,
        asl.id AS target_location_id
    FROM active_inventory ai
    JOIN active_storage_locations asl
      ON asl.location_rank = ((ai.inventory_rank - 1) % asl.location_count) + 1
)
UPDATE product_imeis imeis
SET location_id = assigned.target_location_id,
    updated_at = NOW()
FROM assigned_inventory assigned
WHERE imeis.product_id = COALESCE(assigned.product_id, imeis.product_id)
  AND (
      (assigned.variant_id IS NULL AND imeis.variant_id IS NULL AND imeis.product_id = assigned.product_id)
      OR imeis.variant_id = assigned.variant_id
  )
  AND imeis.status IN ('IN_STOCK', 'PENDING_INBOUND');
