# Inventory Management Notes

## 1. Document purpose
- This file upgrades the inventory module notes from feature bullets into a combined BRD/SRS style reference.
- It separates business process, system design, data model, API direction, and phased implementation.
- It also records the gap between the current implementation and the enterprise-grade target architecture.

## 2. Current-state critique

### 2.1 Business logic mixed with UI flow
- The old description leaned on UI actions such as opening a popup or clicking inventory actions.
- For thesis-grade or enterprise documentation, inventory must be modeled as business processes and state transitions, not screen steps.

### 2.2 Single-stock-column bottleneck
- The current runtime still stores stock in `products.stock_quantity` and `product_variants.stock_quantity`.
- This is acceptable for a single logical warehouse, but it is not structurally sufficient for multi-warehouse inventory.

### 2.3 Costing model gap
- The current stock log can already capture `unit_cost`, but outgoing valuation and COGS are not yet controlled by a formal costing method.
- The target design standardizes on `MOVING_AVERAGE` first, with room to evolve to `FIFO` later if needed.

### 2.4 Internal control gap
- Direct inventory adjustment by one actor is fast, but it does not satisfy maker-checker control for high-risk operations such as stock count adjustments or reversals.

### 2.5 Concurrency gap
- The current implementation already uses transactional writes and row locking.
- The next enterprise step is to supplement direct deduction with `inventory_reservations` so checkout and payment flows can reserve stock first and post final issue later.

## 3. Target business process model

### 3.1 Inbound inventory process
1. Warehouse staff creates inbound document.
2. Document captures supplier, location, item lines, quantity, and unit cost.
3. Document stays `DRAFT` or `PENDING_APPROVAL`.
4. Checker approves document.
5. System posts inventory transaction.
6. On-hand quantity increases at `(item, location)`.
7. Moving-average cost is recalculated.
8. Immutable ledger entry is stored.

### 3.2 Outbound inventory process
1. Sales order or internal request creates reservation.
2. Reservation reduces allocable stock but does not reduce posted stock yet.
3. When shipment or issue is confirmed, reservation is consumed.
4. System posts outbound inventory transaction.
5. On-hand quantity decreases at `(item, location)`.
6. COGS is derived from the active costing method.

### 3.3 Stock count and adjustment process
1. Counter creates count sheet for a location.
2. Expected quantity is loaded from system balance.
3. Counted quantity is entered.
4. Variance is reviewed.
5. Checker approves variance posting.
6. Adjustment ledger entries are generated.

### 3.4 Reversal process
1. Authorized maker requests reversal of an existing posted document.
2. Checker approves reversal.
3. System posts compensating entries instead of editing old rows.

## 4. System requirements

### 4.1 Functional requirements
- Support inventory by product or variant and by warehouse location.
- Support inbound, outbound, transfer-ready, count, adjustment, reversal, and reservation flows.
- Support minimum stock, reorder point, cycle count period, and sale blocking policy.
- Support immutable transaction logs.
- Support approval workflow for high-risk inventory movements.
- Support inventory export for audit and operational use.

### 4.2 Non-functional requirements
- ACID transaction handling for all posted stock movements.
- Idempotency for API requests that can be retried.
- Row-level locking for balance updates.
- Clear audit trail for who created, approved, posted, and reversed stock documents.
- Backward compatibility during migration from single-warehouse to multi-warehouse mode.

## 5. Technical architecture

### 5.1 Current implementation
- Backend: FastAPI + Pydantic + async SQLAlchemy.
- Database: PostgreSQL.
- Admin UI: React + TypeScript.
- Current stock mutation safety: transaction boundary, pessimistic locking, append-only adjustment logs.

### 5.2 Enterprise target architecture
- Inventory balance source of truth moves to `inventory_levels`.
- Stock movement source of truth moves to `inventory_transactions`.
- Human workflow source of truth moves to `inventory_documents` and `inventory_document_lines`.
- Checkout and payment race mitigation moves to `inventory_reservations`.
- Cost valuation is controlled explicitly through `costing_method`.

## 6. Database design direction

### 6.1 New normalized entities
- `inventory_locations`
  - master data for warehouse, branch, or virtual fulfillment location
- `inventory_levels`
  - stock by `(product or variant, location)`
  - stores `on_hand_quantity`, `reserved_quantity`, `safety_stock_quantity`, `reorder_point_quantity`
- `inventory_documents`
  - document header for inbound, count, adjustment, reversal, transfer, reservation release
- `inventory_document_lines`
  - item-level quantities and costing context
- `inventory_transactions`
  - immutable posted ledger rows
- `inventory_reservations`
  - temporary allocation for cart, checkout, or order payment flow

### 6.2 Costing policy
- Standardized initial costing method: `MOVING_AVERAGE`
- Why this first:
  - easier to operate than FIFO in the current codebase
  - sufficient for thesis and mid-market commerce scope
  - compatible with multi-location inventory if cost is tracked per item/location or consolidated by policy

## 7. Approval and control model

### 7.1 Maker-checker
- Maker creates draft or pending inventory document.
- Checker approves or rejects.
- Only approved documents can post stock movements.

### 7.2 Segregation of duties
- `inventory:adjust` is no longer the only future permission.
- Additional permissions are introduced for:
  - `inventory:approve`
  - `inventory:count`
  - `inventory:reserve`

## 8. Concurrency and risk handling

### 8.1 Current control
- `SELECT ... FOR UPDATE` is already used for direct stock updates.

### 8.2 Next control layer
- Introduce reservation records with expiration windows.
- Post final issue only after payment or fulfillment checkpoint.
- Handle lock timeout or retry logic at service layer.
- Preserve compensating transactions for reversals instead of editing posted rows.

## 9. API design direction

### 9.1 Current endpoints retained
- `GET /admin/products/{product_id}/inventory`
- `POST /admin/products/{product_id}/inventory/adjust`
- `PATCH /admin/products/{product_id}/inventory/policy`
- `GET /admin/inventory/export`

### 9.2 Next endpoints to add
- `POST /admin/inventory/documents`
- `POST /admin/inventory/documents/{id}/submit`
- `POST /admin/inventory/documents/{id}/approve`
- `POST /admin/inventory/documents/{id}/reject`
- `POST /admin/inventory/reservations`
- `POST /admin/inventory/reservations/{id}/release`
- `GET /admin/inventory/levels`
- `GET /admin/inventory/transactions`

## 10. What is implemented now
- Product and variant inventory view.
- Adjustment popup and manual inventory transaction capture.
- Supplier, unit cost, location code, and location name on inventory adjustments.
- Product-level minimum stock and sale-block policy.
- CSV export compatible with Excel.
- Automatic stock restoration on order cancellation in order flow.
- Immutable-style inventory log through append-only API behavior.

## 11. What is added in this phase
- Formal documentation restructure to BRD/SRS style.
- Non-breaking schema foundation for:
  - multi-warehouse inventory levels
  - inventory documents and approval workflow
  - posted transaction ledger
  - reservation handling
  - moving-average costing metadata

## 12. Migration strategy

### Phase A: Compatibility mode
- Keep existing `stock_quantity` columns active.
- Mirror initial balances into default location `MAIN`.
- Keep current UI running while new tables are introduced.

### Phase B: Dual-write mode
- New inventory services write to both legacy stock columns and new normalized inventory tables.
- Read models can still use legacy fields until validation is complete.

### Phase C: Full normalized mode
- Balance reads move to `inventory_levels`.
- Outbound flows use reservation plus posting.
- Legacy stock columns become derived or deprecated fields.

## 13. Files touched in this phase
- `backend/INVENTORY_MANAGEMENT_NOTES.md`
- `backend/migrations/036_inventory_policy_and_receipt_metadata.sql`
- `backend/migrations/037_inventory_enterprise_foundation.sql`
- `backend/migrations/017_admin_rbac_permissions.sql`
- `backend/migrations/init_database.sql`

## 14. Open decisions
- Whether product-level inventory should remain supported long-term or all stock should move to variant-only control.
- Whether moving-average cost is tracked globally or per location.
- Whether reservation happens at cart stage, checkout stage, or payment-initiation stage.
