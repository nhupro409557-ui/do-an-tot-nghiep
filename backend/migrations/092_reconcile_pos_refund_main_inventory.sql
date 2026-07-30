WITH target_order AS (
    SELECT orders.id
    FROM orders
    WHERE orders.order_code = 'EMV7893114386'
      AND orders.status = 'REFUNDED'
      AND orders.payment_status = 'REFUNDED'
      AND EXISTS (
          SELECT 1
          FROM inventory_adjustment_logs adjustment
          WHERE adjustment.reference_code = orders.order_code
            AND adjustment.reason = 'ORDER_CANCELLED_RESTOCK'
      )
      AND NOT EXISTS (
          SELECT 1
          FROM order_history_logs history
          WHERE history.order_id = orders.id
            AND history.note = 'Đối soát tồn MAIN của đơn POS kiểm thử đã hoàn tiền.'
      )
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
    WHERE reservation.status = 'CONSUMED'
      AND level.location_id = reservation.location_id
      AND level.product_id IS NOT DISTINCT FROM reservation.product_id
      AND level.variant_id IS NOT DISTINCT FROM reservation.variant_id
    RETURNING reservation.id
), released_reservation AS (
    UPDATE inventory_reservations reservation
    SET status = 'RELEASED',
        released_at = NOW()
    FROM restored_main restored
    WHERE reservation.id = restored.id
    RETURNING reservation.order_id
)
INSERT INTO order_history_logs (
    id, order_id, old_status, new_status, changed_by, note, metadata
)
SELECT
    gen_random_uuid(),
    released.order_id,
    'REFUNDED',
    'REFUNDED',
    'system-reconciliation',
    'Đối soát tồn MAIN của đơn POS kiểm thử đã hoàn tiền.',
    jsonb_build_object('source', 'POS_TEST_MAIN_RECONCILIATION')
FROM released_reservation released;
