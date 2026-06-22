ALTER TABLE flash_sales
    ADD COLUMN IF NOT EXISTS variant_id UUID NULL REFERENCES product_variants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_flash_sales_variant_active
    ON flash_sales(variant_id, status, starts_at, ends_at)
    WHERE variant_id IS NOT NULL;
