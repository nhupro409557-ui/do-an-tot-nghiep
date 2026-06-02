# Product Management Notes

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
