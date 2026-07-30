ALTER TABLE used_device_listings
    ADD COLUMN IF NOT EXISTS manufacturer_warranty_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS manufacturer_warranty_provider VARCHAR(120),
    ADD COLUMN IF NOT EXISTS manufacturer_warranty_activated_at DATE,
    ADD COLUMN IF NOT EXISTS manufacturer_warranty_total_months INTEGER;

ALTER TABLE used_device_listings
    DROP CONSTRAINT IF EXISTS used_device_listings_manufacturer_warranty_months_check;

ALTER TABLE used_device_listings
    ADD CONSTRAINT used_device_listings_manufacturer_warranty_months_check
    CHECK (manufacturer_warranty_total_months IS NULL OR manufacturer_warranty_total_months BETWEEN 1 AND 60);
