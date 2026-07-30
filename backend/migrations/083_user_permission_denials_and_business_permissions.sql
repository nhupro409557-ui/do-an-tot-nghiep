CREATE TABLE IF NOT EXISTS user_permission_denials (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    denied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_user_permission_denials_permission_id
    ON user_permission_denials(permission_id);

INSERT INTO permissions (code, module, description) VALUES
    ('service:read', 'service', 'Xem dịch vụ đi kèm'),
    ('service:create', 'service', 'Tạo dịch vụ đi kèm'),
    ('service:update', 'service', 'Cập nhật dịch vụ đi kèm'),
    ('service:delete', 'service', 'Xóa dịch vụ đi kèm'),
    ('flash_sale:read', 'flash_sale', 'Xem flash sale'),
    ('flash_sale:create', 'flash_sale', 'Tạo flash sale'),
    ('flash_sale:update', 'flash_sale', 'Cập nhật flash sale'),
    ('flash_sale:delete', 'flash_sale', 'Xóa flash sale')
ON CONFLICT (code) DO UPDATE SET module = EXCLUDED.module, description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;
