ALTER TABLE inventory_locations
    DROP CONSTRAINT IF EXISTS inventory_locations_purpose_check;

ALTER TABLE inventory_locations
    ADD CONSTRAINT inventory_locations_purpose_check
    CHECK (purpose IN ('STORAGE', 'WARRANTY', 'QC', 'DAMAGED', 'RETURN', 'USED', 'VIRTUAL'));

INSERT INTO inventory_locations (
    code, name, location_type, status, is_default, zone, description,
    purpose, sort_order, allow_mixed_sku
)
VALUES (
    'CU-01-01',
    'Dãy hàng cũ - Kệ 01 - Ô 01',
    'WAREHOUSE',
    'ACTIVE',
    FALSE,
    'Dãy hàng cũ',
    'Vị trí lưu thiết bị cũ đã được thẩm định, tách khỏi tồn hàng mới',
    'USED',
    94001,
    FALSE
)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    zone = EXCLUDED.zone,
    description = EXCLUDED.description,
    purpose = EXCLUDED.purpose,
    sort_order = EXCLUDED.sort_order,
    allow_mixed_sku = EXCLUDED.allow_mixed_sku,
    updated_at = NOW();

CREATE TABLE IF NOT EXISTS used_device_intake_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_code VARCHAR(40) NOT NULL UNIQUE,
    source_type VARCHAR(30) NOT NULL
        CHECK (source_type IN ('USER_BUYBACK', 'RETURNED_USED')),
    seller_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    seller_name VARCHAR(255),
    seller_phone VARCHAR(30),
    original_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    return_request_id UUID REFERENCES return_requests(id) ON DELETE SET NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    imei VARCHAR(80) NOT NULL,
    serial_number VARCHAR(120),
    expected_price NUMERIC(14, 2) CHECK (expected_price IS NULL OR expected_price >= 0),
    note TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED'
        CHECK (status IN (
            'SUBMITTED', 'RECEIVED', 'INSPECTING', 'APPRAISED',
            'REPAIR_REQUIRED', 'ACCEPTED', 'REJECTED', 'CANCELLED'
        )),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    received_at TIMESTAMPTZ,
    appraised_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_used_intake_active_imei
    ON used_device_intake_requests(imei)
    WHERE status NOT IN ('REJECTED', 'CANCELLED');

CREATE INDEX IF NOT EXISTS idx_used_intake_status_created
    ON used_device_intake_requests(status, created_at DESC);

CREATE TABLE IF NOT EXISTS used_device_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_request_id UUID NOT NULL REFERENCES used_device_intake_requests(id) ON DELETE CASCADE,
    inspector_id UUID REFERENCES users(id) ON DELETE SET NULL,
    outcome VARCHAR(30) NOT NULL
        CHECK (outcome IN ('APPRAISED', 'REPAIR_REQUIRED', 'REJECTED')),
    condition_grade VARCHAR(10)
        CHECK (condition_grade IS NULL OR condition_grade IN ('A', 'B', 'C')),
    condition_score INTEGER CHECK (condition_score IS NULL OR condition_score BETWEEN 0 AND 100),
    battery_health INTEGER CHECK (battery_health IS NULL OR battery_health BETWEEN 0 AND 100),
    checklist JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    repair_cost_estimate NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (repair_cost_estimate >= 0),
    proposed_acquisition_price NUMERIC(14, 2)
        CHECK (proposed_acquisition_price IS NULL OR proposed_acquisition_price >= 0),
    proposed_sale_price NUMERIC(14, 2)
        CHECK (proposed_sale_price IS NULL OR proposed_sale_price >= 0),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_used_inspections_intake_created
    ON used_device_inspections(intake_request_id, created_at DESC);

CREATE TABLE IF NOT EXISTS used_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_code VARCHAR(40) NOT NULL UNIQUE,
    intake_request_id UUID NOT NULL UNIQUE
        REFERENCES used_device_intake_requests(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    product_imei_id UUID REFERENCES product_imeis(id) ON DELETE SET NULL,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    imei VARCHAR(80) NOT NULL UNIQUE,
    serial_number VARCHAR(120),
    condition_grade VARCHAR(10) NOT NULL CHECK (condition_grade IN ('A', 'B', 'C')),
    condition_score INTEGER NOT NULL CHECK (condition_score BETWEEN 0 AND 100),
    battery_health INTEGER CHECK (battery_health IS NULL OR battery_health BETWEEN 0 AND 100),
    ownership_status VARCHAR(20) NOT NULL DEFAULT 'STORE_OWNED'
        CHECK (ownership_status IN ('STORE_OWNED', 'CONSIGNMENT')),
    status VARCHAR(30) NOT NULL DEFAULT 'READY_FOR_PRICING'
        CHECK (status IN (
            'READY_FOR_PRICING', 'READY_FOR_SALE', 'RESERVED', 'SOLD',
            'RETURNED_QC', 'REPAIRING', 'RETIRED'
        )),
    original_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    acquisition_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (acquisition_cost >= 0),
    refurbishment_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (refurbishment_cost >= 0),
    approved_sale_price NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (approved_sale_price >= 0),
    warranty_months INTEGER NOT NULL DEFAULT 0 CHECK (warranty_months BETWEEN 0 AND 36),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_used_devices_serial_number
    ON used_devices(serial_number)
    WHERE serial_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_used_devices_status_location
    ON used_devices(status, location_id, created_at DESC);

CREATE TABLE IF NOT EXISTS used_device_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES used_devices(id) ON DELETE CASCADE,
    original_list_price NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (original_list_price >= 0),
    new_reference_price NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (new_reference_price >= 0),
    acquisition_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (acquisition_cost >= 0),
    refurbishment_cost NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (refurbishment_cost >= 0),
    proposed_sale_price NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (proposed_sale_price >= 0),
    approved_sale_price NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (approved_sale_price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'APPROVED'
        CHECK (status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'SUPERSEDED')),
    reason TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_used_device_prices_device_created
    ON used_device_prices(device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS used_device_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_request_id UUID REFERENCES used_device_intake_requests(id) ON DELETE CASCADE,
    device_id UUID REFERENCES used_devices(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    note TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (intake_request_id IS NOT NULL OR device_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_used_device_events_intake_created
    ON used_device_events(intake_request_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_used_device_events_device_created
    ON used_device_events(device_id, created_at DESC);

INSERT INTO permissions (code, module, description)
VALUES
    ('used_product:read', 'used_product', 'Xem yêu cầu và kho hàng cũ'),
    ('used_product:manage', 'used_product', 'Tiếp nhận và thẩm định hàng cũ'),
    ('used_product:approve', 'used_product', 'Xác nhận thu mua và duyệt giá hàng cũ')
ON CONFLICT (code) DO UPDATE
SET module = EXCLUDED.module,
    description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'SUPER_ADMIN'
  AND p.code IN ('used_product:read', 'used_product:manage', 'used_product:approve')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code = 'used_product:read'
WHERE r.code = 'STAFF_ADMIN'
ON CONFLICT DO NOTHING;
