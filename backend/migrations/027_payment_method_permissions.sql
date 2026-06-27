-- Chèn các permissions mới cho payment method
INSERT INTO permissions (code, module, description)
VALUES
    ('payment_method:read', 'payment_method', 'Xem cấu hình phương thức thanh toán'),
    ('payment_method:update', 'payment_method', 'Cập nhật cấu hình và lịch bảo trì phương thức thanh toán')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

-- Gán tất cả permissions (bao gồm cả các permissions mới) cho SUPER_ADMIN
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;

-- Gán quyền payment_method:read và payment_method:update cho STAFF_ADMIN (hoặc bất kỳ nhân viên vận hành nào quản lý hệ thống)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('payment_method:read', 'payment_method:update')
WHERE r.code = 'STAFF_ADMIN'
ON CONFLICT DO NOTHING;
