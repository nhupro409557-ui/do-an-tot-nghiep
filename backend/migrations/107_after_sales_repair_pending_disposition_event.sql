ALTER TABLE imei_disposition_events
    DROP CONSTRAINT IF EXISTS imei_disposition_events_new_status_check;

ALTER TABLE imei_disposition_events
    ADD CONSTRAINT imei_disposition_events_new_status_check CHECK (new_status IN (
        'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'REPAIR_PENDING', 'RTV_PENDING',
        'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'SCRAP', 'OUT_OF_SYSTEM'
    ));
