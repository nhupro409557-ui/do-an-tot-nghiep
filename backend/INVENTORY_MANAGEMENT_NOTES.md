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
- Môi trường không có font Windows (như Vercel) dùng bốn tệp Roboto đã rút gọn và đóng gói trong
  `app/assets/fonts`; cách này tránh lỗi 500, giữ đầy đủ dấu tiếng Việt và không làm vượt giới hạn
  dung lượng hàm serverless.

## Tệp đính kèm nhập kho

- Upload qua khu vực `inventory` dùng module media storage chung và URL ổn định `/media/{fileKey}`.
- Database lưu `inventory/<uuid>.<ext>`; payload URL cũ được chuẩn hóa về `fileKey`. Ảnh QC lồng
  trong JSON cũng áp dụng cùng quy tắc nhưng vẫn giữ chú thích của từng ảnh.
- Chế độ `bundled` chỉ đọc nên không dùng để tải chứng từ mới trực tiếp trên Vercel.
- Khi dùng S3-compatible storage, giữ nguyên giới hạn tài liệu 20 MB và cấp quyền bucket tối thiểu.
