CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_levels_product_variant_location
    ON inventory_levels(product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id);
