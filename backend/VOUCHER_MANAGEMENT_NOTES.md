# Voucher Management Notes

## Cập nhật 2026-06-29 - Bổ sung test CRUD voucher admin

- Bổ sung test API admin cho voucher: customer bị chặn khi tạo voucher, payload giảm giá âm trả `422`, admin tạo/list/update/deactivate voucher trên database test.
- Test assert trực tiếp bảng `vouchers` để xác nhận trạng thái sau khi update và deactivate.
- Verification: `pytest backend/tests/test_10_admin_permissions_and_orders_flow.py backend/tests/test_11_admin_voucher_flash_sale_flow.py -q` pass.

## Cập nhật 2026-06-29 - Chỉ gửi voucher Checkout đã xác nhận

- Checkout lưu riêng mã đang nhập và mã đã validate thành công.
- Payload tạo đơn chỉ gửi mã đã xác nhận; sửa mã hoặc điều kiện áp dụng sẽ xóa/revalidate trạng thái cũ.
- Response validate cũ bị bỏ qua bằng mã phiên request.
- Verification: frontend `npm run lint` và `npm run build` pass.

## Cập nhật 2026-06-29 - Tái kiểm tra voucher POS theo đầy đủ điều kiện

- Voucher đã áp dụng trong POS được kiểm tra lại khi khách hàng, phương thức thanh toán, mã voucher, tổng tiền hoặc danh sách sản phẩm thay đổi.
- Bỏ qua response validate lỗi thời để tránh trạng thái hợp lệ/không hợp lệ bị ghi đè sai khi thao tác nhanh.
- Verification: frontend `npm run lint` và `npm run build` pass.

## Update 2026-06-26 - Thêm bộ lọc sản phẩm trong form voucher admin

- Form quản lý voucher nay có thanh lọc riêng cho danh sách sản phẩm áp dụng/loại trừ, gồm tìm kiếm theo tên/SKU/thương hiệu, lọc danh mục, lọc thương hiệu và lọc trạng thái.
- Bộ lọc chỉ ảnh hưởng danh sách sản phẩm đang hiển thị để chọn trong form; các sản phẩm đã chọn vẫn được lưu bằng `includeProductIds` và `excludeProductIds` như trước.
- Giới hạn hiển thị tối đa 200 sản phẩm sau khi lọc được giữ lại để tránh danh sách quá dài trong giao diện admin.
- Căn lại ô tìm kiếm sản phẩm bằng label riêng để không bị lệch chiều dọc so với các ô lọc danh mục, thương hiệu và trạng thái.
- Danh sách voucher có thêm tab lọc theo nhóm đối tượng: công khai, khách mới, theo hạng, cấp riêng, mã ẩn và giỏ bỏ quên.
- Trường cấp voucher riêng trong form được đổi nhãn thành `Tài khoản nhận voucher`; khi nhập User ID, form tự chuyển `audienceType` sang `SPECIFIC_USER` để voucher chỉ cấp cho tài khoản đó.
- Form voucher cấp riêng nay chọn được nhiều tài khoản từ danh sách khách hàng có tìm kiếm theo tên/email/số điện thoại, thay vì nhập thủ công một User ID.
- Backend nhận thêm `assignedUserIds`, đồng bộ các tài khoản được cấp vào bảng `user_vouchers` và rule áp dụng voucher kiểm tra người dùng có nằm trong danh sách được cấp riêng.
- Khi mở tab voucher, frontend tải thêm danh sách khách hàng cho bộ chọn tài khoản mà không phụ thuộc từ khóa tìm voucher.
- Bộ chọn tài khoản trong form voucher tải tối đa 100 khách hàng, khớp giới hạn `limit <= 100` của endpoint `/admin/customers` để tránh lỗi `422`.
- Bổ sung nhóm ưu tiên để voucher gần mô hình sàn/app hơn: `displayTitle`, `displayDescription`, `publicTerms`, `applicableChannels` và `applicablePaymentMethods`.
- Form admin có thêm phần nội dung khách hàng nhìn thấy và điều kiện kênh/thanh toán; checkout truyền `paymentMethod` và kênh `WEB` vào rule validate để chặn voucher sai phương thức thanh toán/kênh áp dụng.
- Thêm migration `025_voucher_display_channel_payment.sql` và cập nhật baseline `init_database.sql` cho các cột nội dung/kênh/thanh toán.
- Theo phản hồi UI, bỏ phần chọn `Kênh áp dụng` khỏi form voucher admin; backend vẫn giữ mặc định `WEB` để rule checkout hoạt động ổn định nhưng admin không phải chỉnh trường này.
- Sửa luồng edit form để parse chắc các danh sách JSON như `applicablePaymentMethods`, tránh trường hợp dữ liệu từ DB/API không phải mảng JS thuần làm checkbox phương thức thanh toán không phản ánh đúng.
- Đổi UI chọn phương thức thanh toán từ `MultiPickList` có vùng cuộn sang nhóm nút toggle tĩnh, giúp admin click toàn bộ dòng để chọn/bỏ chọn và tránh lỗi checkbox không đổi trạng thái trong form.
- Sửa storefront checkout: khi bấm áp dụng voucher, frontend gửi thêm `payment_method` và `channel='WEB'` vào `/vouchers/validate`; khi đổi phương thức thanh toán, voucher đang nhập được validate lại để báo lỗi ngay nếu không áp dụng cho phương thức mới.
- Verification: cập nhật voucher test `TESTPAY-0626` sang chỉ `COD` cho kết quả `COD` hợp lệ và `MOMO` bị chặn; cập nhật lại `MOMO/ZALOPAY` cho kết quả `MOMO` hợp lệ và `COD` bị chặn.
- Verification: `npm run lint` trong `frontend` pass.
- Verification: `py_compile` pass cho schema/service/repository/model/router/use case voucher liên quan.
