-- Migration: Add core database invariants check constraints for vouchers and voucher usages
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_vouchers_percent_value'
  ) THEN
    ALTER TABLE vouchers
    ADD CONSTRAINT chk_vouchers_percent_value
    CHECK (discount_type <> 'PERCENT' OR discount_value <= 100);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_vouchers_usage_not_over_limit'
  ) THEN
    ALTER TABLE vouchers
    ADD CONSTRAINT chk_vouchers_usage_not_over_limit
    CHECK (usage_limit = 0 OR used_count <= usage_limit);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_vouchers_budget_not_over_cap'
  ) THEN
    ALTER TABLE vouchers
    ADD CONSTRAINT chk_vouchers_budget_not_over_cap
    CHECK (total_budget_cap IS NULL OR total_discount_used <= total_budget_cap);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_voucher_usages_discount_non_negative'
  ) THEN
    ALTER TABLE voucher_usages
    ADD CONSTRAINT chk_voucher_usages_discount_non_negative
    CHECK (discount_amount >= 0);
  END IF;
END $$;
