# Product Management Notes

## Update 2026-06-16 cleanup stale REV products from inventory

- Dọn dữ liệu local còn sót từ luồng duyệt revision cũ: các sản phẩm SKU `REV-%` trạng thái `MERGED`/`ARCHIVED` không còn được giữ trong bảng `products` như sản phẩm nghiệp vụ hiện hành.
- Trước khi xóa đã xác nhận các bản `REV-%` không có đơn hàng, bundle/accessory, reservation hoặc transaction bán hàng tham chiếu.
- Việc dọn dữ liệu loại bỏ các bản revision khỏi tồn kho khởi tạo để phiếu nhập kho và báo cáo tồn kho chỉ tính sản phẩm thật.
- Lưu ý nghiệp vụ vẫn giữ nguyên theo cập nhật 2026-06-08: lịch sử duyệt revision nằm ở audit trail, không dùng sản phẩm `REV-%` làm bản ghi còn thấy trong catalog/tồn kho.

## Update 2026-06-16 inventory receipt guard for product lifecycle

- Module nhập kho nay kiểm tra vòng đời sản phẩm trước khi cho tạo/sửa phiếu nhập: chỉ sản phẩm `ACTIVE`, chưa xóa và không bị ẩn mới được nhập.
- Sản phẩm đang ngừng kinh doanh (`DISCONTINUED`) hoặc có bản chỉnh sửa `REVISION_DRAFT`/`PENDING` theo `parent_product_id` sẽ bị chặn nhập kho cho đến khi được duyệt hoặc hủy bản chỉnh sửa.
- Ràng buộc này giúp tránh nhập tồn cho dữ liệu sản phẩm chưa ổn định hoặc không còn kinh doanh, đồng bộ với quy tắc revision không được xem như sản phẩm thật.

## Update 2026-06-15 storefront product detail Q&A section

- Thêm component `ProductQuestions` cho trang chi tiết sản phẩm để hiển thị và gửi hỏi đáp sản phẩm bằng các API công khai `/products/{product_id}/questions` đã có.
- Q&A hỗ trợ mô hình 2 tầng: câu hỏi gốc và phản hồi, có optimistic update khi gửi, trạng thái lỗi khi gửi thất bại và thao tác thu hồi nội dung qua API hiện có.
- Nút `Hỏi đáp` trên header chi tiết sản phẩm nay trỏ tới anchor `#product-questions` thay vì khu đánh giá.
- Verification: `npm run lint` trong `frontend` pass.

## Update 2026-06-13 primary and supplemental IMEI support

- Bổ sung mô hình IMEI chính/phụ ở tầng tồn kho: một sản phẩm hoặc biến thể có thể có nhiều IMEI, trong đó đúng một IMEI được đánh dấu chính.
- Khi nhập kho nhiều IMEI, hệ thống lấy IMEI đầu tiên làm IMEI chính nếu sản phẩm/biến thể chưa có IMEI chính; các IMEI còn lại là IMEI bổ sung.
- Bảng tồn kho admin hiển thị `IMEI chính`, số IMEI phụ và tổng trạng thái IMEI để quản trị viên kiểm tra nhanh.
- Migration liên quan: `backend/migrations/061_product_imei_primary.sql`.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-13 product-level serial number policy

- Bổ sung cấu hình `Quản lý serial number` trong form sản phẩm, song song với `Quản lý IMEI`.
- Cấu hình được lưu trong `products.sales_config.serialPolicy` với hai chế độ `CATEGORY` và `MANUAL`; khi `MANUAL`, sản phẩm có thể tự bật/tắt quản lý serial number độc lập với danh mục.
- Sản phẩm hiện có thể rơi vào các tổ hợp: quản lý cả IMEI và serial number, chỉ quản lý IMEI, chỉ quản lý serial number hoặc không quản lý mã định danh.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-10 iPad A16 Wifi video content draft

- Tạo script `backend/scripts/seed_ipad_a16_wifi_video_content.py` để tạo hoặc cập nhật nội dung video nháp cho sản phẩm `iPad A16 Wifi` (SKU `IPADA16`).
- Nội dung video tập trung vào màn hình Liquid Retina 10.9 inch, chip Apple A16 Bionic, Apple Pencil USB-C, Touch ID, camera trước/sau 12MP, loa stereo và các phiên bản A16 Wifi/5G.
- Script gắn video với sản phẩm và các danh mục liên quan qua `content_product_relations` và `content_category_relations`; video được để `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- Đã chạy script trên DB local, tạo/cập nhật video ID `f52656f6-6376-4ba0-b254-04f8c5491719`.
- Verification: `python -m py_compile backend/scripts/seed_ipad_a16_wifi_video_content.py` pass; truy vấn DB xác nhận video có liên kết sản phẩm và 2 liên kết danh mục.

## Update 2026-06-10 Samsung Galaxy S26 Ultra video content draft

- Tạo script `backend/scripts/seed_samsung_galaxy_s26_ultra_video_content.py` để tạo hoặc cập nhật nội dung video nháp cho sản phẩm `Samsung Galaxy S26 Ultra` (SKU `S26U`).
- Nội dung video tập trung vào khung Titanium, màn hình Dynamic AMOLED 2X QHD+ 1-120Hz, Galaxy AI, S Pen tích hợp, camera 200MP/Space Zoom 100x, Snapdragon 8 Elite Gen 5 for Galaxy, Samsung DeX, Knox Security, pin 5000 mAh và sạc nhanh 60W.
- Script gắn video với sản phẩm và các danh mục liên quan qua `content_product_relations` và `content_category_relations`; video được để `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- Đã chạy script trên DB local, tạo/cập nhật video ID `d7ebad55-33ca-42e7-9cb6-2464593a1e68`.
- Verification: `python -m py_compile backend/scripts/seed_samsung_galaxy_s26_ultra_video_content.py` pass; truy vấn DB xác nhận video có liên kết sản phẩm và 2 liên kết danh mục.

## Update 2026-06-10 admin product image deletion persistence

- Sửa lỗi trong màn quản trị sản phẩm: sau khi xóa toàn bộ `Ảnh đại diện chung` và `Bộ ảnh sản phẩm chung`, lưu xong mở lại vẫn thấy ảnh cũ đối với các SKU có ảnh demo.
- Nguyên nhân: `adminProductsApi.adminListProducts` dùng chung `formatProductDemoData`, hàm này tự gán ảnh demo theo SKU và ghi đè dữ liệu `imageUrl`/`images` thật từ backend, làm trạng thái `NULL`/`[]` sau khi xóa bị hiển thị như chưa xóa.
- Thêm `formatProductAdminMedia` để màn admin chỉ chuẩn hóa URL ảnh từ backend, không tự fallback ảnh demo theo SKU. Storefront/public API vẫn giữ `formatProductDemoData`.
- Verification: `npm run lint` trong `frontend` pass.

## Update 2026-06-10 published product image override fix

- Sửa tiếp lỗi sau khi duyệt bản chỉnh sửa: backend đã publish `image_url` và `images` từ `REVISION_DRAFT` sang sản phẩm gốc, nhưng storefront/public API vẫn hiển thị ảnh cũ do `formatProductDemoData` ghi đè ảnh thật bằng bảng ảnh demo theo SKU.
- Xóa bảng fallback ảnh demo theo SKU khỏi `productMedia.ts`; cả admin và public formatter nay chỉ chuẩn hóa URL từ dữ liệu backend. Vì vậy ảnh mới, ảnh đã xóa và gallery rỗng sau duyệt đều được giữ nguyên khi hiển thị.
- Verification: `npm run lint` trong `frontend` pass.

## Update 2026-06-10 batch product image galleries

- Thêm script `backend/scripts/update_batch_product_images.py` để copy ảnh người dùng cung cấp vào `frontend/public/images/products/` theo cấu trúc URL ổn định `cover.*` và `gallery-xx.*`.
- Script nhận diện ảnh đại diện theo tên file có chứa biến thể của `ảnh đại diện`/`ảnh địa diện`; các ảnh còn lại được đưa vào gallery.
- Đã cập nhật `products.image_url`, `products.images`, `product_variants.image_url` và `product_variants.images` cho các sản phẩm: AirPods Pro 2 USB-C, Apple Watch Ultra 2, iPad A16 Wifi, iPad Pro M4 11 inch, MacBook Air M3 13 inch, MacBook Neo 13 inch A18 Pro 2026, Samsung Galaxy A17 5G, Samsung Galaxy A57 5G, Samsung Galaxy S26 và Samsung Galaxy S26 Ultra.
- Các thư mục không phân màu được gắn ảnh dùng chung cho toàn bộ biến thể active; các thư mục phân màu được map theo `color_name` trong database.
- Lưu ý: thư mục `Samsung Galaxy A57 5G/Đen` đã được copy vào public assets nhưng không gắn vào biến thể vì DB hiện không có biến thể active màu Đen cho sản phẩm này.
- Verification: `python -m py_compile backend/scripts/update_batch_product_images.py` pass; chạy script thành công; kiểm tra DB xác nhận 10 sản phẩm có `image_url` mới và các sản phẩm có biến thể active đều không còn biến thể thiếu `image_url`.

## Update 2026-06-10 Samsung Galaxy S26 Ultra color variants update

- Cập nhật tên màu sắc cho Samsung Galaxy S26 Ultra (SKU: `S26U`) theo yêu cầu:
  - Đổi `Đen Titan` (#2f3133) → `Đen Classic`
  - Đổi `Trắng Titan` (#f1f0ee) → `Trắng Classic`
  - Đổi `Xanh Thiên Thanh` (#9ebed2) → `Xanh Sky Blue` (#87ceeb)
  - Thêm mới `Tím Cobalt` (#726b8e)
- Thêm 3 biến thể mới cho màu `Tím Cobalt`:
  - `S26U-CV-256GB`: 12GB RAM, 256GB, giá 33.990.000đ (sale 31.990.000đ)
  - `S26U-CV-512GB`: 12GB RAM, 512GB, giá 37.990.000đ (sale 35.990.000đ)
  - `S26U-CV-1TB`: 16GB RAM, 1TB, giá 44.990.000đ (sale 42.990.000đ)
- Cập nhật `color_name`, `color_code` và `attributes` JSON trong 9 biến thể cũ.
- Tổng biến thể hiện tại: 12 (4 màu × 3 dung lượng).
- Script: `backend/scripts/update_s26u_colors.py`.
- Verification: truy vấn DB xác nhận 12 biến thể active với tên màu đúng.

## Update 2026-06-10 Samsung Galaxy S26 color variants update

- Cập nhật tên màu sắc cho Samsung Galaxy S26 (SKU: `S26`) theo yêu cầu:
  - Đổi `Đen` (#1a1a1a) → `Đen Classic`
  - Đổi `Trắng` (#fdfdfd) → `Trắng Classic`
  - Giữ nguyên `Tím Cobalt` (#726b8e)
  - Thêm mới `Xanh Sky Blue` (#87ceeb)
- Thêm 2 biến thể mới cho màu `Xanh Sky Blue`:
  - `S26-SB-256GB`: 12GB RAM, 256GB, giá 22.990.000đ (sale 21.990.000đ)
  - `S26-SB-512GB`: 12GB RAM, 512GB, giá 26.990.000đ (sale 25.990.000đ)
- Cập nhật `color_name` và `attributes` JSON trong 4 biến thể cũ (BK, WH) để đồng bộ tên mới.
- Cập nhật `products.colors` và `products.options` với 4 màu mới.
- Cập nhật seed data trong `init_database.sql` dòng sản phẩm S26.
- Tổng biến thể hiện tại: 8 (4 màu × 2 dung lượng).
- Script: `backend/scripts/update_s26_colors.py`.
- Verification: truy vấn DB xác nhận 8 biến thể active với tên màu và attributes đúng.

## Update 2026-06-10 OPPO Find X9 Ultra video content draft

- Tạo script `backend/scripts/seed_oppo_find_x9_ultra_video_content.py` để tạo hoặc cập nhật nội dung video nháp cho sản phẩm `OPPO Find X9 Ultra` (SKU `OP-FX9U`).
- Nội dung video tập trung vào mặt lưng da sinh thái, màn hình LTPO AMOLED QHD+ 144Hz, hệ thống camera Hasselblad đa tiêu cự, quay video 8K/4K, pin 7050 mAh, sạc nhanh 100W và chuẩn IP68/IP69.
- Script gắn video với sản phẩm và các danh mục liên quan qua `content_product_relations` và `content_category_relations`; video được để `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- Đã chạy script trên DB local, tạo/cập nhật video ID `ecde02d4-a756-472a-be50-c2d42cd70b27`.
- Verification: `python -m py_compile backend/scripts/seed_oppo_find_x9_ultra_video_content.py` pass; truy vấn DB xác nhận video có liên kết sản phẩm và 2 liên kết danh mục.

## Update 2026-06-10 MacBook Neo A18 Pro video content draft

- Tạo script `backend/scripts/seed_macbook_neo_a18_pro_video_content.py` để tạo hoặc cập nhật nội dung video nháp cho sản phẩm `MacBook Neo 13 inch A18 Pro 2026` (SKU `MBNEOA18P`).
- Nội dung video tập trung vào thiết kế 13 inch gọn nhẹ, màu sắc trẻ trung, chip Apple A18 Pro, màn hình Liquid Retina, pin dài, Magic Keyboard với Touch ID và nhu cầu học tập/văn phòng linh hoạt.
- Script gắn video với sản phẩm và các danh mục liên quan qua `content_product_relations` và `content_category_relations`; video được để `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- Đã chạy script trên DB local, tạo/cập nhật video ID `1bcbcc60-e15c-4aaf-8085-1dd50882fe8b`.
- Verification: `python -m py_compile backend/scripts/seed_macbook_neo_a18_pro_video_content.py` pass; truy vấn DB xác nhận video có liên kết sản phẩm và 2 liên kết danh mục.

## Update 2026-06-10 MacBook Air M3 video content draft

- Tạo script `backend/scripts/seed_macbook_air_m3_video_content.py` để tạo hoặc cập nhật nội dung video nháp cho sản phẩm `MacBook Air M3 13 inch` (SKU `MBAIRM3`).
- Nội dung video tập trung vào thiết kế mỏng nhẹ, chip M3, màn hình Liquid Retina 13.6 inch, thời lượng pin dài và nhu cầu học tập/văn phòng/sáng tạo nhẹ.
- Script gắn video với sản phẩm và các danh mục liên quan qua `content_product_relations` và `content_category_relations`; video được để `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- Đã chạy script trên DB local, tạo/cập nhật video ID `be2b41a3-f30a-4e0d-af16-8232edc84370`.
- Verification: `python -m py_compile backend/scripts/seed_macbook_air_m3_video_content.py` pass; truy vấn DB xác nhận video có liên kết sản phẩm và 2 liên kết danh mục.

## Update 2026-06-08 product comments and Q&A management split

- Tách bảng bình luận hình ảnh sản phẩm khỏi tab `Dịch vụ`; admin có tab riêng `Bình luận & hỏi đáp` để quản lý bình luận vui và hỏi đáp sản phẩm.
- Bổ sung cột `product_image_comments.interaction_type`, mặc định dữ liệu cũ là `IMAGE_COMMENT`; Q&A dùng `PRODUCT_QA` nhưng vẫn chung cơ chế kiểm duyệt/ẩn/thu hồi/phản hồi.
- Thêm API công khai `/products/{product_id}/questions` để liệt kê, gửi và thu hồi hỏi đáp sản phẩm.
- Giữ ràng buộc nghiệp vụ 2 tầng: nếu người dùng hoặc admin trả lời một phản hồi con, backend kéo `parent_id` về câu/cmt gốc, không sinh tầng thứ 3.
- Verification: `npm run lint` trong `frontend` pass; `python -m compileall app` trong `backend` pass.

## Update 2026-06-08 product approval final status parameter fix

- Sửa lỗi duyệt bản chỉnh sửa sản phẩm trả 500 do câu SQL cập nhật sản phẩm gốc dùng `:final_status` nhưng repository chưa truyền tham số này vào đúng lệnh `execute`.
- Bỏ tham số `final_status` thừa khỏi câu insert phụ kiện bán kèm trong cùng nhánh publish revision.
- Verification: `python -m compileall app` trong `backend` pass.

## Update 2026-06-07 admin product submit button layout

- Sửa nút submit dùng chung trong form admin để nhãn `Lưu`/`Thêm` hiển thị đúng Unicode và không bị xuống dòng hoặc co chữ khi vùng hiển thị hẹp.
- `SubmitButtons` nay giữ nguyên dòng bằng `whitespace-nowrap`, không co nút/icon bằng `shrink-0`, giúp nút trong popup quản lý sản phẩm không còn bị vỡ chữ.
- Bổ sung cùng nguyên tắc chống xuống dòng cho nút mở popup `Thêm` trong `CollapsibleSection`.
- Verification: `npm run lint` trong `frontend` thành công.

## Update 2026-06-08 admin product brand selection

- Bỏ ô `Thương hiệu nhập tay` trong form thêm/sửa sản phẩm để tránh lưu thương hiệu không tồn tại trong bảng brands.
- Trường `Thương hiệu` trong form sản phẩm nay là combobox có ô tìm kiếm: bấm vào sẽ sổ danh sách thương hiệu từ database và lọc theo tên/mã.
- Frontend validate bắt buộc `brandId` phải khớp một thương hiệu hiện có; payload gửi backend lấy lại `brand` từ brand được chọn thay vì dùng text tự do trong form.
- Mục tiêu: dữ liệu sản phẩm luôn tham chiếu brand hợp lệ, tránh lệch giữa `products.brand` và `products.brand_id`.

## Update 2026-06-08 admin product category parent-child selection

- Trong form thêm/sửa sản phẩm, khi đã chọn `Danh mục cha`, dropdown `Danh mục con` chỉ hiển thị các danh mục con thuộc cha đó.
- Nếu chưa chọn cha mà admin chọn trực tiếp một danh mục con, frontend tự gán `categoryId` theo `parentId` của danh mục con và cập nhật mã danh mục cha tương ứng.

## Update 2026-06-12 product-level IMEI policy

- Form quản lý sản phẩm có thêm cấu hình `Quản lý IMEI` với hai chế độ: `Theo danh mục` và `Tự chọn cho sản phẩm`.
- Cấu hình được lưu vào `products.sales_config.imeiPolicy`; khi `mode = CATEGORY`, luồng tồn kho giữ nguyên cách xác định theo `categories.inventory_policy`.
- Khi `mode = MANUAL`, backend tồn kho ưu tiên `imeiPolicy.trackImei` của sản phẩm để quyết định phiếu nhập có bắt buộc nhập IMEI hay không.
- Khi đổi danh mục cha sang cha khác, danh mục con đang chọn sẽ được giữ lại chỉ khi vẫn thuộc cha mới; nếu không, form tự clear danh mục con và reset thông số/biến thể theo hành vi đổi danh mục cha hiện có.

## Update 2026-06-08 simplify product draft approval flow

- Đổi nhãn trạng thái sản phẩm `DRAFT` từ `Nháp` thành `Nháp thêm` để phân biệt rõ với `REVISION_DRAFT` là `Nháp chỉnh sửa`.
- Màn danh sách sản phẩm không còn hiển thị nút `Gửi duyệt` cho `DRAFT`/`REVISION_DRAFT`; giữ luồng duyệt trực tiếp bằng nút `Duyệt thẳng` cho Super Admin.
- Duyệt hàng loạt trên frontend nay nhận cả `DRAFT`, `REVISION_DRAFT` và `PENDING`, phù hợp với cơ chế duyệt thẳng đã có ở backend.
- Backend vẫn giữ endpoint gửi duyệt để tương thích API cũ, nhưng admin UI không còn dùng bước trung gian này.

## Update 2026-06-08 split draft workflow from target product status

- Form sản phẩm đổi trường `Trạng thái` thành `Trạng thái sau duyệt` và chỉ cho chọn trạng thái kinh doanh: `Đang bán`, `Tạm ẩn`, `Ngừng kinh doanh`.
- Khi thêm mới, record trong `products.status` luôn là `DRAFT`; khi chỉnh sửa sản phẩm đang bán, record revision vẫn là `REVISION_DRAFT`.
- Trạng thái kinh doanh admin chọn được lưu trong `sales_config.targetProductStatus`; khi duyệt, backend áp dụng giá trị này làm trạng thái cuối của sản phẩm thay vì luôn ép về `ACTIVE`.
- Bảng sản phẩm hiển thị nháp theo dạng `Nháp thêm -> Đang bán` hoặc `Nháp chỉnh sửa -> Tạm ẩn` để phân biệt workflow và trạng thái sau duyệt.
- Cách làm này tách rõ khái niệm mà không cần migration schema ngay: `status` vẫn dùng cho workflow khi còn nháp, còn target nằm trong `sales_config`.

## Update 2026-06-08 attached service delete vs deactivate

- Dịch vụ đi kèm tách rõ thao tác `Xóa`, `Tắt` và `Bật lại`.
- `DELETE /admin/attached-services/{id}` nay xóa cứng dịch vụ chỉ khi chưa có dòng liên kết trong `product_attached_services`; nếu đã được gắn với sản phẩm, backend trả `409` và yêu cầu dùng `Tắt`.
- Thêm endpoint `PATCH /admin/attached-services/{id}/deactivate` để tắt dịch vụ (`is_active = FALSE`) và `PATCH /admin/attached-services/{id}/reactivate` để bật lại.
- UI quản lý dịch vụ hiển thị thao tác tắt/bật lại riêng, còn nút xóa đúng nghĩa là xóa record khi không có ràng buộc.

## Update 2026-06-06 inherited category/brand visibility

- Thêm hai cột `products.hidden_by_category` và `products.hidden_by_brand` để phân biệt sản phẩm bị ẩn do danh mục/thương hiệu với sản phẩm do admin chủ động tắt.
- Khi danh mục hoặc thương hiệu bị ẩn, backend chỉ đánh dấu các sản phẩm đang `ACTIVE` tại thời điểm đó, chuyển chúng sang `INACTIVE` và tắt biến thể để storefront không hiển thị.
- Khi danh mục hoặc thương hiệu bật lại, backend chỉ khôi phục các sản phẩm có cờ ẩn kế thừa tương ứng, không còn bị lý do ẩn khác chặn, và vẫn thỏa điều kiện danh mục/thương hiệu đang bật. Sản phẩm vốn đã `INACTIVE` trước đó không bị bật lại.
- Backend chặn mọi thao tác bật sản phẩm sang `ACTIVE` nếu danh mục, danh mục con hoặc thương hiệu hiện đang ẩn. Admin phải bật danh mục/thương hiệu trước rồi mới bật sản phẩm.
- Tách thao tác sản phẩm thành `Ẩn` và `Xóa`: `POST /admin/products/{id}/hide` chỉ chuyển sản phẩm sang `INACTIVE`, còn `DELETE /admin/products/{id}` giữ rule xóa/xử lý ràng buộc hiện có. Bulk action hỗ trợ thêm `HIDE`, `RESTORE`, `DELETE`.
- Migration liên quan: `backend/migrations/055_product_inherited_visibility.sql`.

## Update 2026-06-06 product reactivate flow

- Thêm endpoint `POST /admin/products/{id}/reactivate` để bật lại sản phẩm từ `INACTIVE` hoặc `DISCONTINUED` về `ACTIVE`, thay vì dùng `PATCH /admin/products/{id}` với payload đầy đủ.
- Khi bật lại sản phẩm từng bị tạm ẩn, backend tự bật lại các biến thể chưa bị xóa/lưu trữ (`deleted_at IS NULL`, status không phải `deleted`/`archived`), tránh lỗi sản phẩm bật lại nhưng biến thể vẫn bị tắt.
- Frontend nút khôi phục/bật lại trong bảng sản phẩm nay hiển thị cho cả `INACTIVE` và `DISCONTINUED`, đồng thời gọi endpoint reactivate riêng.

## Update 2026-06-06 OPPO product image gallery

- Đã copy ảnh người dùng cung cấp cho các dòng OPPO vào `frontend/public/images/products/` với tên thư mục và tên file không dấu để URL ổn định.
- Ảnh đại diện được chọn theo file có tên chứa `ảnh đại diện` hoặc biến thể gõ gần giống trong từng thư mục màu.
- Thêm script `backend/scripts/update_oppo_product_images.py` để cập nhật `products.image_url`, `products.images`, `product_variants.image_url` và `product_variants.images`.
- Đã chạy script trên DB local cho các sản phẩm:
  - `OPPO Reno15 5G`: Trắng Cực Quang, Xanh Chạng Vạng.
  - `OPPO Reno15 F 5G`: Hồng Rực Rỡ, Xanh Dương, Xanh Nhạt.
  - `OPPO Find N6`: Cam Nở Rộ, Titan Ánh Sao.
  - `OPPO Find X9 Ultra`: Cam Hẻm Núi, Nâu Lãnh Nguyên.
  - `OPPO Find X9s`: Cam Hoàng Hôn, Tím Lavender, Xám Bầu Trời.
  - `OPPO Find X8`: Đen Không Gian, Xám Sao Băng.
  - `OPPO Find N3`: gắn ảnh sản phẩm chung từ bộ ảnh đen/vàng vì hiện không có biến thể active.
- Verification: `python -m py_compile backend/scripts/update_oppo_product_images.py` thành công; truy vấn DB xác nhận 7 sản phẩm và các biến thể active đã nhận URL ảnh mới.



#
#

## Update 2026-06-05 product service repository split

- Bắt đầu tách SQL trong `backend/app/application/services/product_service.py` xuống repository.
- Chuyển các truy vấn ít rủi ro sang `backend/app/infrastructure/database/repositories/product_repo.py`: gợi ý sản phẩm, import/export jobs, danh sách export, KPI catalog và audit logs sản phẩm.
- Tiếp tục chuyển các logic liên kết quan hệ xuống `product_repo.py`, bao gồm:
  - Thao tác xóa/chèn liên kết `product_accessories` và `product_attached_services`.
  - Lấy thông tin nhóm dịch vụ đi kèm.
  - Lấy các bản ghi bundle, accessory, và attached service tương ứng tối ưu cho danh sách sản phẩm.
- Chuyển đổi câu truy vấn chính danh sách sản phẩm admin sang `product_repo.py` với hàm `list_admin_product_rows` (xử lý lọc bộ lọc, phân trang, đếm tổng số bản ghi và gom nhóm các biến thể).
- `product_service.py` hiện tại chỉ còn giữ lại các luồng ghi/cập nhật dữ liệu lớn và phức tạp như create/update/duplicate và xử lý từng dòng của import job.

## Update 2026-06-05 backend admin overview refactor

- Tách `backend/app/api/v1/routers/admin_overview.py` theo hướng Controller - Service.
- Router overview hiện chỉ giữ endpoint `/overview`, permission và dependency session.
- Chuyển toàn bộ SQL tổng hợp dashboard sang `backend/app/application/services/overview_service.py`.

## Update 2026-06-05 backend admin products refactor

- Tách `backend/app/api/v1/routers/admin_products.py` theo hướng Controller - Service.
- Router sản phẩm hiện chỉ giữ endpoint, dependency quyền/session, tham số query/upload và chuyển tiếp sang `product_service` hoặc `attached_service`.
- Chuyển các luồng list/suggest/import/export/KPI/audit/create/update/duplicate product sang `backend/app/application/services/product_service.py`.
- Giữ nguyên SQL và transaction trong service ở bước đầu để bảo toàn hành vi của luồng product lớn; repository chi tiết cho product sẽ tiếp tục tách ở vòng sau.

## Update 2026-06-05 backend product approval refactor

- Tách `backend/app/api/v1/routers/admin_product_approvals.py` theo hướng Controller - Service.
- Router duyệt sản phẩm hiện chỉ giữ các endpoint submit, approve, bulk approve, bulk action, archive và delete rồi chuyển tiếp sang `product_approval_service`.
- Chuyển luồng nghiệp vụ duyệt sản phẩm, merge bản revision, archive, deactivate và bulk action sang `backend/app/application/services/product_approval_service.py`.
- Giữ nguyên transaction và SQL trong service ở bước đầu để hạn chế đổi hành vi của luồng merge revision; repository chi tiết cho approval sẽ tách tiếp ở vòng sau.

## Update 2026-06-05 backend product helper refactor

- Tách tiếp `admin_product_utils.py`: Các helper dùng chung của sản phẩm được chuyển sang `backend/app/application/services/product_helper_service.py`.
- SQL phụ trợ cho đồng bộ giá/tồn kho cha và lấy nhãn danh mục/thương hiệu được chuyển sang `backend/app/infrastructure/database/repositories/product_repo.py`.
- Cập nhật `admin_products.py`, `admin_product_approvals.py`, `inventory_service.py` và `product_variant_service.py` để import helper từ tầng application thay vì từ router utils.
- `admin_product_utils.py` giờ chỉ là file tương thích re-export để tránh làm đứt các import cũ ngoài luồng refactor.

## Update 2026-06-05 backend product variant refactor

- Đã hoàn thành tách và cấu trúc lại module quản lý biến thể sản phẩm (`admin_product_variants.py`) theo mô hình Controller - Service - Repository:
  - **Router tinh gọn**: [admin_product_variants.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_product_variants.py) hiện tại chỉ còn endpoint xóa biến thể sản phẩm và chuyển tiếp lời gọi sang lớp Service.
  - **Lớp Service (Logic nghiệp vụ)**: Chuyển toàn bộ logic xử lý nghiệp vụ liên quan sang [product_variant_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/product_variant_service.py), bao gồm:
    - Hàm thêm mới và cập nhật biến thể sản phẩm (`upsert_product_variants`).
    - Hàm xóa biến thể sản phẩm (`delete_product_variant`).
    - Các bước xác thực logic: Kiểm tra trùng lặp mã SKU, kiểm tra cấu hình biến thể mặc định của sản phẩm, kiểm tra tính tương thích giữa thuộc tính biến thể với các tùy chọn (`options`) của sản phẩm cha.
    - Ánh xạ thông số (màu sắc, RAM, ROM, thông số kỹ thuật, hình ảnh, giá cả và số lượng tồn kho).
  - **Lớp Repository (Truy vấn CSDL)**: Chuyển toàn bộ câu lệnh SQL và tương tác DB sang [product_variant_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/product_variant_repo.py), bao gồm:
    - Truy vấn ngữ cảnh sản phẩm.
    - Kiểm tra mã SKU hiện có.
    - Lấy danh sách các biến thể của sản phẩm.
    - Thực hiện các thao tác Insert, Update và Soft-delete biến thể.
    - Tự động cấu hình và chọn biến thể mặc định mới khi cần.
    - Cập nhật lại mã SKU của sản phẩm cha.
  - **Đồng bộ hóa các router liên quan**: Cập nhật [admin_products.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_products.py) để trực tiếp import và gọi `upsert_product_variants` từ lớp Service mới, thay vì import từ router biến thể cũ.
- **Đã kiểm tra kỹ thuật**:
  - Biên dịch thử toàn bộ code backend bằng lệnh `python -m compileall backend/app` thành công (Pass).
  - Kiểm tra việc nạp (import) thành công đối với `app.main`, `admin`, `admin_products`, `admin_product_variants` cùng với service và repo mới lập (Pass).
  - Chưa thực hiện chạy thử nghiệm thao tác ghi nhận trực tiếp vào DB do cần luồng dữ liệu/API hoàn chỉnh để kiểm thử. Về mặt kiến trúc và mã nguồn, cấu trúc quản lý biến thể đã tuân thủ chặt chẽ mô hình phân lớp.

## Update 2026-06-03 React Doctor safe frontend fixes

- Chạy React Doctor ở chế độ tạm thời, không cài package vào project và không thêm hook/config.
- Sửa lỗi hook/runtime không đổi giao diện trong storefront/admin:
  - `ProductDetail.tsx`: đưa effect phím tắt media viewer lên trước nhánh return sớm, thêm cleanup cho timer thông báo thêm vào giỏ và khôi phục overflow khi unmount.
  - `VerifyEmailPage.tsx`: cleanup timer chuyển hướng sau xác nhận email, tránh cập nhật state sau khi rời trang.
  - `CheckoutPage.tsx`: chuyển nhánh giỏ hàng trống xuống sau hook tính phí giao hàng để giữ thứ tự hook ổn định; đồng thời phục hồi chữ tiếng Việt bị lỗi mã hóa trong file.
  - Các tab admin khách hàng/phân quyền/dashboard: đưa các lời gọi quyền ra biến top-level hoặc hàm render thường để tránh gọi hook/component trong JSX/callback.
- Sau sửa, `npm run lint` pass và React Doctor giảm Bugs errors từ 29 xuống 20; phần còn lại là nhóm cảnh báo lớn về state sync trong luồng catalog/data loading, cần refactor riêng để tránh thay đổi hành vi tải dữ liệu ngoài ý muốn.

## Update 2026-06-03 React Doctor Bugs errors cleanup

- Tiếp tục xử lý các lỗi nhóm Bugs còn lại mà không đổi layout/giao diện:
  - `useCatalog.ts`: chốt option ranked featured ở lần mount đầu, thêm cleanup cho async load catalog.
  - `ImagesModal.tsx` và `ReelsModal.tsx`: tách outer/inner modal để remount nội dung khi mở, thay vì reset nhiều state trong effect; thêm cleanup URL query khi đóng modal.
  - `ProductReviews.tsx`: remount theo `productId + user`, thêm cleanup async và đưa prefill review hiện có vào callback eligibility thay vì sync form bằng effect riêng.
  - `VietnamAddressSelector.tsx`: bỏ state `wards`, derive danh sách phường/xã từ `provinces + provinceId` bằng `useMemo`; sửa một số nhãn tiếng Việt có dấu.
  - `ProductDetail.tsx`: chuyển reset lựa chọn sản phẩm/media sang cập nhật có điều kiện theo `product.id`/`activeVariant.id`; effect Swiper chỉ còn điều khiển slide, không set state React.
- Verification: `npm run lint` pass; React Doctor báo Bugs còn `0 errors`, chỉ còn optional warnings.

## Update 2026-06-03 revision variant specs persistence

- Sửa lỗi khi chỉnh sửa sản phẩm đang bán để tạo `REVISION_DRAFT`: backend `upsert_product_variants` nay lưu `product_variants.specs` từ `var.specs` do frontend gửi lên, thay vì ghi đè bằng `attributes`. Nhờ vậy các thông số kỹ thuật được chọn làm biến thể như RAM/ROM/cấu hình giữ đúng thay đổi trong bản nháp chỉnh sửa.
- `attributes` vẫn được dùng riêng cho hợp đồng `options` và validate lựa chọn biến thể; `specs` giữ key kỹ thuật của form admin để khi mở lại bản nháp không bị đọc nhầm về dữ liệu cũ hoặc nhãn hiển thị.

## Update 2026-06-03 admin product form controlled popup close

- Popup thêm/sửa sản phẩm trên admin nay có trạng thái mở/đóng riêng (`productFormOpen`) thay vì chỉ dựa vào `closeSignal`; sau khi thêm hoặc lưu thành công, popup được đóng ngay trước khi reset form để tránh hiện tượng modal vẫn mở nhưng nội dung bị nhảy về form thêm mới/trống.
- `CollapsibleSection` hỗ trợ thêm chế độ controlled qua `open` và `onOpenChange`, trong khi vẫn giữ tương thích với các popup khác đang dùng trạng thái nội bộ và `closeSignal`.

## Update 2026-06-03 admin merged revision action guard (legacy)

- Ghi chú lịch sử: trước ngày 2026-06-08, bản chỉnh sửa sản phẩm sau khi duyệt và merge vào sản phẩm gốc có trạng thái `MERGED`.
- Cơ chế này đã được thay thế: sau khi publish `REVISION_DRAFT`, backend ghi audit `REVISION_PUBLISHED` rồi xóa record revision khỏi bảng `products`, không tạo thêm dòng `MERGED` mới.
- Các thao tác gửi duyệt, duyệt, khôi phục và lưu trữ trong `useAdminProductsLogic.ts` được bọc lỗi để admin nhận thông báo rõ ràng, không còn lỗi promise chưa bắt trên console.
- Backend vẫn từ chối cập nhật/xóa trực tiếp các record `MERGED` cũ còn tồn tại, nhưng sản phẩm `ARCHIVED` hiện được phép khôi phục qua endpoint reactivate chuẩn nếu không bị blocker danh mục/thương hiệu.
- Khi tạo `REVISION_DRAFT`, `upsert_product_variants` không còn đồng bộ `products.sku` của bản revision theo SKU biến thể mặc định, tránh lỗi trùng unique SKU với sản phẩm/biến thể đang active.
- Sau khi chỉnh sửa sản phẩm đang bán, frontend thông báo rõ là đã tạo bản chỉnh sửa cần duyệt, tự chuyển bộ lọc danh sách sang `REVISION_DRAFT` và đóng form trước khi reset để không còn cảm giác popup bị đổi sang form thêm mới.
- Backend `extract_product_metadata` nay nhận đúng các key frontend gửi trong `specifications`: `_variantSpecKeys`, `_accessoryOffers`, `_attachedServices`, `_warrantyPolicy`, rồi lưu vào `sales_config` chuẩn. Frontend cũng fallback đọc các key cũ này từ `specifications` khi mở bản nháp chỉnh sửa đã tạo trước đó.
- Sửa thứ tự đóng popup sản phẩm: `closeSignal` dùng layout effect và `handleProductSubmit` chờ một frame trước khi reset form, tránh modal còn mở nhưng nội dung đã nhảy sang form thêm mới.
- Sửa lưu/mở lại ROM biến thể trong bản chỉnh sửa: frontend chuẩn hóa key biến thể từ label tiếng Việt như `Bộ nhớ trong` về key `storage`, backend validate option/attribute bằng Unicode normalized và fallback map `Bộ nhớ trong`/`ROM` vào cột `product_variants.storage`. Đã test tạo revision tạm với ROM `999GB`, DB lưu đúng `storage = 999GB`, rồi xóa revision test.

## Update 2026-06-03 iPhone 17 Pro Max uses iPhone 17 Pro images

- Theo y?u c?u, d?ng `iPhone 17 Pro Max` d?ng chung b? ?nh t? `iPhone 17 Pro` t?i `frontend/public/images/products/iphone-17-pro`.
- Th?m script `backend/scripts/update_iphone_17_pro_max_images_from_pro.py` ?? c?p nh?t `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho d?ng `iPhone 17 Pro Max`.
- ?? ch?y script tr?n DB local cho SKU ch?nh `IP17PM` v? b?n l?u tr? `REV-D3490FAAC5`.
- C?c m?u ???c g?n t??ng ?ng: B?c d?ng `silver`, Cam V? Tr? d?ng `cosmic-orange`, Xanh S?u d?ng `deep-blue`; c?c bi?n th? Pro Max thi?u m?u ???c chuy?n v? Cam V? Tr? ?? kh?ng c?n d?ng ?nh placeholder.

## Update 2026-06-03 storefront shared product video

- Trang chi tiết sản phẩm nay ưu tiên hiển thị video dùng chung ở đầu gallery nếu sản phẩm có `videoUrl`, giống cách CellphoneS đặt thumbnail "Video" làm media đầu tiên.
- Khi gallery mở bằng video, ảnh dùng cho giỏ hàng vẫn fallback sang ảnh sản phẩm hoặc ảnh biến thể đầu tiên để không lưu URL video làm ảnh sản phẩm trong cart.

## Update 2026-06-03 iPhone 17 Pro image gallery

- ?? copy ?nh ng??i d?ng cung c?p t? th? m?c `iphone 17 pro` v?o `frontend/public/images/products/iphone-17-pro`.
- ?nh ???c chia theo m?u:
  - `silver`: B?c, g?m ?nh ??i di?n v? 7 ?nh gallery.
  - `cosmic-orange`: Cam V? Tr?, g?m ?nh ??i di?n v? 7 ?nh gallery.
  - `deep-blue`: Xanh S?u, g?m ?nh ??i di?n v? 4 ?nh gallery.
  - `common`: 7 ?nh d?ng chung cho trang chi ti?t s?n ph?m.
- Th?m script `backend/scripts/update_iphone_17_pro_images.py` ?? c?p nh?t ?nh s?n ph?m v? ?nh bi?n th? cho d?ng `iPhone 17 Pro`.
- ?? ch?y script tr?n DB local cho SKU ch?nh `IP17P` v? hai b?n l?u tr? `REV-*`; kh?ng c?p nh?t `iPhone 17` th??ng ho?c `iPhone 17 Pro Max`.

## Update 2026-06-03 iPhone 17 image gallery

- ?? copy ?nh ng??i d?ng cung c?p t? th? m?c `iphone 17` v?o `frontend/public/images/products/iphone-17`.
- ?nh ???c chia theo m?u:
  - `black`: ?en, g?m ?nh ??i di?n v? 2 ?nh gallery.
  - `white`: Tr?ng, g?m ?nh ??i di?n.
  - `mist-blue`: Xanh S??ng M?, g?m ?nh ??i di?n v? 1 ?nh gallery.
  - `common`: 9 ?nh d?ng chung cho trang chi ti?t s?n ph?m.
- Th?m script `backend/scripts/update_iphone_17_images.py` ?? c?p nh?t `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images`.
- ?? ch?y script tr?n DB local cho hai b?n `iPhone 17` ?ang t?n t?i: SKU ch?nh `IP17` v? b?n nh?p ch?nh s?a `IP17-BK-256GB`; kh?ng c?p nh?t c?c d?ng `iPhone 17 Pro` ho?c `iPhone 17 Pro Max`.

## Update 2026-06-03 Revert image card UI

- Đã trả lại giao diện thẻ ảnh sản phẩm trên `frontend/src/features/media/pages/ImagesPage.tsx` về kiểu cũ theo yêu cầu: khung ảnh gradient, nhãn nổi, khu thông tin dưới ảnh và nút mua nhỏ hiện theo hover.

## Update 2026-06-03 Product image card UI

- Chỉnh lại thẻ ảnh sản phẩm trên trang thư viện ảnh (`frontend/src/features/media/pages/ImagesPage.tsx`) để ảnh sản phẩm hiển thị thoáng hơn, giảm khoảng trắng xấu quanh ảnh cao/dọc.
- Làm phần thông tin dưới ảnh gọn hơn: tên sản phẩm, giá, lượt xem/lượt thích và nút "Xem sản phẩm" hiển thị cố định thay vì ẩn khi hover.
- Nhãn danh mục và số lượng ảnh được thu gọn để không lấn vào ảnh sản phẩm.

## Update 2026-05-22

- Giu lai cac thong tin chinh cua san pham nhu cu.
- Hinh anh dai dien chung la anh duy nhat o cap san pham.
- Bo phan gallery hinh anh chung trong form admin de tranh trung voi hinh anh theo bien the.
- Video san pham la video dung chung cho toan bo san pham, luu o cap `products.video_url`.
- Form admin bo sung preview cho:
  - anh dai dien chung
  - video dung chung
  - hinh anh bien the theo mau sac
- Bien the uu tien truc mau sac truoc, sau do moi den thong so ky thuat va gia.
- Mua kem giam gia:
  - admin chon san pham mua kem tu danh sach san pham
  - cau hinh giam theo `FIXED` hoac `PERCENT`
  - cau hinh so luong toi da duoc giam gia theo tung san pham mua kem
  - cau hinh duoc luu trong `products.sales_config.accessoryOffers`
  - bang `product_accessories` tiep tuc giu vai tro quan he de tra cuu nhanh
- Cau truc `sales_config.accessoryOffers`:

```json
[
  {
    "productId": "uuid-san-pham-mua-kem",
    "discountType": "PERCENT",
    "discountValue": 25,
    "maxQuantity": 2
  }
]
```

- Quy tac tinh gia o checkout can ap dung:
  - chi giam cho so luong nam trong `maxQuantity`
  - so luong vuot muc giam gia se tinh theo gia goc
  - san pham mua kem chi duoc giam khi cung hoa don voi san pham chinh

## Ghi chu pham vi

- Ban cap nhat nay hoan thien phan quan tri san pham va API luu cau hinh.
- Neu can ap dung gia mua kem tren gio hang/checkout, tiep tuc doc file nay truoc khi sua logic don hang.

## Update 2026-05-23

- Bo phan SEO khoi form quan tri san pham; product SEO metadata cu van duoc doc neu ton tai nhung admin khong nhap moi o man hinh nay.
- San pham ban kem tiep tuc luu trong `products.sales_config.accessoryOffers`, nhung UI chon bang bo loc danh muc, thuong hieu va tim kiem san pham.
- UI cho phep chon tat ca san pham trong ket qua loc hien tai; moi san pham mua kem co gia/uu dai do admin set rieng bang `discountType`, `discountValue`, `maxQuantity`.
- Bien the duoc sap xep va nhap theo mau sac la truc chinh. Cac cau hinh khac nhau cua cung mau van nam trong danh sach bien the nhung UI uu tien nhom theo mau de admin de nhap hon.
- SKU bien the co the do admin nhap; neu de trong thi frontend/backend tu tao theo viet tat ten san pham + viet tat mau + so thu tu, vi du `IPM-DT-01`.
- Dich vu di kem da co nen du lieu qua `attached_services` va `product_attached_services`:
  - `PRODUCT_SERVICE`: bao hanh/mo rong bao hanh gan voi san pham/IMEI, tinh gia theo tien co dinh, phan tram, hoac dinh muc.
  - `SUPPORT_SERVICE`: lap dat, ve sinh, ho tro... do admin set gia co dinh hoac cau hinh rieng.
- Khi lam tiep gio hang/checkout, can xu ly rule moi: trong cung mot `attribute_group` cua dich vu san pham, nguoi mua chi duoc chon mot lua chon.
- Admin da co man `Dich vu` de tao/sua/an danh sach dich vu di kem.
- Form san pham da co khu `Dich vu di kem`, cho chon nhieu dich vu tu danh sach da tao va dat `overridePrice` rieng theo san pham neu can.
- Product form co them `sales_config.warrantyPolicy` de san pham co the:
  - lay mac dinh bao hanh/1 doi 1 tu danh muc
  - hoac admin override thang bao hanh va so ngay 1 doi 1 rieng theo san pham
- Khi chon danh muc cha/con, neu san pham dang bat "theo danh muc" thi UI tu nap `warrantyPolicy` tu danh muc uu tien cao nhat.
- Khi chon dich vu di kem trong product form, UI chan viec chon hai dich vu cung `serviceType + attributeGroup`; backend cung bo qua dich vu trung nhom khi dong bo bang `product_attached_services`.
- Da them `AGENTS.md` vao goc project de ghi nho cach dung CodeGraph va cac file notes can doc truoc khi sua module nay.

## Update 2026-05-23 bo sung

- Form san pham da bo o nhap tay `Combo/bundle: SKU/ID`; luong ban kem chuyen sang chon san pham tu danh sach loc.
- Khu san pham mua kem hien danh sach chon ngay sau khi admin loc theo danh muc, thuong hieu hoac tim theo ten/SKU; co nut chon tat ca ket qua dang loc.
- Khu dich vu di kem trong form san pham khong cho nhap tay. Admin loc/chon tu danh sach `attached_services` da tao theo loai dich vu, nhom dich vu va tu khoa.
- Khi chon dich vu di kem, UI hien loai dich vu, nhom, thoi han bao hanh va gia de admin phan biet cac goi 3/6/9/12/18/24/36 thang.
- Danh sach san pham mua kem trong form admin hien tu du lieu san pham da load san, khong phu thuoc API suggest nen loc danh muc/thuong hieu se co ket qua ngay neu du lieu tren bang dang co san pham phu hop.
- Popup them/sua san pham, danh muc, thuong hieu, voucher va noi dung co `forceOpenKey` theo id dang sua de khi chuyen sang item khac popup tu mo lai, tranh phai reload trang.
- Popup them/sua cung goi ham reset form khi dong, de admin co the dong roi bam sua lai dung cung item ma khong can reload trang.

## Update 2026-05-23 chinh sach dich vu moi

- Danh sach dich vu bao hanh mo rong da cap nhat theo chinh sach ElectroMart Viet Nam:
  - 1 doi 1 VIP
  - Roi vo - roi nuoc
  - S24+
- Cac goi bao hanh nay khong con tinh theo phan tram co dinh; da chuyen sang `TIERED_AMOUNT` va luu bieu phi trong `attached_services.metadata.priceTiers`.
- Product form va bang dich vu hien thi goi `TIERED_AMOUNT` la "Theo bieu phi" de admin khong hieu nham la gia 0 dong.
- UI them/sua dich vu bo sung nhom `ACCIDENTAL_DAMAGE` cho goi roi vo - roi nuoc.

## Update 2026-05-23 khoa gia dich vu theo chinh sach

- Product form da bo o `overridePrice` trong khu dich vu di kem; san pham chi gan ma goi dich vu, khong nhap gia rieng theo san pham.
- Backend bo qua gia override khi dong bo `product_attached_services` va luon luu `override_price = NULL`.
- Gia cac goi bao hanh/dich vu san pham lay theo chinh sach trong `attached_services`, dac biet cac goi `PRODUCT_SERVICE` dung `TIERED_AMOUNT` va `metadata.priceTiers`.

## Update 2026-05-30 product view analytics

- Luot xem san pham khong con duoc cong ngay khi mo trang chi tiet.
- Frontend dung `useViewTracker` gui heartbeat khi tab dang active, kem `activeSeconds`, `scrollDepth`, `sessionId` va `deviceId`.
- Backend endpoint `POST /api/v1/catalog/products/{product_id}/view` chi ghi `product_view_events` khi du 30 giay active hoac scroll toi thieu 50%.
- Khi Redis kha dung, backend tich luy state theo key `product_view:state:{product_id}:{identity}` va khoa trung 24 gio bang `product_view:valid:{product_id}:{identity}`.
- Neu Redis khong kha dung trong moi truong local, backend fallback sang rule DB: chi ghi khi heartbeat da dat nguong va van dedupe trong 24 gio theo device/session/IP/user-agent.
- Bang `product_view_events` co them `device_id`, `duration_seconds`, `scroll_depth`; rankings lay `viewCount` tu valid event thay vi du lieu admin/gia lap.

## Update 2026-05-30 admin upload refactor

- Admin upload routes duoc tach khoi `backend/app/api/v1/routers/admin.py` sang `backend/app/api/v1/routers/admin_uploads.py`.
- Endpoint upload local tiep tuc giu URL cu `/api/v1/admin/uploads/local/{folder}/{filename}` nhung nay yeu cau quyen `product:create`, dong bo voi buoc tao presigned upload.

## Update 2026-05-30 frontend refactor

- Da tach phan logic va state quan ly san pham ra khoi `useAdminLogic.ts` sang hook rieng biet `useAdminProductsLogic.ts` de lam sach va modul hoa frontend code.

## Update 2026-05-30 flat variant completion

- Product create/update/revision now persists `products.options` so variant `attributes` can be validated against the saved option contract.
- Simple products without explicit variants use the product-level price, discount price, and stock to create the default variant instead of always creating a zero-price/zero-stock variant.
- Publishing a product revision now copies `options` and variant metadata (`compare_at_price`, `is_default`, `status`, `attributes`, `deleted_at`, `stock_quantity`) back to the parent product.
- Duplicating a product now preserves `options` and active variant metadata while generating new SKUs.
- Parent product price and stock are synchronized from active, non-deleted variants.
- Catalog product detail now exposes `options`, variant `attributes`, `isDefault`, `status`, and `compareAtPrice`.
- Admin product form validates duplicate SKU, one default variant, non-negative price/stock, and option/attribute consistency before submit.

## Update 2026-05-30 flat variants & default variant refactor

- Thong nhat module quan ly san pham va bien the:
  - Moi san pham co it nhat mot bien thể.
  - San pham don gian khong co lua chon duoc tu dong tao mot default variant trong DB.
  - SKU cua bien the dang active la duy nhat trong toan he thong, nhung SKU cua bien the da bi xoa mem co the duoc tai su dung.
  - Bat buoc moi san pham chi co dung mot bien the mac dinh (`is_default = true`) tai moi thoi diem.
  - Ho tro xoa mem bien the (`deleted_at IS NULL`). Ngang chan xoa bien the cuoi cung cua san pham (`CANNOT_DELETE_LAST_VARIANT`). Tu dong gan bien the hoat dong tiep theo lam mac dinh neu bien the mac dinh bi xoa.
  - Bo loc `deleted_at IS NULL` duoc ap dung dong bo o storefront catalog (`catalog.py`), quan ly ton kho (`admin_inventory.py`), va quan ly san pham (`admin_products.py`).

## Update 2026-05-31 admin product pagination

- Admin product list now loads 20 products per page from `useAdminLogic.ts`.
- `GET /api/v1/admin/products` keeps the default `limit=20` and returns paged `{ items, totalRecords, totalPages, page, limit }` when `page` is provided.
- Fixed PostgreSQL ambiguous null parameters in admin product filters by casting `status_filter` to `TEXT` and `category_id`/`brand_id` to `UUID` in `admin_products.py`.
- Product admin list no longer falls back to the storefront catalog list when the paged admin endpoint fails; this prevents a hidden API error from showing all products as one page.
- Verification: direct backend pagination query returns 20 rows for page 1, and frontend TypeScript check passes.

## Update 2026-05-31 revision draft discard

- Editing an existing active product creates a separate `REVISION_DRAFT`; this draft must be discardable without changing the parent product.
- `DELETE /api/v1/admin/products/{id}` now detects `REVISION_DRAFT` with `parent_product_id` and discards only that revision:
  - deletes relation rows owned by the revision in `product_bundles`, `product_accessories`, and `product_attached_services`
  - soft-deletes revision variants
  - marks the revision product `ARCHIVED` and sets `deleted_at`
- `POST /api/v1/admin/products/{id}/archive` now accepts `REVISION_DRAFT`.
- Admin product UI now allows `REVISION_DRAFT` to be sent for approval or archived, but does not show the restore action for revision drafts.
- Verification: frontend TypeScript check and backend `py_compile` pass; backend server restarted on port 8000.

## Update 2026-05-31 smart revision merge

- Publishing a product revision no longer deletes all live variants and reinserts variants from the revision.
- Added delta merge by SKU in `admin_products.py`:
  - revision variant with matching live SKU updates live variant descriptive fields, price, media, specs, attributes, status, and default flag
  - live variant stock is preserved during updates; stock remains controlled by inventory/order flows
  - revision variant with new SKU inserts a new live variant
  - live variant missing from the revision is soft-disabled instead of physically deleted
- Missing live variants with inventory history become `inactive`; variants without inventory history become `archived`.
- Ghi chú lịch sử: trước ngày 2026-06-08, revision records từng trở thành `MERGED` sau khi publish. Cơ chế mới không tạo `MERGED`; audit trail lưu snapshot trước/sau và record revision bị xóa khỏi `products` sau khi áp dụng.
- Fixed revision variant creation so draft variants receive new IDs instead of reusing live variant IDs.
- Verification: backend `py_compile`, frontend TypeScript check, schema check for inventory history, and backend restart on port 8000 pass.

## Update 2026-05-31 complete enterprise revision design

- Added migration `047_enterprise_product_revision_merge.sql`.
- `product_variants.parent_variant_id` stores durable lineage from revision variants to live variants; SKU remains a fallback matching key.
- `order_items.variant_id` stores the exact sold variant for audit, restock, and safe variant deactivation decisions.
- Commerce order creation now writes `variant_id` to `order_items` when checkout provides a variant.
- Order restock now prefers `order_items.variant_id` and only falls back to inventory adjustment logs for old orders.
- Revision merge now matches live variants by `parent_variant_id` first, then SKU.
- Missing live variants now check both `order_items.variant_id` and `inventory_adjustment_logs.variant_id`; variants with history become `inactive`, otherwise `archived`.
- Local database has been migrated with the new columns and indexes.
- Verification: backend `py_compile`, frontend TypeScript check, schema verification, and backend restart on port 8000 pass.

## Update 2026-05-31 archived product visibility

- Admin product list now hides `ARCHIVED` products by default, the same way it hides `MERGED` revision history.
- `ARCHIVED` products remain in the database for audit/safety, but only appear when the admin explicitly filters status `ARCHIVED`.
- Verification: backend `py_compile`, frontend TypeScript check, and backend restart on port 8000 pass.

## Update 2026-05-31 admin product submit errors

- Fixed product create/update failing when checking category migration status by importing SQLAlchemy `bindparam` in `admin_categories.py`.
- Admin product add/edit now catches API errors during submit and shows a clear alert instead of silently leaving the form unchanged.
- FastAPI validation details returned as JSON are formatted into readable lines before showing to the admin.

## Update 2026-05-31 admin product action cleanup

- Bảng sản phẩm admin đã bỏ các nút phụ `Preview` và `Sao chép` khỏi cột thao tác để giao diện gọn hơn.
- Cột thao tác chỉ giữ các hành động vận hành chính theo trạng thái sản phẩm: sửa, xóa/ẩn, khôi phục nếu có, gửi duyệt, duyệt và lưu trữ.

## Update 2026-05-31 direct approval bypass for super admin

- Khi tài khoản đăng nhập có vai trò `SUPER_ADMIN`, cho phép duyệt thẳng (Duyệt ngay) sản phẩm từ trạng thái `DRAFT` hoặc `REVISION_DRAFT` mà không cần đi qua bước trung gian `PENDING_REVIEW` (gửi duyệt).
- API backend cập nhật các route `/products/{product_id}/approve`, `/products/bulk-approve` và `/products/bulk-action` để tự động kiểm tra `role_code` của user và cho phép trạng thái `DRAFT`/`REVISION_DRAFT` được duyệt thẳng thành `ACTIVE` đối với Super Admin.
- Frontend hiển thị thêm nút "Duyệt thẳng" bên cạnh nút "Gửi duyệt" trên bảng danh sách sản phẩm dành riêng cho Super Admin.

## Update 2026-05-31 fix duplicate SKU check query

- Sửa lỗi `AmbiguousParameterError: could not determine data type of parameter $3` khi kiểm tra trùng lặp SKU trong cơ sở dữ liệu khi cập nhật hoặc thêm sản phẩm.
- Giải pháp: Thực hiện ép kiểu tường minh `CAST(:parent_product_id AS UUID)` trong câu truy vấn `sku_query` của hàm `upsert_product_variants` tại file `admin_products.py`.

## Update 2026-05-31 fix admin products filter logic

- Khắc phục lỗi bộ lọc quản lý sản phẩm Admin (Danh mục và Thương hiệu) không hoạt động do vòng lặp phụ thuộc state và closure lỗi thời (stale state) khi gọi API.
- Giải pháp: Di chuyển các state `productCategoryFilter` và `productBrandFilter` quay trở lại hook cha `useAdminLogic.ts` để quản lý tập trung và đảm bảo reactivity. Truyền các state này cùng setter của chúng xuống hook con `useAdminProductsLogic.ts` để đồng bộ hóa luồng dữ liệu.

## Update 2026-06-01 admin form completion feedback

- Sau khi thêm hoặc chỉnh sửa sản phẩm thành công, popup sản phẩm tự đóng thay vì reset về trạng thái "Thêm sản phẩm mới" ngay trong popup đang mở.
- Admin nhận thông báo thành công rõ ràng sau khi thêm hoặc lưu thay đổi sản phẩm.
- Cùng đợt này, các popup quản trị dùng chung `CollapsibleSection` cho thương hiệu và voucher cũng được đóng bằng `closeSignal` sau khi lưu thành công để giữ hành vi nhất quán.

## Update 2026-06-01 product and variant galleries

- Form quản trị sản phẩm đã có lại phần tải "Bộ ảnh sản phẩm chung" và gửi dữ liệu vào `products.images`; sản phẩm đơn giản không có biến thể hiển thị được gallery chung thay vì chỉ có ảnh đại diện.
- Biến thể tách rõ `imageUrl` là ảnh đại diện biến thể và `images` là bộ ảnh riêng của biến thể.
- Thêm migration `049_product_variant_images.sql` để bổ sung cột `product_variants.images`.
- API admin/catalog trả `images` cho từng biến thể; trang chi tiết sản phẩm gom cả ảnh đại diện biến thể và bộ ảnh biến thể vào gallery hiển thị.
## Update 2026-06-01 storefront product detail scroll

- Ghi chú: bố cục này đã được thay bằng bản sticky ở mục kế tiếp để giảm khoảng trắng tốt hơn.
- Trang chi tiết sản phẩm trên màn hình lớn dùng hai cột độc lập cho khu ảnh/thông số nhanh và khu giá/tuỳ chọn mua hàng.
- Mỗi cột chỉ giới hạn chiều cao theo phần nhìn thấy hợp lý, không ép chiều cao khi nội dung ngắn để tránh tạo khoảng trắng thừa.
- Khi cuộn tới đầu hoặc cuối một cột, phần cuộn còn lại được chuyển tiếp ra trang để người dùng đi xuống nội dung mô tả, sản phẩm gợi ý và đánh giá tự nhiên hơn.

## Update 2026-06-01 storefront product detail sticky layout

- Trang chi tiết sản phẩm đổi từ hai cột cuộn độc lập sang bố cục cột trái sticky và cột phải cuộn theo trang để giảm khoảng trắng và giữ ảnh sản phẩm làm điểm neo thị giác.
- Phần thông số kỹ thuật trên storefront đọc linh hoạt cả `specs` và `specifications`, hỗ trợ dữ liệu dạng object hoặc mảng `{ key, label, value, group }`.
- Tuỳ chọn phiên bản/màu sắc trên storefront được chuẩn hoá label/key trước khi render để tránh lỗi React khi API trả object như `{ name }`.
- Thông số sản phẩm có thêm alias và fallback label tiếng Việt ở storefront, ví dụ `screenSize` được chuẩn hoá về `screen_size`, các key như `wifi`, `bluetooth`, `rear_video`, `noise_cancellation` được hiển thị bằng tên tiếng Việt.

## Update 2026-06-01 storefront product detail premium CellphoneS style

- Cải tiến giao diện trang chi tiết sản phẩm lấy cảm hứng từ CellphoneS:
  - Nút chọn dung lượng và màu sắc tự động hiển thị giá bán tương ứng phía dưới (truy xuất từ biến thể của sản phẩm).
  - Nút trả góp chia thành 2 nút song song: "TRẢ GÓP 0%" (tông vàng cam) và "TRẢ GÓP QUA THẺ" (tông xanh dương) với thông tin phụ trực quan.
  - Phần mô tả sản phẩm (Product Description) mặc định giới hạn chiều cao tối đa 400px, có hiệu ứng phủ mờ đáy (gradient fadeout) và nút toggle "Xem thêm / Thu gọn".
  - Các nút tác vụ nhanh ở đầu trang (Yêu thích, Hỏi đáp, Thông số, So sánh) được phối màu xám đen với hiệu ứng chuyển màu đỏ khi hover đồng bộ với tông màu đỏ của shop.
  - Gom nhóm các khối nội dung rời rạc ở cột phải thành 2 Card lớn thống nhất: "Purchase Card" (chứa giá, các phiên bản chọn, khuyến mãi lồng bên trong, số lượng, cụm nút thanh toán và trả góp) và "Information Card" (chứa Đặc điểm nổi bật + Mô tả chi tiết phân cách bởi một đường kẻ mảnh), giúp loại bỏ hoàn toàn các khoảng trống lề thừa rời rạc ở cột phải.
  - Loại bỏ hoàn toàn nền trắng của khung bao Thumbs Swiper để các ảnh con nổi tự nhiên trên nền xám của trang, triệt tiêu khoảng trống trắng thừa bên phải. Đồng thời đổi ảnh lớn sang kích thước động `w-[90%] h-[90%]` để lấp đầy hộp trắng trưng bày cân đối.
  - Sử dụng Grid tỷ lệ `lg:grid-cols-[500px_1fr]` cố định cột trái 500px và loại bỏ `mx-auto` trên `<aside>` để cột trái bám sát lề trái trang, thu hẹp khoảng hở dọc trống trải ở giữa hai cột.
  - Chuyển nền trang sang trắng tinh (`bg-white`), làm phẳng tiêu đề và ô cam kết, loại bỏ bóng đổ bọc ngoài ở tất cả các khối (chỉ dùng viền mảnh `border-gray-200`) và để các phần tử mua hàng ở cột phải chảy trực tiếp trên nền trắng không đóng hộp bọc ngoài, phản ánh chính xác phong cách tối giản phẳng (Flat Design) của CellphoneS.

## Update 2026-06-01 storefront product detail real data migration

- Loại bỏ hoàn toàn các dữ liệu giả (fallback promotions mặc định, phụ kiện mua kèm cứng) khỏi trang chi tiết sản phẩm.
- Sửa Catalog API `GET /catalog/products/{product_id}` để trả về `salesConfig` và tự động resolve thông tin chi tiết các sản phẩm phụ kiện trong `accessoryOffers` (bao gồm tên, SKU, hình ảnh, giá gốc, giá bán hiện tại và giá sau ưu đãi mua kèm).
- Cập nhật frontend `ProductDetail.tsx` để ẩn khối Khuyến mãi nếu sản phẩm không cấu hình `promotions` trong DB.
- Cập nhật frontend `BundleOffers` để ẩn khối Ưu đãi mua kèm nếu sản phẩm không có `accessoryOffers` thực tế. Khi hiển thị, khối sẽ render tên, hình ảnh, giá bán lẻ hiện tại và giá ưu đãi mua kèm thực tế của các phụ kiện được liên kết.
- Sửa đổi logic tính điểm xu hướng rankings (`ranking_row` trong `catalog.py`): Nếu sản phẩm không phát sinh tương tác nào (lượt xem, tìm kiếm, lượt mua) trong khoảng thời gian trượt đã chọn (ví dụ 24h), điểm xu hướng sẽ trả về 0 thay vì neo giữ điểm tích lũy trọn đời (từ lượt yêu thích/đánh giá).
- Cấu trúc cơ chế sắp xếp phân tầng (multi-level fallback) trong Rankings: Khi các sản phẩm cùng bằng điểm nhau ở tiêu chí chính (ví dụ cùng bằng 0 điểm xu hướng ở khoảng thời gian 24h), hệ thống sẽ tự động so sánh qua các cấp tiếp theo gồm mốc 24h, mốc 7 ngày, mốc 30 ngày, mốc 1 năm, rồi đến doanh thu chu kỳ và cuối cùng là điểm đánh giá của sản phẩm. Logic này áp dụng đồng bộ cho tất cả các tiêu chí sắp xếp (trending, sold, view, search, like, rating) và loại bỏ hoàn toàn các mốc "kỳ trước" (previous period) để đảm bảo tuân thủ đúng yêu cầu mốc thời gian tăng dần của người dùng.
- Thêm `like_stats` và `rating_stats` theo các mốc thời gian vào câu SQL của Rankings API để hỗ trợ đầy đủ cơ chế so sánh phân tầng cho hai tùy chọn "Được yêu thích nhất" (like) và "Đánh giá cao nhất" (rating).
- Sửa điểm xu hướng Rankings để lượt yêu thích/đánh giá chỉ được tính theo đúng khoảng thời gian đang xem. Ví dụ mốc 24h chỉ cộng lượt thích và đánh giá mới trong 24h, không cộng tổng `favorite_count`/`review_count` trọn đời sản phẩm vào điểm xu hướng.
- Rankings không còn lấy `rating`, `review_count`, `favorite_count` trực tiếp từ bảng `products` vì các cột này có thể chứa dữ liệu seed/tổng hợp cũ. API rankings tính lại các chỉ số này từ bảng phát sinh thật gồm `product_reviews` và `user_favorites`; tiêu chí "Yêu thích" và "Đánh giá" ưu tiên dữ liệu trong khoảng thời gian đang chọn.
- Biểu đồ `history` của Rankings chia bucket cố định theo mốc hiển thị: 24h = 24 khung giờ, 7d = 7 ngày, 30d = 30 ngày, 1y = 12 tháng. Bucket được neo vào đầu giờ/ngày/tháng để label không bị lệch hoặc dư điểm cuối.

## Update 2026-06-02 product favorite event history

- Thêm migration `050_product_favorite_events.sql` để bổ sung `is_active`, `updated_at` cho `user_favorites` và tạo bảng `user_favorite_events` ghi nhật ký `LIKE`/`UNLIKE` kèm `created_at`.
- API yêu thích sản phẩm không xóa cứng dòng yêu thích nữa. Khi hủy yêu thích, hệ thống chuyển `is_active = FALSE` và ghi sự kiện `UNLIKE`; khi yêu thích lại, hệ thống bật `is_active = TRUE`, cập nhật thời gian trạng thái hiện tại và ghi sự kiện `LIKE` mới.
- Rankings tính các chỉ số yêu thích theo 24h/7d/30d/1y từ bảng `user_favorite_events` với `action = 'LIKE'`, giúp dữ liệu lịch sử không bị mất khi người dùng hủy yêu thích sau đó. Danh sách sản phẩm yêu thích của người dùng vẫn chỉ hiển thị các dòng `is_active = TRUE`.
- API `GET /catalog/favorites` trả thêm `favoritedAt` và `favoriteUpdatedAt`; tab "Sản phẩm yêu thích" trên tài khoản hiển thị thời điểm người dùng yêu thích sản phẩm.
- API toggle yêu thích có rate limit qua Redis theo cặp user/sản phẩm: tối đa 5 lần thích/hủy trong 10 giây. Nếu vượt ngưỡng, trả 429 với thông báo "Bạn thao tác yêu thích quá nhanh. Vui lòng thử lại sau vài giây." để giảm spam làm nhiễu event log và rankings.
- Rankings tính "Yêu thích" theo điểm ròng từ event log: `LIKE = +1`, `UNLIKE = -1`. Vì vậy nếu người dùng hủy yêu thích trong 24h/7d/30d/1y thì chỉ số có thể đi xuống ở đúng bucket thời gian đó; nếu thích lại thì tăng lại. Cách này tránh việc spam thích/hủy/thích làm buff nhiều lượt `LIKE` giả trong cùng một khoảng thời gian.
## Update 2026-06-02 storefront product list filters

- Trang danh sách sản phẩm đổi bộ lọc Danh mục và Hãng từ danh sách nút/chip sang danh sách sổ xuống để gọn hơn khi dữ liệu nhiều.
- Bộ lọc giá trên storefront dùng một thanh trượt khoảng giá chung và hai ô nhập thủ công cho giá tối thiểu/tối đa đến 100 triệu; giá tùy chỉnh tiếp tục ghi vào query `min_price`/`max_price` để dùng chung luồng lọc catalog hiện có.
- Thẻ sản phẩm storefront bỏ nút So sánh dạng overlay chỉ hiện khi rê chuột trên desktop; nút So sánh nay hiển thị cố định trong chân thẻ để người dùng dễ chọn hơn.

## Update 2026-06-03 smartphone product specifications update

- Thực hiện cập nhật đầy đủ thông số kỹ thuật (specifications) cho toàn bộ sản phẩm thuộc danh mục điện thoại (smartphones).
- Cập nhật trực tiếp file SQL seed `backend/migrations/init_database.sql` cho 5 mẫu điện thoại flagship: iPhone 16 Pro Max (`IP16PM`), Samsung Galaxy S24 Ultra (`S24U`), Samsung Galaxy Z Fold6 (`ZFOLD6`), Xiaomi 14 Ultra (`X14U`), và OPPO Find N3 (`OPPFN3`) với đầy đủ 42 trường specifications theo chuẩn của danh mục.
- Chạy script Python `update_smartphone_specs.py` để bổ sung và chuẩn hóa dữ liệu thực tế bằng tiếng Việt có dấu cho các trường còn thiếu (bao gồm `brightness`, `video_recording`, `connectivity`...) cho toàn bộ 38 sản phẩm điện thoại đang tồn tại trong cơ sở dữ liệu.
- Đảm bảo 100% trường specifications được điền giá trị chuẩn và hiển thị đồng bộ trên storefront.
## Update 2026-06-03 flash sale management

- Thêm migration `051_flash_sales.sql` tạo bảng `flash_sales` tách riêng khỏi bảng `products`.
- Admin có module riêng:
  - Backend: `backend/app/api/v1/routers/admin_flash_sales.py`.
  - Frontend hook: `frontend/src/features/admin-flash-sales/hooks/useAdminFlashSalesLogic.ts`.
  - Frontend tab: `frontend/src/features/admin-flash-sales/components/AdminFlashSalesTab.tsx`.
- File chính chỉ đăng ký router/tab/API để giữ đúng nguyên tắc không nhồi logic flash sale vào module quản lý sản phẩm.
- Flash sale hỗ trợ chọn sản phẩm, giảm theo phần trăm hoặc số tiền, thời gian bắt đầu, thời gian kết thúc hoặc không có thời hạn, thêm, sửa, xóa và bật/tắt trạng thái.
- Backend kiểm tra giá flash sale phải lớn hơn 0 và nhỏ hơn giá bán hiện tại của sản phẩm trước khi lưu.
- Catalog API tính giá flash sale động khi sale đang hiệu lực, không ghi đè `products.price` hoặc `products.sale_price`.
- Storefront product card và trang chi tiết sản phẩm ưu tiên hiển thị giá flash sale, giá gốc bị gạch và nhãn/bảng thông báo flash sale đang diễn ra.
## Update 2026-06-03 storefront product detail real metrics

- Trang chi tiết sản phẩm không còn dùng số liệu ảo cho đánh giá và đã bán:
  - Không fallback rating về `4.8`.
  - Không fallback đã bán về `128`.
  - Khi chưa có dữ liệu, rating hiển thị "Chưa có đánh giá", số đánh giá và đã bán hiển thị `0`.
- Frontend không còn thay ảnh sản phẩm theo bảng ảnh demo trong `apiDb.ts`; ảnh sản phẩm lấy từ dữ liệu backend/database và chỉ được chuẩn hóa URL.
- API chi tiết sản phẩm tính `rating`, `reviewCount`, `favoriteCount` trực tiếp từ `product_reviews` và `user_favorites`; `soldCount` tiếp tục tính từ `order_items` của đơn `COMPLETED`.

## Update 2026-06-03 storefront product detail variant configuration

- Trang chi tiết sản phẩm đổi khu chọn "Phiên bản" thành "Cấu hình" để người mua biết rõ biến thể đang chọn theo thông số nào.
- Frontend dựng nhãn cấu hình từ dữ liệu biến thể thật, ưu tiên `ram`, `storage`/ROM và `configuration`; ví dụ `RAM 8GB / ROM 256GB`.
- Mỗi nút cấu hình hiển thị thêm chip thông số nhỏ như `RAM: 8GB`, `ROM: 256GB` và giá của biến thể tương ứng, ưu tiên đúng màu đang chọn nếu sản phẩm có nhiều màu.
- Catalog API chi tiết sản phẩm trả thêm `options` để storefront có đủ dữ liệu cấu hình biến thể từ database.

## Update 2026-06-03 storefront color-scoped variant configuration

- Khu chọn cấu hình trên trang chi tiết sản phẩm nay lọc theo màu đang chọn: nếu màu đó có 3 biến thể thì chỉ hiển thị 3 lựa chọn cấu hình của màu đó.
- Nhãn cấu hình được rút gọn để tránh lặp `ROM 512GB / Cấu hình 512GB`; khi chỉ có bộ nhớ thì hiển thị `512GB`, khi có RAM và ROM thì hiển thị dạng `8GB / 512GB`.
- Khi đổi màu, nếu cấu hình đang chọn không tồn tại ở màu mới, storefront tự chuyển sang cấu hình đầu tiên có sẵn của màu đó để giá và biến thể active luôn khớp dữ liệu thật.

## Update 2026-06-03 storefront split RAM ROM selection

- Trang chi tiết sản phẩm không còn chỉ chọn cấu hình gộp; storefront tách nhóm chọn theo từng thông số biến thể riêng như `RAM`, `ROM` và cấu hình phụ nếu có.
- Danh sách RAM/ROM được dựng từ các biến thể thật của màu đang chọn; nếu màu đó chỉ có một biến thể thì vẫn hiển thị cấu hình duy nhất để người mua biết rõ đang chọn gì.
- Giá bán lấy từ biến thể khớp với màu + RAM + ROM đang chọn. Khi đổi RAM, hệ thống giữ ROM hiện tại nếu còn hợp lệ; nếu không, tự chọn ROM đầu tiên có trong RAM mới.
- Nút chọn màu không hiển thị giá riêng nữa để tránh hiểu nhầm màu có giá cố định; giá chỉ hiện ở khu giá chính và các lựa chọn cấu hình có ảnh hưởng trực tiếp tới biến thể.
- Thông số kỹ thuật trên trang chi tiết nay merge thông số của biến thể đang chọn vào thông số sản phẩm trước khi hiển thị, nên RAM/ROM và các specs biến thể tự đổi theo cấu hình active thay vì hiện giá trị tổng hợp như `256 GB / 512 GB`.
- Tên sản phẩm trên H1 của trang chi tiết gộp luôn cấu hình dạng `Tên sản phẩm - RAM / ROM`, ví dụ `HONOR 400 Pro - 12GB / 512GB`. Nếu biến thể thiếu RAM hoặc ROM riêng, storefront fallback sang thông số chung của sản phẩm để người mua vẫn thấy cấu hình đầy đủ.

## Update 2026-06-03 storefront specs modal overflow fix

- Sửa popup "Thông số kỹ thuật" trên trang chi tiết sản phẩm để thanh chọn nhóm thông số không bị che hoặc cắt bởi vùng nội dung.
- Header và thanh chọn nhóm được giữ ở vùng riêng, phần bảng thông số chỉ cuộn dọc và không tạo cuộn ngang cho toàn modal.
- Nội dung label/value trong bảng thông số tự xuống dòng để tránh kéo rộng modal khi thông số dài.
- Thanh chọn nhóm thông số trong popup nay là điều hướng cuộn tới nhóm tương ứng, không còn lọc ẩn các nhóm thông số khác.
- Khi bấm nhóm thông số, modal chừa khoảng đệm phía trên section đích để tiêu đề và dòng đầu không bị thanh chọn nhóm che mất; scrollbar ngang của thanh nhóm cũng được ẩn để giao diện sạch hơn.
- Mô tả sản phẩm trên trang chi tiết được làm sạch HTML trước khi hiển thị, tránh lỗi các thẻ như `<p>` xuất hiện trong "Đặc điểm nổi bật" và "Thông tin chi tiết".
- Breadcrumb trang chi tiết sản phẩm hiển thị theo thứ tự `Trang chủ > Danh mục cha > Danh mục con nếu có > Thương hiệu > Tên sản phẩm`; Catalog API trả thêm `subcategory` để frontend có tên danh mục con.

## Update 2026-06-03 HONOR Magic V5 variant RAM correction

- Sửa lỗi các biến thể (variants) của `HONOR Magic V5` (`HN-MGV5`) bị thiếu trường `ram` (giá trị bằng `NULL`/`None`), dẫn đến việc hiển thị không đúng/không đầy đủ tùy chọn RAM bên cạnh tùy chọn ROM/dung lượng trên trang chi tiết sản phẩm.
- Cập nhật trực tiếp cột `options` trong bảng `products` của `HN-MGV5` để thiết lập đúng hợp đồng options (Màu sắc, Dung lượng, RAM).
- Chạy script Python `update_magic_v5_variants.py` cập nhật trực tiếp cho toàn bộ 8 biến thể của dòng máy này:
  - Thiết lập cột `ram = '12GB'`, `specs` = `{"storage": "512GB", "ram": "12GB"}` và `attributes` tương ứng cho các biến thể 512GB.
  - Thiết lập cột `ram = '16GB'`, `specs` = `{"storage": "1TB", "ram": "16GB"}` và `attributes` tương ứng cho các biến thể 1TB.
- Giúp storefront hiển thị chuẩn xác các tùy chọn RAM/ROM tách biệt (như `12GB / 512GB` và `16GB / 1TB`) cho người dùng khi chọn cấu hình sản phẩm.

## Update 2026-06-03 HONOR Magic V5 color deletion

- Thực hiện xóa 2 màu sắc cấu hình "Nâu Lụa" và "Đen Titanium" khỏi dòng máy `HONOR Magic V5` (`HN-MGV5`) theo yêu cầu.

## Update 2026-06-03 HONOR Magic V5 image gallery

- Đã copy ảnh người dùng cung cấp từ thư mục `HONOR Magic V5` vào `frontend/public/images/products/honor-magic-v5`.
- Ảnh được chia theo màu:
  - `white`: Trắng Ngà, gồm ảnh đại diện và 11 ảnh gallery.
  - `gold`: Vàng Bình Minh, gồm ảnh đại diện và 13 ảnh gallery.
  - `common`: 5 ảnh dùng chung.
- Thêm script `backend/scripts/update_magic_v5_images.py` để cập nhật `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho SKU `HN-MGV5`.
- Đã chạy script trên DB local: 2 biến thể Trắng Ngà và 2 biến thể Vàng Bình Minh đã trỏ tới đúng ảnh theo màu; product dùng ảnh đại diện Trắng Ngà và gallery chung.
- Quy ước ảnh HONOR Magic V5: file có chữ "ảnh đại diện" được dùng cho `image_url`; các file còn lại trong thư mục màu là gallery của biến thể đó và được lưu vào `product_variants.images`. Vì vậy `product_variants.images` không chứa lại ảnh đại diện.
- Trang chi tiết sản phẩm nay dựng gallery theo biến thể đang chọn trước, sau đó mới nối ảnh chung của sản phẩm. Khi người dùng đổi màu/cấu hình, ảnh chính tự nhảy về ảnh đầu của biến thể active và không còn gom ảnh của các màu khác vào đầu gallery.
- Sửa form admin sản phẩm: khi mở chỉnh sửa, hook `useAdminProductsLogic.ts` nay map `item.images` vào từng biến thể để preview "Bộ ảnh biến thể" hiển thị đúng ảnh đang lưu trong DB và không bị mất khi lưu lại.
- Storefront có fallback ảnh biến thể theo màu: nếu biến thể active chưa có `imageUrl/images`, trang chi tiết tự tìm biến thể khác cùng `colorName` có ảnh để dùng, rồi vẫn nối thêm ảnh chung của sản phẩm.
- Form admin sản phẩm có thêm thao tác "Lấy ảnh cùng màu" và menu "Lấy ảnh từ biến thể khác" để copy `imageUrl/images` từ biến thể đã có ảnh sang biến thể mới hoặc biến thể cùng màu, giảm việc nhập ảnh lặp lại cho từng RAM/ROM.
- Thẻ sản phẩm ngoài danh sách chỉ dùng ảnh đại diện sản phẩm và ảnh đại diện biến thể; không dùng `product.images` vì bộ ảnh chung chỉ dành cho gallery bên trong trang chi tiết sản phẩm.
- Catalog API chi tiết sản phẩm trả thêm `images` cho từng biến thể để gallery chi tiết có thể nối `variant.imageUrl` + `variant.images` + `product.images`.
- Cập nhật trực tiếp trường `colors` và `options` (Màu sắc) của sản phẩm trong bảng `products` để loại bỏ 2 màu này, chỉ giữ lại "Trắng Ngà" và "Vàng Bình Minh".
- Thực hiện soft-delete (đặt `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biến thể tương ứng của 2 màu sắc này trong bảng `product_variants` (gồm `HN-MGV5-BK-512GB`, `HN-MGV5-BK-1TB`, `HN-MGV5-BR-512GB`, `HN-MGV5-BR-1TB`), đảm bảo đồng bộ dữ liệu trên storefront.
- Cập nhật tập lệnh `backend/scripts/update_magic_v5_variants.py` để loại bỏ hai màu này khỏi mảng options được cấu hình lại, tránh việc chạy lại script khôi phục nhầm các màu đã xóa.

## Update 2026-06-03 HONOR 400 5G color deletion & option setup

- Thực hiện xóa 2 màu sắc cấu hình "Xám Mặt Trăng" và "Đen Bóng Đêm" khỏi dòng máy `HONOR 400 5G` (`HN-400`) theo yêu cầu.
- Cập nhật trực tiếp trường `colors` và `options` (Màu sắc, Dung lượng, RAM) của sản phẩm `HN-400` trong bảng `products` để loại bỏ 2 màu này, chỉ giữ lại "Vàng Sa Mạc", đồng thời đồng bộ cấu hình RAM của phiên bản 256GB là 8GB và 512GB là 12GB.
- Thực hiện soft-delete (đặt `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biến thể tương ứng của 2 màu sắc này trong bảng `product_variants` (gồm `HN-400-GR-256GB`, `HN-400-GR-512GB`, `HN-400-BK-256GB`, `HN-400-BK-512GB`).

## Update 2026-06-03 HONOR 400 series image gallery

- Đã copy ảnh người dùng cung cấp:
  - `HONOR 400 5G` vào `frontend/public/images/products/honor-400-5g`.
  - `Honor 400 pro` vào `frontend/public/images/products/honor-400-pro`.
- Thêm script `backend/scripts/update_honor_400_images.py` để cập nhật ảnh cho SKU `HN-400` và `HN-400P`.
- Đã chạy script trên DB local:
  - `HN-400`: product dùng ảnh đại diện Vàng Sa Mạc, có 5 ảnh chung; 2 biến thể Vàng Sa Mạc có ảnh đại diện và 5 ảnh gallery biến thể.
  - `HN-400P`: product dùng ảnh đại diện Đen Bóng Đêm; 2 biến thể Đen Bóng Đêm có 5 ảnh gallery, 2 biến thể Xám Mặt Trăng có 3 ảnh gallery.
- `HN-400P` màu Xanh Thủy Triều chưa có bộ ảnh được cung cấp nên hiện vẫn giữ ảnh placeholder cũ cho biến thể màu xanh.
- Đồng bộ thông tin RAM (`ram = '8GB'` hoặc `'12GB'`), specifications (`specs`) và thuộc tính (`attributes`) cho tất cả 6 biến thể (bao gồm cả các biến thể đã soft-deleted) tương thích với cấu hình 8GB RAM / 256GB ROM và 12GB RAM / 512GB ROM để dữ liệu đồng bộ nhất quán trên storefront.
- Tạo script `backend/scripts/update_honor_400_5g.py` để thực hiện cập nhật này một cách tự động và lưu trữ dự phòng.

## Update 2026-06-03 Global Laptops & Tablets RAM/Option Standardization

- Thực hiện rà soát toàn bộ sản phẩm trên hệ thống, phát hiện và sửa đổi hoàn chỉnh lỗi thiếu cấu hình tùy chọn (`options`), thiếu RAM trong biến thể hoặc chưa đồng bộ `attributes` và `specs` cho **20 sản phẩm** thuộc danh mục `laptops` và `tablets`.
- Tạo và chạy tập lệnh [repair_products.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/repair_products.py) tự động thực hiện:
  - Đồng bộ hóa mảng `options` của sản phẩm chứa cấu trúc tiếng Việt chuẩn: Màu sắc, Dung lượng, RAM.
  - Điền giá trị RAM chuẩn vào cột `ram` của biến thể.
  - Đồng bộ `specs` và `attributes` đầy đủ bằng tiếng Việt tương ứng cho từng biến thể để storefront hiển thị tùy chọn chính xác nhất.
- Chạy lại script rà soát xác nhận số lượng sản phẩm có cấu hình lỗi đã giảm về 0, đồng thời chạy bộ kiểm thử rules của variant thành công 100%.

## Update 2026-06-03 Smartphones RAM Separation & Option Standardization

- Thực hiện chuẩn hóa cấu hình RAM và bộ nhớ cho toàn bộ danh mục Điện thoại (Smartphones) trên hệ thống.
- Giải quyết triệt để lỗi RAM/ROM gộp trong trường `storage` của biến thể (dạng `"RAM 8GB - 256GB"`) bằng cách tách thành:
  - Cột `storage` là giá trị dung lượng sạch (ví dụ: `"256GB"`).
  - Cột `ram` là mức RAM tương ứng (ví dụ: `"8GB"`).
- Đối với các dòng điện thoại sử dụng dung lượng sạch nhưng chưa được gán RAM ở biến thể, tự động phân tích và gán giá trị RAM chuẩn tương ứng theo thông số kỹ thuật và phân khúc giá (ví dụ: dòng S26 Ultra 1TB có 16GB RAM, các dòng khác có 12GB RAM; Redmi Note 14 Pro+ bản 256GB có 8GB RAM, bản 512GB có 12GB RAM).
- Đồng bộ mảng `options` cấp sản phẩm với cấu trúc đầy đủ bằng tiếng Việt (Màu sắc, Dung lượng, RAM).
- Đồng bộ `specs` và `attributes` đầy đủ bằng tiếng Việt tương ứng cho từng biến thể. Các biến thể khác nhau về RAM/ROM vẫn giữ nguyên mức giá chênh lệch đã được thiết lập trước đó trong cơ sở dữ liệu.
- Tạo và chạy tập lệnh [repair_smartphones.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/repair_smartphones.py) tự động thực hiện và lưu trữ dự phòng.

## Update 2026-06-03 HONOR X9d 5G Color Deletion

- Thực hiện xóa 2 màu sắc cấu hình "Nâu Đỏ" và "Xanh Rừng" khỏi dòng máy `HONOR X9d 5G` (`HN-X9D`) theo yêu cầu.
- Cập nhật trường `colors` và `options` (Màu sắc) của sản phẩm trong bảng `products` để loại bỏ 2 màu này, chỉ giữ lại "Vàng Bình Minh" và "Đen Bóng Đêm".
- Thực hiện soft-delete (đặt `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biến thể tương ứng của 2 màu sắc này trong bảng `product_variants` (gồm `HN-X9D-BR-256GB`, `HN-X9D-BR-512GB`, `HN-X9D-GR-256GB`, `HN-X9D-GR-512GB`), đảm bảo đồng bộ dữ liệu trên storefront.
- Tạo và chạy tập lệnh [delete_honor_x9d_colors.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/delete_honor_x9d_colors.py) tự động thực hiện và lưu trữ dự phòng.

## Update 2026-06-03 HONOR X9d 5G image gallery

- Đã copy ảnh người dùng cung cấp từ thư mục `honor x9d` vào `frontend/public/images/products/honor-x9d`.
- Ảnh được chia theo màu:
  - `black`: Đen Bóng Đêm, gồm ảnh đại diện và 8 ảnh gallery.
  - `gold`: Vàng Bình Minh, gồm ảnh đại diện và 11 ảnh gallery.
  - `common`: 5 ảnh dùng chung cho trang chi tiết sản phẩm.
- Thêm script `backend/scripts/update_honor_x9d_images.py` để cập nhật `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho SKU `HN-X9D`.
- Đã chạy script trên DB local: 2 biến thể Đen Bóng Đêm và 2 biến thể Vàng Bình Minh đã trỏ đúng ảnh theo màu; product dùng ảnh đại diện Đen Bóng Đêm và gallery chung.
- Quy ước ảnh HONOR X9d 5G: file có chữ "ảnh đại diện" hoặc "ảnh địa diện" được dùng cho `image_url`; các file còn lại trong thư mục màu là gallery của biến thể đó và được lưu vào `product_variants.images`.

## Update 2026-06-04 Admin product simple-product variant rule

- Sản phẩm không có biến thể nay được xem là sản phẩm đơn giản hợp lệ; giá, giá bán, tồn kho, ảnh và thông tin chung lấy trực tiếp từ bảng `products`.
- Chỉ sản phẩm có danh sách biến thể mới bắt buộc có đúng một biến thể mặc định. Khi danh sách biến thể rỗng, backend không tự tạo biến thể mặc định nữa và cho phép xóa biến thể cuối cùng bằng soft-delete.
- Form admin thêm trường `Tồn kho chung`, gửi kèm `brand` và `category` để thương hiệu nhập tay không bị rơi về `Khác`, đồng thời không gửi cấu hình option/variant khi sản phẩm không có biến thể.
- Khi sửa sản phẩm, frontend map lại đúng `stockQuantity` và `salePrice` của biến thể để tránh mất tồn kho hoặc giá bán sau khi lưu.
- Backend chỉ đồng bộ giá/tồn kho cha từ biến thể khi sản phẩm thật sự còn biến thể; sản phẩm đơn giản giữ nguyên giá và tồn kho chung.
- Sửa thêm lỗi lọc `status=all` trong danh sách admin và lỗi nhân bản sản phẩm do PostgreSQL không suy luận được kiểu của hậu tố SKU.
- Tách frontend API sản phẩm: thêm `frontend/src/services/productApi.ts` cho các endpoint admin product, chuyển `useAdminProductsLogic.ts`, `AdminProductsTab.tsx` và phần load product trong `useAdminLogic.ts` sang service này. Các endpoint admin product đã chuyển được gỡ khỏi `apiDb`; các endpoint tồn kho liên quan sản phẩm vẫn giữ tạm để tách sang `inventoryApi` sau.
- Sau khi tách thêm hook product/variant, `useAdminProductVariants.ts` trả thêm `colorOptionName` để `useAdminProductsLogic.ts` map lại màu biến thể khi mở form chỉnh sửa. Sửa import thiếu `youtubeEmbedUrl` và `ImageWithFallback` ở `ProductDetail.tsx` sau khi tách helper media.

## Update 2026-06-05 Frontend feature-first refactor for Products & Brands

- Hoàn thành di chuyển toàn bộ module **Thương hiệu (Brands)** và **Sản phẩm (Products)** ở Frontend sang cấu trúc hướng tính năng (**Feature-First Architecture**):
  - **Module Thương hiệu (Brands)**: Di chuyển sang `src/features/admin-brands/` gồm API (`services/adminBrandsApi.ts`), logic hooks (`hooks/useAdminBrandsLogic.ts`) và giao diện (`components/AdminBrandsTab.tsx`).
  - **Module Sản phẩm (Products)**: Di chuyển sang `src/features/admin-products/` gồm API (`services/adminProductsApi.ts`), logic hooks (`hooks/useAdminProductsLogic.ts`, `useAdminProductOffers.ts`, `useAdminProductVariants.ts`) và các UI Components (`components/AdminProductsTab.tsx`, `components/products/ProductAccessoriesSection.tsx`, `ProductFormSection.tsx`, `ProductTableSection.tsx`, `ProductVariantsSection.tsx`).
  - **Cập nhật import chung**: Cập nhật liên kết import trong các file điều phối trung tâm như `apiDb.ts`, `useAdminLogic.ts` và `AdminDashboardTabContent.tsx`.
  - **Dọn dẹp**: Xóa sạch toàn bộ các file và thư mục cũ tại các thư mục dùng chung `components/admin/tabs/`, `components/admin/hooks/` và `services/api/`.
  - **Xác minh**: Chạy thành công lệnh kiểm tra kiểu `npx tsc --noEmit` trên toàn bộ frontend mà không phát sinh bất kỳ lỗi compile nào.

## Update 2026-06-05 Refactor Attached Services to Service Layer & Feature-First

- Backend: Tách logic nghiệp vụ và truy vấn SQL của Dịch vụ đi kèm (Attached Services) ra khỏi `admin_products.py` sang một Service Layer chuyên biệt tại `app/application/services/attached_service.py` để giữ router sạch sẽ, dễ bảo trì. Các route `/attached-services` chỉ làm nhiệm vụ điều hướng và gọi hàm từ service.
- Frontend: Đóng gói toàn bộ module Dịch vụ vào thư mục tính năng chuyên biệt `src/features/admin-services/` theo kiến trúc hướng tính năng (Feature-First Architecture).
  - Tách API Attached Services từ `apiDb.ts` sang `adminServicesApi.ts` trong thư mục feature mới, đồng thời spread gộp lại vào `apiDb.ts` để giữ tương thích ngược.
  - Di chuyển UI tab `AdminServicesTab.tsx` và custom hook `useAdminServicesLogic.ts` vào feature folder, cập nhật các import điều phối liên quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`).
- Kết quả kiểm tra:
  - Frontend: compile thành công bằng `npx tsc --noEmit`.
  - Backend: compile thành công bằng `py_compile`, import `app.main` hoạt động bình thường, không xảy ra import vòng lặp.

## Update 2026-06-05 Refactor Flash Sales to Service Layer & Feature-First

- Backend: Tách logic nghiệp vụ, tính toán giá sale và truy vấn SQL của Flash Sales ra khỏi `admin_flash_sales.py` sang một Service Layer chuyên biệt tại `app/application/services/flash_sale_service.py`. Class pydantic `FlashSalePayload` được di chuyển sang `admin_schemas.py` để thống nhất cấu trúc schema.
- Frontend: Đóng gói toàn bộ module Flash Sales vào thư mục tính năng chuyên biệt `src/features/admin-flash-sales/` theo kiến trúc hướng tính năng (Feature-First Architecture).
  - Tách các API của Flash Sales từ `adminContentApi.ts` sang `adminFlashSalesApi.ts` trong thư mục feature mới, đồng thời spread gộp lại vào `apiDb.ts` để giữ tương thích ngược.
  - Di chuyển UI tab `AdminFlashSalesTab.tsx` và custom hook `useAdminFlashSalesLogic.ts` vào feature folder, cập nhật các import điều phối liên quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`, `adminContentApi.ts`).
- Kết quả kiểm tra:
  - Frontend: compile thành công bằng `npx tsc --noEmit`.
  - Backend: compile thành công bằng `py_compile`, import `app.main` hoạt động bình thường, không xảy ra import vòng lặp.

## Update 2026-06-05 Refactor Reviews to Service Layer & Feature-First

- Backend: Tách logic nghiệp vụ, kiểm duyệt và truy vấn SQL của Đánh giá (Reviews) ra khỏi `admin_reviews.py` sang một Service Layer chuyên biệt tại `app/application/services/review_service.py`.
- Frontend: Đóng gói toàn bộ module Đánh giá vào thư mục tính năng chuyên biệt `src/features/admin-reviews/` theo kiến trúc hướng tính năng (Feature-First Architecture).
  - Tách các API của Đánh giá từ `adminContentApi.ts` sang `adminReviewsApi.ts` trong thư mục feature mới, đồng thời spread gộp lại vào `apiDb.ts` để giữ tương thích ngược.
  - Di chuyển UI tab `AdminReviewsTab.tsx` và custom hook `useAdminReviewsLogic.ts` vào feature folder, cập nhật các import điều phối liên quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`, `adminContentApi.ts`).
- Kết quả kiểm tra:
  - Frontend: compile thành công bằng `npx tsc --noEmit`.
  - Backend: compile thành công bằng `py_compile`, import `app.main` hoạt động bình thường, không xảy ra import vòng lặp.
## Update 2026-06-05 Backend Product Repository Split

- Tách query danh sách sản phẩm admin khỏi `app/application/services/product_service.py` sang `app/infrastructure/database/repositories/product_repo.py` qua hàm `list_admin_product_rows`.
- Repository hiện phụ trách lọc, phân trang, đếm tổng và gom danh sách biến thể; service chỉ còn gọi repo rồi bổ sung quan hệ bundle, phụ kiện và dịch vụ đi kèm trước khi trả response.
- Kết quả kiểm tra: compile toàn bộ backend bằng môi trường ảo `.venv` thành công; import `app.main`, router admin products, product service và product repository đều hoạt động.

## Update 2026-06-05 Product Service SQL Cleanup

- Mở rộng `app/infrastructure/database/repositories/product_repo.py` để chứa các truy vấn DB còn lại của `product_service.py`: import CSV job, insert product, insert revision, update product, deactivate variants khi sản phẩm inactive, và duplicate product/variants/bundles/accessories.
- Làm sạch `app/application/services/product_service.py`: bỏ SQL trực tiếp (`session.execute`, `session.scalar`, `text`) và chuyển import schema sang `app.api.v1.schemas.admin`.
- Giữ service ở vai trò xử lý nghiệp vụ: validate media, chuẩn hóa options/specs/sales config, kiểm tra category migration, gọi variant service, đồng bộ quan hệ sản phẩm, audit và commit.
- Sửa lại thông báo lỗi tiếng Việt cho luồng import CSV.
- Kết quả kiểm tra: compile toàn bộ backend bằng `.venv` thành công; import `app.main`, admin products router, product service và product repository thành công.

## Update 2026-06-05 Product Approval Repository Split

- Tách truy vấn và thao tác dữ liệu của luồng duyệt sản phẩm khỏi `app/application/services/product_approval_service.py` sang `app/infrastructure/database/repositories/product_approval_repo.py`.
- `product_approval_service.py` hiện giữ vai trò điều phối nghiệp vụ: submit, approve, bulk approve/archive/delete, archive, deactivate; đồng thời giữ bước đồng bộ giá sản phẩm cha khi duyệt/xuất bản revision.
- Repository mới phụ trách các thao tác DB nhạy cảm của approval: merge revision variants, cập nhật trạng thái sản phẩm, sao chép bundle/accessory từ revision, archive/deactivate và kiểm tra category migration.
- Kết quả kiểm tra: compile toàn bộ backend bằng `.venv` thành công; import `app.main`, router admin product approvals, product approval service và product approval repository thành công.


## Update 2026-06-05 Admin Overview Repository Split

- Tách truy vấn dashboard tổng quan admin khỏi `app/application/services/overview_service.py` sang `app/infrastructure/database/repositories/overview_repo.py`.
- Service hiện chỉ còn gom dữ liệu từ repo và định dạng response cho router `admin_overview.py`.
- Kết quả kiểm tra: compile backend thành công; import `app.main`, admin overview router, overview service và overview repository thành công.


## Update 2026-06-05 Attached Service Repository Split

- Tách truy vấn và thao tác DB của dịch vụ đi kèm khỏi `app/application/services/attached_service.py` sang `app/infrastructure/database/repositories/attached_service_repo.py`.
- Service hiện chỉ còn chuẩn hóa giá theo loại dịch vụ, gọi repository, commit và trả response cho router admin products.
- Kết quả kiểm tra: compile backend thành công; import `app.main`, admin products router, attached service và attached service repository thành công.

## Update 2026-06-06 product delete rule

- `DELETE /admin/products/{id}` không còn tự chuyển sản phẩm không ràng buộc sang `ARCHIVED`.
- Nếu sản phẩm có đơn hàng hoặc đánh giá, thao tác xóa sẽ chuyển sang `INACTIVE` để giữ lịch sử bán hàng và đánh giá.
- Nếu sản phẩm chưa có đơn hàng/đánh giá nhưng đã có dữ liệu nhập kho thật, backend trả `409` và yêu cầu ẩn sản phẩm thay vì xóa. Dữ liệu nhập kho thật được xác định bằng `inventory_adjustment_logs.transaction_type = 'RECEIPT'` với `delta > 0`, hoặc `inventory_transactions` loại `IN` từ chứng từ `INBOUND`.
- Nếu sản phẩm chưa có đơn hàng, chưa có đánh giá và chưa có dữ liệu nhập kho thật, backend xóa cứng bản ghi sản phẩm; các quan hệ bundle/accessory/service liên quan được dọn trước khi xóa. Tồn kho seed/import nằm trong `stock_quantity` nhưng không có log nhập kho thật không chặn xóa.

## Update 2026-06-06 discontinued product status

- Thêm trạng thái sản phẩm `DISCONTINUED` / `Ngừng kinh doanh` vào constraint DB, helper chuẩn hóa trạng thái và lựa chọn trạng thái trong admin.
- Storefront không đưa sản phẩm `DISCONTINUED` vào danh sách mặc định/trang chủ. Khi người dùng tìm kiếm bằng từ khóa hoặc truy cập trực tiếp trang chi tiết, sản phẩm vẫn hiển thị thông tin tham khảo.
- Trang chi tiết sản phẩm `DISCONTINUED` không hiển thị giá bán, flash sale, gói mua kèm, nút mua ngay, thêm giỏ hàng, số lượng hoặc trả góp. UI chỉ hiển thị nhãn `Ngừng kinh doanh` và thông tin sản phẩm.

## Update 2026-06-06 Delete OPPO Find X8 White Variant

- Thực hiện xóa biến thể "Trắng Tinh Tú" của sản phẩm OPPO Find X8 (ID: `f7712c7b-7390-4a07-972b-fd5f1f7657ba`) trong cơ sở dữ liệu:
  - Cập nhật trường `colors` của sản phẩm để loại bỏ màu "Trắng Tinh Tú".
  - Cập nhật trường `options` của sản phẩm để loại bỏ màu "Trắng Tinh Tú" ra khỏi danh sách giá trị của tùy chọn "Màu sắc".
  - Soft-delete các biến thể màu trắng (`OP-FX8-WH-256GB` và `OP-FX8-WH-512GB`) trong bảng `product_variants` bằng cách cập nhật `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` và ghi nhận thời gian `deleted_at`.
  - Thiết lập biến thể active đầu tiên (`OP-FX8-BK-256GB`) làm biến thể mặc định (`is_default = TRUE`) và cập nhật SKU của sản phẩm cha để đáp ứng yêu cầu nghiệp vụ về biến thể mặc định duy nhất.

## Update 2026-06-06 Delete OPPO Find N6 Black Variant

- Thực hiện xóa biến thể "Đen Sâu Thẳm" của sản phẩm OPPO Find N6 (ID: `8d6c4002-f89d-4b1e-b898-65e5508ce38d`) trong cơ sở dữ liệu:
  - Cập nhật trường `colors` của sản phẩm để loại bỏ màu "Đen Sâu Thẳm".
  - Cập nhật trường `options` của sản phẩm để loại bỏ màu "Đen Sâu Thẳm" ra khỏi danh sách giá trị của tùy chọn "Màu sắc".
  - Soft-delete các biến thể màu đen (`OP-FN6-BK-512GB` và `OP-FN6-BK-1TB`) trong bảng `product_variants` bằng cách cập nhật `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` và ghi nhận thời gian `deleted_at`.
  - Thiết lập biến thể active đầu tiên (`OP-FN6-OR-1TB`) làm biến thể mặc định (`is_default = TRUE`) và cập nhật SKU của sản phẩm cha để đáp ứng yêu cầu nghiệp vụ về biến thể mặc định duy nhất.

## Update 2026-06-06 Modify OPPO Reno15 F 5G Variants

- Thực hiện cập nhật các biến thể của sản phẩm OPPO Reno15 F 5G (ID: `664a9354-89f1-4275-8a74-20ee67607d3f`) trong cơ sở dữ liệu:
  - Cập nhật trường `colors` và `options` của sản phẩm để loại bỏ hai màu "Xanh Cực Quang" và "Trắng Tinh Khôi", đồng thời thêm hai màu mới "Xanh Nhạt" (mã màu: `#add8e6`) và "Xanh Dương" (mã màu: `#2196f3`).
  - Soft-delete các biến thể màu cũ: `OP-RN15F-BL-8-256`, `OP-RN15F-BL-12-256` (Xanh Cực Quang) và `OP-RN15F-WH-8-256`, `OP-RN15F-WH-12-256` (Trắng Tinh Khôi) trong bảng `product_variants`.
  - Tạo mới 4 biến thể cho 2 màu mới:
    - Màu Xanh Nhạt: `OP-RN15F-LB-8-256` (8GB RAM - 256GB ROM, giá 8,490,000đ) và `OP-RN15F-LB-12-256` (12GB RAM - 256GB ROM, giá 9,490,000đ).
    - Màu Xanh Dương: `OP-RN15F-B-8-256` (8GB RAM - 256GB ROM, giá 8,490,000đ) và `OP-RN15F-B-12-256` (12GB RAM - 256GB ROM, giá 9,490,000đ).
  - Thiết lập biến thể `OP-RN15F-PK-8-256` (Hồng Rực Rỡ) làm biến thể mặc định (`is_default = TRUE`) và cập nhật SKU của sản phẩm cha.

## Update 2026-06-06 Delete OPPO Reno15 5G Aurora Variant

- Thực hiện xóa biến thể "Xanh Cực Quang" của sản phẩm OPPO Reno15 5G (ID: `1bcab5a6-c021-4976-83d8-6fd358a36192`) trong cơ sở dữ liệu:
  - Cập nhật trường `colors` của sản phẩm để loại bỏ màu "Xanh Cực Quang".
  - Cập nhật trường `options` của sản phẩm để loại bỏ màu "Xanh Cực Quang" ra khỏi danh sách giá trị của tùy chọn "Màu sắc".
  - Soft-delete các biến thể màu xanh cực quang (`OP-RN15-AB-256GB` và `OP-RN15-AB-512GB`) trong bảng `product_variants` bằng cách cập nhật `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` và ghi nhận thời gian `deleted_at`.
  - Thiết lập biến thể active đầu tiên (`OP-RN15-AW-256GB`) làm biến thể mặc định (`is_default = TRUE`) và cập nhật SKU của sản phẩm cha để đáp ứng yêu cầu nghiệp vụ về biến thể mặc định duy nhất.

## Update 2026-06-06 Add OPPO Find N3 Variants

- Thực hiện bổ sung các biến thể "Đen" và "Vàng" cho sản phẩm OPPO Find N3 (ID: `5f0c3535-c5ce-4cac-8321-a32ac43aefd2`) trong cơ sở dữ liệu:
  - Cập nhật trường `colors` của sản phẩm, thêm hai màu "Đen" (mã màu: `#1a1a1c`) và "Vàng" (mã màu: `#e5c158`).
  - Thiết lập cấu trúc `options` cho sản phẩm gồm có: Màu sắc ("Đen", "Vàng"), Dung lượng ("512GB"), và RAM ("16GB").
  - Tạo mới 2 biến thể trong bảng `product_variants`:
    - Biến thể Đen: SKU `OPPFN3-BK-512GB` (16GB RAM - 512GB ROM, giá 39,990,000đ, giá bán 34,990,000đ, tồn kho 3), đặt làm biến thể mặc định (`is_default = TRUE`).
    - Biến thể Vàng: SKU `OPPFN3-GD-512GB` (16GB RAM - 512GB ROM, giá 39,990,000đ, giá bán 34,990,000đ, tồn kho 3).
  - Cập nhật SKU sản phẩm cha thành `OPPFN3-BK-512GB` theo biến thể mặc định.

## Update 2026-06-06 Catalog Images Display Main Representative Image

- Thay đổi cách lấy ảnh đại diện của sản phẩm hiển thị trên trang thư viện ảnh `/images` (API `list_product_images` trong `catalog_utils.py`):
  - Giá trị trường `mainUrl` trả về cho Product Card nay ưu tiên lấy ảnh đại diện chung của sản phẩm (`product.imageUrl`) nếu nó là ảnh hợp lệ (không phải placeholder).
  - Chỉ khi sản phẩm không có ảnh đại diện hợp lệ thì mới fallback về ảnh đầu tiên trong bộ sưu tập gallery (`image_entries[0]["url"]`).
  - Giúp hiển thị đúng ảnh đại diện đồng bộ của sản phẩm ở trang ngoài danh sách ảnh, tránh việc lấy ngẫu nhiên ảnh chi tiết hoặc ảnh góc cạnh từ gallery.

## Update 2026-06-08 admin archived product save guard (superseded)

- Ghi chú lịch sử: trước đó frontend từng chặn đổi trực tiếp `ARCHIVED` sang `ACTIVE`.
- Rule này đã được thay thế trong cùng ngày: sản phẩm `ARCHIVED` được phép bật lại qua endpoint reactivate chuẩn, có kiểm tra blocker danh mục/thương hiệu và validate giá/biến thể.

## Update 2026-06-08 archived product hard delete fix

- Sửa luồng `DELETE /admin/products/{id}` để sản phẩm `ARCHIVED` không bị chặn mặc định bằng lỗi "Sản phẩm đã được lưu trữ trước đó".
- Sản phẩm đã lưu trữ nay vẫn đi qua cùng bộ kiểm tra ràng buộc như các trạng thái khác: có đơn hàng/đánh giá thì chuyển `INACTIVE`, có nhập kho thật thì trả `409`, không có ràng buộc thì xóa cứng.
- Dọn định nghĩa trùng `deactivate_product_data` trong `product_approval_repo.py` để chỉ còn một luồng xóa có hiệu lực.

## Update 2026-06-08 archived restore and no-MERGED revision publish

- Sản phẩm `ARCHIVED` nay được phép bật lại bằng luồng khôi phục chuẩn `POST /admin/products/{id}/reactivate`, có kiểm tra danh mục/thương hiệu đang ẩn và validate giá/biến thể như `INACTIVE`/`DISCONTINUED`.
- Frontend hiển thị thao tác khôi phục cho `ARCHIVED` và cho phép bulk restore với trạng thái `ARCHIVED`.
- Bỏ cơ chế để lại bản revision với trạng thái `MERGED` trong bảng `products` sau khi duyệt bản chỉnh sửa.
- Khi duyệt `REVISION_DRAFT`, backend vẫn áp dụng dữ liệu revision vào sản phẩm gốc, merge variants/bundle/accessory như cũ, nhưng ghi snapshot trước/sau vào `product_audit_logs` qua action `REVISION_PUBLISHED`, rồi xóa record revision khỏi `products`.
- Mục tiêu kiến trúc: bảng `products` chỉ giữ bản nghiệp vụ hiện hành/đang thao tác, còn lịch sử chỉnh sửa nằm ở audit trail thay vì nhân bản sản phẩm thành `MERGED`.

## Update 2026-06-08 remove catalog general stock input

- Form quản trị sản phẩm đã bỏ ô `Tồn kho chung` vì tồn kho được quản lý qua module Tồn kho/Nhập kho.
- Khi lưu sản phẩm, backend giữ nguyên `products.stock_quantity` hiện có thay vì ghi đè bằng payload từ form catalog.
- Biến thể mới tạo trong form sản phẩm mặc định tồn kho `0`; số lượng thực tế phải được nhập/điều chỉnh trong module tồn kho.
- Sửa lỗi hồi quy trong `create_product`: tạo sản phẩm mới dùng `payload.stock`, còn cập nhật sản phẩm cũ mới giữ `current["stock_quantity"]`; tránh lỗi `NameError: current is not defined` khi `POST /admin/products`.

## Update 2026-06-08 product detail attached services display

- API chi tiết sản phẩm catalog nay nạp `product_attached_services` và trả về trong `salesConfig.attachedServices` để storefront có dữ liệu hiển thị dịch vụ đi kèm.
- Nếu sản phẩm cũ chỉ còn `serviceId` trong `sales_config.attachedServices` nhưng thiếu dòng quan hệ, API chi tiết fallback resolve theo danh sách `serviceId` để vẫn hiển thị được.
- Trang chi tiết sản phẩm hiển thị thêm khối `Dịch vụ đi kèm` dưới khu `Ưu đãi mua kèm`, chỉ hiện khi sản phẩm còn kinh doanh và có dịch vụ active.
- Luồng duyệt `REVISION_DRAFT` đã copy thêm quan hệ `product_attached_services` từ revision sang sản phẩm gốc, đồng bộ với bundle/accessory; tránh việc admin chọn dịch vụ trong bản chỉnh sửa nhưng sau khi duyệt storefront không có dữ liệu.

## Update 2026-06-08 attached service tier price restore

- Trang chi tiết sản phẩm tự tính giá dịch vụ `TIERED_AMOUNT` theo `metadata.priceTiers` và giá sản phẩm/biến thể đang chọn, thay vì chỉ hiện “Theo mức giá sản phẩm”.
- Sửa luồng cập nhật dịch vụ đi kèm để form admin không ghi đè `metadata` rỗng lên dịch vụ sản phẩm đã có biểu phí.
- Chạy lại seed `scripts/seed_attached_services.py` để khôi phục biểu phí bảo hành và cập nhật reference cũ `BHMR-PHONE-12M` sang dịch vụ active `S24-MOBILE-12M`; API iPhone 16 Pro Max hiện trả 17 tier và phí 1.600.000đ cho giá 33.990.000đ.

## Update 2026-06-10 Add iPad Pro M4 11 inch Wi-Fi + Cellular (5G) Variants

- Cập nhật dòng sản phẩm iPad Pro M4 11 inch (SKU gốc: `IPADM4`) trên cả cơ sở dữ liệu (PostgreSQL) và tệp khởi tạo dữ liệu seed (`init_database.sql`):
  - Cập nhật `products.options` của sản phẩm cha để bổ sung tuỳ chọn "Kết nối" với 2 giá trị `"Wi-Fi"` và `"Wi-Fi + Cellular"`.
  - Cập nhật `capacities` của sản phẩm cha bao gồm 6 mức dung lượng: `"256GB"`, `"512GB"`, `"1TB"`, `"1TB Nano"`, `"2TB"`, `"2TB Nano"`.
  - Đồng bộ hóa 12 biến thể Wi-Fi cũ: Cập nhật `configuration` thành `"Wi-Fi"`, đồng thời chuẩn hóa `specs` và `attributes` để có key `"Kết nối": "Wi-Fi"` và `"ram": "8GB"` (hoặc `"16GB"` cho bản 1TB/2TB).
  - Thêm mới 12 biến thể Wi-Fi + Cellular (5G) mới (ví dụ SKU `IPADM4-256-SILVER-5G`) với giá bán cao hơn bản Wi-Fi tương ứng **6.000.000đ**, số lượng tồn kho mặc định là **10** chiếc, trạng thái hoạt động.
- Sửa đổi tệp `init_database.sql`: Khôi phục phần chèn thương hiệu, sản phẩm và biến thể bị hỏng cú pháp trước đó, đồng bộ hóa 24 biến thể của iPad Pro M4 vào dữ liệu seed ban đầu.
- Kết quả kiểm tra:
  - Backend compile thành công không có lỗi cú pháp.
  - CSDL thực tế được cập nhật đầy đủ và chính xác 24 biến thể thông qua script `update_ipad_m4_variants.py`.

## Update 2026-06-10 Add Apple Watch Ultra 2 Variants and Options

- Cập nhật sản phẩm Apple Watch Ultra 2 (SKU gốc: `AWU2`) trên cơ sở dữ liệu (PostgreSQL) và tệp seed `init_database.sql`:
  - Cập nhật sản phẩm cha `AWU2`: Thiết lập `colors` thành màu `"Titan Đen"` (`#2a2b2d`), bổ sung tùy chọn `"Phiên bản"` gồm 9 giá trị tương ứng với 9 loại dây đeo kích thước 49mm, và đồng bộ `capacities` chứa danh sách 9 tên dây đeo. Cập nhật giá bán là `16.990.000đ` và tồn kho là `90`.
  - Bổ sung 9 biến thể mới trong bảng `product_variants` ứng với các loại dây đeo:
    1. `AWU2-49-BLACK-ALPINEL` (49mm Dây Alpine Size L)
    2. `AWU2-49-BLACK-ALPINES` (49mm Dây Alpine Size S) - Biến thể mặc định (`is_default = true`)
    3. `AWU2-49-BLACK-TRAILSM` (49mm Dây Trail Size S/M)
    4. `AWU2-49-BLACK-CAOSU` (49mm Dây Cao Su)
    5. `AWU2-49-BLACK-TRAILML` (49mm Dây Trail Size M/L)
    6. `AWU2-49-BLACK-TITANM` (49mm Dây Titan Size M)
    7. `AWU2-49-BLACK-TITANS` (49mm Dây Titan Size S)
    8. `AWU2-49-BLACK-TITANL` (49mm Dây Titan Size L)
    9. `AWU2-49-BLACK-ALPINEM` (49mm Dây Alpine Size M)
  - Mỗi biến thể được gán màu sắc `"Titan Đen"`, tồn kho mặc định là `10` chiếc, trạng thái `"active"`, và đồng bộ hóa chi tiết trong trường `specs` và `attributes` theo định dạng của frontend.
- Đồng bộ hóa dữ liệu seed: Chèn 9 biến thể này vào phần `variant_seed` và cập nhật thông số sản phẩm cha trong phần `product_seed` của tệp `init_database.sql`.
- Kết quả kiểm tra:
  - CSDL thực tế được cập nhật đầy đủ và chính xác thông qua kịch bản `update_awu2_variants.py`.
  - Chạy thử nghiệm thành công, frontend hiển thị đúng bộ chọn dây đeo và giá tiền.

## Update 2026-06-10 Update iPad A16 Wifi Variants and Options

- Cập nhật cấu hình và biến thể cho dòng sản phẩm iPad A16 Wifi (SKU gốc: `IPADA16`) trên cơ sở dữ liệu (PostgreSQL) và tệp seed `init_database.sql`:
  - Cập nhật sản phẩm cha `IPADA16`:
    - Thiết lập `colors` gồm 4 màu mới: `"Bạc"` (`#d1d5db`), `"Vàng"` (`#f5e08c`), `"Hồng"` (`#e57c91`), `"Xanh"` (`#4b9cd3`).
    - Bổ sung tùy chọn `"Phiên bản"` gồm 5 cấu hình mới: `"A16 Wifi 128GB"`, `"A16 Wifi 256GB"`, `"A16 5G 128GB"`, `"A16 5G 256GB"`, `"A16 Wifi 512GB"`.
    - Đồng bộ `capacities` chứa danh sách 5 cấu hình trên.
    - Cập nhật giá cơ bản của sản phẩm cha thành `9.290.000đ` và tổng tồn kho là `200` (20 variants * 10).
  - Quản lý biến thể cũ: Đánh dấu xóa (soft-delete bằng cách đặt `deleted_at = NOW()`, `status = 'archived'`) đối với 4 biến thể cũ (bản 64GB và bản màu Xám Space Gray).
  - Bổ sung 20 biến thể mới ứng với 5 cấu hình × 4 màu sắc:
    - Các SKU mới theo định dạng `IPADA16-[CONFIG_CODE]-[COLOR_SUFFIX]` (ví dụ: `IPADA16-W128-SILVER`).
    - Thiết lập giá bán: `A16 Wifi 128GB` có giá là `9.290.000đ`, các bản cao hơn lần lượt là `11.290.000đ`, `12.290.000đ`, `14.290.000đ` và `15.290.000đ`.
    - Mỗi biến thể được gán tồn kho mặc định là `10` chiếc, trạng thái `"active"`, và đồng bộ hóa `specs`/`attributes` tương thích với frontend.
    - Đặt biến thể `IPADA16-W128-SILVER` (A16 Wifi 128GB màu Bạc) làm mặc định (`is_default = true`).
- Đồng bộ hóa dữ liệu seed: Cập nhật thông số sản phẩm cha trong phần `product_seed` và thay thế các biến thể cũ bằng 20 biến thể mới trong phần `variant_seed` của tệp `init_database.sql`.
- Kết quả kiểm tra:
  - CSDL thực tế được cập nhật đầy đủ và chính xác thông qua kịch bản `update_ipad_a16_variants.py`.
  - Chạy thử nghiệm thành công, các tùy chọn màu và phiên bản hiển thị khớp với hình ảnh.
