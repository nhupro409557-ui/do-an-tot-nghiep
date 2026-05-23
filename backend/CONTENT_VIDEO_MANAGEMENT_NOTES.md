# Content / Video Management Notes

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
- Neu can banner carousel/slot theo vi tri, bo sung `placement_code` va `audience_rules`.
- Neu can tracking view/like thuc te, tao endpoint storefront rieng thay vi nhap tay so lieu trong admin.
- Neu traffic video lon hon nua, chuyen pagination sang cursor-based va tach feed recommendation rieng.
