-- Migration: 058_after_sales_terms_and_services
-- Adds policy conditions to return and warranty requests, and attached services to order items.

ALTER TABLE return_requests
    ADD COLUMN IF NOT EXISTS has_accessories BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS good_appearance BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS account_unlocked BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS has_vat_invoice BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE warranty_requests
    ADD COLUMN IF NOT EXISTS has_accessories BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS good_appearance BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS account_unlocked BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS has_vat_invoice BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS attached_services JSONB NOT NULL DEFAULT '[]'::jsonb;
