WITH phone_category AS (
    SELECT id
    FROM categories
    WHERE slug = 'smartphones'
      AND parent_id IS NULL
    LIMIT 1
)
UPDATE categories AS category
SET warranty_policy = CASE
        WHEN category.parent_id IS NULL THEN
            '{"inheritWarrantyPolicy": false, "hasWarranty": true, "warrantyMonths": 12, "allowOneForOne": true, "oneForOneDays": 30}'::jsonb
        ELSE
            '{"inheritWarrantyPolicy": true, "hasWarranty": true, "warrantyMonths": 12, "allowOneForOne": true, "oneForOneDays": 30}'::jsonb
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE category.id IN (SELECT id FROM phone_category)
   OR category.parent_id IN (SELECT id FROM phone_category);

WITH phone_categories AS (
    SELECT id
    FROM categories
    WHERE slug = 'smartphones'
      AND parent_id IS NULL

    UNION ALL

    SELECT child.id
    FROM categories AS child
    JOIN categories AS parent ON parent.id = child.parent_id
    WHERE parent.slug = 'smartphones'
      AND parent.parent_id IS NULL
),
phone_warranty AS (
    SELECT '{"inheritWarrantyPolicy": true, "hasWarranty": true, "warrantyMonths": 12, "allowOneForOne": true, "oneForOneDays": 30}'::jsonb AS policy
)
UPDATE products AS product
SET sales_config = jsonb_set(
        COALESCE(product.sales_config, '{}'::jsonb),
        '{warrantyPolicy}',
        phone_warranty.policy,
        true
    ),
    specifications = jsonb_set(
        COALESCE(product.specifications, '{}'::jsonb),
        '{_warrantyPolicy}',
        phone_warranty.policy,
        true
    ),
    updated_at = CURRENT_TIMESTAMP
FROM phone_warranty
WHERE product.deleted_at IS NULL
  AND COALESCE(product.status, '') <> 'MERGED'
  AND (
      product.category_id IN (SELECT id FROM phone_categories)
      OR product.subcategory_id IN (SELECT id FROM phone_categories)
  );
