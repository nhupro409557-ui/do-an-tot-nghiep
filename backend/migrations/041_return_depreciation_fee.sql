ALTER TABLE return_requests
    ADD COLUMN IF NOT EXISTS depreciation_fee NUMERIC(14, 2) NOT NULL DEFAULT 0
        CHECK (depreciation_fee >= 0);
