ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS return_source VARCHAR(30),
    ADD COLUMN IF NOT EXISTS return_reason TEXT,
    ADD COLUMN IF NOT EXISTS return_tracking_code VARCHAR(120),
    ADD COLUMN IF NOT EXISTS return_received_condition VARCHAR(30),
    ADD COLUMN IF NOT EXISTS return_received_at TIMESTAMPTZ;

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_return_source;
ALTER TABLE orders ADD CONSTRAINT ck_orders_return_source
    CHECK (return_source IS NULL OR return_source IN ('DELIVERY_REFUSED', 'CUSTOMER_RETURN'));

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_return_received_condition;
ALTER TABLE orders ADD CONSTRAINT ck_orders_return_received_condition
    CHECK (
        return_received_condition IS NULL
        OR return_received_condition IN ('SEALED', 'OPENED', 'DAMAGED')
    );
