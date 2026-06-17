ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS posted_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_inventory_documents_created_by
    ON inventory_documents(created_by);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_approved_by
    ON inventory_documents(approved_by);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_posted_by
    ON inventory_documents(posted_by);
