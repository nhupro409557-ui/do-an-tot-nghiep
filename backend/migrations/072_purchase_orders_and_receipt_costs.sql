CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY,
    code VARCHAR(120) NOT NULL UNIQUE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'PARTIALLY_RECEIVED', 'COMPLETED', 'CANCELLED')),
    expected_date DATE,
    note VARCHAR(500),
    discount_amount NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_fee NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (shipping_fee >= 0),
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id UUID PRIMARY KEY,
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    variant_id UUID REFERENCES product_variants(id),
    ordered_quantity INTEGER NOT NULL CHECK (ordered_quantity > 0),
    received_quantity INTEGER NOT NULL DEFAULT 0 CHECK (received_quantity >= 0),
    unit_cost NUMERIC(14,2) NOT NULL CHECK (unit_cost > 0),
    note VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT purchase_order_line_received_limit CHECK (received_quantity <= ordered_quantity),
    CONSTRAINT purchase_order_line_unique_item UNIQUE (purchase_order_id, product_id, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_status
    ON purchase_orders(supplier_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_purchase_order_lines_order
    ON purchase_order_lines(purchase_order_id);

