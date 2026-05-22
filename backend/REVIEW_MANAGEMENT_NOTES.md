# Review Management Notes

## Scope of the 2026-05 upgrade
- Added pre-public moderation for new product reviews with default `PENDING` flow.
- Added support for attaching image/video URLs to reviews.
- Added shop replies directly on each review.
- Added admin flags for bad reviews and spam handling metadata.
- Added review summary reporting by product with average rating and moderation counts.
- Added lightweight anti-spam checks to block duplicate comments and hold suspicious reviews for review.
- Added customer self-service edit/delete for reviews within a controlled review window.
- Added review time window enforcement based on completed order age.
- Added refund/return-aware review labeling so historical reviews stay traceable after reverse-logistics events.
- Added denormalized review score sync into `products.rating` and `products.review_count`.
- Added basic input sanitization and rate limiting for review submission/update flows.

## Files touched
- `backend/app/shared/reviews.py`
- `backend/app/api/v1/routers/content.py`
- `backend/app/api/v1/routers/admin.py`
- `backend/app/api/v1/routers/catalog.py`
- `backend/app/api/v1/routers/storefront.py`
- `backend/app/infrastructure/database/models.py`
- `backend/migrations/init_database.sql`
- `backend/migrations/038_review_management_upgrade.sql`
- `backend/migrations/039_review_resilience_and_user_controls.sql`
- `frontend/src/services/apiDb.ts`
- `frontend/src/components/product/ProductReviews.tsx`
- `frontend/src/pages/AdminDashboard.tsx`

## Design notes
- New reviews are stored as `PENDING` so the shop can moderate before they appear publicly.
- Public product pages still only render reviews with status `PUBLISHED`.
- Media attachments currently use uploaded/public URLs instead of raw file bytes so the feature stays compatible with the current stack.
- Spam handling is intentionally conservative: exact duplicate comments are rejected, while suspicious patterns are kept in `PENDING` or flagged metadata for admin review.
- "Bao cao danh gia xau" is modeled as admin flag metadata (`flagged_reason`, `flagged_at`) so teams can investigate without losing the original review content immediately.
- Review content is sanitized before persistence to reduce XSS risk, even though the React layer already escapes render output by default.
- A customer may update or delete their own review only while the related order is still inside the configured review window and has not moved into `RETURNED` or `REFUNDED`.
- Product score widgets should now read `products.rating` and `products.review_count` instead of recalculating `AVG()` from `product_reviews` on every storefront request.
- Rate limiting is intentionally simple in this phase: one user may create at most 3 reviews within 5 minutes.

## Next recommended steps
- Add customer-side upload flow for review media instead of URL-only input.
- Persist which admin account replied or moderated each review in the UI.
- Add server-side pagination and filter params for admin review listing if volume grows.
- Add automated notification when a pending review has been approved or rejected.
- Move review throttling to Redis for stronger distributed rate-limit behavior.
- Add dedicated UML or BPMN artifacts for thesis documentation: use case, activity, and sequence diagram for review moderation.
