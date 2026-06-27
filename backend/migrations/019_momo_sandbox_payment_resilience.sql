ALTER TABLE payment_transactions
    DROP CONSTRAINT IF EXISTS payment_transactions_status_check;

ALTER TABLE payment_transactions
    ADD CONSTRAINT payment_transactions_status_check
    CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'EXPIRED', 'REFUNDED'));

ALTER TABLE payment_transactions
    ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_transactions_order_attempt
    ON payment_transactions(order_id, attempt_number);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_pending_expiry
    ON payment_transactions(status, expires_at);

CREATE TABLE IF NOT EXISTS payment_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(30) NOT NULL,
    event_key VARCHAR(255) NOT NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    payment_transaction_id UUID REFERENCES payment_transactions(id) ON DELETE SET NULL,
    signature_valid BOOLEAN NOT NULL DEFAULT FALSE,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED'
        CHECK (processing_status IN ('RECEIVED', 'PROCESSED', 'IGNORED', 'FAILED')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_webhook_events_provider_key UNIQUE (provider, event_key)
);

CREATE INDEX IF NOT EXISTS idx_payment_webhook_events_order_id
    ON payment_webhook_events(order_id);

