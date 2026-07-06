CREATE TABLE IF NOT EXISTS inventory_identifier_location_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier_type VARCHAR(20) NOT NULL,
    identifier_id UUID NOT NULL,
    identifier_value VARCHAR(120) NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    identifier_pair_id UUID REFERENCES product_identifier_pairs(id) ON DELETE SET NULL,
    current_location_id UUID REFERENCES inventory_locations(id) ON DELETE SET NULL,
    new_location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decided_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decision_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    CONSTRAINT inventory_identifier_location_requests_type_check
        CHECK (identifier_type IN ('IMEI', 'SERIAL')),
    CONSTRAINT inventory_identifier_location_requests_status_check
        CHECK (status IN ('PENDING', 'APPROVED', 'CANCELLED')),
    CONSTRAINT inventory_identifier_location_requests_reason_check
        CHECK (length(trim(reason)) >= 5),
    CONSTRAINT inventory_identifier_location_requests_changed_location_check
        CHECK (current_location_id IS DISTINCT FROM new_location_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_identifier_location_requests_pending
    ON inventory_identifier_location_requests(identifier_type, identifier_id)
    WHERE status = 'PENDING';

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_identifier_location_requests_pending_pair
    ON inventory_identifier_location_requests(identifier_pair_id)
    WHERE status = 'PENDING' AND identifier_pair_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_identifier_location_requests_product
    ON inventory_identifier_location_requests(product_id, variant_id, status, created_at DESC);
