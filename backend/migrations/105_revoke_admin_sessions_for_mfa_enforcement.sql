WITH admin_users AS (
    SELECT DISTINCT u.id
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE r.code IN ('STAFF_ADMIN', 'SUPER_ADMIN')
       OR EXISTS (
            SELECT 1
            FROM user_permissions up
            WHERE up.user_id = u.id
       )
)
UPDATE refresh_token_sessions sessions
SET revoked_at = COALESCE(sessions.revoked_at, NOW())
WHERE sessions.user_id IN (SELECT id FROM admin_users);

INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
SELECT id, NOW(), 'admin_mfa_enforcement'
FROM (
    SELECT DISTINCT u.id
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE r.code IN ('STAFF_ADMIN', 'SUPER_ADMIN')
       OR EXISTS (
            SELECT 1
            FROM user_permissions up
            WHERE up.user_id = u.id
       )
) admin_users
ON CONFLICT (user_id)
DO UPDATE SET
    revoked_after = EXCLUDED.revoked_after,
    reason = EXCLUDED.reason,
    created_at = NOW();
