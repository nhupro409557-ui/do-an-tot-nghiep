# Ghi chú quản lý danh mục

## Media danh mục và thương hiệu

- `iconUrl`, `bannerUrl` của danh mục và `logoUrl` của thương hiệu được chuẩn hóa về `fileKey`
  tương đối khi trỏ tới media do hệ thống quản lý.
- Các khóa dùng namespace `categories/` hoặc `brands/`; không phụ thuộc tên, slug hay vị trí thư mục
  cha vật lý. URL ngoài vẫn được giữ nguyên để không làm hỏng dữ liệu tích hợp hợp lệ.
- Giao diện quản trị dựng URL hiển thị qua `resolveImageUrl`, vì database không còn cần lưu domain.
