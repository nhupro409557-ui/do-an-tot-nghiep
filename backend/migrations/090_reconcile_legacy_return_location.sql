WITH correction_target AS (
    SELECT
        level.id AS inventory_level_id,
        line.product_id,
        line.variant_id,
        location.code AS location_code,
        location.name AS location_name,
        level.on_hand_quantity AS old_quantity
    FROM orders order_record
    JOIN inventory_documents document
      ON document.order_id = order_record.id
     AND document.document_type = 'OUTBOUND'
     AND document.status = 'COMPLETED'
    JOIN inventory_document_lines line
      ON line.document_id = document.id
    JOIN inventory_locations location
      ON location.id = line.location_id
    JOIN inventory_levels level
      ON level.product_id = line.product_id
     AND level.variant_id IS NOT DISTINCT FROM line.variant_id
     AND level.location_id = line.location_id
    JOIN products product
      ON product.id = line.product_id
    JOIN inventory_levels main_level
      ON main_level.product_id = line.product_id
     AND main_level.variant_id IS NOT DISTINCT FROM line.variant_id
    JOIN inventory_locations main_location
      ON main_location.id = main_level.location_id
     AND main_location.code = 'MAIN'
    WHERE order_record.order_code = 'EMV0556172950'
      AND order_record.status = 'RETURNED'
      AND document.document_no = 'OUT-EMV0556172950'
      AND location.code = 'B-01-04'
      AND line.product_id = '68249ddf-5a94-47b6-b3b3-a65adffe8891'::uuid
      AND line.approved_quantity = 1
      AND product.stock_quantity = main_level.on_hand_quantity
      AND product.stock_quantity = level.on_hand_quantity + 1
      AND EXISTS (
          SELECT 1
          FROM inventory_adjustment_logs outbound_log
          WHERE outbound_log.product_id = line.product_id
            AND outbound_log.variant_id IS NOT DISTINCT FROM line.variant_id
            AND outbound_log.reference_code = 'OUT-EMV0556172950'
            AND outbound_log.location_code = 'B-01-04'
            AND outbound_log.delta = -1
      )
      AND EXISTS (
          SELECT 1
          FROM inventory_adjustment_logs restock_log
          WHERE restock_log.product_id = line.product_id
            AND restock_log.variant_id IS NOT DISTINCT FROM line.variant_id
            AND restock_log.reference_code = 'EMV0556172950'
            AND restock_log.reason = 'ORDER_CANCELLED_RESTOCK'
            AND restock_log.location_code IS NULL
            AND restock_log.delta = 1
      )
      AND NOT EXISTS (
          SELECT 1
          FROM inventory_adjustment_logs correction_log
          WHERE correction_log.reference_code = 'RECON-EMV0556172950-B-01-04'
            AND correction_log.product_id = line.product_id
            AND correction_log.variant_id IS NOT DISTINCT FROM line.variant_id
      )
    FOR UPDATE OF level
), updated_level AS (
    UPDATE inventory_levels level
    SET on_hand_quantity = target.old_quantity + 1,
        updated_at = NOW()
    FROM correction_target target
    WHERE level.id = target.inventory_level_id
    RETURNING
        target.product_id,
        target.variant_id,
        target.location_code,
        target.location_name,
        target.old_quantity,
        level.on_hand_quantity AS new_quantity
)
INSERT INTO inventory_adjustment_logs (
    id,
    product_id,
    variant_id,
    old_quantity,
    new_quantity,
    delta,
    reason,
    note,
    location_code,
    location_name,
    reference_code,
    transaction_type
)
SELECT
    gen_random_uuid(),
    product_id,
    variant_id,
    old_quantity,
    new_quantity,
    1,
    'LEGACY_RETURN_LOCATION_RECONCILED',
    'Khôi phục đúng kệ cho hàng hoàn của đơn EMV0556172950; tổng tồn và lô đã được cộng ở luồng cũ nên không điều chỉnh lại.',
    location_code,
    location_name,
    'RECON-EMV0556172950-B-01-04',
    'RETURN'
FROM updated_level;
