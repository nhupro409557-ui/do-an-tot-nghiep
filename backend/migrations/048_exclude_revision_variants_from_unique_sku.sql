-- ==========================================
-- Migration: 048_exclude_revision_variants_from_unique_sku.sql
-- Purpose:
-- - Exclude revision draft variants from the unique SKU constraint.
-- ==========================================

DROP INDEX IF EXISTS idx_unique_active_variant_sku;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_variant_sku
ON product_variants (sku)
WHERE deleted_at IS NULL AND status <> 'revision_draft';
