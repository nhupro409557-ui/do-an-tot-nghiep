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
    ('DJI', ARRAY['cameras']),
    ('Ezviz', ARRAY['cameras']),
    ('Imou', ARRAY['cameras']),
    ('Vietmap', ARRAY['cameras']),
    ('70mai', ARRAY['cameras'])
),
upserted_brands AS (
    INSERT INTO brands (code, name)
    SELECT lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g')), name
    FROM brand_seed
    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, is_active = TRUE, updated_at = NOW()
    RETURNING id, code, name
)
INSERT INTO brand_categories (brand_id, category_id)
SELECT upserted_brands.id, categories.id
FROM brand_seed
JOIN upserted_brands ON upserted_brands.name = brand_seed.name
JOIN LATERAL unnest(brand_seed.category_codes) AS category_code ON TRUE
JOIN categories ON categories.code = category_code
ON CONFLICT DO NOTHING;

WITH product_seed(sku, slug, name, category_code, subcategory_code, brand_name, price, sale_price, stock_quantity, image_url, specifications, colors, capacities, is_featured, is_flash_sale, rating, review_count, badge) AS (
    VALUES
    ('IP16PM', 'iphone-16-pro-max', 'iPhone 16 Pro Max', 'smartphones', 'phone-flagship', 'Apple', 36990000, 33990000, 19, 'https://placehold.co/600x600/f8fafc/0f172a?text=iPhone+16+Pro+Max', '{"processor":"A18 Pro","ram":"8GB","screenSize":"6.9 inch","storage":"256GB","battery":"4685mAh"}'::jsonb, '[{"name":"Titan Sa mạc","code":"#c7a889"},{"name":"Titan đen","code":"#343434"}]'::jsonb, '["256GB","512GB","1TB"]'::jsonb, TRUE, TRUE, 4.9, 245, 'Hot'),
    ('S24U', 'galaxy-s24-ultra', 'Samsung Galaxy S24 Ultra', 'smartphones', 'phone-flagship', 'Samsung', 31990000, 25990000, 15, 'https://placehold.co/600x600/f8fafc/0f172a?text=Galaxy+S24+Ultra', '{"processor":"Snapdragon 8 Gen 3","ram":"12GB","screenSize":"6.8 inch","storage":"256GB","battery":"5000mAh"}'::jsonb, '[{"name":"Titanium Gray","code":"#9ca3af"},{"name":"Titanium Black","code":"#27272a"}]'::jsonb, '["256GB","512GB"]'::jsonb, TRUE, FALSE, 4.8, 197, 'Hot'),
    ('ZFOLD6', 'galaxy-z-fold6', 'Samsung Galaxy Z Fold6', 'smartphones', 'phone-foldable', 'Samsung', 44990000, 41990000, 8, 'https://placehold.co/600x600/f8fafc/0f172a?text=Galaxy+Z+Fold6', '{"processor":"Snapdragon 8 Gen 3","ram":"12GB","screenSize":"7.6 inch","storage":"256GB"}'::jsonb, '[]'::jsonb, '["256GB","512GB"]'::jsonb, TRUE, FALSE, 4.7, 118, 'Hot'),
    ('X14U', 'xiaomi-14-ultra', 'Xiaomi 14 Ultra', 'smartphones', 'phone-flagship', 'Xiaomi', 27990000, 24990000, 12, 'https://placehold.co/600x600/f8fafc/0f172a?text=Xiaomi+14+Ultra', '{"processor":"Snapdragon 8 Gen 3","ram":"16GB","screenSize":"6.73 inch","storage":"512GB","battery":"5000mAh"}'::jsonb, '[]'::jsonb, '["512GB"]'::jsonb, TRUE, FALSE, 4.7, 93, 'Hot'),
    ('OPPFN3', 'oppo-find-n3', 'OPPO Find N3', 'smartphones', 'phone-foldable', 'OPPO', 39990000, 34990000, 6, 'https://placehold.co/600x600/f8fafc/0f172a?text=OPPO+Find+N3', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.6, 78, 'Hot'),
    ('IPADM4', 'ipad-pro-m4', 'iPad Pro M4 11 inch', 'tablets', 'tablet-pro', 'Apple', 31990000, 28990000, 10, 'https://placehold.co/600x600/f8fafc/0f172a?text=iPad+Pro+M4', '{"processor":"Apple M4","screenSize":"11 inch OLED","storage":"256GB"}'::jsonb, '[{"name":"Bạc","code":"#d1d5db"},{"name":"Đen","code":"#111827"}]'::jsonb, '["256GB","512GB","1TB"]'::jsonb, TRUE, FALSE, 4.9, 156, 'Hot'),
    ('MBAIRM3', 'macbook-air-m3', 'MacBook Air M3 13 inch', 'laptops', 'macbook', 'Apple', 29990000, 27490000, 16, 'https://placehold.co/600x600/f8fafc/0f172a?text=MacBook+Air+M3', '{"processor":"Apple M3","ram":"8GB","screenSize":"13.6 inch","storage":"256GB SSD","weight":"1.24 kg"}'::jsonb, '[]'::jsonb, '["256GB","512GB"]'::jsonb, TRUE, TRUE, 4.8, 220, 'Hot'),
    ('ROGG14', 'asus-rog-zephyrus-g14', 'ASUS ROG Zephyrus G14', 'laptops', 'laptop-gaming', 'ASUS', 45990000, 41990000, 7, 'https://placehold.co/600x600/f8fafc/0f172a?text=ROG+Zephyrus+G14', '{"processor":"Ryzen 9","ram":"32GB","graphics":"RTX 4070","storage":"1TB SSD"}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.7, 89, 'Hot'),
    ('APP2USBC', 'airpods-pro-2-usbc', 'AirPods Pro 2 USB-C', 'accessories', 'audio-tws', 'Apple', 6790000, 5490000, 30, 'https://placehold.co/600x600/f8fafc/0f172a?text=AirPods+Pro+2', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, TRUE, 4.8, 534, 'Hot'),
    ('ANK100W', 'anker-prime-100w', 'Củ sạc Anker Prime GaN 100W', 'accessories', 'adapter-gan', 'Anker', 2490000, 1890000, 40, 'https://placehold.co/600x600/f8fafc/0f172a?text=Anker+Prime+100W', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.7, 142, 'Hot'),
    ('AWU2', 'apple-watch-ultra-2', 'Apple Watch Ultra 2', 'wearables', 'watch-sport', 'Apple', 21990000, 19990000, 11, 'https://placehold.co/600x600/f8fafc/0f172a?text=Apple+Watch+Ultra+2', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.8, 99, 'Hot'),
    ('GFENIX7P', 'garmin-fenix-7-pro', 'Garmin Fenix 7 Pro', 'wearables', 'watch-sport', 'Garmin', 21990000, 18990000, 8, 'https://placehold.co/600x600/f8fafc/0f172a?text=Garmin+Fenix+7+Pro', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.9, 76, 'Hot'),
    ('SONYA7IV', 'sony-a7-iv', 'Sony Alpha A7 IV', 'may-anh', 'camera-mirrorless', 'Sony', 57990000, 52990000, 5, 'https://placehold.co/600x600/f8fafc/0f172a?text=Sony+A7+IV', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.9, 48, 'Hot'),
    ('DJIPOCKET3', 'dji-pocket-3', 'DJI Pocket 3', 'cameras', 'action-camera', 'DJI', 14990000, 12990000, 14, 'https://placehold.co/600x600/f8fafc/0f172a?text=DJI+Pocket+3', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.8, 120, 'Hot'),
    ('EZC6N', 'ezviz-c6n', 'Ezviz C6N', 'cameras', 'security-camera', 'Ezviz', 890000, 690000, 55, 'https://placehold.co/600x600/f8fafc/0f172a?text=Ezviz+C6N', '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, TRUE, FALSE, 4.4, 180, NULL)
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
    status = EXCLUDED.status,
    updated_at = NOW();

WITH variant_seed(product_sku, sku, color_name, color_code, storage, ram, configuration, price, sale_price, stock_quantity) AS (
    VALUES
    ('IP16PM', 'IP16PM-256-DT', 'Titan Sa mạc', '#c7a889', '256GB', '8GB', NULL, 33990000, NULL, 12),
    ('IP16PM', 'IP16PM-512-BT', 'Titan đen', '#343434', '512GB', '8GB', NULL, 38990000, NULL, 7),
    ('S24U', 'S24U-256-GRAY', 'Titanium Gray', '#9ca3af', '256GB', '12GB', NULL, 25990000, NULL, 9),
    ('S24U', 'S24U-512-BLACK', 'Titanium Black', '#27272a', '512GB', '12GB', NULL, 29990000, NULL, 6),
    ('IPADM4', 'IPADM4-256-SILVER', 'Bạc', '#d1d5db', '256GB', NULL, 'Wi-Fi', 28990000, NULL, 6),
    ('IPADM4', 'IPADM4-512-BLACK', 'Đen', '#111827', '512GB', NULL, 'Wi-Fi', 34990000, NULL, 4),
    ('MBAIRM3', 'MBAIRM3-8-256', 'Midnight', '#111827', '256GB SSD', '8GB', '13 inch', 27490000, NULL, 10),
    ('MBAIRM3', 'MBAIRM3-16-512', 'Silver', '#d1d5db', '512GB SSD', '16GB', '13 inch', 34990000, NULL, 6)
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
FROM variant_seed
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
CREATE INDEX IF NOT EXISTS idx_videos_content_type ON videos(content_type);
CREATE INDEX IF NOT EXISTS idx_videos_sort_order ON videos(sort_order DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_scheduled_at ON videos(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_videos_deleted_at ON videos(deleted_at);
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

CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions(module);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);

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
    'product:create',
    'product:update',
    'category:read',
    'category:create',
    'category:update',
    'brand:read',
    'brand:create',
    'brand:update',
    'order:read',
    'order:update',
    'customer:read',
    'inventory:read',
    'inventory:adjust',
    'review:read',
    'review:update',
    'content:read',
    'content:create',
    'content:update'
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
ALTER TABLE brands ADD COLUMN IF NOT EXISTS seo_title VARCHAR(255);
ALTER TABLE brands ADD COLUMN IF NOT EXISTS seo_description TEXT;

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
    CHECK (status IN ('DRAFT', 'REVISION_DRAFT', 'PENDING', 'ACTIVE', 'INACTIVE', 'ARCHIVED'));

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
ALTER TABLE categories ADD COLUMN IF NOT EXISTS seo_title VARCHAR(255);
ALTER TABLE categories ADD COLUMN IF NOT EXISTS seo_description TEXT;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS seo_keywords TEXT;

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

CREATE TABLE IF NOT EXISTS inventory_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_no VARCHAR(80) NOT NULL UNIQUE,
    document_type VARCHAR(30) NOT NULL
        CHECK (document_type IN ('INBOUND', 'OUTBOUND', 'ADJUSTMENT', 'COUNT', 'REVERSAL', 'TRANSFER', 'RESERVATION_RELEASE')),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'POSTED', 'CANCELLED')),
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    posted_at TIMESTAMPTZ
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
