CREATE INDEX IF NOT EXISTS idx_inventory_documents_adjustment_no
    ON inventory_documents (document_no)
    WHERE document_type = 'ADJUSTMENT';

INSERT INTO permissions (code, module, description)
VALUES ('inventory:adjust', 'inventory', 'Tạo yêu cầu điều chỉnh tồn kho thủ công')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code = 'inventory:adjust'
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;
