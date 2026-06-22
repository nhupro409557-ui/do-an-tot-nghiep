CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_policy_staged_identifier_active
    ON inventory_policy_migration_identifiers(identifier_value)
    WHERE status = 'STAGED';
