ALTER TABLE report_export_jobs
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

ALTER TABLE report_export_jobs
    DROP CONSTRAINT IF EXISTS report_export_jobs_status_check;

ALTER TABLE report_export_jobs
    ADD CONSTRAINT report_export_jobs_status_check
    CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'EXPIRED'));

CREATE INDEX IF NOT EXISTS idx_report_export_jobs_worker_queue
    ON report_export_jobs(status, next_attempt_at, created_at)
    WHERE status IN ('PENDING', 'PROCESSING');
