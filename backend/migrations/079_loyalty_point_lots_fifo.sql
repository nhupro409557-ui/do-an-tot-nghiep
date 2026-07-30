CREATE TABLE IF NOT EXISTS loyalty_point_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_transaction_id UUID NOT NULL UNIQUE REFERENCES loyalty_transactions(id) ON DELETE CASCADE,
    original_points INTEGER NOT NULL CHECK (original_points > 0),
    remaining_points INTEGER NOT NULL CHECK (remaining_points >= 0 AND remaining_points <= original_points),
    earned_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    expired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loyalty_point_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES loyalty_transactions(id) ON DELETE CASCADE,
    lot_id UUID NOT NULL REFERENCES loyalty_point_lots(id) ON DELETE CASCADE,
    points INTEGER NOT NULL CHECK (points > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (transaction_id, lot_id)
);

CREATE INDEX IF NOT EXISTS idx_loyalty_point_lots_fifo
    ON loyalty_point_lots (user_id, expires_at, earned_at)
    WHERE remaining_points > 0 AND expired_at IS NULL;

INSERT INTO loyalty_point_lots
    (user_id, source_transaction_id, original_points, remaining_points, earned_at, expires_at)
SELECT lt.user_id, lt.id, lt.points, 0, lt.created_at,
       COALESCE(lt.expires_at, (
           date_trunc('month', lt.created_at AT TIME ZONE 'Asia/Bangkok') + INTERVAL '6 months'
       ) AT TIME ZONE 'Asia/Bangkok')
FROM loyalty_transactions lt
WHERE lt.type IN ('EARN', 'REFUND')
   OR (lt.type = 'ADJUST' AND COALESCE((lt.metadata->>'delta')::integer, 0) > 0)
ON CONFLICT (source_transaction_id) DO NOTHING;

WITH ranked AS (
    SELECT l.id,
           LEAST(
               l.original_points,
               GREATEST(
                   u.loyalty_points_balance - COALESCE(
                       SUM(l.original_points) OVER (
                           PARTITION BY l.user_id
                           ORDER BY l.expires_at DESC, l.earned_at DESC, l.id DESC
                           ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                       ), 0
                   ), 0
               )
           )::integer AS remaining
    FROM loyalty_point_lots l
    JOIN users u ON u.id = l.user_id
)
UPDATE loyalty_point_lots l
SET remaining_points = ranked.remaining
FROM ranked
WHERE l.id = ranked.id;

CREATE OR REPLACE FUNCTION apply_loyalty_point_lot_fifo()
RETURNS TRIGGER AS $$
DECLARE
    points_left INTEGER;
    lot_row RECORD;
    allocated INTEGER;
    lot_expiration TIMESTAMPTZ;
BEGIN
    IF NEW.type IN ('EARN', 'REFUND')
       OR (NEW.type = 'ADJUST' AND COALESCE((NEW.metadata->>'delta')::integer, 0) > 0) THEN
        lot_expiration := (
            date_trunc('month', COALESCE(NEW.created_at, NOW()) AT TIME ZONE 'Asia/Bangkok')
            + INTERVAL '6 months'
        ) AT TIME ZONE 'Asia/Bangkok';
        INSERT INTO loyalty_point_lots
            (user_id, source_transaction_id, original_points, remaining_points, earned_at, expires_at)
        VALUES
            (NEW.user_id, NEW.id, NEW.points, NEW.points, COALESCE(NEW.created_at, NOW()), lot_expiration)
        ON CONFLICT (source_transaction_id) DO NOTHING;
        RETURN NEW;
    END IF;

    IF NEW.type NOT IN ('REDEEM', 'REVOKE')
       AND NOT (NEW.type = 'ADJUST' AND COALESCE((NEW.metadata->>'delta')::integer, 0) < 0) THEN
        RETURN NEW;
    END IF;

    points_left := NEW.points;
    FOR lot_row IN
        SELECT id, remaining_points
        FROM loyalty_point_lots
        WHERE user_id = NEW.user_id
          AND remaining_points > 0
          AND expired_at IS NULL
          AND expires_at > NOW()
        ORDER BY expires_at, earned_at, id
        FOR UPDATE
    LOOP
        EXIT WHEN points_left <= 0;
        allocated := LEAST(points_left, lot_row.remaining_points);
        UPDATE loyalty_point_lots
        SET remaining_points = remaining_points - allocated
        WHERE id = lot_row.id;
        INSERT INTO loyalty_point_allocations (transaction_id, lot_id, points)
        VALUES (NEW.id, lot_row.id, allocated)
        ON CONFLICT (transaction_id, lot_id) DO UPDATE
        SET points = loyalty_point_allocations.points + EXCLUDED.points;
        points_left := points_left - allocated;
    END LOOP;
    IF points_left > 0 THEN
        RAISE EXCEPTION 'Số dư lô điểm không đủ để phân bổ FIFO (thiếu % điểm).', points_left;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_apply_loyalty_point_lot_fifo ON loyalty_transactions;
CREATE TRIGGER trg_apply_loyalty_point_lot_fifo
AFTER INSERT ON loyalty_transactions
FOR EACH ROW EXECUTE FUNCTION apply_loyalty_point_lot_fifo();
