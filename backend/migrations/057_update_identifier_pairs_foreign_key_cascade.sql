-- Migration: update product_identifier_pairs foreign keys with ON UPDATE CASCADE

ALTER TABLE product_identifier_pairs
    DROP CONSTRAINT IF EXISTS product_identifier_pairs_imei_fkey,
    DROP CONSTRAINT IF EXISTS product_identifier_pairs_imei1_fkey,
    DROP CONSTRAINT IF EXISTS product_identifier_pairs_imei2_fkey,
    DROP CONSTRAINT IF EXISTS product_identifier_pairs_product_id_serial_number_fkey;

ALTER TABLE product_identifier_pairs
    ADD CONSTRAINT product_identifier_pairs_imei1_fkey
        FOREIGN KEY (imei1) REFERENCES product_imeis(imei) ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT product_identifier_pairs_imei2_fkey
        FOREIGN KEY (imei2) REFERENCES product_imeis(imei) ON DELETE SET NULL ON UPDATE CASCADE,
    ADD CONSTRAINT product_identifier_pairs_product_id_serial_number_fkey
        FOREIGN KEY (product_id, serial_number) REFERENCES product_serial_numbers(product_id, serial_number) ON DELETE CASCADE ON UPDATE CASCADE;
