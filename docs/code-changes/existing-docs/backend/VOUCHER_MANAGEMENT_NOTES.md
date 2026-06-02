# Voucher Management Notes

## Scope of the 2026-05 upgrade
- Added voucher wallet support through `user_vouchers`.
- Activated `validity_days_after_claim` with real claim-time expiration.
- Refactored validation from one long method into a rule pipeline inside `backend/app/application/commerce/use_cases.py`.
- Standardized validation failures with `error_code` and `metadata`.
- Added rollback support when orders move to `CANCELLED` or `REFUNDED`.

## Files touched
- `backend/app/application/commerce/schemas.py`
- `backend/app/application/commerce/use_cases.py`
- `backend/app/api/v1/routers/commerce.py`
- `backend/app/infrastructure/database/models.py`
- `backend/migrations/031_voucher_wallet_and_rollbacks.sql`
- `frontend/src/services/apiDb.ts`
- `frontend/src/pages/CheckoutPage.tsx`

## Design notes
- Voucher wallet is required only when `validity_days_after_claim > 0`.
- Order creation still persists voucher counters directly in PostgreSQL for consistency.
- Redis flash-sale counters are not fully introduced in this patch because the project does not yet have the worker/sync loop needed to flush counters back safely.
- Structured validation errors are intended for frontend upsell or more precise guidance, especially the `shortfall_amount` metadata.
- Voucher rollback currently honors `refund_policy` values `ALWAYS` and `SHOP_FAULT_ONLY`. The latter is treated as rollback-allowed in the current project because no separate root-cause code for cancellation exists yet.

## Next recommended steps
- Add a dedicated voucher wallet page so users can claim and reuse vouchers without typing codes.
- Introduce Redis reservation counters with a background reconciliation job.
- Add unit tests per voucher rule.
- Add cancellation reason codes so `SHOP_FAULT_ONLY` can be enforced more precisely.
