CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY,
    public_url VARCHAR(1024) UNIQUE NOT NULL,
    file_key VARCHAR(1024) NOT NULL,
    folder VARCHAR(100) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INT NOT NULL,
    associated_entity_type VARCHAR(100),
    associated_entity_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_assets_public_url ON media_assets(public_url);
