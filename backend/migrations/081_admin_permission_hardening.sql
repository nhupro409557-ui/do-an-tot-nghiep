INSERT INTO permissions (code, module, description) VALUES
    ('order:carrier', 'order', 'Quản lý vận đơn và sự kiện vận chuyển'),
    ('order:maintenance', 'order', 'Chạy tác vụ bảo trì đơn hàng'),
    ('after_sales:read', 'after_sales', 'Xem hồ sơ hậu mãi'),
    ('after_sales:update', 'after_sales', 'Cập nhật trạng thái và ghi chú hậu mãi'),
    ('after_sales:inspect', 'after_sales', 'Kiểm định hàng trả và bảo hành'),
    ('report:revenue_read', 'report', 'Xem báo cáo doanh thu'),
    ('report:profit_read', 'report', 'Xem giá vốn và lợi nhuận'),
    ('store_info:read', 'store_info', 'Xem thông tin cửa hàng trong quản trị'),
    ('store_info:update', 'store_info', 'Cập nhật thông tin cửa hàng'),
    ('payable:read', 'payable', 'Xem công nợ nhà cung cấp'),
    ('payable:pay', 'payable', 'Ghi nhận thanh toán công nợ nhà cung cấp')
ON CONFLICT (code) DO UPDATE SET module = EXCLUDED.module, description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN (
    'after_sales:read', 'store_info:read', 'payable:read', 'report:revenue_read'
) WHERE r.code = 'STAFF_ADMIN'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;
