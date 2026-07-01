WITH brand_logos(name, logo_url, logo_alt_text, category_codes) AS (
    VALUES
    ('itel', '/images/brands/itel.png', 'Logo itel', ARRAY['smartphones']),
    ('Meizu', '/images/brands/meizu.png', 'Logo Meizu', ARRAY['smartphones']),
    ('realme', '/images/brands/realme.png', 'Logo realme', ARRAY['smartphones'])
)
UPDATE brands
SET logo_url = brand_logos.logo_url,
    logo_alt_text = brand_logos.logo_alt_text,
    cache_version = cache_version + 1,
    updated_at = NOW()
FROM brand_logos
WHERE lower(brands.name) = lower(brand_logos.name);

WITH brand_logos(name, logo_url, logo_alt_text, category_codes) AS (
    VALUES
    ('itel', '/images/brands/itel.png', 'Logo itel', ARRAY['smartphones']),
    ('Meizu', '/images/brands/meizu.png', 'Logo Meizu', ARRAY['smartphones']),
    ('realme', '/images/brands/realme.png', 'Logo realme', ARRAY['smartphones'])
)
INSERT INTO brands (code, name, logo_url, logo_alt_text)
SELECT lower(name), name, logo_url, logo_alt_text
FROM brand_logos
WHERE NOT EXISTS (
    SELECT 1
    FROM brands
    WHERE lower(brands.name) = lower(brand_logos.name)
       OR lower(brands.code) = lower(brand_logos.name)
);

WITH brand_logos(name, logo_url, logo_alt_text, category_codes) AS (
    VALUES
    ('itel', '/images/brands/itel.png', 'Logo itel', ARRAY['smartphones']),
    ('Meizu', '/images/brands/meizu.png', 'Logo Meizu', ARRAY['smartphones']),
    ('realme', '/images/brands/realme.png', 'Logo realme', ARRAY['smartphones'])
)
INSERT INTO brand_categories (brand_id, category_id)
SELECT brands.id, categories.id
FROM brand_logos
JOIN brands ON lower(brands.name) = lower(brand_logos.name)
JOIN LATERAL unnest(brand_logos.category_codes) AS category_code ON TRUE
JOIN categories ON categories.code = category_code
ON CONFLICT DO NOTHING;
