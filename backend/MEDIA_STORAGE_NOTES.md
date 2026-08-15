# Ghi chú lưu trữ hình ảnh và video

## Hợp đồng đường dẫn

- Các bảng nghiệp vụ lưu `fileKey` tương đối, không lưu domain, ổ đĩa hoặc tiền tố URL. Ví dụ:
  `products/<uuid>.webp`, `categories/<uuid>.webp` hoặc `content/<uuid>.mp4`.
- API vẫn nhận `fileKey`, URL `/media/...`, `/uploads/...` và URL S3 cũ; tại biên ghi dữ liệu,
  media do hệ thống quản lý được chuẩn hóa về `fileKey`.
- Database có thể tiếp tục chứa URL `/uploads/...` hoặc `/media/...` lịch sử; backend vẫn phục vụ
  và chuẩn hóa các giá trị này để tương thích. Khi bản ghi cũ được chỉnh sửa, giá trị managed media
  sẽ được lưu lại dưới dạng `fileKey`.
- `fileKey` không chứa domain và có dạng `content/<uuid>.mp4`, `products/<uuid>.webp`,
  `reviews/<userId>/<productId>/<uuid>.webp` hoặc `after-sales/...`.
- Không lưu khóa truy cập storage trong source code. Mọi khóa S3 phải là biến môi trường Sensitive.

## Chế độ lưu trữ

- `MEDIA_STORAGE_DRIVER=auto`: dùng S3 khi đủ cấu hình bắt buộc, nếu không thì dùng local.
- `MEDIA_STORAGE_DRIVER=local`: cho phép upload và ghi vào `MEDIA_LOCAL_DIRECTORY`.
- `MEDIA_STORAGE_DRIVER=bundled`: chỉ đọc file đã có trong Git/bản deploy; upload khi runtime trả 409.
- `MEDIA_STORAGE_DRIVER=s3`: upload Admin bằng presigned PUT; các upload qua backend dùng cùng bucket.

`bundled` không phải kho upload động. Muốn thêm file phải chép file vào `backend/uploads`, commit và
triển khai lại. Trên Vercel, `local` không bảo đảm tồn tại sau khi đổi instance hoặc redeploy.

## Cấu hình S3-compatible

```env
MEDIA_STORAGE_DRIVER=s3
MEDIA_LOCAL_DIRECTORY=uploads
MEDIA_PUBLIC_PATH=/media
S3_ENDPOINT_URL=https://<endpoint>
S3_BUCKET=<bucket>
S3_ACCESS_KEY_ID=<sensitive>
S3_SECRET_ACCESS_KEY=<sensitive>
S3_PUBLIC_BASE_URL=https://<public-domain>
S3_REGION=auto
S3_PRESIGN_EXPIRES_SECONDS=900
```

Bucket cần cấu hình CORS cho `PUT` từ domain frontend và cho phép đọc qua `S3_PUBLIC_BASE_URL`.
Tài khoản truy cập chỉ nên có quyền đọc, ghi và xóa object trong đúng bucket của đồ án.

## Chuyển nơi lưu

1. Sao chép object sang kho mới nhưng giữ nguyên `fileKey`.
2. Cập nhật biến môi trường storage.
3. Redeploy backend.
4. Kiểm tra URL `/media/...`; không cần sửa từng banner, sản phẩm hoặc video mới.

Frontend nhận `fileKey` từ upload để lưu vào biểu mẫu và chỉ ghép `${backend}/media/{fileKey}` khi
hiển thị. `media_assets.public_url` là metadata tương thích của registry upload; quan hệ giữa asset
và sản phẩm/danh mục/thương hiệu được đối chiếu bằng `media_assets.file_key`.

File cũ có URL tuyệt đối `/uploads/...` vẫn hoạt động qua route tương thích. Khi có đợt migration dữ
liệu riêng, nên chuyển URL cũ về `/media/{fileKey}` nhưng không bắt buộc cho lần triển khai này.
