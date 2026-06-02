BEGIN;

ALTER TABLE user_favorites
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE user_favorites
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS user_favorite_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('LIKE', 'UNLIKE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO user_favorite_events (user_id, product_id, action, created_at)
SELECT uf.user_id, uf.product_id, 'LIKE', uf.created_at
FROM user_favorites uf
WHERE NOT EXISTS (
    SELECT 1
    FROM user_favorite_events ufe
    WHERE ufe.user_id = uf.user_id
      AND ufe.product_id = uf.product_id
      AND ufe.action = 'LIKE'
      AND ufe.created_at = uf.created_at
);

CREATE INDEX IF NOT EXISTS idx_user_favorite_events_product_time
ON user_favorite_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_favorite_events_user_product_time
ON user_favorite_events(user_id, product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_favorites_active_product
ON user_favorites(product_id)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_user_favorites_active_user
ON user_favorites(user_id)
WHERE is_active = TRUE;

COMMIT;
