# Content / Video Management Notes

# Update 2026-06-03 iPhone 17 Pro video content

- C?p nh?t n?i dung cho video `iPhone 17 Pro - S?c m?nh Pro trong thi?t k? m?i`.
- Gi? nguy?n `video_url` hi?n c? ?? ng??i d?ng c? th? ch?nh/s?a file video sau.
- B? sung `description`, `content_body`, `cta_label`, `cta_url`, thumbnail t?m t? ?nh s?n ph?m v? li?n k?t s?n ph?m SKU `IP17P`.
- Th?m script d? ph?ng `backend/scripts/update_iphone_17_pro_video_content.py` ?? ch?y l?i khi c?n.

# Update 2026-06-03 admin video Vietnamese encoding fix

- ÄÃ£ sá»­a lá»—i hiá»ƒn thá»‹ tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a (kÃ½ tá»± `?`) trong tá»‡p giao diá»‡n quáº£n lÃ½ video [AdminContentTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-content/components/AdminContentTab.tsx).
- Cáº­p nháº­t logic trong [useAdminContentLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-content/hooks/useAdminContentLogic.ts):
  - Kháº¯c phá»¥c lá»—i gÃ¡n Ä‘Ãºp thuá»™c tÃ­nh `userName` bá»‹ lá»—i á»Ÿ `serializeContentComments`.
  - Loáº¡i bá» cÃ¡c lá»‡nh gÃ¡n Ä‘Ãºp `setContentNotice` bá»‹ lá»—i mÃ£ hÃ³a á»Ÿ hÃ m `handleContentSubmit`.
  - Thay tháº¿ chuá»—i `'Kh?ch h?ng'` thÃ nh `'KhÃ¡ch hÃ ng'` trong Ä‘á»‹nh dáº¡ng vÄƒn báº£n bÃ¬nh luáº­n.

# Update 2026-06-03 HONOR X9d video publish fix

- PhÃ¡t hiá»‡n video `HONOR X9d 5G - Pin trÃ¢u, mÃ n hÃ¬nh sÃ¡ng, bá»n bá»‰ má»—i ngÃ y` Ä‘Ã£ cÃ³ file `video_url` vÃ  thumbnail nhÆ°ng váº«n giá»¯ `status = 'DRAFT'`, nÃªn storefront `/videos` khÃ´ng tráº£ vá» vÃ¬ chá»‰ hiá»ƒn thá»‹ `status = 'PUBLISHED'`.
- ÄÃ£ cáº­p nháº­t báº£n ghi video HONOR X9d sang `status = 'PUBLISHED'`, `is_active = TRUE`, cÃ³ `published_at`, Ä‘á»ƒ trang video ngÆ°á»i dÃ¹ng hiá»ƒn thá»‹ Ä‘Æ°á»£c.
- Form quáº£n lÃ½ video trong `frontend/src/features/admin-content/components/AdminContentTab.tsx` Ä‘Æ°á»£c bá»• sung dropdown `Tráº¡ng thÃ¡i`, giÃºp admin chuyá»ƒn video giá»¯a NhÃ¡p / Chá» Ä‘Äƒng / ÄÃ£ xuáº¥t báº£n / LÆ°u trá»¯ sau khi upload file.

# Update 2026-06-03 HONOR X9d draft video content

- Táº¡o script `backend/scripts/seed_honor_x9d_video_content.py` Ä‘á»ƒ chuáº©n bá»‹ ná»™i dung video nhÃ¡p cho sáº£n pháº©m `HONOR X9d 5G` (`HN-X9D`).
- Script táº¡o/cáº­p nháº­t má»™t báº£n ghi `videos.content_type = 'VIDEO'`, `video_category = 'PRODUCT'`, `status = 'DRAFT'`, `is_active = FALSE`, `video_url = NULL` Ä‘á»ƒ admin cÃ³ thá»ƒ gáº¯n file video sau rá»“i má»›i xuáº¥t báº£n.
- Ná»™i dung Ä‘Ã£ liÃªn káº¿t vá»›i sáº£n pháº©m `HN-X9D`, gáº¯n category/subcategory cá»§a sáº£n pháº©m vÃ  dÃ¹ng áº£nh Ä‘áº¡i diá»‡n sáº£n pháº©m lÃ m thumbnail táº¡m.
- TiÃªu Ä‘á» nhÃ¡p: `HONOR X9d 5G - Pin trÃ¢u, mÃ n hÃ¬nh sÃ¡ng, bá»n bá»‰ má»—i ngÃ y`.

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
- Trang `/video` gom tráº¡ng thÃ¡i tim vá» `VideoPage` Ä‘á»ƒ tháº» video vÃ  modal Reels dÃ¹ng chung `likedIds`.
- Khi báº¥m tim trong modal hoáº·c lÆ°á»›i video, giao diá»‡n cáº­p nháº­t sá»‘ lÆ°á»£t tim láº¡c quan ngay, sau Ä‘Ã³ Ä‘á»“ng bá»™ láº¡i theo `likeCount`/`liked` tá»« endpoint `/videos/{id}/like`.
- NÃºt tim trong Reels dÃ¹ng Ä‘Ãºng video cá»§a tá»«ng slide thay vÃ¬ phá»¥ thuá»™c state `currentVideo`, trÃ¡nh lá»‡ch khi Swiper giá»¯ nhiá»u slide trong DOM.
- Reels khÃ´ng reset `activeIdx`/tráº¡ng thÃ¡i phÃ¡t chá»‰ vÃ¬ `playlist` Ä‘á»•i sau khi cáº­p nháº­t lÆ°á»£t tim; effect reset chá»‰ cháº¡y khi má»Ÿ modal hoáº·c Ä‘á»•i `initialIndex`.
- Reels lÆ°u lá»±a chá»n báº­t/táº¯t tiáº¿ng trong `localStorage` báº±ng key `video_reels_muted`; sau khi ngÆ°á»i dÃ¹ng báº­t tiáº¿ng, láº§n má»Ÿ modal tiáº¿p theo giá»¯ nguyÃªn báº­t tiáº¿ng thay vÃ¬ tá»± mute láº¡i.
- Khi vÃ o báº±ng URL `?watch=...` rá»“i báº¥m Ä‘Ã³ng modal, trang ghi nhá»› video vá»«a Ä‘Ã³ng Ä‘á»ƒ trÃ¡nh effect Ä‘á»c query cÅ© má»Ÿ modal láº¡i, kháº¯c phá»¥c tÃ¬nh tráº¡ng pháº£i báº¥m nÃºt X hai láº§n.
## Update 2026-06-03 admin video delete
- NÃºt xÃ³a video trong tab quáº£n trá»‹ ná»™i dung gá»i qua `deleteContentVideo` cá»§a `useAdminContentLogic` Ä‘á»ƒ dÃ¹ng Ä‘Ãºng API client vÃ  táº£i láº¡i danh sÃ¡ch sau khi xÃ³a.
- `DELETE /admin/videos/{id}` chuyá»ƒn tá»« xÃ³a cá»©ng sang xÃ³a má»m: Ä‘áº·t `deleted_at`, táº¯t `is_active`, chuyá»ƒn `status` sang `ARCHIVED`, tÄƒng `version` vÃ  ghi `updated_by`.
- Viá»‡c xÃ³a má»m giÃºp trÃ¡nh lá»—i khÃ³a ngoáº¡i vá»›i bÃ¬nh luáº­n, lÆ°á»£t thÃ­ch, lÆ°á»£t xem hoáº·c quan há»‡ sáº£n pháº©m/danh má»¥c, Ä‘á»“ng thá»i váº«n lÃ m máº¥t video khá»i danh sÃ¡ch admin/storefront vÃ¬ cÃ¡c truy váº¥n Ä‘ang lá»c `deleted_at IS NULL`.
# Update 2026-06-03 homepage banner management

- ThÃªm luá»“ng quáº£n lÃ½ banner trang chá»§ dÃ¹ng láº¡i Content Hub hiá»‡n cÃ³ (`videos.content_type = 'BANNER'`) Ä‘á»ƒ trÃ¡nh táº¡o kho dá»¯ liá»‡u banner trÃ¹ng láº·p.
- Backend bá»• sung API admin riÃªng cho banner:
  - `GET /admin/banners`
  - `POST /admin/banners`
  - `PATCH /admin/banners/{banner_id}`
  - `DELETE /admin/banners/{banner_id}`
- Backend bá»• sung API storefront `GET /banners` Ä‘á»ƒ trang chá»§ láº¥y banner Ä‘Ã£ xuáº¥t báº£n.
- Má»—i banner báº¯t buá»™c cÃ³ danh má»¥c Ä‘i kÃ¨m. Sáº£n pháº©m Ä‘i kÃ¨m lÃ  tÃ¹y chá»n:
  - Náº¿u cÃ³ sáº£n pháº©m, banner dáº«n Ä‘áº¿n trang chi tiáº¿t sáº£n pháº©m.
  - Náº¿u khÃ´ng cÃ³ sáº£n pháº©m, banner dáº«n Ä‘áº¿n trang danh sÃ¡ch sáº£n pháº©m theo danh má»¥c.
- Frontend admin cÃ³ tab riÃªng `Banner` vá»›i popup thÃªm/sá»­a gá»“m tiÃªu Ä‘á», mÃ´ táº£ cá»±c ngáº¯n, áº£nh banner, danh má»¥c, sáº£n pháº©m tÃ¹y chá»n, thá»© tá»± vÃ  tráº¡ng thÃ¡i hiá»ƒn thá»‹.
- Trang chá»§ `HomeBanner` Ä‘á»•i sang layout gáº§n CellphoneS: dáº£i tab tiÃªu Ä‘á»/mÃ´ táº£ ngáº¯n phÃ­a trÃªn vÃ  áº£nh banner lá»›n phÃ­a dÆ°á»›i, tá»± cháº¡y slide vÃ  cho click theo link cá»§a banner.

# Update 2026-06-04 refactor Module Content & Banners

- **Frontend**: Chuyá»ƒn Ä‘á»•i Module Content & Banners sang kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (**Feature-First Architecture**).
  - Di chuyá»ƒn toÃ n bá»™ giao diá»‡n quáº£n trá»‹ (`AdminContentTab.tsx`, `AdminBannersTab.tsx`), custom hooks (`useAdminContentLogic.ts`, `useAdminBannersLogic.ts`) vÃ  API client (`adminContentApi.ts`) vÃ o thÆ° má»¥c má»›i `src/features/admin-content/`.
  - Cáº­p nháº­t import liÃªn quan táº¡i `apiDb.ts`, `useAdminLogic.ts`, vÃ  `AdminDashboardTabContent.tsx`.
- **Backend**: TÃ¡ch logic nghiá»‡p vá»¥ vÃ  truy váº¥n database ra khá»i file router `admin_content.py` sang Service Layer má»›i (`app/application/services/content_service.py`).
  - File router `admin_content.py` chá»‰ lÃ m nhiá»‡m vá»¥ tiáº¿p nháº­n request vÃ  chuyá»ƒn tiáº¿p xá»­ lÃ½ sang `content_service.py` giÃºp giá»¯ code sáº¡ch sáº½ vÃ  tÃ¡ch biá»‡t nghiá»‡p vá»¥.

