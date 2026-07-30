-- Migration: Add device_id and ip_address to voucher_usages and check per-user/device/IP constraints
ALTER TABLE voucher_usages ADD COLUMN IF NOT EXISTS device_id VARCHAR(120);
ALTER TABLE voucher_usages ADD COLUMN IF NOT EXISTS ip_address VARCHAR(80);

-- Trigger function to validate voucher limits at database level
CREATE OR REPLACE FUNCTION check_voucher_usage_limits()
RETURNS TRIGGER AS $$
DECLARE
    v_per_user_limit INT;
    v_per_device_limit INT;
    v_per_ip_limit INT;
    v_usage_count INT;
BEGIN
    -- Only check limit if usage is RESERVED or USED
    IF NEW.status IN ('RESERVED', 'USED') THEN
        -- Get limits from vouchers table and lock the row to serialize limit checks
        SELECT per_user_limit, per_device_limit, per_ip_limit
        INTO v_per_user_limit, v_per_device_limit, v_per_ip_limit
        FROM vouchers
        WHERE id = NEW.voucher_id
        FOR UPDATE;

        -- 1. Check per-user limit
        IF v_per_user_limit > 0 AND NEW.user_id IS NOT NULL THEN
            SELECT COUNT(*) INTO v_usage_count
            FROM voucher_usages
            WHERE voucher_id = NEW.voucher_id
              AND user_id = NEW.user_id
              AND status IN ('RESERVED', 'USED')
              AND id <> NEW.id;

            IF v_usage_count >= v_per_user_limit THEN
                RAISE EXCEPTION 'Voucher user limit exceeded (Limit: %, Current: %)', v_per_user_limit, v_usage_count
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;

        -- 2. Check per-device limit
        IF v_per_device_limit > 0 AND NEW.device_id IS NOT NULL THEN
            SELECT COUNT(*) INTO v_usage_count
            FROM voucher_usages
            WHERE voucher_id = NEW.voucher_id
              AND device_id = NEW.device_id
              AND status IN ('RESERVED', 'USED')
              AND id <> NEW.id;

            IF v_usage_count >= v_per_device_limit THEN
                RAISE EXCEPTION 'Voucher device limit exceeded (Limit: %, Current: %)', v_per_device_limit, v_usage_count
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;

        -- 3. Check per-ip limit
        IF v_per_ip_limit > 0 AND NEW.ip_address IS NOT NULL THEN
            SELECT COUNT(*) INTO v_usage_count
            FROM voucher_usages
            WHERE voucher_id = NEW.voucher_id
              AND ip_address = NEW.ip_address
              AND status IN ('RESERVED', 'USED')
              AND id <> NEW.id;

            IF v_usage_count >= v_per_ip_limit THEN
                RAISE EXCEPTION 'Voucher IP limit exceeded (Limit: %, Current: %)', v_per_ip_limit, v_usage_count
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_voucher_usage_limits ON voucher_usages;
CREATE TRIGGER trg_check_voucher_usage_limits
BEFORE INSERT OR UPDATE ON voucher_usages
FOR EACH ROW
EXECUTE FUNCTION check_voucher_usage_limits();
