-- Module công nợ phải trả nhà cung cấp.

CREATE TABLE IF NOT EXISTS account_payables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    supplier_name_snapshot VARCHAR(255),
    source_document_id UUID NOT NULL REFERENCES inventory_documents(id) ON DELETE CASCADE,
    source_reference_code VARCHAR(120) NOT NULL,
    invoice_number VARCHAR(120),
    invoice_date TIMESTAMPTZ,
    principal_amount NUMERIC(14, 2) NOT NULL CHECK (principal_amount >= 0),
    paid_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    remaining_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (remaining_amount >= 0),
    payment_term_days INTEGER NOT NULL DEFAULT 0 CHECK (payment_term_days >= 0 AND payment_term_days <= 365),
    due_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'PARTIAL', 'PAID', 'CANCELLED')),
    note TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (paid_amount <= principal_amount),
    CHECK (remaining_amount <= principal_amount)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_account_payables_source_document
    ON account_payables(source_document_id);

CREATE INDEX IF NOT EXISTS idx_account_payables_supplier_status
    ON account_payables(supplier_id, status, due_date);

CREATE INDEX IF NOT EXISTS idx_account_payables_due_date
    ON account_payables(due_date)
    WHERE status IN ('OPEN', 'PARTIAL');

CREATE INDEX IF NOT EXISTS idx_account_payables_reference
    ON account_payables(source_reference_code);

CREATE TABLE IF NOT EXISTS supplier_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payable_id UUID NOT NULL REFERENCES account_payables(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    payment_code VARCHAR(80) NOT NULL UNIQUE,
    payment_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    method VARCHAR(30) NOT NULL DEFAULT 'BANK_TRANSFER'
        CHECK (method IN ('CASH', 'BANK_TRANSFER', 'OTHER')),
    reference_no VARCHAR(120),
    note TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_supplier_payments_payable
    ON supplier_payments(payable_id, payment_date DESC);

CREATE TABLE IF NOT EXISTS account_payable_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payable_id UUID NOT NULL REFERENCES account_payables(id) ON DELETE CASCADE,
    event_type VARCHAR(80) NOT NULL,
    amount NUMERIC(14, 2),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_account_payable_events_payable
    ON account_payable_events(payable_id, created_at DESC);
