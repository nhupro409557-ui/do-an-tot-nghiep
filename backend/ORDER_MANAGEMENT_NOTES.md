# Order Management Notes

## Update 2026-06-18 - Xác nhận xuất từ nhiều kệ

- Một dòng đơn hàng có thể phân bổ số lượng xuất từ nhiều kệ khác nhau.
- Nhân viên thêm/xóa dòng kệ trong màn chi tiết đơn trước khi chuyển sang `SHIPPED`.
- Tổng số lượng của các kệ phải bằng số lượng dòng đơn; cùng một dòng không được chọn trùng kệ.
- Nếu không nhập phân bổ thủ công, hệ thống tiếp tục tự chọn theo FIFO.

## Update 2026-06-18 - Xuất hàng theo lô nội bộ

- Khi đơn chuyển sang `SHIPPED`, tồn kho được trừ đồng thời ở cấp tổng, cấp kệ và cấp lô nội bộ.
- Trong kệ nhân viên xác nhận, backend tự lấy lô có `received_at` cũ nhất trước; nhân viên không cần thấy hoặc chọn mã lô.
- Mỗi lần tiêu thụ lô ghi `inventory_lot_movements` loại `SALE`, liên kết với `order_id` và `order_code`.
- Nếu tồn theo kệ còn nhưng tổng số lượng lô trong kệ không đủ, transaction giao hàng bị rollback để tránh sai lệch dữ liệu.

## Scope of the 2026-05 upgrade
- Added richer admin operations for order handling instead of status-only updates.
- Added order detail data for admin review, printing, staff assignment, shipping tracking, and cancellation handling.
- Added guardrails against invalid backward status transitions such as `COMPLETED -> PENDING`.
- Added stock restoration when an order moves into `CANCELLED`.
- Added manual refund marking for online payments when an order is cancelled or refunded.
- Added Gmail-based email notifications when order status changes.
- Added `PAYMENT_FAILED` to distinguish payment failure from deliberate cancellation.
- Added idempotency support for checkout order creation.
- Added `order_history_logs` so order state changes are auditable.
- Added pending-order expiration logic to auto-release reserved inventory for stale orders.
- Added an in-app maintenance loop so pending-order expiration can run automatically without a manual trigger.
- Added `RETURNING / RETURNED` states for reverse-logistics handling.
- Added stub integration adapters for shipment registration and refund execution so later real providers can plug in without rewriting order business rules.
- Added sandbox shipping-fee calculation and quote endpoint for checkout.
- Added MoMo dev sandbox payment initialization with backend-generated payUrl and IPN callback handling.

## Files touched
- `backend/app/application/commerce/schemas.py`
- `backend/app/application/commerce/use_cases.py`
- `backend/app/api/v1/routers/commerce.py`
- `backend/app/infrastructure/database/models.py`
- `backend/migrations/032_order_management_upgrade.sql`
- `backend/migrations/033_order_resilience_and_history.sql`
- `backend/migrations/034_order_reverse_logistics.sql`
- `backend/app/application/commerce/integrations.py`
- `backend/app/main.py`
- `backend/app/config.py`
- `legacy apiDb.ts`
- `frontend/src/features/storefront-commerce/pages/CheckoutPage.tsx`
- `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

## Design notes
- Current status flow is intentionally strict: pending -> processing -> shipped -> completed, with cancellation only before completion.
- Checkout now accepts an optional `idempotency_key` field or `Idempotency-Key` header so double-click / retry scenarios return the same order instead of creating duplicates.
- `PAYMENT_FAILED` is used for stale or failed online payment scenarios so reporting can distinguish them from human-initiated cancellation.
- Customer notifications currently use the project's existing Gmail SMTP configuration (`smtp.gmail.com` with app password style credentials in `.env`).
- Refund processing is still internal-only for now. The system marks payment transactions as refunded in local data, but does not call a real payment gateway yet.
- Shipping integration is also internal-only in this patch. `shipping_provider` and `tracking_code` are stored so the UI and future integrations have a stable data shape.
- Shipping handoff now goes through a gateway abstraction. The default implementation is still a stub, but the order workflow no longer depends on manual inline tracking-code logic.
- Shipping fee in checkout is now computed by a sandbox pricing service based on destination keywords and item count, then persisted in the order total.
- Restock logic maps order items back to inventory logs using `reference_code = order_code` and the original `ORDER_CREATED` reservation entries.
- Invoice and delivery-note printing are browser-rendered documents from the admin UI, which keeps the feature usable now without introducing a PDF service.
- Order status email sending is best-effort: if Gmail SMTP is not configured or delivery fails, the order update still succeeds.
- Pending-order cleanup now has both a manual maintenance endpoint and an automatic background loop started from FastAPI lifespan.
- Inventory deduction still happens at order creation, but the code now makes the mitigation explicit: stale `PENDING` orders can be moved to `PAYMENT_FAILED`, which also restores stock and voucher usage.
- Inventory race conditions are handled with database transactions plus pessimistic locking (`SELECT ... FOR UPDATE`) around stock reads and writes.
- Reverse logistics is now modeled with `RETURNING -> RETURNED -> REFUNDED` so failed deliveries or customer returns can be represented without overloading `CANCELLED`.
- Refund execution also goes through a gateway abstraction. The current implementation is a safe stub that records provider references in `payment_transactions.raw_response`.
- MoMo sandbox integration follows the official `POST /v2/gateway/api/create` flow and is configured through env vars (`momo_partner_code`, `momo_access_key`, `momo_secret_key`, `momo_redirect_url`, `momo_ipn_path`).
- If MoMo sandbox credentials are missing, the code falls back to a deterministic sandbox URL so the checkout demo flow still remains usable.

## Next recommended steps
- Add real shipping provider webhooks and label creation.
- Add refund gateway adapters for MoMo, VNPay, and card payments.
- Add richer templates and delivery logging for Gmail notifications.
- Replace the in-process maintenance loop with a dedicated scheduler / worker in production if horizontal scaling is introduced.
- Add return-reason codes and warehouse intake inspection outcomes for `RETURNED` orders.
- Replace sandbox shipping pricing with a live carrier quote adapter if exact fee calculation is required.

## Refactor Structure Notes (June 2026)

### 1. Backend Service Layer Pattern
- Logic truy vấn SQL và database mapping của `list_orders` và `get_order_detail` đã được tách hoàn toàn ra khỏi Router Layer (`commerce.py`) và chuyển sang Service Layer chuyên biệt: [order_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/order_service.py).
- Router [commerce.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/commerce.py) hiện tại chỉ còn khai báo endpoints, nhận payload, Dependency Injection và chuyển tiếp xử lý sang `order_service.py` hoặc các Use Cases khác của Commerce.

### 2. Frontend Feature-First Architecture
- Module Quản lý Đơn hàng đã được chuyển dịch hoàn chỉnh về thư mục tính năng độc lập tại: [src/features/admin-orders/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-orders/)
  - **Services**: [adminOrdersApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-orders/services/adminOrdersApi.ts) chứa các hàm gọi API đơn hàng (được bóc tách từ `apiDb.ts` để giữ tính tương thích ngược thông qua spread operator).
  - **Hooks**: [useAdminOrdersLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-orders/hooks/useAdminOrdersLogic.ts) xử lý logic nghiệp vụ và state của UI.
  - **Components**: [AdminOrdersTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-orders/components/AdminOrdersTab.tsx) chứa UI hiển thị danh sách và chi tiết đơn hàng.
- Các file điều phối chung như [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), và [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx) đã được cập nhật đường dẫn import mới.



## Update 2026-06-05 Order Service Repository Split

- Tách truy vấn danh sách đơn hàng và chi tiết đơn hàng khỏi `app/application/services/order_service.py` sang `app/infrastructure/database/repositories/order_repo.py`.
- `order_service.py` hiện chỉ còn gọi repository và xử lý lỗi không tìm thấy đơn hàng.
- Kết quả kiểm tra: compile backend thành công; import `app.main`, commerce router, order service và order repository thành công.


## Update 2026-06-05 Commerce Router SQL Cleanup

- Tách hai truy vấn DB còn lại trong `app/api/v1/routers/commerce.py` sang repository.
- Danh sách voucher public chuyển sang `voucher_repo.list_public_vouchers`; tra cứu đơn hàng theo `order_code` cho MoMo IPN chuyển sang `order_repo.get_order_id_by_code`.
- `commerce.py` hiện không còn SQL trực tiếp; router chỉ điều phối request, repository/service/use case xử lý dữ liệu.
- Kết quả kiểm tra: compile backend thành công; import `app.main`, commerce router, order repository và voucher repository thành công.
