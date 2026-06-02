-- Staff accounts receive only the basic role permissions by default.
-- Super Admin can grant extra permissions to individual staff through user_permissions.

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);

DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'STAFF_ADMIN');

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
    'overview:read',
    'product:read',
    'category:read',
    'brand:read',
    'order:read',
    'customer:read',
    'inventory:read',
    'review:read',
    'content:read'
)
WHERE r.code = 'STAFF_ADMIN'
ON CONFLICT DO NOTHING;
