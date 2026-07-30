ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_payment_method_check;
ALTER TABLE orders ADD CONSTRAINT orders_payment_method_check
    CHECK (payment_method IN ('VNPAY', 'MOMO', 'ZALOPAY', 'SEPAY', 'CREDIT_CARD', 'COD', 'NO_PAYMENT'));

UPDATE orders
SET payment_method = 'NO_PAYMENT', updated_at = NOW()
WHERE payment_requirement = 'NO_PAYMENT_REQUIRED'
  AND payment_method <> 'NO_PAYMENT';

INSERT INTO imei_disposition_events (
    id, imei_id, after_sales_type, after_sales_id,
    old_status, new_status, reason, actor_id
)
SELECT gen_random_uuid(), pi.id, 'WARRANTY', wi.request_id,
       'SOLD', 'DEFECTIVE_RETURNED',
       'Bổ sung lịch sử thu hồi máy bảo hành bị thiếu trước khi siết luồng WMS.', NULL
FROM warranty_request_items wi
JOIN product_imeis pi ON pi.imei = wi.imei
WHERE pi.status = 'DEFECTIVE_RETURNED'
  AND NOT EXISTS (
      SELECT 1
      FROM imei_disposition_events event
      WHERE event.imei_id = pi.id
        AND event.after_sales_type = 'WARRANTY'
        AND event.after_sales_id = wi.request_id
        AND event.new_status = 'DEFECTIVE_RETURNED'
  );

INSERT INTO imei_disposition_events (
    id, serial_id, after_sales_type, after_sales_id,
    old_status, new_status, reason, actor_id
)
SELECT gen_random_uuid(), psn.id, 'WARRANTY', wi.request_id,
       'SOLD', 'DEFECTIVE_RETURNED',
       'Bổ sung lịch sử thu hồi máy bảo hành bị thiếu trước khi siết luồng WMS.', NULL
FROM warranty_request_items wi
JOIN product_serial_numbers psn
  ON psn.serial_number = wi.serial_number
 AND psn.product_id = wi.product_id
WHERE psn.status = 'DEFECTIVE_RETURNED'
  AND NOT EXISTS (
      SELECT 1
      FROM imei_disposition_events event
      WHERE event.serial_id = psn.id
        AND event.after_sales_type = 'WARRANTY'
        AND event.after_sales_id = wi.request_id
        AND event.new_status = 'DEFECTIVE_RETURNED'
  );

UPDATE inventory_levels il
SET on_hand_quantity = GREATEST(pv.stock_quantity, il.reserved_quantity),
    updated_at = NOW()
FROM inventory_locations loc, product_variants pv
WHERE loc.id = il.location_id
  AND loc.code = 'MAIN'
  AND il.variant_id = pv.id
  AND il.on_hand_quantity <> GREATEST(pv.stock_quantity, il.reserved_quantity);

UPDATE inventory_levels il
SET on_hand_quantity = GREATEST(p.stock_quantity, il.reserved_quantity),
    updated_at = NOW()
FROM inventory_locations loc, products p
WHERE loc.id = il.location_id
  AND loc.code = 'MAIN'
  AND il.variant_id IS NULL
  AND il.product_id = p.id
  AND il.on_hand_quantity <> GREATEST(p.stock_quantity, il.reserved_quantity);
