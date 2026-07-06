-- Hệ thống hậu mãi, tracking vận chuyển và trung tâm giao dịch khách hàng.

ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS entity_type VARCHAR(40),
    ADD COLUMN IF NOT EXISTS entity_id UUID,
    ADD COLUMN IF NOT EXISTS action_url TEXT,
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(180),
    ADD COLUMN IF NOT EXISTS available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_idempotency_key
    ON notifications(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS return_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_code VARCHAR(40) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED',
    reason TEXT NOT NULL,
    resolution_type VARCHAR(30),
    customer_fault BOOLEAN NOT NULL DEFAULT FALSE,
    admin_note TEXT,
    qc_note TEXT,
    sla_due_at TIMESTAMPTZ,
    sla_breached_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    qc_approved_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT return_requests_status_check CHECK (status IN (
        'SUBMITTED', 'RECEIVED', 'QC_IN_PROGRESS', 'QC_APPROVED', 'REJECTED',
        'WAITING_FOR_STOCK', 'EXCHANGE_PROCESSING', 'REFUND_PROCESSING',
        'COMPLETED', 'CANCELLED', 'CLOSED_EXPIRED'
    )),
    CONSTRAINT return_requests_resolution_check CHECK (
        resolution_type IS NULL OR resolution_type IN ('EXCHANGE', 'REFUND')
    )
);

CREATE TABLE IF NOT EXISTS warranty_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_code VARCHAR(40) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    status VARCHAR(40) NOT NULL DEFAULT 'SUBMITTED',
    reason TEXT NOT NULL,
    resolution_type VARCHAR(30),
    admin_note TEXT,
    qc_note TEXT,
    sla_due_at TIMESTAMPTZ,
    sla_breached_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    replacement_approved_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT warranty_requests_status_check CHECK (status IN (
        'SUBMITTED', 'RECEIVED', 'QC_IN_PROGRESS', 'WARRANTY_ACCEPTED', 'REJECTED',
        'REPAIRING', 'REPLACEMENT_APPROVED', 'WAITING_FOR_STOCK',
        'REPLACEMENT_PROCESSING', 'READY_TO_RETURN', 'COMPLETED',
        'CANCELLED', 'CLOSED_EXPIRED'
    )),
    CONSTRAINT warranty_requests_resolution_check CHECK (
        resolution_type IS NULL OR resolution_type IN ('REPAIR', 'REPLACEMENT')
    )
);

CREATE TABLE IF NOT EXISTS return_request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES return_requests(id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES order_items(id),
    product_id UUID REFERENCES products(id),
    product_variant_id UUID REFERENCES product_variants(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    imei VARCHAR(80),
    serial_number VARCHAR(120),
    unit_price_snapshot NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_allocation_snapshot NUMERIC(14,2) NOT NULL DEFAULT 0,
    refundable_amount_snapshot NUMERIC(14,2) NOT NULL DEFAULT 0,
    replacement_imei VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS warranty_request_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES warranty_requests(id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES order_items(id),
    product_id UUID REFERENCES products(id),
    product_variant_id UUID REFERENCES product_variants(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    imei VARCHAR(80),
    serial_number VARCHAR(120),
    replacement_imei VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS after_sales_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_type VARCHAR(20) NOT NULL CHECK (reference_type IN ('RETURN', 'WARRANTY')),
    reference_id UUID NOT NULL,
    old_status VARCHAR(40),
    new_status VARCHAR(40) NOT NULL,
    actor_id UUID REFERENCES users(id),
    actor_name VARCHAR(255),
    note TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS after_sales_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_type VARCHAR(20) NOT NULL CHECK (reference_type IN ('RETURN', 'WARRANTY')),
    reference_id UUID NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    original_name VARCHAR(255) NOT NULL,
    storage_key TEXT NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0 AND size_bytes <= 20971520),
    checksum_sha256 VARCHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'PENDING_DELETE', 'DELETED')),
    delete_after TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS after_sales_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_type VARCHAR(20) NOT NULL CHECK (reference_type IN ('RETURN', 'WARRANTY')),
    reference_id UUID NOT NULL,
    product_variant_id UUID REFERENCES product_variants(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'LOCKED'
        CHECK (status IN ('LOCKED', 'RELEASED', 'CONSUMED')),
    expires_at TIMESTAMPTZ NOT NULL,
    released_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_after_sales_active_allocation
    ON after_sales_allocations(reference_type, reference_id, product_id, COALESCE(product_variant_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE status = 'LOCKED';

CREATE TABLE IF NOT EXISTS refund_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    order_item_id UUID REFERENCES order_items(id),
    return_request_id UUID REFERENCES return_requests(id),
    user_id UUID NOT NULL REFERENCES users(id),
    provider VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    gross_amount NUMERIC(14,2) NOT NULL CHECK (gross_amount >= 0),
    shipping_deduction NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (shipping_deduction >= 0),
    refund_amount NUMERIC(14,2) NOT NULL CHECK (refund_amount >= 0),
    transaction_ref VARCHAR(160),
    idempotency_key VARCHAR(180) NOT NULL UNIQUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS compensation_vouchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    refund_transaction_id UUID NOT NULL REFERENCES refund_transactions(id),
    voucher_id UUID NOT NULL REFERENCES vouchers(id),
    user_voucher_id UUID NOT NULL REFERENCES user_vouchers(id),
    source_order_id UUID NOT NULL REFERENCES orders(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(refund_transaction_id)
);

CREATE TABLE IF NOT EXISTS shipment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    event_code VARCHAR(40) NOT NULL CHECK (event_code IN (
        'CONFIRMED', 'PACKED', 'HANDED_TO_CARRIER', 'IN_TRANSIT', 'DELIVERED'
    )),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    shipping_provider VARCHAR(120),
    tracking_code VARCHAR(120),
    source VARCHAR(30) NOT NULL DEFAULT 'INTERNAL',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(order_id, event_code, occurred_at)
);

CREATE TABLE IF NOT EXISTS imei_disposition_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imei_id UUID REFERENCES product_imeis(id),
    serial_id UUID REFERENCES product_serial_numbers(id),
    after_sales_type VARCHAR(20),
    after_sales_id UUID,
    old_status VARCHAR(40),
    new_status VARCHAR(40) NOT NULL CHECK (new_status IN (
        'DEFECTIVE_RETURNED', 'INSPECTION_PENDING', 'RTV_PENDING',
        'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED',
        'SCRAP', 'OUT_OF_SYSTEM'
    )),
    reason TEXT NOT NULL,
    document_reference VARCHAR(160),
    partner_name VARCHAR(255),
    recovery_value NUMERIC(14,2),
    actor_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((imei_id IS NOT NULL) <> (serial_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_return_requests_user_status ON return_requests(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_warranty_requests_user_status ON warranty_requests(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_after_sales_allocations_expiry ON after_sales_allocations(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_after_sales_attachments_cleanup ON after_sales_attachments(status, delete_after);
CREATE INDEX IF NOT EXISTS idx_refund_transactions_user ON refund_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shipment_events_order ON shipment_events(order_id, occurred_at);

ALTER TABLE product_imeis DROP CONSTRAINT IF EXISTS product_imeis_status_check;
ALTER TABLE product_imeis ADD CONSTRAINT product_imeis_status_check CHECK (
    status IN (
        'PENDING_INBOUND',
        'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
        'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING',
        'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED',
        'OUT_OF_SYSTEM'
    )
);

ALTER TABLE product_serial_numbers DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;
ALTER TABLE product_serial_numbers ADD CONSTRAINT product_serial_numbers_status_check CHECK (
    status IN (
        'PENDING_INBOUND',
        'IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
        'RETIRED', 'SCRAP', 'REVERSED', 'DEFECTIVE_RETURNED', 'INSPECTION_PENDING',
        'RTV_PENDING', 'LIQUIDATION_PENDING', 'RTV_COMPLETED', 'LIQUIDATED',
        'OUT_OF_SYSTEM'
    )
);
