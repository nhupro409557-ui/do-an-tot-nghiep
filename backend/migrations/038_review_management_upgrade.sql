-- Review management upgrade
-- Adds moderation, media attachments, shop replies, reporting, and anti-spam support.

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS media_urls JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS moderation_note TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_reply TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_replied_by UUID REFERENCES users(id);

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_replied_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS flagged_reason TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS is_spam BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS spam_reason TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE product_reviews
SET status = 'PENDING'
WHERE status IS NULL;

ALTER TABLE product_reviews
    DROP CONSTRAINT IF EXISTS product_reviews_status_check;

ALTER TABLE product_reviews
    ADD CONSTRAINT product_reviews_status_check
    CHECK (status IN ('PENDING', 'PUBLISHED', 'HIDDEN', 'REJECTED'));

CREATE INDEX IF NOT EXISTS idx_product_reviews_status ON product_reviews(status);
CREATE INDEX IF NOT EXISTS idx_product_reviews_product_status ON product_reviews(product_id, status);
