CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    maintenance_message VARCHAR(500),
    maintenance_starts_at TIMESTAMP WITH TIME ZONE,
    maintenance_ends_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_code ON payment_methods (code);

INSERT INTO payment_methods (id, code, name, description, is_active, maintenance_message, maintenance_starts_at, maintenance_ends_at)
VALUES 
    ('d19b4860-264d-4ba6-847e-8da904b77201', 'COD', 'Thanh toán khi nhận hàng', 'Khách hàng thanh toán bằng tiền mặt khi nhận hàng.', TRUE, NULL, NULL, NULL),
    ('d19b4860-264d-4ba6-847e-8da904b77202', 'MOMO', 'Ví MoMo Sandbox', 'Cổng thanh toán thử nghiệm qua ví điện tử MoMo.', TRUE, NULL, NULL, NULL),
    ('d19b4860-264d-4ba6-847e-8da904b77203', 'ZALOPAY', 'Ví ZaloPay Sandbox', 'Cổng thanh toán thử nghiệm qua ví điện tử ZaloPay.', TRUE, NULL, NULL, NULL),
    ('d19b4860-264d-4ba6-847e-8da904b77204', 'VNPAY', 'Cổng VNPAY', 'Cổng thanh toán điện tử VNPAY.', FALSE, 'Phương thức VNPAY tạm thời chưa được hỗ trợ.', NULL, NULL)
ON CONFLICT (code) DO NOTHING;
