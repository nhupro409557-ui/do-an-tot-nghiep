-- Receipt lifecycle for admin inbound inventory documents.

ALTER TABLE inventory_documents
DROP CONSTRAINT IF EXISTS inventory_documents_status_check;

ALTER TABLE inventory_documents
ADD CONSTRAINT inventory_documents_status_check
CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'RECEIVING', 'COMPLETED', 'CANCELLED', 'REJECTED', 'POSTED'));

ALTER TABLE inventory_document_lines
DROP CONSTRAINT IF EXISTS inventory_document_lines_item_check;

ALTER TABLE inventory_document_lines
ADD CONSTRAINT inventory_document_lines_item_check
CHECK (product_id IS NOT NULL OR variant_id IS NOT NULL);

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_inventory_documents_inbound_status_created
    ON inventory_documents(document_type, status, created_at DESC)
    WHERE document_type = 'INBOUND';
