ALTER TABLE orders
    DROP CONSTRAINT IF EXISTS orders_payment_method_check;

ALTER TABLE orders
    ADD CONSTRAINT orders_payment_method_check
    CHECK (payment_method IN ('VNPAY', 'MOMO', 'ZALOPAY', 'CREDIT_CARD', 'COD'));

