-- Align IMEI lifecycle statuses with the WMS/ERP inventory model.
ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check
    CHECK (status IN (
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'IN_WARRANTY',
        'SCRAP',
        'RETURNED',
        'WARRANTY',
        'RETIRED'
    ));

