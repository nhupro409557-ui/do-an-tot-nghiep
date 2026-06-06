ALTER TABLE products
    ADD COLUMN IF NOT EXISTS hidden_by_category BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS hidden_by_brand BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_products_inherited_visibility
    ON products(hidden_by_category, hidden_by_brand, status);
