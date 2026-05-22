-- Review resilience and user controls
-- Adds ownership-friendly edit/delete support, review time window metadata, and denormalized rating sync.

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS order_id UUID REFERENCES orders(id);

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS review_window_expires_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_product_reviews_user_product ON product_reviews(user_id, product_id);

UPDATE products p
SET
    rating = stats.rating,
    review_count = stats.review_count,
    updated_at = NOW()
FROM (
    SELECT
        product_id,
        ROUND(AVG(rating) FILTER (WHERE status = 'PUBLISHED'), 2)::numeric(3, 2) AS rating,
        COUNT(*) FILTER (WHERE status = 'PUBLISHED') AS review_count
    FROM product_reviews
    GROUP BY product_id
) stats
WHERE p.id = stats.product_id;
