# Category Management Notes

This file records the non-obvious decisions added while hardening category management.

## Files to review first

- `backend/app/api/v1/routers/admin.py`
- `backend/app/api/v1/routers/catalog.py`

## What was added

1. Migration branch lock

- Helper: `ensure_categories_not_migrating(...)`
- Purpose: blocks write actions when a category branch has a running migration job.
- Coverage:
  - category create/update/delete/reorder/bulk update
  - product create/update
  - product status changes
  - product delete/archive

2. Workflow lock marker

- Category `workflow_status` is temporarily set to `MIGRATING` when parent changes create a migration job.
- Reset happens in `process_category_migration_job(...)` on both success and failure.

3. Redirect chain flattening

- Helper: `record_category_redirect(...)`
- Purpose: when slug changes from `C` to `D`, older redirects pointing to `C` are updated to point directly to `D`.
- This avoids long SEO redirect chains.

4. Product behavior on category soft delete

- Helper: `deactivate_products_in_category_branch(...)`
- Rule: products inside the deleted category branch are automatically moved to `INACTIVE`, and variants are disabled.
- Reason: prevents "active product / hidden taxonomy" mismatch on storefront.

5. Partial category cache refresh

- Cache is now split by root branch.
- Keys:
  - `catalog:categories:roots:active`
  - `catalog:categories:roots:stale`
  - `catalog:categories:branch:{rootId}:active`
  - `catalog:categories:branch:{rootId}:stale`
- Public catalog reads branch caches first, then falls back to old full-tree fallback.

6. Migration watchdog / stale job recovery

- Constant: `CATEGORY_MIGRATION_STALE_MINUTES = 30`
- Helper: `recover_stale_category_migrations(...)`
- Purpose: detect migration jobs stuck in `PENDING/RUNNING/IN_PROGRESS` beyond the timeout window.
- Behavior:
  - mark stale jobs as `FAILED`
  - release category `workflow_status` from `MIGRATING`
  - expose stale/recovered counts through category ops metrics
- This is an in-process self-healing fallback, not a full DLQ implementation.

7. Restore UX safety notice

- Frontend restore action now warns admins that category restore does not automatically reactivate products.
- File: `frontend/src/pages/AdminDashboard.tsx`

8. Frontend concurrency message

- Frontend now translates version mismatch / `409 Conflict` style responses into a clearer admin message.
- File: `frontend/src/pages/AdminDashboard.tsx`

9. Category-only refresh path in Admin Dashboard

- Frontend now has a dedicated `loadCategoryWorkspace(...)` flow instead of forcing a full dashboard reload after every category mutation.
- Coverage:
  - create/update/reorder/restore category
  - category edit side data refresh
- Reason:
  - reduces the perceived delay after category edits
  - avoids re-fetching unrelated tabs such as vouchers, reviews, permissions on every category save

10. Category operational telemetry surfaced in UI

- Frontend now consumes:
  - `GET /admin/categories/ops/metrics`
  - `GET /admin/categories/{id}/audit-logs`
  - `GET /admin/categories/{id}/migration-jobs`
- Purpose:
  - show cache hit ratio / P99 latency / running migration jobs
  - expose audit history and migration progress for the category being edited
- File: `frontend/src/pages/AdminDashboard.tsx`

11. Migration job auto-polling while editing category

- When the selected category has `PENDING/RUNNING/IN_PROGRESS` migration jobs, the category workspace now auto-refreshes on an interval.
- Purpose:
  - helps admins observe long-running parent-change migrations without manually reloading the whole dashboard
- File: `frontend/src/pages/AdminDashboard.tsx`

## Maintenance guidance

1. If you add a new product write endpoint, also call `ensure_categories_not_migrating(...)`.
2. If you add a new category mutation endpoint, also refresh affected root caches via `enqueue_category_cache_refresh(...)`.
3. If category tree depth or inheritance rules change, review:
   - `ensure_no_category_cycle(...)`
   - `ensure_category_depth(...)`
   - `ensure_spec_inheritance_safe(...)`
4. If storefront starts needing full nested trees beyond one child level, update both:
   - `fetch_visible_category_branch(...)`
   - `read_category_tree_from_branch_cache(...)`
5. If the app later gets a scheduler/worker platform, move `recover_stale_category_migrations(...)` to a proper cron or DLQ workflow instead of relying on opportunistic request-time cleanup.
6. If category admin grows further, keep new diagnostics under the category-only refresh path instead of reusing the full `loadData()` dashboard fetch.

## Business assumptions introduced in this pass

1. During category migration, branch writes are blocked instead of allowed with eventual reconciliation.
2. Soft deleting a category branch unlists products instead of moving them to an "uncategorized" bucket.
3. Restoring a category does not auto-reactivate products that were inactivated by the delete flow.
4. Stale migration jobs older than 30 minutes are treated as failed and their category workflow lock is released automatically.
5. Category operators benefit from seeing operational telemetry in the same screen as category edits, not only through backend logs.

## Update 2026-06-04 admin category slug validation

- Slug danh mục được chuẩn hóa tiếng Việt đúng dấu khi tự sinh từ tên, bao gồm trường hợp có chữ `đ`/`Đ`.
- Khi thêm danh mục mà để trống slug, backend tự sinh slug dạng `ten-danh-muc-xxxxx` để hạn chế trùng.
- Khi sửa danh mục, kiểm tra trùng slug/mã vẫn loại trừ chính danh mục đang sửa; lỗi trả về được tách rõ giữa `Slug danh mục đã tồn tại.` và `Mã danh mục đã tồn tại.`.
- Frontend hiển thị trực tiếp thông báo lỗi backend khi lưu danh mục thất bại để admin biết đang trùng slug hay trùng mã.
- Sửa lỗi lưu danh mục bị backend trả 500/CORS giả do các helper async gọi `.scalar()` trên coroutine `session.execute`; nay kết quả execute được await trước khi đọc scalar.
- Đã khởi động lại backend local trên port 8000 để process đang chạy dùng code mới.
- CORS middleware được đặt bọc ngoài audit middleware để khi backend có lỗi thật, trình duyệt vẫn nhận `Access-Control-Allow-Origin` và frontend thấy lỗi API thay vì thông báo CORS gây nhiễu.

## Update 2026-05-23

- Danh muc co them `inventory_policy` de quy dinh quan ly IMEI:
  - `inheritImeiPolicy`: danh muc con co lay theo cha hay khong.
  - `trackImei`: danh muc nay co quan ly theo IMEI hay khong.
  - Uu tien cao nhat la danh muc con; neu con bat `inheritImeiPolicy` thi bo qua `trackImei` cua con va theo cha.
- Danh muc co them `warranty_policy` de lam mac dinh cho san pham:
  - `inheritWarrantyPolicy`
  - `hasWarranty`
  - `warrantyMonths`
  - `allowOneForOne`
  - `oneForOneDays`
- Cac gia tri tren chi la mac dinh giup admin do nhap lap. San pham van co quyen override trong `products.sales_config.warrantyPolicy` neu bao hanh thuc te khac danh muc.
- Migration lien quan: `backend/migrations/040_catalog_inventory_services_foundation.sql`.
- Product form da nap mac dinh bao hanh tu danh muc cha/con khi san pham bat "theo danh muc"; danh muc con duoc uu tien, tru khi con bat `inheritWarrantyPolicy`.
- Product form co the override `warrantyMonths`, `allowOneForOne`, `oneForOneDays` de xu ly truong hop san pham khac mac dinh danh muc.

## Update 2026-05-30 frontend refactor

- Da tach phan logic va state quan ly danh muc ra khoi `useAdminLogic.ts` sang hook rieng biet `useAdminCategoriesLogic.ts` de lam sach va modul hoa frontend code.


## Update 2026-06-01 admin form completion feedback

- Sau khi thêm hoặc chỉnh sửa danh mục thành công, popup danh mục tự đóng bằng `closeSignal`.
- Admin nhận thông báo thành công rõ ràng sau khi thêm hoặc lưu thay đổi danh mục.
- Việc reset form vẫn được giữ nguyên, nhưng chỉ diễn ra sau khi popup đã được yêu cầu đóng để tránh cảm giác popup chỉnh sửa chuyển thành popup thêm mới.

## Update 2026-06-01 storefront specs alignment

- Mo rong `spec_fields` cho cac danh muc Dien thoai, May tinh bang, Laptop, Phu kien, Dong ho, Camera va May anh de bao phu cac key thong so chi tiet dang co trong san pham.
- Cac field moi dung label tieng Viet tren storefront, vi du: Loai man hinh, Tinh nang camera sau, Wi-Fi, Bluetooth, Chong on, Codec am thanh, Ngam ong kinh.
- Bo sung du lieu thong so mau cho cac san pham truoc do dang rong nhu AirPods Pro 2 USB-C, Anker GaN 100W, Apple Watch Ultra 2, Garmin Fenix 7 Pro, DJI Pocket 3, Ezviz C6N, Sony Alpha A7 IV va OPPO Find N3.
- Chuan hoa key cu `screenSize` sang `screen_size` de khop voi danh muc.

## Update 2026-06-02 storefront category brand menu

- Thanh danh mục storefront chỉ hiển thị thương hiệu theo sản phẩm thực tế thuộc danh mục cha/con hoặc thương hiệu được gắn rõ với danh mục đó.
- Không còn đưa các thương hiệu chưa gắn danh mục vào mọi danh mục, tránh trường hợp Điện thoại hiển thị lẫn Acer, Dell, Canon, DJI.
- `frontend/src/hooks/useCatalog.ts` đã tính cả `subcategoryId`/`subcategorySlug` khi gom sản phẩm cho danh mục cha, nên hãng của danh mục con vẫn xuất hiện đúng trong menu danh mục cha.

## Update 2026-06-02 storefront category ranking suggestions

- `frontend/src/hooks/useCatalog.ts` nay lấy danh sách "Sản phẩm nổi bật" trong mega menu từ `GET /catalog/rankings` theo từng danh mục.
- Nguồn xếp hạng dùng `criteria=trending`, `period=7d`, `limit=10` để ưu tiên sản phẩm đang có hạng trong danh mục đó.
- Nếu ranking trống hoặc API lỗi, menu fallback về danh sách sản phẩm active đã khớp với danh mục để khu đề xuất không bị rỗng.

## Update 2026-06-02 storefront category mega menu layout

- Danh muc co them `inventory_policy` de quy dinh quan ly IMEI:
  - `inheritImeiPolicy`: danh muc con co lay theo cha hay khong.
  - `trackImei`: danh muc nay co quan ly theo IMEI hay khong.
  - Uu tien cao nhat la danh muc con; neu con bat `inheritImeiPolicy` thi bo qua `trackImei` cua con va theo cha.
- Danh muc co them `warranty_policy` de lam mac dinh cho san pham:
  - `inheritWarrantyPolicy`
  - `hasWarranty`
  - `warrantyMonths`
  - `allowOneForOne`
  - `oneForOneDays`
- Cac gia tri tren chi la mac dinh giup admin do nhap lap. San pham van co quyen override trong `products.sales_config.warrantyPolicy` neu bao hanh thuc te khac danh muc.
- Migration lien quan: `backend/migrations/040_catalog_inventory_services_foundation.sql`.
- Product form da nap mac dinh bao hanh tu danh muc cha/con khi san pham bat "theo danh muc"; danh muc con duoc uu tien, tru khi con bat `inheritWarrantyPolicy`.
- Product form co the override `warrantyMonths`, `allowOneForOne`, `oneForOneDays` de xu ly truong hop san pham khac mac dinh danh muc.

## Update 2026-05-30 frontend refactor

- Da tach phan logic va state quan ly danh muc ra khoi `useAdminLogic.ts` sang hook rieng biet `useAdminCategoriesLogic.ts` de lam sach va modul hoa frontend code.


## Update 2026-06-01 admin form completion feedback

- Sau khi thêm hoặc chỉnh sửa danh mục thành công, popup danh mục tự đóng bằng `closeSignal`.
- Admin nhận thông báo thành công rõ ràng sau khi thêm hoặc lưu thay đổi danh mục.
- Việc reset form vẫn được giữ nguyên, nhưng chỉ diễn ra sau khi popup đã được yêu cầu đóng để tránh cảm giác popup chỉnh sửa chuyển thành popup thêm mới.

## Update 2026-06-01 storefront specs alignment

- Mo rong `spec_fields` cho cac danh muc Dien thoai, May tinh bang, Laptop, Phu kien, Dong ho, Camera va May anh de bao phu cac key thong so chi tiet dang co trong san pham.
- Cac field moi dung label tieng Viet tren storefront, vi du: Loai man hinh, Tinh nang camera sau, Wi-Fi, Bluetooth, Chong on, Codec am thanh, Ngam ong kinh.
- Bo sung du lieu thong so mau cho cac san pham truoc do dang rong nhu AirPods Pro 2 USB-C, Anker GaN 100W, Apple Watch Ultra 2, Garmin Fenix 7 Pro, DJI Pocket 3, Ezviz C6N, Sony Alpha A7 IV va OPPO Find N3.
- Chuan hoa key cu `screenSize` sang `screen_size` de khop voi danh muc.

## Update 2026-06-02 storefront category brand menu

- Thanh danh mục storefront chỉ hiển thị thương hiệu theo sản phẩm thực tế thuộc danh mục cha/con hoặc thương hiệu được gắn rõ với danh mục đó.
- Không còn đưa các thương hiệu chưa gắn danh mục vào mọi danh mục, tránh trường hợp Điện thoại hiển thị lẫn Acer, Dell, Canon, DJI.
- `frontend/src/hooks/useCatalog.ts` đã tính cả `subcategoryId`/`subcategorySlug` khi gom sản phẩm cho danh mục cha, nên hãng của danh mục con vẫn xuất hiện đúng trong menu danh mục cha.

## Update 2026-06-02 storefront category ranking suggestions

- `frontend/src/hooks/useCatalog.ts` nay lấy danh sách "Sản phẩm nổi bật" trong mega menu từ `GET /catalog/rankings` theo từng danh mục.
- Nguồn xếp hạng dùng `criteria=trending`, `period=7d`, `limit=10` để ưu tiên sản phẩm đang có hạng trong danh mục đó.
- Nếu ranking trống hoặc API lỗi, menu fallback về danh sách sản phẩm active đã khớp với danh mục để khu đề xuất không bị rỗng.

## Update 2026-06-02 storefront category mega menu layout

- `frontend/src/components/layout/CategoryMegaMenu.tsx` đổi panel danh mục sang layout nhiều cột dạng danh sách gọn hơn, tham khảo CellphoneS.
- Panel và thanh danh mục có `max-height` theo viewport và cuộn riêng bên trong, tránh che mất nội dung phía dưới khi có nhiều hãng, phân khúc hoặc sản phẩm đề xuất.
- Nhóm "Danh mục con" trong mega menu được đổi cách hiển thị thành "Theo nhu cầu" khi render storefront.
- Bổ sung các nhóm phân khúc phù hợp theo danh mục: giá, nhu cầu sử dụng, dòng máy/chip, kích thước màn hình, tính năng nổi bật.

## Update 2026-06-02 storefront category price filter links

- Các mục "Phân khúc giá" trong mega menu nay trỏ về trang sản phẩm của danh mục với query `min_price`/`max_price`, thay vì tìm kiếm theo chữ.
- `frontend/src/pages/ProductListPage.tsx` hỗ trợ đọc `min_price`/`max_price` trực tiếp từ URL và truyền vào API lọc sản phẩm.
- Khi vào từ mega menu bằng khoảng giá tùy chỉnh, bộ lọc giá hiển thị nhãn khoảng giá đang áp dụng.

## Update 2026-06-04 Khắc phục lỗi backend khi thêm/sửa danh mục

- Khắc phục lỗi `NameError` do thiếu import các helper: `ensure_not_data_url` từ `admin_utils.py`, `enqueue_category_cache_refresh` và `process_category_migration_job` từ `admin_customers.py` vào `admin_categories.py`.
- Sửa lỗi `AmbiguousParameterError` (PostgreSQL/asyncpg) khi kiểm tra trùng slug/mã bằng cách cast explicit kiểu dữ liệu của tham số loại trừ ID trong SQL: `CAST(:exclude_id AS UUID)` và `CAST(:category_id AS UUID)`. Việc này giúp PostgreSQL nhận dạng đúng kiểu dữ liệu kể cả khi tham số truyền vào là `None` (NULL).
- Khắc phục lỗi `AttributeError: 'coroutine' object has no attribute 'scalar'` bằng cách tách các lệnh gộp `(await session.execute(...)).scalar()` thành 2 bước (gán kết quả thực thi rồi mới gọi `.scalar()`), tránh việc Python gọi `.scalar()` trực tiếp trên đối tượng coroutine trước khi await do độ ưu tiên toán tử.
- Khắc phục lỗi `AmbiguousParameterError` khi thêm/sửa danh mục có `parent_id` trong biểu thức dựng `path` bằng cách ép kiểu `CAST(:parent_id AS uuid)` ở cả câu SQL `INSERT` và `UPDATE`.
- CORS không phải nguyên nhân gốc của lỗi lưu danh mục: khi backend phát sinh exception trước đó, trình duyệt hiển thị thành lỗi CORS. Sau khi xử lý exception và sửa SQL, request `PATCH /api/v1/admin/categories/{id}` từ `http://localhost:3000` trả `200 OK` kèm `Access-Control-Allow-Origin`.
- Khắc phục lỗi frontend khi xóa danh mục `Cannot read properties of undefined (reading 'adminDeleteCategory')` bằng cách truyền `apiDb` vào `sharedProps` của `AdminDashboard`; các tab admin đang gọi API qua props nay nhận đúng service.
- Bắt đầu tách frontend API theo miền: thêm `frontend/src/services/categoryApi.ts` cho các endpoint danh mục và chuyển hook/tab danh mục sang dùng service này trực tiếp, giảm phụ thuộc vào object `apiDb` tổng.
- Tách tiếp frontend API: thêm `frontend/src/services/apiClient.ts` chứa `request`/`requestBlob`, thêm `frontend/src/services/brandApi.ts` cho endpoint thương hiệu, và chuyển hook/tab brand cùng phần load brand/category trong `useAdminLogic` sang service theo miền.
- Dọn khối SEO Metadata khỏi quản lý danh mục: frontend không hiển thị/không gửi `seoTitle`, `seoDescription`, `seoKeywords`; backend category payload và SQL không đọc/ghi các cột này; migration `052_remove_category_seo_metadata.sql` drop các cột SEO khỏi bảng `categories`.
- Dọn SEO khỏi quản lý thương hiệu: frontend chỉ giữ `landingTitle`, backend brand payload/API không đọc/ghi `seoTitle` và `seoDescription`; migration `053_remove_brand_seo_metadata.sql` drop các cột SEO khỏi bảng `brands`.
