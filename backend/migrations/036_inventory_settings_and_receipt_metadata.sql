-- Inventory settings and richer receipt metadata
-- This migration extends the existing single-warehouse flow without replacing it.

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(160);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(14, 2);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_code VARCHAR(60);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_name VARCHAR(160);

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS sales_config JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE products
SET sales_config = jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(COALESCE(sales_config, '{}'::jsonb), '{minimumStock}', COALESCE(sales_config->'minimumStock', '0'::jsonb), true),
                    '{blockSaleWhenOutOfStock}',
                    COALESCE(sales_config->'blockSaleWhenOutOfStock', 'true'::jsonb),
                    true
                ),
                '{preferredLocationCode}',
                COALESCE(sales_config->'preferredLocationCode', '""'::jsonb),
                true
            ),
            '{preferredLocationName}',
            COALESCE(sales_config->'preferredLocationName', '""'::jsonb),
            true
        ),
        '{cycleCountDays}',
        COALESCE(sales_config->'cycleCountDays', '30'::jsonb),
        true
    )
WHERE sales_config IS NULL
   OR NOT (sales_config ? 'minimumStock')
   OR NOT (sales_config ? 'blockSaleWhenOutOfStock')
   OR NOT (sales_config ? 'preferredLocationCode')
   OR NOT (sales_config ? 'preferredLocationName')
   OR NOT (sales_config ? 'cycleCountDays');
