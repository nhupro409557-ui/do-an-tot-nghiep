ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversed_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMPTZ;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversal_of_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL;

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
        'RECEIVING'
    ));

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
        'REVERSED',
        'WARRANTY',
        'RETIRED'
    ));

ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;

ALTER TABLE product_serial_numbers
    ADD CONSTRAINT product_serial_numbers_status_check
    CHECK (status IN (
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'RETURNED',
        'REVERSED',
        'WARRANTY',
        'IN_WARRANTY',
        'RETIRED',
        'SCRAP'
    ));

CREATE INDEX IF NOT EXISTS idx_inventory_documents_reversal_of
    ON inventory_documents(reversal_of_document_id);
