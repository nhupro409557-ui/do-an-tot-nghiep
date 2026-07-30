-- Strengthen voucher usage identity-limit checks against concurrent direct writes.
CREATE OR REPLACE FUNCTION check_voucher_usage_limits()
RETURNS TRIGGER AS $$
DECLARE
    v_per_user_limit INT;
    v_per_device_limit INT;
    v_per_ip_limit INT;
    v_usage_count INT;
BEGIN
    IF NEW.status IN ('RESERVED', 'USED') THEN
        SELECT per_user_limit, per_device_limit, per_ip_limit
        INTO v_per_user_limit, v_per_device_limit, v_per_ip_limit
        FROM vouchers
        WHERE id = NEW.voucher_id
        FOR UPDATE;

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
