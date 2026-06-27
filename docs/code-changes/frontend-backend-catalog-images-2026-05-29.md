# Frontend Backend Catalog Images - 2026-05-29

## Tóm tắt

Đợt thay đổi này tập trung vào việc đưa các phép tính catalog từ frontend về backend, đồng thời khôi phục và nâng cấp trang `/images`.

Kết quả chính:

- Frontend không còn phải tự lọc/sắp xếp/tổng hợp danh sách ảnh sản phẩm ở quy mô lớn.
- Backend có endpoint riêng cho thư viện hình ảnh sản phẩm.
- Trang `/images` phân trang 30 sản phẩm mỗi trang.
- Danh sách ảnh được sắp xếp theo điểm xu hướng.
- CORS và lỗi 404/500 của `/catalog/images` đã được xử lý.

## Thay đổi backend

File chính:

- `backend/app/api/v1/routers/catalog.py`

Nội dung:

- Mở rộng `list_products` để nhận tham số lọc và sắp xếp:
  - `q`
  - `category`
  - `brand`
  - `min_price`
  - `max_price`
  - `sort`
  - `limit`
  - `offset`
  - `flash_sale`
  - `featured`
- Mở rộng `list_rankings` để backend tính dữ liệu xếp hạng theo:
  - `period`
  - `criteria`
  - `category`
  - `limit`
- Thêm `list_product_images` cho route `/catalog/images`.
- Thêm các helper tính toán:
  - chuẩn hóa từ khóa tìm kiếm
  - chuẩn hóa danh mục
  - tính điểm khớp từ khóa
  - tính giá hiện tại
  - tính điểm xu hướng xấp xỉ

## Thay đổi frontend

File chính:

- `frontend/src/features/media/pages/ImagesPage.tsx`
- `frontend/src/features/products/pages/ProductListPage.tsx`
- `frontend/src/features/products/pages/RankingsPage.tsx`
- `frontend/src/features/home/pages/HomePage.tsx`
- `frontend/src/features/home/components/FlashSale.tsx`
- `frontend/src/features/products/components/SuggestedProducts.tsx`
- `frontend/src/components/layout/NotificationDropdown.tsx`

Nội dung:

- Các service catalog/product/ranking truyền tham số lọc, sắp xếp và phân trang về backend.
- Service thư viện ảnh gọi `/catalog/images`.
- `ImagesPage` chỉ render dữ liệu backend đã phân trang.
- `NotificationDropdown` bỏ qua request thông báo nếu chưa có token đăng nhập.

## API `/catalog/images`

Request mẫu:

```text
GET /api/v1/catalog/images?page=1&limit=30
```

Response chính:

```json
{
  "items": [],
  "categories": [],
  "totalImages": 158,
  "totalProducts": 61,
  "page": 1,
  "limit": 30,
  "totalPages": 3,
  "hasMore": true
}
```

## Lỗi đã sửa

- Frontend gọi `/api/v1/catalog/images` nhưng backend chưa có route nên bị `404`.
- After adding route, backend từng bị `500` do gọi trực tiếp function FastAPI có mặc định `Query(...)`.
- Khi backend trả `500`, trình duyệt báo lỗi CORS vì phản hồi lỗi không có header mong đợi.
- Đã sửa bằng cách truyền rõ tham số khi endpoint images tải danh sách sản phẩm nội bộ.
- Đã khởi động lại (restart) backend và kiểm tra lại response `200` có CORS đúng.

## Đánh giá hiệu năng

Thay đổi này giúp frontend mượt hơn vì:

- Giảm số sản phẩm/ảnh cần tải và xử lý trong một lần render.
- Giảm việc lọc/sắp xếp lặp lại trên client khi người dùng tìm kiếm, đổi danh mục hoặc đổi trang.
- Backend có thể tối ưu thêm bằng SQL/index/cache mà không cần sửa UI nhiều.

Frontend vẫn có thể tối ưu tiếp:

- Dùng virtualized masonry nếu số lượng ảnh tăng lên hàng trăm/hàng nghin.
- Tối ưu modal 3D để không tự động xoay bằng interval liên tục.
- Chỉ tải trước (preload) ảnh cần thiết trong modal.

## Kiểm tra đã thực hiện

- Backend `/health` hoạt động.
- `GET /api/v1/catalog/images?page=1&limit=30` trả `200`.
- Response có CORS cho `http://localhost:3000`.
- Trang đầu có 30 mục.
- Tổng dữ liệu kiểm tra: 61 sản phẩm, 3 trang, 158 ảnh.
- `npm run build` frontend thành công.

## Việc nên làm tiếp

- Cân nhắc đổi văn bản "Thư Viện Ảnh 3D" thành "Thư Viện Ảnh Sản Phẩm" nếu dữ liệu không phải ảnh 3D thật.

## Bổ sung sau review modal

- Đã thêm API phân giải ảnh bằng `viewId` để liên kết chia sẻ `/images?view=...` mở đúng ảnh ở mọi trang.
- Sản phẩm có ít hơn 3 ảnh hiển thị bộ xem ảnh đơn thay vì carousel 360.
- Sản phẩm có từ 3 ảnh trở lên mới hiện carousel/360.
- Tự động xoay modal đã chuyển sang `requestAnimationFrame`.
- Modal tôn trọng `prefers-reduced-motion` và không tự xoay khi người dùng bật giảm chuyển động.

## Bổ sung layout pixel/mosaic

- Giao diện `/images` tiếp tục giữ phong cách pixel/mosaic với các thẻ ảnh cao thấp khác nhau.
- Thay `columns` masonry bằng CSS grid `auto-rows` + `row-span` để hạn chế khoảng trống lớn giữa các cột.
- Backend không đưa ảnh placeholder vào thư viện ảnh, giúp trang không còn nhiều thẻ "Chưa có ảnh".
- Trang hiện chỉ đếm sản phẩm có ảnh thật trong `totalProducts` và `totalImages`.
- Sau khi sửa, endpoint `/catalog/images?page=1&limit=30` trả 23 sản phẩm và 63 ảnh.

## Việc nên làm tiếp sau bổ sung

- Nếu dữ liệu ảnh tăng lên hàng nghìn sản phẩm, tối ưu endpoint resolve để truy vấn trực tiếp thay vì dựng lại toàn bộ collection.
- Bổ sung nút chuyển ảnh trái/phải cho trường hợp sản phẩm có 2 ảnh nhưng chưa cần carousel 360.
