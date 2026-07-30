ALTER TABLE payment_transactions
    DROP CONSTRAINT IF EXISTS payment_transactions_status_check;

ALTER TABLE payment_transactions
    ADD CONSTRAINT payment_transactions_status_check
    CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'EXPIRED', 'REFUNDED', 'PAID_LATE'));
