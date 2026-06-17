CREATE TABLE IF NOT EXISTS inventory_identifier_edit_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier_type VARCHAR(20) NOT NULL,
    identifier_id UUID NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    current_value VARCHAR(120) NOT NULL,
    new_value VARCHAR(120) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decided_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decision_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    CONSTRAINT inventory_identifier_edit_requests_type_check
        CHECK (identifier_type IN ('IMEI', 'SERIAL')),
    CONSTRAINT inventory_identifier_edit_requests_status_check
        CHECK (status IN ('PENDING', 'APPROVED', 'CANCELLED')),
    CONSTRAINT inventory_identifier_edit_requests_reason_check
        CHECK (length(trim(reason)) >= 5),
    CONSTRAINT inventory_identifier_edit_requests_changed_value_check
        CHECK (current_value <> new_value)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_identifier_edit_requests_pending
    ON inventory_identifier_edit_requests(identifier_type, identifier_id)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_inventory_identifier_edit_requests_product
    ON inventory_identifier_edit_requests(product_id, variant_id, status, created_at DESC);

