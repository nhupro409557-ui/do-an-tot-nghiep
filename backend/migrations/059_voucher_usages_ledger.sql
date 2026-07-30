-- Migration: Create voucher_usages table for tracking ledger voucher applications
CREATE TABLE IF NOT EXISTS voucher_usages (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    voucher_id UUID NOT NULL REFERENCES vouchers(id),
    user_id UUID REFERENCES users(id),
    discount_amount NUMERIC(14, 2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'RESERVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_voucher_usages_status CHECK (status IN ('RESERVED', 'USED', 'RELEASED'))
);

CREATE INDEX IF NOT EXISTS idx_voucher_usages_order_id ON voucher_usages(order_id);
CREATE INDEX IF NOT EXISTS idx_voucher_usages_voucher_id ON voucher_usages(voucher_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_voucher_usages_order_voucher ON voucher_usages(order_id, voucher_id);

