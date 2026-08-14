ALTER TABLE warranty_requests
    ADD COLUMN IF NOT EXISTS repair_channel VARCHAR(20),
    ADD COLUMN IF NOT EXISTS repair_provider_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS repair_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS return_fulfillment_method VARCHAR(30);

ALTER TABLE warranty_requests DROP CONSTRAINT IF EXISTS warranty_requests_status_check;
ALTER TABLE warranty_requests ADD CONSTRAINT warranty_requests_status_check CHECK (status IN (
    'SUBMITTED', 'RECEIVED', 'QC_IN_PROGRESS', 'WARRANTY_ACCEPTED', 'REJECTED',
    'REPAIRING', 'REPAIR_COMPLETED', 'REPLACEMENT_APPROVED', 'WAITING_FOR_STOCK',
    'REPLACEMENT_PROCESSING', 'READY_TO_RETURN', 'RETURNING_TO_CUSTOMER', 'COMPLETED',
    'CANCELLED', 'CLOSED_EXPIRED'
));

ALTER TABLE warranty_requests DROP CONSTRAINT IF EXISTS warranty_requests_repair_channel_check;
ALTER TABLE warranty_requests ADD CONSTRAINT warranty_requests_repair_channel_check CHECK (
    repair_channel IS NULL OR repair_channel IN ('INTERNAL', 'MANUFACTURER')
);

ALTER TABLE warranty_requests DROP CONSTRAINT IF EXISTS warranty_requests_return_fulfillment_check;
ALTER TABLE warranty_requests ADD CONSTRAINT warranty_requests_return_fulfillment_check CHECK (
    return_fulfillment_method IS NULL OR return_fulfillment_method IN ('DELIVERY', 'STORE_PICKUP')
);

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_order_purpose;
ALTER TABLE orders ADD CONSTRAINT ck_orders_order_purpose CHECK (
    order_purpose IN ('SALE', 'WARRANTY_REPLACEMENT', 'WARRANTY_RETURN', 'RETURN_EXCHANGE')
);

ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_orders_after_sales_source;
ALTER TABLE orders ADD CONSTRAINT ck_orders_after_sales_source CHECK (
    (order_purpose = 'SALE' AND warranty_request_id IS NULL AND return_request_id IS NULL)
    OR
    (order_purpose IN ('WARRANTY_REPLACEMENT', 'WARRANTY_RETURN')
        AND warranty_request_id IS NOT NULL AND return_request_id IS NULL AND source_order_id IS NOT NULL)
    OR
    (order_purpose = 'RETURN_EXCHANGE'
        AND return_request_id IS NOT NULL AND warranty_request_id IS NULL AND source_order_id IS NOT NULL)
);

ALTER TABLE product_imeis DROP CONSTRAINT IF EXISTS product_imeis_status_check;
ALTER TABLE product_imeis ADD CONSTRAINT product_imeis_status_check CHECK (status IN (
    'PENDING_INBOUND', 'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
    'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING',
    'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'OUT_OF_SYSTEM'
));

ALTER TABLE product_serial_numbers DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;
ALTER TABLE product_serial_numbers ADD CONSTRAINT product_serial_numbers_status_check CHECK (status IN (
    'PENDING_INBOUND', 'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
    'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING',
    'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'OUT_OF_SYSTEM'
));
