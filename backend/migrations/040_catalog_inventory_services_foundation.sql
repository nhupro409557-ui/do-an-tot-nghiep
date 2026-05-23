-- Catalog inventory, warranty, IMEI, and attached service foundation.
-- The admin UI writes these fields as optional configuration first so existing products keep working.

ALTER TABLE categories
    ADD COLUMN IF NOT EXISTS inventory_policy JSONB NOT NULL DEFAULT '{"inheritImeiPolicy": true, "trackImei": false}'::jsonb;

ALTER TABLE categories
    ADD COLUMN IF NOT EXISTS warranty_policy JSONB NOT NULL DEFAULT '{"inheritWarrantyPolicy": true, "hasWarranty": false, "warrantyMonths": 0, "allowOneForOne": false, "oneForOneDays": 0}'::jsonb;

CREATE TABLE IF NOT EXISTS product_imeis (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    imei VARCHAR(80) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_STOCK',
    source_reference VARCHAR(120),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sold_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    sold_at TIMESTAMPTZ,
    service_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT product_imeis_status_check CHECK (status IN ('IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'RETIRED'))
);

CREATE INDEX IF NOT EXISTS idx_product_imeis_product_variant
    ON product_imeis(product_id, variant_id, status);

CREATE TABLE IF NOT EXISTS attached_services (
    id UUID PRIMARY KEY,
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(180) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    attribute_group VARCHAR(80),
    duration_months INTEGER NOT NULL DEFAULT 0,
    price_mode VARCHAR(30) NOT NULL DEFAULT 'FIXED',
    fixed_price NUMERIC(14, 2) NOT NULL DEFAULT 0,
    percent_value NUMERIC(7, 4) NOT NULL DEFAULT 0,
    base_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT attached_services_type_check CHECK (service_type IN ('PRODUCT_SERVICE', 'SUPPORT_SERVICE')),
    CONSTRAINT attached_services_price_mode_check CHECK (price_mode IN ('FIXED', 'PERCENT', 'TIERED_AMOUNT'))
);

CREATE TABLE IF NOT EXISTS product_attached_services (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES attached_services(id) ON DELETE CASCADE,
    override_price NUMERIC(14, 2),
    PRIMARY KEY (product_id, service_id)
);
