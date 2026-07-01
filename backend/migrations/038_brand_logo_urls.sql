WITH brand_logos(name, logo_url, logo_alt_text, category_codes) AS (
    VALUES
    ('Apple', '/images/brands/apple.png', 'Logo Apple', ARRAY['smartphones','tablets','laptops','accessories','wearables']),
    ('Samsung', '/images/brands/samsung.png', 'Logo Samsung', ARRAY['smartphones','tablets','wearables']),
    ('Xiaomi', '/images/brands/xiaomi.png', 'Logo Xiaomi', ARRAY['smartphones','tablets']),
    ('OPPO', '/images/brands/oppo.png', 'Logo OPPO', ARRAY['smartphones']),
    ('vivo', '/images/brands/vivo.png', 'Logo vivo', ARRAY['smartphones']),
    ('ASUS', '/images/brands/asus.png', 'Logo ASUS', ARRAY['smartphones','laptops']),
    ('Lenovo', '/images/brands/lenovo.png', 'Logo Lenovo', ARRAY['tablets','laptops']),
    ('Microsoft', '/images/brands/microsoft.png', 'Logo Microsoft', ARRAY['tablets','laptops']),
    ('Dell', '/images/brands/dell.png', 'Logo Dell', ARRAY['laptops']),
    ('HP', '/images/brands/hp.png', 'Logo HP', ARRAY['laptops']),
    ('Acer', '/images/brands/acer.png', 'Logo Acer', ARRAY['laptops']),
    ('MSI', '/images/brands/msi.png', 'Logo MSI', ARRAY['laptops']),
    ('Sony', '/images/brands/sony.png', 'Logo Sony', ARRAY['accessories','may-anh']),
    ('HONOR', '/images/brands/honor.png', 'Logo HONOR', ARRAY['smartphones','tablets']),
    ('TECNO', '/images/brands/tecno.png', 'Logo TECNO', ARRAY['smartphones']),
    ('Marshall', '/images/brands/marshall.png', 'Logo Marshall', ARRAY['accessories']),
    ('JBL', '/images/brands/jbl.png', 'Logo JBL', ARRAY['accessories']),
    ('Sennheiser', '/images/brands/sennheiser.png', 'Logo Sennheiser', ARRAY['accessories']),
    ('Razer', '/images/brands/razer.png', 'Logo Razer', ARRAY['accessories']),
    ('Anker', '/images/brands/anker.png', 'Logo Anker', ARRAY['accessories']),
    ('Ugreen', '/images/brands/ugreen.png', 'Logo Ugreen', ARRAY['accessories']),
    ('Baseus', '/images/brands/baseus.png', 'Logo Baseus', ARRAY['accessories']),
    ('Belkin', '/images/brands/belkin.png', 'Logo Belkin', ARRAY['accessories']),
    ('Mophie', '/images/brands/mophie.png', 'Logo Mophie', ARRAY['accessories']),
    ('Garmin', '/images/brands/garmin.png', 'Logo Garmin', ARRAY['wearables']),
    ('Coros', '/images/brands/coros.png', 'Logo Coros', ARRAY['wearables']),
    ('Huawei', '/images/brands/huawei.png', 'Logo Huawei', ARRAY['wearables']),
    ('Amazfit', '/images/brands/amazfit.png', 'Logo Amazfit', ARRAY['wearables']),
    ('Canon', '/images/brands/canon.png', 'Logo Canon', ARRAY['may-anh']),
    ('Fujifilm', '/images/brands/fujifilm.png', 'Logo Fujifilm', ARRAY['may-anh']),
    ('GoPro', '/images/brands/gopro.png', 'Logo GoPro', ARRAY['cameras']),
    ('DJI', '/images/brands/dji.png', 'Logo DJI', ARRAY['cameras']),
    ('Ezviz', '/images/brands/ezviz.png', 'Logo Ezviz', ARRAY['cameras']),
    ('Imou', '/images/brands/imou.png', 'Logo Imou', ARRAY['cameras']),
    ('Vietmap', '/images/brands/vietmap.png', 'Logo Vietmap', ARRAY['cameras']),
    ('70mai', '/images/brands/70mai.png', 'Logo 70mai', ARRAY['cameras'])
),
upserted_brands AS (
    INSERT INTO brands (code, name, logo_url, logo_alt_text)
    SELECT lower(name), name, logo_url, logo_alt_text
    FROM brand_logos
    ON CONFLICT (code) DO UPDATE SET
        name = EXCLUDED.name,
        logo_url = EXCLUDED.logo_url,
        logo_alt_text = EXCLUDED.logo_alt_text,
        cache_version = brands.cache_version + 1,
        updated_at = NOW()
    RETURNING id, name
)
INSERT INTO brand_categories (brand_id, category_id)
SELECT upserted_brands.id, categories.id
FROM brand_logos
JOIN upserted_brands ON upserted_brands.name = brand_logos.name
JOIN LATERAL unnest(brand_logos.category_codes) AS category_code ON TRUE
JOIN categories ON categories.code = category_code
ON CONFLICT DO NOTHING;
