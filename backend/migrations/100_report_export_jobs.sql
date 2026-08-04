CREATE TABLE IF NOT EXISTS report_export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    report_type VARCHAR(30) NOT NULL
        CHECK (report_type IN ('revenue', 'orders', 'customers')),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_rows INTEGER NOT NULL DEFAULT 0,
    file_path TEXT,
    filename TEXT,
    expires_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_export_jobs_requester_created
    ON report_export_jobs(requested_by, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_export_jobs_expiry
    ON report_export_jobs(expires_at)
    WHERE status = 'COMPLETED';
