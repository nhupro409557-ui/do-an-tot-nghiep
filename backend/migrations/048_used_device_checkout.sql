ALTER TABLE order_items
ADD COLUMN IF NOT EXISTS used_device_id UUID REFERENCES used_devices(id);

DROP INDEX IF EXISTS idx_order_items_used_device_once;

CREATE INDEX IF NOT EXISTS idx_order_items_used_device_id
ON order_items(used_device_id)
WHERE used_device_id IS NOT NULL;
