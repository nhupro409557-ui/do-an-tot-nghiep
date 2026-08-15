# Ghi chú quản lý sản phẩm

## Media sản phẩm

- Sản phẩm và biến thể lưu ảnh/video managed dưới dạng `fileKey`, ví dụ
  `products/<uuid>.webp`; URL `/media/...`, `/uploads/...` cũ được chuẩn hóa tại biên API.
- Không dùng tên, slug sản phẩm, danh mục hoặc thương hiệu trong khóa file vì các giá trị đó có thể
  thay đổi. Quan hệ thực thể được quản lý bằng `media_assets.associated_entity_id`.
- Frontend phải dùng `resolveImageUrl`/`resolveMediaUrl` khi hiển thị khóa tương đối. Media bên ngoài
  không được chấp nhận cho sản phẩm; ảnh tĩnh `/images/...` hiện có vẫn được giữ tương thích.
