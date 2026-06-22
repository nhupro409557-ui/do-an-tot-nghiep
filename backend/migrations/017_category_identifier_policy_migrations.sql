CREATE TABLE IF NOT EXISTS inventory_policy_migrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    identifier_type VARCHAR(10) NOT NULL CHECK (identifier_type IN ('IMEI', 'SERIAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    target_inventory_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    affected_product_count INTEGER NOT NULL DEFAULT 0,
    required_identifier_count INTEGER NOT NULL DEFAULT 0,
    staged_identifier_count INTEGER NOT NULL DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    completed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_policy_migration_active
    ON inventory_policy_migrations(category_id, identifier_type)
    WHERE status IN ('PENDING', 'IN_PROGRESS');

CREATE TABLE IF NOT EXISTS inventory_policy_migration_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_id UUID NOT NULL REFERENCES inventory_policy_migrations(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(255),
    physical_stock INTEGER NOT NULL DEFAULT 0 CHECK (physical_stock >= 0),
    existing_identifier_count INTEGER NOT NULL DEFAULT 0 CHECK (existing_identifier_count >= 0),
    required_identifier_count INTEGER NOT NULL DEFAULT 0 CHECK (required_identifier_count >= 0),
    staged_identifier_count INTEGER NOT NULL DEFAULT 0 CHECK (staged_identifier_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (migration_id, product_id, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_policy_migration_lines_migration
    ON inventory_policy_migration_lines(migration_id);

CREATE TABLE IF NOT EXISTS inventory_policy_migration_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_id UUID NOT NULL REFERENCES inventory_policy_migrations(id) ON DELETE CASCADE,
    line_id UUID NOT NULL REFERENCES inventory_policy_migration_lines(id) ON DELETE CASCADE,
    identifier_value VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'STAGED'
        CHECK (status IN ('STAGED', 'ACTIVATED', 'CANCELLED')),
    scanned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    UNIQUE (migration_id, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_inventory_policy_migration_identifiers_line
    ON inventory_policy_migration_identifiers(line_id, status);
