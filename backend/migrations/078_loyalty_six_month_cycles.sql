ALTER TABLE users
    ADD COLUMN IF NOT EXISTS loyalty_tier_period_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS loyalty_tier_period_ends_at TIMESTAMPTZ;

UPDATE users
SET loyalty_tier_period_started_at = COALESCE(
        loyalty_tier_period_started_at,
        CASE
            WHEN EXTRACT(MONTH FROM (NOW() AT TIME ZONE 'Asia/Bangkok')) <= 6
                THEN date_trunc('year', NOW() AT TIME ZONE 'Asia/Bangkok') AT TIME ZONE 'Asia/Bangkok'
            ELSE (date_trunc('year', NOW() AT TIME ZONE 'Asia/Bangkok') + INTERVAL '6 months') AT TIME ZONE 'Asia/Bangkok'
        END
    ),
    loyalty_tier_period_ends_at = COALESCE(
        loyalty_tier_period_ends_at,
        CASE
            WHEN EXTRACT(MONTH FROM (NOW() AT TIME ZONE 'Asia/Bangkok')) <= 6
                THEN (date_trunc('year', NOW() AT TIME ZONE 'Asia/Bangkok') + INTERVAL '6 months') AT TIME ZONE 'Asia/Bangkok'
            ELSE (date_trunc('year', NOW() AT TIME ZONE 'Asia/Bangkok') + INTERVAL '1 year') AT TIME ZONE 'Asia/Bangkok'
        END
    );

ALTER TABLE users
    ALTER COLUMN loyalty_tier_period_started_at SET NOT NULL,
    ALTER COLUMN loyalty_tier_period_ends_at SET NOT NULL;

ALTER TABLE loyalty_transactions
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS expired_at TIMESTAMPTZ;

ALTER TABLE loyalty_transactions DROP CONSTRAINT IF EXISTS loyalty_transactions_type_check;
ALTER TABLE loyalty_transactions ADD CONSTRAINT loyalty_transactions_type_check
    CHECK (type IN ('EARN', 'REDEEM', 'REFUND', 'REVOKE', 'EXPIRE', 'ADJUST'));

UPDATE loyalty_transactions
SET expires_at = (
    date_trunc('month', created_at AT TIME ZONE 'Asia/Bangkok') + INTERVAL '6 months'
) AT TIME ZONE 'Asia/Bangkok'
WHERE type = 'EARN';

CREATE OR REPLACE FUNCTION set_loyalty_earn_expiration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.type = 'EARN' AND NEW.expires_at IS NULL THEN
        NEW.expires_at := (
            date_trunc('month', COALESCE(NEW.created_at, NOW()) AT TIME ZONE 'Asia/Bangkok')
            + INTERVAL '6 months'
        ) AT TIME ZONE 'Asia/Bangkok';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_loyalty_earn_expiration ON loyalty_transactions;
CREATE TRIGGER trg_set_loyalty_earn_expiration
BEFORE INSERT ON loyalty_transactions
FOR EACH ROW EXECUTE FUNCTION set_loyalty_earn_expiration();

CREATE INDEX IF NOT EXISTS idx_loyalty_earn_expiration
    ON loyalty_transactions (expires_at)
    WHERE type = 'EARN' AND expired_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_loyalty_tier_period_end
    ON users (loyalty_tier_period_ends_at)
    WHERE loyalty_wallet_status = 'ACTIVE';
