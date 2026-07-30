ALTER TABLE return_requests
    ADD COLUMN IF NOT EXISTS inventory_disposition VARCHAR(30);

ALTER TABLE return_requests
    DROP CONSTRAINT IF EXISTS return_requests_inventory_disposition_check;

ALTER TABLE return_requests
    ADD CONSTRAINT return_requests_inventory_disposition_check
    CHECK (inventory_disposition IS NULL OR inventory_disposition IN (
        'NEW_STOCK', 'USED_INTAKE', 'REPAIR', 'SCRAP'
    ));

CREATE UNIQUE INDEX IF NOT EXISTS uq_used_intake_return_item
    ON used_device_intake_requests(return_request_id, imei)
    WHERE return_request_id IS NOT NULL;
