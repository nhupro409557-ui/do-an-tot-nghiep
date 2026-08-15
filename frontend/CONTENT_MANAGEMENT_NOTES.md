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
- Video gắn trực tiếp với sản phẩm nằm ở trường `product.videoUrl`, không đi qua API video riêng.
  `formatProductDemoData` và `formatProductAdminMedia` phải chuẩn hóa trường này cùng ảnh sản phẩm;
  nếu bỏ sót, trang chi tiết sản phẩm trên Vercel vẫn nhận URL localhost và video dừng ở
  `readyState = 0`.
- API thư viện ảnh có cấu trúc phân trang và lồng sản phẩm trong từng ảnh. Phải chuẩn hóa `mainUrl`,
  `images[].url`, `product.videoUrl` và media biến thể bằng `formatProductImageGalleryData` trước khi
  giao cho trang ảnh; nếu không, các ảnh đầu có thể hiển thị nhưng ảnh biến thể phía sau báo
  “Chưa có ảnh”.

## Kho lưu trữ media có thể thay đổi

- Upload mới nhận URL ổn định `/media/{fileKey}` từ backend. Frontend không ghép domain của nhà cung
  cấp storage và không cần biết file đang nằm ở local, Git/bundled hay S3.
- `/uploads/...` tiếp tục được chuẩn hóa để hỗ trợ dữ liệu cũ. Không đổi `resolveImageUrl`,
  `resolveMediaUrl` hoặc `formatVideoMediaData` thành URL của một nhà cung cấp cụ thể.
- Khi backend chạy `bundled`, biểu mẫu upload sẽ nhận lỗi 409 vì bản deploy chỉ đọc. File mới phải
  được thêm vào Git rồi triển khai lại, hoặc chuyển backend sang `local`/`s3`.
