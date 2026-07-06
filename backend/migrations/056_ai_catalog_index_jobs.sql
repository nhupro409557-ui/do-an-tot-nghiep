CREATE TABLE IF NOT EXISTS ai_catalog_index_jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    step TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    output_tail TEXT NOT NULL DEFAULT '',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_catalog_index_jobs_status_check
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_ai_catalog_index_jobs_started_at
    ON ai_catalog_index_jobs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_catalog_index_jobs_status
    ON ai_catalog_index_jobs (status);
