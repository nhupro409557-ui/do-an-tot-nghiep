-- Flash sale quota support.
-- NULL quantity_limit means the flash sale is unlimited.

ALTER TABLE flash_sales
    ADD COLUMN IF NOT EXISTS quantity_limit INTEGER NULL,
    ADD COLUMN IF NOT EXISTS sold_quantity INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quota_exhausted_at TIMESTAMPTZ NULL;

ALTER TABLE flash_sales
    DROP CONSTRAINT IF EXISTS flash_sales_quantity_limit_check;

ALTER TABLE flash_sales
    ADD CONSTRAINT flash_sales_quantity_limit_check
    CHECK (quantity_limit IS NULL OR quantity_limit > 0);

ALTER TABLE flash_sales
    DROP CONSTRAINT IF EXISTS flash_sales_sold_quantity_check;

ALTER TABLE flash_sales
    ADD CONSTRAINT flash_sales_sold_quantity_check
    CHECK (sold_quantity >= 0);

UPDATE flash_sales
SET status = 'INACTIVE',
    quota_exhausted_at = COALESCE(quota_exhausted_at, NOW()),
    updated_at = NOW()
WHERE status = 'ACTIVE'
  AND quantity_limit IS NOT NULL
  AND sold_quantity >= quantity_limit;

CREATE INDEX IF NOT EXISTS idx_flash_sales_active_quota
    ON flash_sales(status, quantity_limit, sold_quantity)
    WHERE quantity_limit IS NOT NULL;

ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS flash_sale_id UUID NULL REFERENCES flash_sales(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS flash_sale_quantity INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS flash_sale_released_at TIMESTAMPTZ NULL;

ALTER TABLE order_items
    DROP CONSTRAINT IF EXISTS order_items_flash_sale_quantity_check;

ALTER TABLE order_items
    ADD CONSTRAINT order_items_flash_sale_quantity_check
    CHECK (flash_sale_quantity >= 0);

CREATE INDEX IF NOT EXISTS idx_order_items_flash_sale_id
    ON order_items(flash_sale_id)
    WHERE flash_sale_id IS NOT NULL;
