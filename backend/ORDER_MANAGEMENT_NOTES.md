# Order Management Notes

## Cập nhật 2026-07-13 - Bán thiết bị hàng cũ tại POS

- POS có hai nguồn hàng rõ ràng: `Sản phẩm mới` và `Hàng cũ`; nhân viên có thể tìm máy cũ theo tiêu đề, mã thiết bị hoặc IMEI rồi thêm đúng một thiết bị vật lý vào giỏ.
- Dòng hàng cũ gửi `used_device_id`, không gửi `product_id`/`variant_id`, không hiển thị ô quét IMEI/serial và không cho tăng số lượng hoặc áp dụng nhầm logic mua kèm của hàng mới.
- Thẻ máy và hóa đơn thể hiện rõ nhãn hàng cũ, hạng máy, mã thiết bị, IMEI, pin, bảo hành và giá bán đã duyệt.
- Khi tạo đơn POS, thiết bị và bài đăng chuyển `READY_FOR_SALE/PUBLISHED → SOLD`; máy đã bán biến mất ngay khỏi catalog POS và backend vẫn chặn đồng thời nếu request cũ cố mua lại.
- Sửa hoàn tiền đơn chỉ có hàng cũ: hệ thống nhận diện thiết bị `SOLD` là hàng đã giao dù không có adjustment `ORDER_SHIPPED` của kho catalog, sau đó chuyển máy về `RETURNED_QC`; bài đăng giữ `SOLD` để không tự bán lại trước QC.
- Kiểm thử giao diện hoàn chỉnh bằng các đơn `EMV2093217402` và `EMV5494230567`; cả hai đã `REFUNDED`, điểm đã thu hồi, fixture máy cũ đã được khôi phục `READY_FOR_SALE/PUBLISHED` kèm audit đối soát.

## Cập nhật 2026-07-13 - Hoàn thiện đơn bán tại quầy (POS)

- Đơn POS chọn khách hàng lưu đúng `orders.user_id`, vì vậy đơn xuất hiện trong tài khoản và lịch sử mua hàng của đúng khách được chọn.
- Đơn nhận tại cửa hàng dùng `fulfillment_method = STORE_PICKUP`, không gắn hãng vận chuyển và phí giao hàng luôn bằng `0` dù bộ tính phí trả về báo giá mặc định.
- Thanh toán tiền mặt tại quầy bắt buộc khai báo số tiền khách đưa và backend từ chối hoàn tất khi số tiền nhỏ hơn tổng đơn; frontend đồng thời khóa nút xác nhận để phản hồi sớm.
- Luồng tạo đơn flush các dòng hàng trước khi xuất kho tự động, bảo đảm tồn catalog, tồn kệ, lô FIFO và IMEI/serial đều được cập nhật trong cùng giao dịch.
- Đơn POS kiểm thử được hoàn tác; migration `091_reconcile_admin_pos_test_order.sql` và `092_reconcile_pos_refund_main_inventory.sql` chỉ đối soát hai mã đơn test đã xác định.

## Cập nhật 2026-07-10 - Không bỏ sót trạng thái thiết bị cũ khi giao hàng

- Khi đơn có phiếu xuất kho đã hoàn tất và được chuyển sang `SHIPPED`, backend nay đánh dấu các thiết bị cũ của đơn từ `RESERVED` sang `SOLD` dù FIFO hàng catalog đã được xử lý trước đó.
- Bài đăng của thiết bị đã bán đồng thời chuyển sang `SOLD`, giúp trạng thái đơn, thiết bị và bài đăng nhất quán.

## Cập nhật 2026-07-07 (Bổ sung 5) - Chặn xuất kho thiếu định danh khi giao đơn

- Khi hoàn tất phiếu xuất kho liên kết đơn hàng, backend hiện kiểm tra số dòng IMEI/serial thật sự được cập nhật sang `SOLD`.
- Nếu cập nhật thiếu do dữ liệu định danh bị giao dịch khác thay đổi đồng thời, phiếu xuất không được chuyển `COMPLETED` và đơn không được chuyển `SHIPPED`.

## Cập nhật 2026-07-07 (Bổ sung 4) - Không giữ đơn PENDING sau hủy/thất bại thanh toán

- Cập nhật lại quyết định ở mục "Bổ sung 3": payment online thất bại hoặc khách hủy phiên thanh toán không còn giữ đơn ở `PENDING` để retry nữa.
- Luồng đúng hiện tại là chuyển đơn còn `PENDING` sang `PAYMENT_FAILED` để đóng reservation, voucher, loyalty và quota flash sale ngay trong transaction nghiệp vụ.
- Lý do: ở mức phản biện đồ án, ưu tiên dữ liệu nội bộ nhất quán và có rollback rõ ràng hơn khả năng retry trên cùng một đơn sau khi gateway đã báo thất bại.

## Cập nhật 2026-07-07 (Bổ sung) - Siết vòng đời thanh toán thất bại

- **Chặn trạng thái sai sau khi đã thanh toán**: `ORDER_STATUS_TRANSITIONS` không còn cho phép đơn `PAID` hoặc `PROCESSING` chuyển sang `PAYMENT_FAILED`. Nếu đơn đã có thanh toán thành công hoặc đã xử lý kho, luồng đúng phải là `CANCELLED`/`REFUNDED` thay vì ghi nhận thất bại thanh toán.
- **Đồng bộ giao dịch pending khi đơn thất bại**: Khi đơn còn `PENDING` chuyển sang `PAYMENT_FAILED`, các `payment_transactions` còn `PENDING` của đơn được đánh dấu `FAILED` và ghi `failed_at`, tránh giao dịch treo sau khi reservation/voucher đã được giải phóng.

## Cập nhật 2026-07-07 - Ràng buộc thanh toán và đóng giữ hàng nguyên tử

- **Ràng buộc phương thức thanh toán khi tạo đơn**: `CreateOrderRequest` chỉ chấp nhận `COD`, `MOMO`, `ZALOPAY` và `SEPAY`, đúng với các cổng mà `CreateOrderUseCase` và `PaymentUseCase` đang xử lý. Tránh trường hợp schema cho `VNPAY` hoặc `CREDIT_CARD` đi vào luồng tạo đơn nhưng nghiệp vụ không có gateway tương ứng.
- **Đóng reservation an toàn hơn**: `close_active_order_reservations` khóa dòng reservation và inventory level bằng `FOR UPDATE`, đồng thời thêm điều kiện chặn trực tiếp trong câu `UPDATE` để không thể giải phóng/tiêu thụ lượng giữ hàng nếu `reserved_quantity` hoặc `on_hand_quantity` đã thay đổi giữa chừng.
- **Phạm vi chưa đổi**: Chưa thay đổi chính sách đăng ký vận chuyển sau khi chuyển đơn sang `SHIPPED`; lỗi từ shipping gateway hiện vẫn chỉ được ghi log.

## Cập nhật 2026-07-07 (Bổ sung 2) - Khắc phục các lỗi logic nghiệp vụ phản biện
- **Tránh trùng lặp đăng ký vận chuyển**: Chặn việc tự động đăng ký lại vận chuyển qua API khi đơn chuyển sang `SHIPPED` nếu đơn đã được cấp mã vận đơn (`tracking_code`) từ trước.
- **Tự động hủy phiếu xuất kho khi đơn hoàn tiền (`REFUNDED`)**: Tự động chuyển các phiếu xuất kho (`OUTBOUND` document) liên kết chưa hoàn tất sang `CANCELLED` khi đơn hàng chuyển sang trạng thái `REFUNDED` nhằm tránh việc kho đóng gói nhầm.
- **Mở rộng cập nhật trạng thái hoàn tiền cho COD**: Hỗ trợ thay đổi trạng thái thanh toán của đơn hàng sang `REFUNDED` khi hoàn tiền cho đơn COD (do đơn COD không có các giao dịch thanh toán online qua gateway).

## Cập nhật 2026-07-07 (Bổ sung 3) - Sửa lỗi logic nghiệp vụ phản biện (Bán hàng & Đơn hàng)
- **Kiểm tra trùng lặp khi hoàn kho (Idempotency)**: Thêm check log `ORDER_CANCELLED_RESTOCK` ở đầu hàm `_restock_order_items` tránh cộng dồn tồn kho nhiều lần.
- **Hoàn trả kho khi hoàn tiền trực tiếp (`REFUNDED`)**: Sửa logic check `previous_status != "RETURNED"` cho phép hoàn trả kho từ đơn đã xuất hàng (`SHIPPED` hoặc `COMPLETED`) khi bấm hoàn tiền.
- **Ghi chú đã được cập nhật bởi Bổ sung 4**: Quyết định giữ nguyên trạng thái `PENDING` khi thanh toán online thất bại không còn áp dụng; hiện hệ thống đóng đơn sang `PAYMENT_FAILED` để rollback tài nguyên ngay.
- **Kiểm tra chéo khi thanh toán lại (Cross-Module Validation)**: Bổ sung check active reservations và kiểm tra hạn dùng, trạng thái của voucher trong hàm `retry` của `PaymentUseCase`.

## Cập nhật 2026-07-07 (Bổ sung 6) - Khắc phục các lỗi phản biện đồ án (Tạo & Vận chuyển Đơn hàng)

- **Ngăn ngừa Race Condition trùng lặp đơn hàng**: Chuyển logic kiểm tra `idempotency_key` vào bên trong khối transaction chính của `CreateOrderUseCase` sử dụng ngoại lệ `IdempotencyOrderExistsException` truyền `order_id` (UUID) để triệt tiêu lỗ hổng TOCTOU và tránh lỗi lazy-loading của SQLAlchemy.
- **Đồng bộ hạng thành viên khi tiêu điểm thưởng**: Cập nhật lại `user.loyalty_tier` khi trừ điểm ví thưởng ở luồng checkout online và POS.
- **Sửa lỗi chặn đăng ký vận chuyển**: Thay đổi điều kiện trong `complete_order_carrier.py` để hỗ trợ tạo vận đơn giao hàng với Mock Carrier cho cả các đơn hàng thông thường không đi qua quy trình sinh phiếu xuất kho liên kết.

## Cập nhật 2026-07-07 (Bổ sung 7) - Khắc phục lỗi Saga hoàn tiền và đơn hàng online 0 đồng

- **Gọi API Refund ngoài Transaction (Saga Integrity)**: Cập nhật `CompleteOrderUseCase.execute` để chuyển cuộc gọi `RefundGateway().refund()` ra ngoài ranh giới transaction chính, tránh việc giữ PostgreSQL locks lâu khi API phản hồi chậm, đồng thời lưu trạng thái hoàn tiền của giao dịch/đơn hàng thông qua các transaction ngắn độc lập.
- **Xử lý đơn hàng online 0 đồng (0 VND Checkout)**: Cập nhật `CreateOrderUseCase.execute` để tự động bỏ qua cuộc gọi API cổng thanh toán online nếu số tiền cần thanh toán bằng 0đ (sau khi giảm trừ voucher/loyalty points). Đơn hàng và giao dịch được đánh dấu thành công là `PAID` ngay lập tức và tự động tạo phiếu xuất kho nháp (`OUTBOUND`).

# Cập nhật 2026-07-12 - Tách hai hướng hoàn hàng

- Đơn chuyển sang `RETURNING` bắt buộc xác định nguồn hoàn: khách từ chối nhận (`DELIVERY_REFUSED`) hoặc khách đã nhận rồi chủ động trả (`CUSTOMER_RETURN`).
- Bắt buộc lưu lý do hoàn; có thể lưu riêng mã vận đơn hoàn để không nhầm với vận đơn giao đi.
- Hàng khách đã nhận phải có hồ sơ đổi trả trong module Hậu mãi trước khi đơn được chuyển sang đang hoàn hoặc đã nhận lại.
- Khi cửa hàng xác nhận `RETURNED`, bắt buộc ghi tình trạng tiếp nhận: nguyên niêm phong, đã mở hộp/thiếu phụ kiện hoặc hư hỏng/bất thường.
- Chỉ hàng giao không thành công và còn nguyên niêm phong mới được tự động nhập lại tồn bán được. Hàng đã mở hoặc hư hỏng không tự cộng lại kho hàng mới.
- Giao diện quản trị đơn hàng hiển thị biểu mẫu hoàn chuyên dụng và dẫn nhân viên sang module Hậu mãi cho nhánh khách chủ động trả.
- Migration: `085_order_return_workflow.sql`.
## 2026-07-13 - Làm mới đơn hàng trong trang tài khoản

- Hook đơn hàng tải lại khi người dùng chuyển tab tài khoản, giúp tổng quan và lịch sử mua hàng đồng bộ sau khi trạng thái đơn vừa thay đổi.
- Tổng quan hiển thị trạng thái đang tải thay vì tạm kết luận khách chưa có đơn hàng.
- Form checkout dùng địa chỉ hành chính 2 cấp: tỉnh/thành phố và phường/xã; không còn bắt buộc quận/huyện.

## Cập nhật 2026-07-13 - Hủy đơn có lý do và đồng bộ COD

- Dropdown trạng thái nhanh của quản trị mở chi tiết khi chọn hủy để bắt buộc nhập lý do, tránh API từ chối ngầm và trạng thái tự quay lại.
- Sau khi đổi trạng thái nhanh, frontend đọc lại chi tiết đơn để đồng bộ cả trạng thái thanh toán COD và các tác dụng phụ nghiệp vụ.
- Khách hàng có thể tự hủy đơn `PENDING` ngay tại trang chi tiết, bắt buộc nhập lý do và dùng endpoint hủy đơn dành cho chủ đơn hàng.

## Cập nhật 2026-07-13 - Làm mới số liệu Tổng quan khi quay lại tab

- Tab Tổng quan luôn đọc lại API overview khi người dùng quay về từ phân hệ khác, tránh giữ số đơn đã hủy/hoàn tiền cũ trong cache frontend.
- Truy vấn overview vẫn là nguồn chuẩn cho tổng số và tỉ lệ hủy; bảng đơn hàng không tự ghi đè read-model báo cáo.
