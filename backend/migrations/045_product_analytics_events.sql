CREATE TABLE IF NOT EXISTS product_view_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    session_id VARCHAR(120),
    device_id VARCHAR(160),
    ip_address VARCHAR(80),
    user_agent TEXT,
    source VARCHAR(80),
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    scroll_depth NUMERIC(4, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE product_view_events
    ADD COLUMN IF NOT EXISTS device_id VARCHAR(160),
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS scroll_depth NUMERIC(4, 3) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS product_search_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    normalized_query TEXT NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    session_id VARCHAR(120),
    ip_address VARCHAR(80),
    user_agent TEXT,
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_view_events_product_created
    ON product_view_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_search_events_product_created
    ON product_search_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_search_events_created
    ON product_search_events(created_at DESC);
