ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS include_brand_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS exclude_brand_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
