-- Mở rộng hồ sơ đổi trả để lưu sản phẩm đổi sang và thanh toán chênh lệch.

ALTER TABLE return_requests
    ADD COLUMN IF NOT EXISTS exchange_product_id UUID REFERENCES products(id),
    ADD COLUMN IF NOT EXISTS exchange_variant_id UUID REFERENCES product_variants(id),
    ADD COLUMN IF NOT EXISTS exchange_quantity INTEGER NOT NULL DEFAULT 1 CHECK (exchange_quantity > 0),
    ADD COLUMN IF NOT EXISTS exchange_unit_price_snapshot NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (exchange_unit_price_snapshot >= 0),
    ADD COLUMN IF NOT EXISTS exchange_fee NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (exchange_fee >= 0),
    ADD COLUMN IF NOT EXISTS exchange_shipping_fee NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (exchange_shipping_fee >= 0),
    ADD COLUMN IF NOT EXISTS balance_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30) NOT NULL DEFAULT 'NO_PAYMENT_REQUIRED',
    ADD COLUMN IF NOT EXISTS payment_due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS exchange_payment_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS exchange_payment_reference VARCHAR(160);

ALTER TABLE return_requests
    DROP CONSTRAINT IF EXISTS return_requests_status_check;

ALTER TABLE return_requests
    ADD CONSTRAINT return_requests_status_check CHECK (status IN (
        'SUBMITTED', 'RECEIVED', 'QC_IN_PROGRESS', 'QC_APPROVED', 'REJECTED',
        'WAITING_FOR_STOCK', 'WAITING_FOR_EXCHANGE_PAYMENT',
        'EXCHANGE_PROCESSING', 'REFUND_PROCESSING',
        'COMPLETED', 'CANCELLED', 'CLOSED_EXPIRED'
    ));

ALTER TABLE return_requests
    DROP CONSTRAINT IF EXISTS return_requests_payment_status_check;

ALTER TABLE return_requests
    ADD CONSTRAINT return_requests_payment_status_check CHECK (
        payment_status IN ('NO_PAYMENT_REQUIRED', 'PENDING', 'PAID', 'TIMEOUT')
    );

CREATE INDEX IF NOT EXISTS idx_return_requests_exchange_payment_due
    ON return_requests(status, payment_due_at)
    WHERE status = 'WAITING_FOR_EXCHANGE_PAYMENT';
