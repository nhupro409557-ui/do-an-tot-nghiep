BEGIN;

ALTER TABLE report_export_jobs
    ADD COLUMN IF NOT EXISTS claim_token UUID,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

UPDATE report_export_jobs
SET status = CASE
        WHEN status = 'PROCESSING' THEN 'PENDING'
        ELSE status
    END,
    claimed_at = NULL,
    claim_token = NULL,
    heartbeat_at = NULL,
    next_attempt_at = CASE
        WHEN status = 'PROCESSING' THEN NOW()
        ELSE next_attempt_at
    END,
    updated_at = NOW()
WHERE status = 'PROCESSING'
   OR claimed_at IS NOT NULL
   OR claim_token IS NOT NULL
   OR heartbeat_at IS NOT NULL;

ALTER TABLE report_export_jobs
    DROP CONSTRAINT IF EXISTS report_export_jobs_lease_state_check;

ALTER TABLE report_export_jobs
    ADD CONSTRAINT report_export_jobs_lease_state_check
    CHECK (
        (
            status = 'PROCESSING'
            AND claim_token IS NOT NULL
            AND heartbeat_at IS NOT NULL
            AND claimed_at IS NOT NULL
        )
        OR
        (
            status <> 'PROCESSING'
            AND claim_token IS NULL
            AND heartbeat_at IS NULL
            AND claimed_at IS NULL
        )
    );

CREATE INDEX IF NOT EXISTS idx_report_export_jobs_stale_lease
    ON report_export_jobs(heartbeat_at)
    WHERE status = 'PROCESSING';

COMMIT;
