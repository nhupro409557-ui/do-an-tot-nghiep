CREATE TABLE IF NOT EXISTS product_image_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_name VARCHAR(120) NOT NULL,
    body TEXT NOT NULL,
    parent_id UUID REFERENCES product_image_comments(id) ON DELETE CASCADE,
    reply_to_user_name VARCHAR(120),
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    is_retracted BOOLEAN NOT NULL DEFAULT FALSE,
    moderation_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_image_comments_product_id ON product_image_comments(product_id);
CREATE INDEX IF NOT EXISTS idx_product_image_comments_parent_id ON product_image_comments(parent_id);
