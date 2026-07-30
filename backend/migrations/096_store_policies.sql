CREATE TABLE IF NOT EXISTS store_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO store_policies (code, title, content)
VALUES
    ('OPENING_HOURS', 'Giờ mở cửa', 'Giờ mở cửa hiện chưa được cấu hình. Vui lòng liên hệ hotline trước khi đến cửa hàng.'),
    ('DELIVERY', 'Giao hàng', 'Cửa hàng hỗ trợ giao hàng toàn quốc. Phí chính xác được hiển thị theo địa chỉ trước khi khách xác nhận đơn.'),
    ('INSTALLMENT', 'Trả góp', 'Trả góp chỉ áp dụng cho sản phẩm và đối tác tài chính đủ điều kiện; lựa chọn thực tế hiển thị tại bước thanh toán.'),
    ('VAT_INVOICE', 'Hóa đơn VAT', 'Khách có thể yêu cầu hóa đơn VAT và cần cung cấp đúng thông tin xuất hóa đơn.'),
    ('AUTHENTICITY', 'Nguồn gốc sản phẩm', 'Sản phẩm được bán theo thông tin nguồn gốc và tình trạng công bố trên trang sản phẩm, kèm hóa đơn mua hàng.'),
    ('RETURN_EXCHANGE', 'Đổi trả', 'Thời hạn và điều kiện đổi trả phụ thuộc sản phẩm, lỗi được xác nhận và gói chính sách lúc mua. Chính sách một đổi một chỉ áp dụng cho trường hợp đủ điều kiện.'),
    ('WARRANTY', 'Bảo hành', 'Thời hạn và phạm vi bảo hành phụ thuộc sản phẩm, số serial/IMEI và chính sách ghi nhận lúc mua. Với lỗi phần cứng đủ điều kiện, hồ sơ có thể được sửa chữa hoặc duyệt đổi máy theo kết quả kiểm tra kỹ thuật.'),
    ('PRIVACY', 'Bảo mật thông tin', 'Cửa hàng chỉ sử dụng thông tin cần thiết để xử lý tài khoản, đơn hàng và hậu mãi; không cung cấp dữ liệu riêng tư của khách khác.'),
    ('INSPECTION', 'Kiểm tra hàng', 'Khách nên kiểm tra ngoại quan, đúng sản phẩm và phụ kiện khi nhận; việc kích hoạt hoặc bóc niêm phong thực hiện theo điều kiện của từng sản phẩm.')
ON CONFLICT (code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_store_policies_active
    ON store_policies(is_active, updated_at DESC);
