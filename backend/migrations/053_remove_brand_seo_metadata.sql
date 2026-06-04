-- Remove unused SEO metadata fields from brands.
-- Brand management keeps landing title only.

ALTER TABLE brands DROP COLUMN IF EXISTS seo_title;
ALTER TABLE brands DROP COLUMN IF EXISTS seo_description;
