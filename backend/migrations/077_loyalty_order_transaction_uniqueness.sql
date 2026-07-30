CREATE UNIQUE INDEX IF NOT EXISTS uq_loyalty_transactions_order_event
    ON loyalty_transactions (order_id, type)
    WHERE order_id IS NOT NULL
      AND type IN ('EARN', 'REDEEM', 'REFUND', 'REVOKE');
