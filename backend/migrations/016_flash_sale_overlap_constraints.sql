CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE flash_sales
    ADD CONSTRAINT exclude_overlapping_product_flash_sales
    EXCLUDE USING gist (
        product_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    )
    WHERE (status = 'ACTIVE' AND variant_id IS NULL);

ALTER TABLE flash_sales
    ADD CONSTRAINT exclude_overlapping_variant_flash_sales
    EXCLUDE USING gist (
        variant_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    )
    WHERE (status = 'ACTIVE' AND variant_id IS NOT NULL);
