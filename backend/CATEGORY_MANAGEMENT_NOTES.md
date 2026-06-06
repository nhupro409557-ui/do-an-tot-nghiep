# Category Management Notes

This file records the non-obvious decisions added while hardening category management.

## Update 2026-06-06 inherited product visibility

- Khi admin áº©n danh má»¥c qua cáº­p nháº­t tráº¡ng thÃ¡i `INACTIVE`, sáº£n pháº©m Ä‘ang bÃ¡n trong nhÃ¡nh danh má»¥c Ä‘Æ°á»£c chuyá»ƒn sang `INACTIVE` kÃ¨m `hidden_by_category = TRUE`.
- Khi danh má»¥c báº­t láº¡i hoáº·c Ä‘Æ°á»£c khÃ´i phá»¥c, backend chá»‰ báº­t láº¡i sáº£n pháº©m tá»«ng bá»‹ áº©n bá»Ÿi danh má»¥c vÃ  khÃ´ng bá»‹ thÆ°Æ¡ng hiá»‡u/danh má»¥c khÃ¡c cháº·n; sáº£n pháº©m Ä‘Ã£ bá»‹ admin táº¯t trÆ°á»›c Ä‘Ã³ váº«n giá»¯ `INACTIVE`.
- Luá»“ng cáº­p nháº­t hÃ ng loáº¡t danh má»¥c dÃ¹ng cÃ¹ng quy táº¯c nÃ y Ä‘á»ƒ trÃ¡nh máº¥t tráº¡ng thÃ¡i gá»‘c cá»§a sáº£n pháº©m.

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
- File: `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

8. Frontend concurrency message

- Frontend now translates version mismatch / `409 Conflict` style responses into a clearer admin message.
- File: `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

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
- File: `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

11. Migration job auto-polling while editing category

- When the selected category has `PENDING/RUNNING/IN_PROGRESS` migration jobs, the category workspace now auto-refreshes on an interval.
- Purpose:
  - helps admins observe long-running parent-change migrations without manually reloading the whole dashboard
- File: `frontend/src/features/admin-shell/pages/AdminDashboard.tsx`

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

## Update 2026-06-06 admin category status filter

- MÃ n quáº£n lÃ½ danh má»¥c cá»§a admin cÃ³ thÃªm bá»™ lá»c tráº¡ng thÃ¡i á»Ÿ thanh lá»c phÃ­a trÃªn.
- Bá»™ lá»c há»— trá»£: táº¥t cáº£, Ä‘ang hiá»ƒn thá»‹ vÃ  Ä‘Ã£ áº©n.
- Frontend lá»c theo `isActive` trÃªn dá»¯ liá»‡u danh má»¥c Ä‘Ã£ táº£i sáºµn, nÃªn khÃ´ng thay Ä‘á»•i API/backend.

## Update 2026-06-05 backend admin category refactor

- Báº¯t Ä‘áº§u tÃ¡ch `backend/app/api/v1/routers/admin_categories.py` theo mÃ´ hÃ¬nh Controller - Service - Repository.
- Router `admin_categories.py` hiá»‡n chá»‰ giá»¯ route decorator, dependency FastAPI vÃ  chuyá»ƒn tiáº¿p request sang service.
- Logic quáº£n lÃ½ danh má»¥c, cache, audit log, sitemap refresh, migration guard vÃ  cÃ¡c use case create/update/delete/restore/reorder/bulk Ä‘Ã£ Ä‘Æ°á»£c chuyá»ƒn sang `backend/app/application/services/category_service.py`.
- Táº¡o `backend/app/infrastructure/database/repositories/category_repo.py` lÃ m Ä‘iá»ƒm Ä‘áº·t táº§ng repository cho truy váº¥n category; cÃ¡c truy váº¥n má»›i nÃªn Ä‘Æ°á»£c thÃªm vÃ o Ä‘Ã¢y trÆ°á»›c, sau Ä‘Ã³ tiáº¿p tá»¥c chuyá»ƒn dáº§n SQL cÅ© tá»« service sang repository theo tá»«ng nhÃ³m nhá» Ä‘á»ƒ trÃ¡nh Ä‘á»•i hÃ nh vi.
- Láº§n tÃ¡ch nÃ y giá»¯ nguyÃªn hÃ nh vi API, status code vÃ  transaction boundary hiá»‡n cÃ³: service váº«n lÃ  nÆ¡i commit transaction vÃ  Ä‘iá»u phá»‘i cache/background task sau khi ghi dá»¯ liá»‡u.

## Business assumptions introduced in this pass

1. During category migration, branch writes are blocked instead of allowed with eventual reconciliation.
2. Soft deleting a category branch unlists products instead of moving them to an "uncategorized" bucket.
3. Restoring a category does not auto-reactivate products that were inactivated by the delete flow.
4. Stale migration jobs older than 30 minutes are treated as failed and their category workflow lock is released automatically.
5. Category operators benefit from seeing operational telemetry in the same screen as category edits, not only through backend logs.

## Update 2026-06-04 admin category slug validation

- Slug danh má»¥c Ä‘Æ°á»£c chuáº©n hÃ³a tiáº¿ng Viá»‡t Ä‘Ãºng dáº¥u khi tá»± sinh tá»« tÃªn, bao gá»“m trÆ°á»ng há»£p cÃ³ chá»¯ `Ä‘`/`Ä`.
- Khi thÃªm danh má»¥c mÃ  Ä‘á»ƒ trá»‘ng slug, backend tá»± sinh slug dáº¡ng `ten-danh-muc-xxxxx` Ä‘á»ƒ háº¡n cháº¿ trÃ¹ng.
- Khi sá»­a danh má»¥c, kiá»ƒm tra trÃ¹ng slug/mÃ£ váº«n loáº¡i trá»« chÃ­nh danh má»¥c Ä‘ang sá»­a; lá»—i tráº£ vá» Ä‘Æ°á»£c tÃ¡ch rÃµ giá»¯a `Slug danh má»¥c Ä‘Ã£ tá»“n táº¡i.` vÃ  `MÃ£ danh má»¥c Ä‘Ã£ tá»“n táº¡i.`.
- Frontend hiá»ƒn thá»‹ trá»±c tiáº¿p thÃ´ng bÃ¡o lá»—i backend khi lÆ°u danh má»¥c tháº¥t báº¡i Ä‘á»ƒ admin biáº¿t Ä‘ang trÃ¹ng slug hay trÃ¹ng mÃ£.
- Sá»­a lá»—i lÆ°u danh má»¥c bá»‹ backend tráº£ 500/CORS giáº£ do cÃ¡c helper async gá»i `.scalar()` trÃªn coroutine `session.execute`; nay káº¿t quáº£ execute Ä‘Æ°á»£c await trÆ°á»›c khi Ä‘á»c scalar.
- ÄÃ£ khá»Ÿi Ä‘á»™ng láº¡i backend local trÃªn port 8000 Ä‘á»ƒ process Ä‘ang cháº¡y dÃ¹ng code má»›i.
- CORS middleware Ä‘Æ°á»£c Ä‘áº·t bá»c ngoÃ i audit middleware Ä‘á»ƒ khi backend cÃ³ lá»—i tháº­t, trÃ¬nh duyá»‡t váº«n nháº­n `Access-Control-Allow-Origin` vÃ  frontend tháº¥y lá»—i API thay vÃ¬ thÃ´ng bÃ¡o CORS gÃ¢y nhiá»…u.

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

- Sau khi thÃªm hoáº·c chá»‰nh sá»­a danh má»¥c thÃ nh cÃ´ng, popup danh má»¥c tá»± Ä‘Ã³ng báº±ng `closeSignal`.
- Admin nháº­n thÃ´ng bÃ¡o thÃ nh cÃ´ng rÃµ rÃ ng sau khi thÃªm hoáº·c lÆ°u thay Ä‘á»•i danh má»¥c.
- Viá»‡c reset form váº«n Ä‘Æ°á»£c giá»¯ nguyÃªn, nhÆ°ng chá»‰ diá»…n ra sau khi popup Ä‘Ã£ Ä‘Æ°á»£c yÃªu cáº§u Ä‘Ã³ng Ä‘á»ƒ trÃ¡nh cáº£m giÃ¡c popup chá»‰nh sá»­a chuyá»ƒn thÃ nh popup thÃªm má»›i.

## Update 2026-06-01 storefront specs alignment

- Mo rong `spec_fields` cho cac danh muc Dien thoai, May tinh bang, Laptop, Phu kien, Dong ho, Camera va May anh de bao phu cac key thong so chi tiet dang co trong san pham.
- Cac field moi dung label tieng Viet tren storefront, vi du: Loai man hinh, Tinh nang camera sau, Wi-Fi, Bluetooth, Chong on, Codec am thanh, Ngam ong kinh.
- Bo sung du lieu thong so mau cho cac san pham truoc do dang rong nhu AirPods Pro 2 USB-C, Anker GaN 100W, Apple Watch Ultra 2, Garmin Fenix 7 Pro, DJI Pocket 3, Ezviz C6N, Sony Alpha A7 IV va OPPO Find N3.
- Chuan hoa key cu `screenSize` sang `screen_size` de khop voi danh muc.

## Update 2026-06-02 storefront category brand menu

- Thanh danh má»¥c storefront chá»‰ hiá»ƒn thá»‹ thÆ°Æ¡ng hiá»‡u theo sáº£n pháº©m thá»±c táº¿ thuá»™c danh má»¥c cha/con hoáº·c thÆ°Æ¡ng hiá»‡u Ä‘Æ°á»£c gáº¯n rÃµ vá»›i danh má»¥c Ä‘Ã³.
- KhÃ´ng cÃ²n Ä‘Æ°a cÃ¡c thÆ°Æ¡ng hiá»‡u chÆ°a gáº¯n danh má»¥c vÃ o má»i danh má»¥c, trÃ¡nh trÆ°á»ng há»£p Äiá»‡n thoáº¡i hiá»ƒn thá»‹ láº«n Acer, Dell, Canon, DJI.
- `frontend/src/hooks/useCatalog.ts` Ä‘Ã£ tÃ­nh cáº£ `subcategoryId`/`subcategorySlug` khi gom sáº£n pháº©m cho danh má»¥c cha, nÃªn hÃ£ng cá»§a danh má»¥c con váº«n xuáº¥t hiá»‡n Ä‘Ãºng trong menu danh má»¥c cha.

## Update 2026-06-02 storefront category ranking suggestions

- `frontend/src/hooks/useCatalog.ts` nay láº¥y danh sÃ¡ch "Sáº£n pháº©m ná»•i báº­t" trong mega menu tá»« `GET /catalog/rankings` theo tá»«ng danh má»¥c.
- Nguá»“n xáº¿p háº¡ng dÃ¹ng `criteria=trending`, `period=7d`, `limit=10` Ä‘á»ƒ Æ°u tiÃªn sáº£n pháº©m Ä‘ang cÃ³ háº¡ng trong danh má»¥c Ä‘Ã³.
- Náº¿u ranking trá»‘ng hoáº·c API lá»—i, menu fallback vá» danh sÃ¡ch sáº£n pháº©m active Ä‘Ã£ khá»›p vá»›i danh má»¥c Ä‘á»ƒ khu Ä‘á» xuáº¥t khÃ´ng bá»‹ rá»—ng.

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

## Update 2026-06-05 admin category duplicate guard

- Kiá»ƒm tra trÃ¹ng slug/mÃ£ danh má»¥c khÃ´ng cÃ²n bá» qua báº£n ghi Ä‘Ã£ xÃ³a má»m, vÃ¬ database váº«n giá»¯ unique constraint trÃªn `categories.slug` vÃ  `categories.code`.
- Khi admin táº¡o hoáº·c sá»­a danh má»¥c dÃ¹ng láº¡i mÃ£/slug Ä‘Ã£ tá»“n táº¡i trong database, service tráº£ lá»—i nghiá»‡p vá»¥ `409` thay vÃ¬ Ä‘á»ƒ insert/update rÆ¡i xuá»‘ng lá»—i database `500`.

## Update 2026-06-05 hard delete empty categories

- Khi admin xÃ³a danh má»¥c khÃ´ng cÃ³ danh má»¥c con, sáº£n pháº©m, thÆ°Æ¡ng hiá»‡u, ná»™i dung, migration job hoáº·c redirect SEO liÃªn quan, backend xÃ³a cá»©ng báº£n ghi khá»i `categories`.
- Náº¿u danh má»¥c cÃ²n rÃ ng buá»™c nghiá»‡p vá»¥, backend giá»¯ luá»“ng xÃ³a má»m hiá»‡n cÃ³ Ä‘á»ƒ trÃ¡nh lÃ m Ä‘á»©t dá»¯ liá»‡u sáº£n pháº©m vÃ  quan há»‡ danh má»¥c.
- Audit log cá»§a riÃªng danh má»¥c trá»‘ng Ä‘Æ°á»£c dá»n trÆ°á»›c khi xÃ³a cá»©ng vÃ¬ Ä‘Ã¢y lÃ  dá»¯ liá»‡u ká»¹ thuáº­t phá»¥ vÃ  cÃ³ khÃ³a ngoáº¡i vá» `categories`.

## Update 2026-05-30 frontend refactor

- Da tach phan logic va state quan ly danh muc ra khoi `useAdminLogic.ts` sang hook rieng biet `useAdminCategoriesLogic.ts` de lam sach va modul hoa frontend code.


## Update 2026-06-01 admin form completion feedback

- Sau khi thÃªm hoáº·c chá»‰nh sá»­a danh má»¥c thÃ nh cÃ´ng, popup danh má»¥c tá»± Ä‘Ã³ng báº±ng `closeSignal`.
- Admin nháº­n thÃ´ng bÃ¡o thÃ nh cÃ´ng rÃµ rÃ ng sau khi thÃªm hoáº·c lÆ°u thay Ä‘á»•i danh má»¥c.
- Viá»‡c reset form váº«n Ä‘Æ°á»£c giá»¯ nguyÃªn, nhÆ°ng chá»‰ diá»…n ra sau khi popup Ä‘Ã£ Ä‘Æ°á»£c yÃªu cáº§u Ä‘Ã³ng Ä‘á»ƒ trÃ¡nh cáº£m giÃ¡c popup chá»‰nh sá»­a chuyá»ƒn thÃ nh popup thÃªm má»›i.

## Update 2026-06-01 storefront specs alignment

- Mo rong `spec_fields` cho cac danh muc Dien thoai, May tinh bang, Laptop, Phu kien, Dong ho, Camera va May anh de bao phu cac key thong so chi tiet dang co trong san pham.
- Cac field moi dung label tieng Viet tren storefront, vi du: Loai man hinh, Tinh nang camera sau, Wi-Fi, Bluetooth, Chong on, Codec am thanh, Ngam ong kinh.
- Bo sung du lieu thong so mau cho cac san pham truoc do dang rong nhu AirPods Pro 2 USB-C, Anker GaN 100W, Apple Watch Ultra 2, Garmin Fenix 7 Pro, DJI Pocket 3, Ezviz C6N, Sony Alpha A7 IV va OPPO Find N3.
- Chuan hoa key cu `screenSize` sang `screen_size` de khop voi danh muc.

## Update 2026-06-02 storefront category brand menu

- Thanh danh má»¥c storefront chá»‰ hiá»ƒn thá»‹ thÆ°Æ¡ng hiá»‡u theo sáº£n pháº©m thá»±c táº¿ thuá»™c danh má»¥c cha/con hoáº·c thÆ°Æ¡ng hiá»‡u Ä‘Æ°á»£c gáº¯n rÃµ vá»›i danh má»¥c Ä‘Ã³.
- KhÃ´ng cÃ²n Ä‘Æ°a cÃ¡c thÆ°Æ¡ng hiá»‡u chÆ°a gáº¯n danh má»¥c vÃ o má»i danh má»¥c, trÃ¡nh trÆ°á»ng há»£p Äiá»‡n thoáº¡i hiá»ƒn thá»‹ láº«n Acer, Dell, Canon, DJI.
- `frontend/src/hooks/useCatalog.ts` Ä‘Ã£ tÃ­nh cáº£ `subcategoryId`/`subcategorySlug` khi gom sáº£n pháº©m cho danh má»¥c cha, nÃªn hÃ£ng cá»§a danh má»¥c con váº«n xuáº¥t hiá»‡n Ä‘Ãºng trong menu danh má»¥c cha.

## Update 2026-06-02 storefront category ranking suggestions

- `frontend/src/hooks/useCatalog.ts` nay láº¥y danh sÃ¡ch "Sáº£n pháº©m ná»•i báº­t" trong mega menu tá»« `GET /catalog/rankings` theo tá»«ng danh má»¥c.
- Nguá»“n xáº¿p háº¡ng dÃ¹ng `criteria=trending`, `period=7d`, `limit=10` Ä‘á»ƒ Æ°u tiÃªn sáº£n pháº©m Ä‘ang cÃ³ háº¡ng trong danh má»¥c Ä‘Ã³.
- Náº¿u ranking trá»‘ng hoáº·c API lá»—i, menu fallback vá» danh sÃ¡ch sáº£n pháº©m active Ä‘Ã£ khá»›p vá»›i danh má»¥c Ä‘á»ƒ khu Ä‘á» xuáº¥t khÃ´ng bá»‹ rá»—ng.

## Update 2026-06-02 storefront category mega menu layout

- `frontend/src/components/layout/CategoryMegaMenu.tsx` Ä‘á»•i panel danh má»¥c sang layout nhiá»u cá»™t dáº¡ng danh sÃ¡ch gá»n hÆ¡n, tham kháº£o CellphoneS.
- Panel vÃ  thanh danh má»¥c cÃ³ `max-height` theo viewport vÃ  cuá»™n riÃªng bÃªn trong, trÃ¡nh che máº¥t ná»™i dung phÃ­a dÆ°á»›i khi cÃ³ nhiá»u hÃ£ng, phÃ¢n khÃºc hoáº·c sáº£n pháº©m Ä‘á» xuáº¥t.
- NhÃ³m "Danh má»¥c con" trong mega menu Ä‘Æ°á»£c Ä‘á»•i cÃ¡ch hiá»ƒn thá»‹ thÃ nh "Theo nhu cáº§u" khi render storefront.
- Bá»• sung cÃ¡c nhÃ³m phÃ¢n khÃºc phÃ¹ há»£p theo danh má»¥c: giÃ¡, nhu cáº§u sá»­ dá»¥ng, dÃ²ng mÃ¡y/chip, kÃ­ch thÆ°á»›c mÃ n hÃ¬nh, tÃ­nh nÄƒng ná»•i báº­t.

## Update 2026-06-02 storefront category price filter links

- CÃ¡c má»¥c "PhÃ¢n khÃºc giÃ¡" trong mega menu nay trá» vá» trang sáº£n pháº©m cá»§a danh má»¥c vá»›i query `min_price`/`max_price`, thay vÃ¬ tÃ¬m kiáº¿m theo chá»¯.
- `frontend/src/features/products/pages/ProductListPage.tsx` há»— trá»£ Ä‘á»c `min_price`/`max_price` trá»±c tiáº¿p tá»« URL vÃ  truyá»n vÃ o API lá»c sáº£n pháº©m.
- Khi vÃ o tá»« mega menu báº±ng khoáº£ng giÃ¡ tÃ¹y chá»‰nh, bá»™ lá»c giÃ¡ hiá»ƒn thá»‹ nhÃ£n khoáº£ng giÃ¡ Ä‘ang Ã¡p dá»¥ng.

## Update 2026-06-04 Kháº¯c phá»¥c lá»—i backend khi thÃªm/sá»­a danh má»¥c

- Kháº¯c phá»¥c lá»—i `NameError` do thiáº¿u import cÃ¡c helper: `ensure_not_data_url` tá»« `admin_utils.py`, `enqueue_category_cache_refresh` vÃ  `process_category_migration_job` tá»« `admin_customers.py` vÃ o `admin_categories.py`.
- Sá»­a lá»—i `AmbiguousParameterError` (PostgreSQL/asyncpg) khi kiá»ƒm tra trÃ¹ng slug/mÃ£ báº±ng cÃ¡ch cast explicit kiá»ƒu dá»¯ liá»‡u cá»§a tham sá»‘ loáº¡i trá»« ID trong SQL: `CAST(:exclude_id AS UUID)` vÃ  `CAST(:category_id AS UUID)`. Viá»‡c nÃ y giÃºp PostgreSQL nháº­n dáº¡ng Ä‘Ãºng kiá»ƒu dá»¯ liá»‡u ká»ƒ cáº£ khi tham sá»‘ truyá»n vÃ o lÃ  `None` (NULL).
- Kháº¯c phá»¥c lá»—i `AttributeError: 'coroutine' object has no attribute 'scalar'` báº±ng cÃ¡ch tÃ¡ch cÃ¡c lá»‡nh gá»™p `(await session.execute(...)).scalar()` thÃ nh 2 bÆ°á»›c (gÃ¡n káº¿t quáº£ thá»±c thi rá»“i má»›i gá»i `.scalar()`), trÃ¡nh viá»‡c Python gá»i `.scalar()` trá»±c tiáº¿p trÃªn Ä‘á»‘i tÆ°á»£ng coroutine trÆ°á»›c khi await do Ä‘á»™ Æ°u tiÃªn toÃ¡n tá»­.
- Kháº¯c phá»¥c lá»—i `AmbiguousParameterError` khi thÃªm/sá»­a danh má»¥c cÃ³ `parent_id` trong biá»ƒu thá»©c dá»±ng `path` báº±ng cÃ¡ch Ã©p kiá»ƒu `CAST(:parent_id AS uuid)` á»Ÿ cáº£ cÃ¢u SQL `INSERT` vÃ  `UPDATE`.
- CORS khÃ´ng pháº£i nguyÃªn nhÃ¢n gá»‘c cá»§a lá»—i lÆ°u danh má»¥c: khi backend phÃ¡t sinh exception trÆ°á»›c Ä‘Ã³, trÃ¬nh duyá»‡t hiá»ƒn thá»‹ thÃ nh lá»—i CORS. Sau khi xá»­ lÃ½ exception vÃ  sá»­a SQL, request `PATCH /api/v1/admin/categories/{id}` tá»« `http://localhost:3000` tráº£ `200 OK` kÃ¨m `Access-Control-Allow-Origin`.
- Kháº¯c phá»¥c lá»—i frontend khi xÃ³a danh má»¥c `Cannot read properties of undefined (reading 'adminDeleteCategory')` báº±ng cÃ¡ch truyá»n `apiDb` vÃ o `sharedProps` cá»§a `AdminDashboard`; cÃ¡c tab admin Ä‘ang gá»i API qua props nay nháº­n Ä‘Ãºng service.
- Báº¯t Ä‘áº§u tÃ¡ch frontend API theo miá»n: thÃªm `frontend/src/services/categoryApi.ts` cho cÃ¡c endpoint danh má»¥c vÃ  chuyá»ƒn hook/tab danh má»¥c sang dÃ¹ng service nÃ y trá»±c tiáº¿p, giáº£m phá»¥ thuá»™c vÃ o object `apiDb` tá»•ng.
- TÃ¡ch tiáº¿p frontend API: thÃªm `frontend/src/services/apiClient.ts` chá»©a `request`/`requestBlob`, thÃªm `frontend/src/services/brandApi.ts` cho endpoint thÆ°Æ¡ng hiá»‡u, vÃ  chuyá»ƒn hook/tab brand cÃ¹ng pháº§n load brand/category trong `useAdminLogic` sang service theo miá»n.
- Dá»n khá»‘i SEO Metadata khá»i quáº£n lÃ½ danh má»¥c: frontend khÃ´ng hiá»ƒn thá»‹/khÃ´ng gá»­i `seoTitle`, `seoDescription`, `seoKeywords`; backend category payload vÃ  SQL khÃ´ng Ä‘á»c/ghi cÃ¡c cá»™t nÃ y; migration `052_remove_category_seo_metadata.sql` drop cÃ¡c cá»™t SEO khá»i báº£ng `categories`.
- Dá»n SEO khá»i quáº£n lÃ½ thÆ°Æ¡ng hiá»‡u: frontend chá»‰ giá»¯ `landingTitle`, backend brand payload/API khÃ´ng Ä‘á»c/ghi `seoTitle` vÃ  `seoDescription`; migration `053_remove_brand_seo_metadata.sql` drop cÃ¡c cá»™t SEO khá»i báº£ng `brands`.

## Update 2026-06-05 Tá»‘i Æ°u hÃ³a Ä‘Ã³ng form danh má»¥c vÃ  reset tráº¡ng thÃ¡i

- HÃ m `resetCategoryForm` tá»± Ä‘á»™ng tÄƒng `categoryCloseSignal` giÃºp táº¯t popup ngay láº­p tá»©c khi nháº¥n nÃºt Há»§y.
- HÃ m `handleCategorySubmit` khi thÃ nh cÃ´ng sáº½ tÄƒng `categoryCloseSignal` trÆ°á»›c, trÃ¬ hoÃ£n gá»i `resetCategoryForm` (250ms) vÃ  trÃ¬ hoÃ£n alert thÃ nh cÃ´ng (100ms) Ä‘á»ƒ Ä‘Ã³ng modal mÆ°á»£t mÃ , khÃ´ng block hoáº¡t cáº£nh vÃ  khÃ´ng bá»‹ reset form trÆ°á»›c khi táº¯t.
- Giáº£i quyáº¿t triá»‡t Ä‘á»ƒ lá»—i form chuyá»ƒn vá» tráº¡ng thÃ¡i ThÃªm má»›i trÆ°á»›c khi biáº¿n máº¥t.

## Update 2026-06-05 Category Service Repository Split


- TÃ¡ch thÃªm SQL tá»« `app/application/services/category_service.py` xuá»‘ng `app/infrastructure/database/repositories/category_repo.py`.
- NhÃ³m Ä‘Ã£ chuyá»ƒn gá»“m: danh sÃ¡ch admin categories, kiá»ƒm tra slug, audit logs, migration jobs, operational metrics, kiá»ƒm tra vÃ²ng láº·p danh má»¥c, kiá»ƒm tra Ä‘á»™ sÃ¢u cÃ¢y, kiá»ƒm tra trÃ¹ng spec inherited, Ä‘áº¿m sáº£n pháº©m dÃ¹ng spec keys, watchdog migration stale, tÃ¬m root category vÃ  danh sÃ¡ch root category hiá»ƒn thá»‹.
- `category_service.py` tiáº¿p tá»¥c giá»¯ logic nghiá»‡p vá»¥, raise lá»—i HTTP, cache refresh, audit orchestration vÃ  background job.
- Káº¿t quáº£ kiá»ƒm tra: compile backend báº±ng `.venv` thÃ nh cÃ´ng; import `app.main`, `category_service` vÃ  `category_repo` Ä‘á»u hoáº¡t Ä‘á»™ng.

## Update 2026-06-05 Category Service Full SQL Cleanup

- Má»Ÿ rá»™ng `app/infrastructure/database/repositories/category_repo.py` Ä‘á»ƒ chá»©a cÃ¡c truy váº¥n DB cÃ²n láº¡i cá»§a `category_service.py`: cache branch, deactivate product theo nhÃ¡nh, sitemap refresh, audit product/category, redirect slug, create/update category, reorder, bulk update, restore vÃ  soft delete.
- LÃ m sáº¡ch `app/application/services/category_service.py`: bá» toÃ n bá»™ `session.execute`, `session.scalar`, `text`, `bindparam`; service chá»‰ giá»¯ chuáº©n hÃ³a payload, kiá»ƒm tra nghiá»‡p vá»¥, gá»i repository, audit orchestration, cache refresh vÃ  background job.
- Giá»¯ nguyÃªn chá»¯ kÃ½ cÃ¡c helper Ä‘ang Ä‘Æ°á»£c module khÃ¡c import nhÆ° `audit_product_event`, `ensure_categories_not_migrating`, `rebuild_category_branch_cache` Ä‘á»ƒ khÃ´ng lÃ m gÃ£y product/category flow.
- Káº¿t quáº£ kiá»ƒm tra: compile toÃ n bá»™ backend báº±ng `.venv` thÃ nh cÃ´ng; import `app.main`, admin categories router, category service vÃ  category repository thÃ nh cÃ´ng.
## Update 2026-06-06 tÃ¡ch thao tÃ¡c áº©n vÃ  xÃ³a danh má»¥c

- Frontend quáº£n lÃ½ danh má»¥c tÃ¡ch nÃºt thao tÃ¡c thÃ nh `áº¨n`, `KhÃ´i phá»¥c` vÃ  `XÃ³a`, thá»‘ng nháº¥t vá»›i mÃ n quáº£n lÃ½ thÆ°Æ¡ng hiá»‡u.
- NÃºt `áº¨n` gá»i API cáº­p nháº­t danh má»¥c vá»›i `status = 'INACTIVE'` vÃ  `isActive = false`, khÃ´ng Ä‘áº·t `is_deleted` vÃ  khÃ´ng dÃ¹ng luá»“ng xÃ³a má»m.
- API `DELETE /admin/categories/{id}` chá»‰ xÃ³a cá»©ng khi danh má»¥c khÃ´ng cÃ³ rÃ ng buá»™c. Náº¿u cÃ²n danh má»¥c con, sáº£n pháº©m, thÆ°Æ¡ng hiá»‡u, ná»™i dung, migration job hoáº·c redirect liÃªn quan, backend tráº£ `409` vÃ  yÃªu cáº§u dÃ¹ng thao tÃ¡c áº©n thay vÃ¬ tá»± chuyá»ƒn sang xÃ³a má»m.

## Update 2026-06-06 admin category popup close timing

- Sau khi thÃªm hoáº·c chá»‰nh sá»­a danh má»¥c thÃ nh cÃ´ng, frontend dÃ¹ng `flushSync` Ä‘á»ƒ Ã¡p dá»¥ng tÃ­n hiá»‡u Ä‘Ã³ng popup trÆ°á»›c khi refresh dá»¯ liá»‡u, reset form vÃ  hiá»‡n thÃ´ng bÃ¡o thÃ nh cÃ´ng.
- Má»¥c tiÃªu lÃ  trÃ¡nh trÆ°á»ng há»£p `window.alert` cháº·n trÃ¬nh duyá»‡t khiáº¿n popup chÆ°a ká»‹p Ä‘Ã³ng nhÆ°ng form Ä‘Ã£ reset thÃ nh form thÃªm má»›i trá»‘ng.
- ThÃ´ng bÃ¡o thÃ nh cÃ´ng cá»§a luá»“ng thÃªm/sá»­a danh má»¥c Ä‘Æ°á»£c chuyá»ƒn sang toast ná»•i trong tab danh má»¥c, khÃ´ng dÃ¹ng `window.alert` Ä‘á»ƒ trÃ¡nh cháº·n UI.
- Káº¿t quáº£ kiá»ƒm tra: `npm run lint` trong `frontend` thÃ nh cÃ´ng.
