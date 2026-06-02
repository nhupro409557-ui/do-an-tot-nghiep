-- Add gallery images for each product variant, separate from the representative image.
ALTER TABLE product_variants
ADD COLUMN IF NOT EXISTS images JSONB NOT NULL DEFAULT '[]'::jsonb;
