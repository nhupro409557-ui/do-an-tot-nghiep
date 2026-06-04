-- Remove unused SEO metadata fields from categories.
-- Category management no longer exposes or persists these fields.

ALTER TABLE categories DROP COLUMN IF EXISTS seo_title;
ALTER TABLE categories DROP COLUMN IF EXISTS seo_description;
ALTER TABLE categories DROP COLUMN IF EXISTS seo_keywords;
