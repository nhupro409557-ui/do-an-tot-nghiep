CREATE TABLE store_info (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hotline VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    address VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Insert 1 dòng mặc định làm dữ liệu khởi tạo
INSERT INTO store_info (id, name, hotline, email, address, description, updated_at)
VALUES (
    'a53a99eb-047b-4ecf-a0ff-0f9c2d1bdfd9',
    'ElectroMart Vietnam',
    '1800.2097',
    'support@echophone.local',
    'Hệ thống mô phỏng, hỗ trợ vận hành bán lẻ điện tử.',
    'Hệ thống bán lẻ điện thoại, laptop và phụ kiện chính hãng. Mang đến trải nghiệm mua sắm thông minh với hệ thống tích điểm và ưu đãi cá nhân hóa.',
    NOW()
);
