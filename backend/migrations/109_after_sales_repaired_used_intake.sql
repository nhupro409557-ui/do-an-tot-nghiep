ALTER TABLE used_device_intake_requests
    ADD COLUMN IF NOT EXISTS warranty_request_id UUID
        REFERENCES warranty_requests(id) ON DELETE SET NULL;

ALTER TABLE used_device_intake_requests
    DROP CONSTRAINT IF EXISTS used_device_intake_requests_source_type_check;

ALTER TABLE used_device_intake_requests
    ADD CONSTRAINT used_device_intake_requests_source_type_check
    CHECK (source_type IN ('USER_BUYBACK', 'RETURNED_USED', 'AFTER_SALES_REPAIRED'));

CREATE INDEX IF NOT EXISTS idx_used_intake_warranty_request
    ON used_device_intake_requests(warranty_request_id)
    WHERE warranty_request_id IS NOT NULL;
