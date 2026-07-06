ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check CHECK (
        status IN (
            'PENDING_INBOUND',
            'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
            'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING',
            'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED',
            'OUT_OF_SYSTEM'
        )
    );

ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;

ALTER TABLE product_serial_numbers
    ADD CONSTRAINT product_serial_numbers_status_check CHECK (
        status IN (
            'PENDING_INBOUND',
            'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
            'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING',
            'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED',
            'OUT_OF_SYSTEM'
        )
    );
