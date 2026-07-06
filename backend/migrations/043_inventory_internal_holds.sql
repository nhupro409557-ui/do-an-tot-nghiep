-- Add document type for internal inventory holds.

ALTER TABLE inventory_documents
    DROP CONSTRAINT IF EXISTS inventory_documents_document_type_check;

ALTER TABLE inventory_documents
    ADD CONSTRAINT inventory_documents_document_type_check
    CHECK (document_type IN (
        'INBOUND',
        'OUTBOUND',
        'ADJUSTMENT',
        'COUNT',
        'REVERSAL',
        'TRANSFER',
        'RESERVATION_RELEASE',
        'INTERNAL_HOLD'
    ));

CREATE INDEX IF NOT EXISTS idx_inventory_documents_internal_hold_status_created
    ON inventory_documents(document_type, status, created_at DESC)
    WHERE document_type = 'INTERNAL_HOLD';
