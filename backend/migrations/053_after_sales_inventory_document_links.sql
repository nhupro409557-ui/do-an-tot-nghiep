ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS return_request_id UUID
        REFERENCES return_requests(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS warranty_request_id UUID
        REFERENCES warranty_requests(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    DROP CONSTRAINT IF EXISTS inventory_documents_after_sales_reference_check;

ALTER TABLE inventory_documents
    ADD CONSTRAINT inventory_documents_after_sales_reference_check
    CHECK (num_nonnulls(return_request_id, warranty_request_id) <= 1);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_return_request
    ON inventory_documents(return_request_id)
    WHERE return_request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_documents_warranty_request
    ON inventory_documents(warranty_request_id)
    WHERE warranty_request_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_documents_return_outbound
    ON inventory_documents(return_request_id)
    WHERE return_request_id IS NOT NULL
      AND document_type = 'OUTBOUND'
      AND status <> 'CANCELLED';

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_documents_warranty_outbound
    ON inventory_documents(warranty_request_id)
    WHERE warranty_request_id IS NOT NULL
      AND document_type = 'OUTBOUND'
      AND status <> 'CANCELLED';
