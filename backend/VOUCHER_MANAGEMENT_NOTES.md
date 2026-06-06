# Voucher Management Notes

## Update 2026-06-05 Voucher Service Repository Split

- Tạo `app/infrastructure/database/repositories/voucher_repo.py` để gom truy vấn DB của module voucher.
- Chuyển SQL khỏi `app/application/services/voucher_service.py`, gồm: danh sách voucher admin, tạo voucher, cập nhật voucher và chuyển voucher sang trạng thái `INACTIVE`.
- `voucher_service.py` hiện giữ vai trò chuẩn hóa payload, điều phối commit và xử lý lỗi `Voucher not found`.
- Kết quả kiểm tra: compile backend bằng `.venv` thành công; import `app.main`, `voucher_service` và `voucher_repo` đều hoạt động; `voucher_service.py` không còn SQL trực tiếp.

## Update 2026-06-05 Tối ưu hóa đóng form voucher và reset trạng thái

- Hàm `resetVoucherForm` tự động tăng `voucherCloseSignal` giúp tắt popup ngay lập tức khi nhấn nút Hủy.
- Hàm `handleVoucherSubmit` khi thành công sẽ tăng `voucherCloseSignal` trước, trì hoãn gọi `resetVoucherForm` (250ms) và trì hoãn alert thành công (100ms) để đóng modal mượt mà và không bị reset form trước khi tắt.

