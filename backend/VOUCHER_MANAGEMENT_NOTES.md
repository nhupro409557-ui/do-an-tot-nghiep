# Voucher Management Notes

## Cập nhật 2026-07-11 - Chỉ mất quyền khách hàng mới sau đơn thành công

- Điều kiện `NEW_CUSTOMER`/`firstOrderOnly` chỉ đếm đơn có trạng thái `COMPLETED` (đã giao hàng thành công).
- Các đơn chờ xử lý, đã xác nhận, đã thanh toán, đang xử lý, đang giao, bị hủy, thanh toán thất bại hoặc hoàn tiền không làm khách mất quyền dùng voucher cho đơn đầu tiên.

## Cập nhật 2026-07-11 - Form voucher hiển thị theo ngữ cảnh

- Form quản trị chỉ hiện bộ chọn khách hàng khi đối tượng là `SPECIFIC_USER`, bộ chọn hạng khi là `MEMBER_TIER`, và ngày đăng ký khi là `NEW_CUSTOMER`.
- Cấu hình điểm đổi/hạn sau khi lưu chỉ hiện với chiến dịch `LOYALTY`; giảm tối đa chỉ hiện với voucher phần trăm.
- Khi đổi đối tượng, form xóa các giá trị chỉ thuộc đối tượng cũ để tránh gửi điều kiện ẩn ngoài ý muốn.
- Các cờ đơn đầu tiên, mã ẩn và giỏ bỏ quên được điều khiển trực tiếp bằng lựa chọn đối tượng, không hiển thị thành checkbox trùng lặp.

## Cập nhật 2026-07-11 - Cấu hình cộng dồn theo loại sản phẩm

- Đổi nhãn `stackable` trên màn hình quản trị thành “Áp dụng cùng Flash Sale” để thể hiện đúng quy tắc đang được kiểm tra.
- Thêm `applyOutsideScope`: khi bật, sản phẩm không nằm trong danh sách sản phẩm/danh mục/thương hiệu được chọn vẫn được tính giá trị và giảm giá; các danh sách loại trừ rõ ràng vẫn được ưu tiên và không được áp dụng.
- Giá trị mặc định của `applyOutsideScope` là `false` để voucher cũ giữ nguyên hành vi.

## Cập nhật 2026-07-11 - Làm rõ giá trị đơn đủ điều kiện

- Thông báo thiếu giá trị tối thiểu tại checkout nêu rõ số tiền cần thêm phải đến từ sản phẩm đủ điều kiện của voucher.
- Giá trị tối thiểu không mặc định tính trên toàn bộ giỏ hàng: sản phẩm ngoài phạm vi áp dụng và sản phẩm Flash Sale khi voucher không cho cộng dồn sẽ không được tính.

## Cập nhật 2026-07-11 - Bộ chọn voucher trực tiếp tại checkout

- Checkout tự tải voucher công khai đang hoạt động/còn hạn và voucher trong ví được cấp riêng cho tài khoản đang đăng nhập.
- Voucher được gộp theo mã, sắp xếp theo hạn gần nhất và chọn độc quyền bằng radio; chọn voucher mới sẽ thay voucher cũ.
- Danh sách công khai loại voucher hết lượt hoặc hết ngân sách. Ví cá nhân chỉ trả voucher `AVAILABLE` có chiến dịch còn hiệu lực, còn lượt và còn ngân sách.
- API ví voucher trả thêm tiêu đề, mô tả, điều khoản, nhóm đối tượng và hạn hiệu lực để checkout hiển thị đầy đủ.
- Bộ chọn đối chiếu `applicablePaymentMethods` với phương thức thanh toán đang chọn; voucher không tương thích bị vô hiệu hóa ngay trên giao diện. Backend tiếp tục trả `VOUCHER_ERR_PAYMENT_METHOD` nếu client cố gửi sai.

## Cập nhật 2026-07-11 - Đổi voucher bằng điểm thưởng

- Voucher có thêm `redemption_points`; giá trị `0` là voucher không yêu cầu đổi điểm.
- Admin cấu hình số điểm cần đổi. Checkout hiển thị nút đổi, kiểm tra số dư và chỉ cho chọn voucher sau khi voucher đã vào ví cá nhân.
- Khi đổi, backend khóa tài khoản, trừ điểm, ghi `loyalty_transactions` loại `REDEEM` và tạo `user_vouchers` trong cùng transaction; yêu cầu lặp không trừ điểm lần hai.
- Voucher yêu cầu điểm luôn bắt buộc có bản ghi ví `AVAILABLE`, kể cả khi không cấu hình hạn theo ngày sau khi nhận; người dùng khác biết mã cũng không thể áp dụng trực tiếp.

## Cập nhật 2026-07-11 - Voucher sinh nhật tự động theo hạng

- Ngày sinh chỉ được chính tài khoản `CUSTOMER` khai báo một lần; backend lưu cột riêng và khóa sau lần lưu đầu. Thay đổi tiếp theo phải qua chăm sóc khách hàng.
- Voucher có cờ `birthday_only` và dùng danh sách `eligible_tiers` hiện có để cấu hình hạng thành viên được nhận.
- Job bảo trì chỉ cấp cho khách có số điện thoại, tài khoản ít nhất 30 ngày, đã có tối thiểu một đơn hợp lệ và có sinh nhật trong ngày hiện tại.
- `birthday_voucher_grants` khóa duy nhất theo khách, voucher và năm sinh nhật, bảo đảm mỗi voucher chỉ được cấp một lần mỗi năm dù job chạy lặp.
- Voucher sinh nhật không xuất hiện trong danh sách công khai và luôn bắt buộc nằm trong ví `AVAILABLE`; biết mã không đủ để sử dụng.
- Hạn voucher dùng `validity_days_after_claim`; nếu admin để `0`, hệ thống mặc định 14 ngày nhưng không vượt quá ngày kết thúc chiến dịch.
- Lịch cấp voucher sinh nhật chạy độc lập mỗi giờ, không phụ thuộc cờ bật/tắt tác vụ bảo trì đơn hàng.
- Voucher sinh nhật bắt buộc chọn ít nhất một hạng thành viên và không được đồng thời yêu cầu đổi điểm; việc đối chiếu hạng không phân biệt chữ hoa/chữ thường.

## Cập nhật 2026-07-13 - Báo trước voucher không áp dụng với Flash Sale

- API voucher công khai và voucher trong ví trả thêm cờ `stackable` để checkout biết voucher có được áp dụng cùng Flash Sale hay không.
- Checkout tính trước giá trị sản phẩm chắc chắn đủ điều kiện; voucher bị vô hiệu hóa kèm lý do khi giỏ chỉ có Flash Sale không được cộng dồn hoặc chưa đạt giá trị tối thiểu.
- Tóm tắt thanh toán không còn hiển thị dòng Flash Sale có số lượng bằng `0`.
- Frontend tách cùng một sản phẩm thành phần giá Flash Sale và phần giá thường khi gọi API kiểm tra voucher. Voucher không cho cộng dồn Flash Sale vẫn được tính trên số lượng thực tế mua theo giá thường, thống nhất với các dòng hàng backend tạo khi checkout.
