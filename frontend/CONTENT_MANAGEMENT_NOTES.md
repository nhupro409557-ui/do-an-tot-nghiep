# Ghi chú quản lý nội dung

## URL ảnh banner giữa local và production

- Dữ liệu cũ có thể chứa URL dạng `http://localhost:8000/uploads/...` dù tệp ảnh đã được triển
  khai cùng backend.
- Mọi ảnh xem trước trong trang quản trị phải đi qua `resolveImageUrl` để thay host local bằng
  backend đang cấu hình trên môi trường hiện tại.
- Trang chủ và bảng quản lý banner dùng cùng quy tắc này; không sửa trực tiếp dữ liệu lịch sử chỉ
  để đổi domain, vì cùng một dữ liệu còn phải hoạt động ở local và production.

## URL video giữa local và production

- `listVideosPage` phải chuẩn hóa media giống `listVideos`; nếu trả nguyên URL localhost thì thẻ
  video trên Vercel không tải metadata và luôn dừng ở `readyState = 0`.
- Chuẩn hóa video, thumbnail và ảnh bìa tại biên API bằng `formatVideoMediaData`; biểu mẫu quản trị
  vẫn tự chuẩn hóa lần nữa để xem trước an toàn với dữ liệu vừa nhập.
