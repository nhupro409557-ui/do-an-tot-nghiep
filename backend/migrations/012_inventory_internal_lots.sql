CREATE TABLE IF NOT EXISTS inventory_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_code VARCHAR(80) NOT NULL UNIQUE,
    product_id UUID REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    location_id UUID NOT NULL REFERENCES inventory_locations(id) ON DELETE RESTRICT,
    source_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    source_reference VARCHAR(120),
    initial_quantity INTEGER NOT NULL CHECK (initial_quantity >= 0),
    remaining_quantity INTEGER NOT NULL CHECK (remaining_quantity >= 0),
    unit_cost NUMERIC(14, 2),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'DEPLETED', 'CANCELLED')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (product_id IS NOT NULL AND variant_id IS NULL)
        OR (product_id IS NULL AND variant_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_inventory_lots_variant_fifo
    ON inventory_lots(variant_id, received_at, created_at)
    WHERE status = 'ACTIVE' AND remaining_quantity > 0;

CREATE INDEX IF NOT EXISTS idx_inventory_lots_product_fifo
    ON inventory_lots(product_id, received_at, created_at)
    WHERE status = 'ACTIVE' AND remaining_quantity > 0;

CREATE INDEX IF NOT EXISTS idx_inventory_lots_location
    ON inventory_lots(location_id, status, received_at);

CREATE TABLE IF NOT EXISTS inventory_lot_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id UUID NOT NULL REFERENCES inventory_lots(id) ON DELETE RESTRICT,
    movement_type VARCHAR(20) NOT NULL
        CHECK (movement_type IN ('RECEIPT', 'SALE', 'RETURN', 'ADJUSTMENT', 'REVERSAL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reference_code VARCHAR(120),
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    inventory_document_id UUID REFERENCES inventory_documents(id) ON DELETE SET NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_lot_movements_lot_created
    ON inventory_lot_movements(lot_id, created_at);

CREATE INDEX IF NOT EXISTS idx_inventory_lot_movements_reference
    ON inventory_lot_movements(reference_code, created_at);

WITH existing_levels AS (
    SELECT
        il.id,
        il.product_id,
        il.variant_id,
        il.location_id,
        il.on_hand_quantity,
        il.average_unit_cost,
        il.updated_at
    FROM inventory_levels il
    WHERE il.on_hand_quantity > 0
),
inserted_lots AS (
    INSERT INTO inventory_lots (
        lot_code,
        product_id,
        variant_id,
        location_id,
        source_reference,
        initial_quantity,
        remaining_quantity,
        unit_cost,
        received_at,
        status,
        metadata
    )
    SELECT
        'LOT-INIT-' || REPLACE(level.id::text, '-', ''),
        level.product_id,
        level.variant_id,
        level.location_id,
        'INITIAL-BACKFILL',
        level.on_hand_quantity,
        level.on_hand_quantity,
        level.average_unit_cost,
        COALESCE(level.updated_at, NOW()),
        'ACTIVE',
        jsonb_build_object('backfilled', TRUE, 'inventoryLevelId', level.id::text)
    FROM existing_levels level
    ON CONFLICT (lot_code) DO NOTHING
    RETURNING id, initial_quantity
)
INSERT INTO inventory_lot_movements (
    lot_id,
    movement_type,
    quantity,
    reference_code,
    note
)
SELECT
    lot.id,
    'RECEIPT',
    lot.initial_quantity,
    'INITIAL-BACKFILL',
    'Khởi tạo lô nội bộ từ tồn kho hiện có.'
FROM inserted_lots lot;
