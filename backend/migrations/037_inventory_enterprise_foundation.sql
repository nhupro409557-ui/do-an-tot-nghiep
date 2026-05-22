-- Enterprise inventory foundation
-- This migration is intentionally non-breaking: it introduces normalized tables
-- for future multi-warehouse and approval workflows without removing the current
-- single-stock-column runtime yet.

CREATE TABLE IF NOT EXISTS inventory_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    location_type VARCHAR(30) NOT NULL DEFAULT 'WAREHOUSE'
        CHECK (location_type IN ('WAREHOUSE', 'BRANCH', 'VIRTUAL', 'RETURNS')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    address TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO inventory_locations (code, name, location_type, status, is_default)
VALUES ('MAIN', 'Kho mac dinh', 'WAREHOUSE', 'ACTIVE', TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    location_type = EXCLUDED.location_type,
    status = EXCLUDED.status;

CREATE TABLE IF NOT EXISTS inventory_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    on_hand_quantity INTEGER NOT NULL DEFAULT 0 CHECK (on_hand_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    safety_stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (safety_stock_quantity >= 0),
    reorder_point_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reorder_point_quantity >= 0),
    average_unit_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (average_unit_cost >= 0),
    last_counted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_levels_item_check CHECK (num_nonnulls(product_id, variant_id) = 1),
    CONSTRAINT inventory_levels_reserved_le_on_hand CHECK (reserved_quantity <= on_hand_quantity)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_location
    ON inventory_levels(product_id, location_id)
    WHERE variant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_variant_location
    ON inventory_levels(variant_id, location_id)
    WHERE product_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_levels_location_id
    ON inventory_levels(location_id);

CREATE TABLE IF NOT EXISTS inventory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(80) NOT NULL UNIQUE,
    document_type VARCHAR(30) NOT NULL
        CHECK (document_type IN ('INBOUND', 'OUTBOUND', 'ADJUSTMENT', 'COUNT', 'REVERSAL', 'TRANSFER', 'RESERVATION_RELEASE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'POSTED', 'CANCELLED')),
    source_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    target_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    supplier_name VARCHAR(160),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_status_type
    ON inventory_documents(status, document_type, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_document_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES inventory_documents(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    requested_quantity INTEGER NOT NULL DEFAULT 0 CHECK (requested_quantity >= 0),
    approved_quantity INTEGER CHECK (approved_quantity IS NULL OR approved_quantity >= 0),
    expected_quantity INTEGER CHECK (expected_quantity IS NULL OR expected_quantity >= 0),
    counted_quantity INTEGER CHECK (counted_quantity IS NULL OR counted_quantity >= 0),
    variance_quantity INTEGER,
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    note TEXT,
    CONSTRAINT inventory_document_lines_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_document_lines_document_id
    ON inventory_document_lines(document_id);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    movement_type VARCHAR(30) NOT NULL
        CHECK (movement_type IN ('IN', 'OUT', 'ADJUST', 'COUNT_POST', 'REVERSAL', 'RESERVE', 'RELEASE')),
    quantity INTEGER NOT NULL CHECK (quantity <> 0),
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    total_cost NUMERIC(14, 2) CHECK (total_cost IS NULL OR total_cost >= 0),
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    balance_after INTEGER CHECK (balance_after IS NULL OR balance_after >= 0),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_transactions_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item_location_created_at
    ON inventory_transactions(variant_id, product_id, location_id, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    reservation_code VARCHAR(120) NOT NULL UNIQUE,
    reserved_quantity INTEGER NOT NULL CHECK (reserved_quantity > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'CONSUMED', 'RELEASED', 'EXPIRED', 'CANCELLED')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    CONSTRAINT inventory_reservations_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_reservations_status_expires_at
    ON inventory_reservations(status, expires_at);

-- Backfill current single-warehouse balances into MAIN for compatibility mode.
INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    p.id,
    NULL,
    il.id,
    p.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM products p
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    NULL,
    pv.id,
    il.id,
    pv.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM product_variants pv
JOIN products p ON p.id = pv.product_id
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (code, module, description)
VALUES
    ('inventory:approve', 'inventory', 'Duyet phieu nghiep vu kho'),
    ('inventory:count', 'inventory', 'Tao va doi soat phieu kiem ke kho'),
    ('inventory:reserve', 'inventory', 'Quan ly giu cho ton kho')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('inventory:approve', 'inventory:count', 'inventory:reserve')
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;
