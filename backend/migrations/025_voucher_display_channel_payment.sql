ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS display_title VARCHAR(120),
    ADD COLUMN IF NOT EXISTS display_description VARCHAR(500),
    ADD COLUMN IF NOT EXISTS public_terms TEXT,
    ADD COLUMN IF NOT EXISTS applicable_channels JSONB NOT NULL DEFAULT '["WEB"]'::jsonb,
    ADD COLUMN IF NOT EXISTS applicable_payment_methods JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_vouchers_applicable_channels ON vouchers USING GIN (applicable_channels);
CREATE INDEX IF NOT EXISTS idx_vouchers_applicable_payment_methods ON vouchers USING GIN (applicable_payment_methods);
