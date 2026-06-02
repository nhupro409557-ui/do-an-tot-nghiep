-- ==========================================
-- Migration: 046_product_flat_variants.sql
-- ==========================================

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    -- Drop unique constraint on products(sku) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'products'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'products'::regclass AND attname = 'sku')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE products DROP CONSTRAINT %I', constraint_name);
    END IF;
    
    -- Drop unique constraint on products(slug) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'products'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'products'::regclass AND attname = 'slug')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE products DROP CONSTRAINT %I', constraint_name);
    END IF;

    -- Drop unique constraint on product_variants(sku) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'product_variants'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'product_variants'::regclass AND attname = 'sku')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE product_variants DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE products ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ALTER COLUMN sku DROP NOT NULL;

ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS compare_at_price NUMERIC(14, 2) DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'active';
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS attributes JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_variant_sku
ON product_variants (sku)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_product_sku
ON products (sku)
WHERE deleted_at IS NULL AND sku IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_product_slug
ON products (slug)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_default_variant_per_product
ON product_variants (product_id)
WHERE is_default = true AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_active_variant_attributes
ON product_variants USING GIN (attributes)
WHERE deleted_at IS NULL;
