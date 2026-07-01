# Inventory Management Notes

## Cập nhật 2026-06-29 - Báo cáo tuổi tồn kho

- Bổ sung API `GET /admin/inventory/reports/aging` để tổng hợp các lô `inventory_lots` còn tồn theo nhóm tuổi `0_30`, `31_90`, `91_180`, `180_PLUS`.
- Báo cáo dùng `received_at`, `remaining_quantity`, `unit_cost`, sản phẩm/biến thể và kệ để trả cả bucket tổng quan lẫn danh sách chi tiết theo sản phẩm, biến thể, vị trí.
- Frontend admin tồn kho thêm tab `Tuổi tồn kho`, bộ lọc nhóm tuổi và bảng giá trị vốn còn lại theo từng lô tồn.
- Cần dùng báo cáo này để ưu tiên FIFO, xả hàng tồn lâu, hoặc đánh dấu kế hoạch khuyến mãi/điều chuyển trước khi hàng quá tuổi.

## Cập nhật 2026-06-29 - POS xuất đúng IMEI/serial đã quét

- Bổ sung payload POS cho từng dòng hàng gồm `imeis` và `serial_numbers`; backend truyền danh sách này từ `CreateOrderUseCase` sang `_ship_order_items`.
- Khi POS bán sản phẩm có IMEI/serial đang `IN_STOCK`, backend bắt buộc số mã đã quét khớp số lượng bán, khóa đúng mã theo sản phẩm/biến thể/vị trí kệ và cập nhật chính các mã đó sang `SOLD`.
- Nếu sản phẩm không có mã định danh trong kho, luồng POS vẫn fallback trừ kho FIFO như trước để không ảnh hưởng hàng không quản lý IMEI/serial.
- Frontend POS thêm ô quét/dán IMEI và serial theo từng dòng giỏ hàng; mã được tách theo dòng, khoảng trắng, dấu phẩy hoặc dấu chấm phẩy trước khi gửi API.
- Verification: `py_compile` backend pass cho các use case commerce liên quan; frontend `npm run lint` pass.

## Cập nhật 2026-06-29 - Bổ sung test outbound/picking admin

- Bổ sung test API admin cho luồng xuất kho: nhập kho test, tạo đơn COD có product/variant thật, admin chuyển đơn sang `PROCESSING`, sinh phiếu `OUTBOUND`, auto-suggest picking, hoàn tất phiếu xuất, kiểm tra đơn sang `SHIPPED`.
- Test assert trực tiếp `inventory_documents`, `inventory_levels`, `products`, `product_variants` để xác nhận tồn kho variant giảm từ 5 xuống 3 và không còn database thật bị tác động.
- Sửa lỗi consume lot cho variant: `inventory_lots` của variant lưu `product_id = NULL`, nên truy vấn consume lot phải match theo `variant_id`; sản phẩm gốc mới match theo `product_id`.
- Sửa thứ tự post outbound: consume `inventory_lots` trước khi deduct `inventory_levels` để tránh kiểm tra lot sau khi level đã bị trừ trong cùng transaction.
- Verification: `pytest backend/tests/test_12_admin_inventory_outbound_flow.py -q` pass.

## Cập nhật 2026-06-29 - Bổ sung repository gợi ý và trừ kho xuất hàng

- Bổ sung `commerce_repo.deduct_inventory_levels_fifo` để luồng giao hàng tự động trừ tồn khả dụng theo kệ, ưu tiên kệ có lô nhập cũ nhất rồi mới đến `inventory_levels.updated_at`.
- Bổ sung `inventory_repo.list_identifier_issue_candidates` để gợi ý IMEI/Serial đang `IN_STOCK`, ưu tiên cặp IMEI/Serial hợp lệ để không đếm trùng một thiết bị thành nhiều đơn vị.
- Bổ sung `inventory_repo.list_level_issue_candidates` để chi tiết phiếu xuất kho và màn gợi ý xuất hàng lấy danh sách kệ active còn tồn khả dụng.
- Verification: `py_compile` pass cho 3 repository vừa sửa; import facade xác nhận 3 hàm đã export; script quét 821 lượt gọi `*_repo.<hàm>` trong backend trả `missing=0`.

## Cập nhật 2026-06-29 - Sửa lỗi API IMEI/Serial tồn kho

- Bổ sung các hàm repository còn thiếu cho luồng `GET /admin/inventory/identifiers` và `GET /admin/inventory/identifier-edit-requests`, gồm danh sách IMEI, serial, yêu cầu chỉnh sửa pending và các thao tác tạo/duyệt/hủy yêu cầu.
- Query lọc `product_id`, `variant_id`, `status` được cast kiểu rõ ràng để tránh lỗi asyncpg `could not determine data type of parameter` khi tham số có thể rỗng.
- Frontend `openIdentifierModal` bắt lỗi API và hiển thị thông báo gọn, không để rơi `Uncaught (in promise)` khi backend trả lỗi.
- Verification: backend `py_compile` pass; frontend `npm run lint` pass; gọi trực tiếp service với product/variant trong console lỗi trả dữ liệu hợp lệ, không còn exception.

## Cập nhật 2026-06-29 - Tinh gọn bảng tồn kho

- Bỏ cột `Giá bán` khỏi bảng tồn kho admin, chỉ giữ `Giá vốn BQ` cho màn quản lý tồn.
- Cột `IMEI / Serial` không còn hiển thị dòng tóm tắt dài kiểu `IMEI: chưa có IMEI chính...`; nếu sản phẩm có quản lý mã định danh thì chỉ hiện nút `Xem mã`, không có thì hiện `-`.
- Nút `Xem danh sách kệ` đổi sang icon danh sách để dễ nhận biết hơn khi thao tác xem kệ.
- Verification: frontend `npm run lint` pass.

## Cập nhật 2026-06-29 - Đổi ô kệ thành nút xem danh sách

- Cột `Kệ` trong bảng tồn kho chỉ hiển thị nút `Xem danh sách kệ` kèm badge số kệ, không hiển thị mã kệ/tên kệ/tổng số lượng trực tiếp ngoài bảng.
- Chi tiết mã kệ, tên kệ, dãy và số lượng vẫn nằm trong modal `Danh sách kệ` khi bấm nút.
- Verification: frontend `npm run lint` pass.

## Cập nhật 2026-06-29 - Hiển thị dãy trong modal danh sách kệ

- Modal `Danh sách kệ` của bảng tồn kho sẽ hiển thị cột `Dãy` bằng dữ liệu `zone` nếu API có trả về.
- Nếu `zone` trống, frontend tự suy ra dãy từ tên kệ dạng `Dãy A - Kệ 02 - Ô 04` hoặc từ mã kệ dạng `A-02-04`, nên không còn hiển thị `-` khi tên/mã kệ đã đủ thông tin.
- Verification: frontend `npm run lint` pass.

## Cập nhật 2026-06-29 - Thu gọn cột kệ trong bảng tồn kho

- Cột `Kệ` trong bảng tồn kho admin không còn hiển thị toàn bộ danh sách kệ trực tiếp trong ô, tránh làm vỡ chiều rộng cột khi mã kệ/tên kệ dài.
- Mỗi dòng tồn kho có kệ sẽ hiển thị nút tóm tắt số kệ, kệ đầu tiên và tổng số lượng; bấm vào nút để mở modal `Danh sách kệ` xem mã kệ, tên kệ, dãy và số lượng trên từng kệ.
- Dòng có tồn nhưng chưa phân bổ kệ vẫn hiển thị trạng thái `Chưa phân bổ kệ`; dòng không có tồn hiển thị `-`.
- Verification: frontend `npm run lint` pass; kiểm tra browser tại `http://localhost:3000` trả HTTP 200, có nội dung, không có Vite overlay và không có console error.

## Cập nhật 2026-06-29 - Giảm số lượng phiếu NK20260624-BO-SUNG-TON-MOI theo nhóm hàng

- Thêm script bảo trì `backend/scripts/reduce_receipt_quantities_by_group.py` để giảm số lượng nhập của phiếu `NK20260624-BO-SUNG-TON-MOI` sau khi đã sắp kệ.
- Quy tắc đã áp dụng: sản phẩm thuộc `Phụ kiện công nghệ` đặt 45 cái/biến thể; các nhóm còn lại đặt 12 cái/biến thể.
- Script cập nhật đồng bộ dòng phiếu, lô nhập, tồn kệ, `product_variants.stock_quantity`, tổng tồn sản phẩm, log nhập và giữ giá nhập bằng 20% giá bán hiện hành.
- Verification: phiếu còn 72 dòng với tổng 2.019 sản phẩm; phụ kiện công nghệ 35 dòng/1.575 sản phẩm, nhóm còn lại 37 dòng/444 sản phẩm; số lượng dòng phiếu, lô, tồn kệ và tồn biến thể đều khớp; tổng tồn kệ toàn hệ thống còn 6.489.

## Cập nhật 2026-06-29 - Sắp kệ và giá nhập cho phiếu NK20260624-BO-SUNG-TON-MOI

- Thêm script bảo trì `backend/scripts/arrange_receipt_new_stock_shelves.py` để xử lý phiếu nhập bổ sung tồn mới đã hoàn tất.
- Script đặt `unit_cost` của dòng phiếu, lô nhập, log nhập và `average_unit_cost` của tồn kệ bằng 20% giá bán hiện hành của biến thể/sản phẩm.
- Dữ liệu tồn của 72 dòng phiếu được chuyển khỏi kệ ảo `MAIN` sang kệ vật lý: phụ kiện vào Dãy A, camera/máy ảnh vào Dãy B, nhóm còn lại vào Dãy C; mỗi dòng chọn ô đang nhẹ tải nhất trong dãy tương ứng.
- Số lượng nhập của từng dòng được đối soát theo tồn biến thể hiện có, tổng phiếu giữ nguyên 5.160 sản phẩm và không cộng tồn thêm lần nữa.
- Verification: script chạy thành công, tổng `inventory_levels` toàn hệ thống giữ nguyên 9.630, phiếu còn 72 dòng/5.160 sản phẩm, không còn dòng thiếu giá vốn, tồn của các biến thể phiếu tại `MAIN` còn 0.

## Cập nhật 2026-06-29 - Hiển thị giá bán và kệ trong tồn kho

- API `GET /admin/inventory/levels` trả thêm giá bán hiện hành theo sản phẩm/biến thể, ưu tiên giá khuyến mãi nếu có.
- Bảng quản lý tồn kho thêm cột `Giá bán` và `Kệ`; mỗi kệ hiển thị mã, tên và số lượng tồn trên kệ. Dòng có tồn nhưng chưa có bản ghi kệ sẽ hiển thị `Chưa phân bổ kệ`.
- File export CSV tồn kho cũng có thêm `displayPrice` và `locations`.
- Verification: `python -m py_compile backend\app\infrastructure\database\repositories\inventory\overview.py backend\app\application\services\inventory\common.py backend\app\application\services\inventory\overview.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-06-29 - Lấy địa chỉ cửa hàng khi xuất phiếu nhập kho

- Luồng xuất phiếu nhập kho PDF/DOCX đọc cấu hình `store_info` và truyền tên, mô tả, địa chỉ, hotline cửa hàng vào renderer chứng từ.
- Header phiếu nhập kho không còn để trống dòng địa chỉ cửa hàng khi đã cấu hình thông tin cửa hàng; vẫn giữ fallback bằng dấu chấm nếu chưa có dữ liệu.
- Verification: `python -m py_compile backend\app\application\services\inventory\documents.py backend\app\application\services\document_export_service.py` pass; gọi trực tiếp renderer bằng `backend\.venv\Scripts\python.exe` tạo được PDF và DOCX với địa chỉ cửa hàng mẫu.

## C?p nh?t 2026-06-28 - T?i ?u th?m lookup phi?u nh?p kho

- D?ng danh s?ch bi?n th? nh?p kho kh? d?ng b?ng m?t l??t duy?t v? t?o `Map` bi?n th? theo s?n ph?m tr??c khi validate d?ng phi?u nh?p.
- Kh?ng ??i quy t?c ch?n s?n ph?m/bi?n th? ng?ng ho?t ??ng, payload phi?u nh?p ho?c lu?ng ghi s? kho.
- Verification: frontend `npm run lint` pass; React Doctor full scan c?n 288 c?nh b?o (Performance 35).

## Cập nhật 2026-06-28 - Giảm cảnh báo React Doctor cho luồng kho

- Tối ưu các đoạn dựng tùy chọn vị trí kho, danh sách dòng kiểm kê, payload chứng từ, danh sách IMEI/serial và phát hiện trùng mã bằng vòng lặp một lượt hoặc `Set`.
- Giữ nguyên quy tắc nghiệp vụ nhập kho, kiểm kê, chứng từ và policy IMEI/serial; thay đổi chỉ giảm số lần duyệt mảng trong frontend.
- Verification: frontend `npm run lint` pass; React Doctor full scan còn 309 cảnh báo, Performance còn 55.

## Cáº­p nháº­t 2026-06-28 - Hoist helper React Doctor trong mÃ n kho

- ÄÆ°a cÃ¡c helper thuáº§n trong xuáº¥t kho, phiáº¿u nháº­p vÃ  kiá»ƒm kÃª ra module scope: tráº¡ng thÃ¡i dÃ²ng xuáº¥t, danh sÃ¡ch ká»‡ kháº£ dá»¥ng, badge tráº¡ng thÃ¡i, chuáº©n hÃ³a IMEI/serial, tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh, táº¡o mÃ£ kiá»ƒm kÃª/Ä‘iá»u chá»‰nh vÃ  dá»±ng dÃ²ng kiá»ƒm kÃª.
- ÄÆ°a helper kiá»ƒm tra biáº¿n thá»ƒ/sáº£n pháº©m nháº­p kho ra module scope trong hook inventory; cÃ¡c helper phá»¥ thuá»™c `categories` nhÆ° policy IMEI/serial váº«n giá»¯ trong hook Ä‘á»ƒ trÃ¡nh Ä‘á»•i hÃ nh vi.
- ÄÆ°a helper Ä‘á»‹nh dáº¡ng dung lÆ°á»£ng ká»‡ vÃ  tÃªn biáº¿n thá»ƒ trong `InventoryDialog` ra module scope; payload nháº­p kho vÃ  xá»­ lÃ½ `_clientKey` khÃ´ng Ä‘á»•i.
- Verification: frontend `npm run lint` pass; React Doctor full scan cÃ²n 353 cáº£nh bÃ¡o, `prefer-module-scope-pure-function` chá»‰ cÃ²n 2 cáº£nh bÃ¡o ngoÃ i nhÃ³m kho.

## Cáº­p nháº­t 2026-06-28 - á»”n Ä‘á»‹nh key hiá»ƒn thá»‹ mÃ£ Ä‘á»‹nh danh

- Danh sÃ¡ch IMEI vÃ  serial trÃªn phÃ¢n bá»• xuáº¥t kho dÃ¹ng chÃ­nh mÃ£ Ä‘á»‹nh danh lÃ m React key thay cho vá»‹ trÃ­ trong máº£ng.
- BiÃªn báº£n sai lá»‡ch á»Ÿ chi tiáº¿t phiáº¿u nháº­p Æ°u tiÃªn ID, sau Ä‘Ã³ dÃ¹ng tá»• há»£p ná»™i dung nghiá»‡p vá»¥ lÃ m key á»•n Ä‘á»‹nh.
- Chá»©ng tá»« vÃ  sai lá»‡ch trong form phiáº¿u nháº­p Ä‘Æ°á»£c gáº¯n `_clientKey` khi thÃªm, upload hoáº·c hydrate phiáº¿u sá»­a; payload API váº«n Ä‘Æ°á»£c dá»±ng theo whitelist nÃªn khÃ´ng gá»­i trÆ°á»ng nÃ y sang backend.
- XÃ³a state `detailLoading` khÃ´ng Ä‘Æ°á»£c Ä‘á»c vÃ  Ä‘Æ°a tÃ¹y chá»n tráº¡ng thÃ¡i phiáº¿u nháº­p ra module scope Ä‘á»ƒ giáº£m render/cáº¥p phÃ¡t thá»«a.
- Thay Ä‘á»•i chá»‰ tÃ¡c Ä‘á»™ng Ä‘á»‹nh danh pháº§n tá»­ khi render, khÃ´ng Ä‘á»•i handler xÃ³a mÃ£, dá»¯ liá»‡u phiáº¿u hoáº·c quy táº¯c nháº­p/xuáº¥t kho.
- Verification: frontend `npm run lint` vÃ  `npm run build` pass; React Doctor full scan cÃ²n 390 cáº£nh bÃ¡o vÃ  khÃ´ng cÃ²n rule `no-array-index-as-key`.

### Update 2026-06-28 - Xá»­ lÃ½ cáº£nh bÃ¡o mÃ u chá»¯ React Doctor trong giao diá»‡n kho

- Äá»•i mÃ u chá»¯ cÃ¡c nÃºt thao tÃ¡c phiáº¿u nháº­p, chá»©ng tá»«, sai lá»‡ch vÃ  upload file sang mÃ u cÃ¹ng ngá»¯ nghÄ©a vá»›i tráº¡ng thÃ¡i ná»n/hover Ä‘á»ƒ trÃ¡nh chá»¯ xÃ¡m trÃªn ná»n mÃ u.
- CÃ¡c thay Ä‘á»•i chá»‰ náº±m á»Ÿ class Tailwind, khÃ´ng Ä‘á»•i luá»“ng nháº­p kho, Ä‘á»‹nh danh IMEI/serial hoáº·c dá»¯ liá»‡u phiáº¿u.
- Verification: frontend `npm run lint` pass; React Doctor full scan hiá»‡n cÃ²n 476 warnings vÃ  khÃ´ng cÃ²n rule `no-gray-on-colored-background`.

### Update 2026-06-28 - Giáº£m cáº£nh bÃ¡o accessibility React Doctor trong giao diá»‡n kho

- Bá»• sung `aria-label` cho cÃ¡c Ã´ tÃ¬m kiáº¿m, bá»™ lá»c ngÃ y, checkbox chá»n dÃ²ng, Ã´ nháº­p sá»‘ lÆ°á»£ng, quÃ©t IMEI/serial, import file vÃ  textarea nháº­p danh sÃ¡ch mÃ£ trong cÃ¡c mÃ n tá»“n kho, phiáº¿u xuáº¥t, phiáº¿u nháº­p vÃ  modal IMEI.
- Thay cÃ¡c Ã´ báº£ng/header rá»—ng báº±ng ná»™i dung cÃ³ nghÄ©a hoáº·c kÃ½ hiá»‡u giá»¯ chá»— Ä‘á»ƒ trÃ¬nh Ä‘á»c mÃ n hÃ¬nh khÃ´ng gáº·p cell trá»‘ng.
- Verification: frontend `npm run lint` pass; React Doctor full scan cÃ²n 517 warnings vÃ  khÃ´ng cÃ²n cÃ¡c rule `button-has-type`, `control-has-associated-label`, `label-has-associated-control`, `no-autofocus`, `media-has-caption`, `prefer-tag-over-role`, `no-noninteractive-element-interactions`, `anchor-is-valid`, `click-events-have-key-events`, `no-static-element-interactions`.

### Update 2026-06-28 - Sá»­a lá»—i React Doctor má»©c error trong giao diá»‡n tá»“n kho

- `AdminInventoryTab.tsx` khÃ´ng cÃ²n gá»i `usePermission('inventory:approve')` trong biá»ƒu thá»©c `isSuperAdmin || ...`; hook Ä‘Æ°á»£c gá»i á»Ÿ top-level rá»“i má»›i káº¿t há»£p vá»›i quyá»n super admin.
- `ImeiReceiptModal.tsx` tÃ¡ch wrapper vÃ  ná»™i dung modal theo `key` cá»§a phiáº¿u nháº­p, Ä‘á»ƒ state nháº­p IMEI/serial Ä‘Æ°á»£c khá»Ÿi táº¡o khi modal mount thay vÃ¬ reset hÃ ng loáº¡t trong `useEffect`.
- `AdminInventoryReceiptDetails.tsx` Ä‘á»•i luá»“ng in phiáº¿u nháº­p tá»« `document.write` sang Blob HTML Ä‘á»ƒ trÃ¡nh sink HTML Ä‘á»™ng; trÆ°á»ng tá»“n hiá»‡n táº¡i trong modal Ä‘iá»u chá»‰nh Ä‘Æ°á»£c Ä‘Ã¡nh dáº¥u `readOnly`.
- Verification: frontend `npm run lint` pass; `npx react-doctor@latest --no-telemetry --no-warnings --verbose` khÃ´ng cÃ²n issue má»©c error.

### Update 2026-06-27 (9) - TÃ¡ch tiáº¿p giao diá»‡n vÃ  luá»“ng ghi sá»• kho

- TÃ¡ch workspace tá»“n kho, sá»• kho vÃ  ká»‡ hÃ ng khá»i `AdminInventoryTab.tsx` sang `AdminInventoryWorkspace.tsx`; component cha tiáº¿p tá»¥c giá»¯ state vÃ  quy trÃ¬nh kiá»ƒm kÃª/Ä‘iá»u chá»‰nh.
- TÃ¡ch mÃ n chi tiáº¿t bá»‘c hÃ ng khá»i `AdminInventoryOutboundsTab.tsx` sang `AdminInventoryOutboundDetail.tsx`.
- TÃ¡ch `services/inventory/receipts.py` thÃ nh facade, `receipt_drafts.py` vÃ  `receipt_posting.py`.
- TÃ¡ch `repositories/inventory/stock_mutations.py` thÃ nh cÃ¡c module tá»“n kho, lÃ´ hÃ ng, kiá»ƒm kÃª, mÃ£ Ä‘á»‹nh danh vÃ  Ä‘iá»u chá»‰nh.
- KhÃ´ng thay Ä‘á»•i chá»¯ kÃ½ API, transaction boundary hoáº·c quy táº¯c IMEI/Serial.

### Update 2026-06-27 (8) - TÃ¡ch repository/service tá»“n kho theo cá»¥m nghiá»‡p vá»¥

- TÃ¡ch `inventory_repo.py` thÃ nh facade tÆ°Æ¡ng thÃ­ch vÃ  cÃ¡c module nhá» trong `app/infrastructure/database/repositories/inventory/`: `overview`, `identifiers`, `documents`, `locations`, `receipts`, `stock_mutations`, `outbounds`.
- TÃ¡ch `inventory_service.py` thÃ nh facade tÆ°Æ¡ng thÃ­ch vÃ  cÃ¡c module nhá» trong `app/application/services/inventory/`: `common`, `overview`, `identifiers`, `documents`, `receipts`, `outbounds`.
- CÃ¡c router/service hiá»‡n táº¡i váº«n import qua `inventory_repo` vÃ  `inventory_service` nhÆ° cÅ©, giáº£m rá»§i ro Ä‘á»•i caller trong láº§n refactor nÃ y.
- Frontend inventory tÃ¡ch bá»›t `AdminInventoryTab` thÃ nh `AdminInventoryTabUtils`, `AdminInventoryLocationsSection`, `AdminInventoryTabModals`; tÃ¡ch chi tiáº¿t phiáº¿u nháº­p thÃ nh `AdminInventoryReceiptDetails` vÃ  `ImeiReceiptModal`.
- Verification: `py_compile` pass cho cÃ¡c module inventory backend vÃ  `admin_inventory.py`; frontend `npm run lint` pass.

### Update 2026-06-27 (6) - Sá»­a lá»—i táº£i chi tiáº¿t phiáº¿u xuáº¥t kho do lá»‡ch key

- Bá»• sung cÃ¡c trÆ°á»ng `document_no`, `created_at`, vÃ  `created_by` (snake_case) vÃ o káº¿t quáº£ tráº£ vá» cá»§a API danh sÃ¡ch phiáº¿u xuáº¥t kho (`list_inventory_outbound_documents` á»Ÿ repository) bÃªn cáº¡nh cÃ¡c trÆ°á»ng camelCase sáºµn cÃ³.
- Kháº¯c phá»¥c lá»—i `document_no` bá»‹ rá»—ng (undefined) á»Ÿ frontend lÃ m cho request táº£i chi tiáº¿t phiáº¿u xuáº¥t kho trá» Ä‘áº¿n `/admin/inventory/outbounds/undefined` vÃ  tráº£ vá» 404.
- Kháº¯c phá»¥c viá»‡c cá»™t NgÃ y táº¡o bá»‹ trá»‘ng do khÃ´ng tÃ¬m tháº¥y trÆ°á»ng `created_at`.

### Update 2026-06-27 (5) - Tinh gá»n thao tÃ¡c Ä‘Ã³ng hÃ ng vÃ  chá»n ká»‡ xuáº¥t

- Chi tiáº¿t phiáº¿u xuáº¥t kho nay tráº£ thÃªm `availableLocations` cho tá»«ng dÃ²ng sáº£n pháº©m, chá»‰ gá»“m cÃ¡c ká»‡ Ä‘ang cÃ²n tá»“n kháº£ dá»¥ng cá»§a Ä‘Ãºng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘Ã³.
- MÃ n Ä‘Ã³ng hÃ ng khÃ´ng cÃ²n hiá»ƒn thá»‹ toÃ n bá»™ danh sÃ¡ch ká»‡ trong dropdown; nhÃ¢n viÃªn chá»‰ chá»n trong cÃ¡c ká»‡ cÃ³ hÃ ng tÆ°Æ¡ng á»©ng, giáº£m nháº§m láº«n cho mÃ´ hÃ¬nh má»™t chi nhÃ¡nh.
- NÃºt thao tÃ¡c Ä‘Æ°á»£c tinh gá»n: `LÆ°u Ä‘Ã³ng hÃ ng` Ä‘á»•i thÃ nh `Cáº­p nháº­t`, `HoÃ n táº¥t xuáº¥t kho` Ä‘á»•i thÃ nh `XÃ¡c nháº­n xuáº¥t kho`.
- Khi báº¥m `XÃ¡c nháº­n xuáº¥t kho`, frontend tá»± lÆ°u thÃ´ng tin ká»‡/IMEI/Serial trÆ°á»›c rá»“i má»›i gá»i xÃ¡c nháº­n xuáº¥t kho, nÃªn nhÃ¢n viÃªn khÃ´ng báº¯t buá»™c pháº£i báº¥m `Cáº­p nháº­t` nhÆ° má»™t bÆ°á»›c riÃªng náº¿u Ä‘Ã£ nháº­p Ä‘á»§ dá»¯ liá»‡u.
- CÃ¡c nhÃ£n hiá»ƒn thá»‹ chuyá»ƒn tá»« â€œbá»‘c hÃ ngâ€ sang â€œÄ‘Ã³ng hÃ ng/ká»‡ xuáº¥tâ€ Ä‘á»ƒ phÃ¹ há»£p ngá»¯ cáº£nh cá»­a hÃ ng bÃ¡n láº».

### Update 2026-06-27 (4) - IMEI phá»¥ thuá»™c serial

- Helper Ä‘á»c policy tá»“n kho coi serial lÃ  Ä‘á»‹nh danh gá»‘c: náº¿u policy hiá»‡u lá»±c cÃ³ IMEI thÃ¬ há»‡ thá»‘ng cÅ©ng xem sáº£n pháº©m lÃ  cÃ³ quáº£n lÃ½ serial, ká»ƒ cáº£ dá»¯ liá»‡u cÅ© Ä‘ang lÆ°u `trackImei = true` nhÆ°ng `trackSerialNumber = false`.
- Quy táº¯c nÃ y báº£o Ä‘áº£m luá»“ng nháº­p/xuáº¥t kho luÃ´n yÃªu cáº§u serial cho sáº£n pháº©m cÃ³ IMEI, phÃ¹ há»£p mÃ´ hÃ¬nh serial + IMEI1 + IMEI2 tÃ¹y chá»n.
- Verification: backend `py_compile` pass cho `inventory_service.py`.

### Update 2026-06-27 (3) - GhÃ©p cáº·p IMEI vÃ  serial khi xuáº¥t kho

- **Database**: ThÃªm migration `035_product_identifier_pairs.sql` táº¡o báº£ng `product_identifier_pairs` Ä‘á»ƒ lÆ°u cáº·p IMEI/serial thuá»™c cÃ¹ng má»™t mÃ¡y váº­t lÃ½ theo tá»«ng sáº£n pháº©m/biáº¿n thá»ƒ.
- **Nháº­p kho**: Khi nháº­p sáº£n pháº©m quáº£n lÃ½ Ä‘á»“ng thá»i IMEI vÃ  serial, há»‡ thá»‘ng ghÃ©p cáº·p theo thá»© tá»± hai danh sÃ¡ch Ä‘Ã£ nháº­p; IMEI vÃ  serial cÃ¹ng chá»‰ sá»‘ Ä‘Æ°á»£c xem lÃ  cÃ¹ng má»™t mÃ¡y.
- **Xuáº¥t kho**: ThÃªm API `GET /admin/inventory/outbound-identifier-pair` Ä‘á»ƒ mÃ n phiáº¿u xuáº¥t kho quÃ©t má»™t IMEI hoáº·c serial vÃ  tá»± láº¥y mÃ£ cÃ²n láº¡i náº¿u cáº·p mÃ£ Ä‘ang `IN_STOCK` táº¡i Ä‘Ãºng ká»‡ Ä‘Ã£ chá»n.
- **Frontend**: MÃ n phiáº¿u xuáº¥t kho tá»± thÃªm cáº£ IMEI vÃ  serial vÃ o cÃ¹ng allocation khi sáº£n pháº©m quáº£n lÃ½ cáº£ hai loáº¡i mÃ£, giÃºp nhÃ¢n viÃªn kho khÃ´ng pháº£i quÃ©t láº·p láº¡i hai mÃ£ cá»§a cÃ¹ng má»™t mÃ¡y.
- **Update 036**: Chuyá»ƒn mÃ´ hÃ¬nh sang serial lÃ  Ä‘á»‹nh danh chÃ­nh cá»§a mÃ¡y, `imei1` lÃ  IMEI chÃ­nh báº¯t buá»™c khi sáº£n pháº©m báº­t IMEI, `imei2` lÃ  IMEI phá»¥ tÃ¹y chá»n. Khi xuáº¥t kho cÃ³ thá»ƒ quÃ©t serial, IMEI1 hoáº·c IMEI2; allocation váº«n lÆ°u serial vÃ  IMEI1 Ä‘á»ƒ khá»›p sá»‘ lÆ°á»£ng mÃ¡y hiá»‡n táº¡i.
- **Äá»“ng bá»™ tráº¡ng thÃ¡i**: Khi hoÃ n táº¥t xuáº¥t kho, náº¿u mÃ¡y cÃ³ `imei2` trong báº£ng ghÃ©p cáº·p thÃ¬ há»‡ thá»‘ng cÅ©ng chuyá»ƒn IMEI2 sang `SOLD` cÃ¹ng IMEI1/serial Ä‘á»ƒ trÃ¡nh tá»“n kho Ä‘á»‹nh danh bá»‹ lá»‡ch.

### Update 2026-06-27 (2) - Kháº¯c phá»¥c lá»—i cháº·n luá»“ng vÃ  tá»‘i Æ°u hÃ³a bá»™ lá»c

- **Database Constraint & Migrations**: ThÃªm file migration `034_allow_picking_picked_outbound_status.sql` vÃ  sá»­a baseline `init_database.sql` Ä‘á»ƒ cho phÃ©p tráº¡ng thÃ¡i `PICKING` vÃ  `PICKED` trong check constraint `inventory_documents_status_check`.
- **Auto-Suggest Outbound Document**:
  - TÃ¡ch nhÃ¡nh kiá»ƒm tra `tracks_imei` vÃ  `tracks_serial` thÃ nh Ä‘á»™c láº­p trong `auto_suggest_outbound_document` Ä‘á»ƒ há»— trá»£ bá»‘c hÃ ng song song cáº£ hai Ä‘á»‹nh danh cho sáº£n pháº©m cáº¥u hÃ¬nh song song.
  - Sá»­a lá»—i mapping allocations cá»§a hÃ m `_determine_outbound_status` (Ä‘á»c tá»« trÆ°á»ng pháº³ng `allocations` tráº£ vá» tá»« SQL thay vÃ¬ truy cáº­p `metadata.allocations` bá»‹ rá»—ng).
  - Cáº­p nháº­t tá»± Ä‘á»™ng bá»‘c hÃ ng lÆ°u kÃ¨m chi tiáº¿t `allocations_data` vÃ o metadata dÃ²ng phiáº¿u, vÃ  tá»± Ä‘á»™ng gá»i `_determine_outbound_status` Ä‘á»ƒ nÃ¢ng tráº¡ng thÃ¡i phiáº¿u xuáº¥t lÃªn `PICKED` ngay sau gá»£i Ã½ bá»‘c.
- **Äá»“ng bá»™ tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh khi xuáº¥t kho**: Äá»•i logic cáº­p nháº­t tráº¡ng thÃ¡i IMEI/Serial sang `SOLD` khi hoÃ n táº¥t xuáº¥t kho (`_post_inventory_outbound`) tá»« `elif tracks_serial_number` thÃ nh `if tracks_serial_number` Ä‘á»™c láº­p, báº£o Ä‘áº£m cáº­p nháº­t Ä‘áº§y Ä‘á»§ cáº£ hai loáº¡i Ä‘á»‹nh danh cho sáº£n pháº©m Ã¡p dá»¥ng song song cáº£ hai chÃ­nh sÃ¡ch.
- **Frontend Cleanups & Filtering**:
  - Dá»n dáº¹p logic bá»‘c hÃ ng cÅ© `issue_allocations` vÃ  validate dÆ° thá»«a trong hook `useAdminOrdersLogic.ts` khi lÆ°u Ä‘Æ¡n hÃ ng.
  - ThÃªm cÃ¡c tÃ¹y chá»n bá»™ lá»c `'PICKING'`, `'PICKED'`, vÃ  `'CANCELLED'` vÃ o dropdown select á»Ÿ tab phiáº¿u xuáº¥t kho (`AdminInventoryOutboundsTab.tsx`).
- **Verification**: Cháº¡y thÃ nh cÃ´ng script test luá»“ng xuáº¥t kho `test_outbound_flow.py`, kiá»ƒm thá»­ chuyá»ƒn tráº¡ng thÃ¡i vÃ  cÃ¡c rÃ ng buá»™c Ä‘áº¡t káº¿t quáº£ 100%.

### Update 2026-06-27 - NÃ¢ng cáº¥p quy trÃ¬nh bá»‘c hÃ ng Ä‘a ká»‡ vÃ  Ä‘á»“ng bá»™ Ä‘Æ¡n hÃ ng

- **Commerce Logic & Sync**: Khi phiáº¿u xuáº¥t kho (`inventory_documents.document_type = OUTBOUND`) chuyá»ƒn sang tráº¡ng thÃ¡i `COMPLETED`, há»‡ thá»‘ng tá»± Ä‘á»™ng giáº£i phÃ³ng vÃ  Ä‘Ã³ng cÃ¡c giá»¯ hÃ ng (`inventory_reservations`) liÃªn quan cá»§a Ä‘Æ¡n hÃ ng sang `CONSUMED` (trong `CompleteOrderUseCase.execute`), kháº¯c phá»¥c triá»‡t Ä‘á»ƒ lá»—i treo giá»¯ hÃ ng.
- **VÃ²ng Ä‘á»i tráº¡ng thÃ¡i Phiáº¿u xuáº¥t kho (Outbound Lifecycle)**:
  - Bá»• sung cÃ¡c tráº¡ng thÃ¡i trung gian `PICKING` (Ä‘ang bá»‘c hÃ ng) vÃ  `PICKED` (Ä‘Ã£ bá»‘c xong - chá» duyá»‡t), tá»± Ä‘á»™ng tÃ­nh toÃ¡n tá»« tiáº¿n trÃ¬nh bá»‘c ká»‡ thá»±c táº¿ trong `_determine_outbound_status`.
  - Há»— trá»£ tá»± Ä‘á»™ng há»§y phiáº¿u xuáº¥t liÃªn káº¿t sang `CANCELLED` khi Ä‘Æ¡n hÃ ng bá»‹ há»§y.
  - Siáº¿t cháº·t phÃª duyá»‡t: Chá»‰ cho phÃ©p hoÃ n táº¥t xuáº¥t kho (`COMPLETED`) khi phiáº¿u xuáº¥t Ä‘Ã£ á»Ÿ tráº¡ng thÃ¡i `PICKED` vÃ  ngÆ°á»i duyá»‡t cÃ³ vai trÃ² `SUPER_ADMIN`.
- **Frontend UX & Controls**:
  - áº¨n hoÃ n toÃ n khá»‘i "XÃ¡c nháº­n ká»‡ xuáº¥t thá»±c táº¿" trÃªn mÃ n hÃ¬nh chi tiáº¿t Ä‘Æ¡n hÃ ng (AdminOrdersTab) khi chuyá»ƒn tráº¡ng thÃ¡i sang `SHIPPED`. ToÃ n bá»™ nghiá»‡p vá»¥ chá»n vá»‹ trÃ­ bá»‘c hÃ ng Ä‘Æ°á»£c quy hoáº¡ch táº­p trung táº¡i mÃ n Phiáº¿u xuáº¥t kho.
  - Tab Outbound tá»± Ä‘á»™ng chuyá»ƒn Ä‘á»•i giao diá»‡n thÃ nh read-only (khÃ³a má»i nÃºt bá»‘c hÃ ng, xÃ³a ká»‡, quÃ©t IMEI/Serial) khi phiáº¿u á»Ÿ tráº¡ng thÃ¡i káº¿t thÃºc `COMPLETED` hoáº·c `CANCELLED`.
  - Hiá»ƒn thá»‹ badge tráº¡ng thÃ¡i trá»±c quan: `DRAFT` (slate), `PICKING` (amber), `PICKED` (blue), `COMPLETED` (green), `CANCELLED` (red).
- **Bá»‘c hÃ ng Ä‘a ká»‡ (Multi-shelf Allocations)**: Cáº­p nháº­t API vÃ  service `inventory_service.py` Ä‘á»ƒ há»— trá»£ xuáº¥t má»™t dÃ²ng sáº£n pháº©m tá»« nhiá»u ká»‡ khÃ¡c nhau. Danh sÃ¡ch phÃ¢n bá»• chi tiáº¿t Ä‘Æ°á»£c lÆ°u trá»¯ dáº¡ng máº£ng `allocations` (gá»“m `locationId`, `quantity`, `imeis`, `serialNumbers`) trong trÆ°á»ng `metadata JSONB` cá»§a `inventory_document_lines`.
- **QuÃ©t Ä‘á»‹nh danh song song**: TÃ¡ch biá»‡t UI nháº­p mÃ£ IMEI vÃ  Serial trÃªn mÃ n hÃ¬nh phiáº¿u xuáº¥t kho, cho phÃ©p hiá»ƒn thá»‹ song song cáº£ hai Ã´ quÃ©t náº¿u sáº£n pháº©m Ä‘Æ°á»£c cáº¥u hÃ¬nh Ã¡p dá»¥ng Ä‘á»“ng thá»i cáº£ hai chÃ­nh sÃ¡ch quáº£n lÃ½.
- **Chuáº©n hÃ³a API Router**: Kháº¯c phá»¥c triá»‡t Ä‘á»ƒ cÃ¡c lá»—i cÃº phÃ¡p dá»Ÿ dang vÃ  loáº¡i bá» cÃ¡c route trÃ¹ng láº·p cá»§a inventory receipts táº¡i `admin_inventory.py`.

## Update 2026-06-24 - Báº£o vá»‡ tá»“n kho khi chá»‰nh sá»­a biáº¿n thá»ƒ catalog

- `product_variant_service.upsert_product_variants` nay giá»¯ nguyÃªn `stock_quantity` cá»§a biáº¿n thá»ƒ hiá»‡n cÃ³ khi admin lÆ°u form sáº£n pháº©m.
- Biáº¿n thá»ƒ má»›i Ä‘Æ°á»£c táº¡o tá»« catalog báº¯t Ä‘áº§u vá»›i tá»“n kho `0`; má»i tÄƒng/giáº£m tá»“n pháº£i Ä‘i qua phiáº¿u nháº­p, xuáº¥t kho, Ä‘iá»u chá»‰nh kho hoáº·c luá»“ng Ä‘Æ¡n hÃ ng.
- Biáº¿n thá»ƒ Ä‘Ã£ cÃ³ rÃ ng buá»™c kho/Ä‘Æ¡n hÃ ng/IMEI/serial khÃ´ng Ä‘Æ°á»£c Ä‘á»•i cÃ¡c trÆ°á»ng Ä‘á»‹nh danh nhÆ° SKU, mÃ u sáº¯c, dung lÆ°á»£ng, RAM, cáº¥u hÃ¬nh, thuá»™c tÃ­nh vÃ  thÃ´ng sá»‘ Ä‘á»‹nh danh.
- Má»¥c tiÃªu lÃ  trÃ¡nh lÃ m sai lá»‹ch sá»­ chá»©ng tá»« vÃ  trÃ¡nh lá»‡ch giá»¯a tá»“n thá»±c táº¿, lot, reservation, IMEI/serial vá»›i dá»¯ liá»‡u biáº¿n thá»ƒ hiá»ƒn thá»‹.

## Update 2026-06-24 - Bá»• sung phiáº¿u nháº­p cho tá»“n sáº£n pháº©m má»›i

- Táº¡o script `backend/scripts/create_receipt_for_virtual_new_products.py` Ä‘á»ƒ há»£p thá»©c hÃ³a nhÃ³m sáº£n pháº©m má»›i táº¡o ngÃ y 2026-06-23 Ä‘ang cÃ³ tá»“n trong `inventory_levels` nhÆ°ng chÆ°a cÃ³ phiáº¿u nháº­p hoÃ n táº¥t.
- Script táº¡o phiáº¿u nháº­p `NK20260624-BO-SUNG-TON-MOI` á»Ÿ tráº¡ng thÃ¡i `COMPLETED`, gá»“m 72 dÃ²ng vÃ  tá»•ng sá»‘ lÆ°á»£ng 5.160 sáº£n pháº©m.
- ÄÃ¢y lÃ  phiáº¿u Ä‘á»‘i soÃ¡t tá»“n Ä‘Ã£ cÃ³ sáºµn: metadata cÃ³ `reconcilesExistingStock = true` vÃ  `stockMutationSkipped = true`; script khÃ´ng gá»i luá»“ng post chuáº©n vÃ  khÃ´ng cá»™ng tá»“n láº§n ná»¯a.
- Script bá»• sung `inventory_document_lines`, `inventory_lots`, `inventory_lot_movements`, `inventory_adjustment_logs` vÃ  audit log Ä‘á»ƒ lá»‹ch sá»­ nháº­p kho, lÃ´ ná»™i bá»™ vÃ  bÃ¡o cÃ¡o truy váº¿t khá»›p láº¡i vá»›i tá»“n hiá»‡n táº¡i.
- Verification local: trÆ°á»›c/sau khi cháº¡y script, tá»•ng `inventory_levels` giá»¯ nguyÃªn 9.630; tá»•ng lÃ´ active tÄƒng khá»›p lÃªn 9.630; khÃ´ng cÃ²n dÃ²ng tá»“n má»›i tá»« 2026-06-23 cÃ³ sá»‘ lÆ°á»£ng nhÆ°ng thiáº¿u chá»©ng tá»« nháº­p hoÃ n táº¥t.

## Update 2026-06-23 - Soft Lock háº­u mÃ£i vÃ  vÃ²ng Ä‘á»i IMEI lá»—i

- Module háº­u mÃ£i bá»• sung `after_sales_allocations` Ä‘á»ƒ giá»¯ tá»“n kháº£ dá»¥ng trong 48 giá» sau khi QC duyá»‡t Ä‘á»•i/thay mÃ¡y, khÃ´ng gÃ¡n cá»©ng IMEI cho Ä‘áº¿n lÃºc admin quÃ©t mÃ¡y thay tháº¿.
- CÃ´ng thá»©c tá»“n kháº£ dá»¥ng cá»§a luá»“ng háº­u mÃ£i trá»« thÃªm allocation `LOCKED`, bÃªn cáº¡nh tá»“n Ä‘ang giá»¯ cho Ä‘Æ¡n hÃ ng vÃ  IMEI/serial Ä‘Ã£ reserved.
- Khi hoÃ n táº¥t Ä‘á»•i/thay mÃ¡y, há»‡ thá»‘ng chuyá»ƒn IMEI má»›i sang `SOLD`, trá»« tá»“n váº­t lÃ½ á»Ÿ vá»‹ trÃ­ cá»§a IMEI vÃ  ghi `inventory_adjustment_logs` vá»›i lÃ½ do `AFTER_SALES_REPLACEMENT`.
- IMEI cÅ© Ä‘Æ°á»£c chuyá»ƒn sang `DEFECTIVE_RETURNED` vÃ  cÃ³ báº£ng sá»± kiá»‡n disposition Ä‘á»ƒ theo dÃµi tiáº¿p cÃ¡c tráº¡ng thÃ¡i `INSPECTION_PENDING`, `RTV_PENDING`, `LIQUIDATION_PENDING`, `RTV_COMPLETED`, `LIQUIDATED`, `SCRAP`, `OUT_OF_SYSTEM`.
- KhÃ´ng cho xuáº¥t IMEI khá»i há»‡ thá»‘ng náº¿u chÆ°a cÃ³ káº¿t quáº£ RTV, thanh lÃ½ hoáº·c pháº¿ pháº©m; má»—i láº§n chuyá»ƒn tráº¡ng thÃ¡i lÆ°u lÃ½ do, chá»©ng tá»«, Ä‘á»‘i tÃ¡c vÃ  giÃ¡ trá»‹ thu há»“i.

## Update 2026-06-20 - Backfill IMEI/Serial khi Ä‘á»•i chÃ­nh sÃ¡ch danh má»¥c

- Bá»• sung chá»©ng tá»« ká»¹ thuáº­t `inventory_policy_migrations` Ä‘á»ƒ xá»­ lÃ½ hÃ ng tá»“n cÅ© khi danh má»¥c chuyá»ƒn tá»« khÃ´ng quáº£n lÃ½ sang quáº£n lÃ½ IMEI hoáº·c serial number.
- Danh sÃ¡ch mÃ£ quÃ©t Ä‘Æ°á»£c giá»¯ á»Ÿ staging; chá»‰ khi Ä‘á»§ sá»‘ lÆ°á»£ng vÃ  Ä‘á»‘i soÃ¡t tá»“n khÃ´ng thay Ä‘á»•i má»›i chuyá»ƒn vÃ o `product_imeis` hoáº·c `product_serial_numbers` vá»›i tráº¡ng thÃ¡i `IN_STOCK`.
- TÃ¡c vá»¥ bá»‹ há»§y giá»¯ mÃ£ á»Ÿ tráº¡ng thÃ¡i `CANCELLED` Ä‘á»ƒ audit, khÃ´ng Ä‘Æ°a vÃ o read-model tá»“n kho.
- Má»™t mÃ£ chá»‰ Ä‘Æ°á»£c tá»“n táº¡i trong má»™t staging Ä‘ang hoáº¡t Ä‘á»™ng; database cÃ³ unique index Ä‘á»ƒ cháº·n xung Ä‘á»™t Ä‘á»“ng thá»i.
- IMEI vÃ  serial Ä‘Æ°á»£c kÃ­ch hoáº¡t Ä‘á»™c láº­p, trÃ¡nh hoÃ n táº¥t má»™t tÃ¡c vá»¥ nhÆ°ng vÃ´ tÃ¬nh báº­t policy cá»§a loáº¡i cÃ²n láº¡i.
- Giao diá»‡n danh má»¥c há»— trá»£ quÃ©t liÃªn tá»¥c hoáº·c dÃ¡n nhiá»u mÃ£ theo tá»«ng sáº£n pháº©m/biáº¿n thá»ƒ, hiá»ƒn thá»‹ tiáº¿n Ä‘á»™ vÃ  lá»—i backend ngay trong khá»‘i tÃ¡c vá»¥.
- Pháº¡m vi giá»¯ á»Ÿ má»©c WMS-light cho luáº­n vÄƒn: khÃ´ng thÃªm queue, tracking mode theo lÃ´ hoáº·c quy trÃ¬nh Ä‘á»‘i soÃ¡t doanh nghiá»‡p nhiá»u táº§ng.

## Update 2026-06-19 - Bá»• sung dÃ£y C vÃ  giáº£i phÃ³ng cÃ¡c Ã´ quÃ¡ táº£i

- ThÃªm migration `013_inventory_location_aisle_c_and_rebalance_full_bins.sql` Ä‘á»ƒ táº¡o dÃ£y C theo mÃ´ hÃ¬nh 10 ká»‡ x 4 Ã´, mÃ£ tá»« `C-01-01` Ä‘áº¿n `C-10-04`.
- CÃ¡c Ã´ dÃ£y C dÃ¹ng cÃ¹ng kÃ­ch thÆ°á»›c vÃ  há»‡ sá»‘ sá»­ dá»¥ng vá»›i dÃ£y A/B: `100 x 60 x 40 cm`, `usable_ratio = 0.75`, cho phÃ©p nhiá»u SKU.
- Migration xÃ¡c Ä‘á»‹nh cÃ¡c Ã´ A/B Ä‘ang vÆ°á»£t 100% dung lÆ°á»£ng, chá»n nguyÃªn dÃ²ng SKU theo thá»ƒ tÃ­ch tÄƒng dáº§n cho Ä‘áº¿n khi Ã´ nguá»“n háº¿t quÃ¡ táº£i vÃ  chuyá»ƒn má»—i dÃ²ng sang má»™t Ã´ C trá»‘ng.
- Vá»‹ trÃ­ cá»§a tá»“n kho, IMEI, serial vÃ  lÃ´ ná»™i bá»™ Ä‘Æ°á»£c cáº­p nháº­t Ä‘á»“ng bá»™; metadata lÃ´ ghi láº¡i ká»‡ nguá»“n, ká»‡ Ä‘Ã­ch vÃ  thá»i Ä‘iá»ƒm chuyá»ƒn.
- Migration dá»«ng vá»›i lá»—i rÃµ rÃ ng náº¿u sá»‘ Ã´ C khÃ´ng Ä‘á»§ hoáº·c cÃ³ má»™t dÃ²ng SKU lá»›n hÆ¡n dung lÆ°á»£ng má»™t Ã´, trÃ¡nh cáº­p nháº­t dá»Ÿ dang.
- Verification local: migration cháº¡y thÃ nh cÃ´ng; táº¡o Ä‘á»§ 40 Ã´ C, dÃ¹ng 20 Ã´ Ä‘á»ƒ chuyá»ƒn 20 dÃ²ng SKU; sá»‘ Ã´ vÆ°á»£t dung lÆ°á»£ng giáº£m tá»« 20 xuá»‘ng 0; tá»•ng tá»“n vÃ  tá»•ng lÃ´ Ä‘á»u giá»¯ nguyÃªn `4.470`; sá»‘ IMEI, serial vÃ  lÃ´ lá»‡ch vá»‹ trÃ­ so vá»›i tá»“n kho Ä‘á»u báº±ng 0.

## Update 2026-06-18 - Xuáº¥t má»™t sáº£n pháº©m tá»« nhiá»u ká»‡

- MÃ n chi tiáº¿t Ä‘Æ¡n hÃ ng cho phÃ©p thÃªm nhiá»u dÃ²ng ká»‡ thá»±c táº¿ cho cÃ¹ng má»™t sáº£n pháº©m báº±ng nÃºt `ThÃªm ká»‡`, Ä‘á»“ng thá»i há»— trá»£ xÃ³a tá»«ng dÃ²ng ká»‡.
- Giao diá»‡n hiá»ƒn thá»‹ `ÄÃ£ phÃ¢n bá»• / cáº§n xuáº¥t` theo tá»«ng dÃ²ng sáº£n pháº©m vÃ  Ä‘á»•i tráº¡ng thÃ¡i mÃ u khi tá»•ng sá»‘ lÆ°á»£ng Ä‘Ã£ khá»›p.
- Frontend cháº·n lÆ°u náº¿u dÃ²ng ká»‡ thiáº¿u vá»‹ trÃ­, sá»‘ lÆ°á»£ng khÃ´ng há»£p lá»‡, chá»n trÃ¹ng ká»‡ hoáº·c tá»•ng phÃ¢n bá»• khÃ¡c sá»‘ lÆ°á»£ng Ä‘Æ¡n hÃ ng.
- Backend kiá»ƒm tra láº¡i tá»•ng sá»‘ lÆ°á»£ng vÃ  ká»‡ trÃ¹ng trÆ°á»›c khi trá»« tá»“n; tá»«ng pháº§n phÃ¢n bá»• tiáº¿p tá»¥c trá»« Ä‘Ãºng tá»“n ká»‡ vÃ  lÃ´ FIFO trong ká»‡ Ä‘Ã³.
- Náº¿u nhÃ¢n viÃªn khÃ´ng thÃªm báº¥t ká»³ ká»‡ nÃ o cho má»™t dÃ²ng sáº£n pháº©m, há»‡ thá»‘ng giá»¯ hÃ nh vi fallback FIFO tá»± Ä‘á»™ng.
- Verification: frontend `npm run lint` pass; backend `py_compile` pass cho commerce use case/repository.

## Update 2026-06-18 - LÃ´ tá»“n kho ná»™i bá»™ tá»± Ä‘á»™ng

- ThÃªm migration `012_inventory_internal_lots.sql` táº¡o `inventory_lots` vÃ  `inventory_lot_movements`.
- Khi hoÃ n táº¥t phiáº¿u nháº­p, há»‡ thá»‘ng tá»± sinh lÃ´ ná»™i bá»™ theo tá»«ng dÃ²ng sáº£n pháº©m/biáº¿n thá»ƒ vÃ  ká»‡; nhÃ¢n viÃªn khÃ´ng cáº§n nháº­p hay chá»n mÃ£ lÃ´.
- Khi xuáº¥t Ä‘Æ¡n hÃ ng, há»‡ thá»‘ng tiÃªu thá»¥ lÃ´ cÅ© trÆ°á»›c theo `received_at` bÃªn trong Ä‘Ãºng ká»‡ thá»±c táº¿ Ä‘Ã£ xÃ¡c nháº­n; náº¿u chÆ°a xÃ¡c nháº­n ká»‡ thÃ¬ váº«n chá»n ká»‡ theo FIFO rá»“i chá»n lÃ´ FIFO trong ká»‡.
- Má»—i láº§n nháº­p, bÃ¡n hoáº·c Ä‘áº£o phiáº¿u Ä‘á»u cÃ³ movement Ä‘á»ƒ truy váº¿t nguá»“n phiáº¿u, Ä‘Æ¡n hÃ ng vÃ  sá»‘ lÆ°á»£ng cá»§a lÃ´.
- Äáº£o phiáº¿u nháº­p chá»‰ Ä‘Æ°á»£c phÃ©p khi lÃ´ cá»§a chÃ­nh phiáº¿u Ä‘Ã³ cÃ²n Ä‘á»§ sá»‘ lÆ°á»£ng; náº¿u lÃ´ Ä‘Ã£ Ä‘Æ°á»£c bÃ¡n má»™t pháº§n thÃ¬ há»‡ thá»‘ng cháº·n Ä‘áº£o toÃ n bá»™.
- Migration backfill tá»“n hiá»‡n táº¡i thÃ nh 298 lÃ´ ná»™i bá»™. Äá»‘i soÃ¡t local: tá»•ng `inventory_levels = 4470`, tá»•ng lÃ´ cÃ²n láº¡i `= 4470`, sá»‘ nhÃ³m sáº£n pháº©m/ká»‡ lá»‡ch `= 0`.
- Verification: migration local thÃ nh cÃ´ng; backend `py_compile` pass cho inventory vÃ  commerce service/repository.

## Update 2026-06-18 - XÃ¡c nháº­n ká»‡ xuáº¥t thá»±c táº¿ khi giao hÃ ng

- API admin cáº­p nháº­t Ä‘Æ¡n hÃ ng nháº­n thÃªm `issue_allocations`, gá»“m `order_item_id`, `location_id` vÃ  `quantity` Ä‘á»ƒ nhÃ¢n viÃªn xÃ¡c nháº­n ká»‡ xuáº¥t thá»±c táº¿.
- Khi chuyá»ƒn Ä‘Æ¡n sang `SHIPPED`, náº¿u dÃ²ng Ä‘Æ¡n cÃ³ xÃ¡c nháº­n ká»‡ thÃ¬ backend trá»« Ä‘Ãºng ká»‡ nhÃ¢n viÃªn chá»n; náº¿u dÃ²ng Ä‘Æ¡n chÆ°a cÃ³ xÃ¡c nháº­n thÃ¬ fallback FIFO theo ká»‡ cÅ© trÆ°á»›c.
- Backend kiá»ƒm tra tá»•ng sá»‘ lÆ°á»£ng xÃ¡c nháº­n cá»§a tá»«ng dÃ²ng pháº£i báº±ng sá»‘ lÆ°á»£ng cáº§n xuáº¥t vÃ  ká»‡ Ä‘Æ°á»£c chá»n pháº£i cÃ²n Ä‘á»§ tá»“n kháº£ dá»¥ng.
- MÃ n chi tiáº¿t Ä‘Æ¡n hÃ ng hiá»ƒn thá»‹ khá»‘i `XÃ¡c nháº­n ká»‡ xuáº¥t thá»±c táº¿` khi chuáº©n bá»‹ chuyá»ƒn Ä‘Æ¡n sang `SHIPPED`; chá»n `SHIPPED` tá»« dropdown nhanh ngoÃ i báº£ng sáº½ má»Ÿ chi tiáº¿t Ä‘Æ¡n thay vÃ¬ trá»« kho ngay.
- Verification: backend `py_compile` pass cho `commerce/schemas.py`, `commerce/use_cases.py`, `commerce_repo.py`; frontend `npm run lint` pass.

## Update 2026-06-18 - Xuáº¥t kho theo ká»‡ cÅ© trÆ°á»›c khi giao hÃ ng

- Khi Ä‘Æ¡n hÃ ng chuyá»ƒn sang giao hÃ ng, backend khÃ´ng chá»‰ trá»« `stock_quantity` tá»•ng mÃ  cÃ²n trá»« tá»“n trong `inventory_levels` theo tá»«ng ká»‡.
- Náº¿u má»™t sáº£n pháº©m/biáº¿n thá»ƒ náº±m á»Ÿ nhiá»u ká»‡, há»‡ thá»‘ng láº¥y tá»« ká»‡ cÃ³ `inventory_levels.updated_at` cÅ© nháº¥t trÆ°á»›c, sau Ä‘Ã³ má»›i tá»›i ká»‡ má»›i hÆ¡n.
- Má»—i pháº§n xuáº¥t tá»« má»™t ká»‡ Ä‘Æ°á»£c ghi log `SALE/ORDER_SHIPPED` riÃªng kÃ¨m `location_code` vÃ  `location_name`, giÃºp tra láº¡i Ä‘Æ¡n hÃ ng Ä‘Ã£ láº¥y hÃ ng tá»« Ã´ nÃ o.
- Náº¿u tá»•ng tá»“n cÃ²n nhÆ°ng tá»“n kháº£ dá»¥ng theo ká»‡ khÃ´ng Ä‘á»§, há»‡ thá»‘ng tráº£ lá»—i `KhÃ´ng Ä‘á»§ tá»“n kháº£ dá»¥ng á»Ÿ cÃ¡c ká»‡ Ä‘á»ƒ xuáº¥t kho.` Ä‘á»ƒ trÃ¡nh lá»‡ch giá»¯a tá»“n tá»•ng vÃ  tá»“n theo vá»‹ trÃ­.
- Giá»›i háº¡n hiá»‡n táº¡i: Ä‘Ã¢y lÃ  FIFO theo má»©c ká»‡/vá»‹ trÃ­ dá»±a trÃªn `updated_at`, chÆ°a pháº£i FIFO theo tá»«ng lÃ´ nháº­p riÃªng trong cÃ¹ng má»™t ká»‡.
- Verification: backend `py_compile` pass cho `commerce/use_cases.py` vÃ  `commerce_repo.py`.

## Update 2026-06-18 - Cháº·n nháº­p kho vÆ°á»£t dung lÆ°á»£ng Ã´/ká»‡

- Backend kiá»ƒm tra dung lÆ°á»£ng cÃ²n trá»‘ng cá»§a `inventory_locations` khi lÆ°u phiáº¿u nháº­p vÃ  kiá»ƒm tra láº¡i khi hoÃ n táº¥t phiáº¿u nháº­p.
- Dung lÆ°á»£ng cáº§n thÃªm Ä‘Æ°á»£c tÃ­nh theo sá»‘ lÆ°á»£ng nháº­p nhÃ¢n vá»›i kÃ­ch thÆ°á»›c Ä‘Ã³ng gÃ³i hiá»‡u lá»±c cá»§a danh má»¥c, cÃ³ chia cho `packingRatio` Ä‘á»ƒ bÃ¹ hao há»¥t xáº¿p hÃ ng.
- Náº¿u nhiá»u dÃ²ng phiáº¿u cÃ¹ng chá»n má»™t Ã´, há»‡ thá»‘ng cá»™ng dá»“n dung lÆ°á»£ng yÃªu cáº§u trong cÃ¹ng phiáº¿u trÆ°á»›c khi so vá»›i dung lÆ°á»£ng cÃ²n láº¡i.
- Dropdown chá»n ká»‡ trong phiáº¿u nháº­p hiá»ƒn thá»‹ thÃªm pháº§n trÄƒm Ä‘áº§y vÃ  dung lÆ°á»£ng cÃ²n láº¡i theo cmÂ³ Ä‘á»ƒ nhÃ¢n viÃªn tháº¥y trÆ°á»›c khi lÆ°u.
- Náº¿u Ã´/ká»‡ khÃ´ng cÃ³ cáº¥u hÃ¬nh kÃ­ch thÆ°á»›c, luá»“ng hiá»‡n táº¡i chÆ°a cháº·n theo thá»ƒ tÃ­ch Ä‘á»ƒ trÃ¡nh khÃ³a cÃ¡c khu chá»©c nÄƒng cÅ©; cÃ¡c Ã´ A/B Ä‘Ã£ cÃ³ kÃ­ch thÆ°á»›c nÃªn Ä‘Æ°á»£c kiá»ƒm soÃ¡t.
- Verification: backend `py_compile` pass cho `inventory_service.py` vÃ  `inventory_repo.py`; frontend `npm run lint` pass.

## Update 2026-06-18 - Äiá»u chá»‰nh há»‡ sá»‘ dÃ¹ng Ä‘Æ°á»£c vÃ  xáº¿p hÃ ng

- ThÃªm migration `011_tune_storage_packing_ratios.sql` Ä‘á»ƒ tinh chá»‰nh há»‡ sá»‘ theo giáº£ Ä‘á»‹nh nghiá»‡p vá»¥ má»›i: Ã´ lÆ°u hÃ ng thÆ°á»ng/nhiá»u loáº¡i dÃ¹ng `usable_ratio = 0.75`, khu/cá»“ng ká»nh máº·c Ä‘á»‹nh `0.70`.
- Äiá»u chá»‰nh `packingRatio` theo danh má»¥c: laptop vÃ  tablet `0.80`, phá»¥ kiá»‡n nhá» vÃ  Ä‘iá»‡n thoáº¡i/Ä‘á»“ng há»“ `0.85`, camera vÃ  tai nghe `0.75`.
- Sau Ä‘iá»u chá»‰nh, Ã´ máº«u `A-01-01` cÃ³ thá»ƒ tÃ­ch dÃ¹ng Ä‘Æ°á»£c `180000 cmÂ³`, Ä‘Ã£ dÃ¹ng khoáº£ng `130676 cmÂ³`, má»©c Ä‘áº§y cÃ²n khoáº£ng `72.6%`.
- Verification: migration local thÃ nh cÃ´ng; backend `py_compile` pass; frontend `npm run lint` pass.

## Update 2026-06-18 - TÃ­nh Ä‘áº§y/trá»‘ng ká»‡ theo thá»ƒ tÃ­ch cÃ³ hao há»¥t

- ThÃªm migration `010_storage_volume_utilization_ratios.sql` bá»• sung `usable_ratio` cho `inventory_locations` Ä‘á»ƒ mÃ´ phá»ng hao há»¥t khÃ´ng gian do nhÃ¢n viÃªn xáº¿p hÃ ng, khoáº£ng há»Ÿ vÃ  trá»™n SKU.
- API danh má»¥c ká»‡ hÃ ng tÃ­nh thÃªm `usableVolumeCm3`, `usedVolumeCm3`, `availableVolumeCm3`, `fillRatio` dá»±a trÃªn kÃ­ch thÆ°á»›c Ã´, `usable_ratio`, tá»“n hiá»‡n táº¡i vÃ  kÃ­ch thÆ°á»›c Ä‘Ã³ng gÃ³i danh má»¥c.
- Frontend tab `Ká»‡ hÃ ng` hiá»ƒn thá»‹ pháº§n trÄƒm Ä‘áº§y vÃ  dung lÆ°á»£ng cÃ²n láº¡i theo cmÂ³; form ká»‡ hÃ ng cÃ³ thÃªm trÆ°á»ng `Há»‡ sá»‘ sá»­ dá»¥ng`.
- Verification: migration local thÃ nh cÃ´ng; backend `py_compile` pass; frontend `npm run lint` pass; service kiá»ƒm tra `A-01-01` tráº£ fill khoáº£ng `83.77%`.

## Update 2026-06-18 - Bá»• sung kÃ­ch thÆ°á»›c riÃªng cho tá»«ng Ã´/ká»‡

- ThÃªm migration `008_inventory_location_bin_dimensions.sql` bá»• sung `length_cm`, `width_cm`, `height_cm` cho `inventory_locations`.
- CÃ¡c Ã´ lÆ°u hÃ ng active thuá»™c dÃ£y A/B Ä‘Æ°á»£c gÃ¡n máº·c Ä‘á»‹nh `100 x 60 x 40 cm`; tá»«ng Ã´ cÃ³ thá»ƒ sá»­a kÃ­ch thÆ°á»›c riÃªng trong form ká»‡ hÃ ng.
- API danh má»¥c ká»‡ tráº£ thÃªm `lengthCm`, `widthCm`, `heightCm` vÃ  `capacityVolumeCm3` Ä‘á»ƒ chuáº©n bá»‹ tÃ­nh sá»©c chá»©a theo thá»ƒ tÃ­ch thay vÃ¬ chá»‰ theo sá»‘ lÆ°á»£ng.
- Frontend tab `Ká»‡ hÃ ng` hiá»ƒn thá»‹ kÃ­ch thÆ°á»›c/thá»ƒ tÃ­ch vÃ  form thÃªm/sá»­a ká»‡ cÃ³ trÆ°á»ng `DÃ i`, `Rá»™ng`, `Cao`.
- Verification: cháº¡y migration local thÃ nh cÃ´ng; backend `py_compile` pass; frontend `npm run lint` pass; service lá»c `A-01-01` tráº£ `100 x 60 x 40 cm`, thá»ƒ tÃ­ch `240000 cmÂ³`.

## Update 2026-06-18 - PhÃ¢n bá»• sáº£n pháº©m Ä‘ang bÃ¡n vÃ o ká»‡ A/B

- ThÃªm migration `007_assign_active_inventory_to_storage_bins.sql` Ä‘á»ƒ chuyá»ƒn tá»“n kho cá»§a sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang bÃ¡n tá»« vá»‹ trÃ­ há»‡ thá»‘ng `MAIN` sang cÃ¡c Ã´ lÆ°u hÃ ng active thuá»™c dÃ£y A/B.
- Do hiá»‡n cÃ³ 298 SKU/biáº¿n thá»ƒ Ä‘ang bÃ¡n nhÆ°ng chá»‰ cÃ³ 80 Ã´ A/B, cÃ¡c Ã´ lÆ°u hÃ ng A/B Ä‘Æ°á»£c báº­t `allow_mixed_sku = TRUE` Ä‘á»ƒ cho phÃ©p nhiá»u SKU trong cÃ¹ng má»™t Ã´.
- PhÃ¢n bá»• theo thá»© tá»± sáº£n pháº©m/danh má»¥c vÃ  xoay vÃ²ng qua 80 Ã´; sau khi cháº¡y local, dÃ£y A cÃ³ 160 dÃ²ng tá»“n/2.400 cÃ¡i, dÃ£y B cÃ³ 138 dÃ²ng tá»“n/2.070 cÃ¡i, `MAIN` cÃ²n 0 tá»“n.
- Äá»“ng bá»™ `location_id` cho serial/IMEI theo ká»‡ má»›i; Ä‘á»‘i soÃ¡t serial `IN_STOCK` cho tháº¥y 0 dÃ²ng lá»‡ch ká»‡ so vá»›i `inventory_levels`.

## Update 2026-06-18 - ThÃªm bá»™ lá»c chi tiáº¿t cho danh má»¥c ká»‡ hÃ ng

- API `GET /admin/inventory/locations` há»— trá»£ thÃªm bá»™ lá»c theo `aisle`, `shelf`, `bin` Ä‘á»ƒ lá»c trá»±c tiáº¿p theo cáº¥u trÃºc mÃ£ `DÃ£y-Ká»‡-Ã”`, vÃ­ dá»¥ `B-02-03`.
- Tab `Ká»‡ hÃ ng` trong mÃ n `Quáº£n lÃ½ tá»“n kho` cÃ³ thÃªm bá»™ lá»c mÃ£/tÃªn/khu, dÃ£y, ká»‡, Ã´, khu vá»±c, loáº¡i vÃ  tráº¡ng thÃ¡i.
- Verification: backend `py_compile` pass; frontend `npm run lint` pass; gá»i service lá»c dÃ£y B, ká»‡ 02, Ã´ 03 tráº£ Ä‘Ãºng `B-02-03`.

## Update 2026-06-18 - Bá»• sung dÃ£y B vÃ  chuáº©n hÃ³a nhÃ£n khu Ä‘áº·c biá»‡t

- DÃ£y B Ä‘Æ°á»£c seed theo cÃ¹ng mÃ´ hÃ¬nh vá»›i dÃ£y A: 10 ká»‡ x 4 Ã´, mÃ£ tá»« `B-01-01` Ä‘áº¿n `B-10-04`.
- ThÃªm migration `006_inventory_location_aisle_b_and_special_zone_labels.sql` Ä‘á»ƒ database hiá»‡n táº¡i tá»± bá»• sung Ä‘á»§ 40 vá»‹ trÃ­ active cho dÃ£y B.
- Chuáº©n hÃ³a nhÃ£n cÃ¡c khu Ä‘áº·c biá»‡t cho gá»n trÃªn báº£ng: `QC - Ã” 01`, `Báº£o hÃ nh - Ã” 01`, `HÃ ng lá»—i - Ã” 01`, `HÃ ng tráº£ - Ã” 01`; mÃ£ `QC-01`, `BH-01`, `ERR-01`, `RT-01` Ä‘Æ°á»£c giá»¯ nguyÃªn vÃ¬ Ä‘Ã¢y lÃ  khu chá»©c nÄƒng, khÃ´ng pháº£i dÃ£y lÆ°u hÃ ng.

## Update 2026-06-18 - Chuáº©n hÃ³a dÃ£y A theo mÃ´ hÃ¬nh 10 ká»‡ x 4 Ã´

- DÃ£y A Ä‘Æ°á»£c chuáº©n hÃ³a thÃ nh 10 ká»‡, má»—i ká»‡ cÃ³ 4 Ã´, theo mÃ£ `A-01-01` Ä‘áº¿n `A-10-04`.
- Baseline `init_database.sql` seed 40 vá»‹ trÃ­ active cho dÃ£y A theo Ä‘Ãºng quy Æ°á»›c `DÃ£y-Ká»‡-Ã”`.
- ThÃªm migration `005_inventory_location_aisle_a_10_shelves_4_bins.sql` Ä‘á»ƒ database hiá»‡n táº¡i tá»± bá»• sung Ä‘á»§ 40 vá»‹ trÃ­ vÃ  khÃ³a cÃ¡c mÃ£ cÅ© `A-01-05` Ä‘áº¿n `A-01-10` náº¿u chÆ°a cÃ³ tá»“n kho.

## Update 2026-06-18 - Sá»­a triá»‡t Ä‘á»ƒ cÃ¡c cá»™t chá»©a tiáº¿ng Viá»‡t bá»‹ lá»—i dáº¥u há»i trong database

- PhÃ¡t hiá»‡n vÃ  sá»­a lá»—i encoding mojibake (cÃ¡c chá»¯ tiáº¿ng Viá»‡t cÃ³ dáº¥u biáº¿n thÃ nh dáº¥u há»i `?` literal) trong 3 báº£ng database chÃ­nh: `inventory_adjustment_logs`, `inventory_document_lines` vÃ  `inventory_documents`.
- CÃ¡c giÃ¡ trá»‹ Ä‘Ã£ sá»­a:
  - `"Nh?p kho kh?i t?o"` -> `"Nháº­p kho khá»Ÿi táº¡o"` (298 dÃ²ng trong `inventory_adjustment_logs.reason`)
  - `"Kh?i t?o t?n kho th?t t? d? li?u s?n ph?m/bi?n th? hi?n c?."` -> `"Khá»Ÿi táº¡o tá»“n kho thá»±c táº¿ tá»« dá»¯ liá»‡u sáº£n pháº©m/biáº¿n thá»ƒ hiá»‡n cÃ³."` (298 dÃ²ng trong `inventory_adjustment_logs.note`)
  - `"T?n kho kh?i t?o t? d? li?u s?n ph?m"` -> `"Tá»“n kho khá»Ÿi táº¡o tá»« dá»¯ liá»‡u sáº£n pháº©m"` (298 dÃ²ng trong `inventory_adjustment_logs.supplier_name` vÃ  1 dÃ²ng trong `inventory_documents.supplier_name`)
  - `"D?ng nh?p kh?i t?o t? t?n catalog."` -> `"DÃ²ng nháº­p khá»Ÿi táº¡o tá»« tá»“n catalog."` (298 dÃ²ng trong `inventory_document_lines.note`)
  - `"Kh?i t?o t?n kho th?t t? to?n b? s?n ph?m/bi?n th? active, m?i d?ng 15 c?i."` -> `"Khá»Ÿi táº¡o tá»“n kho thá»±c táº¿ tá»« toÃ n bá»™ sáº£n pháº©m/biáº¿n thá»ƒ active, má»—i dÃ²ng 15 cÃ¡i."` (1 dÃ²ng trong `inventory_documents.note`)
- Verification: Cháº¡y truy váº¥n Ä‘á»‘i soÃ¡t dá»¯ liá»‡u thá»±c táº¿ cho tháº¥y cÃ¡c trÆ°á»ng nÃ y hiá»ƒn thá»‹ tiáº¿ng Viá»‡t cÃ³ dáº¥u chuáº©n 100%. Giao diá»‡n admin cá»§a Nháº­p kho vÃ  Quáº£n lÃ½ tá»“n kho khÃ´ng cÃ²n báº¥t ká»³ dáº¥u há»i lá»—i nÃ o.

## Update 2026-06-18 - Bá»• sung 10 vá»‹ trÃ­ ká»‡ cho dÃ£y A

- Baseline `init_database.sql` hiá»‡n seed Ä‘á»§ 10 vá»‹ trÃ­ lÆ°u hÃ ng bÃ¡n Ä‘Æ°á»£c cho dÃ£y A, tá»« `A-01-01` Ä‘áº¿n `A-01-10`.
- ThÃªm migration `004_inventory_location_aisle_a_shelves.sql` Ä‘á»ƒ database Ä‘Ã£ tá»“n táº¡i Ä‘Æ°á»£c bá»• sung cÃ¡c vá»‹ trÃ­ `A-01-03` Ä‘áº¿n `A-01-10` mÃ  khÃ´ng cáº§n táº¡o láº¡i database.
- CÃ¡c vá»‹ trÃ­ má»›i dÃ¹ng `purpose = STORAGE`, `zone = DÃ£y A`, `allow_mixed_sku = FALSE` vÃ  `sort_order` theo quy Æ°á»›c mÃ£ ká»‡ hiá»‡n cÃ³.

## Update 2026-06-18 - Kiá»ƒm kÃª theo danh sÃ¡ch chá»n hoáº·c toÃ n bá»™

- MÃ n `Quáº£n lÃ½ tá»“n kho` bá»• sung checkbox chá»n dÃ²ng tá»“n kho Ä‘á»ƒ láº­p phiáº¿u kiá»ƒm kÃª theo danh sÃ¡ch Ä‘Ã£ chá»n.
- NÃºt kiá»ƒm kÃª Ä‘Æ°á»£c tÃ¡ch thÃ nh `Kiá»ƒm kÃª Ä‘Ã£ chá»n` vÃ  `Kiá»ƒm kÃª toÃ n bá»™`; kiá»ƒm kÃª toÃ n bá»™ sáº½ táº£i táº¥t cáº£ trang tá»“n kho theo bá»™ lá»c hiá»‡n táº¡i thay vÃ¬ chá»‰ dÃ¹ng trang Ä‘ang hiá»ƒn thá»‹.
- Popup táº¡o phiáº¿u kiá»ƒm kÃª giá»¯ nguyÃªn danh sÃ¡ch dÃ²ng Ä‘Ã£ chá»n/toÃ n bá»™ Ä‘á»ƒ admin nháº­p `Thá»±c Ä‘áº¿m` trÆ°á»›c khi táº¡o phiáº¿u.
- TÄƒng giá»›i háº¡n payload kiá»ƒm kÃª tá»« 300 lÃªn 1000 dÃ²ng Ä‘á»ƒ trÃ¡nh káº¹t khi kiá»ƒm kÃª toÃ n bá»™ cÃ³ thÃªm sáº£n pháº©m/biáº¿n thá»ƒ trong tÆ°Æ¡ng lai.
- Verification: frontend `npm run lint` thÃ nh cÃ´ng; backend `py_compile` cho schema inventory, service inventory vÃ  repository inventory thÃ nh cÃ´ng.

## Update 2026-06-18 - Sá»­a lá»—i mÃ£ hÃ³a vá»‹ trÃ­ kho trong phiáº¿u nháº­p khá»Ÿi táº¡o

- Sá»­a dá»¯ liá»‡u local bá»‹ lÆ°u sai `Kho ch?nh` thÃ nh `Kho chÃ­nh` trong `inventory_adjustment_logs.location_name` vÃ  `inventory_document_lines.metadata.storageLocationName` cá»§a phiáº¿u nháº­p khá»Ÿi táº¡o.
- NguyÃªn nhÃ¢n thao tÃ¡c dá»¯ liá»‡u trÆ°á»›c Ä‘Ã³ truyá»n literal tiáº¿ng Viá»‡t qua PowerShell lÃ m máº¥t kÃ½ tá»± `Ã­`; khi cáº­p nháº­t dá»¯ liá»‡u tiáº¿ng Viá»‡t tá»« script cáº§n truyá»n chuá»—i Unicode qua parameter hoáº·c dÃ¹ng escape Unicode.
- Verification: `inventory_service.list_inventory_receipts` tráº£ `storageLocationName = "Kho chÃ­nh"` vÃ  `locationName = "Kho chÃ­nh"` cho phiáº¿u `NK-KHOI-TAO-20260615-0001`.

## Update 2026-06-18 - Chuáº©n hÃ³a phiáº¿u nháº­p kho khá»Ÿi táº¡o theo toÃ n bá»™ biáº¿n thá»ƒ active

- TÃ¡i táº¡o dá»¯ liá»‡u local cá»§a phiáº¿u `NK-KHOI-TAO-20260615-0001` Ä‘á»ƒ bao phá»§ toÃ n bá»™ sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang active: 290 biáº¿n thá»ƒ vÃ  8 sáº£n pháº©m active khÃ´ng cÃ³ biáº¿n thá»ƒ.
- Má»—i dÃ²ng nháº­p khá»Ÿi táº¡o Ä‘Æ°á»£c Ä‘áº·t sá»‘ lÆ°á»£ng 15 cÃ¡i, trÃ¡nh tÃ¬nh tráº¡ng má»™t láº§n nháº­p khá»Ÿi táº¡o ghi 25-45 cÃ¡i hoáº·c nhiá»u hÆ¡n cho má»™t biáº¿n thá»ƒ.
- Äá»“ng bá»™ láº¡i `inventory_document_lines`, `inventory_adjustment_logs`, `inventory_levels`, tá»“n kho biáº¿n thá»ƒ/sáº£n pháº©m cha vÃ  danh sÃ¡ch serial number theo cÃ¹ng má»©c 15 cÃ¡i má»—i dÃ²ng.
- Sau Ä‘iá»u chá»‰nh, phiáº¿u cÃ³ 298 dÃ²ng, tá»•ng sá»‘ lÆ°á»£ng 4.470 vÃ  tá»•ng giÃ¡ trá»‹ 89.685.600.000Ä‘.
- Verification: gá»i trá»±c tiáº¿p `inventory_service.list_inventory_receipts` tráº£ `lineCount = 298`, `totalQuantity = 4470`; truy váº¥n Ä‘á»‘i soÃ¡t cho tháº¥y thiáº¿u 0 dÃ²ng active, sai sá»‘ lÆ°á»£ng 0 dÃ²ng vÃ  má»i dÃ²ng Ä‘á»u cÃ³ 15 serial.

## Update 2026-06-18 - Lá»c ká»‡ nháº­p kho theo lÃ½ do nháº­p

- Form láº­p phiáº¿u nháº­p kho lá»c danh sÃ¡ch ká»‡ theo `receiptReasonCode` vÃ  `purpose` cá»§a ká»‡ hÃ ng.
- Nháº­p mua, chuyá»ƒn kho, sáº£n xuáº¥t, khá»Ÿi táº¡o vÃ  Ä‘iá»u chá»‰nh tÄƒng Æ°u tiÃªn ká»‡ `STORAGE`; khÃ¡ch tráº£ hÃ ng Æ°u tiÃªn `RETURN`/`QC`; nháº­p báº£o hÃ nh Æ°u tiÃªn `WARRANTY`; nhÃ  cung cáº¥p tráº£/bá»• sung hÃ ng Æ°u tiÃªn `STORAGE`/`QC`; nháº­p khÃ¡c cho chá»n táº¥t cáº£ ká»‡ Ä‘ang hoáº¡t Ä‘á»™ng.
- Khi Ä‘á»•i lÃ½ do nháº­p, náº¿u dÃ²ng phiáº¿u Ä‘ang chá»n ká»‡ khÃ´ng cÃ²n phÃ¹ há»£p vá»›i nhÃ³m lÃ½ do má»›i thÃ¬ frontend tá»± bá» chá»n ká»‡ Ä‘Ã³ Ä‘á»ƒ ngÆ°á»i dÃ¹ng chá»n láº¡i Ä‘Ãºng nhÃ³m.
- Verification: frontend `npm run lint` vÃ  backend `py_compile` thÃ nh cÃ´ng.

## Update 2026-06-18 - Sá»­a lá»—i ledger vÃ  modal IMEI/serial 500

- Sá»­a router `GET /admin/inventory/ledger` tráº£ kiá»ƒu `dict` Ä‘á»ƒ khá»›p response phÃ¢n trang `{items, page, pageSize, total, totalPages}`, trÃ¡nh lá»—i FastAPI response validation khi tab sá»• kho táº£i dá»¯ liá»‡u.
- Bá»• sung migration `003_inventory_identifier_locations.sql` thÃªm `location_id` cho `product_imeis` vÃ  `product_serial_numbers`, backfill vá»‹ trÃ­ tá»« dÃ²ng phiáº¿u nháº­p hoáº·c `inventory_levels` hiá»‡n cÃ³.
- Modal IMEI/serial trong tá»“n kho Ä‘á»c Ä‘Æ°á»£c vá»‹ trÃ­ ká»‡ cá»§a mÃ£ Ä‘á»‹nh danh mÃ  khÃ´ng cÃ²n lá»—i thiáº¿u cá»™t `product_imeis.location_id`.
- Verification: cháº¡y migration local, gá»i trá»±c tiáº¿p service ledger tráº£ 50/290 dÃ²ng vÃ  service identifiers tráº£ dá»¯ liá»‡u serial thÃ nh cÃ´ng; backend `py_compile` thÃ nh cÃ´ng.

## Update 2026-06-18 - Sá»­a lá»—i ká»‡ hÃ ng 500 vÃ  á»•n Ä‘á»‹nh hook admin

- Bá»• sung migration `001_inventory_location_master_columns.sql` Ä‘á»ƒ database Ä‘Ã£ khá»Ÿi táº¡o trÆ°á»›c Ä‘Ã³ cÃ³ Ä‘á»§ metadata ká»‡ hÃ ng: `zone`, `description`, `purpose`, `sort_order`, `allow_mixed_sku` vÃ  seed cÃ¡c ká»‡ máº«u.
- Bá»• sung migration `002_inventory_location_main_sort_order.sql` Ä‘á»ƒ ká»‡ máº·c Ä‘á»‹nh `MAIN` luÃ´n Ä‘á»©ng Ä‘áº§u danh sÃ¡ch.
- Sá»­a truy váº¥n `list_inventory_locations` khÃ´ng cÃ²n truyá»n `NULL` vÃ o tham sá»‘ tÃ¬m kiáº¿m, trÃ¡nh lá»—i asyncpg `could not determine data type of parameter` khi gá»i `GET /admin/inventory/locations?includeInactive=true`.
- ÄÆ°a hook phÃ¢n quyá»n trong `useAdminLogic` lÃªn trÆ°á»›c cÃ¡c logic/memo phá»¥ thuá»™c Ä‘á»ƒ trÃ¡nh cáº£nh bÃ¡o React Ä‘á»•i thá»© tá»± hook trong mÃ n admin sau khi hot reload.
- Verification: cháº¡y migration local, gá»i trá»±c tiáº¿p service `list_inventory_locations` tráº£ dá»¯ liá»‡u thÃ nh cÃ´ng, backend `py_compile` vÃ  frontend `npm run lint` Ä‘á»u thÃ nh cÃ´ng.

## Update 2026-06-18 - PhÃ¢n trang tá»“n kho vÃ  phiáº¿u nháº­p

- API `GET /admin/inventory/levels` vÃ  `GET /admin/inventory/receipts` há»— trá»£ `page` vÃ  `pageSize`, máº·c Ä‘á»‹nh 50 dÃ²ng/trang vÃ  tá»‘i Ä‘a 100 dÃ²ng/trang.
- Káº¿t quáº£ hai API tráº£ vá» `items`, `page`, `pageSize`, `total` vÃ  `totalPages` Ä‘á»ƒ frontend hiá»ƒn thá»‹ Ä‘Ãºng tá»•ng sá»‘ báº£n ghi.
- Bá»™ lá»c tráº¡ng thÃ¡i phiáº¿u nháº­p Ä‘Æ°á»£c chuyá»ƒn vÃ o request backend Ä‘á»ƒ phÃ¢n trang khÃ´ng táº¡o ra cÃ¡c trang trá»‘ng hoáº·c thiáº¿u dÃ²ng phÃ¹ há»£p.
- Bá»™ lá»c danh má»¥c vÃ  thÆ°Æ¡ng hiá»‡u tá»“n kho cÅ©ng Ä‘Æ°á»£c Ã¡p dá»¥ng trÆ°á»›c khi tÃ­nh tá»•ng vÃ  chia trang, trÃ¡nh bá» sÃ³t dá»¯ liá»‡u phÃ¹ há»£p náº±m á»Ÿ trang khÃ¡c.
- MÃ n `Quáº£n lÃ½ tá»“n kho` vÃ  `Quáº£n lÃ½ nháº­p kho` cÃ³ nÃºt `Trang trÆ°á»›c` / `Trang sau`, chá»‰ bÃ¡o trang hiá»‡n táº¡i vÃ  khoáº£ng báº£n ghi Ä‘ang hiá»ƒn thá»‹.
- Khi tÃ¬m kiáº¿m hoáº·c Ã¡p dá»¥ng/xÃ³a bá»™ lá»c, danh sÃ¡ch quay vá» trang Ä‘áº§u tiÃªn.
- Verification: backend `py_compile` vÃ  frontend `npm run lint` Ä‘á»u thÃ nh cÃ´ng.

## Update 2026-06-18 - ÄÆ°a bá»™ lá»c xuá»‘ng dÆ°á»›i tá»•ng quan

- MÃ n `Quáº£n lÃ½ tá»“n kho` hiá»ƒn thá»‹ dashboard tá»•ng quan trÆ°á»›c, sau Ä‘Ã³ má»›i Ä‘áº¿n bá»™ lá»c danh má»¥c, thÆ°Æ¡ng hiá»‡u, tráº¡ng thÃ¡i tá»“n, ká»‡ hÃ ng vÃ  tÃ¬m kiáº¿m.
- MÃ n `Quáº£n lÃ½ nháº­p kho` hiá»ƒn thá»‹ khá»‘i tá»•ng quan nháº­p kho/nhÃ  cung cáº¥p trÆ°á»›c, sau Ä‘Ã³ má»›i Ä‘áº¿n tÃ¬m kiáº¿m, khoáº£ng ngÃ y vÃ  tráº¡ng thÃ¡i phiáº¿u.
- Chá»‰ thay Ä‘á»•i vá»‹ trÃ­ hiá»ƒn thá»‹; hÃ nh vi lá»c vÃ  phÃ¢n trang giá»¯ nguyÃªn.
- Verification: frontend `npm run lint` thÃ nh cÃ´ng vÃ  ná»™i dung tiáº¿ng Viá»‡t má»›i khÃ´ng cÃ³ dáº¥u hiá»‡u lá»—i mÃ£ hÃ³a.

## Update 2026-06-18 - Hiá»ƒn thá»‹ biáº¿n thá»ƒ trong dashboard tá»“n kho

- Danh sÃ¡ch `Top tá»“n nhiá»u` vÃ  `Top cáº§n nháº­p thÃªm` hiá»ƒn thá»‹ mÃ u sáº¯c vÃ  cáº¥u hÃ¬nh biáº¿n thá»ƒ dÆ°á»›i tÃªn sáº£n pháº©m Ä‘á»ƒ phÃ¢n biá»‡t cÃ¡c dÃ²ng cÃ¹ng sáº£n pháº©m; khÃ´ng hiá»ƒn thá»‹ SKU.
- Sáº£n pháº©m khÃ´ng cÃ³ biáº¿n thá»ƒ khÃ´ng hiá»ƒn thá»‹ dÃ²ng thÃ´ng tin phá»¥.
- Dashboard tá»“n kho tiáº¿p tá»¥c tá»•ng há»£p trÃªn toÃ n bá»™ read-model thay vÃ¬ dÃ¹ng response Ä‘Ã£ phÃ¢n trang cá»§a báº£ng tá»“n kho.

## Update 2026-06-18 - TÃ¡ch tab vÃ  phÃ¢n trang sá»• kho

- `Sá»• kho / lá»‹ch sá»­ biáº¿n Ä‘á»™ng tá»“n` Ä‘Æ°á»£c tÃ¡ch thÃ nh tab con `Sá»• kho` cáº¡nh `Tá»“n kho` vÃ  `Ká»‡ hÃ ng`, khÃ´ng cÃ²n kÃ©o dÃ i ná»™i dung cá»§a danh sÃ¡ch tá»“n kho.
- API sá»• kho há»— trá»£ `page` vÃ  `pageSize`, máº·c Ä‘á»‹nh 50 biáº¿n Ä‘á»™ng/trang.
- Tab sá»• kho cÃ³ Ä‘iá»u khiá»ƒn trang trÆ°á»›c/sau, tá»•ng sá»‘ biáº¿n Ä‘á»™ng vÃ  khoáº£ng dá»¯ liá»‡u Ä‘ang hiá»ƒn thá»‹.

## Update 2026-06-18 - Chuáº©n hÃ³a ká»‡ hÃ ng trong kho

- NÃ¢ng cáº¥p `inventory_locations` thÃ nh danh má»¥c ká»‡ hÃ ng quáº£n trá»‹ Ä‘Æ°á»£c, bá»• sung `zone` vÃ  `description`, seed cÃ¡c ká»‡ máº«u `KE-A1`, `KE-B1`, `TU-01` bÃªn cáº¡nh `MAIN / Kho chÃ­nh`.
- ThÃªm API quáº£n lÃ½ ká»‡ hÃ ng: `GET/POST/PUT /admin/inventory/locations` vÃ  `PATCH /admin/inventory/locations/{location_id}/status`.
- Backend chuáº©n hÃ³a mÃ£ ká»‡, cháº·n trÃ¹ng mÃ£, cháº·n khÃ³a ká»‡ máº·c Ä‘á»‹nh vÃ  cháº·n khÃ³a ká»‡ cÃ²n tá»“n kho.
- DÃ²ng phiáº¿u nháº­p nháº­n thÃªm `warehouseLocationId`; backend Æ°u tiÃªn ká»‡ Ä‘Æ°á»£c chá»n tá»« danh má»¥c, váº«n fallback theo `storageLocationCode` cho dá»¯ liá»‡u cÅ©.
- Khi hoÃ n táº¥t phiáº¿u nháº­p, há»‡ thá»‘ng cá»™ng `inventory_levels` theo Ä‘Ãºng ká»‡ cá»§a tá»«ng dÃ²ng vÃ  gÃ¡n `location_id` cho cÃ¡c IMEI/serial number thá»±c nháº­n.
- Bá»• sung migration `072_inventory_locations_master_data.sql` Ä‘á»ƒ thÃªm metadata ká»‡, backfill vá»‹ trÃ­ IMEI/serial tá»« dÃ²ng phiáº¿u nháº­p vÃ  táº¡o index tra cá»©u theo ká»‡/tráº¡ng thÃ¡i.
- Frontend mÃ n `Quáº£n lÃ½ tá»“n kho` cÃ³ khá»‘i danh má»¥c ká»‡ hÃ ng Ä‘á»ƒ thÃªm/sá»­a/khÃ³a/má»Ÿ ká»‡; bá»™ lá»c vá»‹ trÃ­ Ä‘á»•i sang chá»n ká»‡ tá»« danh má»¥c.
- MÃ n `Quáº£n lÃ½ tá»“n kho` tÃ¡ch tab con `Tá»“n kho` vÃ  `Ká»‡ hÃ ng`, giá»¯ ká»‡ hÃ ng trong cÃ¹ng module tá»“n kho nhÆ°ng khÃ´ng trá»™n láº«n vá»›i báº£ng SKU/sá»• kho.
- Form phiáº¿u nháº­p Ä‘á»•i vá»‹ trÃ­ dÃ²ng phiáº¿u tá»« nháº­p text tá»± do sang combobox chá»n ká»‡ hÃ ng, giÃºp dá»¯ liá»‡u ká»‡ thá»‘ng nháº¥t vÃ  phá»¥c vá»¥ truy váº¿t IMEI/serial khi xuáº¥t kho sau nÃ y.
- Danh sÃ¡ch IMEI/serial trong tá»“n kho hiá»ƒn thá»‹ thÃªm ká»‡ hiá»‡n táº¡i cá»§a tá»«ng mÃ£ Ä‘á»‹nh danh.
- Bá»• sung API `GET /admin/inventory/issue-suggestions` Ä‘á»ƒ gá»£i Ã½ xuáº¥t kho theo ká»‡: vá»›i hÃ ng cÃ³ IMEI/serial, FIFO láº¥y tá»« mÃ£ Ä‘á»‹nh danh cÃ²n `IN_STOCK`; vá»›i hÃ ng khÃ´ng Ä‘á»‹nh danh, há»‡ thá»‘ng gá»£i Ã½ tá»« tá»“n kháº£ dá»¥ng theo ká»‡.
- Frontend cÃ³ nÃºt `Gá»£i Ã½ xuáº¥t` trÃªn dÃ²ng tá»“n kho kháº£ dá»¥ng, hiá»ƒn thá»‹ ká»‡ nÃªn láº¥y, sá»‘ lÆ°á»£ng gá»£i Ã½ vÃ  danh sÃ¡ch IMEI/serial Ä‘á» xuáº¥t náº¿u cÃ³.
- Modal `Bá»• sung IMEI/serial number` cÃ³ thÃªm cháº¿ Ä‘á»™ quÃ©t mÃ£ liÃªn tá»¥c: mÃ¡y quÃ©t nháº­p mÃ£ rá»“i Enter sáº½ tá»± thÃªm vÃ o danh sÃ¡ch, cháº·n trÃ¹ng trong frontend vÃ  khÃ´ng cho vÆ°á»£t sá»‘ lÆ°á»£ng dá»± kiáº¿n; backend váº«n validate láº§n cuá»‘i khi xÃ¡c nháº­n.
- Danh má»¥c ká»‡ hÃ ng bá»• sung phÃ¢n loáº¡i vá»‹ trÃ­ `STORAGE`/`QC`/`WARRANTY`/`DAMAGED`/`RETURN`/`VIRTUAL`, `sortOrder` Ä‘á»ƒ sáº¯p xáº¿p Ä‘Æ°á»ng láº¥y hÃ ng vÃ  `allowMixedSku` Ä‘á»ƒ ghi nháº­n ká»‡ cÃ³ cho phÃ©p nhiá»u SKU hay khÃ´ng.
- Quy Æ°á»›c mÃ£ ká»‡ chuyá»ƒn sang dáº¡ng `A-01-01`, `B-01-01`, `QC-01`, `BH-01`, `ERR-01`, `RT-01`; migration seed sáºµn cÃ¡c vá»‹ trÃ­ máº«u theo nhÃ³m lÆ°u hÃ ng, kiá»ƒm tra cháº¥t lÆ°á»£ng, báº£o hÃ nh, hÃ ng lá»—i vÃ  hÃ ng tráº£.

## Update 2026-06-17 - Bá»• sung WMS nháº¹ cho quy trÃ¬nh nháº­p kho Ä‘á»“ Ã¡n

- MÃ n `Quáº£n lÃ½ tá»“n kho` cÃ³ thÃªm dashboard: tá»•ng SKU theo dÃµi, sá»‘ SKU sáº¯p háº¿t, giÃ¡ trá»‹ tá»“n kho, SKU Ä‘ang giá»¯ hÃ ng, top tá»“n nhiá»u vÃ  top cáº§n nháº­p thÃªm.
- API `GET /admin/inventory/dashboard` tá»•ng há»£p dashboard tá»« read-model tá»“n kho hiá»‡n táº¡i.
- API `GET /admin/inventory/ledger` tráº£ sá»• kho/lá»‹ch sá»­ biáº¿n Ä‘á»™ng tá»« `inventory_adjustment_logs`, há»— trá»£ lá»c theo tÃ¬m kiáº¿m, sáº£n pháº©m, khoáº£ng ngÃ y vÃ  loáº¡i giao dá»‹ch `RECEIPT`/`SALE`/`ADJUSTMENT`/`RETURN`/`REVERSAL`.
- API `GET /admin/inventory/levels` nháº­n thÃªm `stockFilter` vÃ  `location` Ä‘á»ƒ lá»c hÃ ng sáº¯p háº¿t, cÃ²n tá»“n, Ä‘ang giá»¯ vÃ  theo vá»‹ trÃ­/ká»‡.
- Snapshot tá»“n kho tráº£ thÃªm `locations` tá»« `inventory_levels`, giÃºp UI lá»c vÃ  hiá»ƒn thá»‹ vá»‹ trÃ­/ká»‡ cÃ³ tá»“n.
- MÃ n `Quáº£n lÃ½ nháº­p kho` cÃ³ thÃªm bá»™ lá»c khoáº£ng thá»i gian `Tá»« ngÃ y` / `Äáº¿n ngÃ y`; API `GET /admin/inventory/receipts` nháº­n `dateFrom` vÃ  `dateTo`, lá»c theo ngÃ y táº¡o phiáº¿u cho cáº£ chá»©ng tá»« nháº­p má»›i vÃ  receipt legacy tá»« log.
- Phiáº¿u nháº­p kho cÃ³ thÃªm metadata nghiá»‡p vá»¥: chá»©ng tá»« Ä‘Ã­nh kÃ¨m, biÃªn báº£n sai lá»‡ch, tráº¡ng thÃ¡i kiá»ƒm tra cháº¥t lÆ°á»£ng, ghi chÃº QC, tráº¡ng thÃ¡i cÃ¡ch ly vÃ  vá»‹ trÃ­ cÃ¡ch ly.
- DÃ²ng phiáº¿u nháº­p cÃ³ thÃªm vá»‹ trÃ­ lÆ°u kho Ä‘Æ¡n giáº£n báº±ng `storageLocationCode` vÃ  `storageLocationName`, phÃ¹ há»£p má»©c `Kho chÃ­nh`, `Ká»‡ A1`, `Ká»‡ B2` thay vÃ¬ triá»ƒn khai slotting WMS Ä‘áº§y Ä‘á»§.
- Vá»‹ trÃ­ dÃ²ng phiáº¿u nay Ä‘Æ°á»£c dÃ¹ng lÃ m `inventory_document_lines.location_id`; khi hoÃ n táº¥t hoáº·c Ä‘áº£o phiáº¿u, `inventory_levels` Ä‘Æ°á»£c cá»™ng/trá»« theo vá»‹ trÃ­ dÃ²ng thay vÃ¬ chá»‰ dÃ¹ng kho header.
- Upload chá»©ng tá»« nháº­p kho dÃ¹ng folder `inventory` trong API upload hiá»‡n cÃ³, cho phÃ©p áº£nh vÃ  tÃ i liá»‡u PDF/DOC/DOCX/XLS/XLSX.
- Bá»• sung API `PATCH /admin/inventory/receipts/{reference_code}/quality` Ä‘á»ƒ cáº­p nháº­t QC/cÃ¡ch ly riÃªng, khÃ´ng cáº§n sá»­a láº¡i toÃ n bá»™ phiáº¿u nháº­p.
- Migration `071_inventory_receipt_wms_lightweight_metadata.sql` bá»• sung `inventory_documents.metadata` vÃ  index tra cá»©u QC/vá»‹ trÃ­.
- Backend cháº·n hoÃ n táº¥t phiáº¿u nháº­p náº¿u QC chÆ°a `PASSED` hoáº·c phiáº¿u cÃ²n Ä‘Ã¡nh dáº¥u cÃ¡ch ly, trÃ¡nh cáº­p nháº­t hÃ ng lá»—i vÃ o tá»“n kháº£ dá»¥ng.
- API `GET /admin/inventory/receipts/report` tráº£ bÃ¡o cÃ¡o nháº­p kho theo ngÃ y, theo thÃ¡ng vÃ  thá»‘ng kÃª nhÃ  cung cáº¥p gá»“m sá»‘ láº§n nháº­p, sá»‘ phiáº¿u sai lá»‡ch, sá»‘ láº§n QC khÃ´ng Ä‘áº¡t vÃ  tá»· lá»‡ lá»—i.
- Frontend mÃ n `Quáº£n lÃ½ nháº­p kho` hiá»ƒn thá»‹ QC/cÃ¡ch ly, chá»©ng tá»«, biÃªn báº£n sai lá»‡ch, vá»‹ trÃ­ ká»‡ vÃ  khá»‘i thá»‘ng kÃª nhÃ  cung cáº¥p ngay trong tab nháº­p kho.

## Update 2026-06-17 - LiÃªn káº¿t giá»¯ hÃ ng Ä‘Æ¡n hÃ ng vá»›i tá»“n kho kháº£ dá»¥ng

- Luá»“ng Ä‘Æ¡n hÃ ng má»›i sá»­ dá»¥ng `inventory_reservations` Ä‘á»ƒ giá»¯ hÃ ng khi checkout, giÃºp mÃ n tá»“n kho phÃ¢n biá»‡t tá»“n váº­t lÃ½, tá»“n Ä‘ang giá»¯ vÃ  tá»“n cÃ³ thá»ƒ bÃ¡n.
- Tá»“n váº­t lÃ½ chá»‰ bá»‹ trá»« khi Ä‘Æ¡n chuyá»ƒn sang `SHIPPED`; cÃ¡c tráº¡ng thÃ¡i há»§y/thanh toÃ¡n lá»—i trÆ°á»›c khi giao chá»‰ giáº£i phÃ³ng giá»¯ hÃ ng.
- Backend giá»¯ tÆ°Æ¡ng thÃ­ch vá»›i Ä‘Æ¡n cÅ© tá»«ng trá»« tá»“n ngay lÃºc táº¡o Ä‘Æ¡n qua log `ORDER_CREATED`, trÃ¡nh trá»« tá»“n láº§n hai khi giao vÃ  váº«n hoÃ n tá»“n Ä‘Ãºng khi há»§y.

## Update 2026-06-17 - Thiáº¿t káº¿ láº¡i quyá»n nháº­p kho theo mÃ´ hÃ¬nh Super Admin duyá»‡t

- Bá»• sung migration `070_inventory_pending_inbound_identifiers.sql` Ä‘á»ƒ thÃªm tráº¡ng thÃ¡i `PENDING_INBOUND` cho IMEI/serial number.
- Khi staff xÃ¡c nháº­n IMEI/serial á»Ÿ bÆ°á»›c `PROCESSING_IMEI`, backend táº¡o báº£n ghi giá»¯ chá»— trong `product_imeis` vÃ  `product_serial_numbers` vá»›i `source_reference` lÃ  mÃ£ phiáº¿u nháº­p vÃ  tráº¡ng thÃ¡i `PENDING_INBOUND`.
- Khi phiáº¿u nháº­p Ä‘Æ°á»£c hoÃ n táº¥t, cÃ¡c mÃ£ `PENDING_INBOUND` Ä‘Ãºng phiáº¿u má»›i Ä‘Æ°á»£c chuyá»ƒn sang `IN_STOCK`; náº¿u mÃ£ khÃ´ng Ä‘Æ°á»£c giá»¯ chá»— Ä‘Ãºng phiáº¿u thÃ¬ backend cháº·n hoÃ n táº¥t.
- Khi phiáº¿u Ä‘Ã£ gá»­i duyá»‡t bá»‹ tráº£ vá» nhÃ¡p Ä‘á»ƒ sá»­a hoáº·c bá»‹ há»§y, cÃ¡c mÃ£ `PENDING_INBOUND` cá»§a phiáº¿u Ä‘Æ°á»£c giáº£i phÃ³ng Ä‘á»ƒ trÃ¡nh rÃ¡c dá»¯ liá»‡u vÃ  trÃ¡nh giá»¯ mÃ£ sai sau khi Ä‘á»•i dÃ²ng phiáº¿u.
- Frontend tá»“n kho hiá»ƒn thá»‹ tráº¡ng thÃ¡i mÃ£ `PENDING_INBOUND` lÃ  `Chá» nháº­p kho`.
- MÃ´ hÃ¬nh váº­n hÃ nh hiá»‡n táº¡i khÃ´ng cÃ³ vai trÃ² káº¿ toÃ¡n riÃªng; `SUPER_ADMIN` lÃ  quáº£n lÃ½ cáº¥p cao nháº¥t vÃ  chá»‹u trÃ¡ch nhiá»‡m cÃ¡c quyáº¿t Ä‘á»‹nh kho cÃ³ rá»§i ro.
- `STAFF_ADMIN` giá»¯ cÃ¡c thao tÃ¡c cÆ¡ báº£n: xem tá»“n kho, táº¡o phiáº¿u nháº­p, sá»­a phiáº¿u á»Ÿ tráº¡ng thÃ¡i `DRAFT`/`PROCESSING_IMEI`, xá»­ lÃ½ IMEI/serial, táº¡o yÃªu cáº§u Ä‘iá»u chá»‰nh hoáº·c kiá»ƒm kÃª náº¿u Ä‘Æ°á»£c cáº¥p quyá»n tÆ°Æ¡ng á»©ng.
- CÃ¡c quyáº¿t Ä‘á»‹nh quáº£n lÃ½ gá»“m duyá»‡t phiáº¿u nháº­p, hoÃ n táº¥t phiáº¿u Ä‘á»ƒ cáº­p nháº­t tá»“n, há»§y phiáº¿u Ä‘Ã£ Ä‘i vÃ o quy trÃ¬nh, Ä‘áº£o phiáº¿u nháº­p, duyá»‡t kiá»ƒm kÃª, duyá»‡t Ä‘iá»u chá»‰nh tá»“n vÃ  duyá»‡t chá»‰nh sá»­a IMEI/serial chá»‰ dÃ nh cho `SUPER_ADMIN`.
- Hai endpoint Ä‘iá»u chá»‰nh tá»“n trá»±c tiáº¿p theo sáº£n pháº©m/biáº¿n thá»ƒ Ä‘Æ°á»£c khÃ³a vá» `SUPER_ADMIN`; staff pháº£i Ä‘i qua phiáº¿u Ä‘iá»u chá»‰nh tá»“n cÃ³ duyá»‡t Ä‘á»ƒ trÃ¡nh bá» qua chá»©ng tá»«.
- Endpoint Ä‘á»•i tráº¡ng thÃ¡i phiáº¿u nháº­p váº«n dÃ¹ng quyá»n váº­n hÃ nh `inventory:adjust` Ä‘á»ƒ staff cÃ³ thá»ƒ chuyá»ƒn phiáº¿u tá»« `DRAFT` sang `PROCESSING_IMEI`; service cháº·n cÃ¡c tráº¡ng thÃ¡i `APPROVED`, `COMPLETED`, `CANCELLED` náº¿u ngÆ°á»i gá»i khÃ´ng pháº£i `SUPER_ADMIN`.
- Migration `069_inventory_super_admin_approval_scope.sql` rÃºt quyá»n `inventory:approve` vÃ  `inventory:reserve` khá»i role `STAFF_ADMIN`, Ä‘á»“ng thá»i báº£o Ä‘áº£m `SUPER_ADMIN` cÃ³ cÃ¡c quyá»n quyáº¿t Ä‘á»‹nh kho.
- Frontend mÃ n `Quáº£n lÃ½ nháº­p kho` chá»‰ hiá»ƒn thá»‹ nÃºt duyá»‡t, hoÃ n táº¥t, há»§y vÃ  Ä‘áº£o phiáº¿u cho Super Admin; staff chá»‰ tháº¥y cÃ¡c thao tÃ¡c phÃ¹ há»£p vá»›i vai trÃ² váº­n hÃ nh.
- Náº¿u phiáº¿u Ä‘Ã£ á»Ÿ `PENDING_APPROVAL`, `PENDING_SHORTAGE_APPROVAL` hoáº·c `APPROVED` mÃ  cáº§n sá»­a, chá»‰ Super Admin Ä‘Æ°á»£c tráº£ phiáº¿u vá» `DRAFT`; thao tÃ¡c nÃ y tiáº¿p tá»¥c ghi audit theo cÆ¡ cháº¿ reset phiáº¿u hiá»‡n cÃ³.
- ChÆ°a Ä‘Æ°a PO/GRN/invoice matching, káº¿ toÃ¡n giÃ¡ vá»‘n Ä‘áº§y Ä‘á»§ hoáº·c Ä‘a kho vÃ o pháº¡m vi vÃ¬ há»‡ thá»‘ng hiá»‡n táº¡i lÃ  cá»­a hÃ ng má»™t chi nhÃ¡nh, khÃ´ng cÃ³ module káº¿ toÃ¡n riÃªng.

## Update 2026-06-17 - Hiá»ƒn thá»‹ lá»—i xÃ¡c nháº­n IMEI/serial trong modal nháº­p kho

- Modal `Bá»• sung IMEI/serial number` nay báº¯t lá»—i khi gá»i API xÃ¡c nháº­n danh sÃ¡ch mÃ£ Ä‘á»‹nh danh vÃ  hiá»ƒn thá»‹ thÃ´ng bÃ¡o lá»—i ngay trong modal thay vÃ¬ Ä‘á»ƒ promise lá»—i vÄƒng ra console.
- Tráº¡ng thÃ¡i Ä‘ang gá»­i Ä‘Æ°á»£c khÃ³a nÃºt xÃ¡c nháº­n Ä‘á»ƒ trÃ¡nh báº¥m láº·p trong lÃºc backend Ä‘ang kiá»ƒm tra danh sÃ¡ch IMEI/serial.
- Quy táº¯c backend validate serial number khÃ´ng Ä‘á»•i: serial pháº£i cÃ³ Ä‘á»‹nh dáº¡ng há»£p lá»‡ theo `SERIAL_PATTERN`; cÃ¡c mÃ£ quÃ¡ ngáº¯n nhÆ° `Y`, `A`, `YA` váº«n bá»‹ tá»« chá»‘i vÃ  thÃ´ng bÃ¡o lá»—i Ä‘Æ°á»£c tráº£ vá» UI.

## Update 2026-06-16 - Siáº¿t chuáº©n doanh nghiá»‡p cho phiáº¿u nháº­p kho

- HoÃ n táº¥t vÃ  Ä‘áº£o phiáº¿u nháº­p kho nay kiá»ƒm tra serial number theo Ä‘Ãºng pháº¡m vi sáº£n pháº©m, Ä‘á»“ng bá»™ vá»›i migration unique `(product_id, serial_number)`. TrÃ¡nh cháº·n nháº§m hoáº·c Ä‘áº£o nháº§m khi hai sáº£n pháº©m khÃ¡c nhau cÃ³ cÃ¹ng serial number.
- Phiáº¿u nháº­p kho cháº·n trÃ¹ng dÃ²ng theo cáº·p sáº£n pháº©m/biáº¿n thá»ƒ trong cÃ¹ng chá»©ng tá»«, tÆ°Æ¡ng tá»± phiáº¿u kiá»ƒm kÃª vÃ  phiáº¿u Ä‘iá»u chá»‰nh, Ä‘á»ƒ trÃ¡nh cá»™ng tá»“n hoáº·c nháº­p mÃ£ Ä‘á»‹nh danh láº·p do thao tÃ¡c nháº§m.
- Bá»• sung audit nghiá»‡p vá»¥ vÃ o `security_audit_logs` cho cÃ¡c thao tÃ¡c táº¡o, sá»­a, xÃ³a, bá»• sung IMEI/serial, Ä‘á»•i tráº¡ng thÃ¡i vÃ  Ä‘áº£o phiáº¿u nháº­p kho. Audit lÆ°u mÃ£ phiáº¿u, tráº¡ng thÃ¡i trÆ°á»›c/sau, sá»‘ dÃ²ng vÃ  snapshot dÃ²ng chÃ­nh Ä‘á»ƒ truy váº¿t thay Ä‘á»•i chá»©ng tá»«.
- TÃ¡ch bÆ°á»›c nháº­p IMEI/serial khá»i bÆ°á»›c duyá»‡t: khi nháº­p Ä‘á»§ mÃ£ Ä‘á»‹nh danh, phiáº¿u chuyá»ƒn sang `PENDING_APPROVAL`; khi nháº­p thiáº¿u váº«n chuyá»ƒn sang `PENDING_SHORTAGE_APPROVAL`. Chá»‰ endpoint Ä‘á»•i tráº¡ng thÃ¡i vá»›i quyá»n `inventory:approve` má»›i Ä‘Æ°a phiáº¿u sang `APPROVED`.
- Backend cháº·n ngÆ°á»i láº­p phiáº¿u tá»± duyá»‡t phiáº¿u nháº­p kho Ä‘á»ƒ tÄƒng kiá»ƒm soÃ¡t phÃ¢n tÃ¡ch nhiá»‡m vá»¥.
- CÃ¡c thay Ä‘á»•i nÃ y chÆ°a thay tháº¿ phÃ¢n há»‡ mua hÃ ng Ä‘áº§y Ä‘á»§ nhÆ° PO/GRN/invoice matching, khÃ³a ká»³ káº¿ toÃ¡n hoáº·c rÃ ng buá»™c tÃ¡ch ngÆ°á»i táº¡o/ngÆ°á»i duyá»‡t; náº¿u triá»ƒn khai WMS/ERP hoÃ n chá»‰nh cáº§n thiáº¿t káº¿ riÃªng cÃ¡c luá»“ng Ä‘Ã³.

## Update 2026-06-16 - Dá»n báº£n revision khá»i tá»“n kho khá»Ÿi táº¡o

- XÃ³a cÃ¡c sáº£n pháº©m SKU `REV-%` cÃ²n sÃ³t trong database local vÃ¬ Ä‘Ã¢y lÃ  báº£n nhÃ¡p/chá»‰nh sá»­a Ä‘Ã£ duyá»‡t, khÃ´ng pháº£i sáº£n pháº©m nghiá»‡p vá»¥ hiá»‡n hÃ nh.
- TrÆ°á»›c khi xÃ³a Ä‘Ã£ kiá»ƒm tra khÃ´ng cÃ³ `order_items`, bundle/accessory, reservation hoáº·c transaction bÃ¡n hÃ ng tham chiáº¿u Ä‘áº¿n cÃ¡c báº£n `REV-%`.
- CÃ¡c dÃ²ng tá»“n kho phÃ¡t sinh tá»« báº£n revision trong phiáº¿u `NK-KHOI-TAO-20260615-0001` Ä‘Æ°á»£c loáº¡i bá» theo cascade: 13 sáº£n pháº©m, 64 biáº¿n thá»ƒ, 10 dÃ²ng phiáº¿u nháº­p, 10 log nháº­p kho, 13 dÃ²ng tá»“n kho vÃ  296 serial.
- Sau khi dá»n, phiáº¿u nháº­p khá»Ÿi táº¡o cÃ²n 290 dÃ²ng, tá»•ng sá»‘ lÆ°á»£ng 5.661 vÃ  tá»•ng tiá»n 73.178.390.000Ä‘; cÃ¡c SKU `REV-%` khÃ´ng cÃ²n trong báº£ng sáº£n pháº©m/tá»“n kho.
- Siáº¿t query read-model tá»“n kho vÃ  danh sÃ¡ch phiáº¿u nháº­p Ä‘á»ƒ loáº¡i sáº£n pháº©m `MERGED` hoáº·c `deleted_at IS NOT NULL`, trÃ¡nh báº£n revision cÅ© lá»t láº¡i vÃ o tá»“n kho/xuáº¥t phiáº¿u náº¿u cÃ²n dá»¯ liá»‡u lá»‹ch sá»­.

## Update 2026-06-16 - RÃ ng buá»™c sáº£n pháº©m Ä‘Æ°á»£c phÃ©p nháº­p kho

- Phiáº¿u nháº­p kho chá»‰ cho phÃ©p nháº­p sáº£n pháº©m tráº¡ng thÃ¡i `ACTIVE`, chÆ°a bá»‹ xÃ³a vÃ  khÃ´ng bá»‹ áº©n theo danh má»¥c/thÆ°Æ¡ng hiá»‡u.
- Náº¿u sáº£n pháº©m Ä‘ang `DISCONTINUED`, `INACTIVE`, `ARCHIVED`, `MERGED`, `DRAFT`, `REVISION_DRAFT`, `PENDING` hoáº·c tráº¡ng thÃ¡i khÃ¡c `ACTIVE`, backend tá»« chá»‘i táº¡o/sá»­a phiáº¿u nháº­p vá»›i lá»—i rÃµ theo tá»«ng dÃ²ng.
- Náº¿u sáº£n pháº©m gá»‘c Ä‘ang cÃ³ báº£n chá»‰nh sá»­a `REVISION_DRAFT` hoáº·c `PENDING` chÆ°a duyá»‡t/há»§y, backend tá»« chá»‘i nháº­p kho Ä‘á»ƒ trÃ¡nh nháº­p tá»“n theo dá»¯ liá»‡u sáº£n pháº©m chÆ°a á»•n Ä‘á»‹nh.
- Biáº¿n thá»ƒ Ä‘Æ°á»£c nháº­p kho pháº£i cÃ²n active, chÆ°a bá»‹ xÃ³a vÃ  khÃ´ng á»Ÿ tráº¡ng thÃ¡i `deleted`/`archived`; danh sÃ¡ch tá»± chá»n biáº¿n thá»ƒ cÅ©ng chá»‰ láº¥y biáº¿n thá»ƒ há»£p lá»‡.
- Frontend lá»c sáº£n pháº©m khÃ´ng há»£p lá»‡ khá»i picker nháº­p kho vÃ  cháº·n submit sá»›m vá»›i cÃ¡c tráº¡ng thÃ¡i UI biáº¿t Ä‘Æ°á»£c; backend váº«n lÃ  lá»›p kiá»ƒm soÃ¡t chÃ­nh cho trÆ°á»ng há»£p cÃ³ báº£n chá»‰nh sá»­a chá» duyá»‡t.

## Update 2026-06-16 - Máº«u in phiáº¿u nháº­p kho dáº¡ng chá»©ng tá»«

- Modal xem phiáº¿u nháº­p kho nay cÃ³ máº«u in riÃªng theo bá»‘ cá»¥c chá»©ng tá»« `Phiáº¿u nháº­p kho`: thÃ´ng tin Ä‘Æ¡n vá»‹, máº«u sá»‘, ngÃ y chá»©ng tá»«, sá»‘ phiáº¿u, nhÃ  cung cáº¥p/ngÆ°á»i giao hÃ ng, lÃ½ do nháº­p, kho nháº­n, ghi chÃº.
- Header phiáº¿u in dÃ¹ng tÃªn cá»­a hÃ ng `ELECTROMART VIá»†T NAM` vÃ  mÃ´ táº£ ngÃ nh hÃ ng cÃ´ng nghá»‡ thay cho placeholder chung.
- Báº£ng in dÃ¹ng cá»™t `STT`, tÃªn hÃ ng hÃ³a, mÃ£ sá»‘/SKU, Ä‘Æ¡n vá»‹ tÃ­nh, sá»‘ lÆ°á»£ng theo chá»©ng tá»«, thá»±c nháº­p, Ä‘Æ¡n giÃ¡ vÃ  thÃ nh tiá»n; dÃ²ng cuá»‘i cá»™ng tá»•ng sá»‘ lÆ°á»£ng vÃ  tá»•ng giÃ¡ trá»‹ nháº­p.
- Phiáº¿u in cÃ³ dÃ²ng `Tá»•ng sá»‘ tiá»n (Viáº¿t báº±ng chá»¯)` vÃ  khu vá»±c kÃ½ tÃªn cho ngÆ°á»i láº­p phiáº¿u, ngÆ°á»i giao hÃ ng, thá»§ kho, káº¿ toÃ¡n trÆ°á»Ÿng/bá»™ pháº­n cÃ³ nhu cáº§u nháº­p.
- Giao diá»‡n xem phiáº¿u trÃªn mÃ n hÃ¬nh váº«n giá»¯ nguyÃªn; khi báº¥m in chá»‰ hiá»‡n máº«u chá»©ng tá»« A4, trÃ¡nh in cáº£ modal quáº£n trá»‹.
- Bá»• sung xuáº¥t phiáº¿u dáº¡ng Word `.doc` báº±ng file HTML Ä‘á»™c láº­p vÃ  xuáº¥t PDF qua cá»­a sá»• chá»©ng tá»« Ä‘áº§y Ä‘á»§ Ä‘á»ƒ lÆ°u báº±ng `Save as PDF`; cáº£ hai dÃ¹ng dá»¯ liá»‡u chá»©ng tá»« Ä‘áº§y Ä‘á»§, khÃ´ng phá»¥ thuá»™c vÃ¹ng cuá»™n cá»§a modal.
- NÃ¢ng cáº¥p xuáº¥t file sang backend: thÃªm dependency `reportlab` vÃ  `python-docx`, module `document_export_service.py`, endpoint `GET /admin/inventory/receipts/{reference_code}/export?format=pdf|docx`. Frontend táº£i trá»±c tiáº¿p file `.pdf` hoáº·c `.docx` tá»« backend, phÃ¹ há»£p Ä‘á»ƒ tÃ¡i dÃ¹ng cho hÃ³a Ä‘Æ¡n khÃ¡ch hÃ ng sau nÃ y.
- Máº«u xuáº¥t PDF/DOCX bá» dÃ²ng tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh trong pháº§n tÃªn hÃ ng; pháº§n mÃ´ táº£ biáº¿n thá»ƒ hiá»ƒn thá»‹ `PhÃ¢n loáº¡i: mÃ u - cáº¥u hÃ¬nh` báº±ng tiáº¿ng Viá»‡t náº¿u cÃ³, cÃ²n SKU/mÃ£ hÃ ng chá»‰ náº±m á»Ÿ cá»™t `MÃ£ sá»‘`.
- TÄƒng Ä‘á»™ rá»™ng cá»™t `STT` trong máº«u PDF vÃ  máº«u in HTML Ä‘á»ƒ sá»‘ thá»© tá»± nhiá»u chá»¯ sá»‘ khÃ´ng bá»‹ tÃ¡ch xuá»‘ng dÃ²ng.
- Bá» khá»‘i `Máº«u sá»‘: 01 - VT / Theo dÃµi nháº­p kho ná»™i bá»™` khá»i header phiáº¿u, Ä‘á»“ng thá»i bá» nhÃ£n `PhÃ¢n loáº¡i:` trong pháº§n tÃªn hÃ ng; náº¿u cÃ³ mÃ u/cáº¥u hÃ¬nh thÃ¬ chá»‰ hiá»ƒn thá»‹ trá»±c tiáº¿p giÃ¡ trá»‹ mÃ u/cáº¥u hÃ¬nh.
- Khi xuáº¥t PDF/DOCX, cÃ¡c dÃ²ng cÃ¹ng tÃªn sáº£n pháº©m, SKU biáº¿n thá»ƒ, mÃ u/cáº¥u hÃ¬nh, Ä‘Æ¡n vá»‹ tÃ­nh vÃ  Ä‘Æ¡n giÃ¡ Ä‘Æ°á»£c gá»™p láº¡i Ä‘á»ƒ trÃ¡nh chá»©ng tá»« hiá»ƒn thá»‹ nhiá»u dÃ²ng giá»‘ng nhau do dá»¯ liá»‡u catalog cÃ³ báº£n ghi sáº£n pháº©m/biáº¿n thá»ƒ trÃ¹ng vá» máº·t hiá»ƒn thá»‹; sá»‘ lÆ°á»£ng vÃ  thÃ nh tiá»n Ä‘Æ°á»£c cá»™ng dá»“n.

## Update 2026-06-15 - Viá»‡t hÃ³a tráº¡ng thÃ¡i IMEI/Serial trong tá»“n kho

- Modal `Danh sÃ¡ch IMEI / Serial` trong mÃ n `Quáº£n lÃ½ tá»“n kho` khÃ´ng cÃ²n hiá»ƒn thá»‹ trá»±c tiáº¿p mÃ£ tráº¡ng thÃ¡i ká»¹ thuáº­t nhÆ° `IN_STOCK`.
- Frontend map tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh sang nhÃ£n tiáº¿ng Viá»‡t: `CÃ²n trong kho`, `Äang giá»¯`, `ÄÃ£ bÃ¡n`, `Äang báº£o hÃ nh`, `Loáº¡i bá»`, `Ngá»«ng sá»­ dá»¥ng`, `ÄÃ£ Ä‘áº£o phiáº¿u`.
- GiÃ¡ trá»‹ API/DB váº«n giá»¯ enum ká»¹ thuáº­t Ä‘á»ƒ khÃ´ng áº£nh hÆ°á»Ÿng logic nháº­p kho, giá»¯ hÃ ng, bÃ¡n hÃ ng, báº£o hÃ nh vÃ  Ä‘áº£o phiáº¿u.

## Update 2026-06-15 - Hiá»ƒn thá»‹ ngÆ°á»i thao tÃ¡c phiáº¿u nháº­p

- Danh sÃ¡ch/xem chi tiáº¿t phiáº¿u nháº­p nay tráº£ thÃªm tÃªn hiá»ƒn thá»‹ cho ngÆ°á»i táº¡o, ngÆ°á»i duyá»‡t, ngÆ°á»i hoÃ n táº¥t, ngÆ°á»i há»§y vÃ  ngÆ°á»i Ä‘áº£o phiáº¿u báº±ng cÃ¡ch join `inventory_documents.*_by` vá»›i báº£ng `users`.
- Frontend Æ°u tiÃªn hiá»ƒn thá»‹ `createdByName`, `approvedByName`, `postedByName`, `reversedByName`; náº¿u thiáº¿u tÃªn má»›i fallback vá» UUID rÃºt gá»n hoáº·c `-`.
- Phiáº¿u nháº­p khá»Ÿi táº¡o báº±ng script cÃ³ mÃ£ `NK-KHOI-TAO-%` khÃ´ng cÃ³ tÃ i khoáº£n thao tÃ¡c nÃªn hiá»ƒn thá»‹ `Há»‡ thá»‘ng` cho ngÆ°á»i táº¡o/duyá»‡t/hoÃ n táº¥t.

## Update 2026-06-15 - Serial number unique theo tá»«ng sáº£n pháº©m

- Äá»•i luáº­t trÃ¹ng serial number tá»« unique toÃ n há»‡ thá»‘ng sang unique theo cáº·p `(product_id, serial_number)`, cho phÃ©p hai sáº£n pháº©m khÃ¡c nhau dÃ¹ng cÃ¹ng má»™t serial number náº¿u nghiá»‡p vá»¥ cáº§n.
- Migration `068_product_serial_number_product_scope_unique.sql` bá» constraint unique cÅ© trÃªn `serial_number` vÃ  táº¡o unique index má»›i `idx_product_serial_numbers_product_serial_unique`.
- Backend kiá»ƒm tra serial number khi nháº­p kho, bá»• sung mÃ£ hoáº·c duyá»‡t chá»‰nh sá»­a theo pháº¡m vi cÃ¹ng sáº£n pháº©m; náº¿u cÃ¹ng sáº£n pháº©m Ä‘Ã£ cÃ³ serial thÃ¬ tá»« chá»‘i, cÃ²n khÃ¡c sáº£n pháº©m thÃ¬ cho phÃ©p.
- ÄÃ£ sinh serial khá»Ÿi táº¡o cho cÃ¡c dÃ²ng tá»“n Ä‘ang báº­t quáº£n lÃ½ serial number: `6.100` serial á»Ÿ tráº¡ng thÃ¡i `IN_STOCK`, nguá»“n `NK-KHOI-TAO-20260615-0001`.
- Kiá»ƒm tra dá»¯ liá»‡u sau khi sinh: khÃ´ng cÃ³ serial trÃ¹ng trong cÃ¹ng sáº£n pháº©m, cÃ³ serial Ä‘Æ°á»£c dÃ¹ng láº¡i giá»¯a nhiá»u sáº£n pháº©m khÃ¡c nhau, vÃ  sá»‘ serial theo tá»«ng dÃ²ng tá»“n khá»›p tá»“n thá»±c táº¿.

## Update 2026-06-15 - Phiáº¿u Ä‘iá»u chá»‰nh tá»“n cÃ³ duyá»‡t

- Bá»• sung quy trÃ¬nh `Phiáº¿u Ä‘iá»u chá»‰nh tá»“n` trong mÃ n `Quáº£n lÃ½ tá»“n kho` Ä‘á»ƒ xá»­ lÃ½ cÃ¡c chá»‰nh sá»­a thá»§ cÃ´ng tá»«ng sáº£n pháº©m/biáº¿n thá»ƒ khi phÃ¡t hiá»‡n lá»‡ch tá»“n ngoÃ i ká»³ kiá»ƒm kÃª.
- API `GET /admin/inventory/adjustments` tráº£ danh sÃ¡ch phiáº¿u Ä‘iá»u chá»‰nh, tráº¡ng thÃ¡i, tá»•ng sá»‘ dÃ²ng, tá»•ng lá»‡ch tuyá»‡t Ä‘á»‘i, lá»‡ch rÃ²ng vÃ  chi tiáº¿t tá»«ng dÃ²ng.
- API `POST /admin/inventory/adjustments` táº¡o chá»©ng tá»« `inventory_documents.document_type = ADJUSTMENT` á»Ÿ tráº¡ng thÃ¡i `DRAFT`; má»—i dÃ²ng lÆ°u tá»“n hiá»‡n táº¡i, tá»“n Ä‘á» xuáº¥t, chÃªnh lá»‡ch, lÃ½ do Ä‘iá»u chá»‰nh vÃ  ghi chÃº.
- Backend kiá»ƒm tra tá»“n hiá»‡n táº¡i lÃºc táº¡o phiáº¿u; náº¿u tá»“n há»‡ thá»‘ng Ä‘Ã£ khÃ¡c sá»‘ ngÆ°á»i dÃ¹ng nhÃ¬n tháº¥y thÃ¬ tá»« chá»‘i táº¡o phiáº¿u Ä‘á»ƒ trÃ¡nh táº¡o yÃªu cáº§u trÃªn dá»¯ liá»‡u cÅ©.
- API `PATCH /admin/inventory/adjustments/{reference_code}/status` dÃ¹ng quyá»n `inventory:approve`; khi duyá»‡t má»›i cáº­p nháº­t tá»“n sáº£n pháº©m/biáº¿n thá»ƒ, cáº­p nháº­t `inventory_levels`, ghi `inventory_adjustment_logs` vÃ  Ä‘á»“ng bá»™ tá»“n sáº£n pháº©m cha náº¿u dÃ²ng lÃ  biáº¿n thá»ƒ.
- Khi há»§y phiáº¿u Ä‘iá»u chá»‰nh, backend chá»‰ Ä‘á»•i tráº¡ng thÃ¡i sang `CANCELLED`, khÃ´ng cáº­p nháº­t tá»“n vÃ  khÃ´ng ghi log Ä‘iá»u chá»‰nh.
- Frontend thÃªm nÃºt `Äiá»u chá»‰nh` trÃªn tá»«ng dÃ²ng tá»“n kho, modal táº¡o phiáº¿u vá»›i tá»“n hiá»‡n táº¡i, tá»“n Ä‘á» xuáº¥t, chÃªnh lá»‡ch vÃ  lÃ½ do báº¯t buá»™c; danh sÃ¡ch phiáº¿u Ä‘iá»u chá»‰nh cÃ³ thao tÃ¡c xem, duyá»‡t vÃ  há»§y.
- Migration `067_inventory_adjustment_approval_workflow.sql` thÃªm index cho chá»©ng tá»« `ADJUSTMENT` vÃ  báº£o Ä‘áº£m quyá»n `inventory:adjust` Ä‘Æ°á»£c gÃ¡n cho vai trÃ² quáº£n trá»‹.

## Update 2026-06-15 - Kiá»ƒm kÃª kho vÃ  duyá»‡t chÃªnh lá»‡ch

- Bá»• sung quy trÃ¬nh kiá»ƒm kÃª kho trong mÃ n `Quáº£n lÃ½ tá»“n kho`: táº¡o phiáº¿u kiá»ƒm kÃª tá»« cÃ¡c dÃ²ng tá»“n kho Ä‘ang hiá»ƒn thá»‹, nháº­p sá»‘ lÆ°á»£ng thá»±c Ä‘áº¿m vÃ  lÆ°u phiáº¿u á»Ÿ tráº¡ng thÃ¡i `DRAFT`.
- API `GET /admin/inventory/stock-counts` tráº£ danh sÃ¡ch phiáº¿u kiá»ƒm kÃª, tá»•ng sá»‘ dÃ²ng, tá»•ng lá»‡ch tuyá»‡t Ä‘á»‘i vÃ  lá»‡ch rÃ²ng Ä‘á»ƒ quáº£n trá»‹ viÃªn xem nhanh má»©c sai lá»‡ch.
- API `POST /admin/inventory/stock-counts` táº¡o chá»©ng tá»« `inventory_documents.document_type = COUNT` vÃ  lÆ°u tá»«ng dÃ²ng vÃ o `inventory_document_lines` vá»›i `expected_quantity`, `counted_quantity`, `variance_quantity`.
- API `PATCH /admin/inventory/stock-counts/{reference_code}/status` dÃ¹ng quyá»n `inventory:approve`; khi duyá»‡t má»›i cáº­p nháº­t tá»“n sáº£n pháº©m/biáº¿n thá»ƒ, cáº­p nháº­t `inventory_levels.last_counted_at`, ghi `inventory_adjustment_logs` loáº¡i `ADJUSTMENT` vá»›i lÃ½ do kiá»ƒm kÃª vÃ  refresh read-model tá»“n kho.
- Danh sÃ¡ch phiáº¿u kiá»ƒm kÃª cÃ³ nÃºt xem chi tiáº¿t tá»«ng dÃ²ng Ä‘á»ƒ ngÆ°á»i duyá»‡t kiá»ƒm tra tá»“n há»‡ thá»‘ng, sá»‘ thá»±c Ä‘áº¿m, chÃªnh lá»‡ch vÃ  ghi chÃº trÆ°á»›c khi duyá»‡t.
- Khi há»§y phiáº¿u kiá»ƒm kÃª, backend chá»‰ Ä‘á»•i tráº¡ng thÃ¡i sang `CANCELLED`, khÃ´ng ghi thay Ä‘á»•i tá»“n.
- Migration `066_inventory_stock_count_workflow.sql` thÃªm index cho chá»©ng tá»« `COUNT` vÃ  báº£o Ä‘áº£m quyá»n `inventory:count` tá»“n táº¡i cho vai trÃ² quáº£n trá»‹.
- Pháº¡m vi hiá»‡n táº¡i má»›i kiá»ƒm kÃª theo sá»‘ lÆ°á»£ng sáº£n pháº©m/biáº¿n thá»ƒ; Ä‘á»‘i soÃ¡t IMEI/serial tá»«ng chiáº¿c nÃªn lÃ m thÃ nh bÆ°á»›c riÃªng Ä‘á»ƒ trÃ¡nh thay Ä‘á»•i hoáº·c loáº¡i bá» mÃ£ Ä‘á»‹nh danh sai nghiá»‡p vá»¥.

## Update 2026-06-15 - Danh sÃ¡ch chá» duyá»‡t vÃ  lá»‹ch sá»­ chá»‰nh sá»­a mÃ£

- MÃ n `Quáº£n lÃ½ tá»“n kho` hiá»ƒn thá»‹ khá»‘i `YÃªu cáº§u chá»‰nh sá»­a IMEI/Serial chá» duyá»‡t` ngay phÃ­a trÃªn báº£ng tá»“n kho Ä‘á»ƒ ngÆ°á»i cÃ³ quyá»n duyá»‡t khÃ´ng pháº£i má»Ÿ tá»«ng sáº£n pháº©m má»›i tháº¥y viá»‡c Ä‘ang chá» xá»­ lÃ½.
- API `GET /admin/inventory/identifier-edit-requests?status=PENDING` tráº£ danh sÃ¡ch yÃªu cáº§u chá»‰nh sá»­a theo tráº¡ng thÃ¡i, kÃ¨m sáº£n pháº©m, biáº¿n thá»ƒ, mÃ£ hiá»‡n táº¡i, mÃ£ Ä‘á» xuáº¥t, lÃ½ do vÃ  thÃ´ng tin quyáº¿t Ä‘á»‹nh.
- Modal `Danh sÃ¡ch IMEI / Serial` tráº£ thÃªm `editRequests` Ä‘á»ƒ xem lá»‹ch sá»­ yÃªu cáº§u Ä‘Ã£ duyá»‡t/há»§y/chá» duyá»‡t cá»§a Ä‘Ãºng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang xem.
- Frontend dÃ¹ng chung thao tÃ¡c duyá»‡t/há»§y trong khá»‘i chá» duyá»‡t vÃ  trong modal chi tiáº¿t; sau khi xá»­ lÃ½ sáº½ táº£i láº¡i danh sÃ¡ch chá» duyá»‡t, modal mÃ£ vÃ  read-model tá»“n kho.
- Query list request dÃ¹ng cast rÃµ rÃ ng cho tham sá»‘ nullable (`status`, `product_id`, `variant_id`) Ä‘á»ƒ trÃ¡nh lá»—i asyncpg `could not determine data type of parameter` khi lá»c toÃ n cá»¥c hoáº·c khÃ´ng truyá»n biáº¿n thá»ƒ.

## Update 2026-06-15 - Duyá»‡t chá»‰nh sá»­a IMEI/Serial trong tá»“n kho

- MÃ n `Quáº£n lÃ½ tá»“n kho` cÃ³ thá»ƒ má»Ÿ danh sÃ¡ch chi tiáº¿t IMEI vÃ  serial number cá»§a tá»«ng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang theo dÃµi mÃ£ Ä‘á»‹nh danh.
- Khi phÃ¡t hiá»‡n IMEI hoáº·c serial number sai, admin táº¡o yÃªu cáº§u chá»‰nh sá»­a kÃ¨m lÃ½ do; há»‡ thá»‘ng lÆ°u yÃªu cáº§u á»Ÿ tráº¡ng thÃ¡i `PENDING` vÃ  chÆ°a cáº­p nháº­t ngay vÃ o `product_imeis` hoáº·c `product_serial_numbers`.
- Bá»• sung báº£ng `inventory_identifier_edit_requests` Ä‘á»ƒ lÆ°u mÃ£ hiá»‡n táº¡i, mÃ£ Ä‘á» xuáº¥t, lÃ½ do, ngÆ°á»i yÃªu cáº§u, ngÆ°á»i duyá»‡t/há»§y vÃ  ghi chÃº quyáº¿t Ä‘á»‹nh.
- Backend cháº·n má»—i mÃ£ chá»‰ cÃ³ má»™t yÃªu cáº§u chá»‰nh sá»­a Ä‘ang chá» duyá»‡t, kiá»ƒm tra Ä‘á»‹nh dáº¡ng IMEI/serial vÃ  kiá»ƒm tra trÃ¹ng mÃ£ trÆ°á»›c khi táº¡o yÃªu cáº§u vÃ  trÆ°á»›c khi duyá»‡t.
- Quyá»n `inventory:adjust` Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ táº¡o yÃªu cáº§u chá»‰nh sá»­a; quyá»n `inventory:approve` Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ duyá»‡t hoáº·c há»§y yÃªu cáº§u.
- Khi duyá»‡t, backend khÃ³a yÃªu cáº§u vÃ  mÃ£ gá»‘c, xÃ¡c minh mÃ£ gá»‘c chÆ°a bá»‹ thay Ä‘á»•i sau lÃºc táº¡o yÃªu cáº§u rá»“i má»›i cáº­p nháº­t giÃ¡ trá»‹ má»›i; khi há»§y thÃ¬ chá»‰ Ä‘á»•i tráº¡ng thÃ¡i yÃªu cáº§u, khÃ´ng thay Ä‘á»•i mÃ£ gá»‘c.
- Migration `065_inventory_identifier_edit_requests.sql` Ä‘Ã£ Ä‘Æ°á»£c thÃªm vÃ o `backend/scripts/run_migrations.py`.
- Sau review, bá»• sung export schema `InventoryIdentifierEditRequestPayload` / `InventoryIdentifierEditDecisionPayload` trong `app.api.schemas.admin`, cháº·n lÃ½ do toÃ n khoáº£ng tráº¯ng vÃ  cháº·n serial number má»›i rá»—ng sau khi trim Ä‘á»ƒ trÃ¡nh lá»—i runtime/DB 500.

## Update 2026-06-15 - Nháº­p thiáº¿u IMEI/Serial theo tá»«ng sáº£n pháº©m

- Modal bá»• sung IMEI/Serial trong mÃ n hÃ¬nh nháº­p kho hiá»ƒn thá»‹ rÃµ tá»«ng dÃ²ng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang Ä‘Æ°á»£c nháº­p mÃ£ Ä‘á»‹nh danh, kÃ¨m sá»‘ lÆ°á»£ng Ä‘Ã£ nháº­p vÃ  sá»‘ lÆ°á»£ng cÃ²n thiáº¿u cá»§a riÃªng dÃ²ng Ä‘Ã³.
- Khi má»™t dÃ²ng sáº£n pháº©m thiáº¿u IMEI hoáº·c serial number, UI báº¯t buá»™c nháº­p lÃ½ do thiáº¿u ngay trong dÃ²ng sáº£n pháº©m Ä‘Ã³ thay vÃ¬ dÃ¹ng má»™t lÃ½ do chung cho toÃ n phiáº¿u.
- Admin pháº£i tick `XÃ¡c nháº­n nháº­p thiáº¿u` á»Ÿ Ä‘Ãºng dÃ²ng sáº£n pháº©m cÃ²n thiáº¿u trÆ°á»›c khi há»‡ thá»‘ng cho gá»­i danh sÃ¡ch thiáº¿u; náº¿u chÆ°a tick, UI yÃªu cáº§u nháº­p Ä‘á»§ mÃ£ hoáº·c xÃ¡c nháº­n thiáº¿u Ä‘á»ƒ trÃ¡nh gá»­i thiáº¿u do Ä‘ang nháº­p dá»Ÿ.
- Payload `POST /admin/inventory/receipts/{reference_code}/imeis` há»— trá»£ thÃªm `acceptShortage` vÃ  `shortageReason` á»Ÿ cáº¥p tá»«ng dÃ²ng; backend tá»« chá»‘i dÃ²ng thiáº¿u mÃ£ náº¿u chÆ°a cÃ³ `acceptShortage = true`.
- API váº«n giá»¯ `shortageReason` cáº¥p phiáº¿u Ä‘á»ƒ tÆ°Æ¡ng thÃ­ch vá»›i client cÅ©, nhÆ°ng client má»›i nÃªn gá»­i lÃ½ do thiáº¿u theo tá»«ng dÃ²ng.
- Backend lÆ°u `shortageReason` vÃ o metadata cá»§a Ä‘Ãºng dÃ²ng thiáº¿u mÃ£; ghi chÃº tráº¡ng thÃ¡i phiáº¿u gom cÃ¡c lÃ½ do thiáº¿u cá»§a nhá»¯ng dÃ²ng bá»‹ thiáº¿u Ä‘á»ƒ phá»¥c vá»¥ tra cá»©u nhanh.
- Modal xem phiáº¿u nháº­p hiá»ƒn thá»‹ sá»‘ mÃ£ cÃ²n thiáº¿u vÃ  lÃ½ do thiáº¿u ngay trÃªn tá»«ng dÃ²ng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘á»ƒ ngÆ°á»i duyá»‡t khÃ´ng pháº£i Ä‘á»c ghi chÃº tá»•ng há»£p.

## Update 2026-06-15 - XÃ³a phiáº¿u nháº­p nhÃ¡p

- Bá»• sung API `DELETE /admin/inventory/receipts/{reference_code}` Ä‘á»ƒ xÃ³a phiáº¿u nháº­p chá»‰ khi phiáº¿u cÃ²n á»Ÿ tráº¡ng thÃ¡i `DRAFT` vÃ  chÆ°a ghi sá»• kho.
- Backend khÃ³a phiáº¿u báº±ng `FOR UPDATE`, kiá»ƒm tra tráº¡ng thÃ¡i, xÃ³a dÃ²ng `inventory_document_lines` trÆ°á»›c rá»“i má»›i xÃ³a header `inventory_documents`.
- Frontend chá»‰ hiá»ƒn thá»‹ nÃºt xÃ³a cho phiáº¿u `NhÃ¡p`; cÃ¡c tráº¡ng thÃ¡i Ä‘Ã£ vÃ o quy trÃ¬nh váº«n dÃ¹ng `Há»§y`, cÃ²n phiáº¿u Ä‘Ã£ hoÃ n táº¥t váº«n dÃ¹ng `Äáº£o phiáº¿u`.

## Update 2026-06-13 siáº¿t hoÃ n táº¥t phiáº¿u nháº­p kho

- Giá»¯ nguyÃªn mÃ´ hÃ¬nh duyá»‡t theo quyá»n `inventory:approve`; Super Admin cÃ³ thá»ƒ lÃ  ngÆ°á»i duyá»‡t phiáº¿u nháº­p, khÃ´ng Ã¡p dá»¥ng rÃ ng buá»™c maker-checker báº¯t buá»™c cho staff trong láº§n nÃ y.
- Phiáº¿u nháº­p nay lÆ°u actor theo tá»«ng má»‘c nghiá»‡p vá»¥: `created_by` khi táº¡o phiáº¿u, `approved_by` khi duyá»‡t, `posted_by` khi hoÃ n táº¥t vÃ  `cancelled_by`/`cancelled_at` khi há»§y.
- Bá»• sung migration `062_inventory_receipt_audit_actors.sql` Ä‘á»ƒ thÃªm `posted_by`, `cancelled_by`, `cancelled_at` vÃ  index tra cá»©u actor cho chá»©ng tá»« tá»“n kho.
- Khi hoÃ n táº¥t phiáº¿u nháº­p, backend nay kiá»ƒm tra `posted_at` cá»§a chá»©ng tá»« Ä‘ang bá»‹ khÃ³a `FOR UPDATE`; náº¿u phiáº¿u Ä‘Ã£ tá»«ng post tá»“n kho thÃ¬ tá»« chá»‘i hoÃ n táº¥t láº¡i Ä‘á»ƒ trÃ¡nh cá»™ng tá»“n láº·p khi retry/race.
- Log nháº­p kho khi post phiáº¿u dÃ¹ng Ä‘Ãºng `inventory_documents.target_location_id` Ä‘Ã£ lÆ°u trÃªn phiáº¿u thay vÃ¬ hard-code `MAIN` / `Kho chÃ­nh`; vá»›i cáº¥u hÃ¬nh má»™t chi nhÃ¡nh hiá»‡n táº¡i váº«n fallback vá» kho chÃ­nh náº¿u thiáº¿u dá»¯ liá»‡u.
- MÃ n nháº­p kho Ä‘á»•i nhÃ£n thao tÃ¡c bá»• sung mÃ£ Ä‘á»‹nh danh tá»« IMEI sang IMEI/Serial Ä‘á»ƒ khÃ´ng gÃ¢y hiá»ƒu nháº§m vá»›i sáº£n pháº©m chá»‰ quáº£n lÃ½ serial number.
- Migration serial number `060_product_serial_number_management.sql` Ä‘Ã£ cÃ³ trong `backend/scripts/run_migrations.py`; cáº§n báº£o Ä‘áº£m DB mÃ´i trÆ°á»ng cháº¡y migration nÃ y trÆ°á»›c khi coi serial number lÃ  Ä‘Ã£ live.
- Bá»• sung migration `063_inventory_receipt_reversal.sql` vÃ  API `POST /admin/inventory/receipts/{reference_code}/reverse` Ä‘á»ƒ Ä‘áº£o phiáº¿u nháº­p Ä‘Ã£ `COMPLETED` báº±ng chá»©ng tá»« `REVERSAL` riÃªng, khÃ´ng dÃ¹ng `CANCELLED` cho phiáº¿u Ä‘Ã£ post.
- Khi Ä‘áº£o phiáº¿u, backend chá»‰ cho xá»­ lÃ½ náº¿u tá»“n kho biáº¿n thá»ƒ cÃ²n Ä‘á»§ vÃ  toÃ n bá»™ IMEI/serial cá»§a phiáº¿u cÃ²n á»Ÿ tráº¡ng thÃ¡i `IN_STOCK`; sau Ä‘Ã³ giáº£m tá»“n, ghi log `REVERSAL`, chuyá»ƒn mÃ£ Ä‘á»‹nh danh sang `REVERSED` vÃ  Ä‘Ã¡nh dáº¥u phiáº¿u gá»‘c `REVERSED`.
- Vá»›i sáº£n pháº©m quáº£n lÃ½ cáº£ IMEI vÃ  serial number, danh sÃ¡ch bá»• sung pháº£i khá»›p sá»‘ lÆ°á»£ng theo tá»«ng mÃ¡y; backend khÃ´ng cÃ²n cho phÃ©p sá»‘ IMEI khÃ¡c sá»‘ serial rá»“i láº¥y `min(...)` vÃ¬ dá»… lÃ m lá»‡ch sá»‘ mÃ£ Ä‘á»‹nh danh so vá»›i tá»“n thá»±c nháº­n.
- Bá»• sung migration `064_inventory_levels_moving_average_cost.sql`; khi hoÃ n táº¥t phiáº¿u nháº­p, backend cáº­p nháº­t `inventory_levels.on_hand_quantity` vÃ  `average_unit_cost` theo phÆ°Æ¡ng phÃ¡p moving average dá»±a trÃªn `unitCost` cá»§a dÃ²ng nháº­p.
- Khi Ä‘áº£o phiáº¿u, backend giáº£m `inventory_levels.on_hand_quantity` nhÆ°ng giá»¯ nguyÃªn `average_unit_cost`; Ä‘Ã¢y lÃ  cÃ¡ch báº£o toÃ n giÃ¡ vá»‘n bÃ¬nh quÃ¢n hiá»‡n hÃ nh cho lÆ°á»£ng tá»“n cÃ²n láº¡i sau chá»©ng tá»« bÃ¹ trá»«.
- API tá»“n kho vÃ  CSV export tráº£ thÃªm `averageUnitCost`; mÃ n `Quáº£n lÃ½ tá»“n kho` hiá»ƒn thá»‹ cá»™t `GiÃ¡ vá»‘n BQ`.

## Update 2026-06-13 tÃ¡ch tab IMEI/Serial trong xem phiáº¿u nháº­p

- Modal xem phiáº¿u nháº­p kho hiá»‡n cÃ³ tab `ThÃ´ng tin phiáº¿u nháº­p` vÃ  tab `Danh sÃ¡ch IMEI / Serial` riÃªng.
- Trong báº£ng chi tiáº¿t nháº­p kho, dÃ²ng nÃ o cÃ³ quáº£n lÃ½ IMEI hoáº·c serial number thÃ¬ tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh lÃ  nÃºt cÃ³ thá»ƒ báº¥m.
- Khi báº¥m tráº¡ng thÃ¡i mÃ£ Ä‘á»‹nh danh cá»§a má»™t dÃ²ng sáº£n pháº©m, modal tá»± chuyá»ƒn sang tab `Danh sÃ¡ch IMEI / Serial` vÃ  chá»‰ hiá»ƒn thá»‹ IMEI/serial cá»§a Ä‘Ãºng dÃ²ng sáº£n pháº©m/biáº¿n thá»ƒ Ä‘Ã³.
- Tab danh sÃ¡ch mÃ£ cÃ³ nÃºt `Xem táº¥t cáº£` Ä‘á»ƒ bá» lá»c vÃ  xem toÃ n bá»™ IMEI/serial trong phiáº¿u.
- Verification: `npm run lint` trong `frontend` pass.
## Update 2026-06-13 xem phiáº¿u nháº­p kho theo IMEI/Serial

- Modal xem phiáº¿u nháº­p kho Ä‘Æ°á»£c chuáº©n hÃ³a thÃ nh hai pháº§n: `ThÃ´ng tin phiáº¿u nháº­p` vÃ  `Chi tiáº¿t nháº­p kho / IMEI / Serial`.
- Báº£ng chi tiáº¿t nháº­p kho hiá»ƒn thá»‹ riÃªng `SL nháº­p`, `SL Ä‘Ã£ nháº­p IMEI`, `SL Ä‘Ã£ nháº­p Serial`, giÃ¡ nháº­p, thÃ nh tiá»n vÃ  tráº¡ng thÃ¡i tá»«ng dÃ²ng.
- Tráº¡ng thÃ¡i dÃ²ng hiá»‡n tÃ­nh song song cho IMEI vÃ  serial number: Ä‘á»§ thÃ¬ hiá»ƒn thá»‹ `Äá»§ IMEI` / `Äá»§ Serial`, thiáº¿u thÃ¬ hiá»ƒn thá»‹ sá»‘ lÆ°á»£ng cÃ²n thiáº¿u tÆ°Æ¡ng á»©ng.
- NÃºt in phiáº¿u phÃ¢n biá»‡t `In phiáº¿u nháº­p táº¡m` vÃ  `In phiáº¿u nháº­p hoÃ n chá»‰nh`; phiáº¿u táº¡m cÃ³ cáº£nh bÃ¡o â€œPhiáº¿u nháº­p chÆ°a hoÃ n táº¥t do chÆ°a bá»• sung Ä‘á»§ IMEI/Serial.â€
- Danh sÃ¡ch mÃ£ Ä‘á»‹nh danh trong phiáº¿u in/xem váº«n gom cáº£ IMEI vÃ  serial number, cÃ³ cá»™t loáº¡i mÃ£ Ä‘á»ƒ dÃ¹ng serial giá»‘ng IMEI.
- Verification: `npm run lint` trong `frontend` pass.

## Update 2026-06-13 xem thÃ´ng tin phiáº¿u nháº­p kho

- MÃ n `Quáº£n lÃ½ nháº­p kho` cÃ³ thÃªm nÃºt `Xem` trÃªn tá»«ng phiáº¿u nháº­p.
- NÃºt nÃ y má»Ÿ modal chá»‰ Ä‘á»c, hiá»ƒn thá»‹ thÃ´ng tin header phiáº¿u, tráº¡ng thÃ¡i, lÃ½ do nháº­p, nhÃ  cung cáº¥p, ngÃ y táº¡o, ghi chÃº, tá»•ng sá»‘ dÃ²ng, tá»•ng sá»‘ lÆ°á»£ng, giÃ¡ trá»‹ nháº­p vÃ  toÃ n bá»™ dÃ²ng sáº£n pháº©m.
- Modal hiá»ƒn thá»‹ thÃªm danh sÃ¡ch IMEI vÃ  serial number Ä‘Ã£ nháº­p theo tá»«ng dÃ²ng sáº£n pháº©m náº¿u phiáº¿u cÃ³ quáº£n lÃ½ mÃ£ Ä‘á»‹nh danh.
- Modal phÃ¢n biá»‡t phiáº¿u táº¡m/chá» bá»• sung IMEI vá»›i phiáº¿u hoÃ n chá»‰nh: náº¿u dÃ²ng hÃ ng cÃ²n thiáº¿u IMEI/serial sáº½ hiá»ƒn thá»‹ cáº£nh bÃ¡o vÃ  nÃºt `In phiáº¿u táº¡m`; náº¿u phiáº¿u Ä‘Ã£ hoÃ n táº¥t vÃ  Ä‘á»§ mÃ£ Ä‘á»‹nh danh sáº½ hiá»ƒn thá»‹ `In phiáº¿u hoÃ n chá»‰nh`.
- Pháº§n xem phiáº¿u tÃ¡ch thÃ nh `ThÃ´ng tin phiáº¿u nháº­p`, báº£ng chi tiáº¿t dÃ²ng nháº­p, vÃ  báº£ng riÃªng `Danh sÃ¡ch IMEI / Serial` cÃ³ STT, sáº£n pháº©m, SKU/biáº¿n thá»ƒ, loáº¡i mÃ£ vÃ  mÃ£ Ä‘á»‹nh danh.
- Modal xem phiáº¿u nháº­p khÃ´ng hiá»ƒn thá»‹ cÃ¡c thao tÃ¡c nghiá»‡p vá»¥ nhÆ° duyá»‡t, há»§y, hoÃ n táº¥t hoáº·c nháº­p IMEI/serial; chá»‰ cÃ³ nÃºt `ÄÃ³ng` Ä‘á»ƒ trÃ¡nh nháº§m vá»›i form thao tÃ¡c.
- Verification: `python -m py_compile backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/application/services/inventory_service.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-13 phÃ¢n loáº¡i lÃ½ do nháº­p kho

- Phiáº¿u nháº­p kho cÃ³ thÃªm mÃ£ lÃ½ do nháº­p á»Ÿ cáº¥p phiáº¿u: `NK_MUA`, `NK_TRA_NCC`, `NK_KH_TRA`, `NK_BH`, `NK_DIEUCHINH`, `NK_CHUYEN`, `NK_SANXUAT`, `NK_KHAC`.
- Backend lÆ°u mÃ£ nÃ y vÃ o `inventory_documents.reason` Ä‘á»ƒ trÃ¡nh thÃªm migration má»›i; log tá»“n kho khi hoÃ n táº¥t phiáº¿u cÅ©ng dÃ¹ng cÃ¹ng mÃ£ nghiá»‡p vá»¥ thay vÃ¬ ghi chung `Nháº­p kho`.
- Khi chá»n `NK_KHAC`, backend vÃ  frontend Ä‘á»u yÃªu cáº§u ghi rÃµ lÃ½ do trong `Ghi chÃº chung`.
- Danh sÃ¡ch phiáº¿u nháº­p hiá»ƒn thá»‹ thÃªm cá»™t `LÃ½ do nháº­p`; Ã´ tÃ¬m kiáº¿m cÃ³ thá»ƒ tÃ¬m theo mÃ£ lÃ½ do.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-13 IMEI chÃ­nh vÃ  IMEI bá»• sung

- Bá»• sung migration `061_product_imei_primary.sql` Ä‘á»ƒ thÃªm cá»™t `product_imeis.is_primary`.
- Má»—i sáº£n pháº©m hoáº·c biáº¿n thá»ƒ cÃ³ thá»ƒ cÃ³ nhiá»u IMEI, nhÆ°ng chá»‰ cÃ³ tá»‘i Ä‘a má»™t IMEI chÃ­nh nhá» unique index riÃªng cho dÃ²ng khÃ´ng cÃ³ biáº¿n thá»ƒ vÃ  dÃ²ng cÃ³ biáº¿n thá»ƒ.
- Dá»¯ liá»‡u IMEI cÅ© Ä‘Æ°á»£c tá»± gÃ¡n IMEI chÃ­nh theo báº£n ghi Ä‘áº§u tiÃªn cá»§a tá»«ng sáº£n pháº©m/biáº¿n thá»ƒ náº¿u trÆ°á»›c Ä‘Ã³ chÆ°a cÃ³ IMEI chÃ­nh.
- Khi nháº­p kho, IMEI Ä‘áº§u tiÃªn cá»§a sáº£n pháº©m/biáº¿n thá»ƒ sáº½ tá»± trá»Ÿ thÃ nh IMEI chÃ­nh náº¿u chÆ°a tá»“n táº¡i IMEI chÃ­nh; cÃ¡c IMEI cÃ²n láº¡i lÃ  IMEI bá»• sung.
- Read-model tá»“n kho vÃ  export CSV tráº£ thÃªm `primaryImei` vÃ  `supplementalImei`; UI tá»“n kho hiá»ƒn thá»‹ IMEI chÃ­nh, sá»‘ IMEI phá»¥ vÃ  cÃ¡c tráº¡ng thÃ¡i trong kho/Ä‘ang giá»¯/Ä‘Ã£ bÃ¡n.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass; migration `061_product_imei_primary.sql` Ä‘Ã£ cháº¡y thÃ nh cÃ´ng trÃªn DB local.

## Update 2026-06-13 quáº£n lÃ½ serial number song song IMEI

- ThÃªm migration `060_product_serial_number_management.sql` Ä‘á»ƒ táº¡o báº£ng `product_serial_numbers` vÃ  má»Ÿ rá»™ng `categories.inventory_policy` vá»›i `inheritSerialPolicy`/`trackSerialNumber`.
- Backend tá»“n kho xÃ¡c Ä‘á»‹nh chÃ­nh sÃ¡ch serial number theo cÃ¹ng thá»© tá»± Æ°u tiÃªn cá»§a IMEI: sáº£n pháº©m cÃ³ `sales_config.serialPolicy` á»Ÿ cháº¿ Ä‘á»™ `MANUAL` Ä‘Æ°á»£c Æ°u tiÃªn, náº¿u khÃ´ng thÃ¬ láº¥y theo danh má»¥c con/cha.
- Phiáº¿u nháº­p kho lÆ°u metadata dÃ²ng phiáº¿u gá»“m `tracksSerialNumber` vÃ  `serialNumbers`; bÆ°á»›c xá»­ lÃ½ mÃ£ Ä‘á»‹nh danh hiá»‡n nháº­n cáº£ IMEI vÃ  serial number. Náº¿u má»™t dÃ²ng yÃªu cáº§u cáº£ hai, sá»‘ lÆ°á»£ng thá»±c nháº­n Ä‘Æ°á»£c tÃ­nh theo sá»‘ cáº·p mÃ£ Ä‘áº§y Ä‘á»§ nhá» nháº¥t.
- Khi hoÃ n táº¥t phiáº¿u nháº­p, backend ghi serial number vÃ o `product_serial_numbers` vá»›i tráº¡ng thÃ¡i `IN_STOCK`, Ä‘á»“ng thá»i váº«n cá»™ng tá»“n kho vÃ  ghi log nháº­p kho nhÆ° trÆ°á»›c.
- Read-model tá»“n kho vÃ  export CSV tráº£ thÃªm `tracksSerialNumber` vÃ  `serialNumberSummary` Ä‘á»ƒ admin theo dÃµi serial trong kho/Ä‘ang giá»¯/Ä‘Ã£ bÃ¡n/báº£o hÃ nh/pháº¿ pháº©m.
- Frontend nháº­p kho hiá»ƒn thá»‹ sáº£n pháº©m cáº§n serial; modal bá»• sung mÃ£ Ä‘á»‹nh danh cho phÃ©p nháº­p/import IMEI vÃ  serial number theo tá»«ng dÃ²ng; báº£ng tá»“n kho hiá»ƒn thá»‹ tÃ³m táº¯t cáº£ IMEI vÃ  serial.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-05 Inventory Service Repository Split

- Táº¡o `app/infrastructure/database/repositories/inventory_repo.py` Ä‘á»ƒ gom truy váº¥n DB cá»§a module tá»“n kho.
- Chuyá»ƒn SQL khá»i `app/application/services/inventory_service.py`, gá»“m: Ä‘á»c tá»“n kho sáº£n pháº©m, danh sÃ¡ch biáº¿n thá»ƒ, lá»‹ch sá»­ Ä‘iá»u chá»‰nh, cáº­p nháº­t cáº¥u hÃ¬nh tá»“n kho, xuáº¥t snapshot CSV, idempotency, cáº­p nháº­t tá»“n kho biáº¿n thá»ƒ, ghi IMEI vÃ  ghi log Ä‘iá»u chá»‰nh tá»“n kho.
- `inventory_service.py` hiá»‡n giá»¯ logic nghiá»‡p vá»¥: tÃ­nh cáº£nh bÃ¡o tá»“n kho, merge `sales_config`, xuáº¥t CSV, chá»n biáº¿n thá»ƒ khi sáº£n pháº©m Ä‘Æ¡n giáº£n, sinh IMEI, kiá»ƒm tra sá»‘ lÆ°á»£ng Ã¢m vÃ  Ä‘á»“ng bá»™ láº¡i giÃ¡/tá»“n kho sáº£n pháº©m cha.
- Sá»­a láº¡i nhÃ£n tiáº¿ng Viá»‡t trong CSV tá»“n kho sang Unicode Ä‘Ãºng dáº¥u.
- Káº¿t quáº£ kiá»ƒm tra: compile backend báº±ng `.venv` thÃ nh cÃ´ng; import `app.main`, `inventory_service` vÃ  `inventory_repo` Ä‘á»u hoáº¡t Ä‘á»™ng; `inventory_service.py` khÃ´ng cÃ²n SQL trá»±c tiáº¿p.

## Update 2026-06-12 vÃ²ng Ä‘á»i tráº¡ng thÃ¡i phiáº¿u nháº­p kho

- Phiáº¿u nháº­p kho admin dÃ¹ng vÃ²ng Ä‘á»i: `DRAFT` (NhÃ¡p), `PENDING_APPROVAL` (Chá» duyá»‡t), `APPROVED` (ÄÃ£ duyá»‡t), `RECEIVING` (Äang nháº­p kho), `COMPLETED` (HoÃ n táº¥t), `CANCELLED` (ÄÃ£ há»§y).
- API `POST /admin/inventory/receipts` nay lÆ°u phiáº¿u vÃ o `inventory_documents` vÃ  `inventory_document_lines`; tráº¡ng thÃ¡i máº·c Ä‘á»‹nh lÃ  `DRAFT`. Phiáº¿u chá»‰ cá»™ng tá»“n kho vÃ  ghi `inventory_adjustment_logs` khi táº¡o tháº³ng `COMPLETED` hoáº·c khi chuyá»ƒn tá»« `APPROVED` sang `RECEIVING`/`COMPLETED`.
- API má»›i `PATCH /admin/inventory/receipts/{reference_code}/status` kiá»ƒm soÃ¡t chuyá»ƒn tráº¡ng thÃ¡i theo luá»“ng: `DRAFT -> PENDING_APPROVAL -> APPROVED -> RECEIVING -> COMPLETED`, vÃ  cho phÃ©p há»§y trÆ°á»›c khi báº¯t Ä‘áº§u nháº­p kho Ä‘á»ƒ trÃ¡nh pháº£i táº¡o reversal sau khi tá»“n kho Ä‘Ã£ Ä‘Æ°á»£c cá»™ng.
- `GET /admin/inventory/receipts` Ä‘á»c phiáº¿u tá»« document tables, Ä‘á»“ng thá»i váº«n hiá»ƒn thá»‹ cÃ¡c phiáº¿u nháº­p cÅ© trong `inventory_adjustment_logs` dÆ°á»›i tráº¡ng thÃ¡i `COMPLETED` Ä‘á»ƒ khÃ´ng máº¥t lá»‹ch sá»­.
- Migration `057_inventory_receipt_lifecycle.sql` má»Ÿ rá»™ng constraint tráº¡ng thÃ¡i, cho phÃ©p dÃ²ng phiáº¿u lÆ°u cáº£ sáº£n pháº©m vÃ  biáº¿n thá»ƒ, bá»• sung `metadata` Ä‘á»ƒ giá»¯ danh sÃ¡ch IMEI nhÃ¡p trÆ°á»›c khi post tá»“n kho.
- Frontend mÃ n `Quáº£n lÃ½ nháº­p kho` hiá»ƒn thá»‹ badge tráº¡ng thÃ¡i vÃ  cÃ¡c hÃ nh Ä‘á»™ng chuyá»ƒn bÆ°á»›c; popup táº¡o phiáº¿u cÃ³ nÃºt `LÆ°u nhÃ¡p`, `Gá»­i duyá»‡t`, `HoÃ n táº¥t nháº­p kho`.
- Káº¿t quáº£ kiá»ƒm tra: Ä‘Ã£ cháº¡y migration 057 local thÃ nh cÃ´ng, backend `py_compile` thÃ nh cÃ´ng, import `app.main`/`inventory_service`/`inventory_repo` thÃ nh cÃ´ng, `npm run lint` frontend thÃ nh cÃ´ng, vÃ  truy váº¥n danh sÃ¡ch phiáº¿u nháº­p qua service tráº£ dá»¯ liá»‡u há»£p lá»‡.

## Update 2026-06-12 Æ°u tiÃªn chÃ­nh sÃ¡ch IMEI theo sáº£n pháº©m

- Luá»“ng tá»“n kho váº«n láº¥y chÃ­nh sÃ¡ch IMEI theo danh má»¥c khi sáº£n pháº©m Ä‘á»ƒ `sales_config.imeiPolicy.mode = CATEGORY`.
- Náº¿u sáº£n pháº©m Ä‘áº·t `sales_config.imeiPolicy.mode = MANUAL`, backend Æ°u tiÃªn `sales_config.imeiPolicy.trackImei` thay cho `categories.inventory_policy`.
- CÃ¡ch nÃ y cho phÃ©p danh má»¥c cÃ³ chÃ­nh sÃ¡ch máº·c Ä‘á»‹nh nhÆ°ng tá»«ng sáº£n pháº©m váº«n cÃ³ thá»ƒ báº­t/táº¯t quáº£n lÃ½ IMEI riÃªng khi nghiá»‡p vá»¥ cáº§n ngoáº¡i lá»‡.

## Update 2026-06-12 tÃ¡ch bÆ°á»›c bá»• sung IMEI khá»i form láº­p phiáº¿u nháº­p

- Form láº­p phiáº¿u nháº­p khÃ´ng cÃ²n nháº­p IMEI. Admin chá»‰ chá»n sáº£n pháº©m/biáº¿n thá»ƒ, nháº­p sá»‘ lÆ°á»£ng dá»± kiáº¿n vÃ  giÃ¡ nháº­p; phiáº¿u má»›i luÃ´n báº¯t Ä‘áº§u á»Ÿ `DRAFT`.
- VÃ²ng Ä‘á»i IMEI má»›i: `DRAFT -> PROCESSING_IMEI -> APPROVED -> COMPLETED`; trÆ°á»ng há»£p thiáº¿u IMEI Ä‘i qua `PROCESSING_IMEI -> PENDING_SHORTAGE_APPROVAL -> APPROVED -> COMPLETED`.
- Khi chuyá»ƒn sang `PROCESSING_IMEI`, sá»‘ lÆ°á»£ng dá»± kiáº¿n bá»‹ khÃ³a á»Ÿ cáº¥p phiáº¿u. IMEI Ä‘Æ°á»£c bá»• sung qua endpoint riÃªng `POST /admin/inventory/receipts/{reference_code}/imeis`.
- Backend validate IMEI nghiÃªm ngáº·t: lÃ m sáº¡ch dá»¯ liá»‡u, báº¯t Ä‘Ãºng 15 chá»¯ sá»‘ theo regex `^[0-9]{15}$`, cháº·n trÃ¹ng trong cÃ¹ng phiáº¿u vÃ  cháº·n trÃ¹ng vá»›i báº£ng `product_imeis`.
- Náº¿u sá»‘ IMEI há»£p lá»‡ báº±ng sá»‘ lÆ°á»£ng dá»± kiáº¿n, backend lÆ°u IMEI vÃ o metadata dÃ²ng phiáº¿u vÃ  chuyá»ƒn phiáº¿u sang `APPROVED`; nÃºt `HoÃ n táº¥t nháº­p kho` má»›i Ä‘Æ°á»£c má»Ÿ.
- Náº¿u sá»‘ IMEI Ã­t hÆ¡n sá»‘ lÆ°á»£ng dá»± kiáº¿n, báº¯t buá»™c cÃ³ lÃ½ do thiáº¿u. Phiáº¿u chuyá»ƒn sang `PENDING_SHORTAGE_APPROVAL`; sau khi admin duyá»‡t thiáº¿u, hoÃ n táº¥t nháº­p kho chá»‰ cá»™ng tá»“n kho theo `receivedQuantity` thá»±c nháº­n.
- Frontend mÃ n `Nháº­p kho` cÃ³ modal `Bá»• sung IMEI` riÃªng vá»›i thanh tiáº¿n Ä‘á»™ tá»«ng dÃ²ng, Ã´ nháº­p tay hÃ ng loáº¡t vÃ  import Excel/CSV/TXT báº±ng thÆ° viá»‡n `xlsx`.
- Migration `058_inventory_receipt_imei_workflow.sql` má»Ÿ rá»™ng tráº¡ng thÃ¡i phiáº¿u vÃ  chuáº©n hÃ³a metadata dÃ²ng phiáº¿u: `tracksImei`, `plannedQuantity`, `receivedQuantity`, `imeis`, `shortageReason`.

## Update 2026-06-12 read-model tá»“n kho kháº£ dá»¥ng theo chuáº©n WMS

- ThÃªm API `GET /admin/inventory/levels` Ä‘á»ƒ mÃ n `Quáº£n lÃ½ tá»“n kho` Ä‘á»c read-model chuyÃªn dá»¥ng thay vÃ¬ chá»‰ dá»±a vÃ o danh sÃ¡ch sáº£n pháº©m catalog.
- Read-model tÃ¡ch rÃµ `physicalStock`, `reservedStock` vÃ  `availableStock`; `availableStock = max(physicalStock - reservedStock, 0)`.
- `reservedStock` Ä‘Æ°á»£c gom tá»« `inventory_reservations` cÃ²n `ACTIVE` chÆ°a háº¿t háº¡n vÃ  IMEI Ä‘ang `RESERVED`; backend dÃ¹ng giÃ¡ trá»‹ lá»›n hÆ¡n Ä‘á»ƒ trÃ¡nh Ä‘áº¿m Ä‘Ã´i khi má»™t Ä‘Æ¡n hÃ ng vá»«a cÃ³ reservation record vá»«a khÃ³a IMEI cá»¥ thá»ƒ.
- Read-model tráº£ thÃªm `tracksImei` vÃ  `imeiSummary` gá»“m sá»‘ IMEI `IN_STOCK`, `RESERVED`, `SOLD`, báº£o hÃ nh vÃ  pháº¿ pháº©m Ä‘á»ƒ admin nhÃ¬n Ä‘Æ°á»£c tráº¡ng thÃ¡i chi tiáº¿t tá»«ng biáº¿n thá»ƒ.
- MÃ n `Quáº£n lÃ½ tá»“n kho` Ä‘á»•i báº£ng sang cÃ¡c cá»™t `Tá»“n thá»±c táº¿`, `Äang giá»¯`, `Kháº£ dá»¥ng`, `IMEI`, `Cáº£nh bÃ¡o`, `Tráº¡ng thÃ¡i`; Ä‘á»“ng thá»i sá»­a láº¡i cÃ¡c nhÃ£n tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong component nÃ y.
- File export CSV tá»“n kho cÅ©ng Ä‘á»•i sang cÃ¡c cá»™t WMS má»›i, gá»“m tá»“n thá»±c táº¿, Ä‘ang giá»¯, kháº£ dá»¥ng, tráº¡ng thÃ¡i, chÃ­nh sÃ¡ch IMEI vÃ  tÃ³m táº¯t IMEI.
- Migration `059_inventory_imei_enterprise_statuses.sql` má»Ÿ rá»™ng constraint tráº¡ng thÃ¡i `product_imeis` Ä‘á»ƒ há»— trá»£ tráº¡ng thÃ¡i chuáº©n `IN_WARRANTY` vÃ  `SCRAP`, váº«n giá»¯ tÆ°Æ¡ng thÃ­ch vá»›i `WARRANTY` vÃ  `RETIRED` cÅ©.
- Verification: `python -m py_compile app\application\services\inventory_service.py app\infrastructure\database\repositories\inventory_repo.py app\api\routers\admin_inventory.py scripts\run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-15 - Chá»‰nh sá»­a phiáº¿u nháº­p chÆ°a hoÃ n táº¥t

- Phiáº¿u nháº­p cÃ³ thá»ƒ chá»‰nh sá»­a khi cÃ²n trong luá»“ng chÆ°a ghi sá»•: `DRAFT`, `PROCESSING_IMEI`, `PENDING_SHORTAGE_APPROVAL`, `APPROVED`.
- Khi lÆ°u thay Ä‘á»•i, backend cáº­p nháº­t header/dÃ²ng phiáº¿u, xÃ³a dÃ²ng cÅ© vÃ  Ä‘Æ°a phiáº¿u vá» `DRAFT`; cÃ¡c thÃ´ng tin duyá»‡t/há»§y cÅ© Ä‘Æ°á»£c xÃ³a Ä‘á»ƒ báº¯t buá»™c cháº¡y láº¡i quy trÃ¬nh duyá»‡t vÃ  nháº­p IMEI/Serial náº¿u cáº§n.
- Phiáº¿u Ä‘Ã£ `COMPLETED`, Ä‘Ã£ cÃ³ `posted_at`, `CANCELLED` hoáº·c `REVERSED` khÃ´ng Ä‘Æ°á»£c chá»‰nh sá»­a qua API cáº­p nháº­t phiáº¿u nháº­p.
# Update 2026-06-18 - Consolidate database migrations

- ToÃ n bá»™ migration tá»“n kho cÅ© Ä‘áº¿n `073` Ä‘Ã£ Ä‘Æ°á»£c gá»™p vÃ o `backend/migrations/init_database.sql`.
- CÃ¡c file migration rá»i cÅ© Ä‘Ã£ Ä‘Æ°á»£c loáº¡i bá»; thay Ä‘á»•i schema tiáº¿p theo báº¯t Ä‘áº§u tá»« `001_*.sql`.

## Update 2026-06-27 (7) - Kháº¯c phá»¥c hiá»ƒn thá»‹ danh sÃ¡ch ká»‡ xuáº¥t vÃ  rÃ ng buá»™c sá»‘ lÆ°á»£ng

- **Sá»­a lá»—i lá»c ká»‡ xuáº¥t**: Thay Ä‘á»•i Ä‘iá»u kiá»‡n lá»c trong `list_level_issue_candidates` cá»§a `inventory_repo.py` tá»« `GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0` thÃ nh `il.on_hand_quantity > 0`. Äiá»u nÃ y kháº¯c phá»¥c lá»—i khi sáº£n pháº©m Ä‘Ã£ Ä‘Æ°á»£c giá»¯ hÃ ng (reserved) cho Ä‘Æ¡n hÃ ng hiá»‡n táº¡i, lÃ m cho tá»“n kháº£ dá»¥ng táº¡m thá»i báº±ng 0 vÃ  dáº«n tá»›i viá»‡c dropdown chá»n ká»‡ bá»‹ trá»‘ng (khÃ´ng hiá»ƒn thá»‹ ká»‡ nÃ o Ä‘á»ƒ bá»‘c hÃ ng).
- **Cáº£i tiáº¿n UI dropdown chá»n ká»‡**: MÃ n phiáº¿u xuáº¥t kho (`AdminInventoryOutboundsTab.tsx`) hiá»ƒn thá»‹ chi tiáº¿t cáº£ sá»‘ lÆ°á»£ng thá»±c táº¿ trÃªn ká»‡ (`Tá»“n`) vÃ  sá»‘ lÆ°á»£ng cÃ²n dÆ° chÆ°a giá»¯ (`Kháº£ dá»¥ng`) theo Ä‘á»‹nh dáº¡ng `Ká»‡ - TÃªn ká»‡ (Tá»“n: X | Kháº£ dá»¥ng: Y)` Ä‘á»ƒ nhÃ¢n viÃªn kho náº¯m thÃ´ng tin rÃµ rÃ ng.
- **RÃ ng buá»™c sá»‘ lÆ°á»£ng xuáº¥t kho**:
  - Bá»• sung validation táº¡i frontend cháº·n viá»‡c báº¥m `Cáº­p nháº­t` (lÆ°u nhÃ¡p) náº¿u tá»•ng sá»‘ lÆ°á»£ng Ä‘Ã£ chá»n trÃªn cÃ¡c ká»‡ vÆ°á»£t quÃ¡ sá»‘ lÆ°á»£ng yÃªu cáº§u cá»§a dÃ²ng sáº£n pháº©m.
  - Hiá»ƒn thá»‹ thÃªm thÃ´ng bÃ¡o cáº£nh bÃ¡o mÃ u Ä‘á» trá»±c quan `(VÆ°á»£t quÃ¡ sá»‘ lÆ°á»£ng yÃªu cáº§u!)` á»Ÿ dÃ²ng tráº¡ng thÃ¡i khi sá»‘ lÆ°á»£ng Ä‘Ã£ chá»n lá»›n hÆ¡n sá»‘ lÆ°á»£ng yÃªu cáº§u.
## Cập nhật 2026-06-29 - Kiểm thử luồng nhập kho trên database cô lập

- Bổ sung luồng lập phiếu nhập, tách người lập/người duyệt, hoàn tất phiếu, kiểm tra tồn sản phẩm và read-model tồn kho.
- Sửa câu lệnh tạo lô nhập kho ép kiểu UUID rõ ràng cho `product_id`/`variant_id`, tránh lỗi PostgreSQL `DatatypeMismatchError` khi hoàn tất phiếu có biến thể.
- Hai script kiểm tra kho cũ bị chặn nếu database không có tiền tố `project_test_`.
- Verification: pytest chạy toàn bộ luồng API và đối chiếu trực tiếp `inventory_documents`, `products` và API `/admin/inventory/levels`.
# Cập nhật 2026-06-30 - Lọc sổ kho theo luồng định đoạt hàng lỗi

- API `GET /admin/inventory/ledger` nhận thêm query `reason` để lọc các log định đoạt hàng lỗi được ghi từ hậu mãi: `RTV_COMPLETED`, `LIQUIDATED`, `SCRAP`, `OUT_OF_SYSTEM`.
- Service tồn kho validate `reason` theo danh sách trạng thái định đoạt hợp lệ trước khi chuyển xuống repository.
- Repository sổ kho lọc trực tiếp theo `inventory_adjustment_logs.reason`, giữ nguyên các bộ lọc hiện có theo ngày, sản phẩm, tìm kiếm và loại giao dịch.
- Màn admin tồn kho thêm dropdown `Lý do định đoạt` trong tab sổ kho và hiển thị badge phụ trên dòng log RTV/thanh lý/hủy/xuất khỏi hệ thống.
- Mục tiêu: nhân viên kho/kế toán có thể truy vết các quyết định xử lý IMEI lỗi từ hậu mãi ngay trong sổ kho mà không phải tìm bằng mã chứng từ thủ công.
