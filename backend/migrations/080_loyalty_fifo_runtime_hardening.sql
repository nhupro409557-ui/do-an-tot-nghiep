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
        WHERE user_id = NEW.user_id AND remaining_points > 0
          AND expired_at IS NULL AND expires_at > NOW()
        ORDER BY expires_at, earned_at, id
        FOR UPDATE
    LOOP
        EXIT WHEN points_left <= 0;
        allocated := LEAST(points_left, lot_row.remaining_points);
        UPDATE loyalty_point_lots SET remaining_points = remaining_points - allocated WHERE id = lot_row.id;
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

DROP TRIGGER IF EXISTS trg_set_loyalty_earn_expiration ON loyalty_transactions;
CREATE TRIGGER trg_set_loyalty_earn_expiration
BEFORE INSERT ON loyalty_transactions
FOR EACH ROW EXECUTE FUNCTION set_loyalty_earn_expiration();

DROP TRIGGER IF EXISTS trg_apply_loyalty_point_lot_fifo ON loyalty_transactions;
CREATE TRIGGER trg_apply_loyalty_point_lot_fifo
AFTER INSERT ON loyalty_transactions
FOR EACH ROW EXECUTE FUNCTION apply_loyalty_point_lot_fifo();
