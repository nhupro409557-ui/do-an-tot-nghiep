-- ==========================================
-- Migration: 047_enterprise_product_revision_merge.sql
-- Purpose:
-- - Preserve variant lineage through product revisions.
-- - Preserve order item variant references for audit/inventory-safe merge.
-- ==========================================

ALTER TABLE product_variants
ADD COLUMN IF NOT EXISTS parent_variant_id UUID NULL REFERENCES product_variants(id);

ALTER TABLE order_items
ADD COLUMN IF NOT EXISTS variant_id UUID NULL REFERENCES product_variants(id);

CREATE INDEX IF NOT EXISTS idx_product_variants_parent_variant_id
ON product_variants (parent_variant_id)
WHERE parent_variant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_order_items_variant_id
ON order_items (variant_id)
WHERE variant_id IS NOT NULL;

