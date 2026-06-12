CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    phone VARCHAR(40),
    email VARCHAR(255),
    address TEXT,
    tax_code VARCHAR(80),
    website VARCHAR(255),
    note TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers(is_active);
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);

INSERT INTO permissions (code, module, description)
VALUES
    ('supplier:read', 'supplier', 'Xem nhà cung cấp'),
    ('supplier:create', 'supplier', 'Tạo nhà cung cấp'),
    ('supplier:update', 'supplier', 'Cập nhật nhà cung cấp'),
    ('supplier:delete', 'supplier', 'Xóa nhà cung cấp')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('supplier:read', 'supplier:create', 'supplier:update', 'supplier:delete')
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;
