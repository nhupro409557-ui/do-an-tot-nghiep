# Code Changes Documentation

Thư mục này chỉ lưu tài liệu thay đổi code còn giá trị tham khảo cho dự án.

## Cấu trúc

- `CHANGELOG.md`: nhật ký thay đổi theo ngày, đọc file này trước nếu cần nắm nhanh lịch sử.
- `frontend-backend-catalog-images-2026-05-29.md`: mô tả đợt chuyển tính toán từ frontend về backend và sửa trang `/images`.

## Nguyên tắc cập nhật

- Khi sửa logic quan trọng, thêm một mục mới vào `CHANGELOG.md`.
- Nếu thay đổi lớn, tạo thêm một file riêng theo mẫu `ten-tinh-nang-yyyy-mm-dd.md`.
- Cập nhật trực tiếp notes gốc trong `backend/` hoặc `frontend/`; không duy trì bản sao thủ công vì dễ lệch logic hiện tại.
- Không đưa log, file build, cache, virtual environment hoặc file sinh tự động vào thư mục này.

## Dọn dẹp 2026-06-24

- Đã xóa `existing-docs/` vì đây là bản sao cũ của các file notes gốc và không còn phù hợp với workflow cập nhật trực tiếp notes hiện tại.
