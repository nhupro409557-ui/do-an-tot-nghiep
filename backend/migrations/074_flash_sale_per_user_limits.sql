-- Giới hạn số lượng được hưởng giá Flash Sale trên mỗi khách hàng.
-- NULL nghĩa là không giới hạn theo khách hàng.

ALTER TABLE flash_sales
    ADD COLUMN IF NOT EXISTS per_user_limit INTEGER NULL;

ALTER TABLE flash_sales
    DROP CONSTRAINT IF EXISTS flash_sales_per_user_limit_check;

ALTER TABLE flash_sales
    ADD CONSTRAINT flash_sales_per_user_limit_check
    CHECK (per_user_limit IS NULL OR per_user_limit > 0);
