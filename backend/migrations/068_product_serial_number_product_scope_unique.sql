ALTER TABLE product_serial_numbers
    DROP CONSTRAINT IF EXISTS product_serial_numbers_serial_number_key;

DROP INDEX IF EXISTS idx_product_serial_numbers_product_serial_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_serial_numbers_product_serial_unique
    ON product_serial_numbers(product_id, serial_number);
