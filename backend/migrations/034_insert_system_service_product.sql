-- Migration: Insert virtual product for system-level services
INSERT INTO products (
    id, 
    name, 
    sku, 
    slug, 
    price, 
    sale_price, 
    stock_quantity, 
    status, 
    category, 
    brand, 
    description, 
    specifications, 
    image_url, 
    images, 
    options, 
    created_at, 
    updated_at
)
VALUES (
    'd0a0d752-5a18-4a8a-9e27-960431d635e8',
    'Dịch vụ đi kèm (Hệ thống)',
    'SYSTEM-SERVICE',
    'dich-vu-di-kem-he-thong',
    0,
    0,
    999999,
    'ACTIVE',
    'SERVICE',
    'SYSTEM',
    'Sản phẩm ảo đại diện cho dịch vụ đi kèm của hệ thống',
    '{}'::jsonb,
    '',
    '[]'::jsonb,
    '[]'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE 
SET stock_quantity = 999999, status = 'ACTIVE';
