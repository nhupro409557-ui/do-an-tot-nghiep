# Content / Video Management Notes

# Update 2026-06-03 iPhone 17 Pro video content

- C?p nh?t n?i dung cho video `iPhone 17 Pro - S?c m?nh Pro trong thi?t k? m?i`.
- Gi? nguy?n `video_url` hi?n c? ?? ng??i d?ng c? th? ch?nh/s?a file video sau.
- B? sung `description`, `content_body`, `cta_label`, `cta_url`, thumbnail t?m t? ?nh s?n ph?m v? li?n k?t s?n ph?m SKU `IP17P`.
- Th?m script d? ph?ng `backend/scripts/update_iphone_17_pro_video_content.py` ?? ch?y l?i khi c?n.

# Update 2026-06-03 admin video Vietnamese encoding fix

- Đã sửa lỗi hiển thị tiếng Việt bị lỗi mã hóa (ký tự `?`) trong tệp giao diện quản lý video [AdminContentTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/components/admin/tabs/AdminContentTab.tsx).
- Cập nhật logic trong [useAdminContentLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/components/admin/hooks/useAdminContentLogic.ts):
  - Khắc phục lỗi gán đúp thuộc tính `userName` bị lỗi ở `serializeContentComments`.
  - Loại bỏ các lệnh gán đúp `setContentNotice` bị lỗi mã hóa ở hàm `handleContentSubmit`.
  - Thay thế chuỗi `'Kh?ch h?ng'` thành `'Khách hàng'` trong định dạng văn bản bình luận.

# Update 2026-06-03 HONOR X9d video publish fix

- Phát hiện video `HONOR X9d 5G - Pin trâu, màn hình sáng, bền bỉ mỗi ngày` đã có file `video_url` và thumbnail nhưng vẫn giữ `status = 'DRAFT'`, nên storefront `/videos` không trả về vì chỉ hiển thị `status = 'PUBLISHED'`.
- Đã cập nhật bản ghi video HONOR X9d sang `status = 'PUBLISHED'`, `is_active = TRUE`, có `published_at`, để trang video người dùng hiển thị được.
- Form quản lý video trong `frontend/src/components/admin/tabs/AdminContentTab.tsx` được bổ sung dropdown `Trạng thái`, giúp admin chuyển video giữa Nháp / Chờ đăng / Đã xuất bản / Lưu trữ sau khi upload file.

# Update 2026-06-03 HONOR X9d draft video content

- Tạo script `backend/scripts/seed_honor_x9d_video_content.py` để chuẩn bị nội dung video nháp cho sản phẩm `HONOR X9d 5G` (`HN-X9D`).
- Script tạo/cập nhật một bản ghi `videos.content_type = 'VIDEO'`, `video_category = 'PRODUCT'`, `status = 'DRAFT'`, `is_active = FALSE`, `video_url = NULL` để admin có thể gắn file video sau rồi mới xuất bản.
- Nội dung đã liên kết với sản phẩm `HN-X9D`, gắn category/subcategory của sản phẩm và dùng ảnh đại diện sản phẩm làm thumbnail tạm.
- Tiêu đề nháp: `HONOR X9d 5G - Pin trâu, màn hình sáng, bền bỉ mỗi ngày`.

## Muc tieu nang cap
- Bien bang `videos` thanh kho noi dung dung chung cho `VIDEO`, `BANNER`, `MARKETING_PAGE`.
- Bo sung quan tri admin cho tao/sua/xoa noi dung, upload media, gan san pham/danh muc, bat/tat hien thi, sap xep thu tu, hen lich dang.
- Chuyen lien ket san pham/danh muc sang bang quan he thay vi JSONB.
- Chuyen comment sang bang rieng de ho tro moderation va mo rong reply thread.
- Doi xoa cung thanh soft delete + co audit actor.

## Du lieu moi
- `content_type`: phan biet video, banner, landing/marketing page.
- `status`: state machine noi dung `DRAFT -> SCHEDULED -> PUBLISHED -> ARCHIVED`.
- `content_body`: noi dung dai cho trang marketing.
- `banner_image_url`, `cta_label`, `cta_url`: dung cho banner/CTA.
- `sort_order`, `scheduled_at`, `published_at`: ho tro sap xep va hen lich dang.
- `deleted_at`: phuc vu soft delete.
- `created_by`, `updated_by`: truy vet ai tao/cap nhat noi dung.
- `version`: optimistic locking tranh ghi de khi 2 admin sua cung luc.

## Quy uoc domain
- Ve mat domain, module nay da la `Content Hub`.
- Ten bang vat ly van la `videos` de tai su dung schema cu va giam rui ro migration lon.
- Trong tai lieu luan van can note ro:
  - logical domain: `content entries`
  - physical table legacy: `videos`

## Chuan hoa mo hinh du lieu
- `content_product_relations`
  - `content_id -> videos.id`
  - `product_id -> products.id`
  - dung `ON DELETE CASCADE` de tranh ID "chet"
- `content_category_relations`
  - `content_id -> videos.id`
  - `category_id -> categories.id`
- `content_comments`
  - luu comment theo dong
  - ho tro `parent_id` cho reply thread
  - co `is_hidden`, `deleted_at`, `created_by`, `updated_by`

## API admin
- `GET /admin/content`: tra ve danh sach day du metadata + danh sach san pham/danh muc lien ket.
- `POST /admin/content`: tao noi dung moi.
- `PATCH /admin/content/{id}`: cap nhat noi dung.
- `DELETE /admin/content/{id}`: soft delete noi dung (`deleted_at = NOW()`).
- Moi thao tac tao/sua/xoa deu ghi `security_audit_logs`.
- Update phai gui `version`; neu sai version thi backend tra conflict de admin reload.

## Giao dien admin
- Tab `Video & noi dung` da chuyen tu danh sach don gian sang form popup + bang thao tac.
- Admin co the:
  - upload video / thumbnail / banner
  - nhap san pham, danh muc lien ket
  - quan ly comments, likes, views
  - hen lich dang va chon thu tu hien thi
- Thumbnail cua video la tuy chon:
  - co the co anh dai dien de hien thi truoc khi play
  - co the khong co, he thong van cho phep video duoc xuat ban

## Bao mat upload
- Folder `content` chi nhan:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
  - `video/mp4`
  - `video/webm`
- Gioi han kich thuoc:
  - anh noi dung: toi da 5MB
  - video noi dung: toi da 500MB
- Neu dung direct-to-cloud:
  - Backend phai tao presigned payload co `content-length-range`
  - ep `Content-Type`
  - key phai nam trong prefix `content/`
  - muc tieu la de cloud tu choi file sai ngay tai lop storage
- Validation nghiep vu:
  - `videoUrl` chi chap nhan `.mp4` hoac `.webm`
  - `scheduledAt` phai lon hon thoi diem hien tai it nhat 5 phut
  - `publishedAt` khong duoc som hon `scheduledAt`

## Orphaned files
- Neu direct-to-cloud upload thanh cong nhung transaction DB rollback, file media co the tro thanh rac luu tru.
- Huong xu ly de dua vao luan van:
  - gan tag tam thoi `pending`
  - chi doi sang `confirmed` sau khi DB commit thanh cong
  - bucket lifecycle rule hoac cron job se xoa file `pending` qua han

## Giao dich ACID
- Cac thao tac `create/update/delete content` phai nam trong cung mot transaction.
- Mot lan ghi bao gom:
  - bang `videos`
  - bang `content_product_relations`
  - bang `content_category_relations`
  - bang `content_comments`
  - bang `security_audit_logs`
- Neu mot buoc loi thi rollback toan bo de tranh du lieu mo coi.

## Storefront performance
- `GET /videos` da co:
  - pagination `page`, `limit`
  - Redis cache TTL 300s
  - cache invalidation khi admin tao/sua/xoa content
- Chi tra ve video:
  - `is_active = TRUE`
  - `deleted_at IS NULL`
  - `scheduled_at <= NOW()` hoac khong co lich

## Indexing
- Feed storefront can:
  - composite index tren `is_active, deleted_at, published_at, sort_order, created_at`
- Tim kiem admin can:
  - GIN full-text index tren `title + description + content_body`

## Cache invalidation
- Khong flush all Redis key.
- Moi trang cache storefront duoc ghi vao set theo doi `storefront:content:videos:keys`.
- Khi admin tao/sua/xoa content:
  - chi xoa cac key trong set nay
  - sau do xoa chinh set theo doi
- Cach nay giam nguy co cache stampede so voi xoa cache toan he thong.
- Neu can tiep tuc nang cap:
  - co the doi sang event-driven invalidation de khong lam cham response admin
  - co the gan tag rieng cho home/list/detail

## Truy van list
- Danh sach admin nen uu tien preview (`contentBodyPreview`) thay vi body day du neu bo sung API detail rieng.
- Ban hien tai van giu `contentBody` trong payload edit de khong vo UX popup sua co san.

## Ghi chu tiep theo
- 2026-05-28: Video da duoc tach thanh module admin rieng qua `/admin/videos`.
  - Van dung bang vat ly `videos`, nhung video admin chi thao tac `content_type = 'VIDEO'`.
  - Them `video_source` (`UPLOAD`, `YOUTUBE`) va `video_category` (`PRODUCT`, `NEWS`, `TIPS`, `SERVICE`, `REVIEW`, `OTHER`).
  - Admin khong nhap tay `like_count`/`view_count`; like doc tu bang `video_likes`, view tang qua endpoint storefront.
  - Xoa video qua `/admin/videos/{id}` la hard delete; comment/like/relations xoa cascade.
  - Comment video gioi han 2 cap: comment goc va reply; reply vao reply van gan ve comment goc va luu `reply_to_user_name`.
  - Comment co tu nhay cam duoc tu dong `is_hidden = TRUE` va luu `moderation_reason`.
  - Admin co the doc comment, tra loi comment, va an/hien comment trong man hinh quan ly video.
- Neu can banner carousel/slot theo vi tri, bo sung `placement_code` va `audience_rules`.
- Neu can tracking view/like thuc te, tao endpoint storefront rieng thay vi nhap tay so lieu trong admin.
- Neu traffic video lon hon nua, chuyen pagination sang cursor-based va tach feed recommendation rieng.

## Update 2026-06-02 storefront video like modal
- Trang `/video` gom trạng thái tim về `VideoPage` để thẻ video và modal Reels dùng chung `likedIds`.
- Khi bấm tim trong modal hoặc lưới video, giao diện cập nhật số lượt tim lạc quan ngay, sau đó đồng bộ lại theo `likeCount`/`liked` từ endpoint `/videos/{id}/like`.
- Nút tim trong Reels dùng đúng video của từng slide thay vì phụ thuộc state `currentVideo`, tránh lệch khi Swiper giữ nhiều slide trong DOM.
- Reels không reset `activeIdx`/trạng thái phát chỉ vì `playlist` đổi sau khi cập nhật lượt tim; effect reset chỉ chạy khi mở modal hoặc đổi `initialIndex`.
- Reels lưu lựa chọn bật/tắt tiếng trong `localStorage` bằng key `video_reels_muted`; sau khi người dùng bật tiếng, lần mở modal tiếp theo giữ nguyên bật tiếng thay vì tự mute lại.
- Khi vào bằng URL `?watch=...` rồi bấm đóng modal, trang ghi nhớ video vừa đóng để tránh effect đọc query cũ mở modal lại, khắc phục tình trạng phải bấm nút X hai lần.
## Update 2026-06-03 admin video delete
- Nút xóa video trong tab quản trị nội dung gọi qua `deleteContentVideo` của `useAdminContentLogic` để dùng đúng API client và tải lại danh sách sau khi xóa.
- `DELETE /admin/videos/{id}` chuyển từ xóa cứng sang xóa mềm: đặt `deleted_at`, tắt `is_active`, chuyển `status` sang `ARCHIVED`, tăng `version` và ghi `updated_by`.
- Việc xóa mềm giúp tránh lỗi khóa ngoại với bình luận, lượt thích, lượt xem hoặc quan hệ sản phẩm/danh mục, đồng thời vẫn làm mất video khỏi danh sách admin/storefront vì các truy vấn đang lọc `deleted_at IS NULL`.
# Update 2026-06-03 homepage banner management

- Thêm luồng quản lý banner trang chủ dùng lại Content Hub hiện có (`videos.content_type = 'BANNER'`) để tránh tạo kho dữ liệu banner trùng lặp.
- Backend bổ sung API admin riêng cho banner:
  - `GET /admin/banners`
  - `POST /admin/banners`
  - `PATCH /admin/banners/{banner_id}`
  - `DELETE /admin/banners/{banner_id}`
- Backend bổ sung API storefront `GET /banners` để trang chủ lấy banner đã xuất bản.
- Mỗi banner bắt buộc có danh mục đi kèm. Sản phẩm đi kèm là tùy chọn:
  - Nếu có sản phẩm, banner dẫn đến trang chi tiết sản phẩm.
  - Nếu không có sản phẩm, banner dẫn đến trang danh sách sản phẩm theo danh mục.
- Frontend admin có tab riêng `Banner` với popup thêm/sửa gồm tiêu đề, mô tả cực ngắn, ảnh banner, danh mục, sản phẩm tùy chọn, thứ tự và trạng thái hiển thị.
- Trang chủ `HomeBanner` đổi sang layout gần CellphoneS: dải tab tiêu đề/mô tả ngắn phía trên và ảnh banner lớn phía dưới, tự chạy slide và cho click theo link của banner.
