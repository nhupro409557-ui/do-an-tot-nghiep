# Order Management Notes

## Cập nhật 2026-06-29 - Bổ sung test đơn hàng sinh phiếu xuất kho

- Bổ sung test admin order lifecycle cho nhánh `PENDING -> PROCESSING`: đơn COD có sản phẩm/variant thật sẽ sinh phiếu xuất kho `OUTBOUND`.
- Sau khi phiếu xuất được auto-suggest và hoàn tất, hệ thống đồng bộ đơn hàng sang `SHIPPED`.
- Sửa query kiểm tra tồn variant khi tạo đơn: cast `variant_id` và `product_id` sang UUID để tránh lỗi asyncpg `could not determine data type of parameter`.
- Verification: `pytest backend/tests/test_12_admin_inventory_outbound_flow.py -q` pass.

## Cập nhật 2026-06-29 - Bổ sung test quyền cho thao tác admin đơn hàng

- Bổ sung test API admin cho `/api/orders/{order_id}/admin`: anonymous và customer bị chặn, admin cập nhật được thông tin xử lý nội bộ của đơn hàng.
- Endpoint cập nhật đơn hàng admin nay dùng `require_staff_or_admin`; trước đó route admin này chưa có dependency phân quyền rõ ràng.
- Sau khi dependency đọc quyền dùng chung session, endpoint rollback transaction đọc trước khi gọi `CompleteOrderUseCase`, tránh lỗi `A transaction is already begun on this Session` khi use case mở transaction ghi.
- Test cũng ghi nhận rule hiện tại không cho chuyển trạng thái `PENDING -> CONFIRMED`; nhánh này được assert là lỗi nghiệp vụ `409`.
- Verification: `pytest backend/tests/test_10_admin_permissions_and_orders_flow.py backend/tests/test_11_admin_voucher_flash_sale_flow.py -q` pass.

## Cập nhật 2026-06-29 - Chống kết quả kiểm tra voucher POS lỗi thời

- POS kiểm tra lại voucher khi phương thức thanh toán, khách hàng, mã voucher, tổng tiền hoặc danh sách sản phẩm thay đổi.
- Mỗi lần kiểm tra có mã phiên tăng dần; response cũ bị bỏ qua để không ghi đè kết quả của request mới hơn.
- Giữ nguyên payload tạo đơn và API validate voucher hiện tại.
- Verification: frontend `npm run lint` và `npm run build` pass.

## Cập nhật 2026-06-27 - Sửa dữ liệu giá mua kèm và dịch vụ trong POS

- Kiểm thử POS sau refactor phát hiện nhiều badge mua kèm và dịch vụ hiển thị `0 ₫`.
- Nguyên nhân nằm ở mapping response của `list_admin_products`: repository đã trả dữ liệu nhưng service không đưa các trường giá, tồn kho, override và metadata vào `salesConfig`.
- Đã khôi phục đầy đủ contract để POS dùng lại công thức giá hiện có; không thay đổi payload tạo đơn.

## Cập nhật 2026-06-27 - Tách tiếp POS và hoàn tất đơn hàng

- Tách giao diện POS đang hoạt động sang `AdminPosWorkspace.tsx`; `AdminPosModal.tsx` giữ state, handler và khung modal.
- Tách `CompleteOrderUseCase` thành lớp điều phối chính cùng hai mixin `complete_order_carrier.py` và `complete_order_fulfillment.py`.
- Giữ nguyên MRO, API gọi hiện tại, quy tắc tồn kho, hoàn tiền, vận chuyển và loyalty.

## Cập nhật 2026-06-27 - Tách commerce use cases/repository và sửa lỗi mã hóa repository

- Tách `app/application/commerce/use_cases.py` thành facade tương thích và các module nhỏ trong `app/application/commerce/use_cases/`: `common`, `voucher_service`, `create_order`, `payment`, `complete_order`, `reporting`.
- Tách `commerce_repo.py` thành facade tương thích và các module nhỏ trong `app/infrastructure/database/repositories/commerce/`: `vouchers`, `reservations`, `inventory_levels`, `payments`, `orders_reports`.
- Sửa lỗi mã hóa/cú pháp trong `commerce_repo.py` tại thông báo `Không đủ tồn khả dụng ở các kệ để xuất kho.`; trước đó chuỗi bị hỏng và dính vào khai báo `deduct_inventory_levels_from_locations`, làm file không compile được.
- Tách POS admin thành `AdminPosModalUtils` và `AdminPosSuccessScreen` để giảm kích thước component chính.
- Verification: `py_compile` pass cho commerce repository, commerce use cases, router commerce và `app/main.py`; frontend `npm run lint` pass.

## Cập nhật 2026-06-27 - Đồng bộ giá mua kèm và dịch vụ trong POS admin

- POS admin tính giá sản phẩm mua kèm theo cùng hướng với storefront: ưu tiên `offer.price` nếu API đã trả giá ưu đãi đã tính sẵn; nếu thiếu thì fallback về giá gốc và công thức giảm theo `discountType/discountValue`.
- API admin products đã hydrate thêm `price`, `salePrice/discountPrice`, `originalPrice` và `normalDiscountPrice` cho sản phẩm mua kèm, tránh badge `[Mua kèm]` hiển thị `0 đ` khi dữ liệu offer cũ không lưu sẵn giá đã tính.
- Giá dịch vụ đi kèm trong POS admin nay ưu tiên `overridePrice`, sau đó mới tính theo `priceMode` gồm `FIXED`, `PERCENT` và `TIERED_AMOUNT`.
- Cách tính `TIERED_AMOUNT` dùng `metadata.priceTiers` và hỗ trợ tier cuối không có `max`, tránh trường hợp dịch vụ có bảng giá hợp lệ nhưng hiển thị `0 đ`.
- Dòng dịch vụ trong giỏ POS được định danh theo cả sản phẩm cha và dịch vụ để cùng một dịch vụ gắn với hai sản phẩm khác nhau không bị gộp nhầm số lượng.

## Cập nhật 2026-06-27 - Khắc phục danh sách sản phẩm và khách hàng trong POS

- Sửa `AdminPosModal.tsx` để danh sách sản phẩm POS gọi `GET /admin/products` với `page=1`, nhờ đó frontend nhận đúng payload dạng `{ items: [...] }`; trước đó endpoint trả mảng trực tiếp khi không truyền `page` nhưng modal chỉ đọc `data.items`, làm danh sách luôn rỗng.
- Sửa tham số tìm khách hàng từ `q` sang `search` để khớp endpoint `GET /admin/customers`.
- Chuẩn hóa đọc response dạng mảng hoặc `{ items }` bằng helper `listFromResponse`, giúp modal bền hơn nếu endpoint thay đổi chế độ phân trang.
- Chuẩn hóa điểm khách hàng từ `points`, `loyaltyPointsBalance` hoặc `loyalty_points_balance`; danh sách khách hàng tải sẵn nay hiển thị ngay dưới ô tìm kiếm thay vì chỉ hiện sau khi nhập từ khóa.
- Chuẩn hóa nhãn và giá biến thể sản phẩm POS từ `configuration`, `colorName`, `storage`, `ram`, `salePrice`, `discountPrice` để tránh hiện `undefined` và dùng đúng giá bán.

## Cập nhật 2026-06-27 - Hiển thị sản phẩm trong quản lý đơn hàng

- Kiểm tra backend endpoint `GET /api/orders` và `GET /api/orders/{order_id}`: dữ liệu đơn hàng đã có trường `items`, lấy từ bảng `order_items`.
- Cập nhật `frontend/src/features/admin-orders/components/AdminOrdersTab.tsx` để bảng quản lý đơn hàng có thêm cột `Sản phẩm`, hiển thị tối đa 2 dòng sản phẩm đầu tiên kèm số lượng và dòng `+n sản phẩm khác` nếu đơn có nhiều sản phẩm.
- Bảng `Sản phẩm trong đơn` trong modal chi tiết dùng helper chuẩn hóa dữ liệu, hỗ trợ cả key camelCase (`productName`, `totalPrice`) và snake_case (`product_name`, `total_price`) để tránh mất hiển thị khi nguồn dữ liệu thay đổi kiểu field.
- Khi một đơn không có dòng sản phẩm, giao diện hiển thị trạng thái rõ ràng `Chưa có dòng sản phẩm` thay vì để bảng trống.

## Cập nhật 2026-06-27 - Luồng tạo đơn hàng tại quầy (POS)

### Backend

- Thêm `is_offline: bool` và `internal_note: str` vào `CreateOrderRequest` trong `backend/app/application/commerce/schemas.py`.
- Trong `CreateOrderUseCase` tại `backend/app/application/commerce/use_cases.py`, nếu `request.is_offline` là `True`:
  - Đơn hàng được tạo trực tiếp với `status = 'COMPLETED'` và `payment_status = 'PAID'`.
  - Gọi `CompleteOrderUseCase._ship_order_items(order)` để trừ tồn kho theo FIFO ngay lập tức.
  - Gọi `commerce_repo.close_active_order_reservations(self._session, order.id, 'CONSUMED')` để đóng reservation tạm thời.
  - Tự động cộng điểm loyalty cho tài khoản khách hàng được chọn.
  - Bỏ qua các bước thanh toán qua cổng online như MoMo, ZaloPay, SePay, kể cả khi nhân viên chọn phương thức thanh toán online để phân loại giao dịch tại quầy.

### Frontend

- Thêm `AdminPosModal.tsx` cho luồng POS mini:
  - Tìm kiếm và chọn sản phẩm, chọn variant phù hợp, kiểm tra tồn kho.
  - Tìm kiếm và gán khách hàng đã đăng ký hoặc để trống cho khách vãng lai.
  - Áp dụng voucher shop và trừ điểm loyalty trực tiếp.
  - Chọn phương thức thanh toán, tính tiền thừa trả khách.
- Tích hợp nút `Tạo đơn tại quầy` vào `AdminOrdersTab.tsx`.
- Sau khi tạo đơn thành công, hệ thống mở bản in hóa đơn nhiệt K80 qua iframe ẩn và gọi `window.print()`.

### Liên kết đơn hàng offline theo email

- POS lưu email khách vãng lai vào `recipient_email` trong bảng `orders`.
- Khi khách đăng ký tài khoản online hoặc đăng nhập Google lần đầu, helper `sync_and_link_offline_orders` trong `backend/app/api/routers/auth_utils.py`:
  - Lấy họ tên và số điện thoại từ đơn offline gần nhất khớp email để điền vào tài khoản mới.
  - Cập nhật `user_id` của các đơn offline cũ khớp email về user mới.
  - Tổng hợp điểm loyalty từ các đơn offline cũ và tạo giao dịch đồng bộ điểm tương ứng.

## Cập nhật 2026-06-27 - Bổ sung Bộ lọc Sản phẩm tại POS

- **Tích hợp UI**: Bổ sung 2 dropdown bộ lọc bên cạnh thanh tìm kiếm sản phẩm tại giao diện POS Modal (`AdminPosModal.tsx`):
  - **Danh mục (Category)**: Tự động tải danh sách danh mục từ API `/admin/categories`.
  - **Thương hiệu (Brand)**: Tự động tải danh sách thương hiệu từ API `/admin/brands`.
- **Tích hợp API & Logic lọc**:
  - Giao diện POS tự động truyền thêm tham số `categoryId` và `brandId` vào query string của API `/admin/products` khi nhân viên thực hiện thao tác chọn bộ lọc.
  - Các bộ lọc và thanh tìm kiếm từ khóa hoạt động đồng bộ và giữ nguyên trạng thái của nhau khi thay đổi.

## Cập nhật 2026-06-27 - Hỗ trợ Mua kèm Phụ kiện & Dịch vụ tại POS

- **Giao diện Badge Thêm nhanh**: Bên dưới thẻ sản phẩm, các phụ kiện gợi ý mua kèm (`accessoryOffers`) và các dịch vụ đi kèm (`attachedServices`) được render thành các badge bấm nhanh nhỏ nhắn, thẩm mỹ:
  - **Badge màu đỏ**: Dành cho Phụ kiện mua kèm, tự động áp dụng giá combo ưu đãi đã giảm (được lưu trong `offer.price`).
  - **Badge màu xanh**: Dành cho Dịch vụ đi kèm (được lưu trong `service.fixedPrice` hoặc `service.percentValue`).
- **Thao tác một chạm**: Nhân viên chỉ cần nhấp vào các badge này, phụ kiện/dịch vụ sẽ tự động được thêm vào giỏ hàng bên phải dưới dạng các dòng đơn hàng chuẩn hóa `[Mua kèm] <Tên>` hoặc `[Dịch vụ] <Tên>` với đúng giá tiền ưu đãi tương ứng.
