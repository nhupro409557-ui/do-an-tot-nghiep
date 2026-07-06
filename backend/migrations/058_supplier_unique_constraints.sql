-- Migration: Add is_deleted to suppliers and create partial unique indexes for code and tax_code

ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- Drop default unique constraint on code to replace it with a partial index
ALTER TABLE suppliers DROP CONSTRAINT IF EXISTS suppliers_code_key;

-- Create partial unique index on code
DROP INDEX IF EXISTS uq_suppliers_code_active;
CREATE UNIQUE INDEX IF NOT EXISTS uq_suppliers_code_active ON suppliers(code) WHERE is_deleted = FALSE;

-- Create partial unique index on tax_code (representing tax_id)
DROP INDEX IF EXISTS uq_suppliers_tax_code_active;
CREATE UNIQUE INDEX IF NOT EXISTS uq_suppliers_tax_code_active ON suppliers(tax_code) WHERE is_deleted = FALSE AND tax_code IS NOT NULL;
