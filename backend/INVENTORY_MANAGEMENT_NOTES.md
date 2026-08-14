# Ghi chú quản lý nhập kho

## Hoàn tất phiếu nhập có thanh toán nhà cung cấp

- Phiếu nhập mua hàng đã thanh toán hoặc có trả trước sẽ tạo chứng từ thanh toán nhà cung cấp
  khi chuyển sang `COMPLETED`.
- Production từng thiếu các cột hardening của bảng `supplier_payments` dù migration
  `103_account_payable_hardening.sql` đã có trong Git, làm bước hoàn tất phiếu trả lỗi 500.
- Trước khi ghi khoản trả trước hoặc truy cập chi tiết công nợ, service kiểm tra schema và bổ
  sung idempotent các cột, bảng `account_payable_adjustments`, ràng buộc và chỉ mục thiết yếu.
  Khóa advisory theo transaction ngăn nhiều request serverless cùng thay đổi schema.
- Luồng cần kiểm tra sau triển khai: `DRAFT` → `APPROVED` → `COMPLETED`, tồn thực tế tăng,
  giá vốn bình quân cập nhật và chứng từ công nợ/thanh toán không bị tạo trùng khi thử lại.
