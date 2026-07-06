ALTER TABLE return_request_items
    ADD COLUMN IF NOT EXISTS replacement_imeis JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS replacement_secondary_imeis JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS replacement_serial_numbers JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE warranty_request_items
    ADD COLUMN IF NOT EXISTS replacement_imeis JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS replacement_secondary_imeis JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS replacement_serial_numbers JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE return_request_items
SET replacement_imeis = jsonb_build_array(replacement_imei)
WHERE replacement_imei IS NOT NULL
  AND replacement_imei <> ''
  AND replacement_imeis = '[]'::jsonb;

UPDATE warranty_request_items
SET replacement_imeis = jsonb_build_array(replacement_imei)
WHERE replacement_imei IS NOT NULL
  AND replacement_imei <> ''
  AND replacement_imeis = '[]'::jsonb;

ALTER TABLE return_request_items
    ADD CONSTRAINT return_request_items_replacement_identifiers_check
    CHECK (
        jsonb_typeof(replacement_imeis) = 'array'
        AND jsonb_typeof(replacement_secondary_imeis) = 'array'
        AND jsonb_typeof(replacement_serial_numbers) = 'array'
    );

ALTER TABLE warranty_request_items
    ADD CONSTRAINT warranty_request_items_replacement_identifiers_check
    CHECK (
        jsonb_typeof(replacement_imeis) = 'array'
        AND jsonb_typeof(replacement_secondary_imeis) = 'array'
        AND jsonb_typeof(replacement_serial_numbers) = 'array'
    );
