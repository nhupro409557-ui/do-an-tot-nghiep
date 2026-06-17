-- Add serial number tracking parallel to IMEI tracking.

UPDATE categories
SET inventory_policy = COALESCE(inventory_policy, '{}'::jsonb)
    || jsonb_build_object(
        'inheritSerialPolicy', COALESCE((inventory_policy->>'inheritSerialPolicy')::boolean, TRUE),
        'trackSerialNumber', COALESCE((inventory_policy->>'trackSerialNumber')::boolean, FALSE)
    )
WHERE NOT (COALESCE(inventory_policy, '{}'::jsonb) ? 'trackSerialNumber');

CREATE TABLE IF NOT EXISTS product_serial_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    serial_number VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_STOCK',
    source_reference VARCHAR(120),
    service_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ,
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT product_serial_numbers_status_check CHECK (
        status IN ('IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY', 'RETIRED', 'SCRAP')
    )
);

CREATE INDEX IF NOT EXISTS idx_product_serial_numbers_product_variant
    ON product_serial_numbers(product_id, variant_id, status);
