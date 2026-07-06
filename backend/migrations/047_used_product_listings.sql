ALTER TABLE used_devices
    DROP CONSTRAINT IF EXISTS used_devices_status_check;

ALTER TABLE used_devices
    ADD CONSTRAINT used_devices_status_check
    CHECK (status IN (
        'READY_FOR_PRICING', 'LISTING_DRAFT', 'LISTING_REVIEW',
        'READY_FOR_SALE', 'RESERVED', 'SOLD', 'RETURNED_QC',
        'REPAIRING', 'RETIRED'
    ));

CREATE TABLE IF NOT EXISTS used_device_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL UNIQUE REFERENCES used_devices(id) ON DELETE RESTRICT,
    slug VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
    images JSONB NOT NULL DEFAULT '[]'::jsonb,
    warranty_months INTEGER NOT NULL DEFAULT 0 CHECK (warranty_months BETWEEN 0 AND 36),
    price_comparison_note TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'PUBLISHED', 'HIDDEN', 'SOLD')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_used_device_listings_public
    ON used_device_listings(status, published_at DESC)
    WHERE status = 'PUBLISHED';

CREATE INDEX IF NOT EXISTS idx_used_device_listings_title
    ON used_device_listings USING gin (to_tsvector('simple', title));
