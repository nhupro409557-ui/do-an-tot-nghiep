-- Add order_id to inventory_documents to link with orders table
ALTER TABLE inventory_documents
ADD COLUMN IF NOT EXISTS order_id UUID NULL REFERENCES orders(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_documents_order_id ON inventory_documents(order_id);
