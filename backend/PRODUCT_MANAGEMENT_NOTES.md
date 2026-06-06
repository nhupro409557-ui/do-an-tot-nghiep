# Product Management Notes

## Update 2026-06-06 inherited category/brand visibility

- ThÃªm hai cá»™t `products.hidden_by_category` vÃ  `products.hidden_by_brand` Ä‘á»ƒ phÃ¢n biá»‡t sáº£n pháº©m bá»‹ áº©n do danh má»¥c/thÆ°Æ¡ng hiá»‡u vá»›i sáº£n pháº©m do admin chá»§ Ä‘á»™ng táº¯t.
- Khi danh má»¥c hoáº·c thÆ°Æ¡ng hiá»‡u bá»‹ áº©n, backend chá»‰ Ä‘Ã¡nh dáº¥u cÃ¡c sáº£n pháº©m Ä‘ang `ACTIVE` táº¡i thá»i Ä‘iá»ƒm Ä‘Ã³, chuyá»ƒn chÃºng sang `INACTIVE` vÃ  táº¯t biáº¿n thá»ƒ Ä‘á»ƒ storefront khÃ´ng hiá»ƒn thá»‹.
- Khi danh má»¥c hoáº·c thÆ°Æ¡ng hiá»‡u báº­t láº¡i, backend chá»‰ khÃ´i phá»¥c cÃ¡c sáº£n pháº©m cÃ³ cá» áº©n káº¿ thá»«a tÆ°Æ¡ng á»©ng, khÃ´ng cÃ²n bá»‹ lÃ½ do áº©n khÃ¡c cháº·n, vÃ  váº«n thá»a Ä‘iá»u kiá»‡n danh má»¥c/thÆ°Æ¡ng hiá»‡u Ä‘ang báº­t. Sáº£n pháº©m vá»‘n Ä‘Ã£ `INACTIVE` trÆ°á»›c Ä‘Ã³ khÃ´ng bá»‹ báº­t láº¡i.
- Backend cháº·n má»i thao tÃ¡c báº­t sáº£n pháº©m sang `ACTIVE` náº¿u danh má»¥c, danh má»¥c con hoáº·c thÆ°Æ¡ng hiá»‡u hiá»‡n Ä‘ang áº©n. Admin pháº£i báº­t danh má»¥c/thÆ°Æ¡ng hiá»‡u trÆ°á»›c rá»“i má»›i báº­t sáº£n pháº©m.
- TÃ¡ch thao tÃ¡c sáº£n pháº©m thÃ nh `áº¨n` vÃ  `XÃ³a`: `POST /admin/products/{id}/hide` chá»‰ chuyá»ƒn sáº£n pháº©m sang `INACTIVE`, cÃ²n `DELETE /admin/products/{id}` giá»¯ rule xÃ³a/xá»­ lÃ½ rÃ ng buá»™c hiá»‡n cÃ³. Bulk action há»— trá»£ thÃªm `HIDE`, `RESTORE`, `DELETE`.
- Migration liÃªn quan: `backend/migrations/055_product_inherited_visibility.sql`.

## Update 2026-06-06 product reactivate flow

- ThÃªm endpoint `POST /admin/products/{id}/reactivate` Ä‘á»ƒ báº­t láº¡i sáº£n pháº©m tá»« `INACTIVE` hoáº·c `DISCONTINUED` vá» `ACTIVE`, thay vÃ¬ dÃ¹ng `PATCH /admin/products/{id}` vá»›i payload Ä‘áº§y Ä‘á»§.
- Khi báº­t láº¡i sáº£n pháº©m tá»«ng bá»‹ táº¡m áº©n, backend tá»± báº­t láº¡i cÃ¡c biáº¿n thá»ƒ chÆ°a bá»‹ xÃ³a/lÆ°u trá»¯ (`deleted_at IS NULL`, status khÃ´ng pháº£i `deleted`/`archived`), trÃ¡nh lá»—i sáº£n pháº©m báº­t láº¡i nhÆ°ng biáº¿n thá»ƒ váº«n bá»‹ táº¯t.
- Frontend nÃºt khÃ´i phá»¥c/báº­t láº¡i trong báº£ng sáº£n pháº©m nay hiá»ƒn thá»‹ cho cáº£ `INACTIVE` vÃ  `DISCONTINUED`, Ä‘á»“ng thá»i gá»i endpoint reactivate riÃªng.

## Update 2026-06-06 OPPO product image gallery

- ÄÃ£ copy áº£nh ngÆ°á»i dÃ¹ng cung cáº¥p cho cÃ¡c dÃ²ng OPPO vÃ o `frontend/public/images/products/` vá»›i tÃªn thÆ° má»¥c vÃ  tÃªn file khÃ´ng dáº¥u Ä‘á»ƒ URL á»•n Ä‘á»‹nh.
- áº¢nh Ä‘áº¡i diá»‡n Ä‘Æ°á»£c chá»n theo file cÃ³ tÃªn chá»©a `áº£nh Ä‘áº¡i diá»‡n` hoáº·c biáº¿n thá»ƒ gÃµ gáº§n giá»‘ng trong tá»«ng thÆ° má»¥c mÃ u.
- ThÃªm script `backend/scripts/update_oppo_product_images.py` Ä‘á»ƒ cáº­p nháº­t `products.image_url`, `products.images`, `product_variants.image_url` vÃ  `product_variants.images`.
- ÄÃ£ cháº¡y script trÃªn DB local cho cÃ¡c sáº£n pháº©m:
  - `OPPO Reno15 5G`: Tráº¯ng Cá»±c Quang, Xanh Cháº¡ng Váº¡ng.
  - `OPPO Reno15 F 5G`: Há»“ng Rá»±c Rá»¡, Xanh DÆ°Æ¡ng, Xanh Nháº¡t.
  - `OPPO Find N6`: Cam Ná»Ÿ Rá»™, Titan Ãnh Sao.
  - `OPPO Find X9 Ultra`: Cam Háº»m NÃºi, NÃ¢u LÃ£nh NguyÃªn.
  - `OPPO Find X9s`: Cam HoÃ ng HÃ´n, TÃ­m Lavender, XÃ¡m Báº§u Trá»i.
  - `OPPO Find X8`: Äen KhÃ´ng Gian, XÃ¡m Sao BÄƒng.
  - `OPPO Find N3`: gáº¯n áº£nh sáº£n pháº©m chung tá»« bá»™ áº£nh Ä‘en/vÃ ng vÃ¬ hiá»‡n khÃ´ng cÃ³ biáº¿n thá»ƒ active.
- Verification: `python -m py_compile backend/scripts/update_oppo_product_images.py` thÃ nh cÃ´ng; truy váº¥n DB xÃ¡c nháº­n 7 sáº£n pháº©m vÃ  cÃ¡c biáº¿n thá»ƒ active Ä‘Ã£ nháº­n URL áº£nh má»›i.



#
#

## Update 2026-06-05 product service repository split

- Báº¯t Ä‘áº§u tÃ¡ch SQL trong `backend/app/application/services/product_service.py` xuá»‘ng repository.
- Chuyá»ƒn cÃ¡c truy váº¥n Ã­t rá»§i ro sang `backend/app/infrastructure/database/repositories/product_repo.py`: gá»£i Ã½ sáº£n pháº©m, import/export jobs, danh sÃ¡ch export, KPI catalog vÃ  audit logs sáº£n pháº©m.
- Tiáº¿p tá»¥c chuyá»ƒn cÃ¡c logic liÃªn káº¿t quan há»‡ xuá»‘ng `product_repo.py`, bao gá»“m:
  - Thao tÃ¡c xÃ³a/chÃ¨n liÃªn káº¿t `product_accessories` vÃ  `product_attached_services`.
  - Láº¥y thÃ´ng tin nhÃ³m dá»‹ch vá»¥ Ä‘i kÃ¨m.
  - Láº¥y cÃ¡c báº£n ghi bundle, accessory, vÃ  attached service tÆ°Æ¡ng á»©ng tá»‘i Æ°u cho danh sÃ¡ch sáº£n pháº©m.
- Chuyá»ƒn Ä‘á»•i cÃ¢u truy váº¥n chÃ­nh danh sÃ¡ch sáº£n pháº©m admin sang `product_repo.py` vá»›i hÃ m `list_admin_product_rows` (xá»­ lÃ½ lá»c bá»™ lá»c, phÃ¢n trang, Ä‘áº¿m tá»•ng sá»‘ báº£n ghi vÃ  gom nhÃ³m cÃ¡c biáº¿n thá»ƒ).
- `product_service.py` hiá»‡n táº¡i chá»‰ cÃ²n giá»¯ láº¡i cÃ¡c luá»“ng ghi/cáº­p nháº­t dá»¯ liá»‡u lá»›n vÃ  phá»©c táº¡p nhÆ° create/update/duplicate vÃ  xá»­ lÃ½ tá»«ng dÃ²ng cá»§a import job.

## Update 2026-06-05 backend admin overview refactor

- TÃ¡ch `backend/app/api/v1/routers/admin_overview.py` theo hÆ°á»›ng Controller - Service.
- Router overview hiá»‡n chá»‰ giá»¯ endpoint `/overview`, permission vÃ  dependency session.
- Chuyá»ƒn toÃ n bá»™ SQL tá»•ng há»£p dashboard sang `backend/app/application/services/overview_service.py`.

## Update 2026-06-05 backend admin products refactor

- TÃ¡ch `backend/app/api/v1/routers/admin_products.py` theo hÆ°á»›ng Controller - Service.
- Router sáº£n pháº©m hiá»‡n chá»‰ giá»¯ endpoint, dependency quyá»n/session, tham sá»‘ query/upload vÃ  chuyá»ƒn tiáº¿p sang `product_service` hoáº·c `attached_service`.
- Chuyá»ƒn cÃ¡c luá»“ng list/suggest/import/export/KPI/audit/create/update/duplicate product sang `backend/app/application/services/product_service.py`.
- Giá»¯ nguyÃªn SQL vÃ  transaction trong service á»Ÿ bÆ°á»›c Ä‘áº§u Ä‘á»ƒ báº£o toÃ n hÃ nh vi cá»§a luá»“ng product lá»›n; repository chi tiáº¿t cho product sáº½ tiáº¿p tá»¥c tÃ¡ch á»Ÿ vÃ²ng sau.

## Update 2026-06-05 backend product approval refactor

- TÃ¡ch `backend/app/api/v1/routers/admin_product_approvals.py` theo hÆ°á»›ng Controller - Service.
- Router duyá»‡t sáº£n pháº©m hiá»‡n chá»‰ giá»¯ cÃ¡c endpoint submit, approve, bulk approve, bulk action, archive vÃ  delete rá»“i chuyá»ƒn tiáº¿p sang `product_approval_service`.
- Chuyá»ƒn luá»“ng nghiá»‡p vá»¥ duyá»‡t sáº£n pháº©m, merge báº£n revision, archive, deactivate vÃ  bulk action sang `backend/app/application/services/product_approval_service.py`.
- Giá»¯ nguyÃªn transaction vÃ  SQL trong service á»Ÿ bÆ°á»›c Ä‘áº§u Ä‘á»ƒ háº¡n cháº¿ Ä‘á»•i hÃ nh vi cá»§a luá»“ng merge revision; repository chi tiáº¿t cho approval sáº½ tÃ¡ch tiáº¿p á»Ÿ vÃ²ng sau.

## Update 2026-06-05 backend product helper refactor

- TÃ¡ch tiáº¿p `admin_product_utils.py`: CÃ¡c helper dÃ¹ng chung cá»§a sáº£n pháº©m Ä‘Æ°á»£c chuyá»ƒn sang `backend/app/application/services/product_helper_service.py`.
- SQL phá»¥ trá»£ cho Ä‘á»“ng bá»™ giÃ¡/tá»“n kho cha vÃ  láº¥y nhÃ£n danh má»¥c/thÆ°Æ¡ng hiá»‡u Ä‘Æ°á»£c chuyá»ƒn sang `backend/app/infrastructure/database/repositories/product_repo.py`.
- Cáº­p nháº­t `admin_products.py`, `admin_product_approvals.py`, `inventory_service.py` vÃ  `product_variant_service.py` Ä‘á»ƒ import helper tá»« táº§ng application thay vÃ¬ tá»« router utils.
- `admin_product_utils.py` giá» chá»‰ lÃ  file tÆ°Æ¡ng thÃ­ch re-export Ä‘á»ƒ trÃ¡nh lÃ m Ä‘á»©t cÃ¡c import cÅ© ngoÃ i luá»“ng refactor.

## Update 2026-06-05 backend product variant refactor

- ÄÃ£ hoÃ n thÃ nh tÃ¡ch vÃ  cáº¥u trÃºc láº¡i module quáº£n lÃ½ biáº¿n thá»ƒ sáº£n pháº©m (`admin_product_variants.py`) theo mÃ´ hÃ¬nh Controller - Service - Repository:
  - **Router tinh gá»n**: [admin_product_variants.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_product_variants.py) hiá»‡n táº¡i chá»‰ cÃ²n endpoint xÃ³a biáº¿n thá»ƒ sáº£n pháº©m vÃ  chuyá»ƒn tiáº¿p lá»i gá»i sang lá»›p Service.
  - **Lá»›p Service (Logic nghiá»‡p vá»¥)**: Chuyá»ƒn toÃ n bá»™ logic xá»­ lÃ½ nghiá»‡p vá»¥ liÃªn quan sang [product_variant_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/product_variant_service.py), bao gá»“m:
    - HÃ m thÃªm má»›i vÃ  cáº­p nháº­t biáº¿n thá»ƒ sáº£n pháº©m (`upsert_product_variants`).
    - HÃ m xÃ³a biáº¿n thá»ƒ sáº£n pháº©m (`delete_product_variant`).
    - CÃ¡c bÆ°á»›c xÃ¡c thá»±c logic: Kiá»ƒm tra trÃ¹ng láº·p mÃ£ SKU, kiá»ƒm tra cáº¥u hÃ¬nh biáº¿n thá»ƒ máº·c Ä‘á»‹nh cá»§a sáº£n pháº©m, kiá»ƒm tra tÃ­nh tÆ°Æ¡ng thÃ­ch giá»¯a thuá»™c tÃ­nh biáº¿n thá»ƒ vá»›i cÃ¡c tÃ¹y chá»n (`options`) cá»§a sáº£n pháº©m cha.
    - Ãnh xáº¡ thÃ´ng sá»‘ (mÃ u sáº¯c, RAM, ROM, thÃ´ng sá»‘ ká»¹ thuáº­t, hÃ¬nh áº£nh, giÃ¡ cáº£ vÃ  sá»‘ lÆ°á»£ng tá»“n kho).
  - **Lá»›p Repository (Truy váº¥n CSDL)**: Chuyá»ƒn toÃ n bá»™ cÃ¢u lá»‡nh SQL vÃ  tÆ°Æ¡ng tÃ¡c DB sang [product_variant_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/product_variant_repo.py), bao gá»“m:
    - Truy váº¥n ngá»¯ cáº£nh sáº£n pháº©m.
    - Kiá»ƒm tra mÃ£ SKU hiá»‡n cÃ³.
    - Láº¥y danh sÃ¡ch cÃ¡c biáº¿n thá»ƒ cá»§a sáº£n pháº©m.
    - Thá»±c hiá»‡n cÃ¡c thao tÃ¡c Insert, Update vÃ  Soft-delete biáº¿n thá»ƒ.
    - Tá»± Ä‘á»™ng cáº¥u hÃ¬nh vÃ  chá»n biáº¿n thá»ƒ máº·c Ä‘á»‹nh má»›i khi cáº§n.
    - Cáº­p nháº­t láº¡i mÃ£ SKU cá»§a sáº£n pháº©m cha.
  - **Äá»“ng bá»™ hÃ³a cÃ¡c router liÃªn quan**: Cáº­p nháº­t [admin_products.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_products.py) Ä‘á»ƒ trá»±c tiáº¿p import vÃ  gá»i `upsert_product_variants` tá»« lá»›p Service má»›i, thay vÃ¬ import tá»« router biáº¿n thá»ƒ cÅ©.
- **ÄÃ£ kiá»ƒm tra ká»¹ thuáº­t**:
  - BiÃªn dá»‹ch thá»­ toÃ n bá»™ code backend báº±ng lá»‡nh `python -m compileall backend/app` thÃ nh cÃ´ng (Pass).
  - Kiá»ƒm tra viá»‡c náº¡p (import) thÃ nh cÃ´ng Ä‘á»‘i vá»›i `app.main`, `admin`, `admin_products`, `admin_product_variants` cÃ¹ng vá»›i service vÃ  repo má»›i láº­p (Pass).
  - ChÆ°a thá»±c hiá»‡n cháº¡y thá»­ nghiá»‡m thao tÃ¡c ghi nháº­n trá»±c tiáº¿p vÃ o DB do cáº§n luá»“ng dá»¯ liá»‡u/API hoÃ n chá»‰nh Ä‘á»ƒ kiá»ƒm thá»­. Vá» máº·t kiáº¿n trÃºc vÃ  mÃ£ nguá»“n, cáº¥u trÃºc quáº£n lÃ½ biáº¿n thá»ƒ Ä‘Ã£ tuÃ¢n thá»§ cháº·t cháº½ mÃ´ hÃ¬nh phÃ¢n lá»›p.

## Update 2026-06-03 React Doctor safe frontend fixes

- Cháº¡y React Doctor á»Ÿ cháº¿ Ä‘á»™ táº¡m thá»i, khÃ´ng cÃ i package vÃ o project vÃ  khÃ´ng thÃªm hook/config.
- Sá»­a lá»—i hook/runtime khÃ´ng Ä‘á»•i giao diá»‡n trong storefront/admin:
  - `ProductDetail.tsx`: Ä‘Æ°a effect phÃ­m táº¯t media viewer lÃªn trÆ°á»›c nhÃ¡nh return sá»›m, thÃªm cleanup cho timer thÃ´ng bÃ¡o thÃªm vÃ o giá» vÃ  khÃ´i phá»¥c overflow khi unmount.
  - `VerifyEmailPage.tsx`: cleanup timer chuyá»ƒn hÆ°á»›ng sau xÃ¡c nháº­n email, trÃ¡nh cáº­p nháº­t state sau khi rá»i trang.
  - `CheckoutPage.tsx`: chuyá»ƒn nhÃ¡nh giá» hÃ ng trá»‘ng xuá»‘ng sau hook tÃ­nh phÃ­ giao hÃ ng Ä‘á»ƒ giá»¯ thá»© tá»± hook á»•n Ä‘á»‹nh; Ä‘á»“ng thá»i phá»¥c há»“i chá»¯ tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong file.
  - CÃ¡c tab admin khÃ¡ch hÃ ng/phÃ¢n quyá»n/dashboard: Ä‘Æ°a cÃ¡c lá»i gá»i quyá»n ra biáº¿n top-level hoáº·c hÃ m render thÆ°á»ng Ä‘á»ƒ trÃ¡nh gá»i hook/component trong JSX/callback.
- Sau sá»­a, `npm run lint` pass vÃ  React Doctor giáº£m Bugs errors tá»« 29 xuá»‘ng 20; pháº§n cÃ²n láº¡i lÃ  nhÃ³m cáº£nh bÃ¡o lá»›n vá» state sync trong luá»“ng catalog/data loading, cáº§n refactor riÃªng Ä‘á»ƒ trÃ¡nh thay Ä‘á»•i hÃ nh vi táº£i dá»¯ liá»‡u ngoÃ i Ã½ muá»‘n.

## Update 2026-06-03 React Doctor Bugs errors cleanup

- Tiáº¿p tá»¥c xá»­ lÃ½ cÃ¡c lá»—i nhÃ³m Bugs cÃ²n láº¡i mÃ  khÃ´ng Ä‘á»•i layout/giao diá»‡n:
  - `useCatalog.ts`: chá»‘t option ranked featured á»Ÿ láº§n mount Ä‘áº§u, thÃªm cleanup cho async load catalog.
  - `ImagesModal.tsx` vÃ  `ReelsModal.tsx`: tÃ¡ch outer/inner modal Ä‘á»ƒ remount ná»™i dung khi má»Ÿ, thay vÃ¬ reset nhiá»u state trong effect; thÃªm cleanup URL query khi Ä‘Ã³ng modal.
  - `ProductReviews.tsx`: remount theo `productId + user`, thÃªm cleanup async vÃ  Ä‘Æ°a prefill review hiá»‡n cÃ³ vÃ o callback eligibility thay vÃ¬ sync form báº±ng effect riÃªng.
  - `VietnamAddressSelector.tsx`: bá» state `wards`, derive danh sÃ¡ch phÆ°á»ng/xÃ£ tá»« `provinces + provinceId` báº±ng `useMemo`; sá»­a má»™t sá»‘ nhÃ£n tiáº¿ng Viá»‡t cÃ³ dáº¥u.
  - `ProductDetail.tsx`: chuyá»ƒn reset lá»±a chá»n sáº£n pháº©m/media sang cáº­p nháº­t cÃ³ Ä‘iá»u kiá»‡n theo `product.id`/`activeVariant.id`; effect Swiper chá»‰ cÃ²n Ä‘iá»u khiá»ƒn slide, khÃ´ng set state React.
- Verification: `npm run lint` pass; React Doctor bÃ¡o Bugs cÃ²n `0 errors`, chá»‰ cÃ²n optional warnings.

## Update 2026-06-03 revision variant specs persistence

- Sá»­a lá»—i khi chá»‰nh sá»­a sáº£n pháº©m Ä‘ang bÃ¡n Ä‘á»ƒ táº¡o `REVISION_DRAFT`: backend `upsert_product_variants` nay lÆ°u `product_variants.specs` tá»« `var.specs` do frontend gá»­i lÃªn, thay vÃ¬ ghi Ä‘Ã¨ báº±ng `attributes`. Nhá» váº­y cÃ¡c thÃ´ng sá»‘ ká»¹ thuáº­t Ä‘Æ°á»£c chá»n lÃ m biáº¿n thá»ƒ nhÆ° RAM/ROM/cáº¥u hÃ¬nh giá»¯ Ä‘Ãºng thay Ä‘á»•i trong báº£n nhÃ¡p chá»‰nh sá»­a.
- `attributes` váº«n Ä‘Æ°á»£c dÃ¹ng riÃªng cho há»£p Ä‘á»“ng `options` vÃ  validate lá»±a chá»n biáº¿n thá»ƒ; `specs` giá»¯ key ká»¹ thuáº­t cá»§a form admin Ä‘á»ƒ khi má»Ÿ láº¡i báº£n nhÃ¡p khÃ´ng bá»‹ Ä‘á»c nháº§m vá» dá»¯ liá»‡u cÅ© hoáº·c nhÃ£n hiá»ƒn thá»‹.

## Update 2026-06-03 admin product form controlled popup close

- Popup thÃªm/sá»­a sáº£n pháº©m trÃªn admin nay cÃ³ tráº¡ng thÃ¡i má»Ÿ/Ä‘Ã³ng riÃªng (`productFormOpen`) thay vÃ¬ chá»‰ dá»±a vÃ o `closeSignal`; sau khi thÃªm hoáº·c lÆ°u thÃ nh cÃ´ng, popup Ä‘Æ°á»£c Ä‘Ã³ng ngay trÆ°á»›c khi reset form Ä‘á»ƒ trÃ¡nh hiá»‡n tÆ°á»£ng modal váº«n má»Ÿ nhÆ°ng ná»™i dung bá»‹ nháº£y vá» form thÃªm má»›i/trá»‘ng.
- `CollapsibleSection` há»— trá»£ thÃªm cháº¿ Ä‘á»™ controlled qua `open` vÃ  `onOpenChange`, trong khi váº«n giá»¯ tÆ°Æ¡ng thÃ­ch vá»›i cÃ¡c popup khÃ¡c Ä‘ang dÃ¹ng tráº¡ng thÃ¡i ná»™i bá»™ vÃ  `closeSignal`.

## Update 2026-06-03 admin merged revision action guard

- Báº£n chá»‰nh sá»­a sáº£n pháº©m sau khi duyá»‡t vÃ  merge vÃ o sáº£n pháº©m gá»‘c cÃ³ tráº¡ng thÃ¡i `MERGED`; Ä‘Ã¢y lÃ  báº£n lá»‹ch sá»­/audit, khÃ´ng Ä‘Æ°á»£c gá»­i duyá»‡t, sá»­a, xÃ³a hoáº·c khÃ´i phá»¥c láº¡i.
- Báº£ng quáº£n trá»‹ sáº£n pháº©m nay chá»‰ hiá»ƒn thá»‹ nhÃ£n "ÄÃ£ Ã¡p dá»¥ng vÃ o sáº£n pháº©m gá»‘c" cho dÃ²ng `MERGED`, thay vÃ¬ cÃ¡c nÃºt thao tÃ¡c váº­n hÃ nh.
- CÃ¡c thao tÃ¡c gá»­i duyá»‡t, duyá»‡t, khÃ´i phá»¥c vÃ  lÆ°u trá»¯ trong `useAdminProductsLogic.ts` Ä‘Æ°á»£c bá»c lá»—i Ä‘á»ƒ admin nháº­n thÃ´ng bÃ¡o rÃµ rÃ ng, khÃ´ng cÃ²n lá»—i promise chÆ°a báº¯t trÃªn console.
- Backend `PATCH /api/v1/admin/products/{id}` vÃ  `DELETE /api/v1/admin/products/{id}` tá»« chá»‘i cáº­p nháº­t/xÃ³a trá»±c tiáº¿p báº£n `MERGED`; backend cÅ©ng tá»« chá»‘i khÃ´i phá»¥c trá»±c tiáº¿p sáº£n pháº©m `ARCHIVED` sang `ACTIVE`.
- Khi táº¡o `REVISION_DRAFT`, `upsert_product_variants` khÃ´ng cÃ²n Ä‘á»“ng bá»™ `products.sku` cá»§a báº£n revision theo SKU biáº¿n thá»ƒ máº·c Ä‘á»‹nh, trÃ¡nh lá»—i trÃ¹ng unique SKU vá»›i sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang active.
- Sau khi chá»‰nh sá»­a sáº£n pháº©m Ä‘ang bÃ¡n, frontend thÃ´ng bÃ¡o rÃµ lÃ  Ä‘Ã£ táº¡o báº£n chá»‰nh sá»­a cáº§n duyá»‡t, tá»± chuyá»ƒn bá»™ lá»c danh sÃ¡ch sang `REVISION_DRAFT` vÃ  Ä‘Ã³ng form trÆ°á»›c khi reset Ä‘á»ƒ khÃ´ng cÃ²n cáº£m giÃ¡c popup bá»‹ Ä‘á»•i sang form thÃªm má»›i.
- Backend `extract_product_metadata` nay nháº­n Ä‘Ãºng cÃ¡c key frontend gá»­i trong `specifications`: `_variantSpecKeys`, `_accessoryOffers`, `_attachedServices`, `_warrantyPolicy`, rá»“i lÆ°u vÃ o `sales_config` chuáº©n. Frontend cÅ©ng fallback Ä‘á»c cÃ¡c key cÅ© nÃ y tá»« `specifications` khi má»Ÿ báº£n nhÃ¡p chá»‰nh sá»­a Ä‘Ã£ táº¡o trÆ°á»›c Ä‘Ã³.
- Sá»­a thá»© tá»± Ä‘Ã³ng popup sáº£n pháº©m: `closeSignal` dÃ¹ng layout effect vÃ  `handleProductSubmit` chá» má»™t frame trÆ°á»›c khi reset form, trÃ¡nh modal cÃ²n má»Ÿ nhÆ°ng ná»™i dung Ä‘Ã£ nháº£y sang form thÃªm má»›i.
- Sá»­a lÆ°u/má»Ÿ láº¡i ROM biáº¿n thá»ƒ trong báº£n chá»‰nh sá»­a: frontend chuáº©n hÃ³a key biáº¿n thá»ƒ tá»« label tiáº¿ng Viá»‡t nhÆ° `Bá»™ nhá»› trong` vá» key `storage`, backend validate option/attribute báº±ng Unicode normalized vÃ  fallback map `Bá»™ nhá»› trong`/`ROM` vÃ o cá»™t `product_variants.storage`. ÄÃ£ test táº¡o revision táº¡m vá»›i ROM `999GB`, DB lÆ°u Ä‘Ãºng `storage = 999GB`, rá»“i xÃ³a revision test.

## Update 2026-06-03 iPhone 17 Pro Max uses iPhone 17 Pro images

- Theo y?u c?u, d?ng `iPhone 17 Pro Max` d?ng chung b? ?nh t? `iPhone 17 Pro` t?i `frontend/public/images/products/iphone-17-pro`.
- Th?m script `backend/scripts/update_iphone_17_pro_max_images_from_pro.py` ?? c?p nh?t `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho d?ng `iPhone 17 Pro Max`.
- ?? ch?y script tr?n DB local cho SKU ch?nh `IP17PM` v? b?n l?u tr? `REV-D3490FAAC5`.
- C?c m?u ???c g?n t??ng ?ng: B?c d?ng `silver`, Cam V? Tr? d?ng `cosmic-orange`, Xanh S?u d?ng `deep-blue`; c?c bi?n th? Pro Max thi?u m?u ???c chuy?n v? Cam V? Tr? ?? kh?ng c?n d?ng ?nh placeholder.

## Update 2026-06-03 storefront shared product video

- Trang chi tiáº¿t sáº£n pháº©m nay Æ°u tiÃªn hiá»ƒn thá»‹ video dÃ¹ng chung á»Ÿ Ä‘áº§u gallery náº¿u sáº£n pháº©m cÃ³ `videoUrl`, giá»‘ng cÃ¡ch CellphoneS Ä‘áº·t thumbnail "Video" lÃ m media Ä‘áº§u tiÃªn.
- Khi gallery má»Ÿ báº±ng video, áº£nh dÃ¹ng cho giá» hÃ ng váº«n fallback sang áº£nh sáº£n pháº©m hoáº·c áº£nh biáº¿n thá»ƒ Ä‘áº§u tiÃªn Ä‘á»ƒ khÃ´ng lÆ°u URL video lÃ m áº£nh sáº£n pháº©m trong cart.

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

- ÄÃ£ tráº£ láº¡i giao diá»‡n tháº» áº£nh sáº£n pháº©m trÃªn `frontend/src/features/media/pages/ImagesPage.tsx` vá» kiá»ƒu cÅ© theo yÃªu cáº§u: khung áº£nh gradient, nhÃ£n ná»•i, khu thÃ´ng tin dÆ°á»›i áº£nh vÃ  nÃºt mua nhá» hiá»‡n theo hover.

## Update 2026-06-03 Product image card UI

- Chá»‰nh láº¡i tháº» áº£nh sáº£n pháº©m trÃªn trang thÆ° viá»‡n áº£nh (`frontend/src/features/media/pages/ImagesPage.tsx`) Ä‘á»ƒ áº£nh sáº£n pháº©m hiá»ƒn thá»‹ thoÃ¡ng hÆ¡n, giáº£m khoáº£ng tráº¯ng xáº¥u quanh áº£nh cao/dá»c.
- LÃ m pháº§n thÃ´ng tin dÆ°á»›i áº£nh gá»n hÆ¡n: tÃªn sáº£n pháº©m, giÃ¡, lÆ°á»£t xem/lÆ°á»£t thÃ­ch vÃ  nÃºt "Xem sáº£n pháº©m" hiá»ƒn thá»‹ cá»‘ Ä‘á»‹nh thay vÃ¬ áº©n khi hover.
- NhÃ£n danh má»¥c vÃ  sá»‘ lÆ°á»£ng áº£nh Ä‘Æ°á»£c thu gá»n Ä‘á»ƒ khÃ´ng láº¥n vÃ o áº£nh sáº£n pháº©m.

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
  - Moi san pham co it nhat mot bien thá»ƒ.
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
- Revision records become `MERGED` after successful publish instead of `ARCHIVED`, and `MERGED` revisions are hidden from the normal admin product list unless explicitly filtered.
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

- Báº£ng sáº£n pháº©m admin Ä‘Ã£ bá» cÃ¡c nÃºt phá»¥ `Preview` vÃ  `Sao chÃ©p` khá»i cá»™t thao tÃ¡c Ä‘á»ƒ giao diá»‡n gá»n hÆ¡n.
- Cá»™t thao tÃ¡c chá»‰ giá»¯ cÃ¡c hÃ nh Ä‘á»™ng váº­n hÃ nh chÃ­nh theo tráº¡ng thÃ¡i sáº£n pháº©m: sá»­a, xÃ³a/áº©n, khÃ´i phá»¥c náº¿u cÃ³, gá»­i duyá»‡t, duyá»‡t vÃ  lÆ°u trá»¯.

## Update 2026-05-31 direct approval bypass for super admin

- Khi tÃ i khoáº£n Ä‘Äƒng nháº­p cÃ³ vai trÃ² `SUPER_ADMIN`, cho phÃ©p duyá»‡t tháº³ng (Duyá»‡t ngay) sáº£n pháº©m tá»« tráº¡ng thÃ¡i `DRAFT` hoáº·c `REVISION_DRAFT` mÃ  khÃ´ng cáº§n Ä‘i qua bÆ°á»›c trung gian `PENDING_REVIEW` (gá»­i duyá»‡t).
- API backend cáº­p nháº­t cÃ¡c route `/products/{product_id}/approve`, `/products/bulk-approve` vÃ  `/products/bulk-action` Ä‘á»ƒ tá»± Ä‘á»™ng kiá»ƒm tra `role_code` cá»§a user vÃ  cho phÃ©p tráº¡ng thÃ¡i `DRAFT`/`REVISION_DRAFT` Ä‘Æ°á»£c duyá»‡t tháº³ng thÃ nh `ACTIVE` Ä‘á»‘i vá»›i Super Admin.
- Frontend hiá»ƒn thá»‹ thÃªm nÃºt "Duyá»‡t tháº³ng" bÃªn cáº¡nh nÃºt "Gá»­i duyá»‡t" trÃªn báº£ng danh sÃ¡ch sáº£n pháº©m dÃ nh riÃªng cho Super Admin.

## Update 2026-05-31 fix duplicate SKU check query

- Sá»­a lá»—i `AmbiguousParameterError: could not determine data type of parameter $3` khi kiá»ƒm tra trÃ¹ng láº·p SKU trong cÆ¡ sá»Ÿ dá»¯ liá»‡u khi cáº­p nháº­t hoáº·c thÃªm sáº£n pháº©m.
- Giáº£i phÃ¡p: Thá»±c hiá»‡n Ã©p kiá»ƒu tÆ°á»ng minh `CAST(:parent_product_id AS UUID)` trong cÃ¢u truy váº¥n `sku_query` cá»§a hÃ m `upsert_product_variants` táº¡i file `admin_products.py`.

## Update 2026-05-31 fix admin products filter logic

- Kháº¯c phá»¥c lá»—i bá»™ lá»c quáº£n lÃ½ sáº£n pháº©m Admin (Danh má»¥c vÃ  ThÆ°Æ¡ng hiá»‡u) khÃ´ng hoáº¡t Ä‘á»™ng do vÃ²ng láº·p phá»¥ thuá»™c state vÃ  closure lá»—i thá»i (stale state) khi gá»i API.
- Giáº£i phÃ¡p: Di chuyá»ƒn cÃ¡c state `productCategoryFilter` vÃ  `productBrandFilter` quay trá»Ÿ láº¡i hook cha `useAdminLogic.ts` Ä‘á»ƒ quáº£n lÃ½ táº­p trung vÃ  Ä‘áº£m báº£o reactivity. Truyá»n cÃ¡c state nÃ y cÃ¹ng setter cá»§a chÃºng xuá»‘ng hook con `useAdminProductsLogic.ts` Ä‘á»ƒ Ä‘á»“ng bá»™ hÃ³a luá»“ng dá»¯ liá»‡u.

## Update 2026-06-01 admin form completion feedback

- Sau khi thÃªm hoáº·c chá»‰nh sá»­a sáº£n pháº©m thÃ nh cÃ´ng, popup sáº£n pháº©m tá»± Ä‘Ã³ng thay vÃ¬ reset vá» tráº¡ng thÃ¡i "ThÃªm sáº£n pháº©m má»›i" ngay trong popup Ä‘ang má»Ÿ.
- Admin nháº­n thÃ´ng bÃ¡o thÃ nh cÃ´ng rÃµ rÃ ng sau khi thÃªm hoáº·c lÆ°u thay Ä‘á»•i sáº£n pháº©m.
- CÃ¹ng Ä‘á»£t nÃ y, cÃ¡c popup quáº£n trá»‹ dÃ¹ng chung `CollapsibleSection` cho thÆ°Æ¡ng hiá»‡u vÃ  voucher cÅ©ng Ä‘Æ°á»£c Ä‘Ã³ng báº±ng `closeSignal` sau khi lÆ°u thÃ nh cÃ´ng Ä‘á»ƒ giá»¯ hÃ nh vi nháº¥t quÃ¡n.

## Update 2026-06-01 product and variant galleries

- Form quáº£n trá»‹ sáº£n pháº©m Ä‘Ã£ cÃ³ láº¡i pháº§n táº£i "Bá»™ áº£nh sáº£n pháº©m chung" vÃ  gá»­i dá»¯ liá»‡u vÃ o `products.images`; sáº£n pháº©m Ä‘Æ¡n giáº£n khÃ´ng cÃ³ biáº¿n thá»ƒ hiá»ƒn thá»‹ Ä‘Æ°á»£c gallery chung thay vÃ¬ chá»‰ cÃ³ áº£nh Ä‘áº¡i diá»‡n.
- Biáº¿n thá»ƒ tÃ¡ch rÃµ `imageUrl` lÃ  áº£nh Ä‘áº¡i diá»‡n biáº¿n thá»ƒ vÃ  `images` lÃ  bá»™ áº£nh riÃªng cá»§a biáº¿n thá»ƒ.
- ThÃªm migration `049_product_variant_images.sql` Ä‘á»ƒ bá»• sung cá»™t `product_variants.images`.
- API admin/catalog tráº£ `images` cho tá»«ng biáº¿n thá»ƒ; trang chi tiáº¿t sáº£n pháº©m gom cáº£ áº£nh Ä‘áº¡i diá»‡n biáº¿n thá»ƒ vÃ  bá»™ áº£nh biáº¿n thá»ƒ vÃ o gallery hiá»ƒn thá»‹.
## Update 2026-06-01 storefront product detail scroll

- Ghi chÃº: bá»‘ cá»¥c nÃ y Ä‘Ã£ Ä‘Æ°á»£c thay báº±ng báº£n sticky á»Ÿ má»¥c káº¿ tiáº¿p Ä‘á»ƒ giáº£m khoáº£ng tráº¯ng tá»‘t hÆ¡n.
- Trang chi tiáº¿t sáº£n pháº©m trÃªn mÃ n hÃ¬nh lá»›n dÃ¹ng hai cá»™t Ä‘á»™c láº­p cho khu áº£nh/thÃ´ng sá»‘ nhanh vÃ  khu giÃ¡/tuá»³ chá»n mua hÃ ng.
- Má»—i cá»™t chá»‰ giá»›i háº¡n chiá»u cao theo pháº§n nhÃ¬n tháº¥y há»£p lÃ½, khÃ´ng Ã©p chiá»u cao khi ná»™i dung ngáº¯n Ä‘á»ƒ trÃ¡nh táº¡o khoáº£ng tráº¯ng thá»«a.
- Khi cuá»™n tá»›i Ä‘áº§u hoáº·c cuá»‘i má»™t cá»™t, pháº§n cuá»™n cÃ²n láº¡i Ä‘Æ°á»£c chuyá»ƒn tiáº¿p ra trang Ä‘á»ƒ ngÆ°á»i dÃ¹ng Ä‘i xuá»‘ng ná»™i dung mÃ´ táº£, sáº£n pháº©m gá»£i Ã½ vÃ  Ä‘Ã¡nh giÃ¡ tá»± nhiÃªn hÆ¡n.

## Update 2026-06-01 storefront product detail sticky layout

- Trang chi tiáº¿t sáº£n pháº©m Ä‘á»•i tá»« hai cá»™t cuá»™n Ä‘á»™c láº­p sang bá»‘ cá»¥c cá»™t trÃ¡i sticky vÃ  cá»™t pháº£i cuá»™n theo trang Ä‘á»ƒ giáº£m khoáº£ng tráº¯ng vÃ  giá»¯ áº£nh sáº£n pháº©m lÃ m Ä‘iá»ƒm neo thá»‹ giÃ¡c.
- Pháº§n thÃ´ng sá»‘ ká»¹ thuáº­t trÃªn storefront Ä‘á»c linh hoáº¡t cáº£ `specs` vÃ  `specifications`, há»— trá»£ dá»¯ liá»‡u dáº¡ng object hoáº·c máº£ng `{ key, label, value, group }`.
- Tuá»³ chá»n phiÃªn báº£n/mÃ u sáº¯c trÃªn storefront Ä‘Æ°á»£c chuáº©n hoÃ¡ label/key trÆ°á»›c khi render Ä‘á»ƒ trÃ¡nh lá»—i React khi API tráº£ object nhÆ° `{ name }`.
- ThÃ´ng sá»‘ sáº£n pháº©m cÃ³ thÃªm alias vÃ  fallback label tiáº¿ng Viá»‡t á»Ÿ storefront, vÃ­ dá»¥ `screenSize` Ä‘Æ°á»£c chuáº©n hoÃ¡ vá» `screen_size`, cÃ¡c key nhÆ° `wifi`, `bluetooth`, `rear_video`, `noise_cancellation` Ä‘Æ°á»£c hiá»ƒn thá»‹ báº±ng tÃªn tiáº¿ng Viá»‡t.

## Update 2026-06-01 storefront product detail premium CellphoneS style

- Cáº£i tiáº¿n giao diá»‡n trang chi tiáº¿t sáº£n pháº©m láº¥y cáº£m há»©ng tá»« CellphoneS:
  - NÃºt chá»n dung lÆ°á»£ng vÃ  mÃ u sáº¯c tá»± Ä‘á»™ng hiá»ƒn thá»‹ giÃ¡ bÃ¡n tÆ°Æ¡ng á»©ng phÃ­a dÆ°á»›i (truy xuáº¥t tá»« biáº¿n thá»ƒ cá»§a sáº£n pháº©m).
  - NÃºt tráº£ gÃ³p chia thÃ nh 2 nÃºt song song: "TRáº¢ GÃ“P 0%" (tÃ´ng vÃ ng cam) vÃ  "TRáº¢ GÃ“P QUA THáºº" (tÃ´ng xanh dÆ°Æ¡ng) vá»›i thÃ´ng tin phá»¥ trá»±c quan.
  - Pháº§n mÃ´ táº£ sáº£n pháº©m (Product Description) máº·c Ä‘á»‹nh giá»›i háº¡n chiá»u cao tá»‘i Ä‘a 400px, cÃ³ hiá»‡u á»©ng phá»§ má» Ä‘Ã¡y (gradient fadeout) vÃ  nÃºt toggle "Xem thÃªm / Thu gá»n".
  - CÃ¡c nÃºt tÃ¡c vá»¥ nhanh á»Ÿ Ä‘áº§u trang (YÃªu thÃ­ch, Há»i Ä‘Ã¡p, ThÃ´ng sá»‘, So sÃ¡nh) Ä‘Æ°á»£c phá»‘i mÃ u xÃ¡m Ä‘en vá»›i hiá»‡u á»©ng chuyá»ƒn mÃ u Ä‘á» khi hover Ä‘á»“ng bá»™ vá»›i tÃ´ng mÃ u Ä‘á» cá»§a shop.
  - Gom nhÃ³m cÃ¡c khá»‘i ná»™i dung rá»i ráº¡c á»Ÿ cá»™t pháº£i thÃ nh 2 Card lá»›n thá»‘ng nháº¥t: "Purchase Card" (chá»©a giÃ¡, cÃ¡c phiÃªn báº£n chá»n, khuyáº¿n mÃ£i lá»“ng bÃªn trong, sá»‘ lÆ°á»£ng, cá»¥m nÃºt thanh toÃ¡n vÃ  tráº£ gÃ³p) vÃ  "Information Card" (chá»©a Äáº·c Ä‘iá»ƒm ná»•i báº­t + MÃ´ táº£ chi tiáº¿t phÃ¢n cÃ¡ch bá»Ÿi má»™t Ä‘Æ°á»ng káº» máº£nh), giÃºp loáº¡i bá» hoÃ n toÃ n cÃ¡c khoáº£ng trá»‘ng lá» thá»«a rá»i ráº¡c á»Ÿ cá»™t pháº£i.
  - Loáº¡i bá» hoÃ n toÃ n ná»n tráº¯ng cá»§a khung bao Thumbs Swiper Ä‘á»ƒ cÃ¡c áº£nh con ná»•i tá»± nhiÃªn trÃªn ná»n xÃ¡m cá»§a trang, triá»‡t tiÃªu khoáº£ng trá»‘ng tráº¯ng thá»«a bÃªn pháº£i. Äá»“ng thá»i Ä‘á»•i áº£nh lá»›n sang kÃ­ch thÆ°á»›c Ä‘á»™ng `w-[90%] h-[90%]` Ä‘á»ƒ láº¥p Ä‘áº§y há»™p tráº¯ng trÆ°ng bÃ y cÃ¢n Ä‘á»‘i.
  - Sá»­ dá»¥ng Grid tá»· lá»‡ `lg:grid-cols-[500px_1fr]` cá»‘ Ä‘á»‹nh cá»™t trÃ¡i 500px vÃ  loáº¡i bá» `mx-auto` trÃªn `<aside>` Ä‘á»ƒ cá»™t trÃ¡i bÃ¡m sÃ¡t lá» trÃ¡i trang, thu háº¹p khoáº£ng há»Ÿ dá»c trá»‘ng tráº£i á»Ÿ giá»¯a hai cá»™t.
  - Chuyá»ƒn ná»n trang sang tráº¯ng tinh (`bg-white`), lÃ m pháº³ng tiÃªu Ä‘á» vÃ  Ã´ cam káº¿t, loáº¡i bá» bÃ³ng Ä‘á»• bá»c ngoÃ i á»Ÿ táº¥t cáº£ cÃ¡c khá»‘i (chá»‰ dÃ¹ng viá»n máº£nh `border-gray-200`) vÃ  Ä‘á»ƒ cÃ¡c pháº§n tá»­ mua hÃ ng á»Ÿ cá»™t pháº£i cháº£y trá»±c tiáº¿p trÃªn ná»n tráº¯ng khÃ´ng Ä‘Ã³ng há»™p bá»c ngoÃ i, pháº£n Ã¡nh chÃ­nh xÃ¡c phong cÃ¡ch tá»‘i giáº£n pháº³ng (Flat Design) cá»§a CellphoneS.

## Update 2026-06-01 storefront product detail real data migration

- Loáº¡i bá» hoÃ n toÃ n cÃ¡c dá»¯ liá»‡u giáº£ (fallback promotions máº·c Ä‘á»‹nh, phá»¥ kiá»‡n mua kÃ¨m cá»©ng) khá»i trang chi tiáº¿t sáº£n pháº©m.
- Sá»­a Catalog API `GET /catalog/products/{product_id}` Ä‘á»ƒ tráº£ vá» `salesConfig` vÃ  tá»± Ä‘á»™ng resolve thÃ´ng tin chi tiáº¿t cÃ¡c sáº£n pháº©m phá»¥ kiá»‡n trong `accessoryOffers` (bao gá»“m tÃªn, SKU, hÃ¬nh áº£nh, giÃ¡ gá»‘c, giÃ¡ bÃ¡n hiá»‡n táº¡i vÃ  giÃ¡ sau Æ°u Ä‘Ã£i mua kÃ¨m).
- Cáº­p nháº­t frontend `ProductDetail.tsx` Ä‘á»ƒ áº©n khá»‘i Khuyáº¿n mÃ£i náº¿u sáº£n pháº©m khÃ´ng cáº¥u hÃ¬nh `promotions` trong DB.
- Cáº­p nháº­t frontend `BundleOffers` Ä‘á»ƒ áº©n khá»‘i Æ¯u Ä‘Ã£i mua kÃ¨m náº¿u sáº£n pháº©m khÃ´ng cÃ³ `accessoryOffers` thá»±c táº¿. Khi hiá»ƒn thá»‹, khá»‘i sáº½ render tÃªn, hÃ¬nh áº£nh, giÃ¡ bÃ¡n láº» hiá»‡n táº¡i vÃ  giÃ¡ Æ°u Ä‘Ã£i mua kÃ¨m thá»±c táº¿ cá»§a cÃ¡c phá»¥ kiá»‡n Ä‘Æ°á»£c liÃªn káº¿t.
- Sá»­a Ä‘á»•i logic tÃ­nh Ä‘iá»ƒm xu hÆ°á»›ng rankings (`ranking_row` trong `catalog.py`): Náº¿u sáº£n pháº©m khÃ´ng phÃ¡t sinh tÆ°Æ¡ng tÃ¡c nÃ o (lÆ°á»£t xem, tÃ¬m kiáº¿m, lÆ°á»£t mua) trong khoáº£ng thá»i gian trÆ°á»£t Ä‘Ã£ chá»n (vÃ­ dá»¥ 24h), Ä‘iá»ƒm xu hÆ°á»›ng sáº½ tráº£ vá» 0 thay vÃ¬ neo giá»¯ Ä‘iá»ƒm tÃ­ch lÅ©y trá»n Ä‘á»i (tá»« lÆ°á»£t yÃªu thÃ­ch/Ä‘Ã¡nh giÃ¡).
- Cáº¥u trÃºc cÆ¡ cháº¿ sáº¯p xáº¿p phÃ¢n táº§ng (multi-level fallback) trong Rankings: Khi cÃ¡c sáº£n pháº©m cÃ¹ng báº±ng Ä‘iá»ƒm nhau á»Ÿ tiÃªu chÃ­ chÃ­nh (vÃ­ dá»¥ cÃ¹ng báº±ng 0 Ä‘iá»ƒm xu hÆ°á»›ng á»Ÿ khoáº£ng thá»i gian 24h), há»‡ thá»‘ng sáº½ tá»± Ä‘á»™ng so sÃ¡nh qua cÃ¡c cáº¥p tiáº¿p theo gá»“m má»‘c 24h, má»‘c 7 ngÃ y, má»‘c 30 ngÃ y, má»‘c 1 nÄƒm, rá»“i Ä‘áº¿n doanh thu chu ká»³ vÃ  cuá»‘i cÃ¹ng lÃ  Ä‘iá»ƒm Ä‘Ã¡nh giÃ¡ cá»§a sáº£n pháº©m. Logic nÃ y Ã¡p dá»¥ng Ä‘á»“ng bá»™ cho táº¥t cáº£ cÃ¡c tiÃªu chÃ­ sáº¯p xáº¿p (trending, sold, view, search, like, rating) vÃ  loáº¡i bá» hoÃ n toÃ n cÃ¡c má»‘c "ká»³ trÆ°á»›c" (previous period) Ä‘á»ƒ Ä‘áº£m báº£o tuÃ¢n thá»§ Ä‘Ãºng yÃªu cáº§u má»‘c thá»i gian tÄƒng dáº§n cá»§a ngÆ°á»i dÃ¹ng.
- ThÃªm `like_stats` vÃ  `rating_stats` theo cÃ¡c má»‘c thá»i gian vÃ o cÃ¢u SQL cá»§a Rankings API Ä‘á»ƒ há»— trá»£ Ä‘áº§y Ä‘á»§ cÆ¡ cháº¿ so sÃ¡nh phÃ¢n táº§ng cho hai tÃ¹y chá»n "ÄÆ°á»£c yÃªu thÃ­ch nháº¥t" (like) vÃ  "ÄÃ¡nh giÃ¡ cao nháº¥t" (rating).
- Sá»­a Ä‘iá»ƒm xu hÆ°á»›ng Rankings Ä‘á»ƒ lÆ°á»£t yÃªu thÃ­ch/Ä‘Ã¡nh giÃ¡ chá»‰ Ä‘Æ°á»£c tÃ­nh theo Ä‘Ãºng khoáº£ng thá»i gian Ä‘ang xem. VÃ­ dá»¥ má»‘c 24h chá»‰ cá»™ng lÆ°á»£t thÃ­ch vÃ  Ä‘Ã¡nh giÃ¡ má»›i trong 24h, khÃ´ng cá»™ng tá»•ng `favorite_count`/`review_count` trá»n Ä‘á»i sáº£n pháº©m vÃ o Ä‘iá»ƒm xu hÆ°á»›ng.
- Rankings khÃ´ng cÃ²n láº¥y `rating`, `review_count`, `favorite_count` trá»±c tiáº¿p tá»« báº£ng `products` vÃ¬ cÃ¡c cá»™t nÃ y cÃ³ thá»ƒ chá»©a dá»¯ liá»‡u seed/tá»•ng há»£p cÅ©. API rankings tÃ­nh láº¡i cÃ¡c chá»‰ sá»‘ nÃ y tá»« báº£ng phÃ¡t sinh tháº­t gá»“m `product_reviews` vÃ  `user_favorites`; tiÃªu chÃ­ "YÃªu thÃ­ch" vÃ  "ÄÃ¡nh giÃ¡" Æ°u tiÃªn dá»¯ liá»‡u trong khoáº£ng thá»i gian Ä‘ang chá»n.
- Biá»ƒu Ä‘á»“ `history` cá»§a Rankings chia bucket cá»‘ Ä‘á»‹nh theo má»‘c hiá»ƒn thá»‹: 24h = 24 khung giá», 7d = 7 ngÃ y, 30d = 30 ngÃ y, 1y = 12 thÃ¡ng. Bucket Ä‘Æ°á»£c neo vÃ o Ä‘áº§u giá»/ngÃ y/thÃ¡ng Ä‘á»ƒ label khÃ´ng bá»‹ lá»‡ch hoáº·c dÆ° Ä‘iá»ƒm cuá»‘i.

## Update 2026-06-02 product favorite event history

- ThÃªm migration `050_product_favorite_events.sql` Ä‘á»ƒ bá»• sung `is_active`, `updated_at` cho `user_favorites` vÃ  táº¡o báº£ng `user_favorite_events` ghi nháº­t kÃ½ `LIKE`/`UNLIKE` kÃ¨m `created_at`.
- API yÃªu thÃ­ch sáº£n pháº©m khÃ´ng xÃ³a cá»©ng dÃ²ng yÃªu thÃ­ch ná»¯a. Khi há»§y yÃªu thÃ­ch, há»‡ thá»‘ng chuyá»ƒn `is_active = FALSE` vÃ  ghi sá»± kiá»‡n `UNLIKE`; khi yÃªu thÃ­ch láº¡i, há»‡ thá»‘ng báº­t `is_active = TRUE`, cáº­p nháº­t thá»i gian tráº¡ng thÃ¡i hiá»‡n táº¡i vÃ  ghi sá»± kiá»‡n `LIKE` má»›i.
- Rankings tÃ­nh cÃ¡c chá»‰ sá»‘ yÃªu thÃ­ch theo 24h/7d/30d/1y tá»« báº£ng `user_favorite_events` vá»›i `action = 'LIKE'`, giÃºp dá»¯ liá»‡u lá»‹ch sá»­ khÃ´ng bá»‹ máº¥t khi ngÆ°á»i dÃ¹ng há»§y yÃªu thÃ­ch sau Ä‘Ã³. Danh sÃ¡ch sáº£n pháº©m yÃªu thÃ­ch cá»§a ngÆ°á»i dÃ¹ng váº«n chá»‰ hiá»ƒn thá»‹ cÃ¡c dÃ²ng `is_active = TRUE`.
- API `GET /catalog/favorites` tráº£ thÃªm `favoritedAt` vÃ  `favoriteUpdatedAt`; tab "Sáº£n pháº©m yÃªu thÃ­ch" trÃªn tÃ i khoáº£n hiá»ƒn thá»‹ thá»i Ä‘iá»ƒm ngÆ°á»i dÃ¹ng yÃªu thÃ­ch sáº£n pháº©m.
- API toggle yÃªu thÃ­ch cÃ³ rate limit qua Redis theo cáº·p user/sáº£n pháº©m: tá»‘i Ä‘a 5 láº§n thÃ­ch/há»§y trong 10 giÃ¢y. Náº¿u vÆ°á»£t ngÆ°á»¡ng, tráº£ 429 vá»›i thÃ´ng bÃ¡o "Báº¡n thao tÃ¡c yÃªu thÃ­ch quÃ¡ nhanh. Vui lÃ²ng thá»­ láº¡i sau vÃ i giÃ¢y." Ä‘á»ƒ giáº£m spam lÃ m nhiá»…u event log vÃ  rankings.
- Rankings tÃ­nh "YÃªu thÃ­ch" theo Ä‘iá»ƒm rÃ²ng tá»« event log: `LIKE = +1`, `UNLIKE = -1`. VÃ¬ váº­y náº¿u ngÆ°á»i dÃ¹ng há»§y yÃªu thÃ­ch trong 24h/7d/30d/1y thÃ¬ chá»‰ sá»‘ cÃ³ thá»ƒ Ä‘i xuá»‘ng á»Ÿ Ä‘Ãºng bucket thá»i gian Ä‘Ã³; náº¿u thÃ­ch láº¡i thÃ¬ tÄƒng láº¡i. CÃ¡ch nÃ y trÃ¡nh viá»‡c spam thÃ­ch/há»§y/thÃ­ch lÃ m buff nhiá»u lÆ°á»£t `LIKE` giáº£ trong cÃ¹ng má»™t khoáº£ng thá»i gian.
## Update 2026-06-02 storefront product list filters

- Trang danh sÃ¡ch sáº£n pháº©m Ä‘á»•i bá»™ lá»c Danh má»¥c vÃ  HÃ£ng tá»« danh sÃ¡ch nÃºt/chip sang danh sÃ¡ch sá»• xuá»‘ng Ä‘á»ƒ gá»n hÆ¡n khi dá»¯ liá»‡u nhiá»u.
- Bá»™ lá»c giÃ¡ trÃªn storefront dÃ¹ng má»™t thanh trÆ°á»£t khoáº£ng giÃ¡ chung vÃ  hai Ã´ nháº­p thá»§ cÃ´ng cho giÃ¡ tá»‘i thiá»ƒu/tá»‘i Ä‘a Ä‘áº¿n 100 triá»‡u; giÃ¡ tÃ¹y chá»‰nh tiáº¿p tá»¥c ghi vÃ o query `min_price`/`max_price` Ä‘á»ƒ dÃ¹ng chung luá»“ng lá»c catalog hiá»‡n cÃ³.
- Tháº» sáº£n pháº©m storefront bá» nÃºt So sÃ¡nh dáº¡ng overlay chá»‰ hiá»‡n khi rÃª chuá»™t trÃªn desktop; nÃºt So sÃ¡nh nay hiá»ƒn thá»‹ cá»‘ Ä‘á»‹nh trong chÃ¢n tháº» Ä‘á»ƒ ngÆ°á»i dÃ¹ng dá»… chá»n hÆ¡n.

## Update 2026-06-03 smartphone product specifications update

- Thá»±c hiá»‡n cáº­p nháº­t Ä‘áº§y Ä‘á»§ thÃ´ng sá»‘ ká»¹ thuáº­t (specifications) cho toÃ n bá»™ sáº£n pháº©m thuá»™c danh má»¥c Ä‘iá»‡n thoáº¡i (smartphones).
- Cáº­p nháº­t trá»±c tiáº¿p file SQL seed `backend/migrations/init_database.sql` cho 5 máº«u Ä‘iá»‡n thoáº¡i flagship: iPhone 16 Pro Max (`IP16PM`), Samsung Galaxy S24 Ultra (`S24U`), Samsung Galaxy Z Fold6 (`ZFOLD6`), Xiaomi 14 Ultra (`X14U`), vÃ  OPPO Find N3 (`OPPFN3`) vá»›i Ä‘áº§y Ä‘á»§ 42 trÆ°á»ng specifications theo chuáº©n cá»§a danh má»¥c.
- Cháº¡y script Python `update_smartphone_specs.py` Ä‘á»ƒ bá»• sung vÃ  chuáº©n hÃ³a dá»¯ liá»‡u thá»±c táº¿ báº±ng tiáº¿ng Viá»‡t cÃ³ dáº¥u cho cÃ¡c trÆ°á»ng cÃ²n thiáº¿u (bao gá»“m `brightness`, `video_recording`, `connectivity`...) cho toÃ n bá»™ 38 sáº£n pháº©m Ä‘iá»‡n thoáº¡i Ä‘ang tá»“n táº¡i trong cÆ¡ sá»Ÿ dá»¯ liá»‡u.
- Äáº£m báº£o 100% trÆ°á»ng specifications Ä‘Æ°á»£c Ä‘iá»n giÃ¡ trá»‹ chuáº©n vÃ  hiá»ƒn thá»‹ Ä‘á»“ng bá»™ trÃªn storefront.
## Update 2026-06-03 flash sale management

- ThÃªm migration `051_flash_sales.sql` táº¡o báº£ng `flash_sales` tÃ¡ch riÃªng khá»i báº£ng `products`.
- Admin cÃ³ module riÃªng:
  - Backend: `backend/app/api/v1/routers/admin_flash_sales.py`.
  - Frontend hook: `frontend/src/features/admin-flash-sales/hooks/useAdminFlashSalesLogic.ts`.
  - Frontend tab: `frontend/src/features/admin-flash-sales/components/AdminFlashSalesTab.tsx`.
- File chÃ­nh chá»‰ Ä‘Äƒng kÃ½ router/tab/API Ä‘á»ƒ giá»¯ Ä‘Ãºng nguyÃªn táº¯c khÃ´ng nhá»“i logic flash sale vÃ o module quáº£n lÃ½ sáº£n pháº©m.
- Flash sale há»— trá»£ chá»n sáº£n pháº©m, giáº£m theo pháº§n trÄƒm hoáº·c sá»‘ tiá»n, thá»i gian báº¯t Ä‘áº§u, thá»i gian káº¿t thÃºc hoáº·c khÃ´ng cÃ³ thá»i háº¡n, thÃªm, sá»­a, xÃ³a vÃ  báº­t/táº¯t tráº¡ng thÃ¡i.
- Backend kiá»ƒm tra giÃ¡ flash sale pháº£i lá»›n hÆ¡n 0 vÃ  nhá» hÆ¡n giÃ¡ bÃ¡n hiá»‡n táº¡i cá»§a sáº£n pháº©m trÆ°á»›c khi lÆ°u.
- Catalog API tÃ­nh giÃ¡ flash sale Ä‘á»™ng khi sale Ä‘ang hiá»‡u lá»±c, khÃ´ng ghi Ä‘Ã¨ `products.price` hoáº·c `products.sale_price`.
- Storefront product card vÃ  trang chi tiáº¿t sáº£n pháº©m Æ°u tiÃªn hiá»ƒn thá»‹ giÃ¡ flash sale, giÃ¡ gá»‘c bá»‹ gáº¡ch vÃ  nhÃ£n/báº£ng thÃ´ng bÃ¡o flash sale Ä‘ang diá»…n ra.
## Update 2026-06-03 storefront product detail real metrics

- Trang chi tiáº¿t sáº£n pháº©m khÃ´ng cÃ²n dÃ¹ng sá»‘ liá»‡u áº£o cho Ä‘Ã¡nh giÃ¡ vÃ  Ä‘Ã£ bÃ¡n:
  - KhÃ´ng fallback rating vá» `4.8`.
  - KhÃ´ng fallback Ä‘Ã£ bÃ¡n vá» `128`.
  - Khi chÆ°a cÃ³ dá»¯ liá»‡u, rating hiá»ƒn thá»‹ "ChÆ°a cÃ³ Ä‘Ã¡nh giÃ¡", sá»‘ Ä‘Ã¡nh giÃ¡ vÃ  Ä‘Ã£ bÃ¡n hiá»ƒn thá»‹ `0`.
- Frontend khÃ´ng cÃ²n thay áº£nh sáº£n pháº©m theo báº£ng áº£nh demo trong `apiDb.ts`; áº£nh sáº£n pháº©m láº¥y tá»« dá»¯ liá»‡u backend/database vÃ  chá»‰ Ä‘Æ°á»£c chuáº©n hÃ³a URL.
- API chi tiáº¿t sáº£n pháº©m tÃ­nh `rating`, `reviewCount`, `favoriteCount` trá»±c tiáº¿p tá»« `product_reviews` vÃ  `user_favorites`; `soldCount` tiáº¿p tá»¥c tÃ­nh tá»« `order_items` cá»§a Ä‘Æ¡n `COMPLETED`.

## Update 2026-06-03 storefront product detail variant configuration

- Trang chi tiáº¿t sáº£n pháº©m Ä‘á»•i khu chá»n "PhiÃªn báº£n" thÃ nh "Cáº¥u hÃ¬nh" Ä‘á»ƒ ngÆ°á»i mua biáº¿t rÃµ biáº¿n thá»ƒ Ä‘ang chá»n theo thÃ´ng sá»‘ nÃ o.
- Frontend dá»±ng nhÃ£n cáº¥u hÃ¬nh tá»« dá»¯ liá»‡u biáº¿n thá»ƒ tháº­t, Æ°u tiÃªn `ram`, `storage`/ROM vÃ  `configuration`; vÃ­ dá»¥ `RAM 8GB / ROM 256GB`.
- Má»—i nÃºt cáº¥u hÃ¬nh hiá»ƒn thá»‹ thÃªm chip thÃ´ng sá»‘ nhá» nhÆ° `RAM: 8GB`, `ROM: 256GB` vÃ  giÃ¡ cá»§a biáº¿n thá»ƒ tÆ°Æ¡ng á»©ng, Æ°u tiÃªn Ä‘Ãºng mÃ u Ä‘ang chá»n náº¿u sáº£n pháº©m cÃ³ nhiá»u mÃ u.
- Catalog API chi tiáº¿t sáº£n pháº©m tráº£ thÃªm `options` Ä‘á»ƒ storefront cÃ³ Ä‘á»§ dá»¯ liá»‡u cáº¥u hÃ¬nh biáº¿n thá»ƒ tá»« database.

## Update 2026-06-03 storefront color-scoped variant configuration

- Khu chá»n cáº¥u hÃ¬nh trÃªn trang chi tiáº¿t sáº£n pháº©m nay lá»c theo mÃ u Ä‘ang chá»n: náº¿u mÃ u Ä‘Ã³ cÃ³ 3 biáº¿n thá»ƒ thÃ¬ chá»‰ hiá»ƒn thá»‹ 3 lá»±a chá»n cáº¥u hÃ¬nh cá»§a mÃ u Ä‘Ã³.
- NhÃ£n cáº¥u hÃ¬nh Ä‘Æ°á»£c rÃºt gá»n Ä‘á»ƒ trÃ¡nh láº·p `ROM 512GB / Cáº¥u hÃ¬nh 512GB`; khi chá»‰ cÃ³ bá»™ nhá»› thÃ¬ hiá»ƒn thá»‹ `512GB`, khi cÃ³ RAM vÃ  ROM thÃ¬ hiá»ƒn thá»‹ dáº¡ng `8GB / 512GB`.
- Khi Ä‘á»•i mÃ u, náº¿u cáº¥u hÃ¬nh Ä‘ang chá»n khÃ´ng tá»“n táº¡i á»Ÿ mÃ u má»›i, storefront tá»± chuyá»ƒn sang cáº¥u hÃ¬nh Ä‘áº§u tiÃªn cÃ³ sáºµn cá»§a mÃ u Ä‘Ã³ Ä‘á»ƒ giÃ¡ vÃ  biáº¿n thá»ƒ active luÃ´n khá»›p dá»¯ liá»‡u tháº­t.

## Update 2026-06-03 storefront split RAM ROM selection

- Trang chi tiáº¿t sáº£n pháº©m khÃ´ng cÃ²n chá»‰ chá»n cáº¥u hÃ¬nh gá»™p; storefront tÃ¡ch nhÃ³m chá»n theo tá»«ng thÃ´ng sá»‘ biáº¿n thá»ƒ riÃªng nhÆ° `RAM`, `ROM` vÃ  cáº¥u hÃ¬nh phá»¥ náº¿u cÃ³.
- Danh sÃ¡ch RAM/ROM Ä‘Æ°á»£c dá»±ng tá»« cÃ¡c biáº¿n thá»ƒ tháº­t cá»§a mÃ u Ä‘ang chá»n; náº¿u mÃ u Ä‘Ã³ chá»‰ cÃ³ má»™t biáº¿n thá»ƒ thÃ¬ váº«n hiá»ƒn thá»‹ cáº¥u hÃ¬nh duy nháº¥t Ä‘á»ƒ ngÆ°á»i mua biáº¿t rÃµ Ä‘ang chá»n gÃ¬.
- GiÃ¡ bÃ¡n láº¥y tá»« biáº¿n thá»ƒ khá»›p vá»›i mÃ u + RAM + ROM Ä‘ang chá»n. Khi Ä‘á»•i RAM, há»‡ thá»‘ng giá»¯ ROM hiá»‡n táº¡i náº¿u cÃ²n há»£p lá»‡; náº¿u khÃ´ng, tá»± chá»n ROM Ä‘áº§u tiÃªn cÃ³ trong RAM má»›i.
- NÃºt chá»n mÃ u khÃ´ng hiá»ƒn thá»‹ giÃ¡ riÃªng ná»¯a Ä‘á»ƒ trÃ¡nh hiá»ƒu nháº§m mÃ u cÃ³ giÃ¡ cá»‘ Ä‘á»‹nh; giÃ¡ chá»‰ hiá»‡n á»Ÿ khu giÃ¡ chÃ­nh vÃ  cÃ¡c lá»±a chá»n cáº¥u hÃ¬nh cÃ³ áº£nh hÆ°á»Ÿng trá»±c tiáº¿p tá»›i biáº¿n thá»ƒ.
- ThÃ´ng sá»‘ ká»¹ thuáº­t trÃªn trang chi tiáº¿t nay merge thÃ´ng sá»‘ cá»§a biáº¿n thá»ƒ Ä‘ang chá»n vÃ o thÃ´ng sá»‘ sáº£n pháº©m trÆ°á»›c khi hiá»ƒn thá»‹, nÃªn RAM/ROM vÃ  cÃ¡c specs biáº¿n thá»ƒ tá»± Ä‘á»•i theo cáº¥u hÃ¬nh active thay vÃ¬ hiá»‡n giÃ¡ trá»‹ tá»•ng há»£p nhÆ° `256 GB / 512 GB`.
- TÃªn sáº£n pháº©m trÃªn H1 cá»§a trang chi tiáº¿t gá»™p luÃ´n cáº¥u hÃ¬nh dáº¡ng `TÃªn sáº£n pháº©m - RAM / ROM`, vÃ­ dá»¥ `HONOR 400 Pro - 12GB / 512GB`. Náº¿u biáº¿n thá»ƒ thiáº¿u RAM hoáº·c ROM riÃªng, storefront fallback sang thÃ´ng sá»‘ chung cá»§a sáº£n pháº©m Ä‘á»ƒ ngÆ°á»i mua váº«n tháº¥y cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§.

## Update 2026-06-03 storefront specs modal overflow fix

- Sá»­a popup "ThÃ´ng sá»‘ ká»¹ thuáº­t" trÃªn trang chi tiáº¿t sáº£n pháº©m Ä‘á»ƒ thanh chá»n nhÃ³m thÃ´ng sá»‘ khÃ´ng bá»‹ che hoáº·c cáº¯t bá»Ÿi vÃ¹ng ná»™i dung.
- Header vÃ  thanh chá»n nhÃ³m Ä‘Æ°á»£c giá»¯ á»Ÿ vÃ¹ng riÃªng, pháº§n báº£ng thÃ´ng sá»‘ chá»‰ cuá»™n dá»c vÃ  khÃ´ng táº¡o cuá»™n ngang cho toÃ n modal.
- Ná»™i dung label/value trong báº£ng thÃ´ng sá»‘ tá»± xuá»‘ng dÃ²ng Ä‘á»ƒ trÃ¡nh kÃ©o rá»™ng modal khi thÃ´ng sá»‘ dÃ i.
- Thanh chá»n nhÃ³m thÃ´ng sá»‘ trong popup nay lÃ  Ä‘iá»u hÆ°á»›ng cuá»™n tá»›i nhÃ³m tÆ°Æ¡ng á»©ng, khÃ´ng cÃ²n lá»c áº©n cÃ¡c nhÃ³m thÃ´ng sá»‘ khÃ¡c.
- Khi báº¥m nhÃ³m thÃ´ng sá»‘, modal chá»«a khoáº£ng Ä‘á»‡m phÃ­a trÃªn section Ä‘Ã­ch Ä‘á»ƒ tiÃªu Ä‘á» vÃ  dÃ²ng Ä‘áº§u khÃ´ng bá»‹ thanh chá»n nhÃ³m che máº¥t; scrollbar ngang cá»§a thanh nhÃ³m cÅ©ng Ä‘Æ°á»£c áº©n Ä‘á»ƒ giao diá»‡n sáº¡ch hÆ¡n.
- MÃ´ táº£ sáº£n pháº©m trÃªn trang chi tiáº¿t Ä‘Æ°á»£c lÃ m sáº¡ch HTML trÆ°á»›c khi hiá»ƒn thá»‹, trÃ¡nh lá»—i cÃ¡c tháº» nhÆ° `<p>` xuáº¥t hiá»‡n trong "Äáº·c Ä‘iá»ƒm ná»•i báº­t" vÃ  "ThÃ´ng tin chi tiáº¿t".
- Breadcrumb trang chi tiáº¿t sáº£n pháº©m hiá»ƒn thá»‹ theo thá»© tá»± `Trang chá»§ > Danh má»¥c cha > Danh má»¥c con náº¿u cÃ³ > ThÆ°Æ¡ng hiá»‡u > TÃªn sáº£n pháº©m`; Catalog API tráº£ thÃªm `subcategory` Ä‘á»ƒ frontend cÃ³ tÃªn danh má»¥c con.

## Update 2026-06-03 HONOR Magic V5 variant RAM correction

- Sá»­a lá»—i cÃ¡c biáº¿n thá»ƒ (variants) cá»§a `HONOR Magic V5` (`HN-MGV5`) bá»‹ thiáº¿u trÆ°á»ng `ram` (giÃ¡ trá»‹ báº±ng `NULL`/`None`), dáº«n Ä‘áº¿n viá»‡c hiá»ƒn thá»‹ khÃ´ng Ä‘Ãºng/khÃ´ng Ä‘áº§y Ä‘á»§ tÃ¹y chá»n RAM bÃªn cáº¡nh tÃ¹y chá»n ROM/dung lÆ°á»£ng trÃªn trang chi tiáº¿t sáº£n pháº©m.
- Cáº­p nháº­t trá»±c tiáº¿p cá»™t `options` trong báº£ng `products` cá»§a `HN-MGV5` Ä‘á»ƒ thiáº¿t láº­p Ä‘Ãºng há»£p Ä‘á»“ng options (MÃ u sáº¯c, Dung lÆ°á»£ng, RAM).
- Cháº¡y script Python `update_magic_v5_variants.py` cáº­p nháº­t trá»±c tiáº¿p cho toÃ n bá»™ 8 biáº¿n thá»ƒ cá»§a dÃ²ng mÃ¡y nÃ y:
  - Thiáº¿t láº­p cá»™t `ram = '12GB'`, `specs` = `{"storage": "512GB", "ram": "12GB"}` vÃ  `attributes` tÆ°Æ¡ng á»©ng cho cÃ¡c biáº¿n thá»ƒ 512GB.
  - Thiáº¿t láº­p cá»™t `ram = '16GB'`, `specs` = `{"storage": "1TB", "ram": "16GB"}` vÃ  `attributes` tÆ°Æ¡ng á»©ng cho cÃ¡c biáº¿n thá»ƒ 1TB.
- GiÃºp storefront hiá»ƒn thá»‹ chuáº©n xÃ¡c cÃ¡c tÃ¹y chá»n RAM/ROM tÃ¡ch biá»‡t (nhÆ° `12GB / 512GB` vÃ  `16GB / 1TB`) cho ngÆ°á»i dÃ¹ng khi chá»n cáº¥u hÃ¬nh sáº£n pháº©m.

## Update 2026-06-03 HONOR Magic V5 color deletion

- Thá»±c hiá»‡n xÃ³a 2 mÃ u sáº¯c cáº¥u hÃ¬nh "NÃ¢u Lá»¥a" vÃ  "Äen Titanium" khá»i dÃ²ng mÃ¡y `HONOR Magic V5` (`HN-MGV5`) theo yÃªu cáº§u.

## Update 2026-06-03 HONOR Magic V5 image gallery

- ÄÃ£ copy áº£nh ngÆ°á»i dÃ¹ng cung cáº¥p tá»« thÆ° má»¥c `HONOR Magic V5` vÃ o `frontend/public/images/products/honor-magic-v5`.
- áº¢nh Ä‘Æ°á»£c chia theo mÃ u:
  - `white`: Tráº¯ng NgÃ , gá»“m áº£nh Ä‘áº¡i diá»‡n vÃ  11 áº£nh gallery.
  - `gold`: VÃ ng BÃ¬nh Minh, gá»“m áº£nh Ä‘áº¡i diá»‡n vÃ  13 áº£nh gallery.
  - `common`: 5 áº£nh dÃ¹ng chung.
- ThÃªm script `backend/scripts/update_magic_v5_images.py` Ä‘á»ƒ cáº­p nháº­t `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho SKU `HN-MGV5`.
- ÄÃ£ cháº¡y script trÃªn DB local: 2 biáº¿n thá»ƒ Tráº¯ng NgÃ  vÃ  2 biáº¿n thá»ƒ VÃ ng BÃ¬nh Minh Ä‘Ã£ trá» tá»›i Ä‘Ãºng áº£nh theo mÃ u; product dÃ¹ng áº£nh Ä‘áº¡i diá»‡n Tráº¯ng NgÃ  vÃ  gallery chung.
- Quy Æ°á»›c áº£nh HONOR Magic V5: file cÃ³ chá»¯ "áº£nh Ä‘áº¡i diá»‡n" Ä‘Æ°á»£c dÃ¹ng cho `image_url`; cÃ¡c file cÃ²n láº¡i trong thÆ° má»¥c mÃ u lÃ  gallery cá»§a biáº¿n thá»ƒ Ä‘Ã³ vÃ  Ä‘Æ°á»£c lÆ°u vÃ o `product_variants.images`. VÃ¬ váº­y `product_variants.images` khÃ´ng chá»©a láº¡i áº£nh Ä‘áº¡i diá»‡n.
- Trang chi tiáº¿t sáº£n pháº©m nay dá»±ng gallery theo biáº¿n thá»ƒ Ä‘ang chá»n trÆ°á»›c, sau Ä‘Ã³ má»›i ná»‘i áº£nh chung cá»§a sáº£n pháº©m. Khi ngÆ°á»i dÃ¹ng Ä‘á»•i mÃ u/cáº¥u hÃ¬nh, áº£nh chÃ­nh tá»± nháº£y vá» áº£nh Ä‘áº§u cá»§a biáº¿n thá»ƒ active vÃ  khÃ´ng cÃ²n gom áº£nh cá»§a cÃ¡c mÃ u khÃ¡c vÃ o Ä‘áº§u gallery.
- Sá»­a form admin sáº£n pháº©m: khi má»Ÿ chá»‰nh sá»­a, hook `useAdminProductsLogic.ts` nay map `item.images` vÃ o tá»«ng biáº¿n thá»ƒ Ä‘á»ƒ preview "Bá»™ áº£nh biáº¿n thá»ƒ" hiá»ƒn thá»‹ Ä‘Ãºng áº£nh Ä‘ang lÆ°u trong DB vÃ  khÃ´ng bá»‹ máº¥t khi lÆ°u láº¡i.
- Storefront cÃ³ fallback áº£nh biáº¿n thá»ƒ theo mÃ u: náº¿u biáº¿n thá»ƒ active chÆ°a cÃ³ `imageUrl/images`, trang chi tiáº¿t tá»± tÃ¬m biáº¿n thá»ƒ khÃ¡c cÃ¹ng `colorName` cÃ³ áº£nh Ä‘á»ƒ dÃ¹ng, rá»“i váº«n ná»‘i thÃªm áº£nh chung cá»§a sáº£n pháº©m.
- Form admin sáº£n pháº©m cÃ³ thÃªm thao tÃ¡c "Láº¥y áº£nh cÃ¹ng mÃ u" vÃ  menu "Láº¥y áº£nh tá»« biáº¿n thá»ƒ khÃ¡c" Ä‘á»ƒ copy `imageUrl/images` tá»« biáº¿n thá»ƒ Ä‘Ã£ cÃ³ áº£nh sang biáº¿n thá»ƒ má»›i hoáº·c biáº¿n thá»ƒ cÃ¹ng mÃ u, giáº£m viá»‡c nháº­p áº£nh láº·p láº¡i cho tá»«ng RAM/ROM.
- Tháº» sáº£n pháº©m ngoÃ i danh sÃ¡ch chá»‰ dÃ¹ng áº£nh Ä‘áº¡i diá»‡n sáº£n pháº©m vÃ  áº£nh Ä‘áº¡i diá»‡n biáº¿n thá»ƒ; khÃ´ng dÃ¹ng `product.images` vÃ¬ bá»™ áº£nh chung chá»‰ dÃ nh cho gallery bÃªn trong trang chi tiáº¿t sáº£n pháº©m.
- Catalog API chi tiáº¿t sáº£n pháº©m tráº£ thÃªm `images` cho tá»«ng biáº¿n thá»ƒ Ä‘á»ƒ gallery chi tiáº¿t cÃ³ thá»ƒ ná»‘i `variant.imageUrl` + `variant.images` + `product.images`.
- Cáº­p nháº­t trá»±c tiáº¿p trÆ°á»ng `colors` vÃ  `options` (MÃ u sáº¯c) cá»§a sáº£n pháº©m trong báº£ng `products` Ä‘á»ƒ loáº¡i bá» 2 mÃ u nÃ y, chá»‰ giá»¯ láº¡i "Tráº¯ng NgÃ " vÃ  "VÃ ng BÃ¬nh Minh".
- Thá»±c hiá»‡n soft-delete (Ä‘áº·t `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biáº¿n thá»ƒ tÆ°Æ¡ng á»©ng cá»§a 2 mÃ u sáº¯c nÃ y trong báº£ng `product_variants` (gá»“m `HN-MGV5-BK-512GB`, `HN-MGV5-BK-1TB`, `HN-MGV5-BR-512GB`, `HN-MGV5-BR-1TB`), Ä‘áº£m báº£o Ä‘á»“ng bá»™ dá»¯ liá»‡u trÃªn storefront.
- Cáº­p nháº­t táº­p lá»‡nh `backend/scripts/update_magic_v5_variants.py` Ä‘á»ƒ loáº¡i bá» hai mÃ u nÃ y khá»i máº£ng options Ä‘Æ°á»£c cáº¥u hÃ¬nh láº¡i, trÃ¡nh viá»‡c cháº¡y láº¡i script khÃ´i phá»¥c nháº§m cÃ¡c mÃ u Ä‘Ã£ xÃ³a.

## Update 2026-06-03 HONOR 400 5G color deletion & option setup

- Thá»±c hiá»‡n xÃ³a 2 mÃ u sáº¯c cáº¥u hÃ¬nh "XÃ¡m Máº·t TrÄƒng" vÃ  "Äen BÃ³ng ÄÃªm" khá»i dÃ²ng mÃ¡y `HONOR 400 5G` (`HN-400`) theo yÃªu cáº§u.
- Cáº­p nháº­t trá»±c tiáº¿p trÆ°á»ng `colors` vÃ  `options` (MÃ u sáº¯c, Dung lÆ°á»£ng, RAM) cá»§a sáº£n pháº©m `HN-400` trong báº£ng `products` Ä‘á»ƒ loáº¡i bá» 2 mÃ u nÃ y, chá»‰ giá»¯ láº¡i "VÃ ng Sa Máº¡c", Ä‘á»“ng thá»i Ä‘á»“ng bá»™ cáº¥u hÃ¬nh RAM cá»§a phiÃªn báº£n 256GB lÃ  8GB vÃ  512GB lÃ  12GB.
- Thá»±c hiá»‡n soft-delete (Ä‘áº·t `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biáº¿n thá»ƒ tÆ°Æ¡ng á»©ng cá»§a 2 mÃ u sáº¯c nÃ y trong báº£ng `product_variants` (gá»“m `HN-400-GR-256GB`, `HN-400-GR-512GB`, `HN-400-BK-256GB`, `HN-400-BK-512GB`).

## Update 2026-06-03 HONOR 400 series image gallery

- ÄÃ£ copy áº£nh ngÆ°á»i dÃ¹ng cung cáº¥p:
  - `HONOR 400 5G` vÃ o `frontend/public/images/products/honor-400-5g`.
  - `Honor 400 pro` vÃ o `frontend/public/images/products/honor-400-pro`.
- ThÃªm script `backend/scripts/update_honor_400_images.py` Ä‘á»ƒ cáº­p nháº­t áº£nh cho SKU `HN-400` vÃ  `HN-400P`.
- ÄÃ£ cháº¡y script trÃªn DB local:
  - `HN-400`: product dÃ¹ng áº£nh Ä‘áº¡i diá»‡n VÃ ng Sa Máº¡c, cÃ³ 5 áº£nh chung; 2 biáº¿n thá»ƒ VÃ ng Sa Máº¡c cÃ³ áº£nh Ä‘áº¡i diá»‡n vÃ  5 áº£nh gallery biáº¿n thá»ƒ.
  - `HN-400P`: product dÃ¹ng áº£nh Ä‘áº¡i diá»‡n Äen BÃ³ng ÄÃªm; 2 biáº¿n thá»ƒ Äen BÃ³ng ÄÃªm cÃ³ 5 áº£nh gallery, 2 biáº¿n thá»ƒ XÃ¡m Máº·t TrÄƒng cÃ³ 3 áº£nh gallery.
- `HN-400P` mÃ u Xanh Thá»§y Triá»u chÆ°a cÃ³ bá»™ áº£nh Ä‘Æ°á»£c cung cáº¥p nÃªn hiá»‡n váº«n giá»¯ áº£nh placeholder cÅ© cho biáº¿n thá»ƒ mÃ u xanh.
- Äá»“ng bá»™ thÃ´ng tin RAM (`ram = '8GB'` hoáº·c `'12GB'`), specifications (`specs`) vÃ  thuá»™c tÃ­nh (`attributes`) cho táº¥t cáº£ 6 biáº¿n thá»ƒ (bao gá»“m cáº£ cÃ¡c biáº¿n thá»ƒ Ä‘Ã£ soft-deleted) tÆ°Æ¡ng thÃ­ch vá»›i cáº¥u hÃ¬nh 8GB RAM / 256GB ROM vÃ  12GB RAM / 512GB ROM Ä‘á»ƒ dá»¯ liá»‡u Ä‘á»“ng bá»™ nháº¥t quÃ¡n trÃªn storefront.
- Táº¡o script `backend/scripts/update_honor_400_5g.py` Ä‘á»ƒ thá»±c hiá»‡n cáº­p nháº­t nÃ y má»™t cÃ¡ch tá»± Ä‘á»™ng vÃ  lÆ°u trá»¯ dá»± phÃ²ng.

## Update 2026-06-03 Global Laptops & Tablets RAM/Option Standardization

- Thá»±c hiá»‡n rÃ  soÃ¡t toÃ n bá»™ sáº£n pháº©m trÃªn há»‡ thá»‘ng, phÃ¡t hiá»‡n vÃ  sá»­a Ä‘á»•i hoÃ n chá»‰nh lá»—i thiáº¿u cáº¥u hÃ¬nh tÃ¹y chá»n (`options`), thiáº¿u RAM trong biáº¿n thá»ƒ hoáº·c chÆ°a Ä‘á»“ng bá»™ `attributes` vÃ  `specs` cho **20 sáº£n pháº©m** thuá»™c danh má»¥c `laptops` vÃ  `tablets`.
- Táº¡o vÃ  cháº¡y táº­p lá»‡nh [repair_products.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/repair_products.py) tá»± Ä‘á»™ng thá»±c hiá»‡n:
  - Äá»“ng bá»™ hÃ³a máº£ng `options` cá»§a sáº£n pháº©m chá»©a cáº¥u trÃºc tiáº¿ng Viá»‡t chuáº©n: MÃ u sáº¯c, Dung lÆ°á»£ng, RAM.
  - Äiá»n giÃ¡ trá»‹ RAM chuáº©n vÃ o cá»™t `ram` cá»§a biáº¿n thá»ƒ.
  - Äá»“ng bá»™ `specs` vÃ  `attributes` Ä‘áº§y Ä‘á»§ báº±ng tiáº¿ng Viá»‡t tÆ°Æ¡ng á»©ng cho tá»«ng biáº¿n thá»ƒ Ä‘á»ƒ storefront hiá»ƒn thá»‹ tÃ¹y chá»n chÃ­nh xÃ¡c nháº¥t.
- Cháº¡y láº¡i script rÃ  soÃ¡t xÃ¡c nháº­n sá»‘ lÆ°á»£ng sáº£n pháº©m cÃ³ cáº¥u hÃ¬nh lá»—i Ä‘Ã£ giáº£m vá» 0, Ä‘á»“ng thá»i cháº¡y bá»™ kiá»ƒm thá»­ rules cá»§a variant thÃ nh cÃ´ng 100%.

## Update 2026-06-03 Smartphones RAM Separation & Option Standardization

- Thá»±c hiá»‡n chuáº©n hÃ³a cáº¥u hÃ¬nh RAM vÃ  bá»™ nhá»› cho toÃ n bá»™ danh má»¥c Äiá»‡n thoáº¡i (Smartphones) trÃªn há»‡ thá»‘ng.
- Giáº£i quyáº¿t triá»‡t Ä‘á»ƒ lá»—i RAM/ROM gá»™p trong trÆ°á»ng `storage` cá»§a biáº¿n thá»ƒ (dáº¡ng `"RAM 8GB - 256GB"`) báº±ng cÃ¡ch tÃ¡ch thÃ nh:
  - Cá»™t `storage` lÃ  giÃ¡ trá»‹ dung lÆ°á»£ng sáº¡ch (vÃ­ dá»¥: `"256GB"`).
  - Cá»™t `ram` lÃ  má»©c RAM tÆ°Æ¡ng á»©ng (vÃ­ dá»¥: `"8GB"`).
- Äá»‘i vá»›i cÃ¡c dÃ²ng Ä‘iá»‡n thoáº¡i sá»­ dá»¥ng dung lÆ°á»£ng sáº¡ch nhÆ°ng chÆ°a Ä‘Æ°á»£c gÃ¡n RAM á»Ÿ biáº¿n thá»ƒ, tá»± Ä‘á»™ng phÃ¢n tÃ­ch vÃ  gÃ¡n giÃ¡ trá»‹ RAM chuáº©n tÆ°Æ¡ng á»©ng theo thÃ´ng sá»‘ ká»¹ thuáº­t vÃ  phÃ¢n khÃºc giÃ¡ (vÃ­ dá»¥: dÃ²ng S26 Ultra 1TB cÃ³ 16GB RAM, cÃ¡c dÃ²ng khÃ¡c cÃ³ 12GB RAM; Redmi Note 14 Pro+ báº£n 256GB cÃ³ 8GB RAM, báº£n 512GB cÃ³ 12GB RAM).
- Äá»“ng bá»™ máº£ng `options` cáº¥p sáº£n pháº©m vá»›i cáº¥u trÃºc Ä‘áº§y Ä‘á»§ báº±ng tiáº¿ng Viá»‡t (MÃ u sáº¯c, Dung lÆ°á»£ng, RAM).
- Äá»“ng bá»™ `specs` vÃ  `attributes` Ä‘áº§y Ä‘á»§ báº±ng tiáº¿ng Viá»‡t tÆ°Æ¡ng á»©ng cho tá»«ng biáº¿n thá»ƒ. CÃ¡c biáº¿n thá»ƒ khÃ¡c nhau vá» RAM/ROM váº«n giá»¯ nguyÃªn má»©c giÃ¡ chÃªnh lá»‡ch Ä‘Ã£ Ä‘Æ°á»£c thiáº¿t láº­p trÆ°á»›c Ä‘Ã³ trong cÆ¡ sá»Ÿ dá»¯ liá»‡u.
- Táº¡o vÃ  cháº¡y táº­p lá»‡nh [repair_smartphones.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/repair_smartphones.py) tá»± Ä‘á»™ng thá»±c hiá»‡n vÃ  lÆ°u trá»¯ dá»± phÃ²ng.

## Update 2026-06-03 HONOR X9d 5G Color Deletion

- Thá»±c hiá»‡n xÃ³a 2 mÃ u sáº¯c cáº¥u hÃ¬nh "NÃ¢u Äá»" vÃ  "Xanh Rá»«ng" khá»i dÃ²ng mÃ¡y `HONOR X9d 5G` (`HN-X9D`) theo yÃªu cáº§u.
- Cáº­p nháº­t trÆ°á»ng `colors` vÃ  `options` (MÃ u sáº¯c) cá»§a sáº£n pháº©m trong báº£ng `products` Ä‘á»ƒ loáº¡i bá» 2 mÃ u nÃ y, chá»‰ giá»¯ láº¡i "VÃ ng BÃ¬nh Minh" vÃ  "Äen BÃ³ng ÄÃªm".
- Thá»±c hiá»‡n soft-delete (Ä‘áº·t `deleted_at = NOW()`, `status = 'deleted'`, `is_active = FALSE`) cho 4 biáº¿n thá»ƒ tÆ°Æ¡ng á»©ng cá»§a 2 mÃ u sáº¯c nÃ y trong báº£ng `product_variants` (gá»“m `HN-X9D-BR-256GB`, `HN-X9D-BR-512GB`, `HN-X9D-GR-256GB`, `HN-X9D-GR-512GB`), Ä‘áº£m báº£o Ä‘á»“ng bá»™ dá»¯ liá»‡u trÃªn storefront.
- Táº¡o vÃ  cháº¡y táº­p lá»‡nh [delete_honor_x9d_colors.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/scripts/delete_honor_x9d_colors.py) tá»± Ä‘á»™ng thá»±c hiá»‡n vÃ  lÆ°u trá»¯ dá»± phÃ²ng.

## Update 2026-06-03 HONOR X9d 5G image gallery

- ÄÃ£ copy áº£nh ngÆ°á»i dÃ¹ng cung cáº¥p tá»« thÆ° má»¥c `honor x9d` vÃ o `frontend/public/images/products/honor-x9d`.
- áº¢nh Ä‘Æ°á»£c chia theo mÃ u:
  - `black`: Äen BÃ³ng ÄÃªm, gá»“m áº£nh Ä‘áº¡i diá»‡n vÃ  8 áº£nh gallery.
  - `gold`: VÃ ng BÃ¬nh Minh, gá»“m áº£nh Ä‘áº¡i diá»‡n vÃ  11 áº£nh gallery.
  - `common`: 5 áº£nh dÃ¹ng chung cho trang chi tiáº¿t sáº£n pháº©m.
- ThÃªm script `backend/scripts/update_honor_x9d_images.py` Ä‘á»ƒ cáº­p nháº­t `products.image_url`, `products.images`, `product_variants.image_url`, `product_variants.images` cho SKU `HN-X9D`.
- ÄÃ£ cháº¡y script trÃªn DB local: 2 biáº¿n thá»ƒ Äen BÃ³ng ÄÃªm vÃ  2 biáº¿n thá»ƒ VÃ ng BÃ¬nh Minh Ä‘Ã£ trá» Ä‘Ãºng áº£nh theo mÃ u; product dÃ¹ng áº£nh Ä‘áº¡i diá»‡n Äen BÃ³ng ÄÃªm vÃ  gallery chung.
- Quy Æ°á»›c áº£nh HONOR X9d 5G: file cÃ³ chá»¯ "áº£nh Ä‘áº¡i diá»‡n" hoáº·c "áº£nh Ä‘á»‹a diá»‡n" Ä‘Æ°á»£c dÃ¹ng cho `image_url`; cÃ¡c file cÃ²n láº¡i trong thÆ° má»¥c mÃ u lÃ  gallery cá»§a biáº¿n thá»ƒ Ä‘Ã³ vÃ  Ä‘Æ°á»£c lÆ°u vÃ o `product_variants.images`.

## Update 2026-06-04 Admin product simple-product variant rule

- Sáº£n pháº©m khÃ´ng cÃ³ biáº¿n thá»ƒ nay Ä‘Æ°á»£c xem lÃ  sáº£n pháº©m Ä‘Æ¡n giáº£n há»£p lá»‡; giÃ¡, giÃ¡ bÃ¡n, tá»“n kho, áº£nh vÃ  thÃ´ng tin chung láº¥y trá»±c tiáº¿p tá»« báº£ng `products`.
- Chá»‰ sáº£n pháº©m cÃ³ danh sÃ¡ch biáº¿n thá»ƒ má»›i báº¯t buá»™c cÃ³ Ä‘Ãºng má»™t biáº¿n thá»ƒ máº·c Ä‘á»‹nh. Khi danh sÃ¡ch biáº¿n thá»ƒ rá»—ng, backend khÃ´ng tá»± táº¡o biáº¿n thá»ƒ máº·c Ä‘á»‹nh ná»¯a vÃ  cho phÃ©p xÃ³a biáº¿n thá»ƒ cuá»‘i cÃ¹ng báº±ng soft-delete.
- Form admin thÃªm trÆ°á»ng `Tá»“n kho chung`, gá»­i kÃ¨m `brand` vÃ  `category` Ä‘á»ƒ thÆ°Æ¡ng hiá»‡u nháº­p tay khÃ´ng bá»‹ rÆ¡i vá» `KhÃ¡c`, Ä‘á»“ng thá»i khÃ´ng gá»­i cáº¥u hÃ¬nh option/variant khi sáº£n pháº©m khÃ´ng cÃ³ biáº¿n thá»ƒ.
- Khi sá»­a sáº£n pháº©m, frontend map láº¡i Ä‘Ãºng `stockQuantity` vÃ  `salePrice` cá»§a biáº¿n thá»ƒ Ä‘á»ƒ trÃ¡nh máº¥t tá»“n kho hoáº·c giÃ¡ bÃ¡n sau khi lÆ°u.
- Backend chá»‰ Ä‘á»“ng bá»™ giÃ¡/tá»“n kho cha tá»« biáº¿n thá»ƒ khi sáº£n pháº©m tháº­t sá»± cÃ²n biáº¿n thá»ƒ; sáº£n pháº©m Ä‘Æ¡n giáº£n giá»¯ nguyÃªn giÃ¡ vÃ  tá»“n kho chung.
- Sá»­a thÃªm lá»—i lá»c `status=all` trong danh sÃ¡ch admin vÃ  lá»—i nhÃ¢n báº£n sáº£n pháº©m do PostgreSQL khÃ´ng suy luáº­n Ä‘Æ°á»£c kiá»ƒu cá»§a háº­u tá»‘ SKU.
- TÃ¡ch frontend API sáº£n pháº©m: thÃªm `frontend/src/services/productApi.ts` cho cÃ¡c endpoint admin product, chuyá»ƒn `useAdminProductsLogic.ts`, `AdminProductsTab.tsx` vÃ  pháº§n load product trong `useAdminLogic.ts` sang service nÃ y. CÃ¡c endpoint admin product Ä‘Ã£ chuyá»ƒn Ä‘Æ°á»£c gá»¡ khá»i `apiDb`; cÃ¡c endpoint tá»“n kho liÃªn quan sáº£n pháº©m váº«n giá»¯ táº¡m Ä‘á»ƒ tÃ¡ch sang `inventoryApi` sau.
- Sau khi tÃ¡ch thÃªm hook product/variant, `useAdminProductVariants.ts` tráº£ thÃªm `colorOptionName` Ä‘á»ƒ `useAdminProductsLogic.ts` map láº¡i mÃ u biáº¿n thá»ƒ khi má»Ÿ form chá»‰nh sá»­a. Sá»­a import thiáº¿u `youtubeEmbedUrl` vÃ  `ImageWithFallback` á»Ÿ `ProductDetail.tsx` sau khi tÃ¡ch helper media.

## Update 2026-06-05 Frontend feature-first refactor for Products & Brands

- HoÃ n thÃ nh di chuyá»ƒn toÃ n bá»™ module **ThÆ°Æ¡ng hiá»‡u (Brands)** vÃ  **Sáº£n pháº©m (Products)** á»Ÿ Frontend sang cáº¥u trÃºc hÆ°á»›ng tÃ­nh nÄƒng (**Feature-First Architecture**):
  - **Module ThÆ°Æ¡ng hiá»‡u (Brands)**: Di chuyá»ƒn sang `src/features/admin-brands/` gá»“m API (`services/adminBrandsApi.ts`), logic hooks (`hooks/useAdminBrandsLogic.ts`) vÃ  giao diá»‡n (`components/AdminBrandsTab.tsx`).
  - **Module Sáº£n pháº©m (Products)**: Di chuyá»ƒn sang `src/features/admin-products/` gá»“m API (`services/adminProductsApi.ts`), logic hooks (`hooks/useAdminProductsLogic.ts`, `useAdminProductOffers.ts`, `useAdminProductVariants.ts`) vÃ  cÃ¡c UI Components (`components/AdminProductsTab.tsx`, `components/products/ProductAccessoriesSection.tsx`, `ProductFormSection.tsx`, `ProductTableSection.tsx`, `ProductVariantsSection.tsx`).
  - **Cáº­p nháº­t import chung**: Cáº­p nháº­t liÃªn káº¿t import trong cÃ¡c file Ä‘iá»u phá»‘i trung tÃ¢m nhÆ° `apiDb.ts`, `useAdminLogic.ts` vÃ  `AdminDashboardTabContent.tsx`.
  - **Dá»n dáº¹p**: XÃ³a sáº¡ch toÃ n bá»™ cÃ¡c file vÃ  thÆ° má»¥c cÅ© táº¡i cÃ¡c thÆ° má»¥c dÃ¹ng chung `components/admin/tabs/`, `components/admin/hooks/` vÃ  `services/api/`.
  - **XÃ¡c minh**: Cháº¡y thÃ nh cÃ´ng lá»‡nh kiá»ƒm tra kiá»ƒu `npx tsc --noEmit` trÃªn toÃ n bá»™ frontend mÃ  khÃ´ng phÃ¡t sinh báº¥t ká»³ lá»—i compile nÃ o.

## Update 2026-06-05 Refactor Attached Services to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥ vÃ  truy váº¥n SQL cá»§a Dá»‹ch vá»¥ Ä‘i kÃ¨m (Attached Services) ra khá»i `admin_products.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/attached_service.py` Ä‘á»ƒ giá»¯ router sáº¡ch sáº½, dá»… báº£o trÃ¬. CÃ¡c route `/attached-services` chá»‰ lÃ m nhiá»‡m vá»¥ Ä‘iá»u hÆ°á»›ng vÃ  gá»i hÃ m tá»« service.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module Dá»‹ch vá»¥ vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-services/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
  - TÃ¡ch API Attached Services tá»« `apiDb.ts` sang `adminServicesApi.ts` trong thÆ° má»¥c feature má»›i, Ä‘á»“ng thá»i spread gá»™p láº¡i vÃ o `apiDb.ts` Ä‘á»ƒ giá»¯ tÆ°Æ¡ng thÃ­ch ngÆ°á»£c.
  - Di chuyá»ƒn UI tab `AdminServicesTab.tsx` vÃ  custom hook `useAdminServicesLogic.ts` vÃ o feature folder, cáº­p nháº­t cÃ¡c import Ä‘iá»u phá»‘i liÃªn quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`).
- Káº¿t quáº£ kiá»ƒm tra:
  - Frontend: compile thÃ nh cÃ´ng báº±ng `npx tsc --noEmit`.
  - Backend: compile thÃ nh cÃ´ng báº±ng `py_compile`, import `app.main` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng, khÃ´ng xáº£y ra import vÃ²ng láº·p.

## Update 2026-06-05 Refactor Flash Sales to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥, tÃ­nh toÃ¡n giÃ¡ sale vÃ  truy váº¥n SQL cá»§a Flash Sales ra khá»i `admin_flash_sales.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/flash_sale_service.py`. Class pydantic `FlashSalePayload` Ä‘Æ°á»£c di chuyá»ƒn sang `admin_schemas.py` Ä‘á»ƒ thá»‘ng nháº¥t cáº¥u trÃºc schema.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module Flash Sales vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-flash-sales/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
  - TÃ¡ch cÃ¡c API cá»§a Flash Sales tá»« `adminContentApi.ts` sang `adminFlashSalesApi.ts` trong thÆ° má»¥c feature má»›i, Ä‘á»“ng thá»i spread gá»™p láº¡i vÃ o `apiDb.ts` Ä‘á»ƒ giá»¯ tÆ°Æ¡ng thÃ­ch ngÆ°á»£c.
  - Di chuyá»ƒn UI tab `AdminFlashSalesTab.tsx` vÃ  custom hook `useAdminFlashSalesLogic.ts` vÃ o feature folder, cáº­p nháº­t cÃ¡c import Ä‘iá»u phá»‘i liÃªn quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`, `adminContentApi.ts`).
- Káº¿t quáº£ kiá»ƒm tra:
  - Frontend: compile thÃ nh cÃ´ng báº±ng `npx tsc --noEmit`.
  - Backend: compile thÃ nh cÃ´ng báº±ng `py_compile`, import `app.main` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng, khÃ´ng xáº£y ra import vÃ²ng láº·p.

## Update 2026-06-05 Refactor Reviews to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥, kiá»ƒm duyá»‡t vÃ  truy váº¥n SQL cá»§a ÄÃ¡nh giÃ¡ (Reviews) ra khá»i `admin_reviews.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/review_service.py`.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module ÄÃ¡nh giÃ¡ vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-reviews/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
  - TÃ¡ch cÃ¡c API cá»§a ÄÃ¡nh giÃ¡ tá»« `adminContentApi.ts` sang `adminReviewsApi.ts` trong thÆ° má»¥c feature má»›i, Ä‘á»“ng thá»i spread gá»™p láº¡i vÃ o `apiDb.ts` Ä‘á»ƒ giá»¯ tÆ°Æ¡ng thÃ­ch ngÆ°á»£c.
  - Di chuyá»ƒn UI tab `AdminReviewsTab.tsx` vÃ  custom hook `useAdminReviewsLogic.ts` vÃ o feature folder, cáº­p nháº­t cÃ¡c import Ä‘iá»u phá»‘i liÃªn quan (`apiDb.ts`, `useAdminLogic.ts`, `AdminDashboardTabContent.tsx`, `adminContentApi.ts`).
- Káº¿t quáº£ kiá»ƒm tra:
  - Frontend: compile thÃ nh cÃ´ng báº±ng `npx tsc --noEmit`.
  - Backend: compile thÃ nh cÃ´ng báº±ng `py_compile`, import `app.main` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng, khÃ´ng xáº£y ra import vÃ²ng láº·p.
## Update 2026-06-05 Backend Product Repository Split

- TÃ¡ch query danh sÃ¡ch sáº£n pháº©m admin khá»i `app/application/services/product_service.py` sang `app/infrastructure/database/repositories/product_repo.py` qua hÃ m `list_admin_product_rows`.
- Repository hiá»‡n phá»¥ trÃ¡ch lá»c, phÃ¢n trang, Ä‘áº¿m tá»•ng vÃ  gom danh sÃ¡ch biáº¿n thá»ƒ; service chá»‰ cÃ²n gá»i repo rá»“i bá»• sung quan há»‡ bundle, phá»¥ kiá»‡n vÃ  dá»‹ch vá»¥ Ä‘i kÃ¨m trÆ°á»›c khi tráº£ response.
- Káº¿t quáº£ kiá»ƒm tra: compile toÃ n bá»™ backend báº±ng mÃ´i trÆ°á»ng áº£o `.venv` thÃ nh cÃ´ng; import `app.main`, router admin products, product service vÃ  product repository Ä‘á»u hoáº¡t Ä‘á»™ng.

## Update 2026-06-05 Product Service SQL Cleanup

- Má»Ÿ rá»™ng `app/infrastructure/database/repositories/product_repo.py` Ä‘á»ƒ chá»©a cÃ¡c truy váº¥n DB cÃ²n láº¡i cá»§a `product_service.py`: import CSV job, insert product, insert revision, update product, deactivate variants khi sáº£n pháº©m inactive, vÃ  duplicate product/variants/bundles/accessories.
- LÃ m sáº¡ch `app/application/services/product_service.py`: bá» SQL trá»±c tiáº¿p (`session.execute`, `session.scalar`, `text`) vÃ  chuyá»ƒn import schema sang `app.api.v1.schemas.admin`.
- Giá»¯ service á»Ÿ vai trÃ² xá»­ lÃ½ nghiá»‡p vá»¥: validate media, chuáº©n hÃ³a options/specs/sales config, kiá»ƒm tra category migration, gá»i variant service, Ä‘á»“ng bá»™ quan há»‡ sáº£n pháº©m, audit vÃ  commit.
- Sá»­a láº¡i thÃ´ng bÃ¡o lá»—i tiáº¿ng Viá»‡t cho luá»“ng import CSV.
- Káº¿t quáº£ kiá»ƒm tra: compile toÃ n bá»™ backend báº±ng `.venv` thÃ nh cÃ´ng; import `app.main`, admin products router, product service vÃ  product repository thÃ nh cÃ´ng.

## Update 2026-06-05 Product Approval Repository Split

- TÃ¡ch truy váº¥n vÃ  thao tÃ¡c dá»¯ liá»‡u cá»§a luá»“ng duyá»‡t sáº£n pháº©m khá»i `app/application/services/product_approval_service.py` sang `app/infrastructure/database/repositories/product_approval_repo.py`.
- `product_approval_service.py` hiá»‡n giá»¯ vai trÃ² Ä‘iá»u phá»‘i nghiá»‡p vá»¥: submit, approve, bulk approve/archive/delete, archive, deactivate; Ä‘á»“ng thá»i giá»¯ bÆ°á»›c Ä‘á»“ng bá»™ giÃ¡ sáº£n pháº©m cha khi duyá»‡t/xuáº¥t báº£n revision.
- Repository má»›i phá»¥ trÃ¡ch cÃ¡c thao tÃ¡c DB nháº¡y cáº£m cá»§a approval: merge revision variants, cáº­p nháº­t tráº¡ng thÃ¡i sáº£n pháº©m, sao chÃ©p bundle/accessory tá»« revision, archive/deactivate vÃ  kiá»ƒm tra category migration.
- Káº¿t quáº£ kiá»ƒm tra: compile toÃ n bá»™ backend báº±ng `.venv` thÃ nh cÃ´ng; import `app.main`, router admin product approvals, product approval service vÃ  product approval repository thÃ nh cÃ´ng.


## Update 2026-06-05 Admin Overview Repository Split

- TÃ¡ch truy váº¥n dashboard tá»•ng quan admin khá»i `app/application/services/overview_service.py` sang `app/infrastructure/database/repositories/overview_repo.py`.
- Service hiá»‡n chá»‰ cÃ²n gom dá»¯ liá»‡u tá»« repo vÃ  Ä‘á»‹nh dáº¡ng response cho router `admin_overview.py`.
- Káº¿t quáº£ kiá»ƒm tra: compile backend thÃ nh cÃ´ng; import `app.main`, admin overview router, overview service vÃ  overview repository thÃ nh cÃ´ng.


## Update 2026-06-05 Attached Service Repository Split

- TÃ¡ch truy váº¥n vÃ  thao tÃ¡c DB cá»§a dá»‹ch vá»¥ Ä‘i kÃ¨m khá»i `app/application/services/attached_service.py` sang `app/infrastructure/database/repositories/attached_service_repo.py`.
- Service hiá»‡n chá»‰ cÃ²n chuáº©n hÃ³a giÃ¡ theo loáº¡i dá»‹ch vá»¥, gá»i repository, commit vÃ  tráº£ response cho router admin products.
- Káº¿t quáº£ kiá»ƒm tra: compile backend thÃ nh cÃ´ng; import `app.main`, admin products router, attached service vÃ  attached service repository thÃ nh cÃ´ng.

## Update 2026-06-06 product delete rule

- `DELETE /admin/products/{id}` khÃ´ng cÃ²n tá»± chuyá»ƒn sáº£n pháº©m khÃ´ng rÃ ng buá»™c sang `ARCHIVED`.
- Náº¿u sáº£n pháº©m cÃ³ Ä‘Æ¡n hÃ ng hoáº·c Ä‘Ã¡nh giÃ¡, thao tÃ¡c xÃ³a sáº½ chuyá»ƒn sang `INACTIVE` Ä‘á»ƒ giá»¯ lá»‹ch sá»­ bÃ¡n hÃ ng vÃ  Ä‘Ã¡nh giÃ¡.
- Náº¿u sáº£n pháº©m chÆ°a cÃ³ Ä‘Æ¡n hÃ ng/Ä‘Ã¡nh giÃ¡ nhÆ°ng Ä‘Ã£ cÃ³ dá»¯ liá»‡u nháº­p kho tháº­t, backend tráº£ `409` vÃ  yÃªu cáº§u áº©n sáº£n pháº©m thay vÃ¬ xÃ³a. Dá»¯ liá»‡u nháº­p kho tháº­t Ä‘Æ°á»£c xÃ¡c Ä‘á»‹nh báº±ng `inventory_adjustment_logs.transaction_type = 'RECEIPT'` vá»›i `delta > 0`, hoáº·c `inventory_transactions` loáº¡i `IN` tá»« chá»©ng tá»« `INBOUND`.
- Náº¿u sáº£n pháº©m chÆ°a cÃ³ Ä‘Æ¡n hÃ ng, chÆ°a cÃ³ Ä‘Ã¡nh giÃ¡ vÃ  chÆ°a cÃ³ dá»¯ liá»‡u nháº­p kho tháº­t, backend xÃ³a cá»©ng báº£n ghi sáº£n pháº©m; cÃ¡c quan há»‡ bundle/accessory/service liÃªn quan Ä‘Æ°á»£c dá»n trÆ°á»›c khi xÃ³a. Tá»“n kho seed/import náº±m trong `stock_quantity` nhÆ°ng khÃ´ng cÃ³ log nháº­p kho tháº­t khÃ´ng cháº·n xÃ³a.

## Update 2026-06-06 discontinued product status

- ThÃªm tráº¡ng thÃ¡i sáº£n pháº©m `DISCONTINUED` / `Ngá»«ng kinh doanh` vÃ o constraint DB, helper chuáº©n hÃ³a tráº¡ng thÃ¡i vÃ  lá»±a chá»n tráº¡ng thÃ¡i trong admin.
- Storefront khÃ´ng Ä‘Æ°a sáº£n pháº©m `DISCONTINUED` vÃ o danh sÃ¡ch máº·c Ä‘á»‹nh/trang chá»§. Khi ngÆ°á»i dÃ¹ng tÃ¬m kiáº¿m báº±ng tá»« khÃ³a hoáº·c truy cáº­p trá»±c tiáº¿p trang chi tiáº¿t, sáº£n pháº©m váº«n hiá»ƒn thá»‹ thÃ´ng tin tham kháº£o.
- Trang chi tiáº¿t sáº£n pháº©m `DISCONTINUED` khÃ´ng hiá»ƒn thá»‹ giÃ¡ bÃ¡n, flash sale, gÃ³i mua kÃ¨m, nÃºt mua ngay, thÃªm giá» hÃ ng, sá»‘ lÆ°á»£ng hoáº·c tráº£ gÃ³p. UI chá»‰ hiá»ƒn thá»‹ nhÃ£n `Ngá»«ng kinh doanh` vÃ  thÃ´ng tin sáº£n pháº©m.

## Update 2026-06-06 Delete OPPO Find X8 White Variant

- Thá»±c hiá»‡n xÃ³a biáº¿n thá»ƒ "Tráº¯ng Tinh TÃº" cá»§a sáº£n pháº©m OPPO Find X8 (ID: `f7712c7b-7390-4a07-972b-fd5f1f7657ba`) trong cÆ¡ sá»Ÿ dá»¯ liá»‡u:
  - Cáº­p nháº­t trÆ°á»ng `colors` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Tráº¯ng Tinh TÃº".
  - Cáº­p nháº­t trÆ°á»ng `options` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Tráº¯ng Tinh TÃº" ra khá»i danh sÃ¡ch giÃ¡ trá»‹ cá»§a tÃ¹y chá»n "MÃ u sáº¯c".
  - Soft-delete cÃ¡c biáº¿n thá»ƒ mÃ u tráº¯ng (`OP-FX8-WH-256GB` vÃ  `OP-FX8-WH-512GB`) trong báº£ng `product_variants` báº±ng cÃ¡ch cáº­p nháº­t `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` vÃ  ghi nháº­n thá»i gian `deleted_at`.
  - Thiáº¿t láº­p biáº¿n thá»ƒ active Ä‘áº§u tiÃªn (`OP-FX8-BK-256GB`) lÃ m biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = TRUE`) vÃ  cáº­p nháº­t SKU cá»§a sáº£n pháº©m cha Ä‘á»ƒ Ä‘Ã¡p á»©ng yÃªu cáº§u nghiá»‡p vá»¥ vá» biáº¿n thá»ƒ máº·c Ä‘á»‹nh duy nháº¥t.

## Update 2026-06-06 Delete OPPO Find N6 Black Variant

- Thá»±c hiá»‡n xÃ³a biáº¿n thá»ƒ "Äen SÃ¢u Tháº³m" cá»§a sáº£n pháº©m OPPO Find N6 (ID: `8d6c4002-f89d-4b1e-b898-65e5508ce38d`) trong cÆ¡ sá»Ÿ dá»¯ liá»‡u:
  - Cáº­p nháº­t trÆ°á»ng `colors` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Äen SÃ¢u Tháº³m".
  - Cáº­p nháº­t trÆ°á»ng `options` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Äen SÃ¢u Tháº³m" ra khá»i danh sÃ¡ch giÃ¡ trá»‹ cá»§a tÃ¹y chá»n "MÃ u sáº¯c".
  - Soft-delete cÃ¡c biáº¿n thá»ƒ mÃ u Ä‘en (`OP-FN6-BK-512GB` vÃ  `OP-FN6-BK-1TB`) trong báº£ng `product_variants` báº±ng cÃ¡ch cáº­p nháº­t `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` vÃ  ghi nháº­n thá»i gian `deleted_at`.
  - Thiáº¿t láº­p biáº¿n thá»ƒ active Ä‘áº§u tiÃªn (`OP-FN6-OR-1TB`) lÃ m biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = TRUE`) vÃ  cáº­p nháº­t SKU cá»§a sáº£n pháº©m cha Ä‘á»ƒ Ä‘Ã¡p á»©ng yÃªu cáº§u nghiá»‡p vá»¥ vá» biáº¿n thá»ƒ máº·c Ä‘á»‹nh duy nháº¥t.

## Update 2026-06-06 Modify OPPO Reno15 F 5G Variants

- Thá»±c hiá»‡n cáº­p nháº­t cÃ¡c biáº¿n thá»ƒ cá»§a sáº£n pháº©m OPPO Reno15 F 5G (ID: `664a9354-89f1-4275-8a74-20ee67607d3f`) trong cÆ¡ sá»Ÿ dá»¯ liá»‡u:
  - Cáº­p nháº­t trÆ°á»ng `colors` vÃ  `options` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» hai mÃ u "Xanh Cá»±c Quang" vÃ  "Tráº¯ng Tinh KhÃ´i", Ä‘á»“ng thá»i thÃªm hai mÃ u má»›i "Xanh Nháº¡t" (mÃ£ mÃ u: `#add8e6`) vÃ  "Xanh DÆ°Æ¡ng" (mÃ£ mÃ u: `#2196f3`).
  - Soft-delete cÃ¡c biáº¿n thá»ƒ mÃ u cÅ©: `OP-RN15F-BL-8-256`, `OP-RN15F-BL-12-256` (Xanh Cá»±c Quang) vÃ  `OP-RN15F-WH-8-256`, `OP-RN15F-WH-12-256` (Tráº¯ng Tinh KhÃ´i) trong báº£ng `product_variants`.
  - Táº¡o má»›i 4 biáº¿n thá»ƒ cho 2 mÃ u má»›i:
    - MÃ u Xanh Nháº¡t: `OP-RN15F-LB-8-256` (8GB RAM - 256GB ROM, giÃ¡ 8,490,000Ä‘) vÃ  `OP-RN15F-LB-12-256` (12GB RAM - 256GB ROM, giÃ¡ 9,490,000Ä‘).
    - MÃ u Xanh DÆ°Æ¡ng: `OP-RN15F-B-8-256` (8GB RAM - 256GB ROM, giÃ¡ 8,490,000Ä‘) vÃ  `OP-RN15F-B-12-256` (12GB RAM - 256GB ROM, giÃ¡ 9,490,000Ä‘).
  - Thiáº¿t láº­p biáº¿n thá»ƒ `OP-RN15F-PK-8-256` (Há»“ng Rá»±c Rá»¡) lÃ m biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = TRUE`) vÃ  cáº­p nháº­t SKU cá»§a sáº£n pháº©m cha.

## Update 2026-06-06 Delete OPPO Reno15 5G Aurora Variant

- Thá»±c hiá»‡n xÃ³a biáº¿n thá»ƒ "Xanh Cá»±c Quang" cá»§a sáº£n pháº©m OPPO Reno15 5G (ID: `1bcab5a6-c021-4976-83d8-6fd358a36192`) trong cÆ¡ sá»Ÿ dá»¯ liá»‡u:
  - Cáº­p nháº­t trÆ°á»ng `colors` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Xanh Cá»±c Quang".
  - Cáº­p nháº­t trÆ°á»ng `options` cá»§a sáº£n pháº©m Ä‘á»ƒ loáº¡i bá» mÃ u "Xanh Cá»±c Quang" ra khá»i danh sÃ¡ch giÃ¡ trá»‹ cá»§a tÃ¹y chá»n "MÃ u sáº¯c".
  - Soft-delete cÃ¡c biáº¿n thá»ƒ mÃ u xanh cá»±c quang (`OP-RN15-AB-256GB` vÃ  `OP-RN15-AB-512GB`) trong báº£ng `product_variants` báº±ng cÃ¡ch cáº­p nháº­t `is_active = FALSE`, `status = 'deleted'`, `is_default = FALSE` vÃ  ghi nháº­n thá»i gian `deleted_at`.
  - Thiáº¿t láº­p biáº¿n thá»ƒ active Ä‘áº§u tiÃªn (`OP-RN15-AW-256GB`) lÃ m biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = TRUE`) vÃ  cáº­p nháº­t SKU cá»§a sáº£n pháº©m cha Ä‘á»ƒ Ä‘Ã¡p á»©ng yÃªu cáº§u nghiá»‡p vá»¥ vá» biáº¿n thá»ƒ máº·c Ä‘á»‹nh duy nháº¥t.

## Update 2026-06-06 Add OPPO Find N3 Variants

- Thá»±c hiá»‡n bá»• sung cÃ¡c biáº¿n thá»ƒ "Äen" vÃ  "VÃ ng" cho sáº£n pháº©m OPPO Find N3 (ID: `5f0c3535-c5ce-4cac-8321-a32ac43aefd2`) trong cÆ¡ sá»Ÿ dá»¯ liá»‡u:
  - Cáº­p nháº­t trÆ°á»ng `colors` cá»§a sáº£n pháº©m, thÃªm hai mÃ u "Äen" (mÃ£ mÃ u: `#1a1a1c`) vÃ  "VÃ ng" (mÃ£ mÃ u: `#e5c158`).
  - Thiáº¿t láº­p cáº¥u trÃºc `options` cho sáº£n pháº©m gá»“m cÃ³: MÃ u sáº¯c ("Äen", "VÃ ng"), Dung lÆ°á»£ng ("512GB"), vÃ  RAM ("16GB").
  - Táº¡o má»›i 2 biáº¿n thá»ƒ trong báº£ng `product_variants`:
    - Biáº¿n thá»ƒ Äen: SKU `OPPFN3-BK-512GB` (16GB RAM - 512GB ROM, giÃ¡ 39,990,000Ä‘, giÃ¡ bÃ¡n 34,990,000Ä‘, tá»“n kho 3), Ä‘áº·t lÃ m biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = TRUE`).
    - Biáº¿n thá»ƒ VÃ ng: SKU `OPPFN3-GD-512GB` (16GB RAM - 512GB ROM, giÃ¡ 39,990,000Ä‘, giÃ¡ bÃ¡n 34,990,000Ä‘, tá»“n kho 3).
  - Cáº­p nháº­t SKU sáº£n pháº©m cha thÃ nh `OPPFN3-BK-512GB` theo biáº¿n thá»ƒ máº·c Ä‘á»‹nh.

## Update 2026-06-06 Catalog Images Display Main Representative Image

- Thay Ä‘á»•i cÃ¡ch láº¥y áº£nh Ä‘áº¡i diá»‡n cá»§a sáº£n pháº©m hiá»ƒn thá»‹ trÃªn trang thÆ° viá»‡n áº£nh `/images` (API `list_product_images` trong `catalog_utils.py`):
  - GiÃ¡ trá»‹ trÆ°á»ng `mainUrl` tráº£ vá» cho Product Card nay Æ°u tiÃªn láº¥y áº£nh Ä‘áº¡i diá»‡n chung cá»§a sáº£n pháº©m (`product.imageUrl`) náº¿u nÃ³ lÃ  áº£nh há»£p lá»‡ (khÃ´ng pháº£i placeholder).
  - Chá»‰ khi sáº£n pháº©m khÃ´ng cÃ³ áº£nh Ä‘áº¡i diá»‡n há»£p lá»‡ thÃ¬ má»›i fallback vá» áº£nh Ä‘áº§u tiÃªn trong bá»™ sÆ°u táº­p gallery (`image_entries[0]["url"]`).
  - GiÃºp hiá»ƒn thá»‹ Ä‘Ãºng áº£nh Ä‘áº¡i diá»‡n Ä‘á»“ng bá»™ cá»§a sáº£n pháº©m á»Ÿ trang ngoÃ i danh sÃ¡ch áº£nh, trÃ¡nh viá»‡c láº¥y ngáº«u nhiÃªn áº£nh chi tiáº¿t hoáº·c áº£nh gÃ³c cáº¡nh tá»« gallery.
