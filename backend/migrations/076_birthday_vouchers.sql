-- Ngày sinh khóa sau lần khai báo đầu và ledger cấp voucher sinh nhật hằng năm.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS birth_date DATE NULL,
    ADD COLUMN IF NOT EXISTS birth_date_locked_at TIMESTAMPTZ NULL;

ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS birthday_only BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS birthday_voucher_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voucher_id UUID NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
    birthday_year INTEGER NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, voucher_id, birthday_year)
);

CREATE INDEX IF NOT EXISTS idx_birthday_voucher_grants_user_year
    ON birthday_voucher_grants(user_id, birthday_year);
