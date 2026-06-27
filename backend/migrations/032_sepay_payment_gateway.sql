-- Tích hợp SePay Payment Gateway sandbox cho đồ án.

ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_payment_method_check;
ALTER TABLE orders
    ADD CONSTRAINT orders_payment_method_check
    CHECK (payment_method IN ('VNPAY', 'MOMO', 'ZALOPAY', 'SEPAY', 'CREDIT_CARD', 'COD'));

ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS payment_transactions_provider_check;
ALTER TABLE payment_transactions
    ADD CONSTRAINT payment_transactions_provider_check
    CHECK (provider IN ('VNPAY', 'MOMO', 'ZALOPAY', 'SEPAY', 'CREDIT_CARD', 'COD'));

INSERT INTO payment_methods (id, code, name, description, is_active, maintenance_message, maintenance_starts_at, maintenance_ends_at)
VALUES
    (
        'd19b4860-264d-4ba6-847e-8da904b77205',
        'SEPAY',
        'SePay Sandbox',
        'Thanh toán chuyển khoản qua cổng SePay sandbox.',
        TRUE,
        NULL,
        NULL,
        NULL
    )
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description,
    updated_at = NOW();
