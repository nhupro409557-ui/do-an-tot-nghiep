-- Allow each product or variant to keep many IMEI values while marking one as the primary IMEI.

ALTER TABLE product_imeis
    ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE;

WITH ranked_imeis AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id
            ORDER BY
                CASE WHEN is_primary THEN 0 ELSE 1 END,
                received_at NULLS LAST,
                created_at,
                id
        ) AS row_number
    FROM product_imeis
)
UPDATE product_imeis pi
SET is_primary = TRUE,
    updated_at = NOW()
FROM ranked_imeis ranked
WHERE ranked.id = pi.id
  AND ranked.row_number = 1
  AND pi.is_primary = FALSE
  AND NOT EXISTS (
      SELECT 1
      FROM product_imeis existing
      WHERE existing.product_id = pi.product_id
        AND (
            existing.variant_id = pi.variant_id
            OR (existing.variant_id IS NULL AND pi.variant_id IS NULL)
        )
        AND existing.is_primary = TRUE
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_imeis_primary_base
    ON product_imeis(product_id)
    WHERE is_primary = TRUE AND variant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_imeis_primary_variant
    ON product_imeis(product_id, variant_id)
    WHERE is_primary = TRUE AND variant_id IS NOT NULL;
