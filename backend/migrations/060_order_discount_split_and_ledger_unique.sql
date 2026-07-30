-- Migration: Split order discount into voucher and loyalty points discount, and ensure unique voucher usage ledger
ALTER TABLE orders ADD COLUMN IF NOT EXISTS voucher_discount_amount NUMERIC(14, 2) DEFAULT 0.00 NOT NULL;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS loyalty_discount_amount NUMERIC(14, 2) DEFAULT 0.00 NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_voucher_usages_order_voucher ON voucher_usages(order_id, voucher_id);
