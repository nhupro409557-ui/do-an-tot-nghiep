ALTER TABLE products
    DROP CONSTRAINT IF EXISTS products_status_check;

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('DRAFT', 'REVISION_DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'DISCONTINUED', 'ARCHIVED', 'MERGED'));
