-- Siết tính nhất quán và khả năng truy vết công nợ nhà cung cấp.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM account_payables
        WHERE supplier_id IS NOT NULL
          AND NULLIF(BTRIM(invoice_number), '') IS NOT NULL
          AND status != 'CANCELLED'
        GROUP BY supplier_id, LOWER(BTRIM(invoice_number))
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION USING
            ERRCODE = 'check_violation',
            MESSAGE = 'Không thể siết công nợ: đang có số hóa đơn trùng của cùng nhà cung cấp. Hãy đối soát dữ liệu trước khi chạy lại migration 103.';
    END IF;
END $$;

ALTER TABLE supplier_payments
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(120),
    ADD COLUMN IF NOT EXISTS request_fingerprint VARCHAR(64),
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'POSTED',
    ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reversed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reversal_reason TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_supplier_payments_status'
          AND conrelid = 'supplier_payments'::regclass
    ) THEN
        ALTER TABLE supplier_payments
            ADD CONSTRAINT ck_supplier_payments_status
            CHECK (status IN ('POSTED', 'REVERSED'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_payments_payable_idempotency
    ON supplier_payments(payable_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_supplier_payments_active
    ON supplier_payments(payable_id, payment_date DESC)
    WHERE status = 'POSTED';

CREATE INDEX IF NOT EXISTS idx_account_payables_supplier_invoice
    ON account_payables(supplier_id, LOWER(BTRIM(invoice_number)))
    WHERE supplier_id IS NOT NULL AND invoice_number IS NOT NULL AND status != 'CANCELLED';

CREATE OR REPLACE FUNCTION enforce_active_supplier_invoice_uniqueness()
RETURNS TRIGGER AS $$
DECLARE
    normalized_invoice TEXT;
BEGIN
    normalized_invoice := LOWER(BTRIM(NEW.invoice_number));
    IF NEW.supplier_id IS NULL OR normalized_invoice IS NULL OR normalized_invoice = '' OR NEW.status = 'CANCELLED' THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('supplier-invoice:' || NEW.supplier_id::text || ':' || normalized_invoice, 0)
    );
    IF EXISTS (
        SELECT 1
        FROM account_payables ap
        WHERE ap.supplier_id = NEW.supplier_id
          AND LOWER(BTRIM(ap.invoice_number)) = normalized_invoice
          AND ap.id != NEW.id
          AND ap.status != 'CANCELLED'
    ) THEN
        RAISE EXCEPTION USING
            ERRCODE = 'unique_violation',
            MESSAGE = 'Số hóa đơn này đã được dùng cho một phiếu nhập khác của nhà cung cấp.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_account_payables_supplier_invoice_unique ON account_payables;
CREATE TRIGGER trg_account_payables_supplier_invoice_unique
BEFORE INSERT OR UPDATE OF supplier_id, invoice_number, status ON account_payables
FOR EACH ROW EXECUTE FUNCTION enforce_active_supplier_invoice_uniqueness();

CREATE TABLE IF NOT EXISTS account_payable_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payable_id UUID NOT NULL REFERENCES account_payables(id) ON DELETE CASCADE,
    adjustment_code VARCHAR(80) NOT NULL UNIQUE,
    adjustment_type VARCHAR(20) NOT NULL CHECK (adjustment_type IN ('DEBIT', 'CREDIT')),
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    reason TEXT NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_account_payable_adjustments_payable
    ON account_payable_adjustments(payable_id, created_at DESC);

COMMIT;
