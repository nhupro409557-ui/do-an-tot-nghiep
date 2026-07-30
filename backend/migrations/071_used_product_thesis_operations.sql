ALTER TABLE used_device_intake_requests
    ALTER COLUMN product_id DROP NOT NULL;

ALTER TABLE used_device_intake_requests
    ADD COLUMN IF NOT EXISTS external_product_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS seller_address VARCHAR(500),
    ADD COLUMN IF NOT EXISTS seller_identity_number VARCHAR(30),
    ADD COLUMN IF NOT EXISTS ownership_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS acquisition_payment_method VARCHAR(30),
    ADD COLUMN IF NOT EXISTS acquisition_payment_reference VARCHAR(120),
    ADD COLUMN IF NOT EXISTS acquisition_paid_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS seller_confirmed_at TIMESTAMPTZ;

ALTER TABLE used_device_intake_requests
    DROP CONSTRAINT IF EXISTS used_intake_product_source_check;

ALTER TABLE used_device_intake_requests
    ADD CONSTRAINT used_intake_product_source_check
    CHECK (product_id IS NOT NULL OR NULLIF(BTRIM(external_product_name), '') IS NOT NULL);

ALTER TABLE used_device_intake_requests
    DROP CONSTRAINT IF EXISTS used_intake_payment_method_check;

ALTER TABLE used_device_intake_requests
    ADD CONSTRAINT used_intake_payment_method_check
    CHECK (
        acquisition_payment_method IS NULL
        OR acquisition_payment_method IN ('CASH', 'BANK_TRANSFER', 'TRADE_IN_CREDIT')
    );

ALTER TABLE used_devices
    ALTER COLUMN product_id DROP NOT NULL;

ALTER TABLE used_devices
    ADD COLUMN IF NOT EXISTS external_product_name VARCHAR(255);

CREATE TABLE IF NOT EXISTS used_device_repairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES used_devices(id) ON DELETE CASCADE,
    description VARCHAR(1000) NOT NULL,
    cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (cost >= 0),
    repaired_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_used_device_repairs_device_date
    ON used_device_repairs(device_id, repaired_at DESC, created_at DESC);
