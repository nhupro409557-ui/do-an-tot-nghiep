-- Cho phép khách hàng dùng điểm thưởng để đổi voucher vào ví cá nhân.

ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS redemption_points INTEGER NOT NULL DEFAULT 0;

ALTER TABLE vouchers
    DROP CONSTRAINT IF EXISTS vouchers_redemption_points_check;

ALTER TABLE vouchers
    ADD CONSTRAINT vouchers_redemption_points_check CHECK (redemption_points >= 0);
