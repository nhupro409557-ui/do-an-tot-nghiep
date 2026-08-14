CREATE TABLE IF NOT EXISTS admin_mfa_recovery_codes (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    challenge_jti VARCHAR(64) NOT NULL,
    code_hash CHAR(64) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_admin_mfa_recovery_attempt_count
        CHECK (attempt_count >= 0 AND attempt_count <= 5)
);

CREATE INDEX IF NOT EXISTS idx_admin_mfa_recovery_codes_expires_at
ON admin_mfa_recovery_codes(expires_at);
