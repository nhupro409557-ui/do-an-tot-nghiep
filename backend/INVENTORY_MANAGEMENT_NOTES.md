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

## Xuất PDF phiếu nhập

- Font Arial tùy chỉnh chỉ được dùng khi đủ cả ba tệp thường, đậm và nghiêng; đồng thời phải
  đăng ký họ font với ReportLab để các thẻ in đậm/in nghiêng trong `Paragraph` được ánh xạ đúng.
- Môi trường không có font Windows (như Vercel) dùng Roboto đóng gói cùng backend thay vì trả về
  tên font `EMVArial-*` chưa đăng ký; cách này tránh lỗi 500 và vẫn giữ đầy đủ dấu tiếng Việt.
