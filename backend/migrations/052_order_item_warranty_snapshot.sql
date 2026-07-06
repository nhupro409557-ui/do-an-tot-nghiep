-- Snapshot warranty months at sale time.
-- Legacy/manual rows may stay NULL. New checkout rows should write a value.

ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS warranty_months_snapshot INTEGER NULL;

ALTER TABLE order_items
    DROP CONSTRAINT IF EXISTS order_items_warranty_months_snapshot_check;

ALTER TABLE order_items
    ADD CONSTRAINT order_items_warranty_months_snapshot_check
    CHECK (warranty_months_snapshot IS NULL OR warranty_months_snapshot >= 0);

UPDATE order_items oi
SET warranty_months_snapshot = GREATEST(COALESCE(p.warranty_period, 0), 0)
FROM products p
WHERE oi.product_id = p.id
  AND oi.warranty_months_snapshot IS NULL;

CREATE INDEX IF NOT EXISTS idx_order_items_warranty_snapshot
    ON order_items(warranty_months_snapshot)
    WHERE warranty_months_snapshot IS NOT NULL;
