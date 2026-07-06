# Review Management Notes

## Cập nhật 2026-07-04 - Chuẩn hóa thông báo lỗi review

- Chuẩn hóa thông báo lỗi khi admin cập nhật/xóa đánh giá sang tiếng Việt có dấu.
- Không đổi logic moderation, notification hoặc đồng bộ điểm đánh giá sản phẩm.
- Verification: `py_compile` và test quản trị liên quan pass.

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
- Added customer notification creation when an admin approves or rejects a pending review.

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
- `frontend/src/features/products/components/ProductReviews.tsx`
- `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

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
- Admin moderation now creates a `notifications` row of type `review` only when status changes into `PUBLISHED` or `REJECTED` and the review belongs to a logged-in user.

## Next recommended steps
- Add customer-side upload flow for review media instead of URL-only input.
- Persist which admin account replied or moderated each review in the UI.
- Add server-side pagination and filter params for admin review listing if volume grows.
- Move review throttling to Redis for stronger distributed rate-limit behavior.
- Add dedicated UML or BPMN artifacts for thesis documentation: use case, activity, and sequence diagram for review moderation.

## Update 2026-06-05 Admin Review Service Refactor

- Tạo `app/infrastructure/database/repositories/review_repo.py` để chứa truy vấn DB cho danh sách đánh giá, thống kê, cập nhật trạng thái, tạo thông báo và xóa đánh giá.
- Làm mỏng `app/application/services/review_service.py`: service chỉ còn dựng payload cập nhật, kiểm tra nghiệp vụ, tạo nội dung thông báo, gọi sync thống kê sản phẩm và commit.
- Cập nhật `app/api/v1/routers/admin_reviews.py` để import `ReviewStatusPayload` trực tiếp từ `app.api.v1.schemas.admin` thay vì file compatibility `admin_schemas.py`.
- Sửa lại nội dung thông báo tiếng Việt khi đánh giá được duyệt hoặc bị từ chối.
- Kết quả kiểm tra: compile toàn bộ backend bằng `.venv` thành công; import `app.main`, admin review router, review service và review repository thành công.
