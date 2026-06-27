DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'product_identifier_pairs'
          AND column_name = 'imei'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'product_identifier_pairs'
          AND column_name = 'imei1'
    ) THEN
        ALTER TABLE product_identifier_pairs RENAME COLUMN imei TO imei1;
    END IF;
END $$;

ALTER TABLE product_identifier_pairs
    ADD COLUMN IF NOT EXISTS imei2 VARCHAR(80);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'product_identifier_pairs_imei1_fkey'
          AND conrelid = 'product_identifier_pairs'::regclass
    ) THEN
        ALTER TABLE product_identifier_pairs
            ADD CONSTRAINT product_identifier_pairs_imei1_fkey
            FOREIGN KEY (imei1) REFERENCES product_imeis(imei) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'product_identifier_pairs_imei2_fkey'
          AND conrelid = 'product_identifier_pairs'::regclass
    ) THEN
        ALTER TABLE product_identifier_pairs
            ADD CONSTRAINT product_identifier_pairs_imei2_fkey
            FOREIGN KEY (imei2) REFERENCES product_imeis(imei) ON DELETE SET NULL;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_product_identifier_pairs_lookup_imei;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_identifier_pairs_product_imei1_unique
    ON product_identifier_pairs(product_id, imei1);

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_identifier_pairs_product_imei2_unique
    ON product_identifier_pairs(product_id, imei2)
    WHERE imei2 IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_product_identifier_pairs_lookup_imei1
    ON product_identifier_pairs(product_id, variant_id, imei1);

CREATE INDEX IF NOT EXISTS idx_product_identifier_pairs_lookup_imei2
    ON product_identifier_pairs(product_id, variant_id, imei2)
    WHERE imei2 IS NOT NULL;
