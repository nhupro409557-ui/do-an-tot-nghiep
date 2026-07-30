ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS after_sales_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS after_sales_request_item_id UUID;

ALTER TABLE order_items DROP CONSTRAINT IF EXISTS ck_order_items_after_sales_type;
ALTER TABLE order_items ADD CONSTRAINT ck_order_items_after_sales_type
    CHECK (after_sales_type IS NULL OR after_sales_type IN ('WARRANTY', 'RETURN'));

CREATE INDEX IF NOT EXISTS idx_order_items_after_sales_request_item
    ON order_items(after_sales_type, after_sales_request_item_id)
    WHERE after_sales_request_item_id IS NOT NULL;
