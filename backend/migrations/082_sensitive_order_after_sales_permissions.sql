INSERT INTO permissions (code, module, description) VALUES
    ('order:refund', 'order', 'Xác nhận hoàn tiền đơn hàng'),
    ('after_sales:refund', 'after_sales', 'Xử lý hoàn tiền hậu mãi'),
    ('after_sales:exchange', 'after_sales', 'Duyệt và xử lý đổi sản phẩm')
ON CONFLICT (code) DO UPDATE SET module = EXCLUDED.module, description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;
