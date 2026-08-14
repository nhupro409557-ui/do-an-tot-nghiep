ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check CHECK (status IN (
        'PENDING_INBOUND', 'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
        'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING',
        'REPAIRED', 'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'OUT_OF_SYSTEM'
    ));

ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;

ALTER TABLE product_serial_numbers
    ADD CONSTRAINT product_serial_numbers_status_check CHECK (status IN (
        'PENDING_INBOUND', 'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
        'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING',
        'REPAIRED', 'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'OUT_OF_SYSTEM'
    ));

ALTER TABLE imei_disposition_events
    DROP CONSTRAINT IF EXISTS imei_disposition_events_new_status_check;

ALTER TABLE imei_disposition_events
    ADD CONSTRAINT imei_disposition_events_new_status_check CHECK (new_status IN (
        'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING', 'REPAIRED', 'RTV_PENDING',
        'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'SCRAP', 'OUT_OF_SYSTEM'
    ));
