-- Bổ sung vị trí kệ cho IMEI/serial trên database đã khởi tạo trước migration kệ hàng.

ALTER TABLE product_imeis
    ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT;

ALTER TABLE product_serial_numbers
    ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT;

UPDATE product_imeis pi
SET location_id = line_locations.location_id
FROM (
    SELECT DISTINCT ON (identifier.metadata_imei)
        l.location_id,
        identifier.metadata_imei
    FROM inventory_document_lines l
    CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(l.metadata->'imeis', '[]'::jsonb)) AS identifier(metadata_imei)
    JOIN inventory_documents d ON d.id = l.document_id
    WHERE d.document_type = 'INBOUND'
      AND l.location_id IS NOT NULL
    ORDER BY identifier.metadata_imei, d.posted_at DESC NULLS LAST, d.created_at DESC
) AS line_locations
WHERE pi.imei = line_locations.metadata_imei
  AND pi.location_id IS NULL;

UPDATE product_serial_numbers psn
SET location_id = line_locations.location_id
FROM (
    SELECT DISTINCT ON (identifier.metadata_serial, l.product_id)
        l.location_id,
        identifier.metadata_serial,
        l.product_id
    FROM inventory_document_lines l
    CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(l.metadata->'serialNumbers', '[]'::jsonb)) AS identifier(metadata_serial)
    JOIN inventory_documents d ON d.id = l.document_id
    WHERE d.document_type = 'INBOUND'
      AND l.location_id IS NOT NULL
    ORDER BY identifier.metadata_serial, l.product_id, d.posted_at DESC NULLS LAST, d.created_at DESC
) AS line_locations
WHERE psn.serial_number = line_locations.metadata_serial
  AND psn.product_id = line_locations.product_id
  AND psn.location_id IS NULL;

UPDATE product_imeis pi
SET location_id = levels.location_id
FROM inventory_levels levels
WHERE pi.location_id IS NULL
  AND pi.status IN ('IN_STOCK', 'RESERVED', 'PENDING_INBOUND')
  AND levels.variant_id = pi.variant_id
  AND levels.product_id IS NULL;

UPDATE product_serial_numbers psn
SET location_id = levels.location_id
FROM inventory_levels levels
WHERE psn.location_id IS NULL
  AND psn.status IN ('IN_STOCK', 'RESERVED', 'PENDING_INBOUND')
  AND levels.variant_id = psn.variant_id
  AND levels.product_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_product_imeis_location_id
    ON product_imeis(location_id);

CREATE INDEX IF NOT EXISTS idx_product_serial_numbers_location_id
    ON product_serial_numbers(location_id);
