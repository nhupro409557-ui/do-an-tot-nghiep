-- ElectroMart database baseline
-- Consolidated through legacy migration 073 on 2026-06-18.
-- For a new database, run this file first. Future migrations start at 001_*.sql.

-- ==========================================
-- Migration: 001_initial_schema.sql
-- ==========================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELETED')),
    marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    loyalty_points_balance INTEGER NOT NULL DEFAULT 0 CHECK (loyalty_points_balance >= 0),
    loyalty_tier VARCHAR(30) NOT NULL DEFAULT 'MEMBER'
        CHECK (loyalty_tier IN ('MEMBER', 'SILVER', 'GOLD', 'DIAMOND')),
    loyalty_wallet_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (loyalty_wallet_status IN ('ACTIVE', 'CLOSED')),
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL CHECK (category IN ('PHONE', 'LAPTOP', 'ACCESSORY')),
    brand VARCHAR(100) NOT NULL,
    description TEXT,
    specifications JSONB NOT NULL DEFAULT '{}'::jsonb,
    price NUMERIC(14, 2) NOT NULL CHECK (price >= 0),
    sale_price NUMERIC(14, 2) CHECK (sale_price IS NULL OR sale_price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    hidden_by_category BOOLEAN NOT NULL DEFAULT FALSE,
    hidden_by_brand BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'OUT_OF_STOCK')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    order_code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'CONFIRMED',
                'PAID',
                'PROCESSING',
                'SHIPPED',
                'COMPLETED',
                'CANCELLED',
                'REFUNDED'
            )
        ),
    payment_method VARCHAR(30) NOT NULL
        CHECK (payment_method IN ('VNPAY', 'MOMO', 'CREDIT_CARD', 'COD')),
    payment_status VARCHAR(30) NOT NULL DEFAULT 'UNPAID'
        CHECK (payment_status IN ('UNPAID', 'PAID', 'FAILED', 'REFUNDED')),
    subtotal_amount NUMERIC(14, 2) NOT NULL CHECK (subtotal_amount >= 0),
    discount_amount NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_fee NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (shipping_fee >= 0),
    total_amount NUMERIC(14, 2) NOT NULL CHECK (total_amount >= 0),
    loyalty_points_earned INTEGER NOT NULL DEFAULT 0 CHECK (loyalty_points_earned >= 0),
    loyalty_points_used INTEGER NOT NULL DEFAULT 0 CHECK (loyalty_points_used >= 0),
    recipient_name VARCHAR(255) NOT NULL,
    recipient_phone VARCHAR(30) NOT NULL,
    shipping_address TEXT NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    order_id UUID REFERENCES orders(id),
    type VARCHAR(30) NOT NULL CHECK (type IN ('EARN', 'REDEEM', 'REFUND', 'REVOKE', 'ADJUST')),
    points INTEGER NOT NULL CHECK (points > 0),
    balance_before INTEGER NOT NULL CHECK (balance_before >= 0),
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    reason TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_context_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID NOT NULL,
    request_scope VARCHAR(50) NOT NULL DEFAULT 'SALES_ASSISTANT'
        CHECK (request_scope IN ('SALES_ASSISTANT')),
    user_message TEXT NOT NULL,
    assistant_response TEXT,
    refusal_reason TEXT,
    dynamic_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_provider VARCHAR(30) NOT NULL CHECK (model_provider IN ('OPENAI', 'GEMINI')),
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14, 2) NOT NULL CHECK (unit_price >= 0),
    total_price NUMERIC(14, 2) NOT NULL CHECK (total_price >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_code ON orders(order_code);
CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_user_id ON loyalty_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_context_logs_user_id ON ai_context_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_context_logs_conversation_id ON ai_context_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

INSERT INTO roles (code, name)
VALUES
  ('CUSTOMER', 'Customer'),
  ('STAFF_ADMIN', 'Staff Admin'),
  ('SUPER_ADMIN', 'Super Administrator')
ON CONFLICT (code) DO NOTHING;


-- ==========================================
-- Migration: 002_commerce_features.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS vouchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('FIXED', 'PERCENT')),
    discount_value NUMERIC(14, 2) NOT NULL CHECK (discount_value > 0),
    min_order_value NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (min_order_value >= 0),
    max_discount NUMERIC(14, 2) CHECK (max_discount IS NULL OR max_discount >= 0),
    usage_limit INTEGER NOT NULL DEFAULT 0 CHECK (usage_limit >= 0),
    used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'EXPIRED')),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id),
    user_id UUID REFERENCES users(id),
    user_name VARCHAR(255) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    media_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PUBLISHED', 'HIDDEN', 'REJECTED')),
    moderation_note TEXT,
    shop_reply TEXT,
    shop_replied_by UUID REFERENCES users(id),
    shop_replied_at TIMESTAMPTZ,
    flagged_reason TEXT,
    flagged_at TIMESTAMPTZ,
    is_spam BOOLEAN NOT NULL DEFAULT FALSE,
    spam_reason TEXT,
    review_window_expires_at TIMESTAMPTZ,
    edited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL CHECK (provider IN ('VNPAY', 'MOMO', 'CREDIT_CARD', 'COD')),
    amount NUMERIC(14, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'REFUNDED')),
    transaction_ref VARCHAR(120),
    checkout_url TEXT,
    raw_response JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vouchers_code ON vouchers(code);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status);
CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_product_reviews_status ON product_reviews(status);
CREATE INDEX IF NOT EXISTS idx_product_reviews_user_product ON product_reviews(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_order_id ON payment_transactions(order_id);

INSERT INTO vouchers (code, discount_type, discount_value, min_order_value, max_discount, usage_limit)
VALUES
    ('WELCOME100', 'FIXED', 100000, 1000000, NULL, 1000),
    ('TECH10', 'PERCENT', 10, 3000000, 500000, 500)
ON CONFLICT (code) DO NOTHING;


-- ==========================================
-- Migration: 003_catalog_taxonomy_seed.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    code VARCHAR(80) NOT NULL UNIQUE,
    slug VARCHAR(120) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(80),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_categories (
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (brand_id, category_id)
);

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'products'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%category%PHONE%LAPTOP%ACCESSORY%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE products DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES categories(id);
ALTER TABLE products ADD COLUMN IF NOT EXISTS subcategory_id UUID REFERENCES categories(id);
ALTER TABLE products ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id);
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS images JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS colors JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS capacities JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS promotions JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS badge VARCHAR(80);
ALTER TABLE products ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS review_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_flash_sale BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS hidden_by_category BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS hidden_by_brand BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(120) NOT NULL UNIQUE,
    color_name VARCHAR(100),
    color_code VARCHAR(30),
    storage VARCHAR(80),
    ram VARCHAR(80),
    configuration VARCHAR(160),
    price NUMERIC(14, 2) NOT NULL CHECK (price >= 0),
    sale_price NUMERIC(14, 2) CHECK (sale_price IS NULL OR sale_price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_subcategory_id ON products(subcategory_id);
CREATE INDEX IF NOT EXISTS idx_products_brand_id ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_inherited_visibility
    ON products(hidden_by_category, hidden_by_brand, status);
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);

INSERT INTO categories (code, slug, name, icon, sort_order)
VALUES
    ('smartphones', 'smartphones', 'Điện thoại', 'smartphone', 1),
    ('tablets', 'tablets', 'Máy tính bảng', 'tablet', 2),
    ('laptops', 'laptops', 'Máy tính xách tay', 'laptop', 3),
    ('accessories', 'accessories', 'Phụ kiện công nghệ', 'accessory', 4),
    ('wearables', 'wearables', 'Đồng hồ thông minh', 'watch', 5),
    ('may-anh', 'may-anh', 'Máy ảnh', 'camera', 6),
    ('cameras', 'cameras', 'Camera', 'camera', 7)
ON CONFLICT (code) DO UPDATE SET
    slug = EXCLUDED.slug,
    name = EXCLUDED.name,
    icon = EXCLUDED.icon,
    sort_order = EXCLUDED.sort_order,
    parent_id = NULL,
    is_active = TRUE,
    updated_at = NOW();

WITH subcategories(code, parent_code, slug, name, sort_order) AS (
    VALUES
    ('phone-flagship', 'smartphones', 'dien-thoai-cao-cap', 'Điện thoại cao cấp', 1),
    ('phone-foldable', 'smartphones', 'dien-thoai-gap', 'Điện thoại gập', 2),
    ('phone-midrange', 'smartphones', 'dien-thoai-tam-trung', 'Điện thoại tầm trung', 3),
    ('phone-budget', 'smartphones', 'dien-thoai-gia-re', 'Điện thoại giá rẻ', 4),
    ('phone-gaming', 'smartphones', 'dien-thoai-gaming', 'Điện thoại Gaming chuyên dụng', 5),
    ('tablet-pro', 'tablets', 'tablet-cao-cap', 'Tablet cao cấp', 1),
    ('tablet-study', 'tablets', 'tablet-hoc-tap-giai-tri', 'Tablet giải trí & học tập', 2),
    ('tablet-2in1', 'tablets', 'tablet-2-in-1', 'Tablet lai 2-in-1', 3),
    ('tablet-mini', 'tablets', 'tablet-mini', 'Tablet mini', 4),
    ('laptop-ultrabook', 'laptops', 'laptop-mong-nhe', 'Laptop mỏng nhẹ', 1),
    ('laptop-gaming', 'laptops', 'laptop-gaming', 'Laptop Gaming', 2),
    ('laptop-workstation', 'laptops', 'laptop-workstation', 'Laptop đồ họa - kỹ thuật', 3),
    ('laptop-office', 'laptops', 'laptop-van-phong', 'Laptop học tập - văn phòng', 4),
    ('macbook', 'laptops', 'macbook', 'MacBook', 5),
    ('audio-tws', 'accessories', 'tai-nghe-tws', 'True Wireless (TWS)', 1),
    ('audio-overear', 'accessories', 'tai-nghe-chup-tai', 'Tai nghe chụp tai', 2),
    ('audio-sport', 'accessories', 'tai-nghe-the-thao', 'Tai nghe thể thao', 3),
    ('audio-gaming', 'accessories', 'tai-nghe-gaming', 'Tai nghe Gaming', 4),
    ('adapter-gan', 'accessories', 'sac-nhanh-gan', 'Sạc nhanh GaN', 5),
    ('adapter-multiport', 'accessories', 'sac-nhieu-cong', 'Sạc nhiều cổng', 6),
    ('adapter-wireless', 'accessories', 'sac-khong-day', 'Sạc không dây MagSafe/Qi', 7),
    ('cable-usbc', 'accessories', 'cap-type-c', 'Cáp Type-C to Type-C', 8),
    ('cable-lightning', 'accessories', 'cap-lightning', 'Cáp Type-C to Lightning', 9),
    ('cable-thunderbolt', 'accessories', 'cap-thunderbolt-4', 'Cáp Thunderbolt 4', 10),
    ('watch-fashion', 'wearables', 'smartwatch-thoi-trang', 'Smartwatch thời trang cao cấp', 1),
    ('watch-sport', 'wearables', 'dong-ho-the-thao', 'Đồng hồ thể thao/Outdoor', 2),
    ('smartband', 'wearables', 'smartband', 'Vòng đeo tay thông minh', 3),
    ('kids-watch', 'wearables', 'dong-ho-dinh-vi-tre-em', 'Đồng hồ định vị trẻ em', 4),
    ('camera-mirrorless', 'may-anh', 'may-anh-mirrorless', 'Máy ảnh Mirrorless', 1),
    ('camera-dslr', 'may-anh', 'may-anh-dslr', 'Máy ảnh DSLR', 2),
    ('action-camera', 'cameras', 'action-camera', 'Camera hành động / Vlog Cam', 1),
    ('security-camera', 'cameras', 'camera-an-ninh', 'Camera an ninh', 2),
    ('dashcam', 'cameras', 'camera-hanh-trinh', 'Camera hành trình', 3)
)
INSERT INTO categories (code, parent_id, slug, name, sort_order)
SELECT subcategories.code, parent.id, subcategories.slug, subcategories.name, subcategories.sort_order
FROM subcategories
JOIN categories parent ON parent.code = subcategories.parent_code
ON CONFLICT (code) DO UPDATE SET
    parent_id = EXCLUDED.parent_id,
    slug = EXCLUDED.slug,
    name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_active = TRUE,
    updated_at = NOW();

WITH brand_seed(name, category_codes) AS (
    VALUES
    ('Apple', ARRAY['smartphones','tablets','laptops','accessories','wearables']),
    ('Samsung', ARRAY['smartphones','tablets','wearables']),
    ('Xiaomi', ARRAY['smartphones','tablets']),
    ('OPPO', ARRAY['smartphones']),
    ('vivo', ARRAY['smartphones']),
    ('ASUS', ARRAY['smartphones','laptops']),
    ('Lenovo', ARRAY['tablets','laptops']),
    ('Microsoft', ARRAY['tablets','laptops']),
    ('Dell', ARRAY['laptops']),
    ('HP', ARRAY['laptops']),
    ('Acer', ARRAY['laptops']),
    ('MSI', ARRAY['laptops']),
    ('Sony', ARRAY['accessories','may-anh']),
    ('Marshall', ARRAY['accessories']),
    ('JBL', ARRAY['accessories']),
    ('Sennheiser', ARRAY['accessories']),
    ('Razer', ARRAY['accessories']),
    ('Anker', ARRAY['accessories']),
    ('Ugreen', ARRAY['accessories']),
    ('Baseus', ARRAY['accessories']),
    ('Belkin', ARRAY['accessories']),
    ('Mophie', ARRAY['accessories']),
    ('Garmin', ARRAY['wearables']),
    ('Coros', ARRAY['wearables']),
    ('Huawei', ARRAY['wearables']),
    ('Amazfit', ARRAY['wearables']),
    ('Canon', ARRAY['may-anh']),
    ('Fujifilm', ARRAY['may-anh']),
    ('GoPro', ARRAY['cameras']),
    ('DJI', ARRAY['cameras'])
)
-- BRAND CATEGORIES INSERT
, upserted_brands AS (
    INSERT INTO brands (code, name)
    SELECT lower(name), name
    FROM brand_seed
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
    RETURNING id, name
)
INSERT INTO brand_categories (brand_id, category_id)
SELECT upserted_brands.id, categories.id
FROM brand_seed
JOIN upserted_brands ON upserted_brands.name = brand_seed.name
JOIN LATERAL unnest(brand_seed.category_codes) AS category_code ON TRUE
JOIN categories ON categories.code = category_code
ON CONFLICT DO NOTHING;

-- PRODUCTS SEED WITH
WITH product_seed(sku, slug, name, category_code, subcategory_code, brand_name, price, sale_price, stock_quantity, image_url, specifications, colors, capacities, is_featured, is_flash_sale, rating, review_count, badge) AS (
    VALUES
    ('AWU2', 'apple-watch-ultra-2', 'Apple Watch Ultra 2', 'wearables', 'watch-sport', 'Apple', 16990000, 16990000, 90, 'https://placehold.co/600x600/f8fafc/0f172a?text=Apple+Watch+Ultra+2', '{"gps": "GPS băng tần kép", "nfc": "Apple Pay", "strap": "Dây Ocean/Trail/Alpine tùy phiên bản", "weight": "Khoảng 61.4 g", "battery": "Tối đa 36 giờ, chế độ tiết kiệm đến 72 giờ", "sensors": "Nhịp tim, SpO2, ECG, nhiệt độ, độ sâu, la bàn", "storage": "64GB", "charging": "Sạc nhanh từ tính USB-C", "material": "Titanium", "case_size": "49 mm", "processor": "Apple S9 SiP", "resolution": "410 x 502 pixels", "screen_size": "49 mm", "connectivity": "GPS, LTE, Wi-Fi, Bluetooth", "sports_modes": "Chạy bộ, đạp xe, bơi, leo núi, lặn giải trí", "compatibility": "iPhone chạy iOS mới", "water_resistance": "WR100, IP6X", "screen_technology": "OLED Retina LTPO"}'::jsonb, '[{"code": "#2a2b2d", "name": "Titan Đen"}]'::jsonb, '["49mm Dây Alpine Size L", "49mm Dây Alpine Size S", "49mm Dây Trail Size S/M", "49mm Dây Cao Su", "49mm Dây Trail Size M/L", "49mm Dây Titan Size M", "49mm Dây Titan Size S", "49mm Dây Titan Size L", "49mm Dây Alpine Size M"]'::jsonb, TRUE, FALSE, 4.8, 99, 'Hot'),
    ('EZC6N', 'ezviz-c6n', 'Ezviz C6N', 'cameras', 'security-camera', 'Ezviz', 890000, 690000, 55, 'https://placehold.co/600x600/f8fafc/0f172a?text=Ezviz+C6N', '{"lens": "Ống kính góc rộng", "zoom": "Digital zoom", "sensor": "CMOS 1/4 inch", "weight": "Khoảng 218 g", "battery": "Dùng nguồn trực tiếp", "storage": "microSD tối đa 256GB, cloud tùy gói", "dimensions": "Khoảng 88 x 88 x 119 mm", "microphone": "Đàm thoại 2 chiều", "resolution": "Full HD 1080p", "connectivity": "Wi-Fi 2.4GHz", "field_of_view": "Xoay ngang 340°, dọc 55°", "stabilization": "Không hỗ trợ chống rung cơ học", "video_recording": "1080p"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.4, 180, NULL),
    ('X14U', 'xiaomi-14-ultra', 'Xiaomi 14 Ultra', 'smartphones', 'phone-flagship', 'Xiaomi', 27990000, 24990000, 12, 'https://placehold.co/600x600/f8fafc/0f172a?text=Xiaomi+14+Ultra', '{"os": "Android 14, HyperOS", "cpu": "8 nhân", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS, NavIC", "gpu": "Adreno 750", "nfc": "Có", "ram": "16GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Loa kép Stereo, Dolby Atmos, Hi-Res & Hi-Res Wireless Audio", "weight": "220 g", "battery": "5000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, quang phổ màu", "storage": "512GB", "charging": "Sạc nhanh 90W có dây, 80W không dây", "infrared": "Có", "material": "Khung hợp kim nhôm siêu bền, Mặt lưng da sinh thái cao cấp", "bluetooth": "Bluetooth 5.4", "processor": "Snapdragon 8 Gen 3", "brightness": "Tối đa 3000 nits", "dimensions": "161.4 x 75.3 x 9.2 mm", "rear_video": "8K@24/30fps, 4K@24/30/60/120fps, Dolby Vision HDR 10-bit", "resolution": "1440 x 3200 pixels (2K+)", "fingerprint": "Quang học dưới màn hình", "front_video": "4K@30/60fps, 1080p@30/60fps", "rear_camera": "Chính 50 MP (Leica Lytech-900) & Phụ 50 MP, 50 MP, 50 MP", "screen_size": "6.73 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình cong tràn viền đục lỗ", "front_camera": "32 MP", "refresh_rate": "120Hz", "release_time": "02/2024", "back_material": "Da nhân tạo cao cấp", "charging_port": "USB Type-C 3.2 Gen 2", "compatibility": "Android", "frame_material": "Hợp kim nhôm siêu bền", "video_recording": "8K@24/30fps, 4K@24/30/60/120fps", "display_features": "68 tỷ màu, Dolby Vision, HDR10+, Kính Shield Glass", "special_features": "Hệ thống làm mát Xiaomi IceLoop, Chip hình ảnh Surge G1/P2", "water_resistance": "IP68", "screen_technology": "LTPO AMOLED", "rear_camera_features": "Ống kính Leica Summilux chuyên nghiệp, Khẩu độ thay đổi vô cấp f/1.63 - f/4.0, Zoom quang 3.2x & 5x, OIS kép"}'::jsonb, '[]'::jsonb, '["512GB"]'::jsonb, TRUE, FALSE, 4.7, 93, 'Hot'),
    ('DJIPOCKET3', 'dji-pocket-3', 'DJI Pocket 3', 'cameras', 'action-camera', 'DJI', 14990000, 12990000, 14, 'https://placehold.co/600x600/f8fafc/0f172a?text=DJI+Pocket+3', '{"lens": "Tiêu cự tương đương 20 mm, f/2.0", "zoom": "Digital zoom", "sensor": "CMOS 1 inch", "weight": "179 g", "battery": "1300 mAh", "storage": "microSD", "dimensions": "139.7 x 42.2 x 33.5 mm", "microphone": "Micro stereo tích hợp", "resolution": "Ảnh tĩnh 9.4MP", "connectivity": "USB-C, Wi-Fi, Bluetooth", "field_of_view": "Góc rộng 20 mm", "stabilization": "Gimbal 3 trục", "video_recording": "4K/120fps, 4K/60fps HDR"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.8, 120, 'Hot'),
    ('S24U', 'galaxy-s24-ultra', 'Samsung Galaxy S24 Ultra', 'smartphones', 'phone-flagship', 'Samsung', 31990000, 25990000, 15, 'https://placehold.co/600x600/f8fafc/0f172a?text=Galaxy+S24+Ultra', '{"os": "Android 14, One UI 6.1", "cpu": "8 nhân", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 750", "nfc": "Có", "ram": "12GB", "sim": "2 Nano SIM hoặc eSIM", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Loa kép Stereo, Dolby Atmos, cân chỉnh bởi AKG", "weight": "232 g", "battery": "5000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay siêu âm, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu", "storage": "256GB", "charging": "Sạc nhanh 45W, Sạc không dây 15W", "infrared": "Không", "material": "Khung Titanium, Mặt kính Corning Gorilla Armor", "bluetooth": "Bluetooth 5.3", "processor": "Snapdragon 8 Gen 3 for Galaxy", "brightness": "Tối đa 2600 nits", "dimensions": "162.3 x 79.0 x 8.6 mm", "rear_video": "8K@30fps, 4K@30/60/120fps, gyro-EIS, OIS", "resolution": "1440 x 3120 pixels (QHD+)", "fingerprint": "Cảm biến vân tay siêu âm dưới màn hình", "front_video": "4K@30/60fps, 1080p@30fps", "rear_camera": "Chính 200 MP & Phụ 50 MP, 12 MP, 10 MP", "screen_size": "6.8 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình đục lỗ (Infinity-O)", "front_camera": "12 MP", "refresh_rate": "120Hz", "release_time": "01/2024", "back_material": "Kính cường lực Corning Gorilla Armor", "charging_port": "USB Type-C 3.2", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Titanium", "video_recording": "8K@30fps, 4K@120fps", "display_features": "Always-On Display, HDR10+, Vision Booster, Kính Gorilla Armor chống chói", "special_features": "Galaxy AI, Hỗ trợ bút S Pen tích hợp, Samsung DeX", "water_resistance": "IP68", "screen_technology": "Dynamic AMOLED 2X", "rear_camera_features": "Zoom quang học 5x & 3x, Zoom Space 100x, OIS, Laser AF"}'::jsonb, '[{"code": "#9ca3af", "name": "Titanium Gray"}, {"code": "#27272a", "name": "Titanium Black"}]'::jsonb, '["256GB", "512GB"]'::jsonb, TRUE, FALSE, 4.8, 197, 'Hot'),
    ('ROGG14', 'asus-rog-zephyrus-g14', 'ASUS ROG Zephyrus G14', 'laptops', 'laptop-gaming', 'ASUS', 45990000, 41990000, 7, 'https://placehold.co/600x600/f8fafc/0f172a?text=ROG+Zephyrus+G14', '{"ram": "32GB", "storage": "1TB SSD", "graphics": "RTX 4070", "processor": "Ryzen 9"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.7, 89, 'Hot'),
    ('ZFOLD6', 'galaxy-z-fold6', 'Samsung Galaxy Z Fold6', 'smartphones', 'phone-foldable', 'Samsung', 44990000, 41990000, 8, 'https://placehold.co/600x600/f8fafc/0f172a?text=Galaxy+Z+Fold6', '{"os": "Android 14, One UI 6.1.1", "cpu": "8 nhân", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 750", "nfc": "Có", "ram": "12GB", "sim": "2 Nano SIM hoặc eSIM", "wifi": "Wi-Fi 6E (802.11ax)", "audio": "Loa kép Stereo, Dolby Atmos", "weight": "239 g", "battery": "4400 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay cạnh bên, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu", "storage": "256GB", "charging": "Sạc nhanh 25W, Sạc không dây 15W", "infrared": "Không", "material": "Khung nhôm Armor Aluminum, Kính Gorilla Glass Victus 2", "bluetooth": "Bluetooth 5.3", "processor": "Snapdragon 8 Gen 3 for Galaxy", "brightness": "Tối đa 2600 nits", "dimensions": "153.5 x 132.6 x 5.6 mm (mở), 153.5 x 68.1 x 12.1 mm (gập)", "rear_video": "8K@30fps, 4K@60fps, gyro-EIS", "resolution": "2160 x 1856 pixels (Màn hình chính)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "4K@30/60fps (Màn hình phụ)", "rear_camera": "Chính 50 MP & Phụ 12 MP, 10 MP", "screen_size": "Chính 7.6 inches, Phụ 6.3 inches", "connectivity": "Wi-Fi 6E, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình gập (Foldable)", "front_camera": "4 MP (dưới màn hình) & 10 MP (màn hình phụ)", "refresh_rate": "120Hz", "release_time": "07/2024", "back_material": "Kính Gorilla Glass Victus 2", "charging_port": "USB Type-C 3.2", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Armor Aluminum", "video_recording": "8K@30fps, 4K@60fps", "display_features": "Màn hình gập thế hệ mới, Hỗ trợ S Pen, Always-On Display", "special_features": "Galaxy AI tối ưu cho màn hình gập, Đa nhiệm Multi-window, Samsung DeX", "water_resistance": "IP48 (Kháng nước nâng cấp)", "screen_technology": "Dynamic AMOLED 2X", "rear_camera_features": "Zoom quang học 3x, OIS, Tự động lấy nét nhanh"}'::jsonb, '[]'::jsonb, '["256GB", "512GB"]'::jsonb, TRUE, FALSE, 4.7, 118, 'Hot'),
    ('ANK100W', 'anker-prime-100w', 'Củ sạc Anker Prime GaN 100W', 'accessories', 'adapter-gan', 'Anker', 2490000, 1890000, 40, 'https://placehold.co/600x600/f8fafc/0f172a?text=Anker+Prime+100W', '{"color": "Đen", "ports": "2 USB-C, 1 USB-A", "power": "100W", "weight": "Khoảng 170 g", "material": "Nhựa chống cháy", "dimensions": "Khoảng 67 x 45 x 32 mm", "connectivity": "USB-C Power Delivery, USB-A", "compatibility": "Điện thoại, tablet, laptop USB-C", "accessory_type": "Củ sạc nhanh GaN", "charging_standard": "USB Power Delivery, PPS"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.7, 142, 'Hot'),
    ('SONYA7IV', 'sony-a7-iv', 'Sony Alpha A7 IV', 'may-anh', 'camera-mirrorless', 'Sony', 57990000, 52990000, 5, 'https://placehold.co/600x600/f8fafc/0f172a?text=Sony+A7+IV', '{"iso": "ISO 100-51200, mở rộng 50-204800", "ports": "USB-C, HDMI, mic, headphone", "sensor": "Full-frame Exmor R CMOS 33MP", "weight": "Khoảng 658 g", "battery": "NP-FZ100", "storage": "2 khe thẻ SD/CFexpress Type A", "autofocus": "759 điểm lấy nét theo pha", "dimensions": "131.3 x 96.4 x 79.8 mm", "lens_mount": "Sony E-mount", "resolution": "33MP", "viewfinder": "OLED EVF 3.69 triệu điểm", "screen_size": "LCD xoay lật 3 inch", "connectivity": "Wi-Fi, Bluetooth, USB-C, HDMI", "shutter_speed": "1/8000 - 30 giây", "stabilization": "Chống rung 5 trục trong thân máy", "video_recording": "4K 60p, 10-bit 4:2:2", "weather_sealing": "Thân máy kháng bụi/ẩm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.9, 48, 'Hot'),
    ('OPPFN3-BK-512GB', 'oppo-find-n3', 'OPPO Find N3', 'smartphones', 'phone-foldable', 'OPPO', 39990000, 34990000, 6, '/images/products/oppo-find-n3/black/cover.webp', '{"os": "Android 13, ColorOS 14", "cpu": "8 nhân", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 740", "nfc": "Có", "ram": "16GB", "sim": "2 Nano SIM", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Hệ thống 3 loa Stereo, Dolby Atmos", "weight": "239 g", "battery": "4805 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay cạnh bên, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, quang phổ màu", "storage": "512GB", "charging": "Sạc siêu nhanh SUPERVOOC 67W", "infrared": "Không", "material": "Khung hợp kim nhôm bọc carbon, Mặt lưng kính hoặc Da sợi", "bluetooth": "Bluetooth 5.3", "processor": "Snapdragon 8 Gen 2", "brightness": "Tối đa 2800 nits", "dimensions": "153.4 x 143.1 x 5.8 mm (mở), 153.4 x 73.3 x 11.7 mm (gập)", "rear_video": "4K@30/60fps, 1080p@30/60/240fps, gyro-EIS, HDR10+", "resolution": "2440 x 2268 pixels (Màn hình chính)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "4K@30fps, 1080p@30fps", "rear_camera": "Chính 48 MP & Phụ 64 MP, 48 MP", "screen_size": "Chính 7.82 inches, Phụ 6.31 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình gập (Foldable)", "front_camera": "20 MP (Trong) & 32 MP (Ngoài)", "refresh_rate": "120Hz", "release_time": "10/2023", "back_material": "Da sinh thái / Kính cường lực", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "4K@30/60fps, 1080p@30/60/240fps", "_variantSpecKeys": ["ram", "Màu sắc", "storage"], "display_features": "Dolby Vision, 1 tỷ màu, Kính siêu mỏng UTG", "special_features": "Đa nhiệm thông minh Canvas, Bản lề Flexion Hinge siêu phẳng", "water_resistance": "IPX4 (Kháng nước bắn nhẹ)", "screen_technology": "LTPO3 OLED", "rear_camera_features": "Camera Hasselblad, OIS, Zoom quang 3x, Cảm biến chồng Sony LYT-T808"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen"}, {"code": "#e5c158", "name": "Vàng"}]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.6, 78, 'Hot'),
    ('GFENIX7P', 'garmin-fenix-7-pro', 'Garmin Fenix 7 Pro', 'wearables', 'watch-sport', 'Garmin', 21990000, 18990000, 8, 'https://placehold.co/600x600/f8fafc/0f172a?text=Garmin+Fenix+7+Pro', '{"gps": "GPS đa băng tần", "strap": "QuickFit 22 mm", "weight": "Khoảng 73 g", "battery": "Tối đa 18 ngày, sạc năng lượng mặt trời đến 22 ngày", "sensors": "Nhịp tim, SpO2, cao độ, khí áp, la bàn", "storage": "32GB", "charging": "Cáp sạc Garmin", "material": "Thép/titan tùy phiên bản", "case_size": "47 mm", "processor": "Garmin GNSS chipset", "resolution": "260 x 260 pixels", "screen_size": "1.3 inch", "connectivity": "Bluetooth, ANT+, Wi-Fi, GPS đa băng tần", "sports_modes": "Đa môn thể thao, chạy trail, golf, bơi, đạp xe", "compatibility": "Android và iOS", "water_resistance": "10 ATM", "screen_technology": "MIP chống chói, hỗ trợ năng lượng mặt trời"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.9, 76, 'Hot'),
    ('IP16PM', 'iphone-16-pro-max', 'iPhone 16 Pro Max', 'smartphones', 'phone-flagship', 'Apple', 36990000, 33990000, 19, 'https://images.unsplash.com/photo-1727371978250-b0c6114eb384?w=600&auto=format&fit=crop', '{"os": "iOS 18", "cpu": "6 nhân (2 nhân hiệu năng + 4 nhân tiết kiệm điện)", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Apple GPU 6 nhân", "nfc": "Có", "ram": "8GB", "sim": "SIM kép (Nano-SIM và eSIM)", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Loa kép Stereo, Dolby Atmos", "weight": "227 g", "battery": "4685 mAh", "network": "5G, 4G LTE", "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển, Gia tốc kế", "storage": "256GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W", "infrared": "Không", "material": "Khung Titanium cấp độ 5, Mặt lưng kính cường lực nhám", "bluetooth": "Bluetooth 5.3", "processor": "Apple A18 Pro", "brightness": "Tối đa 2000 nits", "dimensions": "163.0 x 77.6 x 8.25 mm", "rear_video": "4K Dolby Vision ở tốc độ 24/25/30/60/100/120 fps", "resolution": "2868 x 1320 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48 MP & Phụ 48 MP, 12 MP", "screen_size": "6.9 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình Dynamic Island", "front_camera": "12 MP", "refresh_rate": "120Hz", "release_time": "09/2024", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C (USB 3)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Titanium cấp độ 5", "video_recording": "4K@120fps Dolby Vision", "_variantSpecKeys": [], "display_features": "HDR, True Tone, Always-On Display, Kính Ceramic Shield thế hệ mới", "special_features": "Nút Action, Điều khiển Camera (Camera Control), Apple Intelligence", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "Zoom quang học 5x, OIS chuyển dịch cảm biến, Deep Fusion, Smart HDR 5"}'::jsonb, '[{"code": "#c7a889", "name": "Titan Sa mạc"}, {"code": "#343434", "name": "Titan đen"}]'::jsonb, '["256GB", "512GB", "1TB"]'::jsonb, TRUE, TRUE, 4.9, 245, 'Hot'),
    ('MBAIRM3', 'macbook-air-m3', 'MacBook Air M3 13 inch', 'laptops', 'macbook', 'Apple', 29990000, 27490000, 16, 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop', '{"ram": "8GB", "weight": "1.24 kg", "storage": "256GB SSD", "processor": "Apple M3", "screen_size": "13.6 inch", "_variantSpecKeys": ["ram", "storage"]}'::jsonb, '[]'::jsonb, '["256GB", "512GB"]'::jsonb, TRUE, TRUE, 4.8, 220, 'Hot'),
    ('IPADM4', 'ipad-pro-m4', 'iPad Pro M4 11 inch', 'tablets', 'tablet-pro', 'Apple', 31990000, 28990000, 10, 'https://placehold.co/600x600/f8fafc/0f172a?text=iPad+Pro+M4', '{"storage": "256GB", "processor": "Apple M4", "screen_size": "11 inch OLED"}'::jsonb, '[{"code": "#d1d5db", "name": "Bạc"}, {"code": "#111827", "name": "Đen"}]'::jsonb, '["256GB", "512GB", "1TB", "1TB Nano", "2TB", "2TB Nano"]'::jsonb, TRUE, FALSE, 4.9, 156, 'Hot'),
    ('APP2USBC', 'airpods-pro-2-usbc', 'AirPods Pro 2 USB-C', 'accessories', 'audio-tws', 'Apple', 6790000, 5490000, 30, 'https://placehold.co/600x600/f8fafc/0f172a?text=AirPods+Pro+2', '{"color": "Trắng", "weight": "Khoảng 5.3 g mỗi tai nghe", "battery": "Tối đa 6 giờ nghe nhạc; hộp sạc đến 30 giờ", "material": "Nhựa cao cấp", "microphone": "Micro beamforming kép", "audio_codec": "Adaptive EQ, Spatial Audio", "connectivity": "Bluetooth 5.3, chip Apple H2", "compatibility": "iPhone, iPad, Mac, Apple Watch và thiết bị Bluetooth", "accessory_type": "Tai nghe true wireless", "water_resistance": "IP54 cho tai nghe và hộp sạc", "charging_standard": "USB-C, sạc không dây MagSafe/Qi", "noise_cancellation": "Chống ồn chủ động, xuyên âm thích ứng"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, TRUE, 4.8, 534, 'Hot'),
    ('IP17PM', 'iphone-17-pro-max', 'iPhone 17 Pro Max', 'smartphones', 'phone-flagship', 'Apple', 34990000, 30990000, 120, '/images/products/iphone-17-pro/cosmic-orange/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS, BeiDou", "gpu": "GPU 6 lõi", "nfc": "Có", "ram": "12GB", "sim": "Sim kép (nano-Sim và e-Sim) - Hỗ trợ 2 e-Sim", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "231 g", "battery": "4828 mAh", "network": "5G", "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB / 1TB / 2TB", "charging": "Sạc không dây MagSafe lên đến 25W; sạc không dây Qi2 lên đến 25W", "infrared": "Không", "material": "Khung Titanium, Mặt lưng kính", "bluetooth": "Bluetooth 6.0", "processor": "Chip A19 Pro", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "163.4 x 78.0 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60/100/120 fps, ProRes 4K 120 fps", "resolution": "2868 x 1320 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP & Phụ 48MP, 48MP", "screen_size": "6.9 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 6.0, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "Camera 18MP Center Stage", "refresh_rate": "120Hz", "release_time": "09/2025", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C (hỗ trợ USB 3 lên đến 10Gb/s)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Titanium chuẩn hàng không vũ trụ", "video_recording": "4K Dolby Vision 24/25/30/60/100/120 fps, ProRes 4K 120 fps", "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Độ sáng HDR 1600 nits, Độ sáng ngoài trời 3000 nits", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control), SOS khẩn cấp, Phát hiện va chạm", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS thế hệ 2, Flash True Tone Thích Ứng, Photonic Engine, Deep Fusion, HDR 5, Chế độ Ban Đêm"}'::jsonb, '[{"code": "#f26b2f", "name": "Cam Vũ Trụ"}, {"code": "#24364b", "name": "Xanh Sâu"}, {"code": "#d9d9d4", "name": "Bạc"}]'::jsonb, '["256GB", "512GB", "1TB", "2TB"]'::jsonb, TRUE, FALSE, 0.0, 0, 'New'),
    ('IP17P', 'iphone-17-pro', 'iPhone 17 Pro', 'smartphones', 'phone-flagship', 'Apple', 29990000, 28990000, 100, '/images/products/iphone-17-pro/cosmic-orange/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS, BeiDou", "gpu": "GPU 6 lõi", "nfc": "Có", "ram": "12 GB LPDDR5X", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "206 g", "battery": "Khoảng 3500 mAh", "network": "5G Advanced", "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB / 1TB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Titanium nguyên khối, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 6.0", "processor": "Apple A19 Pro (Tiến trình 2nm)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60/100/120 fps, 1080p 25/30/60/120 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.78 + Siêu rộng 48MP ƒ/2.2 + Telephoto 48MP ƒ/2.8 (Zoom quang học 4x)", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 6.0, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C (hỗ trợ USB 3 lên đến 10Gb/s)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Titanium chuẩn hàng không vũ trụ", "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR, ProRes 4K 120 fps", "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1, Độ sáng HDR 1600 nits, Độ sáng ngoài trời 3000 nits", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control), SOS khẩn cấp, Phát hiện va chạm", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS thế hệ 2, Flash True Tone Thích Ứng, Photonic Engine, Deep Fusion, HDR 5, Chế độ Ban Đêm"}'::jsonb, '[{"code": "#f26b2f", "name": "Cam Vũ Trụ"}, {"code": "#24364b", "name": "Xanh Sâu"}, {"code": "#d9d9d4", "name": "Bạc"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('IP17', 'iphone-17', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 60, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[{"code": "#333333", "name": "Đen"}, {"code": "#f5f5f5", "name": "Trắng"}, {"code": "#a9bce0", "name": "Xanh Sương Mù"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('S26U', 'samsung-galaxy-s26-ultra', 'Samsung Galaxy S26 Ultra', 'smartphones', 'phone-foldable', 'Samsung', 33990000, 31990000, 150, '/images/products/galaxy-s26-ultra/main.png', '{"os": "Android 16, One UI 8.5", "cpu": "8 lõi", "gps": "GPS, GLONASS, BDS, GALILEO, QZSS", "gpu": "Adreno", "nfc": "Có", "ram": "12 GB / 16 GB", "sim": "2 Nano SIM hoặc 2 eSIM", "wifi": "Wi-Fi 7", "audio": "Loa Stereo kép, tinh chỉnh bởi AKG, hỗ trợ Dolby Atmos", "weight": "232 g", "battery": "5000 mAh", "network": "5G", "sensors": "Cảm biến vân tay siêu âm, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu, cảm biến Hall", "storage": "256GB / 512GB / 1TB", "charging": "Sạc nhanh 60W có dây, 15W không dây", "infrared": "Không", "material": "Khung Titanium, Mặt kính Corning Gorilla Armor 2", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Elite Gen 5 for Galaxy", "brightness": "Tối đa 3000 nits", "dimensions": "162.3 x 79.0 x 8.6 mm", "rear_video": "8K@30fps, 4K@30/60/120fps, 1080p@30/60/240fps, HDR10+, gyro-EIS", "resolution": "1440 x 3120 pixels", "fingerprint": "Siêu âm dưới màn hình", "front_video": "4K@30/60fps, 1080p@30fps", "rear_camera": "200MP chính + 50MP Góc siêu rộng + 50MP Tiềm vọng 5x + 10MP Tele 3x", "screen_size": "6.9 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, GPS, NFC", "display_type": "Màn hình đục lỗ (Infinity-O), phẳng hoàn toàn", "front_camera": "12MP khẩu độ f/2.2", "refresh_rate": "120Hz (Adaptive)", "release_time": "02/2026", "back_material": "Kính cường lực Corning Gorilla Armor 2", "charging_port": "USB Type-C 3.2", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Titanium", "video_recording": "8K@30fps, 4K@30/60/120fps, 1080p@30/60/240fps", "display_features": "Tần số quét thích ứng 1-120Hz, Always-On Display, HDR10+, Vision Booster", "special_features": "Galaxy AI toàn diện, Bút S Pen tích hợp, Samsung DeX, Knox Security", "water_resistance": "IP68", "screen_technology": "Dynamic AMOLED 2X, 1-120Hz, HDR10+", "rear_camera_features": "Zoom quang 3x & 5x, Zoom Space 100x, OIS góc rộng & tele, Laser AF, Nightography nâng cao"}'::jsonb, '[{"code": "#2f3133", "name": "Đen Classic"}, {"code": "#726b8e", "name": "Tím Cobalt"}, {"code": "#f1f0ee", "name": "Trắng Classic"}, {"code": "#87ceeb", "name": "Xanh Sky Blue"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('S26', 'samsung-galaxy-s26', 'Samsung Galaxy S26', 'smartphones', 'phone-foldable', 'Samsung', 22990000, 21990000, 200, '/images/products/galaxy-s26/den.png', '{"os": "Android 16, One UI 8.5", "cpu": "8 lõi", "gps": "GPS, GLONASS, BDS, GALILEO", "gpu": "Adreno / Xclipse", "nfc": "Có", "ram": "12 GB", "sim": "2 Nano SIM hoặc 2 eSIM", "wifi": "Wi-Fi 7", "audio": "Loa Stereo kép, hỗ trợ Dolby Atmos", "weight": "168 g", "battery": "4300 mAh", "network": "5G", "sensors": "Cảm biến vân tay siêu âm, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W có dây, 15W không dây", "infrared": "Không", "material": "Khung nhôm Armor Aluminum, Mặt kính Corning Gorilla Glass Armor 2", "bluetooth": "Bluetooth 5.3", "processor": "Qualcomm Snapdragon 8 Elite Gen 5 / Exynos 2600", "brightness": "Tối đa 2600 nits", "dimensions": "147.0 x 70.6 x 7.6 mm", "rear_video": "8K@30fps, 4K@30/60fps, 1080p@30/60/240fps, HDR10+, gyro-EIS", "resolution": "1080 x 2340 pixels", "fingerprint": "Siêu âm dưới màn hình", "front_video": "4K@30/60fps, 1080p@30fps", "rear_camera": "50MP chính + 12MP Siêu rộng + 10MP Tele 3x", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.3, GPS, NFC", "display_type": "Màn hình đục lỗ (Infinity-O), phẳng hoàn toàn", "front_camera": "12MP", "refresh_rate": "120Hz", "release_time": "02/2026", "back_material": "Kính cường lực Corning Gorilla Glass Armor 2", "charging_port": "USB Type-C 3.2", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Nhôm Armor Aluminum", "video_recording": "8K@30fps, 4K@30/60fps, 1080p@30/60/240fps", "display_features": "Tần số quét thích ứng 1-120Hz, Always-On Display, HDR10+, Vision Booster", "special_features": "Galaxy AI, Samsung DeX, Knox Security", "water_resistance": "IP68", "screen_technology": "Dynamic AMOLED 2X, 120Hz, HDR10+", "rear_camera_features": "Zoom quang 3x, OIS góc rộng & tele, Nightography"}'::jsonb, '[{"code": "#1a1a1a", "name": "Đen Classic"}, {"code": "#726b8e", "name": "Tím Cobalt"}, {"code": "#87ceeb", "name": "Xanh Sky Blue"}, {"code": "#fdfdfd", "name": "Trắng Classic"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('A17-5G', 'samsung-galaxy-a17-5g', 'Samsung Galaxy A17 5G', 'smartphones', 'phone-foldable', 'Samsung', 5490000, 4990000, 300, 'https://placehold.co/600x600/1a1a1a/ffffff?text=Galaxy+A17+Den', '{"os": "Android 15, One UI 7.0", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G68", "nfc": "Có", "ram": "6 GB / 8 GB", "sim": "2 Nano SIM (Hỗ trợ thẻ nhớ microSD lên đến 2TB)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa đơn, giắc cắm tai nghe 3.5mm", "weight": "195 g", "battery": "5000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB", "charging": "Sạc nhanh 25W", "infrared": "Không", "material": "Khung nhựa, Mặt lưng nhựa nhám, Kính Gorilla Glass Victus", "bluetooth": "Bluetooth 5.3", "processor": "Exynos 1330", "brightness": "Tối đa 1200 nits", "dimensions": "164.2 x 77.9 x 7.9 mm", "rear_video": "1080p@30/60fps", "resolution": "1080 x 2340 pixels (FHD+)", "fingerprint": "Mở khóa vân tay cạnh viền", "front_video": "1080p@30fps", "rear_camera": "50MP chính + 5MP Siêu rộng + 2MP Macro", "screen_size": "6.7 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS", "display_type": "Giọt nước (Infinity-U)", "front_camera": "13MP", "refresh_rate": "90Hz", "release_time": "08/2025", "back_material": "Nhựa nhám", "charging_port": "USB Type-C 2.0", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Nhựa", "video_recording": "Quay video 1080p@30/60fps", "display_features": "Độ sáng cao, bảo vệ mắt", "special_features": "Samsung Knox, Hỗ trợ cập nhật phần mềm 6 năm", "water_resistance": "IP54 (Kháng bụi và nước nhẹ)", "screen_technology": "Super AMOLED, 90Hz", "rear_camera_features": "OIS, Tự động lấy nét, HDR, Panorama"}'::jsonb, '[{"code": "#1a1a1a", "name": "Đen"}, {"code": "#8a9eb3", "name": "Xanh Lam"}, {"code": "#808080", "name": "Xám"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('A57-5G', 'samsung-galaxy-a57-5g', 'Samsung Galaxy A57 5G', 'smartphones', 'phone-foldable', 'Samsung', 9990000, 9490000, 250, 'https://placehold.co/600x600/1c2b42/ffffff?text=Galaxy+A57+Navy', '{"os": "Android 16, One UI 8.5", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Xclipse GPU", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM hoặc 1 SIM + 1 eSIM", "wifi": "Wi-Fi 6E", "audio": "Loa kép Stereo, Dolby Atmos", "weight": "192 g", "battery": "5000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay dưới màn hình, gia tốc, con quay hồi chuyển, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB / 512 GB", "charging": "Sạc nhanh siêu tốc 45W", "infrared": "Không", "material": "Khung nhôm, Mặt lưng kính, Mặt kính Gorilla Glass Victus+", "bluetooth": "Bluetooth 6.0", "processor": "Exynos 1680 (Tiến trình 4nm)", "brightness": "Tối đa 1200 nits", "dimensions": "161.5 x 76.9 x 6.9 mm", "rear_video": "4K@30fps, 1080p@30/60fps, gyro-EIS", "resolution": "1080 x 2340 pixels (FHD+)", "fingerprint": "Quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30fps", "rear_camera": "50MP chính (OIS) + 12MP Siêu rộng + 5MP Macro", "screen_size": "6.7 inches", "connectivity": "Wi-Fi 6E, Bluetooth 6.0, NFC, GPS", "display_type": "Màn hình đục lỗ (Infinity-O)", "front_camera": "12MP", "refresh_rate": "120Hz", "release_time": "03/2026", "back_material": "Kính", "charging_port": "USB Type-C 2.0", "compatibility": "Android, Galaxy Watch, Galaxy Buds", "frame_material": "Nhôm", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps, gyro-EIS", "display_features": "Độ sáng tối đa 1200 nits, Always-on display, Vision Booster", "special_features": "Samsung Knox Vault, Hỗ trợ cập nhật hệ điều hành 6 năm, Galaxy AI (một số tính năng)", "water_resistance": "IP67 (Kháng bụi và nước ở độ sâu 1m trong 30 phút)", "screen_technology": "Super AMOLED+, 120Hz, HDR10+", "rear_camera_features": "OIS, VDIS, Nightography, Tự động lấy nét, HDR, Chụp chân dung"}'::jsonb, '[{"code": "#1c2b42", "name": "Xanh Navy"}, {"code": "#888888", "name": "Xám"}, {"code": "#d4b8e2", "name": "Tím Lilac"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('RM-N14PP', 'xiaomi-redmi-note-14-pro-plus-5g', 'Xiaomi Redmi Note 14 Pro+ 5G', 'smartphones', 'phone-flagship', 'Xiaomi', 8490000, 7990000, 300, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Redmi+Note+14+Pro+Plus+Den', '{"os": "Android 14, HyperOS", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 710", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G kép)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo, Dolby Atmos, Hi-Res Audio", "weight": "204.5 g", "battery": "5110 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, tiệm cận ảo", "storage": "256 GB / 512 GB", "charging": "Sạc nhanh 120W (Sạc đầy 100% trong khoảng 19 phút)", "infrared": "Có (Cổng hồng ngoại)", "material": "Khung hợp kim, Mặt lưng kính hoặc da sinh thái", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 7s Gen 3 (4 nm)", "brightness": "Tối đa 3000 nits", "dimensions": "161.4 x 74.2 x 8.9 mm", "rear_video": "4K@24/30fps, 1080p@30/60/120fps, gyro-EIS, OIS", "resolution": "1220 x 2712 pixels (1.5K)", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30/60fps", "rear_camera": "200MP chính (OIS) + 8MP Siêu rộng + 2MP Macro", "screen_size": "6.67 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình cong tràn viền, Đục lỗ", "front_camera": "20MP", "refresh_rate": "120Hz", "release_time": "01/2025", "back_material": "Kính / Da sinh thái", "charging_port": "USB Type-C 2.0", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "Quay video 4K@24/30fps, 1080p@30/60/120fps, gyro-EIS, OIS", "display_features": "Độ sáng tối đa 3000 nits, PWM dimming 1920Hz, Kính cường lực Corning Gorilla Glass Victus 2", "special_features": "Hệ thống làm mát VC lớn, Động cơ rung trục X", "water_resistance": "IP68 (Kháng bụi và nước ở độ sâu 1.5m trong 30 phút)", "screen_technology": "AMOLED, 68 tỷ màu, 120Hz, Dolby Vision, HDR10+", "rear_camera_features": "OIS, Lấy nét tự động theo pha, Dual-LED dual-tone flash, HDR, Panorama"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Tinh Tú"}, {"code": "#b4a7d6", "name": "Tím Oải Hương"}, {"code": "#c9e2f5", "name": "Xanh Băng Giá"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('RM-N15', 'xiaomi-redmi-note-15-5g', 'Xiaomi Redmi Note 15 5G', 'smartphones', 'phone-flagship', 'Xiaomi', 5490000, 4990000, 500, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Redmi+Note+15+Den', '{"os": "Android 15, HyperOS", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Adreno", "nfc": "Có", "ram": "8 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép Stereo, giắc cắm tai nghe 3.5mm", "weight": "188 g", "battery": "5520 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB", "charging": "Sạc nhanh 45W", "infrared": "Có", "material": "Khung nhựa, Mặt lưng kính hoặc nhựa giả kính", "bluetooth": "Bluetooth 5.3", "processor": "Qualcomm Snapdragon 6 Gen 3", "brightness": "Tối đa 3200 nits", "dimensions": "162.2 x 75.6 x 7.9 mm", "rear_video": "1080p@30/60fps", "resolution": "1080 x 2392 pixels (FHD+)", "fingerprint": "Vân tay cạnh viền", "front_video": "1080p@30fps", "rear_camera": "108MP chính + 8MP siêu rộng + 2MP macro", "screen_size": "6.77 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình đục lỗ", "front_camera": "20MP", "refresh_rate": "120Hz", "release_time": "01/2026", "back_material": "Kính / Nhựa", "charging_port": "USB Type-C 2.0", "compatibility": "Android", "frame_material": "Nhựa", "video_recording": "Quay video 1080p@30/60fps", "display_features": "Độ sáng tối đa 3200 nits, Bảo vệ mắt TUV Rheinland", "special_features": "Cổng hồng ngoại điều khiển thiết bị, tản nhiệt nâng cấp", "water_resistance": "IP54 (Kháng bụi và nước nhẹ)", "screen_technology": "AMOLED, 120Hz", "rear_camera_features": "Tự động lấy nét, HDR, Panorama, Night Mode"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Huyền Bí"}, {"code": "#a9cce3", "name": "Xanh Sông Băng"}, {"code": "#c39bd3", "name": "Tím Sương Mù"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('POCO-X7P', 'xiaomi-poco-x7-pro-5g', 'Xiaomi POCO X7 Pro 5G', 'smartphones', 'phone-flagship', 'Xiaomi', 7990000, 7490000, 400, 'https://placehold.co/600x600/ffd100/1a1a1c?text=POCO+X7+Pro+Vang', '{"os": "Android 15, HyperOS 2", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Mali-G615 MC6", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo, Hi-Res Audio", "weight": "207 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, tiệm cận ảo", "storage": "256 GB", "charging": "Sạc nhanh HyperCharge 90W", "infrared": "Có (Cổng hồng ngoại)", "material": "Khung hợp kim, Mặt lưng kính hoặc nhựa giả da", "bluetooth": "Bluetooth 5.4", "processor": "MediaTek Dimensity 8400-Ultra (Tiến trình tiên tiến)", "brightness": "Tối đa 3200 nits", "dimensions": "161.4 x 74.2 x 8.9 mm", "rear_video": "4K@24/30/60fps, 1080p@30/60/120/240fps, gyro-EIS", "resolution": "1220 x 2712 pixels (1.5K)", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30/60fps", "rear_camera": "50MP chính (Sony IMX882, OIS) + 8MP Siêu rộng", "screen_size": "6.67 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình phẳng, Đục lỗ", "front_camera": "20MP", "refresh_rate": "120Hz", "release_time": "01/2025", "back_material": "Kính / Nhựa giả da", "charging_port": "USB Type-C 2.0", "compatibility": "Android", "frame_material": "Hợp kim / Nhựa", "video_recording": "Quay video 4K@24/30/60fps, 1080p@30/60/120/240fps, gyro-EIS", "display_features": "Độ sáng tối đa 3200 nits, Bảo vệ Corning Gorilla Glass 7i", "special_features": "Hệ thống làm mát buồng hơi lớn, Động cơ rung tuyến tính trục X, Game Turbo", "water_resistance": "IP68/IP69 (Kháng bụi và kháng nước áp lực cao)", "screen_technology": "AMOLED, 68 tỷ màu, 120Hz, Dolby Vision, HDR10+", "rear_camera_features": "OIS, PDAF, LED flash, HDR, Panorama"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Hắc Diệu"}, {"code": "#1c4a3e", "name": "Xanh Tinh Vân"}, {"code": "#ffd100", "name": "Vàng POCO"}]'::jsonb, '[{"name": "RAM 8GB - 256GB"}, {"name": "RAM 12GB - 256GB"}]'::jsonb, FALSE, TRUE, 0.0, 0, NULL),
    ('XM-17U', 'xiaomi-17-ultra-5g', 'Xiaomi 17 Ultra 5G', 'smartphones', 'phone-flagship', 'Xiaomi', 34990000, 32990000, 100, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Xiaomi+17+Ultra+Den', '{"os": "Android, HyperOS 2", "cpu": "8 lõi", "gps": "L1+L5 GPS, GLONASS, GALILEO, BDS, QZSS, NavIC", "gpu": "Adreno (Thế hệ mới)", "nfc": "Có", "ram": "16 GB", "sim": "2 Nano SIM / eSIM", "wifi": "Wi-Fi 7", "audio": "Loa kép Stereo, Dolby Atmos, Hi-Res & Hi-Res Wireless", "weight": "220 g", "battery": "6800 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay siêu âm, gia tốc, con quay hồi chuyển, la bàn, cảm biến màu sắc, áp kế", "storage": "512 GB / 1 TB", "charging": "Sạc nhanh 90W có dây, 50W không dây", "infrared": "Có (Cổng hồng ngoại)", "material": "Khung Titanium/Nhôm nguyên khối, Mặt lưng Kính/Da nhân tạo/Gốm", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Elite Gen 5 (Tiến trình siêu nhỏ)", "brightness": "Tối đa 3500 nits", "dimensions": "161.4 x 75.3 x 8.29 mm", "rear_video": "8K@24/30fps, 4K@24/30/60/120fps, Dolby Vision HDR 10-bit rec., gyro-EIS", "resolution": "1440 x 3200 pixels (2K+)", "fingerprint": "Siêu âm dưới màn hình", "front_video": "4K@30/60fps", "rear_camera": "Chính 1-inch (Leica) + 200MP Telephoto (Zoom quang học) + Siêu rộng 14mm", "screen_size": "6.9 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình phẳng tràn viền", "front_camera": "32MP", "refresh_rate": "120Hz", "release_time": "02/2026", "back_material": "Da nano / Kính cường lực / Gốm", "charging_port": "USB Type-C 3.2 Gen 2", "compatibility": "Android", "frame_material": "Hợp kim / Titanium", "video_recording": "Quay video 8K@24/30fps, 4K@24/30/60/120fps, Dolby Vision HDR 10-bit rec., gyro-EIS", "display_features": "Độ sáng cực đại 3500 nits, PWM dimming 2160Hz, Xiaomi Shield Glass 3.0", "special_features": "Chip hình ảnh Surge độc quyền, Vệ tinh liên lạc kép, Camera siêu cấp", "water_resistance": "IP68 (Kháng bụi và kháng nước sâu 1.5m)", "screen_technology": "OLED LTPO, 1-120Hz, 68 tỷ màu, Dolby Vision, HDR10+", "rear_camera_features": "Ống kính Leica Summilux, Khẩu độ thay đổi vô cấp, OIS đa trục, Laser AF"}'::jsonb, '[{"code": "#f5f5f5", "name": "Trắng"}, {"code": "#1a1a1c", "name": "Đen"}, {"code": "#6e6270", "name": "Tím"}, {"code": "#41514e", "name": "Xanh Rêu"}]'::jsonb, '[{"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('OP-FX9S', 'oppo-find-x9s', 'OPPO Find X9s', 'smartphones', 'phone-flagship', 'OPPO', 19990000, 18990000, 150, '/images/products/oppo-find-x9s/sky-gray/cover.webp', '{"os": "Android 16, ColorOS 16", "cpu": "8 lõi", "gps": "GPS (L1+L5), GLONASS, GALILEO, BDS, QZSS", "gpu": "Mali-G720 (hoặc tương đương thế hệ mới)", "nfc": "Có", "ram": "12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G kép)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6/7", "audio": "Loa kép Stereo", "weight": "Khoảng 200 g", "battery": "7025 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, quang phổ", "storage": "256 GB / 512 GB", "charging": "Sạc nhanh 80W có dây", "infrared": "Có", "material": "Khung nhôm, Mặt lưng kính hoặc Da sinh thái", "bluetooth": "Bluetooth 5.4", "processor": "MediaTek Dimensity 9500s (Tiến trình cao cấp)", "brightness": "Tối đa 3600 nits", "dimensions": "Mỏng nhẹ (đang cập nhật chi tiết)", "rear_video": "4K@30/60fps, 1080p@30/60/240fps, gyro-EIS, HDR, 10-bit video", "resolution": "1256 x 2760 pixels", "fingerprint": "Siêu âm / Quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30fps", "rear_camera": "50MP chính (OIS) + 50MP Siêu rộng + 50MP Periscope Tele (3x Zoom)", "screen_size": "6.59 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình tràn viền", "front_camera": "32MP", "refresh_rate": "120Hz", "release_time": "05/2026", "back_material": "Kính / Da sinh thái", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "Quay video 4K@30/60fps, 1080p@30/60/240fps, gyro-EIS, HDR, 10-bit video", "display_features": "Độ sáng tối đa 3600 nits, Bảo vệ Corning Gorilla Glass", "special_features": "Hasselblad Camera for Mobile, Siêu pin 7025mAh", "water_resistance": "IP66 / IP68 / IP69 (Kháng nước, kháng bụi chuẩn cao cấp nhất)", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz, HDR10+", "rear_camera_features": "Hiệu chỉnh màu Hasselblad, OIS, PDAF, Panorama, HDR"}'::jsonb, '[{"code": "#a28ab7", "name": "Tím Lavender"}, {"code": "#363636", "name": "Xám Bầu Trời"}, {"code": "#e57f3d", "name": "Cam Hoàng Hôn"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('OP-FN6-OR-1TB', 'oppo-find-n6', 'OPPO Find N6', 'smartphones', 'phone-flagship', 'OPPO', 39990000, 38990000, 80, '/images/products/oppo-find-n6/orange/cover.jpg', '{"os": "Android 16, ColorOS 16 (Tối ưu cho màn hình gập)", "cpu": "7 lõi / 8 lõi (Tùy phiên bản)", "gps": "GPS (L1+L5), GLONASS, GALILEO, BDS", "gpu": "Adreno (Thế hệ mới)", "nfc": "Có", "ram": "12 GB / 16 GB", "sim": "2 Nano SIM / eSIM", "wifi": "Wi-Fi 7", "audio": "Loa kép Stereo đa hướng, Dolby Atmos", "weight": "Khoảng 239 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, cảm biến màu, khí áp kế", "storage": "512 GB / 1 TB", "charging": "Sạc nhanh 80W có dây, 50W không dây (AIRVOOC)", "infrared": "Có", "material": "Bản lề Titanium Flexion Hinge Gen 2, Khung hợp kim, Kính bảo vệ siêu mỏng", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Elite Gen 5 (Tiến trình 3nm siêu mượt)", "brightness": "Tối đa 3000 nits", "dimensions": "Mỏng nhẹ vượt trội (đang cập nhật chi tiết)", "rear_video": "8K@30fps, 4K@30/60/120fps, HDR10+, gyro-EIS", "resolution": "Đang cập nhật (Chuẩn QHD+)", "fingerprint": "Vân tay siêu âm / quang học (Cạnh viền)", "front_video": "4K@30/60fps", "rear_camera": "200MP siêu nét (Hasselblad) + 50MP Siêu rộng + 50MP Telephoto", "screen_size": "Chính: 8.12 inches | Phụ: 6.62 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình gập (Foldable)", "front_camera": "20MP (Màn hình trong) + 20MP (Màn hình ngoài)", "refresh_rate": "120Hz (Thích ứng)", "release_time": "03/2026", "back_material": "Kính / Da", "charging_port": "USB Type-C 3.2 Gen 1", "compatibility": "Android", "frame_material": "Hợp kim / Titanium", "video_recording": "Quay video 8K@30fps, 4K@30/60/120fps, HDR10+, gyro-EIS", "display_features": "Công nghệ nếp gấp tàng hình (Zero-Feel Crease), 1 tỷ màu, Dolby Vision, HDR10+", "special_features": "Hỗ trợ bút cảm ứng OPPO AI Pen, Tính năng đa nhiệm chia màn hình thông minh", "water_resistance": "IP56/IP58/IP59 (Kháng nước và kháng bụi siêu đỉnh)", "screen_technology": "LTPO OLED có thể gập lại (Chính), OLED (Phụ), 120Hz", "rear_camera_features": "Hasselblad Color Calibration, OIS đa trục, Zoom quang học, Macro"}'::jsonb, '[{"code": "#8a8d8f", "name": "Titan Ánh Sao"}, {"code": "#fca172", "name": "Cam Nở Rộ"}]'::jsonb, '[{"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('OP-RN15F-PK-8-256', 'oppo-reno15-f-5g', 'OPPO Reno15 F 5G', 'smartphones', 'phone-flagship', 'OPPO', 8490000, 7990000, 200, '/images/products/oppo-reno-15-f-5g/pink/cover.webp', '{"os": "Android 16, ColorOS 16", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo", "weight": "Khoảng 185 g", "battery": "6500 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, la bàn, con quay hồi chuyển, tiệm cận ảo", "storage": "256 GB", "charging": "Sạc siêu nhanh SUPERVOOC 80W", "infrared": "Có", "material": "Khung viền hợp kim, Mặt lưng Kính/Nhựa", "bluetooth": "Bluetooth 5.3", "processor": "Qualcomm Snapdragon 6 Gen 1", "brightness": "Tối đa 1400 nits", "dimensions": "Đang cập nhật chi tiết", "rear_video": "4K@30fps, 1080p@30/60fps", "resolution": "1080 x 2372 pixels (FHD+)", "fingerprint": "Vân tay quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30/60fps", "rear_camera": "50MP chính + 8MP Siêu rộng + 2MP Macro", "screen_size": "6.57 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình phẳng đục lỗ", "front_camera": "50MP (Góc siêu rộng)", "refresh_rate": "120Hz", "release_time": "01/2026", "back_material": "Nhựa tổng hợp cao cấp / Kính", "charging_port": "USB Type-C 2.0", "compatibility": "Android", "frame_material": "Hợp kim / Nhựa", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps", "display_features": "Độ sáng cực đại 1400 nits, Bảo vệ Corning Gorilla Glass+", "special_features": "Thiết kế siêu mỏng nhẹ với pin khủng, Viền sáng Halo (Halo Light)", "water_resistance": "IP68/IP69 (Kháng nước và bụi siêu việt)", "screen_technology": "AMOLED, 120Hz", "rear_camera_features": "Tự động lấy nét, LED flash, HDR, Chụp đêm sắc nét"}'::jsonb, '[{"code": "#ffb6c1", "name": "Hồng Rực Rỡ"}, {"code": "#add8e6", "name": "Xanh Nhạt"}, {"code": "#2196f3", "name": "Xanh Dương"}]'::jsonb, '[{"name": "RAM 8GB - 256GB"}, {"name": "RAM 12GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('OP-FX9U', 'oppo-find-x9-ultra', 'OPPO Find X9 Ultra', 'smartphones', 'phone-flagship', 'OPPO', 34990000, 33990000, 60, '/images/products/oppo-find-x9-ultra/brown/cover.webp', '{"os": "Android 16, ColorOS 16", "cpu": "8 lõi", "gps": "L1+L5 GPS, GLONASS, GALILEO, BDS, QZSS, NavIC", "gpu": "Adreno", "nfc": "Có", "ram": "12 GB / 16 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 7", "audio": "Loa kép Stereo cao cấp, Dolby Atmos, Hi-Res Audio", "weight": "Khoảng 225 g", "battery": "7050 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay siêu âm, gia tốc, con quay hồi chuyển, la bàn, quang phổ màu", "storage": "512 GB / 1 TB", "charging": "Sạc siêu nhanh 100W có dây, 50W không dây", "infrared": "Có (Cổng hồng ngoại)", "material": "Khung hợp kim Titanium, Mặt lưng Da nhân tạo cao cấp", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Elite Gen 5 (Tiến trình cực tối ưu)", "brightness": "Tối đa 3600 nits", "dimensions": "Đang cập nhật chi tiết (Thiết kế liền mạch)", "rear_video": "8K@30fps, 4K@30/60/120fps, HDR10+, Dolby Vision, gyro-EIS, OIS", "resolution": "1440 x 3168 pixels (QHD+)", "fingerprint": "Siêu âm dưới màn hình", "front_video": "4K@30/60fps", "rear_camera": "200MP chính + 200MP Tele (3x) + 50MP Tele (10x) + 50MP Siêu rộng", "screen_size": "6.82 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình cong tràn viền", "front_camera": "50MP", "refresh_rate": "144Hz (Thích ứng 1-144Hz)", "release_time": "04/2026", "back_material": "Da sinh thái", "charging_port": "USB Type-C 3.2 Gen 1", "compatibility": "Android", "frame_material": "Hợp kim / Titanium", "video_recording": "Quay video 8K@30fps, 4K@30/60/120fps, HDR10+, Dolby Vision, gyro-EIS, OIS", "display_features": "Độ sáng tối đa 3600 nits, PWM dimming cao, Corning Gorilla Glass Armor", "special_features": "Quad-camera siêu cấp, Chip xử lý hình ảnh độc quyền, Vệ tinh liên lạc", "water_resistance": "IP68/IP69 (Kháng nước và kháng bụi tuyệt đối)", "screen_technology": "LTPO AMOLED, 1 tỷ màu, 144Hz, Dolby Vision, HDR10+", "rear_camera_features": "Hệ thống Camera Hasselblad, OIS kép đa trục, Zoom quang 10x cực đại, Laser AF"}'::jsonb, '[{"code": "#463d39", "name": "Nâu Lãnh Nguyên"}, {"code": "#d46b41", "name": "Cam Hẻm Núi"}]'::jsonb, '[{"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('OP-RN15-AW-256GB', 'oppo-reno15-5g', 'OPPO Reno15 5G', 'smartphones', 'phone-flagship', 'OPPO', 11490000, 10990000, 200, '/images/products/oppo-reno-15-5g/white/cover.webp', '{"os": "Android 16, ColorOS 16", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Mali-G715 (hoặc tương đương)", "nfc": "Có", "ram": "12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo, Hi-Res Audio", "weight": "Khoảng 190 g", "battery": "6200 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, la bàn, con quay hồi chuyển, tiệm cận", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh SUPERVOOC 80W", "infrared": "Có", "material": "Khung nhôm nguyên khối, Mặt lưng Kính/Nhựa nhám", "bluetooth": "Bluetooth 5.4", "processor": "MediaTek Dimensity 8450 (Tiến trình cao cấp)", "brightness": "Tối đa 2000 nits", "dimensions": "Mỏng nhẹ (đang cập nhật chi tiết)", "rear_video": "4K@30/60fps, 1080p@30/60/120fps, gyro-EIS, OIS", "resolution": "1080 x 2412 pixels (FHD+)", "fingerprint": "Quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30/60fps", "rear_camera": "200MP chính (OIS) + 50MP Telephoto (Chân dung) + 50MP Siêu rộng", "screen_size": "6.59 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình cong 3D / Phẳng đục lỗ", "front_camera": "50MP (Góc rộng)", "refresh_rate": "120Hz", "release_time": "01/2026", "back_material": "Kính quang học cao cấp", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "Quay video 4K@30/60fps, 1080p@30/60/120fps, gyro-EIS, OIS", "display_features": "Độ sáng cực đại cao, Tần số quét 120Hz, Kính cường lực cao cấp", "special_features": "Thiết kế mỏng nhẹ tinh tế, Viền sáng Halo, Chụp chân dung AI đỉnh cao", "water_resistance": "IP69 (Kháng nước và kháng bụi siêu cường)", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz, HDR10+", "rear_camera_features": "OIS, Tự động lấy nét đa hướng, Chế độ Chân dung chuyên nghiệp AI"}'::jsonb, '[{"code": "#1a516e", "name": "Xanh Chạng Vạng"}, {"code": "#f0f2f5", "name": "Trắng Cực Quang"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('OP-FX8-BK-256GB', 'oppo-find-x8', 'OPPO Find X8', 'smartphones', 'phone-flagship', 'OPPO', 22990000, 21990000, 120, '/images/products/oppo-find-x8/black/cover.webp', '{"os": "Android 15, ColorOS 15", "cpu": "8 lõi", "gps": "GPS (L1+L5), GLONASS, GALILEO, BDS, QZSS", "gpu": "Immortalis-G925", "nfc": "Có", "ram": "12 GB / 16 GB", "sim": "2 Nano SIM (Hỗ trợ 5G kép)", "wifi": "Wi-Fi 7", "audio": "Loa kép Stereo đa hướng", "weight": "193 g", "battery": "5630 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, quang phổ", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh 80W có dây, 50W không dây từ tính", "infrared": "Có (Cổng hồng ngoại)", "material": "Khung hợp kim nhôm, Mặt lưng kính cao cấp (lớp phủ chống bám vân tay)", "bluetooth": "Bluetooth 5.4", "processor": "MediaTek Dimensity 9400 (Tiến trình 3nm siêu mạnh)", "brightness": "Tối đa 4500 nits", "dimensions": "157.4 x 74.3 x 7.85 mm", "rear_video": "4K@30/60fps, 1080p@30/60/240fps, HDR10+, gyro-EIS", "resolution": "1256 x 2760 pixels", "fingerprint": "Siêu âm / Quang học dưới màn hình", "front_video": "4K@30/60fps, 1080p@30/60fps", "rear_camera": "50MP chính (OIS) + 50MP Siêu rộng + 50MP Tele (3x Zoom)", "screen_size": "6.59 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình phẳng đục lỗ", "front_camera": "32MP", "refresh_rate": "120Hz", "release_time": "11/2024", "back_material": "Kính nhám", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "Quay video 4K@30/60fps, 1080p@30/60/240fps, HDR10+, gyro-EIS", "display_features": "Độ sáng đỉnh 4500 nits, Kính cường lực cao cấp", "special_features": "Sạc không dây từ tính, Nút chụp ảnh nhanh Camera Control", "water_resistance": "IP68/IP69 (Kháng nước và bụi đỉnh cao)", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz, Dolby Vision, HDR10+", "rear_camera_features": "Hasselblad Color Calibration, OIS đa trục, Zoom quang học 3x"}'::jsonb, '[{"code": "#666666", "name": "Xám Sao Băng"}, {"code": "#1a1a1c", "name": "Đen Không Gian"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('TC-SP50', 'tecno-spark-50-5g', 'TECNO Spark 50 5G', 'smartphones', 'phone-flagship', 'TECNO', 4490000, 3990000, 300, 'https://placehold.co/600x600/1c1c1c/ffffff?text=TECNO+Spark+50+Den', '{"os": "Android 16, HiOS 16", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G57", "nfc": "Có", "ram": "8 GB (Mở rộng thêm RAM ảo)", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép Stereo, Âm thanh vòm DTS", "weight": "Khoảng 195 g", "battery": "6500 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB", "charging": "Sạc siêu nhanh 45W", "infrared": "Không", "material": "Khung nhựa cao cấp, Mặt lưng nhựa/kính nhám", "bluetooth": "Bluetooth 5.3", "processor": "MediaTek Dimensity 6400 5G (Tiến trình 6nm tiết kiệm điện)", "brightness": "Tối đa 1200 nits", "dimensions": "Đang cập nhật chi tiết", "rear_video": "1080p@30/60fps, 2K@30fps", "resolution": "720 x 1612 pixels (HD+)", "fingerprint": "Cảm biến vân tay cạnh viền (Tích hợp nút nguồn)", "front_video": "1080p@30fps", "rear_camera": "50MP chính + Ống kính phụ AI", "screen_size": "6.78 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình phẳng đục lỗ (Dynamic Port)", "front_camera": "8MP (hoặc 16MP tuỳ thị trường)", "refresh_rate": "120Hz", "release_time": "04/2026", "back_material": "Nhựa tổng hợp cao cấp", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Nhựa cứng", "video_recording": "Quay video 1080p@30/60fps, 2K@30fps", "display_features": "Tần số quét 120Hz mượt mà, Kính cường lực chống xước tốt", "special_features": "Độ bền chuẩn quân đội, Tính năng Dynamic Port 2.0 (tương tự Dynamic Island), Âm lượng 400%", "water_resistance": "IP64 (Kháng bụi và kháng nước bắn) & Chuẩn quân đội MIL-STD-810H", "screen_technology": "IPS LCD, 120Hz", "rear_camera_features": "Dual-LED flash, HDR, Panorama, Super Night Mode"}'::jsonb, '[{"code": "#1c1c1c", "name": "Đen Mực"}, {"code": "#a2d5c6", "name": "Xanh Bạc Hà"}, {"code": "#bfa1ce", "name": "Tím Ảo Ảnh"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('TC-SP40PP', 'tecno-spark-40-pro-plus', 'TECNO Spark 40 Pro+', 'smartphones', 'phone-flagship', 'TECNO', 5490000, 4990000, 150, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Spark+40+Pro+Den', '{"os": "Android 15, HiOS 15", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G57 (hoặc tương đương thế hệ mới)", "nfc": "Có", "ram": "8 GB", "sim": "2 Nano SIM", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép Stereo", "weight": "Khoảng 190 g", "battery": "5200 mAh", "network": "4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, tiệm cận ảo", "storage": "128 GB / 256 GB", "charging": "Sạc siêu nhanh 45W có dây, 30W không dây, Sạc ngược không dây 5W", "infrared": "Có", "material": "Khung nhôm, Mặt lưng nhựa cao cấp / kính", "bluetooth": "Bluetooth 5.3", "processor": "MediaTek Helio G200 (Thế hệ chip hoàn toàn mới)", "brightness": "Tối đa 1200 nits", "dimensions": "Đang cập nhật chi tiết", "rear_video": "2K@30fps, 1080p@30/60fps", "resolution": "1224 x 2720 pixels (1.5K)", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30fps", "rear_camera": "50MP chính + Ống kính phụ", "screen_size": "6.78 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình cong tràn viền đục lỗ", "front_camera": "13MP", "refresh_rate": "144Hz", "release_time": "07/2025", "back_material": "Nhựa / Kính cường lực", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim / Nhựa", "video_recording": "Quay video 2K@30fps, 1080p@30/60fps", "display_features": "Màn hình cong thác nước sang trọng, Kính Corning Gorilla Glass 7i", "special_features": "Tiên phong dùng chip Helio G200, Hỗ trợ sạc không dây 30W", "water_resistance": "IP64 (Kháng bụi và kháng nước bắn)", "screen_technology": "AMOLED cong 3D, 144Hz", "rear_camera_features": "Tự động lấy nét, LED flash kép, Chụp đêm AI"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Tinh Vân"}, {"code": "#f5f5f5", "name": "Trắng Cực Quang"}, {"code": "#41514e", "name": "Xanh Lãnh Nguyên"}, {"code": "#8a8d8f", "name": "Titan Ánh Trăng"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('TC-PV7', 'tecno-pova-7-5g', 'TECNO Pova 7 5G', 'smartphones', 'phone-flagship', 'TECNO', 6490000, 5990000, 200, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Pova+7+Den', '{"os": "Android 15, HiOS 15", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G615", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo, Dolby Atmos", "weight": "Khoảng 210 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, la bàn, con quay hồi chuyển, tiệm cận ảo", "storage": "256 GB", "charging": "Sạc siêu nhanh 45W, Sạc không dây 30W", "infrared": "Có", "material": "Khung nhựa, Mặt lưng nhựa vân cơ khí", "bluetooth": "Bluetooth 5.3", "processor": "MediaTek Dimensity 7300 Ultimate (Tối ưu cho Game)", "brightness": "Tối đa 1200 nits", "dimensions": "Đang cập nhật chi tiết", "rear_video": "2K@30fps, 1080p@30/60fps", "resolution": "1080 x 2460 pixels (FHD+)", "fingerprint": "Cảm biến vân tay cạnh viền", "front_video": "1080p@30fps", "rear_camera": "50MP chính + Camera phụ AI", "screen_size": "6.78 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình phẳng đục lỗ", "front_camera": "13MP", "refresh_rate": "144Hz", "release_time": "07/2025", "back_material": "Nhựa cao cấp kết hợp dải đèn LED", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim / Nhựa cứng", "video_recording": "Quay video 2K@30fps, 1080p@30/60fps", "display_features": "Tần số quét 144Hz siêu mượt, Phản hồi cảm ứng siêu nhạy", "special_features": "Dải đèn LED Delta Light Interface tùy chỉnh, Hỗ trợ Sạc không dây 30W", "water_resistance": "IP64 (Kháng bụi và kháng nước bắn)", "screen_technology": "IPS LCD, 144Hz", "rear_camera_features": "Dual-LED flash, HDR, Panorama, Tối ưu hóa chụp đêm"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Geek"}, {"code": "#e0e4cc", "name": "Bạc Ma Thuật"}, {"code": "#41514e", "name": "Xanh Ốc Đảo"}]'::jsonb, '[{"name": "RAM 8GB - 256GB"}, {"name": "RAM 12GB - 256GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('HN-X9D', 'honor-x9d-5g', 'HONOR X9d 5G', 'smartphones', 'phone-flagship', 'HONOR', 7990000, 7490000, 120, '/images/products/honor-x9d/black/cover.webp', '{"os": "Android 15, MagicOS 9.0", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Adreno", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép, Âm thanh vòm", "weight": "193 g", "battery": "8300 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, tiệm cận ảo", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh 66W", "infrared": "Có", "material": "Khung polycarbonate cao cấp, Mặt lưng nhựa/kính cường lực", "bluetooth": "Bluetooth 5.3", "processor": "Qualcomm Snapdragon 6 Gen 4 (Tiến trình tiên tiến)", "brightness": "Tối đa 6000 nits", "dimensions": "161.9 x 76.1 x 7.8 mm", "rear_video": "4K@30fps, 1080p@30/60fps", "resolution": "1200 x 2640 pixels (1.5K)", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30fps", "rear_camera": "108MP chính (OIS) + 5MP Siêu rộng", "screen_size": "6.79 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình cong tràn viền đục lỗ", "front_camera": "16MP", "refresh_rate": "120Hz", "release_time": "10/2025", "back_material": "Nhựa / Da sinh thái", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim / Nhựa", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps", "display_features": "Độ sáng đỉnh 6000 nits, Kính cường lực HONOR Anti-drop Display", "special_features": "Pin dung lượng siêu khủng 8300mAh, Độ bền tiêu chuẩn siêu việt", "water_resistance": "IP69K, IP68, IP66 (Kháng nước cực mạnh) và Chống rơi vỡ 2.5m", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz", "rear_camera_features": "OIS, Tự động lấy nét theo pha (PDAF), LED flash"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Bóng Đêm"}, {"code": "#d4af37", "name": "Vàng Bình Minh"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('HN-400P', 'honor-400-pro', 'HONOR 400 Pro', 'smartphones', 'phone-flagship', 'HONOR', 16990000, 15990000, 80, '/images/products/honor-400-pro/black/cover.jpg', '{"os": "Android 15, MagicOS 9.0", "cpu": "8 lõi", "gps": "L1+L5 GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 750", "nfc": "Có", "ram": "12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 7", "audio": "Loa kép Stereo, Âm thanh chất lượng cao", "weight": "Khoảng 195 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, quang phổ màu", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh 100W có dây, 50W không dây", "infrared": "Có", "material": "Khung hợp kim, Mặt lưng kính cao cấp", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Gen 3 (Tiến trình 4nm đầu bảng)", "brightness": "Tối đa 5000 nits", "dimensions": "Đang cập nhật chi tiết (Thiết kế mỏng nhẹ tinh tế)", "rear_video": "4K@30/60fps, 1080p@30/60/120fps, gyro-EIS, OIS", "resolution": "1280 x 2800 pixels", "fingerprint": "Siêu âm / Quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30/60fps", "rear_camera": "200MP chính (OIS) + 50MP Tele (Zoom quang 3x, OIS) + 12MP Siêu rộng", "screen_size": "6.7 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình cong tràn viền đục lỗ", "front_camera": "50MP chính + 2MP Đo chiều sâu (Hỗ trợ mở khóa khuôn mặt 3D)", "refresh_rate": "120Hz (Thích ứng)", "release_time": "05/2025", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C 3.2", "compatibility": "Android", "frame_material": "Hợp kim nhôm nguyên khối", "video_recording": "Quay video 4K@30/60fps, 1080p@30/60/120fps, gyro-EIS, OIS", "display_features": "Độ sáng đỉnh 5000 nits, PWM dimming bảo vệ mắt cấp độ cao", "special_features": "Camera Tele 50MP đỉnh cao, Sạc nhanh kép 100W/50W, Pin silicon-carbon 6000mAh", "water_resistance": "IP68/IP69 (Kháng nước và bụi tuyệt đối)", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz, HDR10+", "rear_camera_features": "OIS kép, Cảm biến ánh sáng siêu nhạy, Chụp chân dung chuyên nghiệp"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Bóng Đêm"}, {"code": "#6e727b", "name": "Xám Mặt Trăng"}, {"code": "#334c6e", "name": "Xanh Thủy Triều"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('HN-MGV5', 'honor-magic-v5', 'HONOR Magic V5', 'smartphones', 'phone-flagship', 'HONOR', 41990000, 40990000, 50, '/images/products/honor-magic-v5/white/cover.jpg', '{"os": "Android 15, MagicOS 9.0 (Tối ưu màn hình gập)", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno (Thế hệ mới nhất)", "nfc": "Có", "ram": "12 GB / 16 GB", "sim": "2 Nano SIM (Hỗ trợ 5G kép)", "wifi": "Wi-Fi 7", "audio": "Hệ thống loa kép Stereo đẳng cấp, IMAX Enhanced", "weight": "Siêu nhẹ (Đang cập nhật chi tiết)", "battery": "6100 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn, phong vũ biểu, quang phổ màu", "storage": "512 GB / 1 TB", "charging": "Sạc siêu nhanh 66W có dây, 50W không dây", "infrared": "Có", "material": "Khung Titanium, Mặt lưng Kính/Da nhân tạo cao cấp", "bluetooth": "Bluetooth 5.4", "processor": "Qualcomm Snapdragon 8 Elite (Tiến trình 3nm đầu bảng)", "brightness": "Tối đa 3000 nits", "dimensions": "Mỏng chỉ ~8.8 mm khi gập", "rear_video": "8K@30fps, 4K@30/60fps, 1080p@30/60/240fps, HDR10+, gyro-EIS, OIS", "resolution": "Độ phân giải siêu cao (Tương đương 2K)", "fingerprint": "Cảm biến vân tay cạnh viền siêu nhạy", "front_video": "4K@30fps", "rear_camera": "50MP chính + 50MP Siêu rộng + 64MP Telephoto tiềm vọng", "screen_size": "Chính: 7.95 inches | Phụ: 6.43 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình gập dạng cuốn sách (Book-style Foldable)", "front_camera": "Hai camera 20MP (Màn hình chính và màn hình phụ)", "refresh_rate": "120Hz (Cả 2 màn hình)", "release_time": "07/2025", "back_material": "Kính cường lực / Da sinh thái", "charging_port": "USB Type-C 3.2", "compatibility": "Android", "frame_material": "Hợp kim Titanium siêu nhẹ", "video_recording": "Quay video 8K@30fps, 4K@30/60fps, 1080p@30/60/240fps, HDR10+, gyro-EIS, OIS", "display_features": "Độ sáng cực đại, Bản lề không nếp gấp siêu bền", "special_features": "Thiết kế siêu mỏng nhẹ số 1 thế giới, Bản lề Titanium siêu bền", "water_resistance": "IP68/IP69 (Kháng nước và bụi tuyệt đối)", "screen_technology": "Foldable OLED, 1 tỷ màu, 120Hz, Dolby Vision", "rear_camera_features": "OIS kép, Zoom quang học, Chụp thiên văn, Cảm biến ánh sáng siêu nhạy"}'::jsonb, '[{"code": "#f5f5dc", "name": "Trắng Ngà"}, {"code": "#e6c280", "name": "Vàng Bình Minh"}]'::jsonb, '[{"name": "512GB"}, {"name": "1TB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('HN-400', 'honor-400-5g', 'HONOR 400 5G', 'smartphones', 'phone-flagship', 'HONOR', 11990000, 10990000, 60, '/images/products/honor-400-5g/gold/cover.jpg', '{"os": "Android 15, MagicOS 9.0", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Adreno 720", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo", "weight": "Khoảng 185 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh 80W", "infrared": "Không", "material": "Khung hợp kim, Mặt lưng Kính cao cấp / Da sinh thái", "bluetooth": "Bluetooth 5.3", "processor": "Qualcomm Snapdragon 7 Gen 3 (Tiến trình 4nm)", "brightness": "Tối đa 5000 nits", "dimensions": "Mỏng nhẹ (Đang cập nhật chi tiết)", "rear_video": "4K@30fps, 1080p@30/60fps, gyro-EIS", "resolution": "FHD+ (Tương đương 1.5K)", "fingerprint": "Quang học dưới màn hình", "front_video": "4K@30fps, 1080p@30/60fps", "rear_camera": "200MP chính (OIS) + 12MP Siêu rộng", "screen_size": "6.55 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình cong nghệ thuật", "front_camera": "50MP", "refresh_rate": "120Hz", "release_time": "05/2025", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim / Polycarbonate", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps, gyro-EIS", "display_features": "Độ sáng cực đại 5000 nits, PWM dimming 3840Hz bảo vệ mắt", "special_features": "Camera 200MP siêu nét, Pin 6000mAh trong thiết kế mỏng nhẹ", "water_resistance": "IP65/IP66 (Kháng bụi và kháng tia nước mạnh)", "screen_technology": "AMOLED, 1 tỷ màu, 120Hz", "rear_camera_features": "Cảm biến kích thước lớn, OIS, Super Night Mode"}'::jsonb, '[{"code": "#e5d3b3", "name": "Vàng Sa Mạc"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('RM-NT60', 'realme-note-60', 'realme Note 60', 'smartphones', 'phone-flagship', 'realme', 2990000, 2790000, 400, 'https://placehold.co/600x600/1a516e/ffffff?text=realme+Note+60+Xanh', '{"os": "Android 14, Realme UI 5.0", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G57", "nfc": "Không", "ram": "4 GB / 8 GB", "sim": "2 Nano SIM", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa đơn, Có jack tai nghe 3.5mm", "weight": "187 g", "battery": "5000 mAh", "network": "4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "64 GB / 256 GB (Hỗ trợ thẻ nhớ MicroSD)", "charging": "Sạc tiêu chuẩn 10W", "infrared": "Không", "material": "Khung nhựa, Mặt lưng nhựa vân nhám", "bluetooth": "Bluetooth 5.0", "processor": "Unisoc Tiger T612 (12 nm)", "brightness": "Tối đa 1200 nits", "dimensions": "167.3 x 76.7 x 7.8 mm", "rear_video": "1080p@30fps", "resolution": "720 x 1600 pixels (HD+)", "fingerprint": "Cảm biến vân tay tích hợp nút nguồn ở cạnh bên", "front_video": "720p@30fps", "rear_camera": "32MP chính + Ống kính phụ", "screen_size": "6.74 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.0, GPS", "display_type": "Màn hình giọt nước", "front_camera": "5MP", "refresh_rate": "90Hz", "release_time": "08/2024", "back_material": "Nhựa Polycarbonate cao cấp", "charging_port": "USB Type-C 2.0", "compatibility": "Android", "frame_material": "Nhựa cứng", "video_recording": "Quay video 1080p@30fps", "display_features": "Tần số quét 90Hz, Kính bảo vệ cường lực", "special_features": "Thiết kế siêu mỏng 7.84mm, Hỗ trợ mở rộng thẻ nhớ độc lập", "water_resistance": "IP64 (Kháng bụi và nước bắn)", "screen_technology": "IPS LCD, 90Hz", "rear_camera_features": "Tự động lấy nét theo pha (PDAF), LED flash"}'::jsonb, '[{"code": "#1a516e", "name": "Xanh Viễn Du"}, {"code": "#1c1c1c", "name": "Đen Cẩm Thạch"}]'::jsonb, '[{"name": "4GB - 64GB"}, {"name": "8GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('RM-13P', 'realme-13-plus-5g', 'realme 13+ 5G', 'smartphones', 'phone-flagship', 'realme', 8490000, 7990000, 120, 'https://placehold.co/600x600/1a1a1c/ffffff?text=realme+13+Plus+Tim', '{"os": "Android 14, Realme UI 5.0", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G615", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ Dual 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6", "audio": "Loa kép Stereo, Giắc cắm 3.5mm", "weight": "185 g", "battery": "5000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn", "storage": "256 GB", "charging": "Sạc siêu nhanh 80W Ultra Charge", "infrared": "Không", "material": "Khung nhựa cao cấp, Mặt lưng vân thể thao", "bluetooth": "Bluetooth 5.4", "processor": "MediaTek Dimensity 7300 Energy 5G (4nm)", "brightness": "Tối đa 2000 nits", "dimensions": "161.7 x 74.7 x 7.6 mm", "rear_video": "4K@30fps, 1080p@30/60fps", "resolution": "1080 x 2400 pixels (FHD+)", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30fps", "rear_camera": "50MP chính (Sony LYT-600, OIS) + Ống kính phụ", "screen_size": "6.67 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.4, NFC, GPS", "display_type": "Màn hình phẳng đục lỗ", "front_camera": "16MP", "refresh_rate": "120Hz", "release_time": "08/2024", "back_material": "Nhựa Polycarbonate cao cấp họa tiết Victory", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Nhựa cứng siêu bền", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps", "display_features": "Độ sáng cực đại 2000 nits, Tốc độ lấy mẫu cảm ứng cao", "special_features": "Hệ thống tản nhiệt buồng hơi (VC) thép không gỉ, Màn hình Esport siêu sáng", "water_resistance": "IP65 (Kháng bụi và kháng nước bắn mạnh)", "screen_technology": "OLED Esports Display, 120Hz", "rear_camera_features": "OIS, Tự động lấy nét nhanh, Super Night Mode"}'::jsonb, '[{"code": "#1a1a1c", "name": "Tím Bóng Tối"}, {"code": "#3b5c47", "name": "Xanh Tốc Độ"}, {"code": "#cfb53b", "name": "Vàng Chiến Thắng"}]'::jsonb, '[{"name": "RAM 8GB - 256GB"}, {"name": "RAM 12GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('IT-RS4', 'itel-rs4', 'itel RS4', 'smartphones', 'phone-flagship', 'itel', 3490000, 3190000, 200, 'https://placehold.co/600x600/f5f5f5/333333?text=itel+RS4+Trang', '{"os": "Android 13, itel OS", "cpu": "8 lõi", "gps": "GPS", "gpu": "Mali-G57 MC2", "nfc": "Có", "ram": "8 GB / 12 GB (Hỗ trợ RAM ảo mở rộng)", "sim": "2 Nano SIM", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép âm thanh nổi (Stereo Speakers), Giắc cắm tai nghe 3.5mm", "weight": "Khoảng 190 g", "battery": "5000 mAh", "network": "4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB", "charging": "Sạc nhanh 45W (Hỗ trợ Bypass Charging - Sạc trực tiếp vào main)", "infrared": "Không", "material": "Khung nhựa cứng cáp, Mặt lưng nhựa vân thể thao / Da giả", "bluetooth": "Bluetooth 5.0", "processor": "MediaTek Helio G99 Ultimate (Tiến trình 6nm)", "brightness": "Tối đa 1200 nits", "dimensions": "Mỏng nhẹ (Đang cập nhật chi tiết)", "rear_video": "1080p@30/60fps", "resolution": "720 x 1612 pixels (HD+)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "1080p@30fps", "rear_camera": "50MP chính + Ống kính phụ AI", "screen_size": "6.56 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.0, NFC, GPS", "display_type": "Màn hình đục lỗ (Punch-hole)", "front_camera": "8MP", "refresh_rate": "120Hz", "release_time": "04/2024", "back_material": "Nhựa Polycarbonate họa tiết thể thao", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Nhựa chắc chắn", "video_recording": "Quay video 1080p@30/60fps", "display_features": "Tần số quét 120Hz siêu mượt, Hỗ trợ tốc độ lấy mẫu cảm ứng 240Hz", "special_features": "Sạc Bypass bảo vệ pin khi chơi game, Màn hình 120Hz giá cực rẻ", "water_resistance": "Không tiêu chuẩn", "screen_technology": "IPS LCD, 120Hz", "rear_camera_features": "Tự động lấy nét, LED flash kép"}'::jsonb, '[{"code": "#f5f5f5", "name": "Trắng Bạc"}, {"code": "#1c1c1c", "name": "Đen Lurex"}, {"code": "#f5f5dc", "name": "Be Thanh Lịch"}]'::jsonb, '[{"name": "RAM 8GB - 128GB"}, {"name": "RAM 12GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('IT-P55P', 'itel-p55-plus', 'itel P55 Plus', 'smartphones', 'phone-flagship', 'itel', 2790000, 2590000, 300, 'https://placehold.co/600x600/183e38/ffffff?text=itel+P55+Plus+Xanh', '{"os": "Android 13, itel OS", "cpu": "8 lõi", "gps": "GPS", "gpu": "Mali-G57 MP1", "nfc": "Không", "ram": "8 GB (Hỗ trợ mở rộng thêm 8GB RAM ảo)", "sim": "2 Nano SIM", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa đơn, Giắc cắm tai nghe 3.5mm", "weight": "Khoảng 187 g", "battery": "5000 mAh", "network": "4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB (Hỗ trợ thẻ nhớ MicroSD)", "charging": "Sạc nhanh 45W", "infrared": "Không", "material": "Khung nhựa cứng cáp, Mặt lưng nhựa / Da sinh thái", "bluetooth": "Bluetooth 5.0", "processor": "Unisoc T606 (12 nm)", "brightness": "Tối đa 1200 nits", "dimensions": "Mỏng nhẹ", "rear_video": "1080p@30fps", "resolution": "720 x 1612 pixels (HD+)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "1080p@30fps", "rear_camera": "50MP chính + Ống kính phụ", "screen_size": "6.6 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.0, GPS", "display_type": "Màn hình đục lỗ (Punch-hole)", "front_camera": "8MP", "refresh_rate": "90Hz", "release_time": "02/2024", "back_material": "Nhựa Polycarbonate / Da nhân tạo cao cấp", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Nhựa chắc chắn", "video_recording": "Quay video 1080p@30fps", "display_features": "Tần số quét 90Hz, Tính năng thông báo Dynamic Bar", "special_features": "Tính năng hiển thị Dynamic Bar, Sạc nhanh 45W", "water_resistance": "Không", "screen_technology": "IPS LCD, 90Hz", "rear_camera_features": "Tự động lấy nét, LED flash"}'::jsonb, '[{"code": "#183e38", "name": "Xanh Hoàng Gia (Lưng da)"}, {"code": "#664263", "name": "Tím Thiên Thạch"}, {"code": "#1c1c1c", "name": "Đen Thiên Thạch"}]'::jsonb, '[{"name": "RAM 8GB - 128GB"}, {"name": "RAM 8GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('MZ-LK08', 'meizu-lucky-08', 'Meizu Lucky 08 5G', 'smartphones', 'phone-flagship', 'Meizu', 5990000, 5490000, 60, 'https://placehold.co/600x600/f5f5f5/333333?text=Meizu+Lucky+08+Trang', '{"os": "Android 14, Flyme AIOS", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Adreno 710", "nfc": "Có", "ram": "8 GB / 12 GB", "sim": "2 Nano SIM (Hỗ trợ 5G)", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép Stereo", "weight": "202 g", "battery": "6000 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay, gia tốc, con quay hồi chuyển, la bàn", "storage": "256 GB / 512 GB", "charging": "Sạc siêu nhanh 45W", "infrared": "Có", "material": "Khung hợp kim, Mặt lưng Kính/Nhựa", "bluetooth": "Bluetooth 5.1", "processor": "Qualcomm Snapdragon 7s Gen 2 (4nm)", "brightness": "Tối đa 5000 nits", "dimensions": "163 x 77.5 x 8.6 mm", "rear_video": "4K@30fps, 1080p@30/60fps", "resolution": "1264 × 2780 pixels", "fingerprint": "Quang học dưới màn hình", "front_video": "1080p@30fps", "rear_camera": "108MP chính + 2MP Macro", "screen_size": "6.78 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.1, NFC, GPS, Cổng hồng ngoại", "display_type": "Màn hình phẳng viền siêu mỏng", "front_camera": "8MP", "refresh_rate": "144Hz (LTPO)", "release_time": "09/2024", "back_material": "Kính cường lực nhám", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim cứng cáp", "video_recording": "Quay video 4K@30fps, 1080p@30/60fps", "display_features": "Độ sáng cực đại 5000 nits, Tần số quét tự động thích ứng", "special_features": "Màn hình 5000 nits, Hệ điều hành tích hợp AI thông minh", "water_resistance": "Kháng nước, kháng bụi nhẹ (Chưa công bố chuẩn IP)", "screen_technology": "LTPO AMOLED, 1.5K, 144Hz", "rear_camera_features": "Chụp siêu phân giải, AI Scene Detection"}'::jsonb, '[{"code": "#f5f5f5", "name": "Trắng"}, {"code": "#1c1c1c", "name": "Đen"}, {"code": "#00ffff", "name": "Xanh Cyan"}]'::jsonb, '[{"name": "RAM 8GB - 256GB"}, {"name": "RAM 12GB - 512GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('MZ-MB22', 'meizu-mblu-22-pro', 'Meizu Mblu 22 Pro NFC', 'smartphones', 'phone-flagship', 'Meizu', 3490000, 3190000, 400, 'https://placehold.co/600x600/1a1a1c/ffffff?text=Mblu+22+Pro+Den', '{"os": "Android 15, Flyme OS", "cpu": "8 lõi", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G52 MC2", "nfc": "Có (Tùy chọn NFC mở rộng)", "ram": "8 GB (Hỗ trợ RAM ảo)", "sim": "2 Nano SIM", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa đơn, Giắc cắm tai nghe 3.5mm", "weight": "Khoảng 198 g", "battery": "5000 mAh", "network": "4G LTE", "sensors": "Vân tay, gia tốc, la bàn, tiệm cận ảo", "storage": "128 GB / 256 GB (Hỗ trợ thẻ nhớ MicroSD)", "charging": "Sạc tiêu chuẩn 18W", "infrared": "Không", "material": "Khung nhựa, Mặt lưng nhựa vân nhám/bóng", "bluetooth": "Bluetooth 5.0", "processor": "MediaTek Helio G81", "brightness": "Tối đa 1200 nits", "dimensions": "Mỏng nhẹ (Đang cập nhật chi tiết)", "rear_video": "1080p@30fps", "resolution": "FHD+ (Tương đương 1080 x 2460 pixels)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "1080p@30fps", "rear_camera": "50MP chính + 2MP Macro", "screen_size": "6.79 inches", "connectivity": "Wi-Fi dual-band, Bluetooth 5.0, GPS", "display_type": "Màn hình giọt nước / đục lỗ", "front_camera": "8MP", "refresh_rate": "120Hz", "release_time": "03/2025", "back_material": "Nhựa Polycarbonate cấu trúc Titan Shield", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Nhựa chắc chắn chống sốc", "video_recording": "Quay video 1080p@30fps", "display_features": "Tần số quét 120Hz", "special_features": "Cấu trúc chống sốc Titan Shield siêu bền, Tích hợp NFC", "water_resistance": "Không tiêu chuẩn", "screen_technology": "IPS LCD, 120Hz", "rear_camera_features": "Tự động lấy nét, Chụp đêm"}'::jsonb, '[{"code": "#1a1a1c", "name": "Đen Titan"}, {"code": "#1c3d5a", "name": "Xanh Biển Sâu"}, {"code": "#f5f5f5", "name": "Trắng Tuyết"}]'::jsonb, '[{"name": "RAM 8GB - 128GB"}, {"name": "RAM 8GB - 256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('IPADA16', 'ipad-a16-wifi', 'iPad A16 Wifi', 'tablets', 'tablet-study', 'Apple', 9290000, 9290000, 200, '/images/products/ipad-a16-wifi/main.png', '{"os": "iPadOS", "cpu": "Hexa-core (2 lõi hiệu năng cao và 4 lõi tiết kiệm điện)", "gps": "iBeacon vi định vị", "gpu": "Apple GPU 5 lõi", "nfc": "Không", "ram": "6 GB", "wifi": "Wi‑Fi 6 (802.11ax)", "audio": "Loa stereo (kép)", "weight": "477 g", "battery": "28.6 Wh (Khoảng 7606 mAh)", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Con quay hồi chuyển, La bàn, Khí áp kế, Cảm biến ánh sáng", "storage": "64GB / 256GB", "charging": "Sạc nhanh 20W", "bluetooth": "Bluetooth 5.3", "processor": "Apple A16 Bionic", "dimensions": "248.6 x 179.5 x 7 mm", "rear_video": "Quay video 4K ở 24/25/30/60 fps, 1080p HD ở 25/30/60 fps", "resolution": "2360 x 1640 pixels", "fingerprint": "Touch ID tích hợp ở nút nguồn", "front_video": "Quay video 1080p HD ở 25/30/60 fps", "memory_card": "Không hỗ trợ", "rear_camera": "12MP ƒ/1.8", "screen_size": "10.9 inches", "front_camera": "12MP Ultra Wide ƒ/2.4, góc nhìn 122°", "release_time": "Năm 2026", "tablet_model": "iPad", "charging_port": "Type-C", "compatibility": "Apple Pencil (USB-C)", "headphone_jack": "Không", "other_utilities": "Micrô kép cho cuộc gọi, quay video và ghi âm", "display_features": "Độ sáng tối đa 500 nits, Công nghệ True Tone, Lớp phủ chống bám vân tay", "water_resistance": "Không", "screen_technology": "Liquid Retina IPS LCD", "utility_technology": "Mở khóa bằng vân tay Touch ID", "rear_camera_features": "Zoom kỹ thuật số lên đến 5x, Toàn cảnh (Panorama), Smart HDR 4"}'::jsonb, '[{"code": "#d1d5db", "name": "Bạc"}, {"code": "#f5e08c", "name": "Vàng"}, {"code": "#e57c91", "name": "Hồng"}, {"code": "#4b9cd3", "name": "Xanh"}]'::jsonb, '["A16 Wifi 128GB", "A16 Wifi 256GB", "A16 5G 128GB", "A16 5G 256GB", "A16 Wifi 512GB"]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('MATEPADSE', 'huawei-matepad-se', 'Huawei MatePad SE', 'tablets', 'tablet-study', 'Huawei', 4990000, 4490000, 100, '/images/products/huawei-matepad-se/main.png', '{"os": "HarmonyOS 3", "cpu": "Octa-core", "gps": "GPS, GLONASS, BDS, GALILEO", "gpu": "Adreno 610", "nfc": "Không", "ram": "4 GB", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép vòm Histen 8.0", "weight": "440 g", "battery": "5100 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Cảm biến ánh sáng", "storage": "64GB / 128GB", "charging": "Sạc 10W", "bluetooth": "Bluetooth 5.0", "processor": "Snapdragon 680", "dimensions": "246.9 x 156.7 x 7.85 mm", "rear_video": "Quay video 1080p ở 30 fps", "resolution": "2000 x 1200 pixels", "fingerprint": "Không", "front_video": "Quay video 720p ở 30 fps", "memory_card": "MicroSD, hỗ trợ tối đa 1TB", "rear_camera": "5MP", "screen_size": "10.4 inches", "front_camera": "2MP", "release_time": "Năm 2022", "tablet_model": "MatePad", "charging_port": "Type-C", "compatibility": "Không hỗ trợ bút stylus chuẩn", "headphone_jack": "3.5 mm", "other_utilities": "Kids Corner", "display_features": "Tần số quét 60Hz, Chứng nhận TÜV Rheinland bảo vệ mắt", "water_resistance": "Không", "screen_technology": "IPS LCD", "utility_technology": "Nhận diện khuôn mặt", "rear_camera_features": "Tự động lấy nét, Panorama"}'::jsonb, '[{"code": "#1a1c29", "name": "Đen Than"}, {"code": "#336699", "name": "Xanh Dương"}]'::jsonb, '[{"name": "64GB"}, {"name": "128GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('YOGATAB', 'lenovo-yoga-tab-wifi', 'Lenovo Yoga Tab 11 Wifi', 'tablets', 'tablet-study', 'Lenovo', 8990000, 7990000, 100, '/images/products/lenovo-yoga-tab/main.png', '{"os": "Android 11", "cpu": "Octa-core", "gps": "GPS, GLONASS", "gpu": "Mali-G76 MC4", "nfc": "Không", "ram": "4 GB / 8 GB", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "4 loa JBL, Dolby Atmos", "weight": "650 g", "battery": "7500 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Cảm biến ánh sáng, Con quay hồi chuyển", "storage": "128GB / 256GB", "charging": "Sạc nhanh 20W", "bluetooth": "Bluetooth 5.0", "processor": "MediaTek Helio G90T", "dimensions": "256.8 x 169.0 x 7.9-8.3 mm", "rear_video": "Quay video 1080p ở 30 fps", "resolution": "2000 x 1200 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps", "memory_card": "MicroSD, hỗ trợ tối đa 512GB", "rear_camera": "8MP", "screen_size": "11 inches", "front_camera": "8MP", "release_time": "Năm 2021", "tablet_model": "Yoga Tab", "charging_port": "Type-C", "compatibility": "Lenovo Precision Pen 2", "headphone_jack": "Không", "other_utilities": "Google Entertainment Space", "display_features": "Tần số quét 60Hz, Dolby Vision, độ sáng 400 nits, chống bám vân tay", "water_resistance": "Không", "screen_technology": "IPS LCD", "utility_technology": "Nhận diện khuôn mặt, Chân đế thép không gỉ đa năng", "rear_camera_features": "Tự động lấy nét"}'::jsonb, '[{"code": "#4A4D54", "name": "Xám Bão"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('POCOPADX1', 'xiaomi-poco-pad-x1', 'Xiaomi Poco Pad X1', 'tablets', 'tablet-study', 'Xiaomi', 7990000, 7490000, 100, '/images/products/xiaomi-poco-pad-x1/main.png', '{"os": "HyperOS (dựa trên Android 14)", "cpu": "Octa-core", "gps": "Không có (chỉ định vị qua Wi-Fi)", "gpu": "Adreno 710", "nfc": "Không", "ram": "8 GB", "wifi": "Wi-Fi 6 (802.11 a/b/g/n/ac/ax)", "audio": "4 loa stereo, Dolby Atmos, Hi-Res Audio", "weight": "571 g", "battery": "10000 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Con quay hồi chuyển, Cảm biến ánh sáng, La bàn", "storage": "128GB / 256GB", "charging": "Sạc nhanh 33W", "bluetooth": "Bluetooth 5.2", "processor": "Snapdragon 7s Gen 2", "dimensions": "280.0 x 181.85 x 7.52 mm", "rear_video": "Quay video 1080p ở 30 fps", "resolution": "2560 x 1600 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps", "memory_card": "MicroSD, hỗ trợ tối đa 1.5TB", "rear_camera": "8MP", "screen_size": "12.1 inches", "front_camera": "8MP", "release_time": "Năm 2024", "tablet_model": "Poco Pad", "charging_port": "Type-C", "compatibility": "Poco Smart Pen", "headphone_jack": "3.5 mm", "other_utilities": "Không có", "display_features": "Tần số quét 120Hz, Dolby Vision, độ sáng 600 nits, Gorilla Glass 3", "water_resistance": "Kháng bụi và nước nhẹ (IP52)", "screen_technology": "IPS LCD", "utility_technology": "Mở khóa khuôn mặt 2D", "rear_camera_features": "Tự động lấy nét, HDR"}'::jsonb, '[{"code": "#4B5364", "name": "Xám Đen"}, {"code": "#6699CC", "name": "Xanh Dương"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('MATEPAD12X', 'huawei-matepad-12-x', 'Huawei MatePad 12 X', 'tablets', 'tablet-pro', 'Huawei', 13990000, 12990000, 100, '/images/products/huawei-matepad-12-x/main.png', '{"os": "HarmonyOS 4.2", "cpu": "Octa-core", "gps": "Có (Tùy phiên bản mạng)", "gpu": "Maleoon 910", "nfc": "Không", "ram": "8 GB / 12 GB", "wifi": "Wi-Fi 6 (802.11 a/b/g/n/ac/ax) 2x2 MIMO", "audio": "6 loa vòm, công nghệ Huawei Histen", "weight": "555 g", "battery": "10100 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Con quay hồi chuyển, Cảm biến ánh sáng, Cảm biến từ trường", "storage": "256GB / 512GB", "charging": "Sạc siêu nhanh Huawei SuperCharge 66W", "bluetooth": "Bluetooth 5.2 (Hỗ trợ BLE, SBC, AAC, LDAC)", "processor": "Kirin 9000W (hoặc tương đương tùy thị trường)", "dimensions": "270.0 x 183.0 x 5.9 mm", "rear_video": "Quay video 4K ở 30 fps", "resolution": "2800 x 1840 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps", "memory_card": "Không hỗ trợ", "rear_camera": "13MP (chính) + 8MP (góc rộng)", "screen_size": "12.0 inches", "front_camera": "8MP", "release_time": "Năm 2024", "tablet_model": "MatePad", "charging_port": "Type-C", "compatibility": "Huawei M-Pencil (Thế hệ 3)", "headphone_jack": "Không (Dùng qua Type-C)", "other_utilities": "WPS Office cấp PC, Hỗ trợ ứng dụng vẽ GoPaint", "display_features": "Tần số quét 144Hz, Độ sáng tối đa 1000 nits, Chống lóa PaperMatte, Tỷ lệ 3:2", "water_resistance": "Không", "screen_technology": "IPS LCD (PaperMatte Edition)", "utility_technology": "Mở khóa khuôn mặt 2D", "rear_camera_features": "Tự động lấy nét, Đèn flash LED"}'::jsonb, '[{"code": "#D5DDE0", "name": "Trắng Ngọc Trai"}, {"code": "#CDE0CD", "name": "Xanh Lá Pastel"}]'::jsonb, '[{"name": "256GB"}, {"name": "512GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('MIPADMINI', 'xiaomi-pad-mini', 'Xiaomi Pad Mini', 'tablets', 'tablet-mini', 'Xiaomi', 4990000, 4590000, 100, '/images/products/xiaomi-pad-mini/main.png', '{"os": "HyperOS", "cpu": "Octa-core", "gps": "GPS, GLONASS, GALILEO, BDS", "gpu": "Mali-G57 MC2", "nfc": "Không", "ram": "4 GB / 6 GB", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "Loa kép stereo", "weight": "375 g", "battery": "6600 mAh", "network": "Hỗ trợ 4G (Tùy phiên bản)", "sensors": "Gia tốc kế, La bàn, Cảm biến ánh sáng", "storage": "128GB / 256GB", "charging": "Sạc nhanh 18W", "bluetooth": "Bluetooth 5.3", "processor": "MediaTek Helio G99", "dimensions": "211.5 x 125.4 x 8.8 mm", "rear_video": "Quay video 1080p ở 30 fps", "resolution": "1340 x 800 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps", "memory_card": "MicroSD, hỗ trợ tối đa 1TB", "rear_camera": "8MP", "screen_size": "8.7 inches", "front_camera": "5MP", "release_time": "Năm 2025", "tablet_model": "Pad Mini", "charging_port": "Type-C", "compatibility": "Không hỗ trợ bút thông minh", "headphone_jack": "3.5 mm", "other_utilities": "Dolby Atmos", "display_features": "Tần số quét 90Hz, Độ sáng 400 nits, Chế độ đọc sách bảo vệ mắt", "water_resistance": "Kháng bụi và nước nhẹ (IP53)", "screen_technology": "IPS LCD", "utility_technology": "Mở khóa khuôn mặt 2D", "rear_camera_features": "Tự động lấy nét"}'::jsonb, '[{"code": "#383E42", "name": "Xám Không Gian"}, {"code": "#E2E4E5", "name": "Bạc Ánh Trăng"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('POCOPADM1', 'xiaomi-poco-pad-m1', 'Xiaomi Poco Pad M1', 'tablets', 'tablet-study', 'Xiaomi', 4490000, 3990000, 100, '/images/products/xiaomi-poco-pad-m1/main.png', '{"os": "HyperOS", "cpu": "Octa-core", "gps": "Có hỗ trợ", "gpu": "Mali-G57 MC2", "nfc": "Không", "ram": "4 GB / 6 GB", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "4 loa stereo", "weight": "445 g", "battery": "8000 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Cảm biến ánh sáng", "storage": "64GB / 128GB", "charging": "Sạc nhanh 18W", "bluetooth": "Bluetooth 5.3", "processor": "MediaTek Helio G99", "dimensions": "250.3 x 157.9 x 7.05 mm", "rear_video": "Quay video 1080p ở 30 fps", "resolution": "2000 x 1200 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps, góc nhìn rộng", "memory_card": "MicroSD, hỗ trợ tối đa 1TB", "rear_camera": "8MP", "screen_size": "10.6 inches", "front_camera": "8MP", "release_time": "Năm 2025", "tablet_model": "Poco Pad", "charging_port": "Type-C", "compatibility": "Không hỗ trợ bút thông minh", "headphone_jack": "Không", "other_utilities": "Dolby Atmos", "display_features": "Tần số quét 90Hz, Độ sáng 400 nits, Bảo vệ mắt SGS", "water_resistance": "Không", "screen_technology": "IPS LCD", "utility_technology": "Mở khóa khuôn mặt 2D", "rear_camera_features": "Tự động lấy nét"}'::jsonb, '[{"code": "#1D1E20", "name": "Đen Bạc"}, {"code": "#A0B5AA", "name": "Xanh Bạc Hà"}]'::jsonb, '[{"name": "64GB"}, {"name": "128GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('HONORPAD10', 'honor-pad-10', 'HONOR Pad 10', 'tablets', 'tablet-study', 'HONOR', 6990000, 6490000, 100, '/images/products/honor-pad-10/main.png', '{"os": "MagicOS (dựa trên Android)", "cpu": "Octa-core", "gps": "Không có (chỉ định vị qua Wi-Fi)", "gpu": "Adreno 710", "nfc": "Không", "ram": "8 GB", "wifi": "Wi-Fi 802.11 a/b/g/n/ac", "audio": "8 loa âm thanh nổi, HONOR Histen", "weight": "555 g", "battery": "8300 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Cảm biến ánh sáng", "storage": "128GB / 256GB", "charging": "Sạc nhanh 35W", "bluetooth": "Bluetooth 5.1", "processor": "Snapdragon 6 Gen 1", "dimensions": "278.2 x 180.1 x 6.9 mm", "rear_video": "Quay video 4K ở 30 fps", "resolution": "2560 x 1600 pixels", "fingerprint": "Không", "front_video": "Quay video 1080p ở 30 fps", "memory_card": "Không hỗ trợ", "rear_camera": "13MP", "screen_size": "12.1 inches", "front_camera": "8MP", "release_time": "Năm 2025", "tablet_model": "Pad", "charging_port": "Type-C", "compatibility": "HONOR Magic-Pencil", "headphone_jack": "Không", "other_utilities": "Không gian đa cửa sổ (Multi-Window)", "display_features": "Tần số quét 120Hz, Độ sáng 500 nits, Bảo vệ mắt Eye Comfort", "water_resistance": "Không", "screen_technology": "TFT LCD (IPS)", "utility_technology": "Mở khóa khuôn mặt 2D", "rear_camera_features": "Tự động lấy nét, Nhận diện cảnh AI"}'::jsonb, '[{"code": "#383E42", "name": "Xám Không Gian"}, {"code": "#6A8C8E", "name": "Xanh Ngọc bích"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, FALSE, FALSE, 0.0, 0, NULL),
    ('TABS11', 'samsung-galaxy-tab-s11', 'Samsung Galaxy Tab S11', 'tablets', 'tablet-pro', 'Samsung', 19990000, 18990000, 100, '/images/products/samsung-galaxy-tab-s11/main.png', '{"os": "Android 15 (One UI 7.1.1)", "cpu": "Octa-core", "gps": "GPS, GLONASS, BDS, GALILEO", "gpu": "Adreno 750", "nfc": "Không", "ram": "8 GB / 12 GB", "wifi": "Wi-Fi 7 (802.11be)", "audio": "4 loa AKG, hỗ trợ Dolby Atmos", "weight": "498 g", "battery": "8400 mAh", "network": "Chỉ Wi-Fi", "sensors": "Gia tốc kế, Con quay hồi chuyển, Cảm biến ánh sáng, Cảm biến từ trường (La bàn)", "storage": "128GB / 256GB / 512GB", "charging": "Sạc siêu nhanh 45W", "bluetooth": "Bluetooth 5.3", "processor": "Snapdragon 8 Gen 3 for Galaxy", "dimensions": "254.3 x 165.8 x 5.9 mm", "rear_video": "Quay video 4K ở 30/60 fps", "resolution": "2560 x 1600 pixels", "fingerprint": "Vân tay dưới màn hình", "front_video": "Quay video 4K ở 30 fps", "memory_card": "MicroSD, hỗ trợ tối đa 1TB", "rear_camera": "13MP (chính) + 8MP (siêu rộng)", "screen_size": "11.0 inches", "front_camera": "12MP Ultra Wide", "release_time": "Năm 2025", "tablet_model": "Galaxy Tab S", "charging_port": "Type-C (USB 3.2 Gen 1)", "compatibility": "S Pen (Có sẵn trong hộp), Bàn phím Book Cover", "headphone_jack": "Không (Dùng qua cổng Type-C)", "other_utilities": "Vỏ nhôm Armor Aluminum siêu bền", "display_features": "Tần số quét 120Hz, HDR10+, Kính cường lực Corning Gorilla Glass", "water_resistance": "IP68 (Kháng bụi và nước)", "screen_technology": "Dynamic AMOLED 2X", "utility_technology": "Mở khóa bằng vân tay dưới màn hình, Samsung DeX", "rear_camera_features": "Tự động lấy nét, LED flash, HDR, Panorama"}'::jsonb, '[{"code": "#333333", "name": "Đen Graphite"}, {"code": "#E2E2E2", "name": "Bạc Titanium"}]'::jsonb, '[{"name": "128GB"}, {"name": "256GB"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('HPOBXF14', 'hp-omnibook-x-flip-14-fk0092au', 'Laptop HP Omnibook X Flip 14-FK0092AU BZ7P5PA', 'laptops', 'laptop-ultrabook', 'HP', 30790000, 28990000, 30, '/images/products/hp-omnibook-x-flip/main.png', '{"os": "Windows 11 Home + Office Home & Student 2024", "ram": "16GB LPDDR5x (onboard)", "audio": "Bang & Olufsen, 2 loa", "ports": "2x USB-C, 1x USB-A, 1x HDMI, 3.5mm jack", "webcam": "HP True Vision 720p HD", "weight": "1.39 kg", "battery": "3-cell, 59 Wh", "storage": "512GB PCIe Gen4 NVMe M.2 SSD", "graphics": "AMD Radeon 840M Graphics", "keyboard": "Bàn phím đèn nền, đi kèm bút cảm ứng", "material": "Hợp kim nhôm", "wireless": "Wi-Fi 6E, Bluetooth 5.3", "processor": "AMD Ryzen AI 5 340 (6 nhân, 12 luồng, lên đến 4.80 GHz)", "brightness": "400 nits, 62.5% sRGB", "dimensions": "31.36 x 22.24 x 1.65 cm", "resolution": "1920 x 1200 pixels", "screen_size": "14 inch", "refresh_rate": "60Hz", "screen_technology": "WUXGA IPS, cảm ứng, gập 360°"}'::jsonb, '[{"code": "#c0c0c0", "name": "Bạc (Meteor Silver)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('MSIP13AIU', 'msi-prestige-13-ai-ukiyoe-edition', 'Laptop MSI Prestige 13 AI+ Ukiyoe Edition A2VMG-075VN', 'laptops', 'laptop-ultrabook', 'MSI', 47990000, 44990000, 15, '/images/products/msi-prestige-13-ai-ukiyoe/main.png', '{"os": "Windows 11 Home", "ram": "32GB LPDDR5x-8533 (onboard)", "audio": "2 loa, Hi-Res Audio", "ports": "2x Thunderbolt 4, 1x USB 3.2 Gen1 Type-A, 1x HDMI 2.1, Micro SD, 3.5mm jack", "webcam": "IR Webcam FHD, Windows Hello", "weight": "0.99 kg", "battery": "4-cell, 75 Whr", "storage": "2TB NVMe PCIe Gen4 SSD", "graphics": "Intel Arc 140V", "keyboard": "Bàn phím đèn nền, vân tay tích hợp", "material": "Hợp kim Magie-Nhôm, phiên bản Ukiyo-e giới hạn", "wireless": "Wi-Fi 7 BE1750, Bluetooth 5.4", "processor": "Intel Core Ultra 9 288V (8 nhân, 8 luồng, lên đến 5.1 GHz)", "brightness": "500 nits HDR, 100% DCI-P3", "dimensions": "29.94 x 21.04 x 1.59 cm", "resolution": "2880 x 1800 pixels (2.8K)", "screen_size": "13.3 inch", "refresh_rate": "120Hz", "screen_technology": "OLED, VESA DisplayHDR 500"}'::jsonb, '[{"code": "#2c3e6b", "name": "Ukiyo-e Edition"}]'::jsonb, '[{"name": "2TB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, 'Limited'),
    ('HPOB5AI16', 'hp-omnibook-5-ai-16-af1048tu', 'Laptop HP Omnibook 5 AI 16-AF1048TU BZ7Q9PA', 'laptops', 'laptop-office', 'HP', 26190000, 24490000, 40, '/images/products/hp-omnibook-5-ai/main.png', '{"os": "Windows 11 Home + Office Home & Student 2024 (vĩnh viễn)", "ram": "16GB LPDDR5x-7467 (onboard)", "audio": "Bang & Olufsen, 2 loa", "ports": "2x USB-C (PD + DP 1.4a), 2x USB-A, HDMI 2.1, 3.5mm jack", "webcam": "HP True Vision 1080p FHD IR camera", "weight": "1.73 kg", "battery": "3-cell Li-ion polymer, 59 Wh, sạc nhanh 50% trong 30 phút", "storage": "512GB SSD PCIe Gen4 NVMe M.2", "graphics": "Intel Graphics (tích hợp)", "keyboard": "Bàn phím full-size đèn nền, phím Copilot", "material": "Hợp kim nhôm, Glacier Silver", "wireless": "Wi-Fi 6E, Bluetooth 5.3", "processor": "Intel Core Ultra 5 225U (12 nhân, 14 luồng, lên đến 4.8 GHz, Intel AI Boost)", "brightness": "300 nits, 95% DCI-P3", "dimensions": "35.77 x 25.48 x 1.79 cm", "resolution": "1920 x 1200 pixels (WUXGA)", "screen_size": "16 inch", "refresh_rate": "60Hz", "screen_technology": "IPS, anti-glare, tỷ lệ 16:10"}'::jsonb, '[{"code": "#e0e0e0", "name": "Bạc (Glacier Silver)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('MBNEOA18P', 'macbook-neo-13-a18-pro-2026', 'MacBook Neo 13 inch A18 Pro 2026', 'laptops', 'macbook', 'Apple', 15990000, 14990000, 60, '/images/products/macbook-neo-13/main.png', '{"os": "macOS (Tahoe)", "ram": "8GB bộ nhớ thống nhất (onboard)", "audio": "2 loa Dolby Atmos, 2 microphone", "ports": "2x USB-C, 3.5mm jack", "webcam": "Full HD Webcam", "weight": "1.23 kg", "battery": "Li-ion 36.5 Wh, lên đến 16 giờ sử dụng", "storage": "256GB / 512GB SSD", "graphics": "Apple A18 Pro GPU 5 lõi", "keyboard": "Magic Keyboard với Touch ID", "material": "Nhôm tái chế nguyên khối", "wireless": "Wi-Fi 6E, Bluetooth 6.0", "processor": "Apple A18 Pro (3nm gen2, CPU 6 lõi: 2 hiệu năng + 4 tiết kiệm điện)", "brightness": "500 nits", "dimensions": "30.41 x 21.24 x 1.27 cm", "resolution": "2408 x 1506 pixels", "screen_size": "13 inch", "refresh_rate": "60Hz", "screen_technology": "Liquid Retina, 1 tỷ màu"}'::jsonb, '[{"code": "#f5c6c6", "name": "Hồng phớt (Blush)"}, {"code": "#3f5277", "name": "Xanh Indigo"}, {"code": "#c0c0c0", "name": "Bạc (Silver)"}, {"code": "#e8c547", "name": "Vàng Citrus"}]'::jsonb, '[{"name": "256GB SSD"}, {"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('ACGA7', 'acer-gaming-aspire-7-a715-59g-57tu', 'Laptop Acer Gaming Aspire 7 A715-59G-57TU', 'laptops', 'laptop-gaming', 'Acer', 19990000, 17990000, 35, '/images/products/acer-aspire-7-gaming/main.png', '{"os": "Windows 11 Home", "ram": "16GB DDR4 3200MHz (2 khe cắm, hỗ trợ nâng cấp)", "audio": "2 loa stereo, DTS:X Ultra", "ports": "1x USB-C, 2x USB-A 3.2, 1x HDMI 2.0, RJ-45 LAN, 3.5mm jack", "webcam": "HD Webcam 720p", "weight": "2.1 kg", "battery": "3-cell, 54.8 Wh", "storage": "512GB PCIe NVMe SSD", "graphics": "NVIDIA GeForce RTX 3050 6GB GDDR6", "keyboard": "Bàn phím đèn nền 15 màu (One Zone), phím Copilot", "material": "Nhựa composite, Titanium Black", "wireless": "Wi-Fi 6E, Bluetooth 5.2", "processor": "Intel Core i5-12450H (8 nhân, 12 luồng, lên đến 4.40 GHz)", "brightness": "250 nits", "dimensions": "36.24 x 23.6 x 2.29 cm", "resolution": "1920 x 1080 pixels", "screen_size": "15.6 inch", "refresh_rate": "144Hz", "screen_technology": "IPS, Full HD"}'::jsonb, '[{"code": "#333333", "name": "Đen (Titanium Black)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('ACAL15', 'acer-aspire-lite-15-al15-42p-r8e6', 'Laptop Acer Aspire Lite 15 AL15-42P-R8E6', 'laptops', 'laptop-office', 'Acer', 15990000, 14490000, 45, '/images/products/acer-aspire-lite-15/main.png', '{"os": "Windows 11 Home + Office Home & Student 2024 (vĩnh viễn)", "ram": "16GB DDR4 (nâng cấp tối đa 32GB)", "audio": "2 loa stereo", "ports": "1x USB-C, 2x USB-A 3.2, 1x HDMI 2.1, 3.5mm jack", "webcam": "FHD Webcam 1080p", "weight": "1.7 kg", "battery": "3-cell Li-ion, 58 Wh", "storage": "512GB SSD NVMe PCIe", "graphics": "AMD Radeon Graphics (tích hợp)", "keyboard": "Bàn phím full-size, phím Copilot", "material": "Nhựa composite, Light Silver", "wireless": "Wi-Fi 6, Bluetooth 5.1", "processor": "AMD Ryzen 5 7430U (6 nhân, 12 luồng, lên đến 4.3 GHz)", "brightness": "250 nits", "dimensions": "36.0 x 23.7 x 1.79 cm", "resolution": "1920 x 1080 pixels (Full HD)", "screen_size": "15.6 inch", "refresh_rate": "60Hz", "screen_technology": "IPS, Acer ComfyView anti-glare"}'::jsonb, '[{"code": "#d0d0d0", "name": "Bạc (Light Silver)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('ACNPP15', 'acer-gaming-nitro-propanel-anv15-41-r7cr', 'Laptop Acer Gaming Nitro ProPanel ANV15-41-R7CR', 'laptops', 'laptop-gaming', 'Acer', 28990000, 26990000, 25, '/images/products/acer-nitro-propanel/main.png', '{"os": "Windows 11 Home SL", "ram": "16GB DDR5 4800MHz (1x16GB, 2 khe, nâng cấp tối đa 96GB)", "audio": "2 loa stereo, DTS:X Ultra", "ports": "1x USB-C, 3x USB-A 3.2, 1x HDMI 2.1, RJ-45 LAN, 3.5mm jack", "webcam": "HD Webcam 720p", "weight": "2.1 kg", "battery": "4-cell Li-ion, 57 Wh", "storage": "512GB SSD M.2 NVMe PCIe", "graphics": "NVIDIA GeForce RTX 4050 6GB GDDR6", "keyboard": "Bàn phím Chiclet đèn nền, phím Copilot", "material": "Nhựa composite, tản nhiệt Dual-fan", "wireless": "Wi-Fi 6E, Bluetooth 5.2", "processor": "AMD Ryzen 5 7535HS (6 nhân, 12 luồng, lên đến 4.55 GHz)", "brightness": "300 nits", "dimensions": "36.25 x 25.43 x 2.64 cm", "resolution": "1920 x 1080 pixels", "screen_size": "15.6 inch", "refresh_rate": "180Hz", "screen_technology": "IPS, Full HD, 100% sRGB"}'::jsonb, '[{"code": "#1a1a1a", "name": "Đen (Black)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, 'Hot'),
    ('LNLOQ15', 'lenovo-loq-15arp10e-83s0007avn', 'Laptop Lenovo LOQ 15ARP10E 83S0007AVN', 'laptops', 'laptop-gaming', 'Lenovo', 25990000, 23990000, 30, '/images/products/lenovo-loq-15/main.png', '{"os": "Windows 11 Home", "ram": "16GB DDR5-4800MHz (2 khe SO-DIMM, hỗ trợ nâng cấp)", "audio": "2 loa Nahimic, 2W", "ports": "1x USB-C (PD 3.0), 2x USB-A 3.2, 1x HDMI 2.1, RJ-45 LAN, 3.5mm jack", "webcam": "HD Webcam 720p, màn trập bảo mật", "weight": "1.8 kg", "battery": "57.5 Wh, Rapid Charge Pro (50% trong 30 phút), sạc 135W Slim Tip", "storage": "512GB SSD PCIe Gen4 M.2 2242 NVMe (hỗ trợ 2 ổ M.2)", "graphics": "NVIDIA GeForce RTX 3050 6GB GDDR6", "keyboard": "Bàn phím full-size đèn nền trắng", "material": "PC-ABS, bề mặt IMR, Luna Grey", "wireless": "Wi-Fi 6, Bluetooth 5.1", "processor": "AMD Ryzen 7 7735HS (8 nhân, 16 luồng, lên đến 4.75 GHz)", "brightness": "300 nits", "dimensions": "35.92 x 23.6 x 1.99 cm", "resolution": "1920 x 1080 pixels", "screen_size": "15.6 inch", "refresh_rate": "144Hz", "screen_technology": "IPS, Full HD, 100% sRGB"}'::jsonb, '[{"code": "#6b6b7b", "name": "Luna Grey"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('ASGV16', 'asus-gaming-v16-v3607vu-rp343w', 'Laptop ASUS Gaming V16 V3607VU-RP343W', 'laptops', 'laptop-gaming', 'ASUS', 24990000, 22990000, 25, '/images/products/asus-gaming-v16/main.png', '{"os": "Windows 11 Home", "ram": "16GB DDR5 (có khả năng nâng cấp)", "audio": "2 loa stereo, Dolby Atmos", "ports": "1x USB-C (display/PD), 2x USB-A, 1x HDMI 2.1, RJ-45 LAN, 3.5mm jack", "webcam": "Webcam 1080p FHD, nắp che bảo mật", "weight": "1.95 kg", "battery": "3-cell Li-ion, 63 WHrs", "storage": "512GB M.2 NVMe PCIe 4.0 SSD", "graphics": "NVIDIA GeForce RTX 4050 6GB GDDR6 (194 AI TOPS)", "keyboard": "Bàn phím full-size đèn nền, NumberPad", "material": "Nhựa composite, Matte Black", "wireless": "Wi-Fi 6E, Bluetooth 5.3", "processor": "Intel Core 5-210H (8 nhân, 12 luồng, 2.2 GHz lên đến 4.8 GHz, 12MB Cache)", "brightness": "300 nits", "dimensions": "35.91 x 24.91 x 2.31 cm", "resolution": "1920 x 1200 pixels", "screen_size": "16 inch", "refresh_rate": "144Hz", "_variantSpecKeys": ["ram", "storage"], "screen_technology": "WUXGA IPS, anti-glare, tỷ lệ 16:10"}'::jsonb, '[{"code": "#222222", "name": "Đen (Matte Black)"}]'::jsonb, '[{"name": "512GB SSD"}]'::jsonb, TRUE, FALSE, 0.0, 0, NULL),
    ('None', 'test-phone-c5e6', 'Test Phone 54c5', '', '', '', 1000, NULL, 0, '', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, FALSE, FALSE, NULL, 0, NULL),
    ('IP17-BK-256GB', 'iphone-17-revision-ddda92', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "_warrantyPolicy": {"hasWarranty": false, "oneForOneDays": 0, "allowOneForOne": false, "warrantyMonths": 0, "inheritWarrantyPolicy": true}, "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_accessoryOffers": [], "_variantSpecKeys": ["ram", "storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "_attachedServices": [], "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-E46E7072F9', 'iphone-17-revision-e46e70', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "_warrantyPolicy": {"hasWarranty": false, "oneForOneDays": 0, "allowOneForOne": false, "warrantyMonths": 0, "inheritWarrantyPolicy": true}, "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_accessoryOffers": [], "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "_attachedServices": [], "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-4375418818', 'iphone-17-revision-437541', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "_warrantyPolicy": {"hasWarranty": false, "oneForOneDays": 0, "allowOneForOne": false, "warrantyMonths": 0, "inheritWarrantyPolicy": true}, "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_accessoryOffers": [], "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "_attachedServices": [], "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-CDDA941186', 'iphone-17-revision-cdda94', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "_warrantyPolicy": {"hasWarranty": false, "oneForOneDays": 0, "allowOneForOne": false, "warrantyMonths": 0, "inheritWarrantyPolicy": true}, "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_accessoryOffers": [], "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "_attachedServices": [], "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-9C9E361303', 'iphone-17-revision-9c9e36', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "_warrantyPolicy": {"hasWarranty": false, "oneForOneDays": 0, "allowOneForOne": false, "warrantyMonths": 0, "inheritWarrantyPolicy": true}, "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_accessoryOffers": [], "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "_attachedServices": [], "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-94E7D85E41', 'iphone-17-revision-94e7d8', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-33E1E3B529', 'iphone-17-revision-33e1e3', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 0, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('TEST-1780565512-BK-128', 'ki-m-th-qu-n-l-s-n-ph-m-1780565512-f96bd5', 'Ki?m th? qu?n l? s?n ph?m 1780565512', 'cameras', '', '70mai', 1234000, 1234000, 2, '/images/products/placeholder.svg', '{"ram": "8GB", "storage": "128GB"}'::jsonb, '[]'::jsonb, '[]'::jsonb, FALSE, FALSE, NULL, 0, NULL),
    ('REV-3B9B7C933A', 'iphone-17-revision-3b9b7c', 'iPhone 17', 'smartphones', 'phone-flagship', 'Apple', 24990000, 24990000, 60, '/images/products/iphone-17/black/cover.webp', '{"os": "iOS 26", "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện", "gps": "GPS, GLONASS, Galileo, QZSS", "gpu": "GPU 5 lõi", "nfc": "Có", "ram": "8 GB LPDDR5", "sim": "SIM kép (eSIM)", "wifi": "Wi-Fi 7", "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos", "weight": "190 g", "battery": "Khoảng 3300 mAh", "network": "5G", "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế", "storage": "256GB / 512GB", "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W", "infrared": "Không", "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2", "bluetooth": "Bluetooth 5.3", "processor": "Apple A19 (Tiến trình 3nm+)", "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)", "dimensions": "150.0 x 71.9 x 8.75 mm", "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps", "resolution": "2622 x 1206 pixels", "fingerprint": "Không (Sử dụng Face ID)", "front_video": "4K Dolby Vision 24/25/30/60 fps", "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2", "screen_size": "6.3 inches", "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC", "display_type": "Dynamic Island", "front_camera": "18MP Center Stage khẩu độ ƒ/1.9", "refresh_rate": "120Hz (ProMotion)", "release_time": "09/2025", "back_material": "Kính pha màu", "charging_port": "USB Type-C (USB 2)", "compatibility": "iOS, Apple Watch, AirPods", "frame_material": "Nhôm chuẩn hàng không vũ trụ", "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR", "_variantSpecKeys": ["storage"], "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1", "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)", "water_resistance": "IP68 (sâu 6 mét trong 30 phút)", "screen_technology": "Super Retina XDR OLED", "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-4C5D370010', 'oppo-find-n3-revision-4c5d37', 'OPPO Find N3', 'smartphones', 'phone-foldable', 'OPPO', 39990000, 34990000, 6, '/images/products/oppo-find-n3/black/cover.webp', '{"os": "Android 13, ColorOS 14", "cpu": "8 nhân", "gps": "GPS, GLONASS, GALILEO, BDS, QZSS", "gpu": "Adreno 740", "nfc": "Có", "ram": "16GB", "sim": "2 Nano SIM", "wifi": "Wi-Fi 7 (802.11be)", "audio": "Hệ thống 3 loa Stereo, Dolby Atmos", "weight": "239 g", "battery": "4805 mAh", "network": "5G, 4G LTE", "sensors": "Vân tay cạnh bên, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, quang phổ màu", "storage": "512GB", "charging": "Sạc siêu nhanh SUPERVOOC 67W", "infrared": "Không", "material": "Khung hợp kim nhôm bọc carbon, Mặt lưng kính hoặc Da sợi", "bluetooth": "Bluetooth 5.3", "processor": "Snapdragon 8 Gen 2", "brightness": "Tối đa 2800 nits", "dimensions": "153.4 x 143.1 x 5.8 mm (mở), 153.4 x 73.3 x 11.7 mm (gập)", "rear_video": "4K@30/60fps, 1080p@30/60/240fps, gyro-EIS, HDR10+", "resolution": "2440 x 2268 pixels (Màn hình chính)", "fingerprint": "Cảm biến vân tay cạnh bên", "front_video": "4K@30fps, 1080p@30fps", "rear_camera": "Chính 48 MP & Phụ 64 MP, 48 MP", "screen_size": "Chính 7.82 inches, Phụ 6.31 inches", "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS", "display_type": "Màn hình gập (Foldable)", "front_camera": "20 MP (Trong) & 32 MP (Ngoài)", "refresh_rate": "120Hz", "release_time": "10/2023", "back_material": "Da sinh thái / Kính cường lực", "charging_port": "USB Type-C", "compatibility": "Android", "frame_material": "Hợp kim nhôm", "video_recording": "4K@30/60fps, 1080p@30/60/240fps", "_variantSpecKeys": ["ram", "Màu sắc", "storage"], "display_features": "Dolby Vision, 1 tỷ màu, Kính siêu mỏng UTG", "special_features": "Đa nhiệm thông minh Canvas, Bản lề Flexion Hinge siêu phẳng", "water_resistance": "IPX4 (Kháng nước bắn nhẹ)", "screen_technology": "LTPO3 OLED", "rear_camera_features": "Camera Hasselblad, OIS, Zoom quang 3x, Cảm biến chồng Sony LYT-T808"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-54F35277EF', 'laptop-asus-gaming-v16-v3607vu-rp343w-revision-54f352', 'Laptop ASUS Gaming V16 V3607VU-RP343W', 'laptops', 'laptop-gaming', 'ASUS', 24990000, 22990000, 25, '/images/products/asus-gaming-v16/main.png', '{"os": "Windows 11 Home", "ram": "16GB DDR5 (có khả năng nâng cấp)", "audio": "2 loa stereo, Dolby Atmos", "ports": "1x USB-C (display/PD), 2x USB-A, 1x HDMI 2.1, RJ-45 LAN, 3.5mm jack", "webcam": "Webcam 1080p FHD, nắp che bảo mật", "weight": "1.95 kg", "battery": "3-cell Li-ion, 63 WHrs", "storage": "512GB M.2 NVMe PCIe 4.0 SSD", "graphics": "NVIDIA GeForce RTX 4050 6GB GDDR6 (194 AI TOPS)", "keyboard": "Bàn phím full-size đèn nền, NumberPad", "material": "Nhựa composite, Matte Black", "wireless": "Wi-Fi 6E, Bluetooth 5.3", "processor": "Intel Core 5-210H (8 nhân, 12 luồng, 2.2 GHz lên đến 4.8 GHz, 12MB Cache)", "brightness": "300 nits", "dimensions": "35.91 x 24.91 x 2.31 cm", "resolution": "1920 x 1200 pixels", "screen_size": "16 inch", "refresh_rate": "144Hz", "_variantSpecKeys": ["ram", "storage"], "screen_technology": "WUXGA IPS, anti-glare, tỷ lệ 16:10"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL),
    ('REV-7124BABDED', 'laptop-asus-gaming-v16-v3607vu-rp343w-revision-7124ba', 'Laptop ASUS Gaming V16 V3607VU-RP343W', 'laptops', 'laptop-gaming', 'ASUS', 24990000, 22990000, 25, '/images/products/asus-gaming-v16/main.png', '{"os": "Windows 11 Home", "ram": "16GB DDR5 (có khả năng nâng cấp)", "audio": "2 loa stereo, Dolby Atmos", "ports": "1x USB-C (display/PD), 2x USB-A, 1x HDMI 2.1, RJ-45 LAN, 3.5mm jack", "webcam": "Webcam 1080p FHD, nắp che bảo mật", "weight": "1.95 kg", "battery": "3-cell Li-ion, 63 WHrs", "storage": "512GB M.2 NVMe PCIe 4.0 SSD", "graphics": "NVIDIA GeForce RTX 4050 6GB GDDR6 (194 AI TOPS)", "keyboard": "Bàn phím full-size đèn nền, NumberPad", "material": "Nhựa composite, Matte Black", "wireless": "Wi-Fi 6E, Bluetooth 5.3", "processor": "Intel Core 5-210H (8 nhân, 12 luồng, 2.2 GHz lên đến 4.8 GHz, 12MB Cache)", "brightness": "300 nits", "dimensions": "35.91 x 24.91 x 2.31 cm", "resolution": "1920 x 1200 pixels", "screen_size": "16 inch", "refresh_rate": "144Hz", "_variantSpecKeys": ["ram", "storage"], "screen_technology": "WUXGA IPS, anti-glare, tỷ lệ 16:10"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, NULL, 0, NULL)
)
INSERT INTO products (
    sku, slug, name, category, brand, category_id, subcategory_id, brand_id,
    price, sale_price, stock_quantity, image_url, specifications, colors, capacities,
    is_featured, is_flash_sale, rating, review_count, badge, status
)
SELECT
    product_seed.sku,
    product_seed.slug,
    product_seed.name,
    upper(product_seed.category_code),
    product_seed.brand_name,
    category.id,
    subcategory.id,
    brand.id,
    product_seed.price,
    product_seed.sale_price,
    product_seed.stock_quantity,
    product_seed.image_url,
    product_seed.specifications,
    product_seed.colors,
    product_seed.capacities,
    product_seed.is_featured,
    product_seed.is_flash_sale,
    product_seed.rating,
    product_seed.review_count,
    product_seed.badge,
    'ACTIVE'
FROM product_seed
JOIN categories category ON category.code = product_seed.category_code
JOIN categories subcategory ON subcategory.code = product_seed.subcategory_code
JOIN brands brand ON brand.name = product_seed.brand_name
ON CONFLICT (sku) DO UPDATE SET
    slug = EXCLUDED.slug,
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    brand = EXCLUDED.brand,
    category_id = EXCLUDED.category_id,
    subcategory_id = EXCLUDED.subcategory_id,
    brand_id = EXCLUDED.brand_id,
    price = EXCLUDED.price,
    sale_price = EXCLUDED.sale_price,
    stock_quantity = EXCLUDED.stock_quantity,
    image_url = EXCLUDED.image_url,
    specifications = EXCLUDED.specifications,
    colors = EXCLUDED.colors,
    capacities = EXCLUDED.capacities,
    is_featured = EXCLUDED.is_featured,
    is_flash_sale = EXCLUDED.is_flash_sale,
    rating = EXCLUDED.rating,
    review_count = EXCLUDED.review_count,
    badge = EXCLUDED.badge,
    status = 'ACTIVE',
    updated_at = NOW();

-- PRODUCT VARIANTS SEED WITH
WITH variant_seed(product_sku, sku, color_name, color_code, storage, ram, configuration, price, sale_price, stock_quantity) AS (
    VALUES
    ('AWU2', 'AWU2-49-BLACK-ALPINEL', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Alpine Size L', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-ALPINES', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Alpine Size S', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-TRAILSM', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Trail Size S/M', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-CAOSU', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Cao Su', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-TRAILML', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Trail Size M/L', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-TITANM', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Titan Size M', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-TITANS', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Titan Size S', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-TITANL', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Titan Size L', 16990000, NULL, 10),
    ('AWU2', 'AWU2-49-BLACK-ALPINEM', 'Titan Đen', '#2a2b2d', NULL, NULL, '49mm Dây Alpine Size M', 16990000, NULL, 10),
    ('A17-5G', 'A17-5G-BK-128GB', 'Đen', '#1a1a1a', '128GB', '6GB', '128GB', 5490000, 4990000, 30),
    ('A17-5G', 'A17-5G-BK-256GB', 'Đen', '#1a1a1a', '256GB', '8GB', '256GB', 6490000, 5990000, 30),
    ('A17-5G', 'A17-5G-BL-128GB', 'Xanh Lam', '#8a9eb3', '128GB', '6GB', '128GB', 5490000, 4990000, 30),
    ('A17-5G', 'A17-5G-BL-256GB', 'Xanh Lam', '#8a9eb3', '256GB', '8GB', '256GB', 6490000, 5990000, 30),
    ('A17-5G', 'A17-5G-GR-128GB', 'Xám', '#808080', '128GB', '6GB', '128GB', 5490000, 4990000, 30),
    ('A17-5G', 'A17-5G-GR-256GB', 'Xám', '#808080', '256GB', '8GB', '256GB', 6490000, 5990000, 30),
    ('A57-5G', 'A57-5G-GR-128GB', 'Xám', '#888888', '128GB', '8GB', '128GB', 9990000, 9490000, 25),
    ('A57-5G', 'A57-5G-GR-256GB', 'Xám', '#888888', '256GB', '12GB', '256GB', 10990000, 10490000, 25),
    ('A57-5G', 'A57-5G-LL-128GB', 'Tím Lilac', '#d4b8e2', '128GB', '8GB', '128GB', 9990000, 9490000, 25),
    ('A57-5G', 'A57-5G-LL-256GB', 'Tím Lilac', '#d4b8e2', '256GB', '12GB', '256GB', 10990000, 10490000, 25),
    ('A57-5G', 'A57-5G-NV-128GB', 'Xanh Navy', '#1c2b42', '128GB', '8GB', '128GB', 9990000, 9490000, 25),
    ('A57-5G', 'A57-5G-NV-256GB', 'Xanh Navy', '#1c2b42', '256GB', '12GB', '256GB', 10990000, 10490000, 25),
    ('ACAL15', 'ACAL15-SL-512GBSSD', 'Bạc (Light Silver)', '#d0d0d0', '512GB SSD', '16GB', '512GB SSD', 15990000, 14490000, 45),
    ('ACGA7', 'ACGA7-BK-512GBSSD', 'Đen (Titanium Black)', '#333333', '512GB SSD', '16GB', '512GB SSD', 19990000, 17990000, 35),
    ('ACNPP15', 'ACNPP15-BK-512GBSSD', 'Đen (Black)', '#1a1a1a', '512GB SSD', '16GB', '512GB SSD', 28990000, 26990000, 25),
    ('ASGV16', 'ASGV16-BK-512GBSSD', 'Đen (Matte Black)', '#CCCCCC', '512GB SSD', '16GB', '512GB SSD', 24990000, 22990000, 25),
    ('HN-400', 'HN-400-GD-256GB', 'Vàng Sa Mạc', '#e5d3b3', '256GB', '8GB', '256GB', 11990000, 10990000, 10),
    ('HN-400', 'HN-400-GD-512GB', 'Vàng Sa Mạc', '#e5d3b3', '512GB', '12GB', '512GB', 13490000, 12490000, 10),
    ('HN-400P', 'HN-400P-BK-256GB', 'Đen Bóng Đêm', '#1a1a1c', '256GB', '12GB', '256GB', 16990000, 15990000, 15),
    ('HN-400P', 'HN-400P-BK-512GB', 'Đen Bóng Đêm', '#1a1a1c', '512GB', '12GB', '512GB', 18990000, 17990000, 15),
    ('HN-400P', 'HN-400P-BL-256GB', 'Xanh Thủy Triều', '#334c6e', '256GB', '12GB', '256GB', 16990000, 15990000, 15),
    ('HN-400P', 'HN-400P-BL-512GB', 'Xanh Thủy Triều', '#334c6e', '512GB', '12GB', '512GB', 18990000, 17990000, 15),
    ('HN-400P', 'HN-400P-GR-256GB', 'Xám Mặt Trăng', '#6e727b', '256GB', '12GB', '256GB', 16990000, 15990000, 15),
    ('HN-400P', 'HN-400P-GR-512GB', 'Xám Mặt Trăng', '#6e727b', '512GB', '12GB', '512GB', 18990000, 17990000, 15),
    ('HN-MGV5', 'HN-MGV5-GD-1TB', 'Vàng Bình Minh', '#e6c280', '1TB', '16GB', '1TB', 45990000, 44900000, 10),
    ('HN-MGV5', 'HN-MGV5-GD-512GB', 'Vàng Bình Minh', '#e6c280', '512GB', '16GB', '512GB', 41990000, 40990000, 10),
    ('HN-MGV5', 'HN-MGV5-WH-1TB', 'Trắng Ngà', '#f5f5dc', '1TB', '16GB', '1TB', 45990000, 44900000, 10),
    ('HN-MGV5', 'HN-MGV5-WH-512GB', 'Trắng Ngà', '#f5f5dc', '512GB', '16GB', '512GB', 41990000, 40990000, 10),
    ('HN-X9D', 'HN-X9D-BK-256GB', 'Đen Bóng Đêm', '#1a1a1c', '256GB', '8GB', '256GB', 7990000, 7490000, 15),
    ('HN-X9D', 'HN-X9D-BK-512GB', 'Đen Bóng Đêm', '#1a1a1c', '512GB', '12GB', '512GB', 8990000, 8490000, 15),
    ('HN-X9D', 'HN-X9D-GD-256GB', 'Vàng Bình Minh', '#d4af37', '256GB', '8GB', '256GB', 7990000, 7490000, 15),
    ('HN-X9D', 'HN-X9D-GD-512GB', 'Vàng Bình Minh', '#d4af37', '512GB', '12GB', '512GB', 8990000, 8490000, 15),
    ('HONORPAD10', 'HONORPAD10-BL-128GB', 'Xanh Ngọc bích', '#6A8C8E', '128GB', '8GB', '128GB', 6990000, 6490000, 10),
    ('HONORPAD10', 'HONORPAD10-BL-256GB', 'Xanh Ngọc bích', '#6A8C8E', '256GB', '8GB', '256GB', 7990000, 7490000, 10),
    ('HONORPAD10', 'HONORPAD10-GY-128GB', 'Xám Không Gian', '#383E42', '128GB', '8GB', '128GB', 6990000, 6490000, 10),
    ('HONORPAD10', 'HONORPAD10-GY-256GB', 'Xám Không Gian', '#383E42', '256GB', '8GB', '256GB', 7990000, 7490000, 10),
    ('HPOB5AI16', 'HPOB5AI16-SL-512GBSSD', 'Bạc (Glacier Silver)', '#e0e0e0', '512GB SSD', '16GB', '512GB SSD', 26190000, 24490000, 10),
    ('HPOBXF14', 'HPOBXF14-SL-512GBSSD', 'Bạc (Meteor Silver)', '#c0c0c0', '512GB SSD', '16GB', '512GB SSD', 30790000, 28990000, 30),
    ('IP16PM', 'IP16PM-256-DT', 'Titan Sa mạc', '#CCCCCC', '256GB', '8GB', NULL, 33990000, 33990000, 12),
    ('IP16PM', 'IP16PM-512-BT', 'Titan đen', '#CCCCCC', '512GB', '8GB', NULL, 38990000, 38990000, 7),
    ('IP17', 'IP17-BK-256GB', 'Đen', '#000000', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('IP17', 'IP17-BK-512GB', 'Đen', '#000000', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('IP17', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('IP17', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('IP17', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('IP17', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('IP17-BK-256GB', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('IP17-BK-256GB', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('IP17-BK-256GB', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('IP17-BK-256GB', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('IP17-BK-256GB', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('IP17-BK-256GB', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('IP17P', 'IP17P-CO-1TB', 'Cam Vũ Trụ', '#f26b2f', '1TB', '12GB', '1TB', 41990000, 40990000, 10),
    ('IP17P', 'IP17P-CO-256GB', 'Cam Vũ Trụ', '#f26b2f', '256GB', '12GB', '256GB', 29990000, 28990000, 10),
    ('IP17P', 'IP17P-CO-512GB', 'Cam Vũ Trụ', '#f26b2f', '512GB', '12GB', '512GB', 34990000, 33990000, 10),
    ('IP17P', 'IP17P-DB-1TB', 'Xanh Sâu', '#24364b', '1TB', '12GB', '1TB', 41990000, 40990000, 10),
    ('IP17P', 'IP17P-DB-256GB', 'Xanh Sâu', '#24364b', '256GB', '12GB', '256GB', 29990000, 28990000, 10),
    ('IP17P', 'IP17P-DB-512GB', 'Xanh Sâu', '#24364b', '512GB', '12GB', '512GB', 34990000, 33990000, 10),
    ('IP17P', 'IP17P-SV-1TB', 'Bạc', '#d9d9d4', '1TB', '12GB', '1TB', 41990000, 40990000, 10),
    ('IP17P', 'IP17P-SV-256GB', 'Bạc', '#d9d9d4', '256GB', '12GB', '256GB', 29990000, 28990000, 10),
    ('IP17P', 'IP17P-SV-512GB', 'Bạc', '#d9d9d4', '512GB', '12GB', '512GB', 34990000, 33990000, 10),
    ('IP17PM', 'IP17PM-1TB', 'Cam Vũ Trụ', NULL, '1TB', '12GB', '1TB', 49990000, NULL, 10),
    ('IP17PM', 'IP17PM-256', 'Cam Vũ Trụ', NULL, '256GB', '12GB', '256GB', 37990000, NULL, 10),
    ('IP17PM', 'IP17PM-2TB', 'Cam Vũ Trụ', NULL, '2TB', '12GB', '2TB', 55990000, NULL, 10),
    ('IP17PM', 'IP17PM-512', 'Cam Vũ Trụ', NULL, '512GB', '12GB', '512GB', 43990000, NULL, 10),
    ('IP17PM', 'IP17PM-CO-1TB', 'Cam Vũ Trụ', '#f26b2f', '1TB', '12GB', '1TB', 46990000, 42990000, 10),
    ('IP17PM', 'IP17PM-CO-256', 'Cam Vũ Trụ', '#f26b2f', '256GB', '12GB', '256GB', 34990000, 30990000, 10),
    ('IP17PM', 'IP17PM-CO-2TB', 'Cam Vũ Trụ', '#f26b2f', '2TB', '12GB', '2TB', 49990000, 45990000, 10),
    ('IP17PM', 'IP17PM-CO-512', 'Cam Vũ Trụ', '#f26b2f', '512GB', '12GB', '512GB', 38990000, 34990000, 10),
    ('IP17PM', 'IP17PM-DB-1TB', 'Xanh Sâu', '#24364b', '1TB', '12GB', '1TB', 46990000, 42990000, 10),
    ('IP17PM', 'IP17PM-DB-256', 'Xanh Sâu', '#24364b', '256GB', '12GB', '256GB', 34990000, 30990000, 10),
    ('IP17PM', 'IP17PM-DB-2TB', 'Xanh Sâu', '#24364b', '2TB', '12GB', '2TB', 49990000, 45990000, 10),
    ('IP17PM', 'IP17PM-DB-512', 'Xanh Sâu', '#24364b', '512GB', '12GB', '512GB', 38990000, 34990000, 10),
    ('IP17PM', 'IP17PM-SV-1TB', 'Bạc', '#d9d9d4', '1TB', '12GB', '1TB', 46990000, 42990000, 10),
    ('IP17PM', 'IP17PM-SV-256', 'Bạc', '#d9d9d4', '256GB', '12GB', '256GB', 34990000, 30990000, 10),
    ('IP17PM', 'IP17PM-SV-2TB', 'Bạc', '#d9d9d4', '2TB', '12GB', '2TB', 49990000, 45990000, 10),
    ('IP17PM', 'IP17PM-SV-512', 'Bạc', '#d9d9d4', '512GB', '12GB', '512GB', 38990000, 34990000, 10),
    ('IPADA16', 'IPADA16-W128-SILVER', 'Bạc', '#d1d5db', '128GB', '6GB', 'A16 Wifi 128GB', 9290000, NULL, 10),
    ('IPADA16', 'IPADA16-W256-SILVER', 'Bạc', '#d1d5db', '256GB', '6GB', 'A16 Wifi 256GB', 11290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G128-SILVER', 'Bạc', '#d1d5db', '128GB', '6GB', 'A16 5G 128GB', 12290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G256-SILVER', 'Bạc', '#d1d5db', '256GB', '6GB', 'A16 5G 256GB', 14290000, NULL, 10),
    ('IPADA16', 'IPADA16-W512-SILVER', 'Bạc', '#d1d5db', '512GB', '6GB', 'A16 Wifi 512GB', 15290000, NULL, 10),
    ('IPADA16', 'IPADA16-W128-YELLOW', 'Vàng', '#f5e08c', '128GB', '6GB', 'A16 Wifi 128GB', 9290000, NULL, 10),
    ('IPADA16', 'IPADA16-W256-YELLOW', 'Vàng', '#f5e08c', '256GB', '6GB', 'A16 Wifi 256GB', 11290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G128-YELLOW', 'Vàng', '#f5e08c', '128GB', '6GB', 'A16 5G 128GB', 12290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G256-YELLOW', 'Vàng', '#f5e08c', '256GB', '6GB', 'A16 5G 256GB', 14290000, NULL, 10),
    ('IPADA16', 'IPADA16-W512-YELLOW', 'Vàng', '#f5e08c', '512GB', '6GB', 'A16 Wifi 512GB', 15290000, NULL, 10),
    ('IPADA16', 'IPADA16-W128-PINK', 'Hồng', '#e57c91', '128GB', '6GB', 'A16 Wifi 128GB', 9290000, NULL, 10),
    ('IPADA16', 'IPADA16-W256-PINK', 'Hồng', '#e57c91', '256GB', '6GB', 'A16 Wifi 256GB', 11290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G128-PINK', 'Hồng', '#e57c91', '128GB', '6GB', 'A16 5G 128GB', 12290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G256-PINK', 'Hồng', '#e57c91', '256GB', '6GB', 'A16 5G 256GB', 14290000, NULL, 10),
    ('IPADA16', 'IPADA16-W512-PINK', 'Hồng', '#e57c91', '512GB', '6GB', 'A16 Wifi 512GB', 15290000, NULL, 10),
    ('IPADA16', 'IPADA16-W128-BLUE', 'Xanh', '#4b9cd3', '128GB', '6GB', 'A16 Wifi 128GB', 9290000, NULL, 10),
    ('IPADA16', 'IPADA16-W256-BLUE', 'Xanh', '#4b9cd3', '256GB', '6GB', 'A16 Wifi 256GB', 11290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G128-BLUE', 'Xanh', '#4b9cd3', '128GB', '6GB', 'A16 5G 128GB', 12290000, NULL, 10),
    ('IPADA16', 'IPADA16-5G256-BLUE', 'Xanh', '#4b9cd3', '256GB', '6GB', 'A16 5G 256GB', 14290000, NULL, 10),
    ('IPADA16', 'IPADA16-W512-BLUE', 'Xanh', '#4b9cd3', '512GB', '6GB', 'A16 Wifi 512GB', 15290000, NULL, 10),
    ('IPADM4', 'IPADM4-1TB-BLACK', 'Đen', '#111827', '1TB', '16GB', 'Wi-Fi', 45990000, NULL, 10),
    ('IPADM4', 'IPADM4-1TB-BLACK-5G', 'Đen', '#111827', '1TB', '16GB', 'Wi-Fi + Cellular', 51990000, NULL, 10),
    ('IPADM4', 'IPADM4-1TB-SILVER', 'Bạc', '#d1d5db', '1TB', '16GB', 'Wi-Fi', 45990000, NULL, 10),
    ('IPADM4', 'IPADM4-1TB-SILVER-5G', 'Bạc', '#d1d5db', '1TB', '16GB', 'Wi-Fi + Cellular', 51990000, NULL, 10),
    ('IPADM4', 'IPADM4-1TBN-BLACK', 'Đen', '#111827', '1TB Nano', '16GB', 'Wi-Fi', 48490000, NULL, 10),
    ('IPADM4', 'IPADM4-1TBN-BLACK-5G', 'Đen', '#111827', '1TB Nano', '16GB', 'Wi-Fi + Cellular', 54490000, NULL, 10),
    ('IPADM4', 'IPADM4-1TBN-SILVER', 'Bạc', '#d1d5db', '1TB Nano', '16GB', 'Wi-Fi', 48490000, NULL, 10),
    ('IPADM4', 'IPADM4-1TBN-SILVER-5G', 'Bạc', '#d1d5db', '1TB Nano', '16GB', 'Wi-Fi + Cellular', 54490000, NULL, 10),
    ('IPADM4', 'IPADM4-256-BLACK', 'Đen', '#111827', '256GB', '8GB', 'Wi-Fi', 28990000, NULL, 10),
    ('IPADM4', 'IPADM4-256-BLACK-5G', 'Đen', '#111827', '256GB', '8GB', 'Wi-Fi + Cellular', 34990000, NULL, 10),
    ('IPADM4', 'IPADM4-256-SILVER', 'Bạc', '#d1d5db', '256GB', '8GB', 'Wi-Fi', 28990000, NULL, 10),
    ('IPADM4', 'IPADM4-256-SILVER-5G', 'Bạc', '#d1d5db', '256GB', '8GB', 'Wi-Fi + Cellular', 34990000, NULL, 10),
    ('IPADM4', 'IPADM4-2TB-BLACK', 'Đen', '#111827', '2TB', '16GB', 'Wi-Fi', 57490000, NULL, 10),
    ('IPADM4', 'IPADM4-2TB-BLACK-5G', 'Đen', '#111827', '2TB', '16GB', 'Wi-Fi + Cellular', 63490000, NULL, 10),
    ('IPADM4', 'IPADM4-2TB-SILVER', 'Bạc', '#d1d5db', '2TB', '16GB', 'Wi-Fi', 57490000, NULL, 10),
    ('IPADM4', 'IPADM4-2TB-SILVER-5G', 'Bạc', '#d1d5db', '2TB', '16GB', 'Wi-Fi + Cellular', 63490000, NULL, 10),
    ('IPADM4', 'IPADM4-2TBN-BLACK', 'Đen', '#111827', '2TB Nano', '16GB', 'Wi-Fi', 59990000, NULL, 10),
    ('IPADM4', 'IPADM4-2TBN-BLACK-5G', 'Đen', '#111827', '2TB Nano', '16GB', 'Wi-Fi + Cellular', 65990000, NULL, 10),
    ('IPADM4', 'IPADM4-2TBN-SILVER', 'Bạc', '#d1d5db', '2TB Nano', '16GB', 'Wi-Fi', 59990000, NULL, 10),
    ('IPADM4', 'IPADM4-2TBN-SILVER-5G', 'Bạc', '#d1d5db', '2TB Nano', '16GB', 'Wi-Fi + Cellular', 65990000, NULL, 10),
    ('IPADM4', 'IPADM4-512-BLACK', 'Đen', '#111827', '512GB', '8GB', 'Wi-Fi', 34990000, NULL, 10),
    ('IPADM4', 'IPADM4-512-BLACK-5G', 'Đen', '#111827', '512GB', '8GB', 'Wi-Fi + Cellular', 40990000, NULL, 10),
    ('IPADM4', 'IPADM4-512-SILVER', 'Bạc', '#d1d5db', '512GB', '8GB', 'Wi-Fi', 34990000, NULL, 10),
    ('IPADM4', 'IPADM4-512-SILVER-5G', 'Bạc', '#d1d5db', '512GB', '8GB', 'Wi-Fi + Cellular', 40990000, NULL, 10),
    ('IT-P55P', 'IT-P55P-BK-8-128', 'Đen Thiên Thạch', '#1c1c1c', '128GB', '8GB', 'RAM 8GB - 128GB', 2790000, 2590000, 50),
    ('IT-P55P', 'IT-P55P-BK-8-256', 'Đen Thiên Thạch', '#1c1c1c', '256GB', '8GB', 'RAM 8GB - 256GB', 3190000, 2890000, 50),
    ('IT-P55P', 'IT-P55P-GN-8-128', 'Xanh Hoàng Gia (Lưng da)', '#183e38', '128GB', '8GB', 'RAM 8GB - 128GB', 2790000, 2590000, 50),
    ('IT-P55P', 'IT-P55P-GN-8-256', 'Xanh Hoàng Gia (Lưng da)', '#183e38', '256GB', '8GB', 'RAM 8GB - 256GB', 3190000, 2890000, 50),
    ('IT-P55P', 'IT-P55P-PU-8-128', 'Tím Thiên Thạch', '#664263', '128GB', '8GB', 'RAM 8GB - 128GB', 2790000, 2590000, 50),
    ('IT-P55P', 'IT-P55P-PU-8-256', 'Tím Thiên Thạch', '#664263', '256GB', '8GB', 'RAM 8GB - 256GB', 3190000, 2890000, 50),
    ('IT-RS4', 'IT-RS4-BE-12-256', 'Be Thanh Lịch', '#f5f5dc', '256GB', '12GB', 'RAM 12GB - 256GB', 4290000, 3990000, 30),
    ('IT-RS4', 'IT-RS4-BE-8-128', 'Be Thanh Lịch', '#f5f5dc', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('IT-RS4', 'IT-RS4-BK-12-256', 'Đen Lurex', '#1c1c1c', '256GB', '12GB', 'RAM 12GB - 256GB', 4290000, 3990000, 30),
    ('IT-RS4', 'IT-RS4-BK-8-128', 'Đen Lurex', '#1c1c1c', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('IT-RS4', 'IT-RS4-WH-12-256', 'Trắng Bạc', '#f5f5f5', '256GB', '12GB', 'RAM 12GB - 256GB', 4290000, 3990000, 30),
    ('IT-RS4', 'IT-RS4-WH-8-128', 'Trắng Bạc', '#f5f5f5', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('LNLOQ15', 'LNLOQ15-GR-512GBSSD', 'Luna Grey', '#6b6b7b', '512GB SSD', '16GB', '512GB SSD', 25990000, 23990000, 30),
    ('MATEPAD12X', 'MATEPAD12X-GR-256GB', 'Xanh Lá Pastel', '#CDE0CD', '256GB', '8GB', '256GB', 13990000, 12990000, 10),
    ('MATEPAD12X', 'MATEPAD12X-GR-512GB', 'Xanh Lá Pastel', '#CDE0CD', '512GB', '12GB', '512GB', 15990000, 14990000, 10),
    ('MATEPAD12X', 'MATEPAD12X-WH-256GB', 'Trắng Ngọc Trai', '#D5DDE0', '256GB', '8GB', '256GB', 13990000, 12990000, 10),
    ('MATEPAD12X', 'MATEPAD12X-WH-512GB', 'Trắng Ngọc Trai', '#D5DDE0', '512GB', '12GB', '512GB', 15990000, 14990000, 10),
    ('MATEPADSE', 'MATEPADSE-BK-128GB', 'Đen Than', '#1a1c29', '128GB', '4GB', '128GB', 5990000, 5490000, 10),
    ('MATEPADSE', 'MATEPADSE-BK-64GB', 'Đen Than', '#1a1c29', '64GB', '4GB', '64GB', 4990000, 4490000, 10),
    ('MATEPADSE', 'MATEPADSE-BL-128GB', 'Xanh Dương', '#336699', '128GB', '4GB', '128GB', 5990000, 5490000, 10),
    ('MATEPADSE', 'MATEPADSE-BL-64GB', 'Xanh Dương', '#336699', '64GB', '4GB', '64GB', 4990000, 4490000, 10),
    ('MBAIRM3', 'MBAIRM3-16-512', 'Đen', '#000000', '512GB SSD', '16GB', '13 inch', 34990000, 34990000, 6),
    ('MBAIRM3', 'MBAIRM3-8-256', 'Đen', '#000000', '256GB SSD', '8GB', '13 inch', 27490000, 27490000, 10),
    ('MBNEOA18P', 'MBNEOA18P-CT-256GB SSD', 'Vàng Citrus', '#e8c547', '256GB SSD', '8GB', '256GB SSD', 15990000, 14990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-CT-512GB SSD', 'Vàng Citrus', '#e8c547', '512GB SSD', '8GB', '512GB SSD', 19990000, 18990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-IN-256GB SSD', 'Xanh Indigo', '#3f5277', '256GB SSD', '8GB', '256GB SSD', 15990000, 14990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-IN-512GB SSD', 'Xanh Indigo', '#3f5277', '512GB SSD', '8GB', '512GB SSD', 19990000, 18990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-PK-256GB SSD', 'Hồng phớt (Blush)', '#f5c6c6', '256GB SSD', '8GB', '256GB SSD', 15990000, 14990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-PK-512GB SSD', 'Hồng phớt (Blush)', '#f5c6c6', '512GB SSD', '8GB', '512GB SSD', 19990000, 18990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-SL-256GB SSD', 'Bạc (Silver)', '#c0c0c0', '256GB SSD', '8GB', '256GB SSD', 15990000, 14990000, 8),
    ('MBNEOA18P', 'MBNEOA18P-SL-512GB SSD', 'Bạc (Silver)', '#c0c0c0', '512GB SSD', '8GB', '512GB SSD', 19990000, 18990000, 8),
    ('MIPADMINI', 'MIPADMINI-GY-128GB', 'Xám Không Gian', '#383E42', '128GB', '4GB', '128GB', 4990000, 4590000, 10),
    ('MIPADMINI', 'MIPADMINI-GY-256GB', 'Xám Không Gian', '#383E42', '256GB', '6GB', '256GB', 5990000, 5490000, 10),
    ('MIPADMINI', 'MIPADMINI-SL-128GB', 'Bạc Ánh Trăng', '#E2E4E5', '128GB', '4GB', '128GB', 4990000, 4590000, 10),
    ('MIPADMINI', 'MIPADMINI-SL-256GB', 'Bạc Ánh Trăng', '#E2E4E5', '256GB', '6GB', '256GB', 5990000, 5490000, 10),
    ('MSIP13AIU', 'MSIP13AIU-UE-2TBSSD', 'Ukiyo-e Edition', '#2c3e6b', '2TB SSD', '32GB', '2TB SSD', 47990000, 44990000, 15),
    ('MZ-LK08', 'MZ-LK08-BK-12-512', 'Đen', '#1c1c1c', '512GB', '12GB', 'RAM 12GB - 512GB', 7490000, 6990000, 10),
    ('MZ-LK08', 'MZ-LK08-BK-8-256', 'Đen', '#1c1c1c', '256GB', '8GB', 'RAM 8GB - 256GB', 5990000, 5490000, 10),
    ('MZ-LK08', 'MZ-LK08-CY-12-512', 'Xanh Cyan', '#00ffff', '512GB', '12GB', 'RAM 12GB - 512GB', 7490000, 6990000, 10),
    ('MZ-LK08', 'MZ-LK08-CY-8-256', 'Xanh Cyan', '#00ffff', '256GB', '8GB', 'RAM 8GB - 256GB', 5990000, 5490000, 10),
    ('MZ-LK08', 'MZ-LK08-WH-12-512', 'Trắng', '#f5f5f5', '512GB', '12GB', 'RAM 12GB - 512GB', 7490000, 6990000, 10),
    ('MZ-LK08', 'MZ-LK08-WH-8-256', 'Trắng', '#f5f5f5', '256GB', '8GB', 'RAM 8GB - 256GB', 5990000, 5490000, 10),
    ('MZ-MB22', 'MZ-MB22-BK-8-128', 'Đen Titan', '#1a1a1c', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('MZ-MB22', 'MZ-MB22-BK-8-256', 'Đen Titan', '#1a1a1c', '256GB', '8GB', 'RAM 8GB - 256GB', 3990000, 3690000, 30),
    ('MZ-MB22', 'MZ-MB22-BU-8-128', 'Xanh Biển Sâu', '#1c3d5a', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('MZ-MB22', 'MZ-MB22-BU-8-256', 'Xanh Biển Sâu', '#1c3d5a', '256GB', '8GB', 'RAM 8GB - 256GB', 3990000, 3690000, 30),
    ('MZ-MB22', 'MZ-MB22-WH-8-128', 'Trắng Tuyết', '#f5f5f5', '128GB', '8GB', 'RAM 8GB - 128GB', 3490000, 3190000, 30),
    ('MZ-MB22', 'MZ-MB22-WH-8-256', 'Trắng Tuyết', '#f5f5f5', '256GB', '8GB', 'RAM 8GB - 256GB', 3990000, 3690000, 30),
    ('OP-FN6-OR-1TB', 'OP-FN6-OR-1TB', 'Cam Nở Rộ', '#fca172', '1TB', '16GB', '1TB', 44990000, 43990000, 10),
    ('OP-FN6-OR-1TB', 'OP-FN6-OR-512GB', 'Cam Nở Rộ', '#fca172', '512GB', '16GB', '512GB', 39990000, 38990000, 10),
    ('OP-FN6-OR-1TB', 'OP-FN6-TI-1TB', 'Titan Ánh Sao', '#8a8d8f', '1TB', '16GB', '1TB', 44990000, 43990000, 10),
    ('OP-FN6-OR-1TB', 'OP-FN6-TI-512GB', 'Titan Ánh Sao', '#8a8d8f', '512GB', '16GB', '512GB', 39990000, 38990000, 10),
    ('OP-FX8-BK-256GB', 'OP-FX8-BK-256GB', 'Đen Không Gian', '#1a1a1c', '256GB', '12GB', '256GB', 22990000, 21990000, 20),
    ('OP-FX8-BK-256GB', 'OP-FX8-BK-512GB', 'Đen Không Gian', '#1a1a1c', '512GB', '16GB', '512GB', 25990000, 24990000, 20),
    ('OP-FX8-BK-256GB', 'OP-FX8-GR-256GB', 'Xám Sao Băng', '#666666', '256GB', '12GB', '256GB', 22990000, 21990000, 20),
    ('OP-FX8-BK-256GB', 'OP-FX8-GR-512GB', 'Xám Sao Băng', '#666666', '512GB', '16GB', '512GB', 25990000, 24990000, 20),
    ('OP-FX9S', 'OP-FX9S-GR-256GB', 'Xám Bầu Trời', '#363636', '256GB', '12GB', '256GB', 19990000, 18990000, 15),
    ('OP-FX9S', 'OP-FX9S-GR-512GB', 'Xám Bầu Trời', '#363636', '512GB', '12GB', '512GB', 22990000, 21990000, 15),
    ('OP-FX9S', 'OP-FX9S-LV-256GB', 'Tím Lavender', '#a28ab7', '256GB', '12GB', '256GB', 19990000, 18990000, 15),
    ('OP-FX9S', 'OP-FX9S-LV-512GB', 'Tím Lavender', '#a28ab7', '512GB', '12GB', '512GB', 22990000, 21990000, 15),
    ('OP-FX9S', 'OP-FX9S-OR-256GB', 'Cam Hoàng Hôn', '#e57f3d', '256GB', '12GB', '256GB', 19990000, 18990000, 15),
    ('OP-FX9S', 'OP-FX9S-OR-512GB', 'Cam Hoàng Hôn', '#e57f3d', '512GB', '12GB', '512GB', 22990000, 21990000, 15),
    ('OP-FX9U', 'OP-FX9U-BR-1TB', 'Nâu Lãnh Nguyên', '#463d39', '1TB', '16GB', '1TB', 39990000, 38990000, 10),
    ('OP-FX9U', 'OP-FX9U-BR-512GB', 'Nâu Lãnh Nguyên', '#463d39', '512GB', '16GB', '512GB', 34990000, 33990000, 10),
    ('OP-FX9U', 'OP-FX9U-OR-1TB', 'Cam Hẻm Núi', '#d46b41', '1TB', '16GB', '1TB', 39990000, 38990000, 10),
    ('OP-FX9U', 'OP-FX9U-OR-512GB', 'Cam Hẻm Núi', '#d46b41', '512GB', '16GB', '512GB', 34990000, 33990000, 10),
    ('OP-RN15-AW-256GB', 'OP-RN15-AW-256GB', 'Trắng Cực Quang', '#f0f2f5', '256GB', '12GB', '256GB', 11490000, 10990000, 30),
    ('OP-RN15-AW-256GB', 'OP-RN15-AW-512GB', 'Trắng Cực Quang', '#f0f2f5', '512GB', '12GB', '512GB', 12490000, 11990000, 30),
    ('OP-RN15-AW-256GB', 'OP-RN15-DB-256GB', 'Xanh Chạng Vạng', '#1a516e', '256GB', '12GB', '256GB', 11490000, 10990000, 30),
    ('OP-RN15-AW-256GB', 'OP-RN15-DB-512GB', 'Xanh Chạng Vạng', '#1a516e', '512GB', '12GB', '512GB', 12490000, 11990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-B-12-256', 'Xanh Dương', '#2196f3', '256GB', '12GB', NULL, 9490000, 8990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-B-8-256', 'Xanh Dương', '#2196f3', '256GB', '8GB', NULL, 8490000, 7990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-LB-12-256', 'Xanh Nhạt', '#add8e6', '256GB', '12GB', NULL, 9490000, 8990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-LB-8-256', 'Xanh Nhạt', '#add8e6', '256GB', '8GB', NULL, 8490000, 7990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-PK-12-256', 'Hồng Rực Rỡ', '#ffb6c1', '256GB', '12GB', 'RAM 12GB - 256GB', 9490000, 8990000, 30),
    ('OP-RN15F-PK-8-256', 'OP-RN15F-PK-8-256', 'Hồng Rực Rỡ', '#ffb6c1', '256GB', '8GB', 'RAM 8GB - 256GB', 8490000, 7990000, 30),
    ('OPPFN3-BK-512GB', 'OPPFN3-BK-512GB', 'Đen', '#CCCCCC', '512GB', '16GB', NULL, 39990000, 34990000, 3),
    ('OPPFN3-BK-512GB', 'OPPFN3-GD-512GB', 'Vàng', '#CCCCCC', '512GB', '16GB', NULL, 39990000, 34990000, 3),
    ('POCO-X7P', 'POCO-X7P-BK-12-256', 'Đen Hắc Diệu', '#1a1a1c', '256GB', '12GB', 'RAM 12GB - 256GB', 8990000, 8490000, 40),
    ('POCO-X7P', 'POCO-X7P-BK-8-256', 'Đen Hắc Diệu', '#1a1a1c', '256GB', '8GB', 'RAM 8GB - 256GB', 7990000, 7490000, 40),
    ('POCO-X7P', 'POCO-X7P-GR-12-256', 'Xanh Tinh Vân', '#1c4a3e', '256GB', '12GB', 'RAM 12GB - 256GB', 8990000, 8490000, 40),
    ('POCO-X7P', 'POCO-X7P-GR-8-256', 'Xanh Tinh Vân', '#1c4a3e', '256GB', '8GB', 'RAM 8GB - 256GB', 7990000, 7490000, 40),
    ('POCO-X7P', 'POCO-X7P-YE-12-256', 'Vàng POCO', '#ffd100', '256GB', '12GB', 'RAM 12GB - 256GB', 8990000, 8490000, 40),
    ('POCO-X7P', 'POCO-X7P-YE-8-256', 'Vàng POCO', '#ffd100', '256GB', '8GB', 'RAM 8GB - 256GB', 7990000, 7490000, 40),
    ('POCOPADM1', 'POCOPADM1-BK-128GB', 'Đen Bạc', '#1D1E20', '128GB', '6GB', '128GB', 5290000, 4790000, 10),
    ('POCOPADM1', 'POCOPADM1-BK-64GB', 'Đen Bạc', '#1D1E20', '64GB', '4GB', '64GB', 4490000, 3990000, 10),
    ('POCOPADM1', 'POCOPADM1-GR-128GB', 'Xanh Bạc Hà', '#A0B5AA', '128GB', '6GB', '128GB', 5290000, 4790000, 10),
    ('POCOPADM1', 'POCOPADM1-GR-64GB', 'Xanh Bạc Hà', '#A0B5AA', '64GB', '4GB', '64GB', 4490000, 3990000, 10),
    ('POCOPADX1', 'POCOPADX1-BL-128GB', 'Xanh Dương', '#6699CC', '128GB', '8GB', '128GB', 7990000, 7490000, 10),
    ('POCOPADX1', 'POCOPADX1-BL-256GB', 'Xanh Dương', '#6699CC', '256GB', '8GB', '256GB', 8990000, 8490000, 10),
    ('POCOPADX1', 'POCOPADX1-GY-128GB', 'Xám Đen', '#4B5364', '128GB', '8GB', '128GB', 7990000, 7490000, 10),
    ('POCOPADX1', 'POCOPADX1-GY-256GB', 'Xám Đen', '#4B5364', '256GB', '8GB', '256GB', 8990000, 8490000, 10),
    ('REV-33E1E3B529', 'IP17-BK-256GB', 'Đen', '#000000', '256GB', '256GB', NULL, 24990000, NULL, 0),
    ('REV-33E1E3B529', 'IP17-BK-512GB', 'Đen', '#000000', '512GB', '512GB', NULL, 28990000, NULL, 0),
    ('REV-33E1E3B529', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', '256GB', '256GB', NULL, 24990000, NULL, 0),
    ('REV-33E1E3B529', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', '512GB', '512GB', NULL, 28990000, NULL, 0),
    ('REV-33E1E3B529', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', '256GB', '256GB', NULL, 24990000, NULL, 0),
    ('REV-33E1E3B529', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', '512GB', '512GB', NULL, 28990000, NULL, 0),
    ('REV-3B9B7C933A', 'IP17-BK-256GB', 'Đen', '#000000', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('REV-3B9B7C933A', 'IP17-BK-512GB', 'Đen', '#000000', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('REV-3B9B7C933A', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('REV-3B9B7C933A', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('REV-3B9B7C933A', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', '256GB', '256GB', NULL, 24990000, 24990000, 10),
    ('REV-3B9B7C933A', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', '512GB', '512GB', NULL, 28990000, 28990000, 10),
    ('REV-4375418818', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-4375418818', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-4375418818', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-4375418818', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-4375418818', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-4375418818', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-4C5D370010', 'OPPFN3-BK-512GB', 'Đen', '#CCCCCC', '512GB', '16GB', NULL, 39990000, 34990000, 3),
    ('REV-4C5D370010', 'OPPFN3-GD-512GB', 'Vàng', '#CCCCCC', '512GB', '16GB', NULL, 39990000, 34990000, 3),
    ('REV-54F35277EF', 'ASGV16-BK-512GBSSD', 'Đen (Matte Black)', '#CCCCCC', '512GB SSD', '16GB', '512GB SSD', 24990000, 22990000, 25),
    ('REV-7124BABDED', 'ASGV16-BK-512GBSSD', 'Đen (Matte Black)', '#CCCCCC', '512GB SSD', '16GB', '512GB SSD', 24990000, 22990000, 25),
    ('REV-94E7D85E41', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-94E7D85E41', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-94E7D85E41', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-94E7D85E41', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-94E7D85E41', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-94E7D85E41', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-9C9E361303', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '512GB', NULL, 24990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-CDDA941186', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 28990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-BK-256GB', 'Đen', '#000000', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-BK-512GB', 'Đen', '#000000', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-MB-256GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-MB-512GB', 'Xanh Sương Mù', '#CCCCCC', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-WH-256GB', 'Trắng', '#FFFFFF', NULL, '256GB', NULL, 24990000, NULL, 0),
    ('REV-E46E7072F9', 'IP17-WH-512GB', 'Trắng', '#FFFFFF', NULL, '512GB', NULL, 28990000, NULL, 0),
    ('RM-13P', 'RM-13P-GD-12-256', 'Vàng Chiến Thắng', '#cfb53b', '256GB', '12GB', 'RAM 12GB - 256GB', 9490000, 8990000, 25),
    ('RM-13P', 'RM-13P-GD-8-256', 'Vàng Chiến Thắng', '#cfb53b', '256GB', '8GB', 'RAM 8GB - 256GB', 8490000, 7990000, 25),
    ('RM-13P', 'RM-13P-GR-12-256', 'Xanh Tốc Độ', '#3b5c47', '256GB', '12GB', 'RAM 12GB - 256GB', 9490000, 8990000, 25),
    ('RM-13P', 'RM-13P-GR-8-256', 'Xanh Tốc Độ', '#3b5c47', '256GB', '8GB', 'RAM 8GB - 256GB', 8490000, 7990000, 25),
    ('RM-13P', 'RM-13P-PU-12-256', 'Tím Bóng Tối', '#1a1a1c', '256GB', '12GB', 'RAM 12GB - 256GB', 9490000, 8990000, 25),
    ('RM-13P', 'RM-13P-PU-8-256', 'Tím Bóng Tối', '#1a1a1c', '256GB', '8GB', 'RAM 8GB - 256GB', 8490000, 7990000, 25),
    ('RM-N14PP', 'RM-N14PP-BK-256GB', 'Đen Tinh Tú', '#1a1a1c', '256GB', '8GB', '256GB', 8490000, 7990000, 30),
    ('RM-N14PP', 'RM-N14PP-BK-512GB', 'Đen Tinh Tú', '#1a1a1c', '512GB', '12GB', '512GB', 9990000, 9490000, 30),
    ('RM-N14PP', 'RM-N14PP-BL-256GB', 'Xanh Băng Giá', '#c9e2f5', '256GB', '8GB', '256GB', 8490000, 7990000, 30),
    ('RM-N14PP', 'RM-N14PP-BL-512GB', 'Xanh Băng Giá', '#c9e2f5', '512GB', '12GB', '512GB', 9990000, 9490000, 30),
    ('RM-N14PP', 'RM-N14PP-PP-256GB', 'Tím Oải Hương', '#b4a7d6', '256GB', '8GB', '256GB', 8490000, 7990000, 30),
    ('RM-N14PP', 'RM-N14PP-PP-512GB', 'Tím Oải Hương', '#b4a7d6', '512GB', '12GB', '512GB', 9990000, 9490000, 30),
    ('RM-N15', 'RM-N15-BK-128GB', 'Đen Huyền Bí', '#1a1a1c', '128GB', '8GB', '128GB', 5490000, 4990000, 50),
    ('RM-N15', 'RM-N15-BK-256GB', 'Đen Huyền Bí', '#1a1a1c', '256GB', '8GB', '256GB', 6490000, 5990000, 50),
    ('RM-N15', 'RM-N15-BL-128GB', 'Xanh Sông Băng', '#a9cce3', '128GB', '8GB', '128GB', 5490000, 4990000, 50),
    ('RM-N15', 'RM-N15-BL-256GB', 'Xanh Sông Băng', '#a9cce3', '256GB', '8GB', '256GB', 6490000, 5990000, 50),
    ('RM-N15', 'RM-N15-PP-128GB', 'Tím Sương Mù', '#c39bd3', '128GB', '8GB', '128GB', 5490000, 4990000, 50),
    ('RM-N15', 'RM-N15-PP-256GB', 'Tím Sương Mù', '#c39bd3', '256GB', '8GB', '256GB', 6490000, 5990000, 50),
    ('RM-NT60', 'RM-NT60-BK-4-64', 'Đen Cẩm Thạch', '#1c1c1c', '64GB', '4GB', '4GB - 64GB', 2990000, 2790000, 100),
    ('RM-NT60', 'RM-NT60-BK-8-256', 'Đen Cẩm Thạch', '#1c1c1c', '256GB', '8GB', '8GB - 256GB', 3990000, 3690000, 100),
    ('RM-NT60', 'RM-NT60-BU-4-64', 'Xanh Viễn Du', '#1a516e', '64GB', '4GB', '4GB - 64GB', 2990000, 2790000, 100),
    ('RM-NT60', 'RM-NT60-BU-8-256', 'Xanh Viễn Du', '#1a516e', '256GB', '8GB', '8GB - 256GB', 3990000, 3690000, 100),
    ('S24U', 'S24U-256-GRAY', 'Titanium Gray', '#9ca3af', '256GB', '12GB', NULL, 25990000, NULL, 9),
    ('S24U', 'S24U-512-BLACK', 'Titanium Black', '#27272a', '512GB', '12GB', NULL, 29990000, NULL, 6),
    ('S26', 'S26-BK-256GB', 'Đen', '#1a1a1a', '256GB', '12GB', '256GB', 22990000, 21990000, 20),
    ('S26', 'S26-BK-512GB', 'Đen', '#1a1a1a', '512GB', '12GB', '512GB', 26990000, 25990000, 20),
    ('S26', 'S26-CV-256GB', 'Tím Cobalt', '#726b8e', '256GB', '12GB', '256GB', 22990000, 21990000, 20),
    ('S26', 'S26-CV-512GB', 'Tím Cobalt', '#726b8e', '512GB', '12GB', '512GB', 26990000, 25990000, 20),
    ('S26', 'S26-WH-256GB', 'Trắng', '#fdfdfd', '256GB', '12GB', '256GB', 22990000, 21990000, 20),
    ('S26', 'S26-WH-512GB', 'Trắng', '#fdfdfd', '512GB', '12GB', '512GB', 26990000, 25990000, 20),
    ('S26U', 'S26U-BK-1TB', 'Đen Titan', '#2f3133', '1TB', '16GB', '1TB', 44990000, 42990000, 15),
    ('S26U', 'S26U-BK-256GB', 'Đen Titan', '#2f3133', '256GB', '12GB', '256GB', 33990000, 31990000, 15),
    ('S26U', 'S26U-BK-512GB', 'Đen Titan', '#2f3133', '512GB', '12GB', '512GB', 37990000, 35990000, 15),
    ('S26U', 'S26U-SB-1TB', 'Xanh Thiên Thanh', '#9ebed2', '1TB', '16GB', '1TB', 44990000, 42990000, 15),
    ('S26U', 'S26U-SB-256GB', 'Xanh Thiên Thanh', '#9ebed2', '256GB', '12GB', '256GB', 33990000, 31990000, 15),
    ('S26U', 'S26U-SB-512GB', 'Xanh Thiên Thanh', '#9ebed2', '512GB', '12GB', '512GB', 37990000, 35990000, 15),
    ('S26U', 'S26U-WH-1TB', 'Trắng Titan', '#f1f0ee', '1TB', '16GB', '1TB', 44990000, 42990000, 15),
    ('S26U', 'S26U-WH-256GB', 'Trắng Titan', '#f1f0ee', '256GB', '12GB', '256GB', 33990000, 31990000, 15),
    ('S26U', 'S26U-WH-512GB', 'Trắng Titan', '#f1f0ee', '512GB', '12GB', '512GB', 37990000, 35990000, 15),
    ('TABS11', 'TABS11-BK-128GB', 'Đen Graphite', '#333333', '128GB', '8GB', '128GB', 19990000, 18990000, 10),
    ('TABS11', 'TABS11-BK-256GB', 'Đen Graphite', '#333333', '256GB', '8GB', '256GB', 22990000, 21990000, 10),
    ('TABS11', 'TABS11-SL-128GB', 'Bạc Titanium', '#E2E2E2', '128GB', '8GB', '128GB', 19990000, 18990000, 10),
    ('TABS11', 'TABS11-SL-256GB', 'Bạc Titanium', '#E2E2E2', '256GB', '8GB', '256GB', 22990000, 21990000, 10),
    ('TC-PV7', 'TC-PV7-BK-12-256', 'Đen Geek', '#1a1a1c', '256GB', '12GB', 'RAM 12GB - 256GB', 7490000, 6990000, 30),
    ('TC-PV7', 'TC-PV7-BK-8-256', 'Đen Geek', '#1a1a1c', '256GB', '8GB', 'RAM 8GB - 256GB', 6490000, 5990000, 30),
    ('TC-PV7', 'TC-PV7-GR-12-256', 'Xanh Ốc Đảo', '#41514e', '256GB', '12GB', 'RAM 12GB - 256GB', 7490000, 6990000, 30),
    ('TC-PV7', 'TC-PV7-GR-8-256', 'Xanh Ốc Đảo', '#41514e', '256GB', '8GB', 'RAM 8GB - 256GB', 6490000, 5990000, 30),
    ('TC-PV7', 'TC-PV7-SV-12-256', 'Bạc Ma Thuật', '#e0e4cc', '256GB', '12GB', 'RAM 12GB - 256GB', 7490000, 6990000, 30),
    ('TC-PV7', 'TC-PV7-SV-8-256', 'Bạc Ma Thuật', '#e0e4cc', '256GB', '8GB', 'RAM 8GB - 256GB', 6490000, 5990000, 30),
    ('TC-SP40PP', 'TC-SP40PP-BK-128GB', 'Đen Tinh Vân', '#1a1a1c', '128GB', '8GB', '128GB', 5490000, 4990000, 30),
    ('TC-SP40PP', 'TC-SP40PP-BK-256GB', 'Đen Tinh Vân', '#1a1a1c', '256GB', '8GB', '256GB', 5990000, 5490000, 30),
    ('TC-SP40PP', 'TC-SP40PP-GR-128GB', 'Xanh Lãnh Nguyên', '#41514e', '128GB', '8GB', '128GB', 5490000, 4990000, 30),
    ('TC-SP40PP', 'TC-SP40PP-GR-256GB', 'Xanh Lãnh Nguyên', '#41514e', '256GB', '8GB', '256GB', 5990000, 5490000, 30),
    ('TC-SP40PP', 'TC-SP40PP-TI-128GB', 'Titan Ánh Trăng', '#8a8d8f', '128GB', '8GB', '128GB', 5490000, 4990000, 30),
    ('TC-SP40PP', 'TC-SP40PP-TI-256GB', 'Titan Ánh Trăng', '#8a8d8f', '256GB', '8GB', '256GB', 5990000, 5490000, 30),
    ('TC-SP40PP', 'TC-SP40PP-WH-128GB', 'Trắng Cực Quang', '#f5f5f5', '128GB', '8GB', '128GB', 5490000, 4990000, 30),
    ('TC-SP40PP', 'TC-SP40PP-WH-256GB', 'Trắng Cực Quang', '#f5f5f5', '256GB', '8GB', '256GB', 5990000, 5490000, 30),
    ('TC-SP50', 'TC-SP50-BK-128GB', 'Đen Mực', '#1c1c1c', '128GB', '8GB', '128GB', 4490000, 3990000, 50),
    ('TC-SP50', 'TC-SP50-BK-256GB', 'Đen Mực', '#1c1c1c', '256GB', '8GB', '256GB', 4990000, 4490000, 50),
    ('TC-SP50', 'TC-SP50-GR-128GB', 'Xanh Bạc Hà', '#a2d5c6', '128GB', '8GB', '128GB', 4490000, 3990000, 50),
    ('TC-SP50', 'TC-SP50-GR-256GB', 'Xanh Bạc Hà', '#a2d5c6', '256GB', '8GB', '256GB', 4990000, 4490000, 50),
    ('TC-SP50', 'TC-SP50-PP-128GB', 'Tím Ảo Ảnh', '#bfa1ce', '128GB', '8GB', '128GB', 4490000, 3990000, 50),
    ('TC-SP50', 'TC-SP50-PP-256GB', 'Tím Ảo Ảnh', '#bfa1ce', '256GB', '8GB', '256GB', 4990000, 4490000, 50),
    ('TEST-1780565512-BK-128', 'TEST-1780565512-BK-128', '?en', NULL, '128GB', '8GB', NULL, 1234000, NULL, 2),
    ('XM-17U', 'XM-17U-BK-1TB', 'Đen', '#1a1a1c', '1TB', '16GB', '1TB', 39990000, 37990000, 10),
    ('XM-17U', 'XM-17U-BK-512GB', 'Đen', '#1a1a1c', '512GB', '16GB', '512GB', 34990000, 32990000, 10),
    ('XM-17U', 'XM-17U-GR-1TB', 'Xanh Rêu', '#41514e', '1TB', '16GB', '1TB', 39990000, 37990000, 10),
    ('XM-17U', 'XM-17U-GR-512GB', 'Xanh Rêu', '#41514e', '512GB', '16GB', '512GB', 34990000, 32990000, 10),
    ('XM-17U', 'XM-17U-PP-1TB', 'Tím', '#6e6270', '1TB', '16GB', '1TB', 39990000, 37990000, 10),
    ('XM-17U', 'XM-17U-PP-512GB', 'Tím', '#6e6270', '512GB', '16GB', '512GB', 34990000, 32990000, 10),
    ('XM-17U', 'XM-17U-WH-1TB', 'Trắng', '#f5f5f5', '1TB', '16GB', '1TB', 39990000, 37990000, 10),
    ('XM-17U', 'XM-17U-WH-512GB', 'Trắng', '#f5f5f5', '512GB', '16GB', '512GB', 34990000, 32990000, 10),
    ('YOGATAB', 'YOGATAB-GY-128GB', 'Xám Bão', '#4A4D54', '128GB', '4GB', '128GB', 8990000, 7990000, 10),
    ('YOGATAB', 'YOGATAB-GY-256GB', 'Xám Bão', '#4A4D54', '256GB', '8GB', '256GB', 10990000, 9990000, 10)
)
INSERT INTO product_variants (
    product_id, sku, color_name, color_code, storage, ram, configuration,
    price, sale_price, stock_quantity
)
SELECT
    products.id,
    variant_seed.sku,
    variant_seed.color_name,
    variant_seed.color_code,
    variant_seed.storage,
    variant_seed.ram,
    variant_seed.configuration,
    variant_seed.price,
    variant_seed.sale_price::NUMERIC(14, 2),
    variant_seed.stock_quantity
FROM (
    SELECT DISTINCT ON (sku) *
    FROM variant_seed
    ORDER BY sku
) AS variant_seed
JOIN products ON products.sku = variant_seed.product_sku
ON CONFLICT (sku) DO UPDATE SET
    color_name = EXCLUDED.color_name,
    color_code = EXCLUDED.color_code,
    storage = EXCLUDED.storage,
    ram = EXCLUDED.ram,
    configuration = EXCLUDED.configuration,
    price = EXCLUDED.price,
    sale_price = EXCLUDED.sale_price,
    stock_quantity = EXCLUDED.stock_quantity,
    is_active = TRUE,
    updated_at = NOW();

-- MIGRATION 004 FOR USERS AND PASSWORD RESET TOKENS

-- ==========================================
-- Migration: 004_user_auth_profile.sql
-- ==========================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS profile JSONB NOT NULL DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS addresses JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token TEXT PRIMARY KEY,
    email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email ON password_reset_tokens(email);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL DEFAULT 'order',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rewards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cost INTEGER NOT NULL DEFAULT 0 CHECK (cost >= 0),
    image_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_url TEXT,
    thumbnail_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_rewards_is_active ON rewards(is_active);
CREATE INDEX IF NOT EXISTS idx_videos_is_active ON videos(is_active);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS content_type VARCHAR(30) NOT NULL DEFAULT 'VIDEO';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'DRAFT';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS content_body TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS banner_image_url TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS cta_label VARCHAR(160);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS cta_url TEXT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS like_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE videos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_source VARCHAR(30) NOT NULL DEFAULT 'UPLOAD';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_category VARCHAR(60) NOT NULL DEFAULT 'PRODUCT';
CREATE INDEX IF NOT EXISTS idx_videos_content_type ON videos(content_type);
CREATE INDEX IF NOT EXISTS idx_videos_sort_order ON videos(sort_order DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_scheduled_at ON videos(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_videos_deleted_at ON videos(deleted_at);
CREATE INDEX IF NOT EXISTS idx_videos_video_category ON videos(video_category);
CREATE INDEX IF NOT EXISTS idx_videos_storefront_feed
    ON videos(is_active, deleted_at, published_at, sort_order DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_admin_search
    ON videos
    USING GIN (to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(content_body, '')));

CREATE TABLE IF NOT EXISTS content_product_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(content_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_content_product_relations_content_id
    ON content_product_relations(content_id);
CREATE INDEX IF NOT EXISTS idx_content_product_relations_product_id
    ON content_product_relations(product_id);

CREATE TABLE IF NOT EXISTS content_category_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(content_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_content_category_relations_content_id
    ON content_category_relations(content_id);
CREATE INDEX IF NOT EXISTS idx_content_category_relations_category_id
    ON content_category_relations(category_id);

CREATE TABLE IF NOT EXISTS content_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_name VARCHAR(120) NOT NULL,
    body TEXT NOT NULL,
    parent_id UUID REFERENCES content_comments(id) ON DELETE CASCADE,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    reply_to_user_name VARCHAR(120),
    moderation_reason VARCHAR(255),
    is_retracted BOOLEAN NOT NULL DEFAULT FALSE,
    retracted_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_content_comments_content_id
    ON content_comments(content_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_comments_parent_id
    ON content_comments(parent_id);

CREATE TABLE IF NOT EXISTS video_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_video_likes_video_id ON video_likes(video_id);
CREATE INDEX IF NOT EXISTS idx_video_likes_user_id ON video_likes(user_id);


-- ==========================================
-- Migration: 005_admin_content_page_cleanup.sql
-- ==========================================



-- ==========================================
-- Migration: 006_catalog_admin_media_variants.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS spec_fields JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE brands ADD COLUMN IF NOT EXISTS logo_url TEXT;

ALTER TABLE products ADD COLUMN IF NOT EXISTS video_url TEXT;

ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS specs JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS images JSONB NOT NULL DEFAULT '[]'::jsonb;


-- ==========================================
-- Migration: 007_voucher_targeting_limits.sql
-- ==========================================

ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS per_user_limit INTEGER NOT NULL DEFAULT 0 CHECK (per_user_limit >= 0),
    ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(40) NOT NULL DEFAULT 'CONVERSION',
    ADD COLUMN IF NOT EXISTS audience_type VARCHAR(40) NOT NULL DEFAULT 'PUBLIC',
    ADD COLUMN IF NOT EXISTS eligible_tiers JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS assigned_user_id UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS first_order_only BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS hidden_code BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS abandoned_cart_only BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS internal_note TEXT;

CREATE INDEX IF NOT EXISTS idx_vouchers_campaign_type ON vouchers(campaign_type);
CREATE INDEX IF NOT EXISTS idx_vouchers_audience_type ON vouchers(audience_type);
CREATE INDEX IF NOT EXISTS idx_vouchers_assigned_user_id ON vouchers(assigned_user_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_window ON vouchers(starts_at, ends_at);

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS voucher_code VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_orders_user_voucher ON orders(user_id, voucher_code);


-- ==========================================
-- Migration: 008_voucher_advanced_limits.sql
-- ==========================================

ALTER TABLE vouchers
    ADD COLUMN IF NOT EXISTS total_budget_cap NUMERIC(14, 2) CHECK (total_budget_cap IS NULL OR total_budget_cap >= 0),
    ADD COLUMN IF NOT EXISTS total_discount_used NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (total_discount_used >= 0),
    ADD COLUMN IF NOT EXISTS per_device_limit INTEGER NOT NULL DEFAULT 0 CHECK (per_device_limit >= 0),
    ADD COLUMN IF NOT EXISTS per_ip_limit INTEGER NOT NULL DEFAULT 0 CHECK (per_ip_limit >= 0),
    ADD COLUMN IF NOT EXISTS eligible_user_registered_after TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS include_product_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS exclude_product_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS include_category_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS exclude_category_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS validity_days_after_claim INTEGER NOT NULL DEFAULT 0 CHECK (validity_days_after_claim >= 0),
    ADD COLUMN IF NOT EXISTS stackable BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS refund_policy VARCHAR(40) NOT NULL DEFAULT 'SHOP_FAULT_ONLY';

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS voucher_device_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS voucher_ip_address VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_orders_voucher_device ON orders(voucher_code, voucher_device_id);
CREATE INDEX IF NOT EXISTS idx_orders_voucher_ip ON orders(voucher_code, voucher_ip_address);


-- ==========================================
-- Migration: 009_category_spec_field_groups.sql
-- ==========================================

UPDATE categories
SET spec_fields = '[
  {"key":"screen_size","label":"Kích thước màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"screen_technology","label":"Công nghệ màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"resolution","label":"Độ phân giải","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"refresh_rate","label":"Tần số quét","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"brightness","label":"Độ sáng tối đa","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"processor","label":"Chip xử lý","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"ram","label":"RAM","group":"Hiệu năng","type":"text","required":true,"variant":true},
  {"key":"storage","label":"Bộ nhớ trong","group":"Hiệu năng","type":"text","required":false,"variant":true},
  {"key":"os","label":"Hệ điều hành","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"rear_camera","label":"Camera sau","group":"Camera","type":"text","required":false,"variant":false},
  {"key":"front_camera","label":"Camera trước","group":"Camera","type":"text","required":false,"variant":false},
  {"key":"video_recording","label":"Quay video","group":"Camera","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Dung lượng pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"charging","label":"Công nghệ sạc","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"sim","label":"SIM","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"network","label":"Mạng di động","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"connectivity","label":"Kết nối khác","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"material","label":"Chất liệu","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"dimensions","label":"Kích thước","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'smartphones';

UPDATE categories
SET spec_fields = '[
  {"key":"screen_size","label":"Kích thước màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"screen_technology","label":"Công nghệ màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"resolution","label":"Độ phân giải","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"refresh_rate","label":"Tần số quét","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"processor","label":"CPU","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"graphics","label":"Card đồ họa","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"ram","label":"RAM","group":"Hiệu năng","type":"text","required":true,"variant":true},
  {"key":"storage","label":"Ổ cứng","group":"Hiệu năng","type":"text","required":false,"variant":true},
  {"key":"os","label":"Hệ điều hành","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"ports","label":"Cổng kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"wireless","label":"Kết nối không dây","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"webcam","label":"Webcam","group":"Camera & âm thanh","type":"text","required":false,"variant":false},
  {"key":"audio","label":"Âm thanh","group":"Camera & âm thanh","type":"text","required":false,"variant":false},
  {"key":"keyboard","label":"Bàn phím","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"material","label":"Chất liệu","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"dimensions","label":"Kích thước","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'laptops';

UPDATE categories
SET spec_fields = '[
  {"key":"screen_size","label":"Kích thước màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"screen_technology","label":"Công nghệ màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"resolution","label":"Độ phân giải","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"refresh_rate","label":"Tần số quét","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"processor","label":"Chip xử lý","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"ram","label":"RAM","group":"Hiệu năng","type":"text","required":false,"variant":true},
  {"key":"storage","label":"Bộ nhớ trong","group":"Hiệu năng","type":"text","required":false,"variant":true},
  {"key":"os","label":"Hệ điều hành","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"rear_camera","label":"Camera sau","group":"Camera","type":"text","required":false,"variant":false},
  {"key":"front_camera","label":"Camera trước","group":"Camera","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Dung lượng pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"charging","label":"Công nghệ sạc","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"connectivity","label":"Kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"sim","label":"SIM/eSIM","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"dimensions","label":"Kích thước","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'tablets';

UPDATE categories
SET spec_fields = '[
  {"key":"screen_size","label":"Kích thước màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"screen_technology","label":"Công nghệ màn hình","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"resolution","label":"Độ phân giải","group":"Màn hình","type":"text","required":false,"variant":false},
  {"key":"processor","label":"Chip xử lý","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"storage","label":"Bộ nhớ","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"sensors","label":"Cảm biến sức khỏe","group":"Tính năng","type":"text","required":false,"variant":false},
  {"key":"sports_modes","label":"Chế độ luyện tập","group":"Tính năng","type":"text","required":false,"variant":false},
  {"key":"water_resistance","label":"Kháng nước","group":"Độ bền","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Thời lượng pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"charging","label":"Sạc","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"connectivity","label":"Kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"compatibility","label":"Tương thích","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"case_size","label":"Kích thước mặt","group":"Thiết kế","type":"text","required":false,"variant":true},
  {"key":"strap","label":"Dây đeo","group":"Thiết kế","type":"text","required":false,"variant":true},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'wearables';

UPDATE categories
SET spec_fields = '[
  {"key":"sensor","label":"Cảm biến","group":"Hình ảnh","type":"text","required":false,"variant":false},
  {"key":"resolution","label":"Độ phân giải","group":"Hình ảnh","type":"text","required":false,"variant":false},
  {"key":"lens","label":"Ống kính","group":"Hình ảnh","type":"text","required":false,"variant":false},
  {"key":"zoom","label":"Zoom","group":"Hình ảnh","type":"text","required":false,"variant":false},
  {"key":"video_recording","label":"Quay video","group":"Video","type":"text","required":false,"variant":false},
  {"key":"stabilization","label":"Chống rung","group":"Video","type":"text","required":false,"variant":false},
  {"key":"field_of_view","label":"Góc nhìn","group":"Video","type":"text","required":false,"variant":false},
  {"key":"storage","label":"Lưu trữ","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"connectivity","label":"Kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"water_resistance","label":"Kháng nước/bụi","group":"Độ bền","type":"text","required":false,"variant":false},
  {"key":"dimensions","label":"Kích thước","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'cameras';

UPDATE categories
SET spec_fields = '[
  {"key":"accessory_type","label":"Loại phụ kiện","group":"Thông tin chung","type":"text","required":false,"variant":false},
  {"key":"compatibility","label":"Tương thích","group":"Thông tin chung","type":"text","required":false,"variant":false},
  {"key":"power","label":"Công suất","group":"Hiệu năng","type":"text","required":false,"variant":false},
  {"key":"capacity","label":"Dung lượng","group":"Hiệu năng","type":"text","required":false,"variant":true},
  {"key":"ports","label":"Cổng kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"connectivity","label":"Chuẩn kết nối","group":"Kết nối","type":"text","required":false,"variant":false},
  {"key":"charging_standard","label":"Chuẩn sạc","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"battery","label":"Pin","group":"Pin & sạc","type":"text","required":false,"variant":false},
  {"key":"material","label":"Chất liệu","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"color","label":"Màu sắc","group":"Thiết kế","type":"text","required":false,"variant":true},
  {"key":"dimensions","label":"Kích thước","group":"Thiết kế","type":"text","required":false,"variant":false},
  {"key":"weight","label":"Trọng lượng","group":"Thiết kế","type":"text","required":false,"variant":false}
]'::jsonb,
updated_at = NOW()
WHERE parent_id IS NULL AND slug = 'accessories';


-- ==========================================
-- Migration: 010_staff_admin_role.sql
-- ==========================================

INSERT INTO roles (code, name)
VALUES
  ('STAFF_ADMIN', 'Staff Admin'),
  ('SUPER_ADMIN', 'Super Administrator')
ON CONFLICT (code) DO NOTHING;

UPDATE users
SET role_id = (SELECT id FROM roles WHERE code = 'STAFF_ADMIN')
WHERE role_id = (SELECT id FROM roles WHERE code = 'ADMIN')
  AND EXISTS (SELECT 1 FROM roles WHERE code = 'STAFF_ADMIN');

DELETE FROM roles
WHERE code = 'ADMIN'
  AND NOT EXISTS (SELECT 1 FROM users WHERE users.role_id = roles.id);


-- ==========================================
-- Migration: 011_split_camera_categories.sql
-- ==========================================

INSERT INTO categories (code, slug, name, icon, sort_order, is_active)
VALUES
  ('may-anh', 'may-anh', 'Máy ảnh', 'camera', 6, TRUE)
ON CONFLICT (code) DO UPDATE SET
  slug = EXCLUDED.slug,
  name = EXCLUDED.name,
  icon = EXCLUDED.icon,
  sort_order = EXCLUDED.sort_order,
  parent_id = NULL,
  is_active = TRUE,
  updated_at = NOW();

UPDATE categories
SET name = 'Camera',
    slug = 'cameras',
    icon = 'camera',
    sort_order = 7,
    parent_id = NULL,
    is_active = TRUE,
    updated_at = NOW()
WHERE code = 'cameras';

UPDATE categories
SET parent_id = (SELECT id FROM categories WHERE code = 'may-anh'),
    sort_order = CASE code
      WHEN 'camera-mirrorless' THEN 1
      WHEN 'camera-dslr' THEN 2
      ELSE sort_order
    END,
    updated_at = NOW()
WHERE code IN ('camera-mirrorless', 'camera-dslr');

UPDATE categories
SET parent_id = (SELECT id FROM categories WHERE code = 'cameras'),
    sort_order = CASE code
      WHEN 'action-camera' THEN 1
      WHEN 'security-camera' THEN 2
      WHEN 'dashcam' THEN 3
      ELSE sort_order
    END,
    updated_at = NOW()
WHERE code IN ('action-camera', 'security-camera', 'dashcam');

UPDATE products
SET category_id = (SELECT id FROM categories WHERE code = 'may-anh'),
    category = 'MAY-ANH',
    updated_at = NOW()
WHERE subcategory_id IN (
  SELECT id FROM categories WHERE code IN ('camera-mirrorless', 'camera-dslr')
);

DELETE FROM brand_categories
WHERE category_id IN (SELECT id FROM categories WHERE code IN ('cameras', 'may-anh'))
  AND brand_id IN (SELECT id FROM brands WHERE name IN ('Sony', 'Canon', 'Fujifilm'));

INSERT INTO brand_categories (brand_id, category_id)
SELECT brands.id, categories.id
FROM brands
JOIN categories ON categories.code = 'may-anh'
WHERE brands.name IN ('Sony', 'Canon', 'Fujifilm')
ON CONFLICT DO NOTHING;

INSERT INTO brand_categories (brand_id, category_id)
SELECT brands.id, categories.id
FROM brands
JOIN categories ON categories.code = 'cameras'
WHERE brands.name IN ('GoPro', 'DJI', 'Ezviz', 'Imou', 'Vietmap', '70mai')
ON CONFLICT DO NOTHING;


-- ==========================================
-- Migration: 012_backend_auth_verification.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS registration_verification_tokens (
    token TEXT PRIMARY KEY,
    code VARCHAR(6) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_registration_verification_tokens_email
ON registration_verification_tokens(email);

CREATE INDEX IF NOT EXISTS idx_registration_verification_tokens_expires_at
ON registration_verification_tokens(expires_at);

ALTER TABLE password_reset_tokens
ADD COLUMN IF NOT EXISTS code VARCHAR(6),
ADD COLUMN IF NOT EXISTS verification_token TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_password_reset_tokens_verification_token
ON password_reset_tokens(verification_token);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_code_email
ON password_reset_tokens(email, code);

CREATE INDEX IF NOT EXISTS idx_registration_verification_tokens_code_email
ON registration_verification_tokens(email, code);


-- ==========================================
-- Migration: 013_refresh_token_rotation_audit.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS refresh_token_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(80),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID,
    grace_until TIMESTAMPTZ,
    replaced_by_token_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ
);

ALTER TABLE refresh_token_sessions
ADD COLUMN IF NOT EXISTS grace_until TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS replaced_by_token_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_refresh_token_sessions_user_id
ON refresh_token_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_refresh_token_sessions_token_hash
ON refresh_token_sessions(token_hash);

CREATE TABLE IF NOT EXISTS security_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(80) NOT NULL,
    email VARCHAR(255),
    ip_address VARCHAR(80),
    user_agent TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_audit_logs_user_id
ON security_audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_security_audit_logs_event_type
ON security_audit_logs(event_type);

CREATE TABLE IF NOT EXISTS auth_session_revocations (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    revoked_after TIMESTAMPTZ NOT NULL,
    reason VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ==========================================
-- Migration: 014_inventory_adjustment_logs.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS inventory_adjustment_logs (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    old_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    reason VARCHAR(80) NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_adjustment_logs_product
    ON inventory_adjustment_logs(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inventory_adjustment_logs_variant
    ON inventory_adjustment_logs(variant_id, created_at DESC);


-- ==========================================
-- Migration: 015_product_status_draft.sql
-- ==========================================

ALTER TABLE products
    DROP CONSTRAINT IF EXISTS products_status_check;

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('ACTIVE', 'INACTIVE', 'OUT_OF_STOCK', 'DRAFT'));


-- ==========================================
-- Migration: 016_catalog_inventory_state_machine.sql
-- ==========================================

ALTER TABLE products
    DROP CONSTRAINT IF EXISTS products_status_check;

UPDATE products
SET status = CASE
    WHEN status = 'OUT_OF_STOCK' THEN 'ACTIVE'
    WHEN status IN ('DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'ARCHIVED') THEN status
    ELSE 'DRAFT'
END;

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'ARCHIVED'));

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS reference_code VARCHAR(120);

UPDATE inventory_adjustment_logs
SET reference_code = COALESCE(reference_code, 'LEGACY-' || id::text);

ALTER TABLE inventory_adjustment_logs
    ALTER COLUMN reference_code SET NOT NULL;

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(30) NOT NULL DEFAULT 'ADJUSTMENT';

ALTER TABLE inventory_adjustment_logs
    DROP CONSTRAINT IF EXISTS inventory_adjustment_logs_transaction_type_check;

ALTER TABLE inventory_adjustment_logs
    ADD CONSTRAINT inventory_adjustment_logs_transaction_type_check
    CHECK (transaction_type IN ('RECEIPT', 'ADJUSTMENT', 'SALE', 'RETURN', 'REVERSAL'));

CREATE INDEX IF NOT EXISTS idx_inventory_adjustment_logs_reference
    ON inventory_adjustment_logs(reference_code);


-- ==========================================
-- Migration: 017_admin_rbac_permissions.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(120) NOT NULL UNIQUE,
    module VARCHAR(60) NOT NULL,
    description VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions(module);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);

INSERT INTO permissions (code, module, description)
VALUES
    ('overview:read', 'overview', 'Xem tổng quan quản trị'),
    ('product:read', 'product', 'Xem sản phẩm'),
    ('product:create', 'product', 'Tạo sản phẩm'),
    ('product:update', 'product', 'Cập nhật sản phẩm'),
    ('product:delete', 'product', 'Ẩn hoặc lưu trữ sản phẩm'),
    ('category:read', 'category', 'Xem danh mục'),
    ('category:create', 'category', 'Tạo danh mục'),
    ('category:update', 'category', 'Cập nhật danh mục'),
    ('category:delete', 'category', 'Xóa hoặc ẩn danh mục'),
    ('brand:read', 'brand', 'Xem thương hiệu'),
    ('brand:create', 'brand', 'Tạo thương hiệu'),
    ('brand:update', 'brand', 'Cập nhật thương hiệu'),
    ('brand:delete', 'brand', 'Xóa hoặc ẩn thương hiệu'),
    ('order:read', 'order', 'Xem đơn hàng'),
    ('order:update', 'order', 'Cập nhật đơn hàng'),
    ('voucher:read', 'voucher', 'Xem voucher'),
    ('voucher:create', 'voucher', 'Tạo voucher'),
    ('voucher:update', 'voucher', 'Cập nhật voucher'),
    ('voucher:delete', 'voucher', 'Tắt voucher'),
    ('customer:read', 'customer', 'Xem khách hàng'),
    ('inventory:read', 'inventory', 'Xem tồn kho'),
    ('inventory:adjust', 'inventory', 'Điều chỉnh tồn kho'),
    ('review:read', 'review', 'Xem đánh giá'),
    ('review:update', 'review', 'Duyệt hoặc ẩn đánh giá'),
    ('review:delete', 'review', 'Xóa đánh giá'),
    ('content:read', 'content', 'Xem nội dung'),
    ('audit:read', 'audit', 'Xem nhật ký quản trị'),
    ('sys:manage_users', 'sys', 'Quản lý vai trò và trạng thái người dùng'),
    ('sys:manage_roles', 'sys', 'Quản lý ma trận phân quyền')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO permissions (code, module, description)
VALUES
    ('content:create', 'content', 'Tao video, banner va noi dung'),
    ('content:update', 'content', 'Cap nhat video, banner va noi dung'),
    ('content:delete', 'content', 'Xoa hoac an video, banner va noi dung')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
    'overview:read',
    'product:read',
    'category:read',
    'brand:read',
    'order:read',
    'customer:read',
    'inventory:read',
    'review:read',
    'content:read'
)
WHERE r.code = 'STAFF_ADMIN'
ON CONFLICT DO NOTHING;


-- ==========================================
-- Migration: 018_admin_mfa_security.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS admin_mfa_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_mfa_settings_enabled
ON admin_mfa_settings(mfa_enabled);


-- ==========================================
-- Migration: 019_category_media_filters.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS icon_url TEXT;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS banner_url TEXT;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS filter_config JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_slug_unique ON categories(slug);


-- ==========================================
-- Migration: 020_category_hidden_by_parent.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS hidden_by_parent BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_categories_parent_active ON categories(parent_id, is_active);


-- ==========================================
-- Migration: 021_brand_landing_seo_import.sql
-- ==========================================

ALTER TABLE brands ADD COLUMN IF NOT EXISTS slug VARCHAR(120);
ALTER TABLE brands ADD COLUMN IF NOT EXISTS landing_title VARCHAR(255);
WITH normalized AS (
    SELECT
        id,
        lower(regexp_replace(regexp_replace(trim(name), '[^[:alnum:]]+', '-', 'g'), '(^-|-$)', '', 'g')) AS base_slug
    FROM brands
    WHERE slug IS NULL OR slug = ''
),
deduped AS (
    SELECT
        id,
        CASE
            WHEN COUNT(*) OVER (PARTITION BY base_slug) > 1
                THEN concat(NULLIF(base_slug, ''), '-', left(id::text, 8))
            ELSE COALESCE(NULLIF(base_slug, ''), left(id::text, 8))
        END AS final_slug
    FROM normalized
)
UPDATE brands
SET slug = deduped.final_slug
FROM deduped
WHERE brands.id = deduped.id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_slug_unique ON brands(slug);


-- ==========================================
-- Migration: 022_brand_enterprise_controls.sql
-- ==========================================

ALTER TABLE brands ADD COLUMN IF NOT EXISTS logo_alt_text VARCHAR(255);

CREATE TABLE IF NOT EXISTS brand_slug_redirects (
    id UUID PRIMARY KEY,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    old_slug VARCHAR(255) NOT NULL UNIQUE,
    new_slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brand_slug_redirects_brand_id
ON brand_slug_redirects(brand_id);

CREATE TABLE IF NOT EXISTS brand_import_jobs (
    id UUID PRIMARY KEY,
    mode VARCHAR(20) NOT NULL DEFAULT 'skip',
    source_filename VARCHAR(255),
    total_rows INT NOT NULL DEFAULT 0,
    imported_rows INT NOT NULL DEFAULT 0,
    updated_rows INT NOT NULL DEFAULT 0,
    skipped_rows INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
    report JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ==========================================
-- Migration: 023_brand_import_queue_audit.sql
-- ==========================================

ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS progress INT NOT NULL DEFAULT 0;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS processed_rows INT NOT NULL DEFAULT 0;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

UPDATE brand_import_jobs
SET progress = CASE WHEN status IN ('COMPLETED', 'FAILED') THEN 100 ELSE progress END,
    processed_rows = CASE WHEN processed_rows = 0 THEN total_rows ELSE processed_rows END
WHERE status IN ('COMPLETED', 'FAILED');

CREATE INDEX IF NOT EXISTS idx_brand_import_jobs_status_created
ON brand_import_jobs(status, created_at DESC);


-- ==========================================
-- Migration: 024_brand_import_file_cache_version.sql
-- ==========================================

ALTER TABLE brands ADD COLUMN IF NOT EXISTS cache_version BIGINT NOT NULL DEFAULT 1;
ALTER TABLE brand_import_jobs ADD COLUMN IF NOT EXISTS source_path TEXT;


-- ==========================================
-- Migration: 025_product_lifecycle_relations.sql
-- ==========================================

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS seo_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS sales_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS is_price_out_of_stock BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS parent_product_id UUID REFERENCES products(id) ON DELETE CASCADE;

ALTER TABLE products
    DROP CONSTRAINT IF EXISTS products_status_check;

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('DRAFT', 'REVISION_DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'DISCONTINUED', 'ARCHIVED', 'MERGED'));

CREATE TABLE IF NOT EXISTS product_bundles (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    bundled_product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (product_id, bundled_product_id),
    CHECK (product_id <> bundled_product_id)
);

CREATE TABLE IF NOT EXISTS product_accessories (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    accessory_product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (product_id, accessory_product_id),
    CHECK (product_id <> accessory_product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_bundles_bundled_product
    ON product_bundles(bundled_product_id);

CREATE INDEX IF NOT EXISTS idx_product_accessories_accessory_product
    ON product_accessories(accessory_product_id);

CREATE TABLE IF NOT EXISTS product_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    total_rows INTEGER NOT NULL DEFAULT 0,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_rows INTEGER NOT NULL DEFAULT 0,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    file_path TEXT,
    download_url TEXT,
    expires_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_inventory_idempotency (
    idempotency_key VARCHAR(160) PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_parent_product
    ON products(parent_product_id);

CREATE TABLE IF NOT EXISTS product_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES users(id),
    action VARCHAR(80) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_audit_logs_product_created
    ON product_audit_logs(product_id, created_at DESC);

CREATE TABLE IF NOT EXISTS brand_status_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    target_is_active BOOLEAN NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    total_products INTEGER NOT NULL DEFAULT 0,
    processed_products INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ==========================================
-- Migration: 026_category_workflow_seo_soft_delete.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

UPDATE categories
SET status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END
WHERE status IS NULL OR status = '';

CREATE INDEX IF NOT EXISTS idx_categories_status_deleted ON categories(status, is_deleted);
CREATE INDEX IF NOT EXISTS idx_categories_parent_visible ON categories(parent_id, status, is_deleted);


-- ==========================================
-- Migration: 027_category_scale_safety.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS previous_status VARCHAR(30);

CREATE TABLE IF NOT EXISTS url_redirects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path VARCHAR(255) NOT NULL UNIQUE,
    target_path VARCHAR(255) NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 301,
    entity_type VARCHAR(60) NOT NULL DEFAULT 'category',
    entity_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_url_redirects_source_path ON url_redirects(source_path);

CREATE TABLE IF NOT EXISTS category_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id),
    actor_id UUID,
    action_type VARCHAR(80) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_category_audit_logs_category_created
    ON category_audit_logs(category_id, created_at DESC);


-- ==========================================
-- Migration: 028_category_enterprise_guardrails.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS spec_schema_version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS category_migration_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id),
    old_parent_id UUID,
    new_parent_id UUID,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    total_products INTEGER NOT NULL DEFAULT 0,
    processed_products INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_category_migration_jobs_category_created
    ON category_migration_jobs(category_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sitemap_refresh_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(60) NOT NULL,
    entity_id UUID,
    reason VARCHAR(120) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sitemap_refresh_events_status_created
    ON sitemap_refresh_events(status, created_at DESC);

CREATE TABLE IF NOT EXISTS category_audit_log_archives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    archive_month DATE NOT NULL UNIQUE,
    storage_uri TEXT,
    archived_rows INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);


-- ==========================================
-- Migration: 029_category_ltree_path.sql
-- ==========================================

CREATE EXTENSION IF NOT EXISTS ltree;

ALTER TABLE categories ADD COLUMN IF NOT EXISTS path LTREE;

UPDATE categories root
SET path = ('c_' || replace(root.id::text, '-', ''))::ltree
WHERE root.parent_id IS NULL AND root.path IS NULL;

WITH RECURSIVE tree AS (
    SELECT id, parent_id, path
    FROM categories
    WHERE parent_id IS NULL
    UNION ALL
    SELECT child.id, child.parent_id, tree.path || ('c_' || replace(child.id::text, '-', ''))::ltree
    FROM categories child
    JOIN tree ON child.parent_id = tree.id
)
UPDATE categories c
SET path = tree.path
FROM tree
WHERE c.id = tree.id;

CREATE INDEX IF NOT EXISTS idx_categories_path_gist ON categories USING GIST(path);


-- ==========================================
-- Migration: 030_category_enterprise_hardening.sql
-- ==========================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(30) NOT NULL DEFAULT 'APPROVED';

ALTER TABLE category_migration_jobs ADD COLUMN IF NOT EXISTS job_type VARCHAR(40) NOT NULL DEFAULT 'SPEC_MIGRATION';

CREATE INDEX IF NOT EXISTS idx_category_migration_jobs_running
    ON category_migration_jobs(category_id, status)
    WHERE status IN ('PENDING', 'RUNNING', 'IN_PROGRESS');

CREATE INDEX IF NOT EXISTS idx_categories_workflow_status
    ON categories(workflow_status);


-- ==========================================
-- Migration: 031_voucher_wallet_and_rollbacks.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS user_vouchers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voucher_id UUID NOT NULL REFERENCES vouchers(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'RESERVED', 'USED', 'EXPIRED', 'REVOKED')),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_vouchers_user_voucher_open
    ON user_vouchers(user_id, voucher_id)
    WHERE status IN ('AVAILABLE', 'RESERVED', 'USED');

CREATE INDEX IF NOT EXISTS idx_user_vouchers_user_status
    ON user_vouchers(user_id, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_user_vouchers_voucher_status
    ON user_vouchers(voucher_id, status);

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS voucher_claim_id UUID REFERENCES user_vouchers(id) ON DELETE SET NULL;


-- ==========================================
-- Migration: 032_order_management_upgrade.sql
-- ==========================================

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS assigned_staff_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS internal_note TEXT,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT,
    ADD COLUMN IF NOT EXISTS shipping_provider VARCHAR(120),
    ADD COLUMN IF NOT EXISTS tracking_code VARCHAR(120),
    ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_orders_tracking_code ON orders(tracking_code);
CREATE INDEX IF NOT EXISTS idx_orders_assigned_staff_name ON orders(assigned_staff_name);


-- ==========================================
-- Migration: 033_order_resilience_and_history.sql
-- ==========================================

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(120);

ALTER TABLE orders
    DROP CONSTRAINT IF EXISTS orders_status_check;

ALTER TABLE orders
    ADD CONSTRAINT orders_status_check
    CHECK (
        status IN (
            'PENDING',
            'CONFIRMED',
            'PAID',
            'PROCESSING',
            'SHIPPED',
            'COMPLETED',
            'CANCELLED',
            'REFUNDED',
            'PAYMENT_FAILED'
        )
    );

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key
    ON orders(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS order_history_logs (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status VARCHAR(40),
    new_status VARCHAR(40) NOT NULL,
    changed_by VARCHAR(255),
    note TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_history_logs_order_id
    ON order_history_logs(order_id, created_at DESC);


-- ==========================================
-- Migration: 034_order_reverse_logistics.sql
-- ==========================================

ALTER TABLE orders
    DROP CONSTRAINT IF EXISTS orders_status_check;

ALTER TABLE orders
    ADD CONSTRAINT orders_status_check
    CHECK (
        status IN (
            'PENDING',
            'CONFIRMED',
            'PAID',
            'PROCESSING',
            'SHIPPED',
            'COMPLETED',
            'CANCELLED',
            'REFUNDED',
            'PAYMENT_FAILED',
            'RETURNING',
            'RETURNED'
        )
    );


-- ==========================================
-- Migration: 035_customer_management_extension.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS customer_tags (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_customer_tags_user_id ON customer_tags(user_id);

CREATE TABLE IF NOT EXISTS customer_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_notes_user_id_created_at
    ON customer_notes(user_id, created_at DESC);

INSERT INTO permissions (code, module, description)
VALUES
    ('customer:update', 'customer', 'Cập nhật tag và ghi chú khách hàng'),
    ('customer:loyalty_adjust', 'customer', 'Cộng hoặc trừ điểm thưởng thủ công'),
    ('customer:issue_voucher', 'customer', 'Gửi voucher riêng cho khách hàng')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
    'customer:update',
    'customer:loyalty_adjust',
    'customer:issue_voucher'
)
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;


-- ==========================================
-- Migration: 036_inventory_settings_and_receipt_metadata.sql
-- ==========================================

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(160);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(14, 2);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_code VARCHAR(60);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_name VARCHAR(160);

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS sales_config JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE products
SET sales_config = jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(COALESCE(sales_config, '{}'::jsonb), '{minimumStock}', COALESCE(sales_config->'minimumStock', '0'::jsonb), true),
                    '{blockSaleWhenOutOfStock}',
                    COALESCE(sales_config->'blockSaleWhenOutOfStock', 'true'::jsonb),
                    true
                ),
                '{preferredLocationCode}',
                COALESCE(sales_config->'preferredLocationCode', '""'::jsonb),
                true
            ),
            '{preferredLocationName}',
            COALESCE(sales_config->'preferredLocationName', '""'::jsonb),
            true
        ),
        '{cycleCountDays}',
        COALESCE(sales_config->'cycleCountDays', '30'::jsonb),
        true
    )
WHERE sales_config IS NULL
   OR NOT (sales_config ? 'minimumStock')
   OR NOT (sales_config ? 'blockSaleWhenOutOfStock')
   OR NOT (sales_config ? 'preferredLocationCode')
   OR NOT (sales_config ? 'preferredLocationName')
   OR NOT (sales_config ? 'cycleCountDays');


-- ==========================================
-- Migration: 037_inventory_enterprise_foundation.sql
-- ==========================================

CREATE TABLE IF NOT EXISTS inventory_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    location_type VARCHAR(30) NOT NULL DEFAULT 'WAREHOUSE'
        CHECK (location_type IN ('WAREHOUSE', 'BRANCH', 'VIRTUAL', 'RETURNS')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    address TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO inventory_locations (code, name, location_type, status, is_default)
VALUES ('MAIN', 'Kho mac dinh', 'WAREHOUSE', 'ACTIVE', TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    location_type = EXCLUDED.location_type,
    status = EXCLUDED.status;

CREATE TABLE IF NOT EXISTS inventory_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    on_hand_quantity INTEGER NOT NULL DEFAULT 0 CHECK (on_hand_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    safety_stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (safety_stock_quantity >= 0),
    reorder_point_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reorder_point_quantity >= 0),
    average_unit_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (average_unit_cost >= 0),
    last_counted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_levels_item_check CHECK (num_nonnulls(product_id, variant_id) = 1),
    CONSTRAINT inventory_levels_reserved_le_on_hand CHECK (reserved_quantity <= on_hand_quantity)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_location
    ON inventory_levels(product_id, location_id)
    WHERE variant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_variant_location
    ON inventory_levels(variant_id, location_id)
    WHERE product_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_levels_location_id
    ON inventory_levels(location_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_variant_location
    ON inventory_levels(product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id);

CREATE TABLE IF NOT EXISTS inventory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(80) NOT NULL UNIQUE,
    document_type VARCHAR(30) NOT NULL
        CHECK (document_type IN ('INBOUND', 'OUTBOUND', 'ADJUSTMENT', 'COUNT', 'REVERSAL', 'TRANSFER', 'RESERVATION_RELEASE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'POSTED', 'CANCELLED', 'COMPLETED', 'PROCESSING_IMEI', 'PENDING_SHORTAGE_APPROVAL', 'RECEIVING', 'REVERSED')),
    source_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    target_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    supplier_name VARCHAR(160),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    posted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reversed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reversal_of_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    reversed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_status_type
    ON inventory_documents(status, document_type, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_document_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES inventory_documents(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    requested_quantity INTEGER NOT NULL DEFAULT 0 CHECK (requested_quantity >= 0),
    approved_quantity INTEGER CHECK (approved_quantity IS NULL OR approved_quantity >= 0),
    expected_quantity INTEGER CHECK (expected_quantity IS NULL OR expected_quantity >= 0),
    counted_quantity INTEGER CHECK (counted_quantity IS NULL OR counted_quantity >= 0),
    variance_quantity INTEGER,
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    note TEXT,
    CONSTRAINT inventory_document_lines_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_document_lines_document_id
    ON inventory_document_lines(document_id);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    movement_type VARCHAR(30) NOT NULL
        CHECK (movement_type IN ('IN', 'OUT', 'ADJUST', 'COUNT_POST', 'REVERSAL', 'RESERVE', 'RELEASE')),
    quantity INTEGER NOT NULL CHECK (quantity <> 0),
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    total_cost NUMERIC(14, 2) CHECK (total_cost IS NULL OR total_cost >= 0),
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    balance_after INTEGER CHECK (balance_after IS NULL OR balance_after >= 0),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_transactions_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item_location_created_at
    ON inventory_transactions(variant_id, product_id, location_id, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    reservation_code VARCHAR(120) NOT NULL UNIQUE,
    reserved_quantity INTEGER NOT NULL CHECK (reserved_quantity > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'CONSUMED', 'RELEASED', 'EXPIRED', 'CANCELLED')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    CONSTRAINT inventory_reservations_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_reservations_status_expires_at
    ON inventory_reservations(status, expires_at);

INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    p.id,
    NULL,
    il.id,
    p.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM products p
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    NULL,
    pv.id,
    il.id,
    pv.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM product_variants pv
JOIN products p ON p.id = pv.product_id
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (code, module, description)
VALUES
    ('inventory:approve', 'inventory', 'Duyet phieu nghiep vu kho'),
    ('inventory:count', 'inventory', 'Tao va doi soat phieu kiem ke kho'),
    ('inventory:reserve', 'inventory', 'Quan ly giu cho ton kho')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('inventory:approve', 'inventory:count', 'inventory:reserve')
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;

-- Staff Admin is only an internal staff account type.
-- Business permissions are granted per staff account through user_permissions.
DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'STAFF_ADMIN');


-- ============================================================================
-- Consolidated legacy migration: 036_inventory_settings_and_receipt_metadata.sql
-- ============================================================================
-- Inventory settings and richer receipt metadata
-- This migration extends the existing single-warehouse flow without replacing it.

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(160);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(14, 2);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_code VARCHAR(60);

ALTER TABLE inventory_adjustment_logs
    ADD COLUMN IF NOT EXISTS location_name VARCHAR(160);

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS sales_config JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE products
SET sales_config = jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(COALESCE(sales_config, '{}'::jsonb), '{minimumStock}', COALESCE(sales_config->'minimumStock', '0'::jsonb), true),
                    '{blockSaleWhenOutOfStock}',
                    COALESCE(sales_config->'blockSaleWhenOutOfStock', 'true'::jsonb),
                    true
                ),
                '{preferredLocationCode}',
                COALESCE(sales_config->'preferredLocationCode', '""'::jsonb),
                true
            ),
            '{preferredLocationName}',
            COALESCE(sales_config->'preferredLocationName', '""'::jsonb),
            true
        ),
        '{cycleCountDays}',
        COALESCE(sales_config->'cycleCountDays', '30'::jsonb),
        true
    )
WHERE sales_config IS NULL
   OR NOT (sales_config ? 'minimumStock')
   OR NOT (sales_config ? 'blockSaleWhenOutOfStock')
   OR NOT (sales_config ? 'preferredLocationCode')
   OR NOT (sales_config ? 'preferredLocationName')
   OR NOT (sales_config ? 'cycleCountDays');


-- ============================================================================
-- Consolidated legacy migration: 037_inventory_enterprise_foundation.sql
-- ============================================================================
-- Enterprise inventory foundation
-- This migration is intentionally non-breaking: it introduces normalized tables
-- for future multi-warehouse and approval workflows without removing the current
-- single-stock-column runtime yet.

CREATE TABLE IF NOT EXISTS inventory_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    location_type VARCHAR(30) NOT NULL DEFAULT 'WAREHOUSE'
        CHECK (location_type IN ('WAREHOUSE', 'BRANCH', 'VIRTUAL', 'RETURNS')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    address TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO inventory_locations (code, name, location_type, status, is_default)
VALUES ('MAIN', 'Kho mac dinh', 'WAREHOUSE', 'ACTIVE', TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    location_type = EXCLUDED.location_type,
    status = EXCLUDED.status;

CREATE TABLE IF NOT EXISTS inventory_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    on_hand_quantity INTEGER NOT NULL DEFAULT 0 CHECK (on_hand_quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    safety_stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (safety_stock_quantity >= 0),
    reorder_point_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reorder_point_quantity >= 0),
    average_unit_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (average_unit_cost >= 0),
    last_counted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_levels_item_check CHECK (num_nonnulls(product_id, variant_id) = 1),
    CONSTRAINT inventory_levels_reserved_le_on_hand CHECK (reserved_quantity <= on_hand_quantity)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_location
    ON inventory_levels(product_id, location_id)
    WHERE variant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_variant_location
    ON inventory_levels(variant_id, location_id)
    WHERE product_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_levels_location_id
    ON inventory_levels(location_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_variant_location
    ON inventory_levels(product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id);

CREATE TABLE IF NOT EXISTS inventory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(80) NOT NULL UNIQUE,
    document_type VARCHAR(30) NOT NULL
        CHECK (document_type IN ('INBOUND', 'OUTBOUND', 'ADJUSTMENT', 'COUNT', 'REVERSAL', 'TRANSFER', 'RESERVATION_RELEASE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'POSTED', 'CANCELLED', 'COMPLETED', 'PROCESSING_IMEI', 'PENDING_SHORTAGE_APPROVAL', 'RECEIVING', 'REVERSED')),
    source_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    target_location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    supplier_name VARCHAR(160),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    posted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reversed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reversal_of_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    reversed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_status_type
    ON inventory_documents(status, document_type, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_document_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES inventory_documents(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    requested_quantity INTEGER NOT NULL DEFAULT 0 CHECK (requested_quantity >= 0),
    approved_quantity INTEGER CHECK (approved_quantity IS NULL OR approved_quantity >= 0),
    expected_quantity INTEGER CHECK (expected_quantity IS NULL OR expected_quantity >= 0),
    counted_quantity INTEGER CHECK (counted_quantity IS NULL OR counted_quantity >= 0),
    variance_quantity INTEGER,
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    note TEXT,
    CONSTRAINT inventory_document_lines_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_document_lines_document_id
    ON inventory_document_lines(document_id);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    movement_type VARCHAR(30) NOT NULL
        CHECK (movement_type IN ('IN', 'OUT', 'ADJUST', 'COUNT_POST', 'REVERSAL', 'RESERVE', 'RELEASE')),
    quantity INTEGER NOT NULL CHECK (quantity <> 0),
    unit_cost NUMERIC(14, 2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    total_cost NUMERIC(14, 2) CHECK (total_cost IS NULL OR total_cost >= 0),
    costing_method VARCHAR(30) NOT NULL DEFAULT 'MOVING_AVERAGE'
        CHECK (costing_method IN ('MOVING_AVERAGE', 'FIFO', 'MANUAL')),
    balance_after INTEGER CHECK (balance_after IS NULL OR balance_after >= 0),
    reference_code VARCHAR(120),
    reason VARCHAR(120),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT inventory_transactions_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item_location_created_at
    ON inventory_transactions(variant_id, product_id, location_id, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    reservation_code VARCHAR(120) NOT NULL UNIQUE,
    reserved_quantity INTEGER NOT NULL CHECK (reserved_quantity > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'CONSUMED', 'RELEASED', 'EXPIRED', 'CANCELLED')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    CONSTRAINT inventory_reservations_item_check CHECK (num_nonnulls(product_id, variant_id) = 1)
);

CREATE INDEX IF NOT EXISTS idx_inventory_reservations_status_expires_at
    ON inventory_reservations(status, expires_at);

-- Backfill current single-warehouse balances into MAIN for compatibility mode.
INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    p.id,
    NULL,
    il.id,
    p.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM products p
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO inventory_levels (
    product_id,
    variant_id,
    location_id,
    on_hand_quantity,
    reserved_quantity,
    safety_stock_quantity,
    reorder_point_quantity,
    average_unit_cost,
    updated_at
)
SELECT
    NULL,
    pv.id,
    il.id,
    pv.stock_quantity,
    0,
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    COALESCE((p.sales_config->>'minimumStock')::INTEGER, 0),
    0,
    NOW()
FROM product_variants pv
JOIN products p ON p.id = pv.product_id
CROSS JOIN inventory_locations il
WHERE il.code = 'MAIN'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (code, module, description)
VALUES
    ('inventory:approve', 'inventory', 'Duyet phieu nghiep vu kho'),
    ('inventory:count', 'inventory', 'Tao va doi soat phieu kiem ke kho'),
    ('inventory:reserve', 'inventory', 'Quan ly giu cho ton kho')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('inventory:approve', 'inventory:count', 'inventory:reserve')
WHERE r.code IN ('SUPER_ADMIN', 'STAFF_ADMIN')
ON CONFLICT DO NOTHING;


-- ============================================================================
-- Consolidated legacy migration: 038_review_management_upgrade.sql
-- ============================================================================
-- Review management upgrade
-- Adds moderation, media attachments, shop replies, reporting, and anti-spam support.

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS media_urls JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS moderation_note TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_reply TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_replied_by UUID REFERENCES users(id);

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS shop_replied_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS flagged_reason TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS is_spam BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS spam_reason TEXT;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE product_reviews
SET status = 'PENDING'
WHERE status IS NULL;

ALTER TABLE product_reviews
    DROP CONSTRAINT IF EXISTS product_reviews_status_check;

ALTER TABLE product_reviews
    ADD CONSTRAINT product_reviews_status_check
    CHECK (status IN ('PENDING', 'PUBLISHED', 'HIDDEN', 'REJECTED'));

CREATE INDEX IF NOT EXISTS idx_product_reviews_status ON product_reviews(status);
CREATE INDEX IF NOT EXISTS idx_product_reviews_product_status ON product_reviews(product_id, status);


-- ============================================================================
-- Consolidated legacy migration: 039_review_resilience_and_user_controls.sql
-- ============================================================================
-- Review resilience and user controls
-- Adds ownership-friendly edit/delete support, review time window metadata, and denormalized rating sync.

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS order_id UUID REFERENCES orders(id);

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS review_window_expires_at TIMESTAMPTZ;

ALTER TABLE product_reviews
    ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_product_reviews_user_product ON product_reviews(user_id, product_id);

UPDATE products p
SET
    rating = stats.rating,
    review_count = stats.review_count,
    updated_at = NOW()
FROM (
    SELECT
        product_id,
        ROUND(AVG(rating) FILTER (WHERE status = 'PUBLISHED'), 2)::numeric(3, 2) AS rating,
        COUNT(*) FILTER (WHERE status = 'PUBLISHED') AS review_count
    FROM product_reviews
    GROUP BY product_id
) stats
WHERE p.id = stats.product_id;


-- ============================================================================
-- Consolidated legacy migration: 040_catalog_inventory_services_foundation.sql
-- ============================================================================
-- Catalog inventory, warranty, IMEI, and attached service foundation.
-- The admin UI writes these fields as optional configuration first so existing products keep working.

ALTER TABLE categories
    ADD COLUMN IF NOT EXISTS inventory_policy JSONB NOT NULL DEFAULT '{"inheritImeiPolicy": true, "trackImei": false}'::jsonb;

ALTER TABLE categories
    ADD COLUMN IF NOT EXISTS warranty_policy JSONB NOT NULL DEFAULT '{"inheritWarrantyPolicy": true, "hasWarranty": false, "warrantyMonths": 0, "allowOneForOne": false, "oneForOneDays": 0}'::jsonb;

CREATE TABLE IF NOT EXISTS product_imeis (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    imei VARCHAR(80) NOT NULL UNIQUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_STOCK',
    source_reference VARCHAR(120),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sold_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    sold_at TIMESTAMPTZ,
    service_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT product_imeis_status_check CHECK (status IN ('IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'RETIRED'))
);

CREATE INDEX IF NOT EXISTS idx_product_imeis_product_variant
    ON product_imeis(product_id, variant_id, status);

CREATE TABLE IF NOT EXISTS attached_services (
    id UUID PRIMARY KEY,
    code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(180) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    attribute_group VARCHAR(80),
    duration_months INTEGER NOT NULL DEFAULT 0,
    price_mode VARCHAR(30) NOT NULL DEFAULT 'FIXED',
    fixed_price NUMERIC(14, 2) NOT NULL DEFAULT 0,
    percent_value NUMERIC(7, 4) NOT NULL DEFAULT 0,
    base_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT attached_services_type_check CHECK (service_type IN ('PRODUCT_SERVICE', 'SUPPORT_SERVICE')),
    CONSTRAINT attached_services_price_mode_check CHECK (price_mode IN ('FIXED', 'PERCENT', 'TIERED_AMOUNT'))
);

CREATE TABLE IF NOT EXISTS product_attached_services (
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES attached_services(id) ON DELETE CASCADE,
    override_price NUMERIC(14, 2),
    PRIMARY KEY (product_id, service_id)
);


-- ============================================================================
-- Consolidated legacy migration: 041_product_favorites.sql
-- ============================================================================
BEGIN;

ALTER TABLE products 
ADD COLUMN favorite_count INT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS user_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, product_id)
);

-- Index for quick lookup
CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX idx_user_favorites_product_id ON user_favorites(product_id);

COMMIT;


-- ============================================================================
-- Consolidated legacy migration: 042_staff_user_permissions.sql
-- ============================================================================
-- Staff Admin is only an internal staff account type.
-- Super Admin grants business permissions to each staff account through user_permissions.

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);

DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'STAFF_ADMIN');

-- Do not seed shared STAFF_ADMIN permissions here.
-- Every staff account starts without business permissions until Super Admin grants them individually.


-- ============================================================================
-- Consolidated legacy migration: 043_video_management_split.sql
-- ============================================================================
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_source VARCHAR(30) NOT NULL DEFAULT 'UPLOAD';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS video_category VARCHAR(60) NOT NULL DEFAULT 'PRODUCT';

ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS reply_to_user_name VARCHAR(120);
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS moderation_reason VARCHAR(255);
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS is_retracted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE content_comments ADD COLUMN IF NOT EXISTS retracted_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS video_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(video_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_video_likes_video_id ON video_likes(video_id);
CREATE INDEX IF NOT EXISTS idx_video_likes_user_id ON video_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_video_category ON videos(video_category);


-- ============================================================================
-- Consolidated legacy migration: 044_product_image_comments.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_image_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_name VARCHAR(120) NOT NULL,
    body TEXT NOT NULL,
    parent_id UUID REFERENCES product_image_comments(id) ON DELETE CASCADE,
    reply_to_user_name VARCHAR(120),
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    is_retracted BOOLEAN NOT NULL DEFAULT FALSE,
    moderation_reason VARCHAR(255),
    interaction_type VARCHAR(30) NOT NULL DEFAULT 'IMAGE_COMMENT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE product_image_comments
ADD COLUMN IF NOT EXISTS interaction_type VARCHAR(30) NOT NULL DEFAULT 'IMAGE_COMMENT';

CREATE INDEX IF NOT EXISTS idx_product_image_comments_product_id ON product_image_comments(product_id);
CREATE INDEX IF NOT EXISTS idx_product_image_comments_parent_id ON product_image_comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_product_image_comments_type ON product_image_comments(interaction_type);


-- ============================================================================
-- Consolidated legacy migration: 045_product_analytics_events.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_view_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    session_id VARCHAR(120),
    device_id VARCHAR(160),
    ip_address VARCHAR(80),
    user_agent TEXT,
    source VARCHAR(80),
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    scroll_depth NUMERIC(4, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE product_view_events
    ADD COLUMN IF NOT EXISTS device_id VARCHAR(160),
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS scroll_depth NUMERIC(4, 3) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS product_search_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    normalized_query TEXT NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    session_id VARCHAR(120),
    ip_address VARCHAR(80),
    user_agent TEXT,
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_view_events_product_created
    ON product_view_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_search_events_product_created
    ON product_search_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_search_events_created
    ON product_search_events(created_at DESC);


-- ============================================================================
-- Consolidated legacy migration: 046_product_flat_variants.sql
-- ============================================================================
-- ==========================================
-- Migration: 046_product_flat_variants.sql
-- ==========================================

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    -- Drop unique constraint on products(sku) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'products'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'products'::regclass AND attname = 'sku')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE products DROP CONSTRAINT %I', constraint_name);
    END IF;
    
    -- Drop unique constraint on products(slug) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'products'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'products'::regclass AND attname = 'slug')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE products DROP CONSTRAINT %I', constraint_name);
    END IF;

    -- Drop unique constraint on product_variants(sku) if exists
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'product_variants'::regclass 
      AND contype = 'u' 
      AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'product_variants'::regclass AND attname = 'sku')];
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE product_variants DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE products ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE products ALTER COLUMN sku DROP NOT NULL;

ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS compare_at_price NUMERIC(14, 2) DEFAULT NULL;
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'active';
ALTER TABLE product_variants ADD COLUMN IF NOT EXISTS attributes JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_variant_sku
ON product_variants (sku)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_product_sku
ON products (sku)
WHERE deleted_at IS NULL AND sku IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_product_slug
ON products (slug)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_default_variant_per_product
ON product_variants (product_id)
WHERE is_default = true AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_active_variant_attributes
ON product_variants USING GIN (attributes)
WHERE deleted_at IS NULL;


-- ============================================================================
-- Consolidated legacy migration: 047_enterprise_product_revision_merge.sql
-- ============================================================================
-- ==========================================
-- Migration: 047_enterprise_product_revision_merge.sql
-- Purpose:
-- - Preserve variant lineage through product revisions.
-- - Preserve order item variant references for audit/inventory-safe merge.
-- ==========================================

ALTER TABLE product_variants
ADD COLUMN IF NOT EXISTS parent_variant_id UUID NULL REFERENCES product_variants(id);

ALTER TABLE order_items
ADD COLUMN IF NOT EXISTS variant_id UUID NULL REFERENCES product_variants(id);

CREATE INDEX IF NOT EXISTS idx_product_variants_parent_variant_id
ON product_variants (parent_variant_id)
WHERE parent_variant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_order_items_variant_id
ON order_items (variant_id)
WHERE variant_id IS NOT NULL;



-- ============================================================================
-- Consolidated legacy migration: 048_exclude_revision_variants_from_unique_sku.sql
-- ============================================================================
-- ==========================================
-- Migration: 048_exclude_revision_variants_from_unique_sku.sql
-- Purpose:
-- - Exclude revision draft variants from the unique SKU constraint.
-- ==========================================

DROP INDEX IF EXISTS idx_unique_active_variant_sku;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_variant_sku
ON product_variants (sku)
WHERE deleted_at IS NULL AND status <> 'revision_draft';


-- ============================================================================
-- Consolidated legacy migration: 049_product_variant_images.sql
-- ============================================================================
-- Add gallery images for each product variant, separate from the representative image.
ALTER TABLE product_variants
ADD COLUMN IF NOT EXISTS images JSONB NOT NULL DEFAULT '[]'::jsonb;


-- ============================================================================
-- Consolidated legacy migration: 050_product_favorite_events.sql
-- ============================================================================
BEGIN;

ALTER TABLE user_favorites
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE user_favorites
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS user_favorite_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL CHECK (action IN ('LIKE', 'UNLIKE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO user_favorite_events (user_id, product_id, action, created_at)
SELECT uf.user_id, uf.product_id, 'LIKE', uf.created_at
FROM user_favorites uf
WHERE NOT EXISTS (
    SELECT 1
    FROM user_favorite_events ufe
    WHERE ufe.user_id = uf.user_id
      AND ufe.product_id = uf.product_id
      AND ufe.action = 'LIKE'
      AND ufe.created_at = uf.created_at
);

CREATE INDEX IF NOT EXISTS idx_user_favorite_events_product_time
ON user_favorite_events(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_favorite_events_user_product_time
ON user_favorite_events(user_id, product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_favorites_active_product
ON user_favorites(product_id)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_user_favorites_active_user
ON user_favorites(user_id)
WHERE is_active = TRUE;

COMMIT;


-- ============================================================================
-- Consolidated legacy migration: 051_flash_sales.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS flash_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('FIXED', 'PERCENT')),
    discount_value NUMERIC(14, 2) NOT NULL CHECK (discount_value > 0),
    starts_at TIMESTAMPTZ NULL,
    ends_at TIMESTAMPTZ NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_flash_sales_product_active
    ON flash_sales(product_id, status, starts_at, ends_at);

CREATE INDEX IF NOT EXISTS idx_flash_sales_active_window
    ON flash_sales(status, starts_at, ends_at);


-- ============================================================================
-- Consolidated legacy migration: 052_remove_category_seo_metadata.sql
-- ============================================================================
-- Remove unused SEO metadata fields from categories.
-- Category management no longer exposes or persists these fields.

ALTER TABLE categories DROP COLUMN IF EXISTS seo_title;
ALTER TABLE categories DROP COLUMN IF EXISTS seo_description;
ALTER TABLE categories DROP COLUMN IF EXISTS seo_keywords;


-- ============================================================================
-- Consolidated legacy migration: 053_remove_brand_seo_metadata.sql
-- ============================================================================
-- Remove unused SEO metadata fields from brands.
-- Brand management keeps landing title only.

ALTER TABLE brands DROP COLUMN IF EXISTS seo_title;
ALTER TABLE brands DROP COLUMN IF EXISTS seo_description;


-- ============================================================================
-- Consolidated legacy migration: 054_product_discontinued_status.sql
-- ============================================================================
ALTER TABLE products
    DROP CONSTRAINT IF EXISTS products_status_check;

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('DRAFT', 'REVISION_DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'DISCONTINUED', 'ARCHIVED', 'MERGED'));


-- ============================================================================
-- Consolidated legacy migration: 055_product_inherited_visibility.sql
-- ============================================================================
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS hidden_by_category BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS hidden_by_brand BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_products_inherited_visibility
    ON products(hidden_by_category, hidden_by_brand, status);


-- ============================================================================
-- Consolidated legacy migration: 056_suppliers.sql
-- ============================================================================
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


-- ============================================================================
-- Consolidated legacy migration: 057_inventory_receipt_lifecycle.sql
-- ============================================================================
-- Receipt lifecycle for admin inbound inventory documents.

ALTER TABLE inventory_documents
DROP CONSTRAINT IF EXISTS inventory_documents_status_check;

ALTER TABLE inventory_documents
ADD CONSTRAINT inventory_documents_status_check
CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'RECEIVING', 'COMPLETED', 'CANCELLED', 'REJECTED', 'POSTED'));

ALTER TABLE inventory_document_lines
DROP CONSTRAINT IF EXISTS inventory_document_lines_item_check;

ALTER TABLE inventory_document_lines
ADD CONSTRAINT inventory_document_lines_item_check
CHECK (product_id IS NOT NULL OR variant_id IS NOT NULL);

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_inventory_documents_inbound_status_created
    ON inventory_documents(document_type, status, created_at DESC)
    WHERE document_type = 'INBOUND';


-- ============================================================================
-- Consolidated legacy migration: 058_inventory_receipt_imei_workflow.sql
-- ============================================================================
-- Separate IMEI collection from receipt creation.

ALTER TABLE inventory_documents
DROP CONSTRAINT IF EXISTS inventory_documents_status_check;

ALTER TABLE inventory_documents
ADD CONSTRAINT inventory_documents_status_check
CHECK (status IN (
    'DRAFT',
    'PROCESSING_IMEI',
    'PENDING_SHORTAGE_APPROVAL',
    'APPROVED',
    'COMPLETED',
    'CANCELLED',
    'REJECTED',
    'POSTED',
    'PENDING_APPROVAL',
    'RECEIVING'
));

ALTER TABLE inventory_document_lines
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE inventory_document_lines
SET metadata = metadata
    || jsonb_build_object(
        'plannedQuantity', requested_quantity,
        'receivedQuantity', COALESCE((metadata->>'receivedQuantity')::int, 0),
        'tracksImei', COALESCE((metadata->>'tracksImei')::boolean, FALSE)
    )
WHERE document_id IN (
    SELECT id FROM inventory_documents WHERE document_type = 'INBOUND'
);


-- ============================================================================
-- Consolidated legacy migration: 059_inventory_imei_enterprise_statuses.sql
-- ============================================================================
-- Align IMEI lifecycle statuses with the WMS/ERP inventory model.
ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check
    CHECK (status IN (
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'IN_WARRANTY',
        'SCRAP',
        'RETURNED',
        'WARRANTY',
        'RETIRED'
    ));



-- ============================================================================
-- Consolidated legacy migration: 060_product_serial_number_management.sql
-- ============================================================================
-- Add serial number tracking parallel to IMEI tracking.

UPDATE categories
SET inventory_policy = COALESCE(inventory_policy, '{}'::jsonb)
    || jsonb_build_object(
        'inheritSerialPolicy', COALESCE((inventory_policy->>'inheritSerialPolicy')::boolean, TRUE),
        'trackSerialNumber', COALESCE((inventory_policy->>'trackSerialNumber')::boolean, FALSE)
    )
WHERE NOT (COALESCE(inventory_policy, '{}'::jsonb) ? 'trackSerialNumber');

CREATE TABLE IF NOT EXISTS product_serial_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    serial_number VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_STOCK',
    source_reference VARCHAR(120),
    service_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ,
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT product_serial_numbers_status_check CHECK (
        status IN ('IN_STOCK', 'RESERVED', 'SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY', 'RETIRED', 'SCRAP')
    )
);

CREATE INDEX IF NOT EXISTS idx_product_serial_numbers_product_variant
    ON product_serial_numbers(product_id, variant_id, status);


-- ============================================================================
-- Consolidated legacy migration: 061_product_imei_primary.sql
-- ============================================================================
-- Allow each product or variant to keep many IMEI values while marking one as the primary IMEI.

ALTER TABLE product_imeis
    ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE;

WITH ranked_imeis AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id
            ORDER BY
                CASE WHEN is_primary THEN 0 ELSE 1 END,
                received_at NULLS LAST,
                created_at,
                id
        ) AS row_number
    FROM product_imeis
)
UPDATE product_imeis pi
SET is_primary = TRUE,
    updated_at = NOW()
FROM ranked_imeis ranked
WHERE ranked.id = pi.id
  AND ranked.row_number = 1
  AND pi.is_primary = FALSE
  AND NOT EXISTS (
      SELECT 1
      FROM product_imeis existing
      WHERE existing.product_id = pi.product_id
        AND (
            existing.variant_id = pi.variant_id
            OR (existing.variant_id IS NULL AND pi.variant_id IS NULL)
        )
        AND existing.is_primary = TRUE
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_imeis_primary_base
    ON product_imeis(product_id)
    WHERE is_primary = TRUE AND variant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_product_imeis_primary_variant
    ON product_imeis(product_id, variant_id)
    WHERE is_primary = TRUE AND variant_id IS NOT NULL;


-- ============================================================================
-- Consolidated legacy migration: 062_inventory_receipt_audit_actors.sql
-- ============================================================================
ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS posted_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_inventory_documents_created_by
    ON inventory_documents(created_by);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_approved_by
    ON inventory_documents(approved_by);

CREATE INDEX IF NOT EXISTS idx_inventory_documents_posted_by
    ON inventory_documents(posted_by);


-- ============================================================================
-- Consolidated legacy migration: 063_inventory_receipt_reversal.sql
-- ============================================================================
ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversed_by UUID REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMPTZ;

ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS reversal_of_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL;

ALTER TABLE inventory_documents
    DROP CONSTRAINT IF EXISTS inventory_documents_status_check;

ALTER TABLE inventory_documents
    ADD CONSTRAINT inventory_documents_status_check
    CHECK (status IN (
        'DRAFT',
        'PROCESSING_IMEI',
        'PENDING_SHORTAGE_APPROVAL',
        'APPROVED',
        'COMPLETED',
        'CANCELLED',
        'REVERSED',
        'REJECTED',
        'POSTED',
        'PENDING_APPROVAL',
        'RECEIVING'
    ));

ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check
    CHECK (status IN (
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'IN_WARRANTY',
        'SCRAP',
        'RETURNED',
        'REVERSED',
        'WARRANTY',
        'RETIRED'
    ));

ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;

ALTER TABLE product_serial_numbers
    ADD CONSTRAINT product_serial_numbers_status_check
    CHECK (status IN (
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'RETURNED',
        'REVERSED',
        'WARRANTY',
        'IN_WARRANTY',
        'RETIRED',
        'SCRAP'
    ));

CREATE INDEX IF NOT EXISTS idx_inventory_documents_reversal_of
    ON inventory_documents(reversal_of_document_id);


-- ============================================================================
-- Consolidated legacy migration: 064_inventory_levels_moving_average_cost.sql
-- ============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_variant_location
    ON inventory_levels(product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id);


-- ============================================================================
-- Consolidated legacy migration: 065_inventory_identifier_edit_requests.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventory_identifier_edit_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier_type VARCHAR(20) NOT NULL,
    identifier_id UUID NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    current_value VARCHAR(120) NOT NULL,
    new_value VARCHAR(120) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decided_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decision_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    CONSTRAINT inventory_identifier_edit_requests_type_check
        CHECK (identifier_type IN ('IMEI', 'SERIAL')),
    CONSTRAINT inventory_identifier_edit_requests_status_check
        CHECK (status IN ('PENDING', 'APPROVED', 'CANCELLED')),
    CONSTRAINT inventory_identifier_edit_requests_reason_check
        CHECK (length(trim(reason)) >= 5),
    CONSTRAINT inventory_identifier_edit_requests_changed_value_check
        CHECK (current_value <> new_value)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_identifier_edit_requests_pending
    ON inventory_identifier_edit_requests(identifier_type, identifier_id)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_inventory_identifier_edit_requests_product
    ON inventory_identifier_edit_requests(product_id, variant_id, status, created_at DESC);



-- ============================================================================
-- Consolidated legacy migration: 066_inventory_stock_count_workflow.sql
-- ============================================================================
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


-- ============================================================================
-- Consolidated legacy migration: 067_inventory_adjustment_approval_workflow.sql
-- ============================================================================
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


-- ============================================================================
-- Consolidated legacy migration: 068_product_serial_number_product_scope_unique.sql
-- ============================================================================
ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_serial_number_key;

DROP INDEX IF EXISTS idx_product_serial_numbers_product_serial_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_serial_numbers_product_serial_unique
    ON product_serial_numbers(product_id, serial_number);


-- ============================================================================
-- Consolidated legacy migration: 069_inventory_super_admin_approval_scope.sql
-- ============================================================================
DELETE FROM role_permissions rp
USING roles r, permissions p
WHERE rp.role_id = r.id
  AND rp.permission_id = p.id
  AND r.code = 'STAFF_ADMIN'
  AND p.code IN ('inventory:approve', 'inventory:reserve');

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('inventory:approve', 'inventory:count', 'inventory:reserve')
WHERE r.code = 'SUPER_ADMIN'
ON CONFLICT DO NOTHING;


-- ============================================================================
-- Consolidated legacy migration: 070_inventory_pending_inbound_identifiers.sql
-- ============================================================================
-- Reserve inbound IMEI/serial numbers while an inventory receipt is waiting for approval.

ALTER TABLE product_imeis
    DROP CONSTRAINT IF EXISTS product_imeis_status_check;

ALTER TABLE product_imeis
    ADD CONSTRAINT product_imeis_status_check
    CHECK (status IN (
        'PENDING_INBOUND',
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'IN_WARRANTY',
        'SCRAP',
        'RETURNED',
        'REVERSED',
        'WARRANTY',
        'RETIRED'
    ));

ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_status_check;

ALTER TABLE product_serial_numbers
    ADD CONSTRAINT product_serial_numbers_status_check
    CHECK (status IN (
        'PENDING_INBOUND',
        'IN_STOCK',
        'RESERVED',
        'SOLD',
        'RETURNED',
        'REVERSED',
        'WARRANTY',
        'IN_WARRANTY',
        'RETIRED',
        'SCRAP'
    ));

CREATE INDEX IF NOT EXISTS idx_product_imeis_pending_inbound_source
    ON product_imeis(source_reference, status)
    WHERE status = 'PENDING_INBOUND';

CREATE INDEX IF NOT EXISTS idx_product_serial_numbers_pending_inbound_source
    ON product_serial_numbers(source_reference, status)
    WHERE status = 'PENDING_INBOUND';


-- ============================================================================
-- Consolidated legacy migration: 071_inventory_receipt_wms_lightweight_metadata.sql
-- ============================================================================
ALTER TABLE inventory_documents
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_inventory_documents_metadata_quality_status
    ON inventory_documents ((metadata->>'qualityStatus'))
    WHERE document_type = 'INBOUND';

CREATE INDEX IF NOT EXISTS idx_inventory_document_lines_metadata_storage_location
    ON inventory_document_lines ((metadata->>'storageLocationCode'))
    WHERE metadata ? 'storageLocationCode';


-- ============================================================================
-- Consolidated legacy migration: 072_inventory_locations_master_data.sql
-- ============================================================================
-- Chuẩn hóa vị trí/kệ hàng thành danh mục quản lý được và gắn kệ cho IMEI/serial.

ALTER TABLE inventory_locations
    ADD COLUMN IF NOT EXISTS zone VARCHAR(160),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) NOT NULL DEFAULT 'STORAGE',
    ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS allow_mixed_sku BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS length_cm NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS width_cm NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS height_cm NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS usable_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0.75;

ALTER TABLE inventory_locations
    DROP CONSTRAINT IF EXISTS inventory_locations_purpose_check;

ALTER TABLE inventory_locations
    ADD CONSTRAINT inventory_locations_purpose_check
    CHECK (purpose IN ('STORAGE', 'WARRANTY', 'QC', 'DAMAGED', 'RETURN', 'VIRTUAL'));

UPDATE inventory_locations
SET name = 'Kho chính',
    zone = COALESCE(zone, 'Kho chính'),
    purpose = 'VIRTUAL',
    sort_order = 0,
    allow_mixed_sku = TRUE
WHERE code = 'MAIN';

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
VALUES
    ('A-01-01', 'Dãy A - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, ưu tiên gần khu lấy hàng', 'STORAGE', 10101, FALSE),
    ('A-01-02', 'Dãy A - Kệ 01 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10102, FALSE),
    ('A-01-03', 'Dãy A - Kệ 01 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10103, FALSE),
    ('A-01-04', 'Dãy A - Kệ 01 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, cùng kệ A-01', 'STORAGE', 10104, FALSE),
    ('A-02-01', 'Dãy A - Kệ 02 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-02', 'STORAGE', 10201, FALSE),
    ('A-02-02', 'Dãy A - Kệ 02 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-02', 'STORAGE', 10202, FALSE),
    ('A-02-03', 'Dãy A - Kệ 02 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-02', 'STORAGE', 10203, FALSE),
    ('A-02-04', 'Dãy A - Kệ 02 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-02', 'STORAGE', 10204, FALSE),
    ('A-03-01', 'Dãy A - Kệ 03 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-03', 'STORAGE', 10301, FALSE),
    ('A-03-02', 'Dãy A - Kệ 03 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-03', 'STORAGE', 10302, FALSE),
    ('A-03-03', 'Dãy A - Kệ 03 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-03', 'STORAGE', 10303, FALSE),
    ('A-03-04', 'Dãy A - Kệ 03 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-03', 'STORAGE', 10304, FALSE),
    ('A-04-01', 'Dãy A - Kệ 04 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-04', 'STORAGE', 10401, FALSE),
    ('A-04-02', 'Dãy A - Kệ 04 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-04', 'STORAGE', 10402, FALSE),
    ('A-04-03', 'Dãy A - Kệ 04 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-04', 'STORAGE', 10403, FALSE),
    ('A-04-04', 'Dãy A - Kệ 04 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-04', 'STORAGE', 10404, FALSE),
    ('A-05-01', 'Dãy A - Kệ 05 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-05', 'STORAGE', 10501, FALSE),
    ('A-05-02', 'Dãy A - Kệ 05 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-05', 'STORAGE', 10502, FALSE),
    ('A-05-03', 'Dãy A - Kệ 05 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-05', 'STORAGE', 10503, FALSE),
    ('A-05-04', 'Dãy A - Kệ 05 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-05', 'STORAGE', 10504, FALSE),
    ('A-06-01', 'Dãy A - Kệ 06 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-06', 'STORAGE', 10601, FALSE),
    ('A-06-02', 'Dãy A - Kệ 06 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-06', 'STORAGE', 10602, FALSE),
    ('A-06-03', 'Dãy A - Kệ 06 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-06', 'STORAGE', 10603, FALSE),
    ('A-06-04', 'Dãy A - Kệ 06 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-06', 'STORAGE', 10604, FALSE),
    ('A-07-01', 'Dãy A - Kệ 07 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-07', 'STORAGE', 10701, FALSE),
    ('A-07-02', 'Dãy A - Kệ 07 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-07', 'STORAGE', 10702, FALSE),
    ('A-07-03', 'Dãy A - Kệ 07 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-07', 'STORAGE', 10703, FALSE),
    ('A-07-04', 'Dãy A - Kệ 07 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-07', 'STORAGE', 10704, FALSE),
    ('A-08-01', 'Dãy A - Kệ 08 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-08', 'STORAGE', 10801, FALSE),
    ('A-08-02', 'Dãy A - Kệ 08 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-08', 'STORAGE', 10802, FALSE),
    ('A-08-03', 'Dãy A - Kệ 08 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-08', 'STORAGE', 10803, FALSE),
    ('A-08-04', 'Dãy A - Kệ 08 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-08', 'STORAGE', 10804, FALSE),
    ('A-09-01', 'Dãy A - Kệ 09 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-09', 'STORAGE', 10901, FALSE),
    ('A-09-02', 'Dãy A - Kệ 09 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-09', 'STORAGE', 10902, FALSE),
    ('A-09-03', 'Dãy A - Kệ 09 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-09', 'STORAGE', 10903, FALSE),
    ('A-09-04', 'Dãy A - Kệ 09 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-09', 'STORAGE', 10904, FALSE),
    ('A-10-01', 'Dãy A - Kệ 10 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-10', 'STORAGE', 11001, FALSE),
    ('A-10-02', 'Dãy A - Kệ 10 - Ô 02', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-10', 'STORAGE', 11002, FALSE),
    ('A-10-03', 'Dãy A - Kệ 10 - Ô 03', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-10', 'STORAGE', 11003, FALSE),
    ('A-10-04', 'Dãy A - Kệ 10 - Ô 04', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy A', 'Vị trí lưu hàng bán được, kệ A-10', 'STORAGE', 11004, FALSE),
    ('B-01-01', 'Dãy B - Kệ 01 - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Dãy B', 'Vị trí lưu hàng bán được ở dãy B', 'STORAGE', 20101, TRUE),
    ('QC-01', 'QC - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'QC', 'Vị trí cách ly hàng chờ kiểm tra hoặc chưa đạt QC', 'QC', 90001, TRUE),
    ('BH-01', 'Bảo hành - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Bảo hành', 'Vị trí lưu hàng gửi/nhận bảo hành', 'WARRANTY', 91001, TRUE),
    ('ERR-01', 'Hàng lỗi - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Hàng lỗi', 'Vị trí lưu hàng hư hỏng, phế phẩm hoặc chờ xử lý', 'DAMAGED', 92001, TRUE),
    ('RT-01', 'Hàng trả - Ô 01', 'WAREHOUSE', 'ACTIVE', FALSE, 'Hàng trả', 'Vị trí lưu hàng khách trả trước khi phân loại', 'RETURN', 93001, TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();

INSERT INTO inventory_locations (code, name, location_type, status, is_default, zone, description, purpose, sort_order, allow_mixed_sku)
SELECT
    format('B-%s-%s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS code,
    format('Dãy B - Kệ %s - Ô %s', lpad(shelf_no::text, 2, '0'), lpad(bin_no::text, 2, '0')) AS name,
    'WAREHOUSE',
    'ACTIVE',
    FALSE,
    'Dãy B',
    format('Vị trí lưu hàng bán được, kệ B-%s', lpad(shelf_no::text, 2, '0')) AS description,
    'STORAGE',
    20000 + shelf_no * 100 + bin_no AS sort_order,
    FALSE
FROM generate_series(1, 10) AS shelf_no
CROSS JOIN generate_series(1, 4) AS bin_no
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    status = 'ACTIVE',
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();

UPDATE inventory_locations
SET length_cm = COALESCE(length_cm, 100),
    width_cm = COALESCE(width_cm, 60),
    height_cm = COALESCE(height_cm, 40),
    updated_at = NOW()
WHERE status = 'ACTIVE'
  AND purpose = 'STORAGE'
  AND code ~ '^[AB]-[0-9]{2}-[0-9]{2}$';

UPDATE inventory_locations
SET purpose = CASE
        WHEN code LIKE 'BH-%' THEN 'WARRANTY'
        WHEN code LIKE 'QC-%' THEN 'QC'
        WHEN code LIKE 'ERR-%' THEN 'DAMAGED'
        WHEN code LIKE 'RT-%' THEN 'RETURN'
        WHEN code = 'MAIN' THEN 'VIRTUAL'
        ELSE COALESCE(NULLIF(purpose, ''), 'STORAGE')
    END,
    sort_order = CASE
        WHEN sort_order <> 0 THEN sort_order
        WHEN code ~ '^[A-Z]-[0-9]{2}-[0-9]{2}$'
            THEN ((ascii(substr(code, 1, 1)) - ascii('A') + 1) * 10000)
                + (substr(code, 3, 2)::int * 100)
                + substr(code, 6, 2)::int
        ELSE 99999
    END;

ALTER TABLE product_imeis
    ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT;

ALTER TABLE product_serial_numbers
    ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES inventory_locations(id) ON DELETE RESTRICT;

UPDATE product_imeis pi
SET location_id = line_locations.location_id
FROM (
    SELECT DISTINCT ON (identifier.metadata_imei)
        l.location_id,
        identifier.metadata_imei
    FROM inventory_document_lines l
    CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(l.metadata->'imeis', '[]'::jsonb)) AS identifier(metadata_imei)
    JOIN inventory_documents d ON d.id = l.document_id
    WHERE d.document_type = 'INBOUND'
      AND l.location_id IS NOT NULL
    ORDER BY identifier.metadata_imei, d.posted_at DESC NULLS LAST, d.created_at DESC
) AS line_locations
WHERE pi.imei = line_locations.metadata_imei
  AND pi.location_id IS NULL;

UPDATE product_serial_numbers psn
SET location_id = line_locations.location_id
FROM (
    SELECT DISTINCT ON (identifier.metadata_serial)
        l.location_id,
        identifier.metadata_serial,
        l.product_id
    FROM inventory_document_lines l
    CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(l.metadata->'serialNumbers', '[]'::jsonb)) AS identifier(metadata_serial)
    JOIN inventory_documents d ON d.id = l.document_id
    WHERE d.document_type = 'INBOUND'
      AND l.location_id IS NOT NULL
    ORDER BY identifier.metadata_serial, d.posted_at DESC NULLS LAST, d.created_at DESC
) AS line_locations
WHERE psn.product_id = line_locations.product_id
  AND psn.serial_number = line_locations.metadata_serial
  AND psn.location_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_product_imeis_location_status
    ON product_imeis(location_id, status);

CREATE INDEX IF NOT EXISTS idx_product_serial_numbers_location_status
    ON product_serial_numbers(location_id, status);


-- ============================================================================
-- Consolidated legacy migration: 073_staff_admin_per_account_permissions.sql
-- ============================================================================
-- Staff Admin is only an internal staff account type.
-- Business permissions must be granted per staff account through user_permissions.

DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'STAFF_ADMIN');

