-- Policy management upgrade: rich content metadata, publish scheduling, scoping, versioning, and history.

ALTER TABLE policies
    ADD COLUMN IF NOT EXISTS summary TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS seo_title VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS seo_description VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS seo_keywords VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS scope_type VARCHAR(30) NOT NULL DEFAULT 'GLOBAL',
    ADD COLUMN IF NOT EXISTS product_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS category_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

UPDATE policies
SET status = CASE
        WHEN is_active = TRUE THEN 'PUBLISHED'
        ELSE 'DRAFT'
    END,
    published_at = COALESCE(published_at, updated_at),
    version = COALESCE(version, 1)
WHERE status IS NULL
   OR published_at IS NULL
   OR version IS NULL;

CREATE TABLE IF NOT EXISTS policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    action VARCHAR(30) NOT NULL DEFAULT 'UPDATED',
    snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_policy_versions_policy_version
    ON policy_versions(policy_id, version_number);

CREATE INDEX IF NOT EXISTS idx_policies_status_publish
    ON policies(status, is_active, scheduled_at, published_at);

CREATE INDEX IF NOT EXISTS idx_policy_versions_policy_created
    ON policy_versions(policy_id, created_at DESC);
