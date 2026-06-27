# Change Log

## 2026-06-24 - Dọn tài liệu snapshot cũ và nạp lại CodeGraph

- Xóa thư mục `docs/code-changes/existing-docs/` vì đây là bản sao thủ công của notes gốc, dễ lệch với logic hiện tại.
- Cập nhật `docs/code-changes/README.md` để chỉ dẫn cập nhật trực tiếp notes gốc trong `backend/` hoặc `frontend/`.
- Dọn dữ liệu CodeGraph cũ và nạp lại index mới sau khi loại bỏ tài liệu snapshot.

## 2026-05-30 - Thông báo kết quả duyệt đánh giá

- Hoàn thiện đề xuất trong `REVIEW_MANAGEMENT_NOTES.md`: khi admin đổi review sang `PUBLISHED` hoặc `REJECTED`, backend tạo notification type `review` cho khách hàng nếu review có `user_id`.
- Notification chỉ được tạo khi trạng thái thực sự thay đổi để tránh lặp thông báo khi admin cập nhật ghi chú/phản hồi.
- Notes hiện được cập nhật trực tiếp ở file gốc, không còn duy trì bản sao trong `existing-docs/`.

## 2026-05-30 - Thêm LangGraph cho backend

- Thêm dependency `langgraph>=1.0.0` vào `backend/pyproject.toml`.
- Cài đặt thành công `langgraph 1.2.2` vào môi trường ảo `backend/.venv`.
- Sửa pip trong `.venv` bằng bootstrap pip mới vì pip cũ bị lỗi resolver nội bộ.
- Kiểm tra import và chạy graph tối thiểu thành công với `StateGraph`.

## 2026-05-30 - Chỉnh lại thư viện ảnh kiểu pixel

- Giữ lại tinh thần pixel/mosaic của trang `/images` thay vì grid bằng phẳng.
- Đổi layout từ CSS `columns` masonry sang CSS grid mosaic có `row-span` để các ô cao thấp khác nhau nhưng ít bị hở khoảng trống lớn.
- Backend lọc bỏ các URL ảnh placeholder như `placehold.co` và các URL rỗng khỏi thư viện ảnh.
- Sau khi lọc placeholder, API `/catalog/images` trả 23 sản phẩm có ảnh thật và 63 ảnh.
- Frontend skeleton và image tile được điều chỉnh theo mosaic grid mới.
- Kiểm tra lại `npm run build` thành công và console không có lỗi trên `/images`.

## 2026-05-29 - Catalog, rankings và trang hình ảnh

### Bổ sung nâng cấp modal ảnh và deep-link

- Thêm endpoint `GET /api/v1/catalog/images/resolve/{viewId}` để tìm đúng sản phẩm, ảnh và trang theo liên kết chia sẻ.
- `ImagesPage` có thể mở modal từ `?view=...` ngay cả khi ảnh không nằm trong 30 sản phẩm của trang hiện tại.
- `ImagesModal` tách chế độ ảnh đơn và carousel:
  - sản phẩm ít hơn 3 ảnh hiển thị viewer ảnh lớn dạng tĩnh
  - sản phẩm từ 3 ảnh trở lên mới hiện carousel/360
- Tự động xoay của carousel đã chuyển từ `setInterval` sang `requestAnimationFrame`.
- Modal tôn trọng `prefers-reduced-motion` và tắt tự xoay nếu người dùng giảm chuyển động.

### Mục tiêu

- Giảm tính toán ở frontend bằng cách đưa lọc, sắp xếp, xếp hạng và tổng hợp hình ảnh về backend.
- Sắp xếp thư viện ảnh theo điểm xu hướng thay vì chỉ dựa vào thứ tự dữ liệu frontend.
- Sửa lỗi endpoint `/api/v1/catalog/images` không tồn tại/trả lời sai làm frontend mất danh sách hình ảnh.
- Giảm log lỗi thông báo khi người dùng chưa đăng nhập hoặc phiên đăng nhập đã hết hạn.

### Backend

- Thêm lọc và sắp xếp cho `GET /api/v1/catalog/products`.
- Thêm tham số xếp hạng cho `GET /api/v1/catalog/rankings`.
- Thêm endpoint `GET /api/v1/catalog/images`.
- Backend tính các chỉ số như giá hiện tại, điểm tìm kiếm, điểm xu hướng và tổng số ảnh.
- Endpoint hình ảnh trả về `items`, `categories`, `totalImages`, `totalProducts`, `page`, `limit`, `totalPages`, `hasMore`.

### Frontend

- `ImagesPage` gọi endpoint backend mới thay vì tự tổng hợp toàn bộ sản phẩm trên client.
- `ProductListPage`, `RankingsPage`, `HomePage`, `FlashSale`, `SuggestedProducts` chuyển sang dùng tham số backend để lọc/lay dữ liệu.
- Các service frontend hỗ trợ tham số mới cho catalog, rankings và images.
- `NotificationDropdown` không gọi notifications khi chưa có token đăng nhập.

### Kiểm tra

- `GET /api/v1/catalog/images?page=1&limit=30` trả `200`.
- CORS trả `Access-Control-Allow-Origin: http://localhost:3000`.
- Trang đầu trả 30 sản phẩm, tổng 61 sản phẩm, 3 trang, 158 ảnh.
- `npm run build` frontend thành công.

### Ghi chú tiếp theo

- Nếu dữ liệu ảnh tăng lên rất lớn, nên tối ưu endpoint resolve bằng truy vấn trực tiếp theo product id/image index thay vì dựng lại collection.
- Cân nhắc đổi văn bản "Thư Viện Ảnh 3D" thành "Thư Viện Ảnh Sản Phẩm" nếu phần lớn sản phẩm chỉ có ảnh thường.
