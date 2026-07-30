ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS order_purpose VARCHAR(40) NOT NULL DEFAULT 'SALE',
    ADD COLUMN IF NOT EXISTS source_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS warranty_request_id UUID REFERENCES warranty_requests(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS return_request_id UUID REFERENCES return_requests(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS payment_requirement VARCHAR(40) NOT NULL DEFAULT 'PAYMENT_REQUIRED',
    ADD COLUMN IF NOT EXISTS fulfillment_method VARCHAR(30) NOT NULL DEFAULT 'DELIVERY';

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_order_purpose;
ALTER TABLE orders ADD CONSTRAINT ck_orders_order_purpose
    CHECK (order_purpose IN ('SALE', 'WARRANTY_REPLACEMENT', 'RETURN_EXCHANGE'));

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_payment_requirement;
ALTER TABLE orders ADD CONSTRAINT ck_orders_payment_requirement
    CHECK (payment_requirement IN ('PAYMENT_REQUIRED', 'NO_PAYMENT_REQUIRED', 'BALANCE_PAYMENT'));

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_fulfillment_method;
ALTER TABLE orders ADD CONSTRAINT ck_orders_fulfillment_method
    CHECK (fulfillment_method IN ('DELIVERY', 'STORE_PICKUP'));

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_after_sales_source;
ALTER TABLE orders ADD CONSTRAINT ck_orders_after_sales_source CHECK (
    (order_purpose = 'SALE' AND warranty_request_id IS NULL AND return_request_id IS NULL)
    OR
    (order_purpose = 'WARRANTY_REPLACEMENT' AND warranty_request_id IS NOT NULL AND return_request_id IS NULL AND source_order_id IS NOT NULL)
    OR
    (order_purpose = 'RETURN_EXCHANGE' AND return_request_id IS NOT NULL AND warranty_request_id IS NULL AND source_order_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_warranty_request
    ON orders(warranty_request_id) WHERE warranty_request_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_return_request
    ON orders(return_request_id) WHERE return_request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_source_order_id ON orders(source_order_id);
