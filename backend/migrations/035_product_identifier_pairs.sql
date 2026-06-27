CREATE TABLE IF NOT EXISTS product_identifier_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variants(id) ON DELETE CASCADE,
    imei VARCHAR(80) NOT NULL REFERENCES product_imeis(imei) ON DELETE CASCADE,
    serial_number VARCHAR(120) NOT NULL,
    source_reference VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, imei),
    UNIQUE (product_id, serial_number),
    FOREIGN KEY (product_id, serial_number)
        REFERENCES product_serial_numbers(product_id, serial_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_product_identifier_pairs_lookup_imei
    ON product_identifier_pairs(product_id, variant_id, imei);

CREATE INDEX IF NOT EXISTS idx_product_identifier_pairs_lookup_serial
    ON product_identifier_pairs(product_id, variant_id, serial_number);

INSERT INTO product_identifier_pairs (
    product_id,
    variant_id,
    imei,
    serial_number,
    source_reference
)
SELECT
    pi.product_id,
    pi.variant_id,
    pi.imei,
    psn.serial_number,
    COALESCE(pi.source_reference, psn.source_reference)
FROM product_imeis pi
JOIN product_serial_numbers psn
  ON psn.product_id = pi.product_id
 AND psn.variant_id IS NOT DISTINCT FROM pi.variant_id
 AND psn.source_reference IS NOT DISTINCT FROM pi.source_reference
WHERE pi.source_reference IS NOT NULL
  AND pi.imei IS NOT NULL
  AND psn.serial_number IS NOT NULL
  AND (
      SELECT COUNT(*)
      FROM product_imeis pi_count
      WHERE pi_count.product_id = pi.product_id
        AND pi_count.variant_id IS NOT DISTINCT FROM pi.variant_id
        AND pi_count.source_reference IS NOT DISTINCT FROM pi.source_reference
  ) = (
      SELECT COUNT(*)
      FROM product_serial_numbers psn_count
      WHERE psn_count.product_id = psn.product_id
        AND psn_count.variant_id IS NOT DISTINCT FROM psn.variant_id
        AND psn_count.source_reference IS NOT DISTINCT FROM psn.source_reference
  )
  AND (
      SELECT COUNT(*)
      FROM product_imeis pi_count
      WHERE pi_count.product_id = pi.product_id
        AND pi_count.variant_id IS NOT DISTINCT FROM pi.variant_id
        AND pi_count.source_reference IS NOT DISTINCT FROM pi.source_reference
  ) = 1
ON CONFLICT DO NOTHING;
