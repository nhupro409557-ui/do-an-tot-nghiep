CREATE INDEX IF NOT EXISTS idx_inventory_documents_count_status_created
    ON inventory_documents(document_type, status, created_at DESC)
    WHERE document_type = 'COUNT';

INSERT INTO permissions (code, module, description)
VALUES
    ('inventory:count', 'inventory', 'Tạo và đối soát phiếu kiểm kê kho')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code = 'inventory:count'
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;
