-- Separate IMEI collection from receipt creation.

ALTER TABLE inventory_documents
DROP CONSTRAINT IF EXISTS inventory_documents_status_check;

ALTER TABLE inventory_documents
ADD CONSTRAINT inventory_documents_status_check
CHECK (status IN (
    'DRAFT',
    'PROCESSING_IMEI',
    'PENDING_SHORTAGE_APPROVAL',
    'APPROVED',
    'COMPLETED',
    'CANCELLED',
    'REJECTED',
    'POSTED',
    'PENDING_APPROVAL',
    'RECEIVING'
));

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE inventory_document_lines
SET metadata = metadata
    || jsonb_build_object(
        'plannedQuantity', requested_quantity,
        'receivedQuantity', COALESCE((metadata->>'receivedQuantity')::int, 0),
        'tracksImei', COALESCE((metadata->>'tracksImei')::boolean, FALSE)
    )
WHERE document_id IN (
    SELECT id FROM inventory_documents WHERE document_type = 'INBOUND'
);
