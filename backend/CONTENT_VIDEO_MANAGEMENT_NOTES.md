# Content / Video Management Notes

# Update 2026-06-03 admin video Vietnamese encoding fix

- Đã sửa lỗi hiển thị tiếng Việt bị lỗi mã hóa (ký tự `?`) trong tệp giao diện quản lý video [AdminContentTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-content/components/AdminContentTab.tsx).
- Cập nhật logic trong [useAdminContentLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-content/hooks/useAdminContentLogic.ts):
  - Khắc phục lỗi gán đúp thuộc tính `userName` bị lỗi ở `serializeContentComments`.
  - Loại bỏ các lệnh gán đúp `setContentNotice` bị lỗi mã hóa ở hàm `handleContentSubmit`.
  - Thay thế chuỗi `'Kh?ch h?ng'` thành `'Khách hàng'` trong định dạng văn bản bình luận.

# Update 2026-06-03 HONOR X9d video publish fix

- Phát hiện video `HONOR X9d 5G - Pin trâu, màn hình sáng, bền bỉ mỗi ngày` đã có file `video_url` và thumbnail nhưng vẫn giữ `status = 'DRAFT'`, nên storefront `/videos` không trả về vì chỉ hiển thị `status = 'PUBLISHED'`.
- Đã cập nhật bản ghi video HONOR X9d sang `status = 'PUBLISHED'`, `is_active = TRUE`, có `published_at`, để trang video người dùng hiển thị được.
- Form quản lý video trong `frontend/src/features/admin-content/components/AdminContentTab.tsx` được bổ sung dropdown `Trạng thái`, giúp admin chuyển video giữa Nháp / Chờ đăng / Đã xuất bản / Lưu trữ sau khi upload file.

# Update 2026-06-03 HONOR X9d draft video content

- Tạo script `backend/scripts/seed_honor_x9d_video_content.py` để chuẩn bị nội dung video nháp cho sản phẩm `HONOR X9d 5G` (`HN-X9D`).
- Script tạo/cập nhật một bản ghi `videos.content_type = 'VIDEO'`, `video_category = 'PRODUCT'`, `status = 'DRAFT'`, `is_active = FALSE`, `video_url = NULL` để admin có thể gắn file video sau rồi mới xuất bản.
- Nội dung đã liên kết với sản phẩm `HN-X9D`, gắn category/subcategory của sản phẩm và dùng ảnh đại diện sản phẩm làm thumbnail tạm.
- Tiêu đề nháp: `HONOR X9d 5G - Pin trâu, màn hình sáng, bền bỉ mỗi ngày`.

## Mục tiêu nâng cấp
- Biến bảng `videos` thành kho nội dung dùng chung cho `VIDEO`, `BANNER`, `MARKETING_PAGE`.
- Bổ sung quản trị admin cho tạo/sửa/xóa nội dung, upload media, gán sản phẩm/danh mục, bật/tắt hiển thị, sắp xếp thứ tự, hẹn lịch đăng.
- Chuyển liên kết sản phẩm/danh mục sang bảng quan hệ thay vì JSONB.
- Chuyển bình luận (comment) sang bảng riêng để hỗ trợ kiểm duyệt (moderation) và mở rộng luồng phản hồi (reply thread).
- Đổi xóa cứng thành xóa mềm (soft delete) + có ghi nhận tác nhân thực hiện (audit actor).

## Dữ liệu mới
- `content_type`: phân biệt video, banner, landing/marketing page.
- `status`: máy trạng thái (state machine) nội dung `DRAFT -> SCHEDULED -> PUBLISHED -> ARCHIVED`.
- `content_body`: nội dung dài cho trang marketing.
- `banner_image_url`, `cta_label`, `cta_url`: dùng cho banner/CTA.
- `sort_order`, `scheduled_at`, `published_at`: hỗ trợ sắp xếp và hẹn lịch đăng.
- `deleted_at`: phục vụ xóa mềm (soft delete).
- `created_by`, `updated_by`: truy vết ai tạo/cập nhật nội dung.
- `version`: khóa lạc quan (optimistic locking) tránh ghi đè khi 2 admin sửa cùng lúc.

## Quy ước domain
- Về mặt domain, mô-đun này đã là `Content Hub`.
- Tên bảng vật lý vẫn là `videos` để tái sử dụng schema cũ và giảm rủi ro migration lớn.
- Trong tài liệu luận văn cần ghi chú rõ:
  - logical domain: `content entries`
  - physical table legacy: `videos`

## Chuẩn hóa mô hình dữ liệu
- `content_product_relations`
  - `content_id -> videos.id`
  - `product_id -> products.id`
  - Dùng `ON DELETE CASCADE` để tránh ID "chết"
- `content_category_relations`
  - `content_id -> videos.id`
  - `category_id -> categories.id`
- `content_comments`
  - Lưu comment theo dòng
  - Hỗ trợ `parent_id` cho reply thread
  - Có `is_hidden`, `deleted_at`, `created_by`, `updated_by`

## API admin
- `GET /admin/content`: trả về danh sách đầy đủ metadata + danh sách sản phẩm/danh mục liên kết.
- `POST /admin/content`: tạo nội dung mới.
- `PATCH /admin/content/{id}`: cập nhật nội dung.
- `DELETE /admin/content/{id}`: xóa mềm nội dung (`deleted_at = NOW()`).
- Mỗi thao tác tạo/sửa/xóa đều ghi `security_audit_logs`.
- Cập nhật phải gửi `version`; nếu sai version thì backend trả về lỗi xung đột (conflict) để admin tải lại.

## Giao diện admin
- Tab `Video & nội dung` đã chuyển từ danh sách đơn giản sang form popup + bảng thao tác.
- Admin có thể:
  - Tải lên (upload) video / ảnh thu nhỏ (thumbnail) / ảnh banner
  - Nhập sản phẩm, danh mục liên kết
  - Quản lý bình luận (comments), lượt thích (likes), lượt xem (views)
  - Hẹn lịch đăng và chọn thứ tự hiển thị
- Ảnh thu nhỏ (thumbnail) của video là tùy chọn:
  - Có thể có ảnh đại diện để hiển thị trước khi phát video
  - Có thể không có, hệ thống vẫn cho phép video được xuất bản

## Bảo mật tải lên (upload)
- Thư mục `content` chỉ nhận:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
  - `video/mp4`
  - `video/webm`
- Giới hạn kích thước:
  - Ảnh nội dung: tối đa 5MB
  - Video nội dung: tối đa 500MB
- Nếu dùng direct-to-cloud:
  - Backend phải tạo presigned payload có `content-length-range`
  - Ép `Content-Type`
  - Key phải nằm trong tiền tố `content/`
  - Mục tiêu là để dịch vụ đám mây từ chối file sai ngay tại lớp lưu trữ (storage)
- Xác thực (validation) nghiệp vụ:
  - `videoUrl` chỉ chấp nhận đuôi `.mp4` hoặc `.webm`
  - `scheduledAt` phải lớn hơn thời điểm hiện tại ít nhất 5 phút
  - `publishedAt` không được sớm hơn `scheduledAt`

## Tệp mồ côi (Orphaned files)
- Nếu tải trực tiếp lên đám mây (direct-to-cloud upload) thành công nhưng giao dịch (transaction) DB bị rollback, file media có thể trở thành rác lưu trữ.
- Hướng xử lý để đưa vào luận văn:
  - Gán nhãn (tag) tạm thời `pending`
  - Chỉ đổi sang `confirmed` sau khi DB commit thành công
  - Quy tắc vòng đời của bucket (lifecycle rule) hoặc cron job sẽ xóa file `pending` quá hạn

## Giao dịch ACID
- Các thao tác `create/update/delete content` phải nằm trong cùng một transaction.
- Một lần ghi bao gồm:
  - Bảng `videos`
  - Bảng `content_product_relations`
  - Bảng `content_category_relations`
  - Bảng `content_comments`
  - Bảng `security_audit_logs`
- Nếu một bước lỗi thì rollback toàn bộ để tránh dữ liệu mồ côi.

## Hiệu năng Storefront
- `GET /videos` đã có:
  - Phân trang `page`, `limit`
  - Bộ nhớ đệm Redis (cache) với thời gian sống (TTL) 300 giây
  - Vô hiệu hóa cache (invalidation) khi admin tạo/sửa/xóa nội dung
- Chỉ trả về video:
  - `is_active = TRUE`
  - `deleted_at IS NULL`
  - `scheduled_at <= NOW()` hoặc không có lịch

## Đánh chỉ mục (Indexing)
- Feed storefront cần:
  - Composite index trên `is_active`, `deleted_at`, `published_at`, `sort_order`, `created_at`
- Tìm kiếm admin cần:
  - GIN full-text index trên `title + description + content_body`

## Vô hiệu hóa bộ nhớ đệm (Cache invalidation)
- Không xóa sạch tất cả (flush all) các khóa Redis.
- Mỗi trang cache storefront được ghi vào tập hợp theo dõi `storefront:content:videos:keys`.
- Khi admin tạo/sửa/xóa nội dung:
  - Chỉ xóa các key trong set này
  - Sau đó xóa chính set theo dõi
- Cách này giảm nguy cơ nghẽn cache (cache stampede) so với việc xóa cache toàn hệ thống.
- Nếu cần tiếp tục nâng cấp:
  - Có thể đổi sang cơ chế xóa dựa trên sự kiện (event-driven invalidation) để không làm chậm phản hồi của admin
  - Có thể gán nhãn (tag) riêng cho trang chủ (home)/danh sách (list)/chi tiết (detail)

## Truy vấn danh sách
- Danh sách admin nên ưu tiên hiển thị bản xem trước (`contentBodyPreview`) thay vì toàn bộ phần thân nếu bổ sung API chi tiết riêng.
- Bản hiện tại vẫn giữ `contentBody` trong payload chỉnh sửa để không làm hỏng trải nghiệm người dùng (UX) popup sửa có sẵn.

## Ghi chú tiếp theo
- 2026-05-28: Video đã được tách thành mô-đun admin riêng qua `/admin/videos`.
  - Vẫn dùng bảng vật lý `videos`, nhưng video admin chỉ thao tác trên `content_type = 'VIDEO'`.
  - Thêm `video_source` (`UPLOAD`, `YOUTUBE`) và `video_category` (`PRODUCT`, `NEWS`, `TIPS`, `SERVICE`, `REVIEW`, `OTHER`).
  - Admin không nhập tay lượt thích (`like_count`) / lượt xem (`view_count`); lượt thích được đọc từ bảng `video_likes`, lượt xem tăng qua endpoint storefront.
  - Xóa video qua `/admin/videos/{id}` là xóa cứng (hard delete); bình luận/lượt thích/mối quan hệ sẽ được xóa liên đới (cascade).
  - Bình luận video giới hạn 2 cấp: bình luận gốc và phản hồi; phản hồi vào phản hồi vẫn gán về bình luận gốc và lưu `reply_to_user_name`.
  - Bình luận có từ nhạy cảm được tự động ẩn `is_hidden = TRUE` và lưu `moderation_reason`.
  - Admin có thể đọc bình luận, trả lời bình luận, và ẩn/hiện bình luận trong màn hình quản lý video.
- Nếu cần banner xoay vòng (carousel)/vị trí (slot) theo vị trí, bổ sung `placement_code` và `audience_rules`.
- Nếu cần theo dõi (tracking) lượt xem/thích thực tế, tạo endpoint storefront riêng thay vì nhập tay số liệu trong admin.
- Nếu lưu lượng (traffic) video lớn hơn nữa, chuyển phân trang sang dạng con trỏ (cursor-based) và tách feed gợi ý (recommendation) riêng.

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

# Update 2026-06-04 refactor Module Content & Banners

- **Frontend**: Chuyển đổi Module Content & Banners sang kiến trúc hướng tính năng (**Feature-First Architecture**).
  - Di chuyển toàn bộ giao diện quản trị (`AdminContentTab.tsx`, `AdminBannersTab.tsx`), custom hooks (`useAdminContentLogic.ts`, `useAdminBannersLogic.ts`) và API client (`adminContentApi.ts`) vào thư mục mới `src/features/admin-content/`.
- **Backend**: Tách logic nghiệp vụ và truy vấn database ra khỏi file router `admin_content.py` sang Service Layer mới (`app/application/services/content_service.py`).
  - File router `admin_content.py` chỉ làm nhiệm vụ tiếp nhận request và chuyển tiếp xử lý sang `content_service.py` giúp giữ code sạch sẽ và tách biệt nghiệp vụ.
