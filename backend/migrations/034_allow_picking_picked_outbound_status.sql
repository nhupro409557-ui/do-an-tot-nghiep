-- Update constraint inventory_documents_status_check to allow 'PICKING' and 'PICKED' statuses
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
        'REVERSED',
        'REJECTED',
        'POSTED',
        'PENDING_APPROVAL',
        'RECEIVING',
        'PICKING',
        'PICKED'
    ));
