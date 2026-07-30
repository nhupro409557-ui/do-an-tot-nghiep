WITH target_order AS (
    SELECT orders.id, orders.user_id, orders.status
    FROM orders
    WHERE orders.order_code = 'EMV8811835848'
      AND orders.internal_note = '[POS] TEST-LINK-ADMIN-20260713'
      AND orders.status = 'COMPLETED'
      AND NOT EXISTS (
          SELECT 1
          FROM order_history_logs history
          WHERE history.order_id = orders.id
            AND history.note = 'Hoàn tác đơn POS dùng để kiểm thử liên kết tài khoản.'
      )
      AND NOT EXISTS (
          SELECT 1
          FROM inventory_adjustment_logs adjustment
          WHERE adjustment.reference_code = orders.order_code
            AND adjustment.reason = 'ORDER_SHIPPED'
      )
    FOR UPDATE
), earned_points AS (
    SELECT earn_tx.id, earn_tx.user_id, earn_tx.order_id, earn_tx.points
    FROM loyalty_transactions earn_tx
    JOIN target_order target ON target.id = earn_tx.order_id
    WHERE earn_tx.type = 'EARN'
      AND NOT EXISTS (
          SELECT 1
          FROM loyalty_transactions revoke
          WHERE revoke.order_id = earn_tx.order_id
            AND revoke.type = 'REVOKE'
      )
), locked_user AS (
    SELECT users.id, users.loyalty_points_balance
    FROM users
    JOIN earned_points earned ON earned.user_id = users.id
    FOR UPDATE
), restored_main AS (
    UPDATE inventory_levels level
    SET on_hand_quantity = level.on_hand_quantity + reservation.reserved_quantity,
        updated_at = NOW()
    FROM inventory_reservations reservation
    JOIN inventory_locations location
      ON location.id = reservation.location_id
     AND location.code = 'MAIN'
    JOIN target_order target
      ON target.id = reservation.order_id
    WHERE level.location_id = reservation.location_id
      AND level.product_id IS NOT DISTINCT FROM reservation.product_id
      AND level.variant_id IS NOT DISTINCT FROM reservation.variant_id
      AND reservation.status = 'CONSUMED'
    RETURNING reservation.id
), released_reservation AS (
    UPDATE inventory_reservations reservation
    SET status = 'RELEASED',
        released_at = NOW()
    FROM restored_main restored
    WHERE reservation.id = restored.id
    RETURNING reservation.id
), revoke_transaction AS (
    INSERT INTO loyalty_transactions (
        id, user_id, order_id, type, points,
        balance_before, balance_after, reason, metadata
    )
    SELECT
        gen_random_uuid(),
        earned.user_id,
        earned.order_id,
        'REVOKE',
        earned.points,
        locked.loyalty_points_balance,
        GREATEST(locked.loyalty_points_balance - earned.points, 0),
        'Thu hồi điểm của đơn POS dùng để kiểm thử liên kết tài khoản.',
        jsonb_build_object('source', 'POS_TEST_RECONCILIATION')
    FROM earned_points earned
    JOIN locked_user locked ON locked.id = earned.user_id
    RETURNING user_id, order_id, points, balance_after
), updated_user AS (
    UPDATE users
    SET loyalty_points_balance = revoke.balance_after,
        updated_at = NOW()
    FROM revoke_transaction revoke
    WHERE users.id = revoke.user_id
    RETURNING users.id
), updated_order AS (
    UPDATE orders
    SET status = 'REFUNDED',
        payment_status = 'REFUNDED',
        shipping_fee = 0,
        total_amount = GREATEST(subtotal_amount - discount_amount, 0),
        refunded_at = NOW(),
        cancellation_reason = 'Hoàn tác đơn POS dùng để kiểm thử liên kết tài khoản.',
        updated_at = NOW()
    FROM target_order target
    WHERE orders.id = target.id
    RETURNING orders.id, target.status AS old_status
)
INSERT INTO order_history_logs (
    id, order_id, old_status, new_status, changed_by, note, metadata
)
SELECT
    gen_random_uuid(),
    updated.id,
    updated.old_status,
    'REFUNDED',
    'system-reconciliation',
    'Hoàn tác đơn POS dùng để kiểm thử liên kết tài khoản.',
    jsonb_build_object('source', 'POS_TEST_RECONCILIATION')
FROM updated_order updated;
