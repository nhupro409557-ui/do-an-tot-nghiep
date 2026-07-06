# Inventory Management Notes

## Cập nhật 2026-07-06 - Báo cáo đối soát nâng cao và sinh lịch kiểm kê đến hạn (Giai đoạn 3)

- **Mở rộng báo cáo đối soát** (`list_inventory_reconciliation_rows` tại `overview.py` repo):
  - Thêm kiểm tra **Tồn bán được lệch với tổng kệ bán được** (`SELLABLE_STOCK_MISMATCH`).
  - Thêm kiểm tra **Tồn kệ lệch với tổng lô còn lại** (`LOT_QUANTITY_MISMATCH`).
  - Thêm kiểm tra **Giữ chỗ reserved lệch với lượng định danh đang RESERVED** (`RESERVED_QUANTITY_MISMATCH`).
  - Thêm kiểm tra **Cặp định danh IMEI1-Serial bị lệch vị trí/trạng thái trong kho** (`IDENTIFIER_PAIR_MISMATCH`).
  - Thêm kiểm tra **Chứng từ hoàn tất nhưng không thấy ghi sổ kho** (`DOCUMENT_LEDGER_MISMATCH`).
  - Sửa lỗi bất tương thích kiểu dữ liệu (`UNION types character varying and jsonb cannot be matched`) bằng cách cast trường `variant_configuration` rỗng thành `NULL::text`.
- **Sinh danh sách kiểm kê đến hạn từ `cycleCountDays`**:
  - Thêm API route `GET /api/admin/inventory/stock-counts/due` tự động tìm và gợi ý các sản phẩm cần kiểm kê định kỳ dựa trên ngày kiểm kê cuối cùng hoặc ngày tạo sản phẩm.
- **Verification**:
  - Viết mới test case `test_advanced_inventory_reconciliation_report_mismatches` kiểm thử toàn diện các loại đối soát mới.
  - Viết mới test case `test_cycle_count_due` kiểm thử API gợi ý kiểm kê đến hạn.
  - Tất cả các bài test tích hợp liên quan chạy thành công 100%.

## Cập nhật 2026-07-06 - Đồng bộ tồn kho cha-con, sửa lỗi router và scope bug đảo phiếu (Giai đoạn 1)

- Khắc phục lỗi cú pháp trùng lắp tham số signature của API router tại `admin_inventory.py` và dọn dẹp mã thừa/lặp ở `adminInventoryApi.ts` để khôi phục biên dịch frontend và hoạt động của các route status.
- Sửa lỗi scope bug rò rỉ biến trong hàm `reverse_inventory_receipt` tại `receipt_posting.py` để đồng bộ đúng cho từng sản phẩm của phiếu nhập được đảo.
- Bổ sung tự động đồng bộ tồn kho sản phẩm cha từ các biến thể con (`sync_parent_price_from_variants`) khi xuất kho (`_post_inventory_outbound`), checkout (`_ship_order_items`) và hoàn kho (`_restock_order_items`).
- Gộp xuất kho vật lý và cập nhật đơn hàng thành một transaction nguyên tử duy nhất bằng cách bỏ commit sớm trong `post_outbound_document` và hỗ trợ chạy trong transaction hiện hữu cho `CompleteOrderUseCase`.
- Tạo file migration `057_update_identifier_pairs_foreign_key_cascade.sql` thêm `ON UPDATE CASCADE` cho các ràng buộc khoá ngoại của `product_identifier_pairs` sang `product_imeis` và `product_serial_numbers`.
- Đồng bộ lô hàng FIFO (`inventory_lots`) khi duyệt phiếu điều chỉnh tồn kho (`ADJUSTMENT`) bằng cách gọi `consume_inventory_lots_fifo` hoặc `create_inventory_lot_for_reconciliation`.
- Áp dụng cơ chế Maker-Checker (chặn tự phê duyệt) cho toàn bộ chứng từ kho (kiểm kê, điều chỉnh tồn, chuyển kệ, giữ nội bộ, xử lý tồn, điều chỉnh giá vốn) và yêu cầu sửa mã/vị trí định danh.
- Bổ sung kiểm tra QC theo từng dòng sản phẩm (Receipt Line-level QC) lưu trữ trong metadata của dòng chứng từ.
- Thêm cơ chế chặn xuất bán trực tiếp từ kệ không được phép bán (kệ inactive hoặc kệ phi thương mại như QC, DAMAGED, RETURN, WARRANTY).
- Thêm kiểm tra chặn điều chuyển các IMEI/Serial từ kệ không bán được về kệ bán được nếu phiếu nhập gốc chưa đạt QC (chất lượng khác PASSED).
- Hỗ trợ thực nhận thiếu/thừa cho cả hàng không quản lý mã định danh bằng cách cập nhật `submit_inventory_receipt_imeis` và schema `InventoryReceiptImeiLinePayload`.
- Thêm bảo vệ kệ đang có tồn kho: Chặn thay đổi mục đích (`purpose`), chặn khóa kệ (`isActive`), và chặn giảm dung lượng kệ xuống dưới mức thể tích đang sử dụng thực tế.
- Thêm thao tác phát hành lại phiếu xuất đã hủy (cho phép chuyển trạng thái phiếu xuất từ CANCELLED về DRAFT).
- Verification: Chạy thành công 100% bộ test suite backend (75 passed) và biên dịch frontend thành công không có lỗi.

## Cập nhật 2026-07-05 - Hoàn thiện các ràng buộc và logic tồn kho

- Chặn tạo phiếu điều chỉnh tồn (`ADJUSTMENT`) đối với sản phẩm quản lý IMEI/Serial (thực hiện kiểm tra chính sách trong `create_inventory_adjustment_request`).
- Đồng bộ tự động lô hàng (`inventory_lots`) khi duyệt phiếu Kiểm kê (`STOCK_COUNT`) có chênh lệch:
  + Nếu chênh lệch thừa (`variance > 0`): gọi `create_inventory_lot_for_reconciliation` để chèn lô mới với giá vốn bình quân từ level.
  + Nếu chênh lệch thiếu (`variance < 0`): gọi `consume_inventory_lots_fifo` để tiêu thụ lượng thiếu hụt theo FIFO tại kệ đó. Lỗi thiếu lô (ví dụ dữ liệu seed cũ không có lô) được xử lý bỏ qua gracefully để đảm bảo phiếu kiểm kê hoàn tất suôn sẻ.
- Đối soát khớp cặp định danh thiết bị khi lập phiếu Chuyển kệ (`TRANSFER`):
  + Đối với sản phẩm quản lý cả hai (IMEI và Serial), bắt buộc IMEI và Serial gửi lên phải khớp cặp hoàn toàn theo bảng `product_identifier_pairs`, ngăn việc vỡ cặp hoặc chuyển lệch.
- Khóa và mở khóa mã định danh cụ thể khi lập phiếu Giữ kho nội bộ (`INTERNAL_HOLD`):
  + Cập nhật API schema nhận `imeis` và `serialNumbers` tùy chọn ở dòng phiếu giữ.
  + Bắt buộc truyền đầy đủ IMEI/Serial tương ứng với số lượng khi sản phẩm bật quản lý định danh.
  + Khi duyệt phiếu (`APPROVED`), khóa các IMEI/Serial được chọn sang trạng thái `RESERVED` tại kệ để cách ly khỏi các luồng bán hàng/điều chuyển. Khi giải phóng (`COMPLETED`), trả các mã này về trạng thái `IN_STOCK`.
- Verification: Viết mới bộ test case tích hợp `backend/tests/test_26_inventory_custom_constraints.py` bao phủ toàn bộ các ràng buộc trên; chạy test suite (`test_13`, `test_15`, `test_17`, `test_26`) thành công 100% (8 test passed).

## Cập nhật 2026-07-05 - Sửa lỗi cú pháp phiếu kiểm kê lệch thừa

- Loại bỏ hai dòng thừa còn sót trong nhánh tạo lô khi kiểm kê lệch thừa tại `inventory/documents.py`.
- Thay đổi chỉ khôi phục khả năng import/compile backend, không đổi công thức tính variance, cập nhật tồn hoặc ghi log kiểm kê.

## Cập nhật 2026-07-05 - Phiếu xuất hậu mãi nhiều dòng và định danh serial

- `insert_after_sales_replacement_outbound` nhận danh sách dòng thay thế thay vì một sản phẩm/IMEI đơn lẻ; một hồ sơ return/warranty vẫn tạo một phiếu `OUTBOUND` nhưng có thể chứa nhiều dòng sản phẩm và nhiều vị trí xuất.
- Metadata header/dòng phiếu xuất lưu `replacementImeis`, `replacementSecondaryImeis`, `replacementSerialNumbers`; read-model outbound trả thêm IMEI2 để giao diện admin đối soát đủ cặp định danh.
- Khi hoàn tất đổi/thay, backend trừ `inventory_levels`, `products.stock_quantity` và `product_variants.stock_quantity` theo số máy vật lý; IMEI2/serial đi kèm không bị tính thành một máy riêng.
- Serial thay thế được chuyển sang `SOLD` và ghi `soldOrderId/orderId` trong `service_payload`; serial/IMEI gốc của khách được đánh dấu lỗi để tiếp tục luồng định đoạt hậu mãi.
- Verification: full backend đạt 66 test, riêng `test_07_after_sales_flow.py` đạt 8 test; frontend lint/build pass sau khi màn phiếu xuất hiển thị thêm IMEI2.

## Cập nhật 2026-07-05 - Liên kết phiếu xuất kho với hồ sơ hậu mãi

- Migration `053_after_sales_inventory_document_links.sql` bổ sung `return_request_id` và `warranty_request_id` cho `inventory_documents`, kèm ràng buộc mỗi phiếu chỉ thuộc tối đa một loại hồ sơ.
- Unique partial index bảo đảm mỗi hồ sơ return/warranty chỉ có một phiếu `OUTBOUND` chưa hủy.
- Khi cấp máy đổi/thay thế, backend tạo phiếu xuất `COMPLETED` và một dòng hàng chứa IMEI, vị trí xuất, giá vốn bình quân cùng metadata truy vết; phiếu có `stockMutationSkipped = true` vì tồn đã được trừ trong transaction hậu mãi.
- Read-model phiếu xuất trả thêm `afterSalesType` và `afterSalesRequestCode`, hỗ trợ tìm theo mã hồ sơ hậu mãi; màn admin hiển thị mã này ở danh sách và chi tiết.
- Sổ điều chỉnh `AFTER_SALES_REPLACEMENT` dùng mã hồ sơ hậu mãi làm `reference_code`, đáp ứng ràng buộc bắt buộc và giúp đối soát với phiếu xuất.
- Verification: hai test tích hợp return/warranty xác nhận tồn giảm đúng một lần và chỉ tạo một phiếu xuất liên kết; full backend đạt 65 test, frontend lint và build production đều đạt.

## Cập nhật 2026-07-05 - Ràng buộc trả trước công nợ từ phiếu nhập

- Phiếu nhập mua hàng `NK_MUA` không được hoàn tất nếu `paidAmount` khai báo lớn hơn tổng giá trị thực nhận.
- Lỗi được phát hiện trong cùng transaction hoàn tất phiếu, nên không post tồn kho và không tạo công nợ khi dữ liệu trả trước sai.

## Cập nhật 2026-07-05 - Toàn vẹn định danh khi đảo và hủy phiếu nhập

- Đảo phiếu nhập chỉ được thực hiện khi IMEI1, IMEI2 và serial number vẫn thuộc đúng phiếu, còn ở trạng thái có thể thu hồi và chưa rời khỏi kệ nhận ban đầu.
- Phiếu nhập cách ly tại kệ QC/hàng trả/hàng lỗi/bảo hành được đảo theo tồn vật lý tại `inventory_levels`, không trừ nhầm `product_variants.stock_quantity` vì tồn bán được chưa từng được cộng.
- Khi đảo thành công, cả IMEI1, IMEI2 và serial number chuyển sang `REVERSED`, bỏ `location_id`; cặp `product_identifier_pairs` được giữ để truy vết lịch sử và chứng từ đảo lưu đầy đủ `secondaryImeis`.
- Phiếu gốc được cập nhật thật sang `REVERSED`, lưu người/thời điểm đảo và audit log; trước đây API chỉ trả trạng thái này trong response nhưng chưa cập nhật chứng từ gốc.
- Khi hủy phiếu trước hoàn tất, backend xóa rõ ràng cặp định danh pending trước khi xóa IMEI/serial chờ, tránh để lại quan hệ mồ côi.
- Migration `050_inventory_identifier_reversed_status.sql` bổ sung `REVERSED` vào constraint IMEI/serial hiện hành; đồng thời sửa migration hậu mãi `023` để clean replay không ghi đè mất trạng thái này.
- Verification: migration replay pass; `py_compile` pass; nhóm `test_06_inventory_receipt_flow.py`, `test_19_inventory_reconciliation_report.py` và `test_22_supplier_account_payables_flow.py` pass `6` test; `remaining_test_databases=0`.

## Cập nhật 2026-07-05 - Hoàn thiện IMEI2 trong phiếu nhập

- Metadata dòng phiếu nhập lưu và trả về đầy đủ `secondaryImeis`; màn hình chi tiết hiển thị IMEI2 cùng IMEI1 và serial number.
- Khi hoàn tất phiếu, backend kiểm tra trạng thái giữ chỗ của cả IMEI1/IMEI2, gán cùng kệ nhận và kích hoạt cùng trạng thái theo mục đích kệ. Số lượng nhập kho vẫn tính theo số máy/IMEI1, không cộng IMEI2 thành một máy riêng.
- Import Excel phía admin báo lỗi rõ ràng khi file không có sheet, không có mã hoặc không đọc được; input được đặt lại để có thể chọn lại chính file vừa nhập sai.
- E2E dùng file `.xlsx` thật để kiểm tra file rỗng, chọn lại file, nhập đủ IMEI1/IMEI2/serial và đọc lại các mã trong chi tiết phiếu.
- Verification: `py_compile` pass; `test_06_inventory_receipt_flow.py` pass `3` test; frontend `npm run lint` và `npm run build` pass; Playwright pass `5` test; `remaining_test_databases=0`.

## Cập nhật 2026-07-04 - E2E import Excel cho phiếu nhập

- `run_test_server.py` seed một phiếu `PROCESSING_IMEI` có hai IMEI dự kiến trong database `project_test_*`, đồng thời cấp `inventory:adjust` cho tài khoản admin E2E.
- Playwright tạo file `.xlsx` thật trong bộ nhớ, xác nhận trình duyệt chưa tải `xlsx` khi chỉ mở tab nhập kho và chỉ yêu cầu module sau thao tác chọn file.
- Sau khi import, E2E kiểm tra textarea nhận đủ hai IMEI, API lưu mã trả `200` và phiếu chuyển sang `PENDING_APPROVAL`.
- Bài test không hoàn tất phiếu nên không cộng tồn; các mã chỉ tồn tại ở trạng thái chờ trong database tạm và bị xóa cùng database sau suite.
- Verification: `py_compile`, `npm run lint`, bài admin E2E chạy riêng pass, full `npm run test:e2e` pass `5` test và `remaining_test_databases=0`.

## Cập nhật 2026-07-04 - Chuẩn hóa lỗi tồn kho còn lại

- Chuẩn hóa lỗi không tìm thấy sản phẩm/biến thể và lỗi số lượng tồn kho âm sang tiếng Việt có dấu.
- Không đổi logic cập nhật tồn kho, settings tồn kho hoặc ghi log điều chỉnh.
- Verification: `py_compile` và test inventory liên quan pass.

## Cập nhật 2026-07-04 - Dọn định nghĩa schema inventory trùng

- Xóa block định nghĩa trùng của `InventoryStockCountStatusPayload`, `InventoryAdjustmentRequestLinePayload`, `InventoryAdjustmentRequestPayload` và `InventoryAdjustmentRequestStatusPayload` trong `admin/inventory.py`.
- Giữ bản định nghĩa đầu tiên trước nhóm schema chuyển kho để không đổi contract API, chỉ loại bỏ shadowing gây khó bảo trì.
- Verification: `py_compile` và các test inventory liên quan pass.

## Cập nhật 2026-07-04 - Chuẩn hóa endpoint trạng thái phiếu xuất kho

- `PATCH /admin/inventory/outbounds/{document_no}/status` nay đọc đúng payload `status`: `COMPLETED` đi qua luồng post xuất kho hiện có, `CANCELLED` hủy phiếu và ghi `cancelled_at/cancelled_by`.
- Khi hủy phiếu xuất, backend bắt buộc có `cancelReason`, lưu vào `note` và không trừ tồn kho hay đẩy đơn hàng sang `SHIPPED`.
- Tạo phiếu xuất tự động cho đơn hàng bỏ qua các phiếu `CANCELLED`, tránh coi phiếu đã hủy là phiếu còn hiệu lực.
- Verification: bổ sung test hủy phiếu xuất nháp, xác nhận tồn kho không bị trừ và phiếu có thời điểm hủy.

## Cập nhật 2026-07-04 - Phiếu nhập phát sinh công nợ nhà cung cấp

- Phiếu nhập mua hàng `NK_MUA` khi chuyển sang `COMPLETED` sẽ tạo/cập nhật công nợ nhà cung cấp trong module `account_payables`.
- Tổng công nợ lấy theo số lượng thực nhận và `unit_cost` của từng dòng phiếu nhập; phiếu nhập không có giá trị nhập hoặc không phải `NK_MUA` sẽ không tạo công nợ.
- Điều khoản thanh toán được lưu trong `inventory_documents.metadata`: nhà cung cấp, số hóa đơn, ngày hóa đơn, hình thức thanh toán, số ngày được nợ, ngày đến hạn, số đã trả trước và ghi chú công nợ.
- Đảo phiếu nhập sẽ hủy công nợ nguồn nếu có, tránh để tồn kho đã đảo nhưng công nợ vẫn mở.
- Chi tiết thiết kế và API nằm trong `backend/ACCOUNT_PAYABLE_MANAGEMENT_NOTES.md`.
- Verification: migration `049_supplier_account_payables.sql` chạy thành công; `test_22_supplier_account_payables_flow.py` pass; `test_06_inventory_receipt_flow.py` pass; full backend `pytest -q` pass 50 test; frontend `npm run lint` pass; Playwright kiểm tra tab công nợ phát sinh từ phiếu nhập và ghi nhận thanh toán trên database E2E pass ở desktop/mobile; full frontend e2e `npx playwright test --project=chromium` pass 4 test.

## Cập nhật 2026-07-03 - Reservation hàng cũ không đi qua FIFO hàng mới

- Checkout hàng cũ dùng trạng thái của `used_devices` để giữ/bán máy: `READY_FOR_SALE -> RESERVED -> SOLD`.
- Khi đơn hàng cũ bị hủy hoặc thanh toán lỗi trước giao hàng, hệ thống trả thiết bị về `READY_FOR_SALE`.
- Dòng `order_items.used_device_id` bị bỏ qua khi tạo phiếu xuất kho tự động và khi trừ `inventory_levels`, nên không ảnh hưởng tồn hàng mới.
- Sửa nhánh hủy đơn để cập nhật phiếu xuất bằng `cancelled_at/cancelled_by` đúng schema hiện tại thay vì cột `updated_at` không tồn tại.
- Verification: full backend pass 48 test.

## Cập nhật 2026-07-03 - Tách kho hàng cũ khỏi tồn hàng mới

- Bổ sung mục đích vị trí `USED` và vị trí mặc định `CU-01-01` cho thiết bị cũ đã qua thẩm định.
- Thiết bị cũ được lưu theo từng IMEI trong `used_devices` và chỉ tham chiếu `inventory_locations`; không ghi vào `inventory_levels`, `inventory_lots` hoặc `products/product_variants.stock_quantity`.
- Cách tách này ngăn luồng reservation/FIFO của đơn hàng mới phân bổ nhầm thiết bị cũ có cùng sản phẩm hoặc biến thể.
- Form quản lý vị trí kho nhận diện dãy `CU` là `USED`, tránh đổi nhầm thành `STORAGE` khi admin chỉnh sửa.
- Workflow test xác nhận sau khi thu mua thiết bị cũ, tổng `inventory_levels` của sản phẩm/biến thể gốc vẫn bằng `0`.

## Cập nhật 2026-07-03 - Bổ sung IMEI/serial cho tồn kho đã nhập

- Thêm script `backend/scripts/backfill_missing_inventory_imeis.py` để bổ sung IMEI và serial number còn thiếu cho các dòng `inventory_levels` đang có tồn.
- Script mặc định chỉ xử lý sản phẩm có policy IMEI/serial đang bật; khi cần đối soát dữ liệu seed/demo đã nhập kho nhưng chưa bật policy, chạy thêm `--include-untracked`.
- Script tạo IMEI 15 chữ số có check digit, tạo serial hợp lệ khi thiếu, gắn `location_id`, `source_reference = BACKFILL-IMEI-20260703` và ghép `product_identifier_pairs` theo từng đơn vị tồn khi có đủ IMEI/serial.
- Đã chạy backfill local cho dữ liệu hiện tại: tạo 6.492 IMEI, 2.024 serial number và 6.492 cặp IMEI-serial; không thay đổi số lượng tồn kho.
- Verification: `python -m py_compile scripts/backfill_missing_inventory_imeis.py` pass; chạy lại script với `--include-untracked` trả 0 ứng viên; báo cáo đối soát tồn/mã trả `totalIssues = 0`.

## Cập nhật 2026-07-03 - Chọn IMEI/serial khi lập phiếu chuyển kệ

- Modal tạo phiếu chuyển kệ không còn nhập tay IMEI/serial bằng textarea. UI hiển thị bốn bảng: IMEI hiện tại, IMEI cần chuyển, serial hiện tại và serial cần chuyển.
- Khi tick mã ở bảng hiện tại, mã được chuyển sang bảng cần chuyển; khi bỏ tick ở bảng cần chuyển, mã quay lại bảng hiện tại. Payload gửi API vẫn giữ dạng danh sách `imeis` và `serialNumbers` như cũ nên không đổi backend.
- Số lượng trên dòng chuyển tự cập nhật theo số mã đã chọn, giới hạn bởi tồn tối đa trên kệ nguồn.
- Modal tạo phiếu xử lý tồn dùng cùng cơ chế chọn mã: IMEI/serial hiện tại chuyển sang IMEI/serial xử lý khi tick, thay cho nhập tay bằng textarea.
- Verification: frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Hoàn thiện nhập hàng cách ly sau QC

- Phiếu nhập có `quarantine = true` không còn bị chặn hoàn tất chỉ vì QC chưa `PASSED`; phiếu vẫn đi qua `DRAFT -> APPROVED -> COMPLETED` như các phiếu nhập khác.
- Khi bật cách ly, backend bắt buộc mọi dòng nhập phải chọn kệ nghiệp vụ không bán được: `QC`, `RETURN`, `DAMAGED` hoặc `WARRANTY`. Nếu gửi nhầm kệ `STORAGE/VIRTUAL`, API chặn trước khi lưu hoặc hoàn tất.
- Khi hoàn tất phiếu cách ly, hệ thống vẫn cộng tồn vật lý tại `inventory_levels`, tạo `inventory_lots` và ghi log nhập kho, nhưng không cộng `products.stock_quantity`/`product_variants.stock_quantity` bán được.
- IMEI/serial pending inbound được kích hoạt theo mục đích kệ nhận: `QC -> INSPECTION_PENDING`, `RETURN -> RETURNED`, `DAMAGED -> DEFECTIVE_RETURNED`, `WARRANTY -> IN_WARRANTY`, còn kệ bán được vẫn là `IN_STOCK`.
- Đồng bộ lại constraint trạng thái IMEI/serial trong migration hậu mãi để chấp nhận `PENDING_INBOUND`; bản ghi pending inbound dùng `received_at = NOW()` để phù hợp schema hiện tại.
- Đảo phiếu nhập cho phép đảo cả các mã còn nằm trong trạng thái kệ nghiệp vụ kể trên, tránh khóa rollback đối với phiếu cách ly đã hoàn tất.
- Frontend form nhập kho đổi bộ lọc kệ khi bật `Cách ly hàng`: chỉ hiện kệ QC/hàng trả/hàng lỗi/bảo hành và tự xóa lựa chọn kệ cũ nếu không còn hợp lệ.
- Sau QC đạt, nhân viên dùng phiếu chuyển kệ/trạng thái hiện có để chuyển hàng từ kệ cách ly về kệ bán được; lúc đó hệ thống mới tăng tồn bán được.
- Verification: backend `py_compile` pass; full nhóm inventory test gồm `test_06`, `test_12` đến `test_20` pass tổng cộng 13 test; full backend `pytest backend/tests -q` pass 47 test; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Phiếu điều chỉnh giá vốn

- Thêm phiếu `COST_ADJUSTMENT` cho nghiệp vụ điều chỉnh giá vốn tách riêng khỏi điều chỉnh tồn vật lý.
- Phiếu dùng vòng đời `DRAFT -> APPROVED -> COMPLETED/CANCELLED`; tạo và duyệt phiếu chưa thay đổi tồn, chỉ khi `COMPLETED` mới cập nhật giá vốn.
- Khi hoàn tất, backend cập nhật `inventory_levels.average_unit_cost` tại đúng sản phẩm/biến thể/kệ và cập nhật `inventory_lots.unit_cost` cho các lô còn tồn được chọn. Nếu frontend không gửi danh sách lô riêng, phiếu áp dụng giá vốn mới cho toàn bộ lô active còn tồn tại kệ đó.
- Phiếu khóa lại tồn tại kệ khi hoàn tất và chặn nếu `on_hand_quantity` đã thay đổi so với lúc lập phiếu, buộc lập lại phiếu để tránh chỉnh giá trên dữ liệu tồn đã khác.
- Số lượng tồn, reserved, IMEI/serial và vị trí kệ không thay đổi. Sổ kho ghi log `ADJUSTMENT` với `delta = 0`, `reason = COST_ADJUSTMENT`, `unit_cost` là giá vốn mới để truy vết.
- Frontend thêm API, danh sách `Phiếu điều chỉnh giá vốn`, nút `Giá vốn` trong modal danh sách kệ, modal tạo phiếu và modal xem chi tiết giá cũ/giá mới/lô áp dụng.
- Verification: migration `045_inventory_cost_adjustments.sql` chạy thành công; backend `py_compile` pass; `test_15_inventory_transfer_workflow.py`, `test_16_inventory_state_transfer_workflow.py`, `test_17_inventory_internal_hold_workflow.py`, `test_18_inventory_disposal_workflow.py`, `test_19_inventory_reconciliation_report.py`, `test_20_inventory_cost_adjustment_workflow.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Báo cáo đối soát lệch tồn và mã

- Thêm API `GET /admin/inventory/reports/reconciliation` để rà soát các lệch giữa `inventory_levels`, `product_imeis` và `product_serial_numbers`.
- Báo cáo hiện gom bốn nhóm lỗi chính: tồn kệ lớn hơn số mã đang `IN_STOCK`, mã `IN_STOCK` chưa có `location_id`, mã có kệ nhưng kệ không có `inventory_levels.on_hand_quantity > 0`, và mã đã rời kho/kết thúc vòng đời nhưng vẫn còn `location_id`.
- Với sản phẩm có nhiều IMEI trên cùng thiết bị, phần đếm so với tồn kệ ưu tiên IMEI chính (`is_primary = TRUE`) để tránh báo lệch giả khi một sản phẩm có IMEI1/IMEI2.
- API hỗ trợ lọc `search` và `issueType`, trả `summary` theo nhóm lỗi cùng danh sách chi tiết sản phẩm, biến thể, kệ, mã định danh, trạng thái và ghi chú xử lý.
- Frontend tab quản lý tồn kho có thêm tab `Đối soát`, thẻ tổng hợp số lỗi theo nhóm và bảng chi tiết để nhân viên kho biết cần gán kệ, sửa tồn level, hoặc dọn `location_id` của mã đã bán/hủy/xuất khỏi hệ thống.
- Báo cáo chỉ đọc dữ liệu, không tự sửa tồn hoặc mã định danh; các trường hợp sai lệch vẫn phải xử lý qua phiếu/yêu cầu có duyệt phù hợp.
- Verification: backend `py_compile` pass; `test_15_inventory_transfer_workflow.py`, `test_16_inventory_state_transfer_workflow.py`, `test_17_inventory_internal_hold_workflow.py`, `test_18_inventory_disposal_workflow.py`, `test_19_inventory_reconciliation_report.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Phiếu hủy/thanh lý/xuất khỏi hệ thống

- Thêm phiếu `DISPOSAL` cho nghiệp vụ xử lý tồn cuối: `SCRAP`, `LIQUIDATED`, `OUT_OF_SYSTEM`.
- Phiếu bắt buộc qua `DRAFT -> APPROVED -> COMPLETED/CANCELLED`; tạo và duyệt phiếu chưa trừ tồn, chỉ khi `COMPLETED` mới ghi nhận xử lý thực tế.
- Khi hoàn tất, backend trừ `inventory_levels.on_hand_quantity`, trừ `inventory_lots` theo FIFO tại đúng kệ và ghi movement lô.
- Với hàng quản lý IMEI/serial, phiếu bắt buộc nhập đủ mã theo số lượng; khi hoàn tất IMEI/serial được chuyển sang trạng thái xử lý cuối và `location_id = NULL`.
- Nếu IMEI có cặp IMEI1/IMEI2 trong `product_identifier_pairs`, IMEI còn lại được cập nhật theo cùng trạng thái dù phiếu chỉ nhập IMEI chính.
- Nếu hàng đang ở kệ bán được (`STORAGE/VIRTUAL`), hệ thống giảm `products.stock_quantity`/`product_variants.stock_quantity`; nếu hàng đã nằm ở kệ nghiệp vụ không bán được thì không trừ tồn bán được lần nữa.
- Frontend tab tồn kho có nút `Xử lý tồn` trong danh sách kệ, danh sách `Phiếu xử lý tồn`, modal tạo phiếu, xem chi tiết, duyệt và hoàn tất.
- Verification: migration `044_inventory_disposals.sql` chạy thành công; backend `py_compile` pass; `test_15_inventory_transfer_workflow.py`, `test_16_inventory_state_transfer_workflow.py`, `test_17_inventory_internal_hold_workflow.py`, `test_18_inventory_disposal_workflow.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Khóa/mở khóa tồn nội bộ

- Thêm phiếu `INTERNAL_HOLD` cho nghiệp vụ giữ tồn không gắn với đơn hàng, tách rõ khỏi `inventory_reservations` của đơn/hậu mãi.
- Phiếu hỗ trợ loại giữ `QC_HOLD`, `CLAIM_HOLD`, `INTERNAL_HOLD` và bắt buộc qua luồng `DRAFT -> APPROVED -> COMPLETED/CANCELLED`.
- Tạo phiếu nháp chưa làm thay đổi tồn. Khi duyệt, backend tăng `inventory_levels.reserved_quantity` theo đúng sản phẩm/biến thể/kệ; khi hoàn tất, backend giảm lại số đang giữ để mở khóa tồn.
- Backend kiểm tra lại tồn khả dụng tại thời điểm duyệt, chặn giữ vượt `on_hand_quantity - reserved_quantity`; khi mở khóa cũng chặn nếu số đang giữ tại kệ không đủ.
- Read-model tồn kho cộng số giữ theo `inventory_levels.reserved_quantity` vào `reservedStock`, đồng thời từng kệ trả thêm `reservedQuantity` và `availableQuantity`.
- FIFO/gợi ý xuất kho tự giảm theo số giữ vì đã dùng `inventory_levels.reserved_quantity`; hold nội bộ không làm đổi tổng tồn vật lý, lô, IMEI hoặc serial.
- Frontend tab tồn kho có nút `Giữ nội bộ` trong danh sách kệ, danh sách `Phiếu giữ nội bộ`, modal tạo phiếu, xem chi tiết, duyệt giữ và mở khóa.
- Verification: migration `043_inventory_internal_holds.sql` chạy thành công; backend `py_compile` pass; `test_15_inventory_transfer_workflow.py`, `test_16_inventory_state_transfer_workflow.py`, `test_17_inventory_internal_hold_workflow.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Điều chuyển trạng thái hàng theo mục đích kệ

- Phiếu chuyển kệ dùng chung cho nghiệp vụ `CHUYEN_TRANG_THAI` và vẫn bắt buộc qua `DRAFT -> APPROVED -> COMPLETED`; tạo hoặc duyệt phiếu chưa làm thay đổi dữ liệu thực tế.
- Khi hoàn tất, trạng thái IMEI/serial được suy ra từ mục đích kệ đích: `STORAGE/VIRTUAL -> IN_STOCK`, `DAMAGED -> DEFECTIVE_RETURNED`, `WARRANTY -> IN_WARRANTY`, `QC -> INSPECTION_PENDING`, `RETURN -> RETURNED`.
- Backend không nhận tùy ý trạng thái mã trái với mục đích kệ, tránh trường hợp mã báo bán được nhưng đang nằm ở kệ lỗi/cách ly.
- Chuyển giữa kệ bán được (`STORAGE/VIRTUAL`) và kệ nghiệp vụ sẽ tăng hoặc giảm `products.stock_quantity`/`product_variants.stock_quantity`; tổng `inventory_levels.on_hand_quantity` vẫn không đổi vì hàng còn tồn vật lý trong kho.
- `inventory_levels`, `inventory_lots`, IMEI1, IMEI2 cùng cặp và serial được chuyển đồng thời khi hoàn tất. IMEI2 tự đi theo cặp dù phiếu chỉ nhập IMEI chính.
- FIFO gợi ý xuất kho chỉ đọc tồn ở kệ `STORAGE/VIRTUAL`; kệ lỗi, bảo hành, cách ly và hàng trả không được đưa vào gợi ý xuất bán.
- Modal danh sách kệ có hành động `Chuyển trạng thái`; danh sách kệ nguồn/đích hiển thị thêm mục đích kệ để nhân viên chọn đúng khu vực.
- Verification: backend `py_compile` pass; `test_15_inventory_transfer_workflow.py` và `test_16_inventory_state_transfer_workflow.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-03 - Hoàn chỉnh phiếu chuyển kệ và gom/tách kệ

- Vòng đời phiếu chuyển kệ đổi thành `DRAFT -> APPROVED -> COMPLETED`; phiếu có thể chuyển sang `CANCELLED` từ `DRAFT` hoặc `APPROVED`.
- Bước `APPROVED` chỉ ghi nhận phê duyệt, chưa thay đổi tồn, IMEI/serial hoặc lô. Bước `COMPLETED` mới khóa và chuyển dữ liệu thực tế.
- Khi hoàn tất, backend tiếp tục kiểm tra tồn khả dụng và mã định danh tại kệ nguồn trước khi chuyển `inventory_levels`, IMEI và serial.
- Bổ sung `transfer_inventory_lots_fifo`: tách lượng cần chuyển từ các lô cũ nhất tại kệ nguồn, tạo lô con tại kệ đích, giữ nguyên ngày nhập, giá vốn, chứng từ nguồn và metadata truy vết lô gốc.
- Mỗi lần chuyển lô ghi hai movement `ADJUSTMENT` cho lô nguồn và lô đích; tổng `remaining_quantity` của SKU không đổi.
- UI phiếu chuyển kệ có hành động `Hoàn tất` riêng sau khi duyệt. Nút `Tách/chuyển` xử lý một phần số lượng; nút `Gom về đây` tạo phiếu nhiều dòng để gom cùng SKU từ các kệ khác về kệ đang chọn.
- Verification: backend `py_compile` pass; `test_15_inventory_transfer_workflow.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-02 - Yêu cầu gán lại vị trí IMEI/serial có duyệt

- Thêm bảng `inventory_identifier_location_requests` qua migration `042_inventory_identifier_location_requests.sql`, lưu loại mã, mã định danh, kệ hiện tại, kệ đề xuất, lý do, người yêu cầu, người duyệt và trạng thái `PENDING/APPROVED/CANCELLED`.
- API `/admin/inventory/identifier-location-requests` hỗ trợ xem danh sách, tạo yêu cầu và super admin duyệt hoặc hủy.
- Có thể tạo yêu cầu bằng ID của mã đang hiển thị hoặc nhập trực tiếp giá trị IMEI/serial đang chưa có `location_id`.
- Chỉ mã ở trạng thái `IN_STOCK` được đổi vị trí. Kệ đích phải đang hoạt động và phải có `inventory_levels.on_hand_quantity > 0` của đúng sản phẩm/biến thể.
- Khi duyệt, backend khóa cả yêu cầu và dòng IMEI/serial, kiểm tra lại giá trị mã, trạng thái và vị trí ban đầu trước khi chỉ cập nhật `location_id`.
- Nếu mã thuộc `product_identifier_pairs`, yêu cầu lưu thêm `identifier_pair_id`; khi duyệt hệ thống khóa và chuyển đồng thời IMEI1, IMEI2 và serial của cùng thiết bị sang kệ đích.
- Chỉ cho tồn tại một yêu cầu vị trí `PENDING` cho toàn bộ bộ mã ghép cặp, tránh hai yêu cầu từ IMEI và serial của cùng thiết bị chuyển về hai kệ khác nhau.
- Trước khi chuyển bộ mã, tất cả thành viên phải còn tồn tại và ở trạng thái `IN_STOCK`; nếu thiếu hoặc có mã không còn trong kho thì yêu cầu bị chặn duyệt.
- Nghiệp vụ này không thay đổi tồn tổng hoặc số lượng tại `inventory_levels`; yêu cầu trùng đang chờ duyệt cho cùng mã bị chặn.
- Frontend thêm nút `Đổi kệ` trên từng mã, thao tác gán IMEI/serial chưa có kệ vào kệ đang xem và bảng yêu cầu vị trí chờ duyệt.
- Verification: migration chạy thành công; backend `py_compile` pass; `test_14_inventory_identifier_location_requests.py` pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-02 - Kiểm kê theo kệ và mã quét

- Phiếu kiểm kê bắt buộc chọn một kệ đang hoạt động; backend lấy tồn kỳ vọng trực tiếp từ `inventory_levels` tại kệ, không tin số lượng kỳ vọng do frontend gửi lên.
- Khi duyệt, tồn tổng sản phẩm/biến thể được cập nhật theo `tồn tổng cũ + chênh lệch tại kệ`; không còn đặt tồn tổng bằng số thực đếm của riêng một kệ.
- Backend khóa duyệt nếu tồn tại kệ đã thay đổi sau khi lập phiếu hoặc nếu thực đếm nhỏ hơn số lượng đang giữ tại kệ.
- Dòng kiểm kê lưu IMEI/serial đã quét cùng danh sách mã thiếu và mã thừa trong metadata. Với hàng quản lý mã, `countedQuantity` được tính từ danh sách mã quét thay vì ô số lượng nhập tay.
- Phiếu có IMEI/serial thiếu hoặc thừa so với mã `IN_STOCK` thực tế tại kệ vẫn được lưu nháp để xem sai lệch, nhưng không được duyệt cho đến khi xử lý xong mã định danh.
- Frontend yêu cầu chọn kệ trước khi kiểm kê, hỗ trợ mở `Kiểm kê kệ` ngay từ danh sách kệ và hiển thị ô quét IMEI/serial theo chính sách sản phẩm.
- Sửa truy vấn khóa phiếu kiểm kê thành `FOR UPDATE OF d` để tránh lỗi PostgreSQL khi `LEFT JOIN` vị trí.
- Verification: backend `py_compile` pass; `test_13_inventory_stock_count_by_location.py` có 2 test pass; frontend `npm run lint` pass.

## Cập nhật 2026-07-02 - FIFO xuất kho chỉ gợi ý kệ

- API `GET /admin/inventory/issue-suggestions` không còn ưu tiên trả danh sách IMEI/serial theo FIFO; gợi ý xuất kho chỉ trả kệ, tồn khả dụng và số lượng nên lấy ở từng kệ.
- Auto-suggest trong phiếu xuất kho dùng FIFO theo kệ từ `list_level_issue_candidates`, có thể phân bổ nhiều kệ nếu một kệ không đủ số lượng, nhưng để trống `imeis` và `serialNumbers`.
- Nhân viên kho đi tới kệ theo gợi ý, lấy hàng thực tế rồi mới quét/nhập IMEI hoặc serial trên phiếu xuất; bước hoàn tất vẫn kiểm tra mã đã quét đủ số lượng và đúng kệ.
- Cách này tránh hệ thống tự chọn trước IMEI/serial không khớp với máy nhân viên thực tế lấy trên kệ.
- Sửa vị trí triển khai: loại bỏ khối auto-suggest bị chèn nhầm trong `_post_inventory_outbound`, để bước hoàn tất tiếp tục kiểm tra phân bổ, trừ tồn và chuyển trạng thái IMEI/serial; `auto_suggest_outbound_document` là nơi duy nhất tạo phân bổ kệ FIFO.
- Xóa truy vấn gợi ý IMEI/serial cũ và fallback kệ `MAIN`; nếu không đủ tồn khả dụng, phiếu chỉ ghi nhận số lượng thực sự có thể gợi ý trên các kệ hiện tại.
- Verification: backend `py_compile` pass; test tích hợp `test_12_admin_inventory_outbound_flow.py` pass và xác nhận auto-suggest chỉ lưu kệ, không lưu sẵn IMEI/serial.

## Cập nhật 2026-07-02 - Bổ sung phiếu chuyển kệ/chuyển vị trí

- Thêm nghiệp vụ `TRANSFER` cho quản lý tồn kho: nhân viên tạo phiếu chuyển kệ ở trạng thái `DRAFT`, Super Admin duyệt, hoàn tất hoặc hủy qua API `/admin/inventory/transfers`.
- Phiếu chuyển kệ lưu từng dòng gồm sản phẩm/biến thể, kệ nguồn, kệ đích, số lượng, danh sách IMEI và danh sách serial cần chuyển.
- Khi hoàn tất, backend khóa dòng tồn ở kệ nguồn, chỉ cho chuyển phần tồn khả dụng (`on_hand_quantity - reserved_quantity`), trừ số lượng khỏi kệ nguồn và cộng sang kệ đích.
- Với sản phẩm có bật quản lý IMEI hoặc serial, payload chuyển kệ bắt buộc có đủ số mã tương ứng với số lượng chuyển; mã phải đang `IN_STOCK` và đang nằm đúng kệ nguồn thì mới được cập nhật `location_id` sang kệ đích.
- Mã đang `RESERVED` không được chuyển trong luồng này để tránh lệch `reserved_quantity` theo kệ.
- Sổ kho ghi hai dòng lịch sử `ADJUSTMENT` với reason `TRANSFER_OUT` và `TRANSFER_IN` theo từng kệ, vì constraint hiện tại của `inventory_adjustment_logs.transaction_type` chưa có `TRANSFER`.
- Frontend tab tồn kho thêm danh sách `Phiếu chuyển kệ`, modal chi tiết phiếu và nút `Chuyển kệ` ngay trong từng dòng kệ của modal `Danh sách kệ`.
- Từ cập nhật 2026-07-03, phiếu chuyển đã đồng bộ `inventory_lots` theo FIFO và giữ nguyên dữ liệu tuổi tồn/giá vốn của lô nguồn.
- Verification: backend `py_compile` pass cho schema/router/service/repository chuyển kệ; frontend `npm run lint` pass.

## Cập nhật 2026-07-02 - Đồng bộ lọc tồn kho theo cấp lớn đến cấp nhỏ

- Màn quản lý tồn kho giữ riêng danh sách kệ đầy đủ để các dropdown `Dãy -> Kệ -> Ô` luôn lấy tùy chọn từ toàn bộ dữ liệu kệ, còn bảng kệ vẫn hiển thị theo bộ lọc hiện tại.
- Khi đổi danh mục trong bộ lọc tồn kho, thương hiệu được reset để tránh giữ lựa chọn không còn thuộc danh mục mới.
- Dropdown kệ hàng trong bộ lọc tồn kho dùng danh sách kệ đầy đủ, không bị thu hẹp bởi tab danh mục kệ đang lọc.
- Bảng tồn kho không còn lọc lại dữ liệu theo danh mục/thương hiệu ở frontend trước khi bấm `Lọc tồn`; API `/admin/inventory/levels` là nguồn áp dụng bộ lọc để tránh bảng trống tạm thời do trang dữ liệu hiện tại chưa chứa danh mục vừa chọn.
- Modal `Danh sách kệ` trong bảng tồn kho hiển thị thêm IMEI và serial number đang `IN_STOCK`/`RESERVED` theo từng kệ để nhân viên biết kệ đó đang giữ mã nào của sản phẩm/biến thể.
- API `/admin/inventory/levels` trả thêm `imeis` và `serialNumbers` trong từng phần tử `locations`; dữ liệu lấy theo `location_id` của `product_imeis` và `product_serial_numbers`.
- Sửa join mã định danh theo kệ cho biến thể: nếu `inventory_levels` chỉ có `variant_id` thì map IMEI/serial theo `variant_id`, không bắt buộc `product_id` của level phải khớp.
- Mã đã chuyển sang `SOLD` không còn trả vị trí kệ trong modal `Xem mã`, và các luồng xuất/bán mới sẽ đặt `location_id = NULL` khi chuyển IMEI/serial sang `SOLD`.
- Nếu kệ còn tồn nhưng chưa có mã khớp theo kệ, modal hiển thị cảnh báo số lượng chưa gắn IMEI/serial thay vì báo mơ hồ là không có mã.
- Bảng `Danh sách kệ` không render trực tiếp toàn bộ IMEI/serial trong dòng kệ; mỗi dòng chỉ có nút `Xem danh sách` mở modal riêng để tránh bảng bị dài và khó đọc.
- Bảng tồn kho chính bỏ hẳn cột/nút và modal ngoài `IMEI / Serial`; danh sách mã định danh chỉ xem theo từng kệ trong modal `Danh sách kệ` để dữ liệu cập nhật tập trung theo vị trí.
- Modal `Danh sách mã trên kệ` có nút `Sửa` trên từng IMEI/serial để tạo yêu cầu chỉnh sửa mã định danh ngay theo ngữ cảnh kệ; API read-model trả thêm `id` của từng mã để gửi đúng `identifierId`.
- Khi dữ liệu tồn kho reload sau thao tác duyệt/sửa, modal mã theo kệ đang mở tự đồng bộ lại theo dòng sản phẩm/biến thể và kệ hiện tại.
- Verification: frontend `npm run lint` pass; backend `py_compile` pass cho read-model tồn kho, mã định danh, xuất kho, hoàn tất đơn và hậu mãi.

## Cập nhật 2026-07-02 - Bổ sung chứng từ cho phiếu nhập đã hoàn tất

- `PATCH /admin/inventory/receipts/{reference_code}/attachments` chỉ tạo yêu cầu bổ sung chứng từ, lưu danh sách đề xuất vào `metadata.pendingAttachments` và đặt `attachmentApprovalStatus = PENDING`.
- Thêm endpoint super admin `PATCH /admin/inventory/receipts/{reference_code}/attachments/decision` để duyệt hoặc từ chối chứng từ chờ duyệt.
- Khi duyệt, hệ thống mới ghi danh sách vào `metadata.attachments`; khi từ chối, chứng từ chính thức giữ nguyên và `pendingAttachments` được xóa.
- Các thao tác gửi duyệt, duyệt và từ chối lần lượt ghi audit log `attachments_submitted`, `attachments_approved`, `attachments_rejected`.
- Modal chi tiết phiếu nhập hiển thị khu vực `Chứng từ đang chờ duyệt`; chỉ super admin có nút `Duyệt` và `Từ chối`.
- Luồng này không thay đổi dòng hàng, số lượng, giá vốn, trạng thái, IMEI/Serial hoặc bút toán tồn kho.

## Cập nhật 2026-07-01 - Gộp khu vào dãy trong cấu hình kệ

- Màn `Kệ hàng` chỉ còn bộ lọc/cột `Dãy`; giá trị lấy từ tiền tố mã kệ trước dấu gạch ngang, hỗ trợ cả dãy ngắn như `A-01-01` và dãy nghiệp vụ như `BH-01-01`, `CL-01-01`, `ERR-01-01`.
- Dropdown `Dãy` luôn có sẵn `MAIN`, `A`, `B`, `C`, `BH`, `CL`, `ERR`, `RT`, sau đó mới gộp thêm dãy phát sinh từ dữ liệu thật; nhãn hiển thị không còn dạng `Dãy A (A)`.
- Form kệ chỉ có trường `Tên dãy` như `Kho`, `Dãy bảo hành`, `Dãy cách ly`; đã bỏ bộ lọc/cột/trường `Khu chức năng` và bỏ dòng `Loại tự suy ra` khỏi giao diện.
- Riêng `Kho`/`MAIN` là vị trí tổng nên không dùng diện tích: form không hiện các trường dài/rộng/cao khi mã là `MAIN`, payload gửi kích thước `null`, DB local đã đặt `MAIN.length_cm/width_cm/height_cm = NULL`. Các dãy vật lý/nghiệp vụ khác vẫn có kích thước và hệ số sử dụng.
- Khi lọc một dãy chưa có kệ, bảng hiển thị rõ trạng thái `Chưa có kệ trong dãy...` và nút `Thêm kệ dãy này`; form thêm kệ tự điền mã theo dãy đang chọn như `CL-01-01`.
- Chuẩn hóa dữ liệu local và migration `014_normalize_inventory_location_areas.sql`: `QC-01 -> CL-01-01`, `BH-01 -> BH-01-01`, `ERR-01 -> ERR-01-01`, `RT-01 -> RT-01-01`, `MAIN` hiển thị là `Kho`; các dãy nghiệp vụ dùng tên `Dãy cách ly`, `Dãy bảo hành`, `Dãy hàng lỗi`, `Dãy hàng trả`.
- Backend nới validate `aisle` từ một chữ cái sang tiền tố 1-4 chữ cái và đổi lọc SQL sang `split_part(loc.code, '-', n)`, nên dãy nhiều chữ lọc được theo dãy/kệ/ô như dãy cũ.
- Nhãn `Vị trí hệ thống` đổi thành `Kho`; nhãn `Lưu hàng bán` đổi thành `Sản phẩm bán` để dễ hiểu hơn khi vận hành.
- Verification: frontend `npm run lint` pass; backend `py_compile` pass cho các module kho vừa sửa; kiểm tra nhanh phần ghi chú mới không có chuỗi tiếng Việt lỗi mã hóa.

## Cập nhật 2026-07-01 - Thiết kế lại giao diện Danh mục kệ hàng (Tab Kệ hàng)

- Cải tiến nút "Thêm kệ" sử dụng hiệu ứng gradient sinh động và icon `Plus` hiện đại.
- Bọc nhóm bộ lọc trong container xám nhạt bo góc mịn, đồng thời trang trí lại nút "Lọc" (gradient Indigo/Violet kèm icon) và nút "Xóa" (icon `RotateCcw`) giúp tổng thể gọn gàng, có chiều sâu.
- Chuyển đổi bảng danh sách kệ sang sử dụng component `<AdminTable>` đồng bộ với hệ thống trang quản trị (viền bo góc, hover row mịn).
- Tinh chỉnh các thuộc tính cột: dùng tag code font mono nổi bật cho mã kệ, bổ sung badge màu sắc riêng biệt cho từng loại vị trí (Lưu trữ, Hàng lỗi, Kiểm tra, v.v.), badge bo tròn cho tùy chọn trộn SKU.
- Nâng cấp cột Kích thước: thay thế hiển thị phần trăm đầy khô khan bằng **thanh tiến trình (progress bar)** trực quan tự động chuyển màu (Xanh lá -> Vàng -> Đỏ) tương ứng với độ đầy của kệ.
- Trang bị thêm điểm trạng thái phát sáng (chấm xanh lá cho hoạt động, xám cho đã khóa) và thu nhỏ các nút Sửa/Khóa đi kèm icon tinh tế.
- Verification: frontend `npm run lint` pass.

## Cập nhật 2026-07-01 - Tinh gọn nút xem kệ trong bảng tồn kho admin

- Chỉnh sửa nút "Xem danh sách kệ" thành "Xem kệ" trong `AdminInventoryTab.tsx`.
- Loại bỏ ép kích thước `w-full max-w-40` để nút tự co giãn theo nội dung, thêm `whitespace-nowrap` để chống rớt dòng chữ trên màn hình nhỏ.
- Giảm padding từ `px-3 py-2` xuống `px-2 py-1` và đổi `rounded-lg` thành `rounded-md` giúp nút trông nhỏ gọn, vừa vặn hơn.
- Thêm `shrink-0` cho icon và badge số lượng kệ để không bị bóp méo.
- Verification: frontend `npm run lint` pass.

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

## Cập nhật 2026-06-28 - Hoist helper React Doctor trong màn kho

- Đưa các helper thuần trong xuất kho, phiếu nhập và kiểm kê ra module scope: trạng thái dòng xuất, danh sách kệ khả dụng, badge trạng thái, chuẩn hóa IMEI/serial, trạng thái mã định danh, tạo mã kiểm kê/điều chỉnh và dựng dòng kiểm kê.
- Đưa helper kiểm tra biến thể/sản phẩm nhập kho ra module scope trong hook inventory; các helper phụ thuộc `categories` như policy IMEI/serial vẫn giữ trong hook để tránh đổi hành vi.
- Đưa helper định dạng dung lượng kệ và tên biến thể trong `InventoryDialog` ra module scope; payload nhập kho và xử lý `_clientKey` không đổi.
- Verification: frontend `npm run lint` pass; React Doctor full scan còn 353 cảnh báo, `prefer-module-scope-pure-function` chỉ còn 2 cảnh báo ngoài nhóm kho.

## Cập nhật 2026-06-28 - Ổn định key hiển thị mã định danh

- Danh sách IMEI và serial trên phân bổ xuất kho dùng chính mã định danh làm React key thay cho vị trí trong mảng.
- Biên bản sai lệch ở chi tiết phiếu nhập ưu tiên ID, sau đó dùng tổ hợp nội dung nghiệp vụ làm key ổn định.
- Chứng từ và sai lệch trong form phiếu nhập được gắn `_clientKey` khi thêm, upload hoặc hydrate phiếu sửa; payload API vẫn được dựng theo whitelist nên không gửi trường này sang backend.
- Xóa state `detailLoading` không được đọc và đưa tùy chọn trạng thái phiếu nhập ra module scope để giảm render/cấp phát thừa.
- Thay đổi chỉ tác động định danh phần tử khi render, không đổi handler xóa mã, dữ liệu phiếu hoặc quy tắc nhập/xuất kho.
- Verification: frontend `npm run lint` và `npm run build` pass; React Doctor full scan còn 390 cảnh báo và không còn rule `no-array-index-as-key`.

### Update 2026-06-28 - Xử lý cảnh báo màu chữ React Doctor trong giao diện kho

- Đổi màu chữ các nút thao tác phiếu nhập, chứng từ, sai lệch và upload file sang màu cùng ngữ nghĩa với trạng thái nền/hover để tránh chữ xám trên nền màu.
- Các thay đổi chỉ nằm ở class Tailwind, không đổi luồng nhập kho, định danh IMEI/serial hoặc dữ liệu phiếu.
- Verification: frontend `npm run lint` pass; React Doctor full scan hiện còn 476 warnings và không còn rule `no-gray-on-colored-background`.

### Update 2026-06-28 - Giảm cảnh báo accessibility React Doctor trong giao diện kho

- Bổ sung `aria-label` cho các ô tìm kiếm, bộ lọc ngày, checkbox chọn dòng, ô nhập số lượng, quét IMEI/serial, import file và textarea nhập danh sách mã trong các màn tồn kho, phiếu xuất, phiếu nhập và modal IMEI.
- Thay các ô bảng/header rỗng bằng nội dung có nghĩa hoặc ký hiệu giữ chỗ để trình đọc màn hình không gặp cell trống.
- Verification: frontend `npm run lint` pass; React Doctor full scan còn 517 warnings và không còn các rule `button-has-type`, `control-has-associated-label`, `label-has-associated-control`, `no-autofocus`, `media-has-caption`, `prefer-tag-over-role`, `no-noninteractive-element-interactions`, `anchor-is-valid`, `click-events-have-key-events`, `no-static-element-interactions`.

### Update 2026-06-28 - Sửa lỗi React Doctor mức error trong giao diện tồn kho

- `AdminInventoryTab.tsx` không còn gọi `usePermission('inventory:approve')` trong biểu thức `isSuperAdmin || ...`; hook được gọi ở top-level rồi mới kết hợp với quyền super admin.
- `ImeiReceiptModal.tsx` tách wrapper và nội dung modal theo `key` của phiếu nhập, để state nhập IMEI/serial được khởi tạo khi modal mount thay vì reset hàng loạt trong `useEffect`.
- `AdminInventoryReceiptDetails.tsx` đổi luồng in phiếu nhập từ `document.write` sang Blob HTML để tránh sink HTML động; trường tồn hiện tại trong modal điều chỉnh được đánh dấu `readOnly`.
- Verification: frontend `npm run lint` pass; `npx react-doctor@latest --no-telemetry --no-warnings --verbose` không còn issue mức error.

### Update 2026-06-27 (9) - Tách tiếp giao diện và luồng ghi sổ kho

- Tách workspace tồn kho, sổ kho và kệ hàng khỏi `AdminInventoryTab.tsx` sang `AdminInventoryWorkspace.tsx`; component cha tiếp tục giữ state và quy trình kiểm kê/điều chỉnh.
- Tách màn chi tiết bốc hàng khỏi `AdminInventoryOutboundsTab.tsx` sang `AdminInventoryOutboundDetail.tsx`.
- Tách `services/inventory/receipts.py` thành facade, `receipt_drafts.py` và `receipt_posting.py`.
- Tách `repositories/inventory/stock_mutations.py` thành các module tồn kho, lô hàng, kiểm kê, mã định danh và điều chỉnh.
- Không thay đổi chữ ký API, transaction boundary hoặc quy tắc IMEI/Serial.

### Update 2026-06-27 (8) - Tách repository/service tồn kho theo cụm nghiệp vụ

- Tách `inventory_repo.py` thành facade tương thích và các module nhỏ trong `app/infrastructure/database/repositories/inventory/`: `overview`, `identifiers`, `documents`, `locations`, `receipts`, `stock_mutations`, `outbounds`.
- Tách `inventory_service.py` thành facade tương thích và các module nhỏ trong `app/application/services/inventory/`: `common`, `overview`, `identifiers`, `documents`, `receipts`, `outbounds`.
- Các router/service hiện tại vẫn import qua `inventory_repo` và `inventory_service` như cũ, giảm rủi ro đổi caller trong lần refactor này.
- Frontend inventory tách bớt `AdminInventoryTab` thành `AdminInventoryTabUtils`, `AdminInventoryLocationsSection`, `AdminInventoryTabModals`; tách chi tiết phiếu nhập thành `AdminInventoryReceiptDetails` và `ImeiReceiptModal`.
- Verification: `py_compile` pass cho các module inventory backend và `admin_inventory.py`; frontend `npm run lint` pass.

### Update 2026-06-27 (6) - Sửa lỗi tải chi tiết phiếu xuất kho do lệch key

- Bổ sung các trường `document_no`, `created_at`, và `created_by` (snake_case) vào kết quả trả về của API danh sách phiếu xuất kho (`list_inventory_outbound_documents` ở repository) bên cạnh các trường camelCase sẵn có.
- Khắc phục lỗi `document_no` bị rỗng (undefined) ở frontend làm cho request tải chi tiết phiếu xuất kho trỏ đến `/admin/inventory/outbounds/undefined` và trả về 404.
- Khắc phục việc cột Ngày tạo bị trống do không tìm thấy trường `created_at`.

### Update 2026-06-27 (5) - Tinh gọn thao tác đóng hàng và chọn kệ xuất

- Chi tiết phiếu xuất kho nay trả thêm `availableLocations` cho từng dòng sản phẩm, chỉ gồm các kệ đang còn tồn khả dụng của đúng sản phẩm/biến thể đó.
- Màn đóng hàng không còn hiển thị toàn bộ danh sách kệ trong dropdown; nhân viên chỉ chọn trong các kệ có hàng tương ứng, giảm nhầm lẫn cho mô hình một chi nhánh.
- Nút thao tác được tinh gọn: `Lưu đóng hàng` đổi thành `Cập nhật`, `Hoàn tất xuất kho` đổi thành `Xác nhận xuất kho`.
- Khi bấm `Xác nhận xuất kho`, frontend tự lưu thông tin kệ/IMEI/Serial trước rồi mới gọi xác nhận xuất kho, nên nhân viên không bắt buộc phải bấm `Cập nhật` như một bước riêng nếu đã nhập đủ dữ liệu.
- Các nhãn hiển thị chuyển từ “bốc hàng” sang “đóng hàng/kệ xuất” để phù hợp ngữ cảnh cửa hàng bán lẻ.

### Update 2026-06-27 (4) - IMEI phụ thuộc serial

- Helper đọc policy tồn kho coi serial là định danh gốc: nếu policy hiệu lực có IMEI thì hệ thống cũng xem sản phẩm là có quản lý serial, kể cả dữ liệu cũ đang lưu `trackImei = true` nhưng `trackSerialNumber = false`.
- Quy tắc này bảo đảm luồng nhập/xuất kho luôn yêu cầu serial cho sản phẩm có IMEI, phù hợp mô hình serial + IMEI1 + IMEI2 tùy chọn.
- Verification: backend `py_compile` pass cho `inventory_service.py`.

### Update 2026-06-27 (3) - Ghép cặp IMEI và serial khi xuất kho

- **Database**: Thêm migration `035_product_identifier_pairs.sql` tạo bảng `product_identifier_pairs` để lưu cặp IMEI/serial thuộc cùng một máy vật lý theo từng sản phẩm/biến thể.
- **Nhập kho**: Khi nhập sản phẩm quản lý đồng thời IMEI và serial, hệ thống ghép cặp theo thứ tự hai danh sách đã nhập; IMEI và serial cùng chỉ số được xem là cùng một máy.
- **Xuất kho**: Thêm API `GET /admin/inventory/outbound-identifier-pair` để màn phiếu xuất kho quét một IMEI hoặc serial và tự lấy mã còn lại nếu cặp mã đang `IN_STOCK` tại đúng kệ đã chọn.
- **Frontend**: Màn phiếu xuất kho tự thêm cả IMEI và serial vào cùng allocation khi sản phẩm quản lý cả hai loại mã, giúp nhân viên kho không phải quét lặp lại hai mã của cùng một máy.
- **Update 036**: Chuyển mô hình sang serial là định danh chính của máy, `imei1` là IMEI chính bắt buộc khi sản phẩm bật IMEI, `imei2` là IMEI phụ tùy chọn. Khi xuất kho có thể quét serial, IMEI1 hoặc IMEI2; allocation vẫn lưu serial và IMEI1 để khớp số lượng máy hiện tại.
- **Đồng bộ trạng thái**: Khi hoàn tất xuất kho, nếu máy có `imei2` trong bảng ghép cặp thì hệ thống cũng chuyển IMEI2 sang `SOLD` cùng IMEI1/serial để tránh tồn kho định danh bị lệch.

### Update 2026-06-27 (2) - Khắc phục lỗi chặn luồng và tối ưu hóa bộ lọc

- **Database Constraint & Migrations**: Thêm file migration `034_allow_picking_picked_outbound_status.sql` và sửa baseline `init_database.sql` để cho phép trạng thái `PICKING` và `PICKED` trong check constraint `inventory_documents_status_check`.
- **Auto-Suggest Outbound Document**:
  - Tách nhánh kiểm tra `tracks_imei` và `tracks_serial` thành độc lập trong `auto_suggest_outbound_document` để hỗ trợ bốc hàng song song cả hai định danh cho sản phẩm cấu hình song song.
  - Sửa lỗi mapping allocations của hàm `_determine_outbound_status` (đọc từ trường phẳng `allocations` trả về từ SQL thay vì truy cập `metadata.allocations` bị rỗng).
  - Cập nhật tự động bốc hàng lưu kèm chi tiết `allocations_data` vào metadata dòng phiếu, và tự động gọi `_determine_outbound_status` để nâng trạng thái phiếu xuất lên `PICKED` ngay sau gợi ý bốc.
- **Đồng bộ trạng thái mã định danh khi xuất kho**: Đổi logic cập nhật trạng thái IMEI/Serial sang `SOLD` khi hoàn tất xuất kho (`_post_inventory_outbound`) từ `elif tracks_serial_number` thành `if tracks_serial_number` độc lập, bảo đảm cập nhật đầy đủ cả hai loại định danh cho sản phẩm áp dụng song song cả hai chính sách.
- **Frontend Cleanups & Filtering**:
  - Dọn dẹp logic bốc hàng cũ `issue_allocations` và validate dư thừa trong hook `useAdminOrdersLogic.ts` khi lưu đơn hàng.
  - Thêm các tùy chọn bộ lọc `'PICKING'`, `'PICKED'`, và `'CANCELLED'` vào dropdown select ở tab phiếu xuất kho (`AdminInventoryOutboundsTab.tsx`).
- **Verification**: Chạy thành công script test luồng xuất kho `test_outbound_flow.py`, kiểm thử chuyển trạng thái và các ràng buộc đạt kết quả 100%.

### Update 2026-06-27 - Nâng cấp quy trình bốc hàng đa kệ và đồng bộ đơn hàng

- **Commerce Logic & Sync**: Khi phiếu xuất kho (`inventory_documents.document_type = OUTBOUND`) chuyển sang trạng thái `COMPLETED`, hệ thống tự động giải phóng và đóng các giữ hàng (`inventory_reservations`) liên quan của đơn hàng sang `CONSUMED` (trong `CompleteOrderUseCase.execute`), khắc phục triệt để lỗi treo giữ hàng.
- **Vòng đời trạng thái Phiếu xuất kho (Outbound Lifecycle)**:
  - Bổ sung các trạng thái trung gian `PICKING` (đang bốc hàng) và `PICKED` (đã bốc xong - chờ duyệt), tự động tính toán từ tiến trình bốc kệ thực tế trong `_determine_outbound_status`.
  - Hỗ trợ tự động hủy phiếu xuất liên kết sang `CANCELLED` khi đơn hàng bị hủy.
  - Siết chặt phê duyệt: Chỉ cho phép hoàn tất xuất kho (`COMPLETED`) khi phiếu xuất đã ở trạng thái `PICKED` và người duyệt có vai trò `SUPER_ADMIN`.
- **Frontend UX & Controls**:
  - Ẩn hoàn toàn khối "Xác nhận kệ xuất thực tế" trên màn hình chi tiết đơn hàng (AdminOrdersTab) khi chuyển trạng thái sang `SHIPPED`. Toàn bộ nghiệp vụ chọn vị trí bốc hàng được quy hoạch tập trung tại màn Phiếu xuất kho.
  - Tab Outbound tự động chuyển đổi giao diện thành read-only (khóa mọi nút bốc hàng, xóa kệ, quét IMEI/Serial) khi phiếu ở trạng thái kết thúc `COMPLETED` hoặc `CANCELLED`.
  - Hiển thị badge trạng thái trực quan: `DRAFT` (slate), `PICKING` (amber), `PICKED` (blue), `COMPLETED` (green), `CANCELLED` (red).
- **Bốc hàng đa kệ (Multi-shelf Allocations)**: Cập nhật API và service `inventory_service.py` để hỗ trợ xuất một dòng sản phẩm từ nhiều kệ khác nhau. Danh sách phân bổ chi tiết được lưu trữ dạng mảng `allocations` (gồm `locationId`, `quantity`, `imeis`, `serialNumbers`) trong trường `metadata JSONB` của `inventory_document_lines`.
- **Quét định danh song song**: Tách biệt UI nhập mã IMEI và Serial trên màn hình phiếu xuất kho, cho phép hiển thị song song cả hai ô quét nếu sản phẩm được cấu hình áp dụng đồng thời cả hai chính sách quản lý.
- **Chuẩn hóa API Router**: Khắc phục triệt để các lỗi cú pháp dở dang và loại bỏ các route trùng lặp của inventory receipts tại `admin_inventory.py`.

## Update 2026-06-24 - Bảo vệ tồn kho khi chỉnh sửa biến thể catalog

- `product_variant_service.upsert_product_variants` nay giữ nguyên `stock_quantity` của biến thể hiện có khi admin lưu form sản phẩm.
- Biến thể mới được tạo từ catalog bắt đầu với tồn kho `0`; mọi tăng/giảm tồn phải đi qua phiếu nhập, xuất kho, điều chỉnh kho hoặc luồng đơn hàng.
- Biến thể đã có ràng buộc kho/đơn hàng/IMEI/serial không được đổi các trường định danh như SKU, màu sắc, dung lượng, RAM, cấu hình, thuộc tính và thông số định danh.
- Mục tiêu là tránh làm sai lịch sử chứng từ và tránh lệch giữa tồn thực tế, lot, reservation, IMEI/serial với dữ liệu biến thể hiển thị.

## Update 2026-06-24 - Bổ sung phiếu nhập cho tồn sản phẩm mới

- Tạo script `backend/scripts/create_receipt_for_virtual_new_products.py` để hợp thức hóa nhóm sản phẩm mới tạo ngày 2026-06-23 đang có tồn trong `inventory_levels` nhưng chưa có phiếu nhập hoàn tất.
- Script tạo phiếu nhập `NK20260624-BO-SUNG-TON-MOI` ở trạng thái `COMPLETED`, gồm 72 dòng và tổng số lượng 5.160 sản phẩm.
- Đây là phiếu đối soát tồn đã có sẵn: metadata có `reconcilesExistingStock = true` và `stockMutationSkipped = true`; script không gọi luồng post chuẩn và không cộng tồn lần nữa.
- Script bổ sung `inventory_document_lines`, `inventory_lots`, `inventory_lot_movements`, `inventory_adjustment_logs` và audit log để lịch sử nhập kho, lô nội bộ và báo cáo truy vết khớp lại với tồn hiện tại.
- Verification local: trước/sau khi chạy script, tổng `inventory_levels` giữ nguyên 9.630; tổng lô active tăng khớp lên 9.630; không còn dòng tồn mới từ 2026-06-23 có số lượng nhưng thiếu chứng từ nhập hoàn tất.

## Update 2026-06-23 - Soft Lock hậu mãi và vòng đời IMEI lỗi

- Module hậu mãi bổ sung `after_sales_allocations` để giữ tồn khả dụng trong 48 giờ sau khi QC duyệt đổi/thay máy, không gán cứng IMEI cho đến lúc admin quét máy thay thế.
- Công thức tồn khả dụng của luồng hậu mãi trừ thêm allocation `LOCKED`, bên cạnh tồn đang giữ cho đơn hàng và IMEI/serial đã reserved.
- Khi hoàn tất đổi/thay máy, hệ thống chuyển IMEI mới sang `SOLD`, trừ tồn vật lý ở vị trí của IMEI và ghi `inventory_adjustment_logs` với lý do `AFTER_SALES_REPLACEMENT`.
- IMEI cũ được chuyển sang `DEFECTIVE_RETURNED` và có bảng sự kiện disposition để theo dõi tiếp các trạng thái `INSPECTION_PENDING`, `RTV_PENDING`, `LIQUIDATION_PENDING`, `RTV_COMPLETED`, `LIQUIDATED`, `SCRAP`, `OUT_OF_SYSTEM`.
- Không cho xuất IMEI khỏi hệ thống nếu chưa có kết quả RTV, thanh lý hoặc phế phẩm; mỗi lần chuyển trạng thái lưu lý do, chứng từ, đối tác và giá trị thu hồi.

## Update 2026-06-20 - Backfill IMEI/Serial khi đổi chính sách danh mục

- Bổ sung chứng từ kỹ thuật `inventory_policy_migrations` để xử lý hàng tồn cũ khi danh mục chuyển từ không quản lý sang quản lý IMEI hoặc serial number.
- Danh sách mã quét được giữ ở staging; chỉ khi đủ số lượng và đối soát tồn không thay đổi mới chuyển vào `product_imeis` hoặc `product_serial_numbers` với trạng thái `IN_STOCK`.
- Tác vụ bị hủy giữ mã ở trạng thái `CANCELLED` để audit, không đưa vào read-model tồn kho.
- Một mã chỉ được tồn tại trong một staging đang hoạt động; database có unique index để chặn xung đột đồng thời.
- IMEI và serial được kích hoạt độc lập, tránh hoàn tất một tác vụ nhưng vô tình bật policy của loại còn lại.
- Giao diện danh mục hỗ trợ quét liên tục hoặc dán nhiều mã theo từng sản phẩm/biến thể, hiển thị tiến độ và lỗi backend ngay trong khối tác vụ.
- Phạm vi giữ ở mức WMS-light cho luận văn: không thêm queue, tracking mode theo lô hoặc quy trình đối soát doanh nghiệp nhiều tầng.

## Update 2026-06-19 - Bổ sung dãy C và giải phóng các ô quá tải

- Thêm migration `013_inventory_location_aisle_c_and_rebalance_full_bins.sql` để tạo dãy C theo mô hình 10 kệ x 4 ô, mã từ `C-01-01` đến `C-10-04`.
- Các ô dãy C dùng cùng kích thước và hệ số sử dụng với dãy A/B: `100 x 60 x 40 cm`, `usable_ratio = 0.75`, cho phép nhiều SKU.
- Migration xác định các ô A/B đang vượt 100% dung lượng, chọn nguyên dòng SKU theo thể tích tăng dần cho đến khi ô nguồn hết quá tải và chuyển mỗi dòng sang một ô C trống.
- Vị trí của tồn kho, IMEI, serial và lô nội bộ được cập nhật đồng bộ; metadata lô ghi lại kệ nguồn, kệ đích và thời điểm chuyển.
- Migration dừng với lỗi rõ ràng nếu số ô C không đủ hoặc có một dòng SKU lớn hơn dung lượng một ô, tránh cập nhật dở dang.
- Verification local: migration chạy thành công; tạo đủ 40 ô C, dùng 20 ô để chuyển 20 dòng SKU; số ô vượt dung lượng giảm từ 20 xuống 0; tổng tồn và tổng lô đều giữ nguyên `4.470`; số IMEI, serial và lô lệch vị trí so với tồn kho đều bằng 0.

## Update 2026-06-18 - Xuất một sản phẩm từ nhiều kệ

- Màn chi tiết đơn hàng cho phép thêm nhiều dòng kệ thực tế cho cùng một sản phẩm bằng nút `Thêm kệ`, đồng thời hỗ trợ xóa từng dòng kệ.
- Giao diện hiển thị `Đã phân bổ / cần xuất` theo từng dòng sản phẩm và đổi trạng thái màu khi tổng số lượng đã khớp.
- Frontend chặn lưu nếu dòng kệ thiếu vị trí, số lượng không hợp lệ, chọn trùng kệ hoặc tổng phân bổ khác số lượng đơn hàng.
- Backend kiểm tra lại tổng số lượng và kệ trùng trước khi trừ tồn; từng phần phân bổ tiếp tục trừ đúng tồn kệ và lô FIFO trong kệ đó.
- Nếu nhân viên không thêm bất kỳ kệ nào cho một dòng sản phẩm, hệ thống giữ hành vi fallback FIFO tự động.
- Verification: frontend `npm run lint` pass; backend `py_compile` pass cho commerce use case/repository.

## Update 2026-06-18 - Lô tồn kho nội bộ tự động

- Thêm migration `012_inventory_internal_lots.sql` tạo `inventory_lots` và `inventory_lot_movements`.
- Khi hoàn tất phiếu nhập, hệ thống tự sinh lô nội bộ theo từng dòng sản phẩm/biến thể và kệ; nhân viên không cần nhập hay chọn mã lô.
- Khi xuất đơn hàng, hệ thống tiêu thụ lô cũ trước theo `received_at` bên trong đúng kệ thực tế đã xác nhận; nếu chưa xác nhận kệ thì vẫn chọn kệ theo FIFO rồi chọn lô FIFO trong kệ.
- Mỗi lần nhập, bán hoặc đảo phiếu đều có movement để truy vết nguồn phiếu, đơn hàng và số lượng của lô.
- Đảo phiếu nhập chỉ được phép khi lô của chính phiếu đó còn đủ số lượng; nếu lô đã được bán một phần thì hệ thống chặn đảo toàn bộ.
- Migration backfill tồn hiện tại thành 298 lô nội bộ. Đối soát local: tổng `inventory_levels = 4470`, tổng lô còn lại `= 4470`, số nhóm sản phẩm/kệ lệch `= 0`.
- Verification: migration local thành công; backend `py_compile` pass cho inventory và commerce service/repository.

## Update 2026-06-18 - Xác nhận kệ xuất thực tế khi giao hàng

- API admin cập nhật đơn hàng nhận thêm `issue_allocations`, gồm `order_item_id`, `location_id` và `quantity` để nhân viên xác nhận kệ xuất thực tế.
- Khi chuyển đơn sang `SHIPPED`, nếu dòng đơn có xác nhận kệ thì backend trừ đúng kệ nhân viên chọn; nếu dòng đơn chưa có xác nhận thì fallback FIFO theo kệ cũ trước.
- Backend kiểm tra tổng số lượng xác nhận của từng dòng phải bằng số lượng cần xuất và kệ được chọn phải còn đủ tồn khả dụng.
- Màn chi tiết đơn hàng hiển thị khối `Xác nhận kệ xuất thực tế` khi chuẩn bị chuyển đơn sang `SHIPPED`; chọn `SHIPPED` từ dropdown nhanh ngoài bảng sẽ mở chi tiết đơn thay vì trừ kho ngay.
- Verification: backend `py_compile` pass cho `commerce/schemas.py`, `commerce/use_cases.py`, `commerce_repo.py`; frontend `npm run lint` pass.

## Update 2026-06-18 - Xuất kho theo kệ cũ trước khi giao hàng

- Khi đơn hàng chuyển sang giao hàng, backend không chỉ trừ `stock_quantity` tổng mà còn trừ tồn trong `inventory_levels` theo từng kệ.
- Nếu một sản phẩm/biến thể nằm ở nhiều kệ, hệ thống lấy từ kệ có `inventory_levels.updated_at` cũ nhất trước, sau đó mới tới kệ mới hơn.
- Mỗi phần xuất từ một kệ được ghi log `SALE/ORDER_SHIPPED` riêng kèm `location_code` và `location_name`, giúp tra lại đơn hàng đã lấy hàng từ ô nào.
- Nếu tổng tồn còn nhưng tồn khả dụng theo kệ không đủ, hệ thống trả lỗi `Không đủ tồn khả dụng ở các kệ để xuất kho.` để tránh lệch giữa tồn tổng và tồn theo vị trí.
- Giới hạn hiện tại: đây là FIFO theo mức kệ/vị trí dựa trên `updated_at`, chưa phải FIFO theo từng lô nhập riêng trong cùng một kệ.
- Verification: backend `py_compile` pass cho `commerce/use_cases.py` và `commerce_repo.py`.

## Update 2026-06-18 - Chặn nhập kho vượt dung lượng ô/kệ

- Backend kiểm tra dung lượng còn trống của `inventory_locations` khi lưu phiếu nhập và kiểm tra lại khi hoàn tất phiếu nhập.
- Dung lượng cần thêm được tính theo số lượng nhập nhân với kích thước đóng gói hiệu lực của danh mục, có chia cho `packingRatio` để bù hao hụt xếp hàng.
- Nếu nhiều dòng phiếu cùng chọn một ô, hệ thống cộng dồn dung lượng yêu cầu trong cùng phiếu trước khi so với dung lượng còn lại.
- Dropdown chọn kệ trong phiếu nhập hiển thị thêm phần trăm đầy và dung lượng còn lại theo cm³ để nhân viên thấy trước khi lưu.
- Nếu ô/kệ không có cấu hình kích thước, luồng hiện tại chưa chặn theo thể tích để tránh khóa các khu chức năng cũ; các ô A/B đã có kích thước nên được kiểm soát.
- Verification: backend `py_compile` pass cho `inventory_service.py` và `inventory_repo.py`; frontend `npm run lint` pass.

## Update 2026-06-18 - Điều chỉnh hệ số dùng được và xếp hàng

- Thêm migration `011_tune_storage_packing_ratios.sql` để tinh chỉnh hệ số theo giả định nghiệp vụ mới: ô lưu hàng thường/nhiều loại dùng `usable_ratio = 0.75`, khu/cồng kềnh mặc định `0.70`.
- Điều chỉnh `packingRatio` theo danh mục: laptop và tablet `0.80`, phụ kiện nhỏ và điện thoại/đồng hồ `0.85`, camera và tai nghe `0.75`.
- Sau điều chỉnh, ô mẫu `A-01-01` có thể tích dùng được `180000 cm³`, đã dùng khoảng `130676 cm³`, mức đầy còn khoảng `72.6%`.
- Verification: migration local thành công; backend `py_compile` pass; frontend `npm run lint` pass.

## Update 2026-06-18 - Tính đầy/trống kệ theo thể tích có hao hụt

- Thêm migration `010_storage_volume_utilization_ratios.sql` bổ sung `usable_ratio` cho `inventory_locations` để mô phỏng hao hụt không gian do nhân viên xếp hàng, khoảng hở và trộn SKU.
- API danh mục kệ hàng tính thêm `usableVolumeCm3`, `usedVolumeCm3`, `availableVolumeCm3`, `fillRatio` dựa trên kích thước ô, `usable_ratio`, tồn hiện tại và kích thước đóng gói danh mục.
- Frontend tab `Kệ hàng` hiển thị phần trăm đầy và dung lượng còn lại theo cm³; form kệ hàng có thêm trường `Hệ số sử dụng`.
- Verification: migration local thành công; backend `py_compile` pass; frontend `npm run lint` pass; service kiểm tra `A-01-01` trả fill khoảng `83.77%`.

## Update 2026-06-18 - Bổ sung kích thước riêng cho từng ô/kệ

- Thêm migration `008_inventory_location_bin_dimensions.sql` bổ sung `length_cm`, `width_cm`, `height_cm` cho `inventory_locations`.
- Các ô lưu hàng active thuộc dãy A/B được gán mặc định `100 x 60 x 40 cm`; từng ô có thể sửa kích thước riêng trong form kệ hàng.
- API danh mục kệ trả thêm `lengthCm`, `widthCm`, `heightCm` và `capacityVolumeCm3` để chuẩn bị tính sức chứa theo thể tích thay vì chỉ theo số lượng.
- Frontend tab `Kệ hàng` hiển thị kích thước/thể tích và form thêm/sửa kệ có trường `Dài`, `Rộng`, `Cao`.
- Verification: chạy migration local thành công; backend `py_compile` pass; frontend `npm run lint` pass; service lọc `A-01-01` trả `100 x 60 x 40 cm`, thể tích `240000 cm³`.

## Update 2026-06-18 - Phân bổ sản phẩm đang bán vào kệ A/B

- Thêm migration `007_assign_active_inventory_to_storage_bins.sql` để chuyển tồn kho của sản phẩm/biến thể đang bán từ vị trí hệ thống `MAIN` sang các ô lưu hàng active thuộc dãy A/B.
- Do hiện có 298 SKU/biến thể đang bán nhưng chỉ có 80 ô A/B, các ô lưu hàng A/B được bật `allow_mixed_sku = TRUE` để cho phép nhiều SKU trong cùng một ô.
- Phân bổ theo thứ tự sản phẩm/danh mục và xoay vòng qua 80 ô; sau khi chạy local, dãy A có 160 dòng tồn/2.400 cái, dãy B có 138 dòng tồn/2.070 cái, `MAIN` còn 0 tồn.
- Đồng bộ `location_id` cho serial/IMEI theo kệ mới; đối soát serial `IN_STOCK` cho thấy 0 dòng lệch kệ so với `inventory_levels`.

## Update 2026-06-18 - Thêm bộ lọc chi tiết cho danh mục kệ hàng

- API `GET /admin/inventory/locations` hỗ trợ thêm bộ lọc theo `aisle`, `shelf`, `bin` để lọc trực tiếp theo cấu trúc mã `Dãy-Kệ-Ô`, ví dụ `B-02-03`.
- Tab `Kệ hàng` trong màn `Quản lý tồn kho` có thêm bộ lọc mã/tên/khu, dãy, kệ, ô, khu vực, loại và trạng thái.
- Verification: backend `py_compile` pass; frontend `npm run lint` pass; gọi service lọc dãy B, kệ 02, ô 03 trả đúng `B-02-03`.

## Update 2026-06-18 - Bổ sung dãy B và chuẩn hóa nhãn khu đặc biệt

- Dãy B được seed theo cùng mô hình với dãy A: 10 kệ x 4 ô, mã từ `B-01-01` đến `B-10-04`.
- Thêm migration `006_inventory_location_aisle_b_and_special_zone_labels.sql` để database hiện tại tự bổ sung đủ 40 vị trí active cho dãy B.
- Chuẩn hóa nhãn các khu đặc biệt cho gọn trên bảng: `QC - Ô 01`, `Bảo hành - Ô 01`, `Hàng lỗi - Ô 01`, `Hàng trả - Ô 01`; mã `QC-01`, `BH-01`, `ERR-01`, `RT-01` được giữ nguyên vì đây là khu chức năng, không phải dãy lưu hàng.

## Update 2026-06-18 - Chuẩn hóa dãy A theo mô hình 10 kệ x 4 ô

- Dãy A được chuẩn hóa thành 10 kệ, mỗi kệ có 4 ô, theo mã `A-01-01` đến `A-10-04`.
- Baseline `init_database.sql` seed 40 vị trí active cho dãy A theo đúng quy ước `Dãy-Kệ-Ô`.
- Thêm migration `005_inventory_location_aisle_a_10_shelves_4_bins.sql` để database hiện tại tự bổ sung đủ 40 vị trí và khóa các mã cũ `A-01-05` đến `A-01-10` nếu chưa có tồn kho.

## Update 2026-06-18 - Sửa triệt để các cột chứa tiếng Việt bị lỗi dấu hỏi trong database

- Phát hiện và sửa lỗi encoding mojibake (các chữ tiếng Việt có dấu biến thành dấu hỏi `?` literal) trong 3 bảng database chính: `inventory_adjustment_logs`, `inventory_document_lines` và `inventory_documents`.
- Các giá trị đã sửa:
  - `"Nh?p kho kh?i t?o"` -> `"Nhập kho khởi tạo"` (298 dòng trong `inventory_adjustment_logs.reason`)
  - `"Kh?i t?o t?n kho th?t t? d? li?u s?n ph?m/bi?n th? hi?n c?."` -> `"Khởi tạo tồn kho thực tế từ dữ liệu sản phẩm/biến thể hiện có."` (298 dòng trong `inventory_adjustment_logs.note`)
  - `"T?n kho kh?i t?o t? d? li?u s?n ph?m"` -> `"Tồn kho khởi tạo từ dữ liệu sản phẩm"` (298 dòng trong `inventory_adjustment_logs.supplier_name` và 1 dòng trong `inventory_documents.supplier_name`)
  - `"D?ng nh?p kh?i t?o t? t?n catalog."` -> `"Dòng nhập khởi tạo từ tồn catalog."` (298 dòng trong `inventory_document_lines.note`)
  - `"Kh?i t?o t?n kho th?t t? to?n b? s?n ph?m/bi?n th? active, m?i d?ng 15 c?i."` -> `"Khởi tạo tồn kho thực tế từ toàn bộ sản phẩm/biến thể active, mỗi dòng 15 cái."` (1 dòng trong `inventory_documents.note`)
- Verification: Chạy truy vấn đối soát dữ liệu thực tế cho thấy các trường này hiển thị tiếng Việt có dấu chuẩn 100%. Giao diện admin của Nhập kho và Quản lý tồn kho không còn bất kỳ dấu hỏi lỗi nào.

## Update 2026-06-18 - Bổ sung 10 vị trí kệ cho dãy A

- Baseline `init_database.sql` hiện seed đủ 10 vị trí lưu hàng bán được cho dãy A, từ `A-01-01` đến `A-01-10`.
- Thêm migration `004_inventory_location_aisle_a_shelves.sql` để database đã tồn tại được bổ sung các vị trí `A-01-03` đến `A-01-10` mà không cần tạo lại database.
- Các vị trí mới dùng `purpose = STORAGE`, `zone = Dãy A`, `allow_mixed_sku = FALSE` và `sort_order` theo quy ước mã kệ hiện có.

## Update 2026-06-18 - Kiểm kê theo danh sách chọn hoặc toàn bộ

- Màn `Quản lý tồn kho` bổ sung checkbox chọn dòng tồn kho để lập phiếu kiểm kê theo danh sách đã chọn.
- Nút kiểm kê được tách thành `Kiểm kê đã chọn` và `Kiểm kê toàn bộ`; kiểm kê toàn bộ sẽ tải tất cả trang tồn kho theo bộ lọc hiện tại thay vì chỉ dùng trang đang hiển thị.
- Popup tạo phiếu kiểm kê giữ nguyên danh sách dòng đã chọn/toàn bộ để admin nhập `Thực đếm` trước khi tạo phiếu.
- Tăng giới hạn payload kiểm kê từ 300 lên 1000 dòng để tránh kẹt khi kiểm kê toàn bộ có thêm sản phẩm/biến thể trong tương lai.
- Verification: frontend `npm run lint` thành công; backend `py_compile` cho schema inventory, service inventory và repository inventory thành công.

## Update 2026-06-18 - Sửa lỗi mã hóa vị trí kho trong phiếu nhập khởi tạo

- Sửa dữ liệu local bị lưu sai `Kho ch?nh` thành `Kho chính` trong `inventory_adjustment_logs.location_name` và `inventory_document_lines.metadata.storageLocationName` của phiếu nhập khởi tạo.
- Nguyên nhân thao tác dữ liệu trước đó truyền literal tiếng Việt qua PowerShell làm mất ký tự `í`; khi cập nhật dữ liệu tiếng Việt từ script cần truyền chuỗi Unicode qua parameter hoặc dùng escape Unicode.
- Verification: `inventory_service.list_inventory_receipts` trả `storageLocationName = "Kho chính"` và `locationName = "Kho chính"` cho phiếu `NK-KHOI-TAO-20260615-0001`.

## Update 2026-06-18 - Chuẩn hóa phiếu nhập kho khởi tạo theo toàn bộ biến thể active

- Tái tạo dữ liệu local của phiếu `NK-KHOI-TAO-20260615-0001` để bao phủ toàn bộ sản phẩm/biến thể đang active: 290 biến thể và 8 sản phẩm active không có biến thể.
- Mỗi dòng nhập khởi tạo được đặt số lượng 15 cái, tránh tình trạng một lần nhập khởi tạo ghi 25-45 cái hoặc nhiều hơn cho một biến thể.
- Đồng bộ lại `inventory_document_lines`, `inventory_adjustment_logs`, `inventory_levels`, tồn kho biến thể/sản phẩm cha và danh sách serial number theo cùng mức 15 cái mỗi dòng.
- Sau điều chỉnh, phiếu có 298 dòng, tổng số lượng 4.470 và tổng giá trị 89.685.600.000đ.
- Verification: gọi trực tiếp `inventory_service.list_inventory_receipts` trả `lineCount = 298`, `totalQuantity = 4470`; truy vấn đối soát cho thấy thiếu 0 dòng active, sai số lượng 0 dòng và mọi dòng đều có 15 serial.

## Update 2026-06-18 - Lọc kệ nhập kho theo lý do nhập

- Form lập phiếu nhập kho lọc danh sách kệ theo `receiptReasonCode` và `purpose` của kệ hàng.
- Nhập mua, chuyển kho, sản xuất, khởi tạo và điều chỉnh tăng ưu tiên kệ `STORAGE`; khách trả hàng ưu tiên `RETURN`/`QC`; nhập bảo hành ưu tiên `WARRANTY`; nhà cung cấp trả/bổ sung hàng ưu tiên `STORAGE`/`QC`; nhập khác cho chọn tất cả kệ đang hoạt động.
- Khi đổi lý do nhập, nếu dòng phiếu đang chọn kệ không còn phù hợp với nhóm lý do mới thì frontend tự bỏ chọn kệ đó để người dùng chọn lại đúng nhóm.
- Verification: frontend `npm run lint` và backend `py_compile` thành công.

## Update 2026-06-18 - Sửa lỗi ledger và modal IMEI/serial 500

- Sửa router `GET /admin/inventory/ledger` trả kiểu `dict` để khớp response phân trang `{items, page, pageSize, total, totalPages}`, tránh lỗi FastAPI response validation khi tab sổ kho tải dữ liệu.
- Bổ sung migration `003_inventory_identifier_locations.sql` thêm `location_id` cho `product_imeis` và `product_serial_numbers`, backfill vị trí từ dòng phiếu nhập hoặc `inventory_levels` hiện có.
- Modal IMEI/serial trong tồn kho đọc được vị trí kệ của mã định danh mà không còn lỗi thiếu cột `product_imeis.location_id`.
- Verification: chạy migration local, gọi trực tiếp service ledger trả 50/290 dòng và service identifiers trả dữ liệu serial thành công; backend `py_compile` thành công.

## Update 2026-06-18 - Sửa lỗi kệ hàng 500 và ổn định hook admin

- Bổ sung migration `001_inventory_location_master_columns.sql` để database đã khởi tạo trước đó có đủ metadata kệ hàng: `zone`, `description`, `purpose`, `sort_order`, `allow_mixed_sku` và seed các kệ mẫu.
- Bổ sung migration `002_inventory_location_main_sort_order.sql` để kệ mặc định `MAIN` luôn đứng đầu danh sách.
- Sửa truy vấn `list_inventory_locations` không còn truyền `NULL` vào tham số tìm kiếm, tránh lỗi asyncpg `could not determine data type of parameter` khi gọi `GET /admin/inventory/locations?includeInactive=true`.
- Đưa hook phân quyền trong `useAdminLogic` lên trước các logic/memo phụ thuộc để tránh cảnh báo React đổi thứ tự hook trong màn admin sau khi hot reload.
- Verification: chạy migration local, gọi trực tiếp service `list_inventory_locations` trả dữ liệu thành công, backend `py_compile` và frontend `npm run lint` đều thành công.

## Update 2026-06-18 - Phân trang tồn kho và phiếu nhập

- API `GET /admin/inventory/levels` và `GET /admin/inventory/receipts` hỗ trợ `page` và `pageSize`, mặc định 50 dòng/trang và tối đa 100 dòng/trang.
- Kết quả hai API trả về `items`, `page`, `pageSize`, `total` và `totalPages` để frontend hiển thị đúng tổng số bản ghi.
- Bộ lọc trạng thái phiếu nhập được chuyển vào request backend để phân trang không tạo ra các trang trống hoặc thiếu dòng phù hợp.
- Bộ lọc danh mục và thương hiệu tồn kho cũng được áp dụng trước khi tính tổng và chia trang, tránh bỏ sót dữ liệu phù hợp nằm ở trang khác.
- Màn `Quản lý tồn kho` và `Quản lý nhập kho` có nút `Trang trước` / `Trang sau`, chỉ báo trang hiện tại và khoảng bản ghi đang hiển thị.
- Khi tìm kiếm hoặc áp dụng/xóa bộ lọc, danh sách quay về trang đầu tiên.
- Verification: backend `py_compile` và frontend `npm run lint` đều thành công.

## Update 2026-06-18 - Đưa bộ lọc xuống dưới tổng quan

- Màn `Quản lý tồn kho` hiển thị dashboard tổng quan trước, sau đó mới đến bộ lọc danh mục, thương hiệu, trạng thái tồn, kệ hàng và tìm kiếm.
- Màn `Quản lý nhập kho` hiển thị khối tổng quan nhập kho/nhà cung cấp trước, sau đó mới đến tìm kiếm, khoảng ngày và trạng thái phiếu.
- Chỉ thay đổi vị trí hiển thị; hành vi lọc và phân trang giữ nguyên.
- Verification: frontend `npm run lint` thành công và nội dung tiếng Việt mới không có dấu hiệu lỗi mã hóa.

## Update 2026-06-18 - Hiển thị biến thể trong dashboard tồn kho

- Danh sách `Top tồn nhiều` và `Top cần nhập thêm` hiển thị màu sắc và cấu hình biến thể dưới tên sản phẩm để phân biệt các dòng cùng sản phẩm; không hiển thị SKU.
- Sản phẩm không có biến thể không hiển thị dòng thông tin phụ.
- Dashboard tồn kho tiếp tục tổng hợp trên toàn bộ read-model thay vì dùng response đã phân trang của bảng tồn kho.

## Update 2026-06-18 - Tách tab và phân trang sổ kho

- `Sổ kho / lịch sử biến động tồn` được tách thành tab con `Sổ kho` cạnh `Tồn kho` và `Kệ hàng`, không còn kéo dài nội dung của danh sách tồn kho.
- API sổ kho hỗ trợ `page` và `pageSize`, mặc định 50 biến động/trang.
- Tab sổ kho có điều khiển trang trước/sau, tổng số biến động và khoảng dữ liệu đang hiển thị.

## Update 2026-06-18 - Chuẩn hóa kệ hàng trong kho

- Nâng cấp `inventory_locations` thành danh mục kệ hàng quản trị được, bổ sung `zone` và `description`, seed các kệ mẫu `KE-A1`, `KE-B1`, `TU-01` bên cạnh `MAIN / Kho chính`.
- Thêm API quản lý kệ hàng: `GET/POST/PUT /admin/inventory/locations` và `PATCH /admin/inventory/locations/{location_id}/status`.
- Backend chuẩn hóa mã kệ, chặn trùng mã, chặn khóa kệ mặc định và chặn khóa kệ còn tồn kho.
- Dòng phiếu nhập nhận thêm `warehouseLocationId`; backend ưu tiên kệ được chọn từ danh mục, vẫn fallback theo `storageLocationCode` cho dữ liệu cũ.
- Khi hoàn tất phiếu nhập, hệ thống cộng `inventory_levels` theo đúng kệ của từng dòng và gán `location_id` cho các IMEI/serial number thực nhận.
- Bổ sung migration `072_inventory_locations_master_data.sql` để thêm metadata kệ, backfill vị trí IMEI/serial từ dòng phiếu nhập và tạo index tra cứu theo kệ/trạng thái.
- Frontend màn `Quản lý tồn kho` có khối danh mục kệ hàng để thêm/sửa/khóa/mở kệ; bộ lọc vị trí đổi sang chọn kệ từ danh mục.
- Màn `Quản lý tồn kho` tách tab con `Tồn kho` và `Kệ hàng`, giữ kệ hàng trong cùng module tồn kho nhưng không trộn lẫn với bảng SKU/sổ kho.
- Form phiếu nhập đổi vị trí dòng phiếu từ nhập text tự do sang combobox chọn kệ hàng, giúp dữ liệu kệ thống nhất và phục vụ truy vết IMEI/serial khi xuất kho sau này.
- Danh sách IMEI/serial trong tồn kho hiển thị thêm kệ hiện tại của từng mã định danh.
- Bổ sung API `GET /admin/inventory/issue-suggestions` để gợi ý xuất kho theo kệ: với hàng có IMEI/serial, FIFO lấy từ mã định danh còn `IN_STOCK`; với hàng không định danh, hệ thống gợi ý từ tồn khả dụng theo kệ.
- Frontend có nút `Gợi ý xuất` trên dòng tồn kho khả dụng, hiển thị kệ nên lấy, số lượng gợi ý và danh sách IMEI/serial đề xuất nếu có.
- Modal `Bổ sung IMEI/serial number` có thêm chế độ quét mã liên tục: máy quét nhập mã rồi Enter sẽ tự thêm vào danh sách, chặn trùng trong frontend và không cho vượt số lượng dự kiến; backend vẫn validate lần cuối khi xác nhận.
- Danh mục kệ hàng bổ sung phân loại vị trí `STORAGE`/`QC`/`WARRANTY`/`DAMAGED`/`RETURN`/`VIRTUAL`, `sortOrder` để sắp xếp đường lấy hàng và `allowMixedSku` để ghi nhận kệ có cho phép nhiều SKU hay không.
- Quy ước mã kệ chuyển sang dạng `A-01-01`, `B-01-01`, `QC-01`, `BH-01`, `ERR-01`, `RT-01`; migration seed sẵn các vị trí mẫu theo nhóm lưu hàng, kiểm tra chất lượng, bảo hành, hàng lỗi và hàng trả.

## Update 2026-06-17 - Bổ sung WMS nhẹ cho quy trình nhập kho đồ án

- Màn `Quản lý tồn kho` có thêm dashboard: tổng SKU theo dõi, số SKU sắp hết, giá trị tồn kho, SKU đang giữ hàng, top tồn nhiều và top cần nhập thêm.
- API `GET /admin/inventory/dashboard` tổng hợp dashboard từ read-model tồn kho hiện tại.
- API `GET /admin/inventory/ledger` trả sổ kho/lịch sử biến động từ `inventory_adjustment_logs`, hỗ trợ lọc theo tìm kiếm, sản phẩm, khoảng ngày và loại giao dịch `RECEIPT`/`SALE`/`ADJUSTMENT`/`RETURN`/`REVERSAL`.
- API `GET /admin/inventory/levels` nhận thêm `stockFilter` và `location` để lọc hàng sắp hết, còn tồn, đang giữ và theo vị trí/kệ.
- Snapshot tồn kho trả thêm `locations` từ `inventory_levels`, giúp UI lọc và hiển thị vị trí/kệ có tồn.
- Màn `Quản lý nhập kho` có thêm bộ lọc khoảng thời gian `Từ ngày` / `Đến ngày`; API `GET /admin/inventory/receipts` nhận `dateFrom` và `dateTo`, lọc theo ngày tạo phiếu cho cả chứng từ nhập mới và receipt legacy từ log.
- Phiếu nhập kho có thêm metadata nghiệp vụ: chứng từ đính kèm, biên bản sai lệch, trạng thái kiểm tra chất lượng, ghi chú QC, trạng thái cách ly và vị trí cách ly.
- Dòng phiếu nhập có thêm vị trí lưu kho đơn giản bằng `storageLocationCode` và `storageLocationName`, phù hợp mức `Kho chính`, `Kệ A1`, `Kệ B2` thay vì triển khai slotting WMS đầy đủ.
- Vị trí dòng phiếu nay được dùng làm `inventory_document_lines.location_id`; khi hoàn tất hoặc đảo phiếu, `inventory_levels` được cộng/trừ theo vị trí dòng thay vì chỉ dùng kho header.
- Upload chứng từ nhập kho dùng folder `inventory` trong API upload hiện có, cho phép ảnh và tài liệu PDF/DOC/DOCX/XLS/XLSX.
- Bổ sung API `PATCH /admin/inventory/receipts/{reference_code}/quality` để cập nhật QC/cách ly riêng, không cần sửa lại toàn bộ phiếu nhập.
- Migration `071_inventory_receipt_wms_lightweight_metadata.sql` bổ sung `inventory_documents.metadata` và index tra cứu QC/vị trí.
- Backend chặn hoàn tất phiếu nhập nếu QC chưa `PASSED` hoặc phiếu còn đánh dấu cách ly, tránh cập nhật hàng lỗi vào tồn khả dụng.
- API `GET /admin/inventory/receipts/report` trả báo cáo nhập kho theo ngày, theo tháng và thống kê nhà cung cấp gồm số lần nhập, số phiếu sai lệch, số lần QC không đạt và tỷ lệ lỗi.
- Frontend màn `Quản lý nhập kho` hiển thị QC/cách ly, chứng từ, biên bản sai lệch, vị trí kệ và khối thống kê nhà cung cấp ngay trong tab nhập kho.

## Update 2026-06-17 - Liên kết giữ hàng đơn hàng với tồn kho khả dụng

- Luồng đơn hàng mới sử dụng `inventory_reservations` để giữ hàng khi checkout, giúp màn tồn kho phân biệt tồn vật lý, tồn đang giữ và tồn có thể bán.
- Tồn vật lý chỉ bị trừ khi đơn chuyển sang `SHIPPED`; các trạng thái hủy/thanh toán lỗi trước khi giao chỉ giải phóng giữ hàng.
- Backend giữ tương thích với đơn cũ từng trừ tồn ngay lúc tạo đơn qua log `ORDER_CREATED`, tránh trừ tồn lần hai khi giao và vẫn hoàn tồn đúng khi hủy.

## Update 2026-06-17 - Thiết kế lại quyền nhập kho theo mô hình Super Admin duyệt

- Bổ sung migration `070_inventory_pending_inbound_identifiers.sql` để thêm trạng thái `PENDING_INBOUND` cho IMEI/serial number.
- Khi staff xác nhận IMEI/serial ở bước `PROCESSING_IMEI`, backend tạo bản ghi giữ chỗ trong `product_imeis` và `product_serial_numbers` với `source_reference` là mã phiếu nhập và trạng thái `PENDING_INBOUND`.
- Khi phiếu nhập được hoàn tất, các mã `PENDING_INBOUND` đúng phiếu mới được chuyển sang `IN_STOCK`; nếu mã không được giữ chỗ đúng phiếu thì backend chặn hoàn tất.
- Khi phiếu đã gửi duyệt bị trả về nháp để sửa hoặc bị hủy, các mã `PENDING_INBOUND` của phiếu được giải phóng để tránh rác dữ liệu và tránh giữ mã sai sau khi đổi dòng phiếu.
- Frontend tồn kho hiển thị trạng thái mã `PENDING_INBOUND` là `Chờ nhập kho`.
- Mô hình vận hành hiện tại không có vai trò kế toán riêng; `SUPER_ADMIN` là quản lý cấp cao nhất và chịu trách nhiệm các quyết định kho có rủi ro.
- `STAFF_ADMIN` giữ các thao tác cơ bản: xem tồn kho, tạo phiếu nhập, sửa phiếu ở trạng thái `DRAFT`/`PROCESSING_IMEI`, xử lý IMEI/serial, tạo yêu cầu điều chỉnh hoặc kiểm kê nếu được cấp quyền tương ứng.
- Các quyết định quản lý gồm duyệt phiếu nhập, hoàn tất phiếu để cập nhật tồn, hủy phiếu đã đi vào quy trình, đảo phiếu nhập, duyệt kiểm kê, duyệt điều chỉnh tồn và duyệt chỉnh sửa IMEI/serial chỉ dành cho `SUPER_ADMIN`.
- Hai endpoint điều chỉnh tồn trực tiếp theo sản phẩm/biến thể được khóa về `SUPER_ADMIN`; staff phải đi qua phiếu điều chỉnh tồn có duyệt để tránh bỏ qua chứng từ.
- Endpoint đổi trạng thái phiếu nhập vẫn dùng quyền vận hành `inventory:adjust` để staff có thể chuyển phiếu từ `DRAFT` sang `PROCESSING_IMEI`; service chặn các trạng thái `APPROVED`, `COMPLETED`, `CANCELLED` nếu người gọi không phải `SUPER_ADMIN`.
- Migration `069_inventory_super_admin_approval_scope.sql` rút quyền `inventory:approve` và `inventory:reserve` khỏi role `STAFF_ADMIN`, đồng thời bảo đảm `SUPER_ADMIN` có các quyền quyết định kho.
- Frontend màn `Quản lý nhập kho` chỉ hiển thị nút duyệt, hoàn tất, hủy và đảo phiếu cho Super Admin; staff chỉ thấy các thao tác phù hợp với vai trò vận hành.
- Nếu phiếu đã ở `PENDING_APPROVAL`, `PENDING_SHORTAGE_APPROVAL` hoặc `APPROVED` mà cần sửa, chỉ Super Admin được trả phiếu về `DRAFT`; thao tác này tiếp tục ghi audit theo cơ chế reset phiếu hiện có.
- Chưa đưa PO/GRN/invoice matching, kế toán giá vốn đầy đủ hoặc đa kho vào phạm vi vì hệ thống hiện tại là cửa hàng một chi nhánh, không có module kế toán riêng.

## Update 2026-06-17 - Hiển thị lỗi xác nhận IMEI/serial trong modal nhập kho

- Modal `Bổ sung IMEI/serial number` nay bắt lỗi khi gọi API xác nhận danh sách mã định danh và hiển thị thông báo lỗi ngay trong modal thay vì để promise lỗi văng ra console.
- Trạng thái đang gửi được khóa nút xác nhận để tránh bấm lặp trong lúc backend đang kiểm tra danh sách IMEI/serial.
- Quy tắc backend validate serial number không đổi: serial phải có định dạng hợp lệ theo `SERIAL_PATTERN`; các mã quá ngắn như `Y`, `A`, `YA` vẫn bị từ chối và thông báo lỗi được trả về UI.

## Update 2026-06-16 - Siết chuẩn doanh nghiệp cho phiếu nhập kho

- Hoàn tất và đảo phiếu nhập kho nay kiểm tra serial number theo đúng phạm vi sản phẩm, đồng bộ với migration unique `(product_id, serial_number)`. Tránh chặn nhầm hoặc đảo nhầm khi hai sản phẩm khác nhau có cùng serial number.
- Phiếu nhập kho chặn trùng dòng theo cặp sản phẩm/biến thể trong cùng chứng từ, tương tự phiếu kiểm kê và phiếu điều chỉnh, để tránh cộng tồn hoặc nhập mã định danh lặp do thao tác nhầm.
- Bổ sung audit nghiệp vụ vào `security_audit_logs` cho các thao tác tạo, sửa, xóa, bổ sung IMEI/serial, đổi trạng thái và đảo phiếu nhập kho. Audit lưu mã phiếu, trạng thái trước/sau, số dòng và snapshot dòng chính để truy vết thay đổi chứng từ.
- Tách bước nhập IMEI/serial khỏi bước duyệt: khi nhập đủ mã định danh, phiếu chuyển sang `PENDING_APPROVAL`; khi nhập thiếu vẫn chuyển sang `PENDING_SHORTAGE_APPROVAL`. Chỉ endpoint đổi trạng thái với quyền `inventory:approve` mới đưa phiếu sang `APPROVED`.
- Backend chặn người lập phiếu tự duyệt phiếu nhập kho để tăng kiểm soát phân tách nhiệm vụ.
- Các thay đổi này chưa thay thế phân hệ mua hàng đầy đủ như PO/GRN/invoice matching, khóa kỳ kế toán hoặc ràng buộc tách người tạo/người duyệt; nếu triển khai WMS/ERP hoàn chỉnh cần thiết kế riêng các luồng đó.

## Update 2026-06-16 - Dọn bản revision khỏi tồn kho khởi tạo

- Xóa các sản phẩm SKU `REV-%` còn sót trong database local vì đây là bản nháp/chỉnh sửa đã duyệt, không phải sản phẩm nghiệp vụ hiện hành.
- Trước khi xóa đã kiểm tra không có `order_items`, bundle/accessory, reservation hoặc transaction bán hàng tham chiếu đến các bản `REV-%`.
- Các dòng tồn kho phát sinh từ bản revision trong phiếu `NK-KHOI-TAO-20260615-0001` được loại bỏ theo cascade: 13 sản phẩm, 64 biến thể, 10 dòng phiếu nhập, 10 log nhập kho, 13 dòng tồn kho và 296 serial.
- Sau khi dọn, phiếu nhập khởi tạo còn 290 dòng, tổng số lượng 5.661 và tổng tiền 73.178.390.000đ; các SKU `REV-%` không còn trong bảng sản phẩm/tồn kho.
- Siết query read-model tồn kho và danh sách phiếu nhập để loại sản phẩm `MERGED` hoặc `deleted_at IS NOT NULL`, tránh bản revision cũ lọt lại vào tồn kho/xuất phiếu nếu còn dữ liệu lịch sử.

## Update 2026-06-16 - Ràng buộc sản phẩm được phép nhập kho

- Phiếu nhập kho chỉ cho phép nhập sản phẩm trạng thái `ACTIVE`, chưa bị xóa và không bị ẩn theo danh mục/thương hiệu.
- Nếu sản phẩm đang `DISCONTINUED`, `INACTIVE`, `ARCHIVED`, `MERGED`, `DRAFT`, `REVISION_DRAFT`, `PENDING` hoặc trạng thái khác `ACTIVE`, backend từ chối tạo/sửa phiếu nhập với lỗi rõ theo từng dòng.
- Nếu sản phẩm gốc đang có bản chỉnh sửa `REVISION_DRAFT` hoặc `PENDING` chưa duyệt/hủy, backend từ chối nhập kho để tránh nhập tồn theo dữ liệu sản phẩm chưa ổn định.
- Biến thể được nhập kho phải còn active, chưa bị xóa và không ở trạng thái `deleted`/`archived`; danh sách tự chọn biến thể cũng chỉ lấy biến thể hợp lệ.
- Frontend lọc sản phẩm không hợp lệ khỏi picker nhập kho và chặn submit sớm với các trạng thái UI biết được; backend vẫn là lớp kiểm soát chính cho trường hợp có bản chỉnh sửa chờ duyệt.

## Update 2026-06-16 - Mẫu in phiếu nhập kho dạng chứng từ

- Modal xem phiếu nhập kho nay có mẫu in riêng theo bố cục chứng từ `Phiếu nhập kho`: thông tin đơn vị, mẫu số, ngày chứng từ, số phiếu, nhà cung cấp/người giao hàng, lý do nhập, kho nhận, ghi chú.
- Header phiếu in dùng tên cửa hàng `ELECTROMART VIỆT NAM` và mô tả ngành hàng công nghệ thay cho placeholder chung.
- Bảng in dùng cột `STT`, tên hàng hóa, mã số/SKU, đơn vị tính, số lượng theo chứng từ, thực nhập, đơn giá và thành tiền; dòng cuối cộng tổng số lượng và tổng giá trị nhập.
- Phiếu in có dòng `Tổng số tiền (Viết bằng chữ)` và khu vực ký tên cho người lập phiếu, người giao hàng, thủ kho, kế toán trưởng/bộ phận có nhu cầu nhập.
- Giao diện xem phiếu trên màn hình vẫn giữ nguyên; khi bấm in chỉ hiện mẫu chứng từ A4, tránh in cả modal quản trị.
- Bổ sung xuất phiếu dạng Word `.doc` bằng file HTML độc lập và xuất PDF qua cửa sổ chứng từ đầy đủ để lưu bằng `Save as PDF`; cả hai dùng dữ liệu chứng từ đầy đủ, không phụ thuộc vùng cuộn của modal.
- Nâng cấp xuất file sang backend: thêm dependency `reportlab` và `python-docx`, module `document_export_service.py`, endpoint `GET /admin/inventory/receipts/{reference_code}/export?format=pdf|docx`. Frontend tải trực tiếp file `.pdf` hoặc `.docx` từ backend, phù hợp để tái dùng cho hóa đơn khách hàng sau này.
- Mẫu xuất PDF/DOCX bỏ dòng trạng thái mã định danh trong phần tên hàng; phần mô tả biến thể hiển thị `Phân loại: màu - cấu hình` bằng tiếng Việt nếu có, còn SKU/mã hàng chỉ nằm ở cột `Mã số`.
- Tăng độ rộng cột `STT` trong mẫu PDF và mẫu in HTML để số thứ tự nhiều chữ số không bị tách xuống dòng.
- Bỏ khối `Mẫu số: 01 - VT / Theo dõi nhập kho nội bộ` khỏi header phiếu, đồng thời bỏ nhãn `Phân loại:` trong phần tên hàng; nếu có màu/cấu hình thì chỉ hiển thị trực tiếp giá trị màu/cấu hình.
- Khi xuất PDF/DOCX, các dòng cùng tên sản phẩm, SKU biến thể, màu/cấu hình, đơn vị tính và đơn giá được gộp lại để tránh chứng từ hiển thị nhiều dòng giống nhau do dữ liệu catalog có bản ghi sản phẩm/biến thể trùng về mặt hiển thị; số lượng và thành tiền được cộng dồn.

## Update 2026-06-15 - Việt hóa trạng thái IMEI/Serial trong tồn kho

- Modal `Danh sách IMEI / Serial` trong màn `Quản lý tồn kho` không còn hiển thị trực tiếp mã trạng thái kỹ thuật như `IN_STOCK`.
- Frontend map trạng thái mã định danh sang nhãn tiếng Việt: `Còn trong kho`, `Đang giữ`, `Đã bán`, `Đang bảo hành`, `Loại bỏ`, `Ngừng sử dụng`, `Đã đảo phiếu`.
- Giá trị API/DB vẫn giữ enum kỹ thuật để không ảnh hưởng logic nhập kho, giữ hàng, bán hàng, bảo hành và đảo phiếu.

## Update 2026-06-15 - Hiển thị người thao tác phiếu nhập

- Danh sách/xem chi tiết phiếu nhập nay trả thêm tên hiển thị cho người tạo, người duyệt, người hoàn tất, người hủy và người đảo phiếu bằng cách join `inventory_documents.*_by` với bảng `users`.
- Frontend ưu tiên hiển thị `createdByName`, `approvedByName`, `postedByName`, `reversedByName`; nếu thiếu tên mới fallback về UUID rút gọn hoặc `-`.
- Phiếu nhập khởi tạo bằng script có mã `NK-KHOI-TAO-%` không có tài khoản thao tác nên hiển thị `Hệ thống` cho người tạo/duyệt/hoàn tất.

## Update 2026-06-15 - Serial number unique theo từng sản phẩm

- Đổi luật trùng serial number từ unique toàn hệ thống sang unique theo cặp `(product_id, serial_number)`, cho phép hai sản phẩm khác nhau dùng cùng một serial number nếu nghiệp vụ cần.
- Migration `068_product_serial_number_product_scope_unique.sql` bỏ constraint unique cũ trên `serial_number` và tạo unique index mới `idx_product_serial_numbers_product_serial_unique`.
- Backend kiểm tra serial number khi nhập kho, bổ sung mã hoặc duyệt chỉnh sửa theo phạm vi cùng sản phẩm; nếu cùng sản phẩm đã có serial thì từ chối, còn khác sản phẩm thì cho phép.
- Đã sinh serial khởi tạo cho các dòng tồn đang bật quản lý serial number: `6.100` serial ở trạng thái `IN_STOCK`, nguồn `NK-KHOI-TAO-20260615-0001`.
- Kiểm tra dữ liệu sau khi sinh: không có serial trùng trong cùng sản phẩm, có serial được dùng lại giữa nhiều sản phẩm khác nhau, và số serial theo từng dòng tồn khớp tồn thực tế.

## Update 2026-06-15 - Phiếu điều chỉnh tồn có duyệt

- Bổ sung quy trình `Phiếu điều chỉnh tồn` trong màn `Quản lý tồn kho` để xử lý các chỉnh sửa thủ công từng sản phẩm/biến thể khi phát hiện lệch tồn ngoài kỳ kiểm kê.
- API `GET /admin/inventory/adjustments` trả danh sách phiếu điều chỉnh, trạng thái, tổng số dòng, tổng lệch tuyệt đối, lệch ròng và chi tiết từng dòng.
- API `POST /admin/inventory/adjustments` tạo chứng từ `inventory_documents.document_type = ADJUSTMENT` ở trạng thái `DRAFT`; mỗi dòng lưu tồn hiện tại, tồn đề xuất, chênh lệch, lý do điều chỉnh và ghi chú.
- Backend kiểm tra tồn hiện tại lúc tạo phiếu; nếu tồn hệ thống đã khác số người dùng nhìn thấy thì từ chối tạo phiếu để tránh tạo yêu cầu trên dữ liệu cũ.
- API `PATCH /admin/inventory/adjustments/{reference_code}/status` dùng quyền `inventory:approve`; khi duyệt mới cập nhật tồn sản phẩm/biến thể, cập nhật `inventory_levels`, ghi `inventory_adjustment_logs` và đồng bộ tồn sản phẩm cha nếu dòng là biến thể.
- Khi hủy phiếu điều chỉnh, backend chỉ đổi trạng thái sang `CANCELLED`, không cập nhật tồn và không ghi log điều chỉnh.
- Frontend thêm nút `Điều chỉnh` trên từng dòng tồn kho, modal tạo phiếu với tồn hiện tại, tồn đề xuất, chênh lệch và lý do bắt buộc; danh sách phiếu điều chỉnh có thao tác xem, duyệt và hủy.
- Migration `067_inventory_adjustment_approval_workflow.sql` thêm index cho chứng từ `ADJUSTMENT` và bảo đảm quyền `inventory:adjust` được gán cho vai trò quản trị.

## Update 2026-06-15 - Kiểm kê kho và duyệt chênh lệch

- Bổ sung quy trình kiểm kê kho trong màn `Quản lý tồn kho`: tạo phiếu kiểm kê từ các dòng tồn kho đang hiển thị, nhập số lượng thực đếm và lưu phiếu ở trạng thái `DRAFT`.
- API `GET /admin/inventory/stock-counts` trả danh sách phiếu kiểm kê, tổng số dòng, tổng lệch tuyệt đối và lệch ròng để quản trị viên xem nhanh mức sai lệch.
- API `POST /admin/inventory/stock-counts` tạo chứng từ `inventory_documents.document_type = COUNT` và lưu từng dòng vào `inventory_document_lines` với `expected_quantity`, `counted_quantity`, `variance_quantity`.
- API `PATCH /admin/inventory/stock-counts/{reference_code}/status` dùng quyền `inventory:approve`; khi duyệt mới cập nhật tồn sản phẩm/biến thể, cập nhật `inventory_levels.last_counted_at`, ghi `inventory_adjustment_logs` loại `ADJUSTMENT` với lý do kiểm kê và refresh read-model tồn kho.
- Danh sách phiếu kiểm kê có nút xem chi tiết từng dòng để người duyệt kiểm tra tồn hệ thống, số thực đếm, chênh lệch và ghi chú trước khi duyệt.
- Khi hủy phiếu kiểm kê, backend chỉ đổi trạng thái sang `CANCELLED`, không ghi thay đổi tồn.
- Migration `066_inventory_stock_count_workflow.sql` thêm index cho chứng từ `COUNT` và bảo đảm quyền `inventory:count` tồn tại cho vai trò quản trị.
- Phạm vi hiện tại mới kiểm kê theo số lượng sản phẩm/biến thể; đối soát IMEI/serial từng chiếc nên làm thành bước riêng để tránh thay đổi hoặc loại bỏ mã định danh sai nghiệp vụ.

## Update 2026-06-15 - Danh sách chờ duyệt và lịch sử chỉnh sửa mã

- Màn `Quản lý tồn kho` hiển thị khối `Yêu cầu chỉnh sửa IMEI/Serial chờ duyệt` ngay phía trên bảng tồn kho để người có quyền duyệt không phải mở từng sản phẩm mới thấy việc đang chờ xử lý.
- API `GET /admin/inventory/identifier-edit-requests?status=PENDING` trả danh sách yêu cầu chỉnh sửa theo trạng thái, kèm sản phẩm, biến thể, mã hiện tại, mã đề xuất, lý do và thông tin quyết định.
- Modal `Danh sách IMEI / Serial` trả thêm `editRequests` để xem lịch sử yêu cầu đã duyệt/hủy/chờ duyệt của đúng sản phẩm/biến thể đang xem.
- Frontend dùng chung thao tác duyệt/hủy trong khối chờ duyệt và trong modal chi tiết; sau khi xử lý sẽ tải lại danh sách chờ duyệt, modal mã và read-model tồn kho.
- Query list request dùng cast rõ ràng cho tham số nullable (`status`, `product_id`, `variant_id`) để tránh lỗi asyncpg `could not determine data type of parameter` khi lọc toàn cục hoặc không truyền biến thể.

## Update 2026-06-15 - Duyệt chỉnh sửa IMEI/Serial trong tồn kho

- Màn `Quản lý tồn kho` có thể mở danh sách chi tiết IMEI và serial number của từng sản phẩm/biến thể đang theo dõi mã định danh.
- Khi phát hiện IMEI hoặc serial number sai, admin tạo yêu cầu chỉnh sửa kèm lý do; hệ thống lưu yêu cầu ở trạng thái `PENDING` và chưa cập nhật ngay vào `product_imeis` hoặc `product_serial_numbers`.
- Bổ sung bảng `inventory_identifier_edit_requests` để lưu mã hiện tại, mã đề xuất, lý do, người yêu cầu, người duyệt/hủy và ghi chú quyết định.
- Backend chặn mỗi mã chỉ có một yêu cầu chỉnh sửa đang chờ duyệt, kiểm tra định dạng IMEI/serial và kiểm tra trùng mã trước khi tạo yêu cầu và trước khi duyệt.
- Quyền `inventory:adjust` được dùng để tạo yêu cầu chỉnh sửa; quyền `inventory:approve` được dùng để duyệt hoặc hủy yêu cầu.
- Khi duyệt, backend khóa yêu cầu và mã gốc, xác minh mã gốc chưa bị thay đổi sau lúc tạo yêu cầu rồi mới cập nhật giá trị mới; khi hủy thì chỉ đổi trạng thái yêu cầu, không thay đổi mã gốc.
- Migration `065_inventory_identifier_edit_requests.sql` đã được thêm vào `backend/scripts/run_migrations.py`.
- Sau review, bổ sung export schema `InventoryIdentifierEditRequestPayload` / `InventoryIdentifierEditDecisionPayload` trong `app.api.schemas.admin`, chặn lý do toàn khoảng trắng và chặn serial number mới rỗng sau khi trim để tránh lỗi runtime/DB 500.

## Update 2026-06-15 - Nhập thiếu IMEI/Serial theo từng sản phẩm

- Modal bổ sung IMEI/Serial trong màn hình nhập kho hiển thị rõ từng dòng sản phẩm/biến thể đang được nhập mã định danh, kèm số lượng đã nhập và số lượng còn thiếu của riêng dòng đó.
- Khi một dòng sản phẩm thiếu IMEI hoặc serial number, UI bắt buộc nhập lý do thiếu ngay trong dòng sản phẩm đó thay vì dùng một lý do chung cho toàn phiếu.
- Admin phải tick `Xác nhận nhập thiếu` ở đúng dòng sản phẩm còn thiếu trước khi hệ thống cho gửi danh sách thiếu; nếu chưa tick, UI yêu cầu nhập đủ mã hoặc xác nhận thiếu để tránh gửi thiếu do đang nhập dở.
- Payload `POST /admin/inventory/receipts/{reference_code}/imeis` hỗ trợ thêm `acceptShortage` và `shortageReason` ở cấp từng dòng; backend từ chối dòng thiếu mã nếu chưa có `acceptShortage = true`.
- API vẫn giữ `shortageReason` cấp phiếu để tương thích với client cũ, nhưng client mới nên gửi lý do thiếu theo từng dòng.
- Backend lưu `shortageReason` vào metadata của đúng dòng thiếu mã; ghi chú trạng thái phiếu gom các lý do thiếu của những dòng bị thiếu để phục vụ tra cứu nhanh.
- Modal xem phiếu nhập hiển thị số mã còn thiếu và lý do thiếu ngay trên từng dòng sản phẩm/biến thể để người duyệt không phải đọc ghi chú tổng hợp.

## Update 2026-06-15 - Xóa phiếu nhập nháp

- Bổ sung API `DELETE /admin/inventory/receipts/{reference_code}` để xóa phiếu nhập chỉ khi phiếu còn ở trạng thái `DRAFT` và chưa ghi sổ kho.
- Backend khóa phiếu bằng `FOR UPDATE`, kiểm tra trạng thái, xóa dòng `inventory_document_lines` trước rồi mới xóa header `inventory_documents`.
- Frontend chỉ hiển thị nút xóa cho phiếu `Nháp`; các trạng thái đã vào quy trình vẫn dùng `Hủy`, còn phiếu đã hoàn tất vẫn dùng `Đảo phiếu`.

## Update 2026-06-13 siết hoàn tất phiếu nhập kho

- Giữ nguyên mô hình duyệt theo quyền `inventory:approve`; Super Admin có thể là người duyệt phiếu nhập, không áp dụng ràng buộc maker-checker bắt buộc cho staff trong lần này.
- Phiếu nhập nay lưu actor theo từng mốc nghiệp vụ: `created_by` khi tạo phiếu, `approved_by` khi duyệt, `posted_by` khi hoàn tất và `cancelled_by`/`cancelled_at` khi hủy.
- Bổ sung migration `062_inventory_receipt_audit_actors.sql` để thêm `posted_by`, `cancelled_by`, `cancelled_at` và index tra cứu actor cho chứng từ tồn kho.
- Khi hoàn tất phiếu nhập, backend nay kiểm tra `posted_at` của chứng từ đang bị khóa `FOR UPDATE`; nếu phiếu đã từng post tồn kho thì từ chối hoàn tất lại để tránh cộng tồn lặp khi retry/race.
- Log nhập kho khi post phiếu dùng đúng `inventory_documents.target_location_id` đã lưu trên phiếu thay vì hard-code `MAIN` / `Kho chính`; với cấu hình một chi nhánh hiện tại vẫn fallback về kho chính nếu thiếu dữ liệu.
- Màn nhập kho đổi nhãn thao tác bổ sung mã định danh từ IMEI sang IMEI/Serial để không gây hiểu nhầm với sản phẩm chỉ quản lý serial number.
- Migration serial number `060_product_serial_number_management.sql` đã có trong `backend/scripts/run_migrations.py`; cần bảo đảm DB môi trường chạy migration này trước khi coi serial number là đã live.
- Bổ sung migration `063_inventory_receipt_reversal.sql` và API `POST /admin/inventory/receipts/{reference_code}/reverse` để đảo phiếu nhập đã `COMPLETED` bằng chứng từ `REVERSAL` riêng, không dùng `CANCELLED` cho phiếu đã post.
- Khi đảo phiếu, backend chỉ cho xử lý nếu tồn kho biến thể còn đủ và toàn bộ IMEI/serial của phiếu còn ở trạng thái `IN_STOCK`; sau đó giảm tồn, ghi log `REVERSAL`, chuyển mã định danh sang `REVERSED` và đánh dấu phiếu gốc `REVERSED`.
- Với sản phẩm quản lý cả IMEI và serial number, danh sách bổ sung phải khớp số lượng theo từng máy; backend không còn cho phép số IMEI khác số serial rồi lấy `min(...)` vì dễ làm lệch số mã định danh so với tồn thực nhận.
- Bổ sung migration `064_inventory_levels_moving_average_cost.sql`; khi hoàn tất phiếu nhập, backend cập nhật `inventory_levels.on_hand_quantity` và `average_unit_cost` theo phương pháp moving average dựa trên `unitCost` của dòng nhập.
- Khi đảo phiếu, backend giảm `inventory_levels.on_hand_quantity` nhưng giữ nguyên `average_unit_cost`; đây là cách bảo toàn giá vốn bình quân hiện hành cho lượng tồn còn lại sau chứng từ bù trừ.
- API tồn kho và CSV export trả thêm `averageUnitCost`; màn `Quản lý tồn kho` hiển thị cột `Giá vốn BQ`.

## Update 2026-06-13 tách tab IMEI/Serial trong xem phiếu nhập

- Modal xem phiếu nhập kho hiện có tab `Thông tin phiếu nhập` và tab `Danh sách IMEI / Serial` riêng.
- Trong bảng chi tiết nhập kho, dòng nào có quản lý IMEI hoặc serial number thì trạng thái mã định danh là nút có thể bấm.
- Khi bấm trạng thái mã định danh của một dòng sản phẩm, modal tự chuyển sang tab `Danh sách IMEI / Serial` và chỉ hiển thị IMEI/serial của đúng dòng sản phẩm/biến thể đó.
- Tab danh sách mã có nút `Xem tất cả` để bỏ lọc và xem toàn bộ IMEI/serial trong phiếu.
- Verification: `npm run lint` trong `frontend` pass.
## Update 2026-06-13 xem phiáº¿u nháº­p kho theo IMEI/Serial

- Modal xem phiếu nhập kho được chuẩn hóa thành hai phần: `Thông tin phiếu nhập` và `Chi tiết nhập kho / IMEI / Serial`.
- Bảng chi tiết nhập kho hiển thị riêng `SL nhập`, `SL đã nhập IMEI`, `SL đã nhập Serial`, giá nhập, thành tiền và trạng thái từng dòng.
- Trạng thái dòng hiện tính song song cho IMEI và serial number: đủ thì hiển thị `Đủ IMEI` / `Đủ Serial`, thiếu thì hiển thị số lượng còn thiếu tương ứng.
- Nút in phiếu phân biệt `In phiếu nhập tạm` và `In phiếu nhập hoàn chỉnh`; phiếu tạm có cảnh báo “Phiếu nhập chưa hoàn tất do chưa bổ sung đủ IMEI/Serial.”
- Danh sách mã định danh trong phiếu in/xem vẫn gom cả IMEI và serial number, có cột loại mã để dùng serial giống IMEI.
- Verification: `npm run lint` trong `frontend` pass.

## Update 2026-06-13 xem thông tin phiếu nhập kho

- Màn `Quản lý nhập kho` có thêm nút `Xem` trên từng phiếu nhập.
- Nút này mở modal chỉ đọc, hiển thị thông tin header phiếu, trạng thái, lý do nhập, nhà cung cấp, ngày tạo, ghi chú, tổng số dòng, tổng số lượng, giá trị nhập và toàn bộ dòng sản phẩm.
- Modal hiển thị thêm danh sách IMEI và serial number đã nhập theo từng dòng sản phẩm nếu phiếu có quản lý mã định danh.
- Modal phân biệt phiếu tạm/chờ bổ sung IMEI với phiếu hoàn chỉnh: nếu dòng hàng còn thiếu IMEI/serial sẽ hiển thị cảnh báo và nút `In phiếu tạm`; nếu phiếu đã hoàn tất và đủ mã định danh sẽ hiển thị `In phiếu hoàn chỉnh`.
- Phần xem phiếu tách thành `Thông tin phiếu nhập`, bảng chi tiết dòng nhập, và bảng riêng `Danh sách IMEI / Serial` có STT, sản phẩm, SKU/biến thể, loại mã và mã định danh.
- Modal xem phiếu nhập không hiển thị các thao tác nghiệp vụ như duyệt, hủy, hoàn tất hoặc nhập IMEI/serial; chỉ có nút `Đóng` để tránh nhầm với form thao tác.
- Verification: `python -m py_compile backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/application/services/inventory_service.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-13 phân loại lý do nhập kho

- Phiếu nhập kho có thêm mã lý do nhập ở cấp phiếu: `NK_MUA`, `NK_TRA_NCC`, `NK_KH_TRA`, `NK_BH`, `NK_DIEUCHINH`, `NK_CHUYEN`, `NK_SANXUAT`, `NK_KHAC`.
- Backend lưu mã này vào `inventory_documents.reason` để tránh thêm migration mới; log tồn kho khi hoàn tất phiếu cũng dùng cùng mã nghiệp vụ thay vì ghi chung `Nhập kho`.
- Khi chọn `NK_KHAC`, backend và frontend đều yêu cầu ghi rõ lý do trong `Ghi chú chung`.
- Danh sách phiếu nhập hiển thị thêm cột `Lý do nhập`; ô tìm kiếm có thể tìm theo mã lý do.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-13 IMEI chính và IMEI bổ sung

- Bổ sung migration `061_product_imei_primary.sql` để thêm cột `product_imeis.is_primary`.
- Mỗi sản phẩm hoặc biến thể có thể có nhiều IMEI, nhưng chỉ có tối đa một IMEI chính nhờ unique index riêng cho dòng không có biến thể và dòng có biến thể.
- Dữ liệu IMEI cũ được tự gán IMEI chính theo bản ghi đầu tiên của từng sản phẩm/biến thể nếu trước đó chưa có IMEI chính.
- Khi nhập kho, IMEI đầu tiên của sản phẩm/biến thể sẽ tự trở thành IMEI chính nếu chưa tồn tại IMEI chính; các IMEI còn lại là IMEI bổ sung.
- Read-model tồn kho và export CSV trả thêm `primaryImei` và `supplementalImei`; UI tồn kho hiển thị IMEI chính, số IMEI phụ và các trạng thái trong kho/đang giữ/đã bán.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass; migration `061_product_imei_primary.sql` đã chạy thành công trên DB local.

## Update 2026-06-13 quản lý serial number song song IMEI

- Thêm migration `060_product_serial_number_management.sql` để tạo bảng `product_serial_numbers` và mở rộng `categories.inventory_policy` với `inheritSerialPolicy`/`trackSerialNumber`.
- Backend tồn kho xác định chính sách serial number theo cùng thứ tự ưu tiên của IMEI: sản phẩm có `sales_config.serialPolicy` ở chế độ `MANUAL` được ưu tiên, nếu không thì lấy theo danh mục con/cha.
- Phiếu nhập kho lưu metadata dòng phiếu gồm `tracksSerialNumber` và `serialNumbers`; bước xử lý mã định danh hiện nhận cả IMEI và serial number. Nếu một dòng yêu cầu cả hai, số lượng thực nhận được tính theo số cặp mã đầy đủ nhỏ nhất.
- Khi hoàn tất phiếu nhập, backend ghi serial number vào `product_serial_numbers` với trạng thái `IN_STOCK`, đồng thời vẫn cộng tồn kho và ghi log nhập kho như trước.
- Read-model tồn kho và export CSV trả thêm `tracksSerialNumber` và `serialNumberSummary` để admin theo dõi serial trong kho/đang giữ/đã bán/bảo hành/phế phẩm.
- Frontend nhập kho hiển thị sản phẩm cần serial; modal bổ sung mã định danh cho phép nhập/import IMEI và serial number theo từng dòng; bảng tồn kho hiển thị tóm tắt cả IMEI và serial.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-05 Inventory Service Repository Split

- Tạo `app/infrastructure/database/repositories/inventory_repo.py` để gom truy vấn DB của module tồn kho.
- Chuyển SQL khỏi `app/application/services/inventory_service.py`, gồm: đọc tồn kho sản phẩm, danh sách biến thể, lịch sử điều chỉnh, cập nhật cấu hình tồn kho, xuất snapshot CSV, idempotency, cập nhật tồn kho biến thể, ghi IMEI và ghi log điều chỉnh tồn kho.
- `inventory_service.py` hiện giữ logic nghiệp vụ: tính cảnh báo tồn kho, merge `sales_config`, xuất CSV, chọn biến thể khi sản phẩm đơn giản, sinh IMEI, kiểm tra số lượng âm và đồng bộ lại giá/tồn kho sản phẩm cha.
- Sửa lại nhãn tiếng Việt trong CSV tồn kho sang Unicode đúng dấu.
- Kết quả kiểm tra: compile backend bằng `.venv` thành công; import `app.main`, `inventory_service` và `inventory_repo` đều hoạt động; `inventory_service.py` không còn SQL trực tiếp.

## Update 2026-06-12 vòng đời trạng thái phiếu nhập kho

- Phiếu nhập kho admin dùng vòng đời: `DRAFT` (Nháp), `PENDING_APPROVAL` (Chờ duyệt), `APPROVED` (Đã duyệt), `RECEIVING` (Đang nhập kho), `COMPLETED` (Hoàn tất), `CANCELLED` (Đã hủy).
- API `POST /admin/inventory/receipts` nay lưu phiếu vào `inventory_documents` và `inventory_document_lines`; trạng thái mặc định là `DRAFT`. Phiếu chỉ cộng tồn kho và ghi `inventory_adjustment_logs` khi tạo thẳng `COMPLETED` hoặc khi chuyển từ `APPROVED` sang `RECEIVING`/`COMPLETED`.
- API mới `PATCH /admin/inventory/receipts/{reference_code}/status` kiểm soát chuyển trạng thái theo luồng: `DRAFT -> PENDING_APPROVAL -> APPROVED -> RECEIVING -> COMPLETED`, và cho phép hủy trước khi bắt đầu nhập kho để tránh phải tạo reversal sau khi tồn kho đã được cộng.
- `GET /admin/inventory/receipts` đọc phiếu từ document tables, đồng thời vẫn hiển thị các phiếu nhập cũ trong `inventory_adjustment_logs` dưới trạng thái `COMPLETED` để không mất lịch sử.
- Migration `057_inventory_receipt_lifecycle.sql` mở rộng constraint trạng thái, cho phép dòng phiếu lưu cả sản phẩm và biến thể, bổ sung `metadata` để giữ danh sách IMEI nháp trước khi post tồn kho.
- Frontend màn `Quản lý nhập kho` hiển thị badge trạng thái và các hành động chuyển bước; popup tạo phiếu có nút `Lưu nháp`, `Gửi duyệt`, `Hoàn tất nhập kho`.
- Kết quả kiểm tra: đã chạy migration 057 local thành công, backend `py_compile` thành công, import `app.main`/`inventory_service`/`inventory_repo` thành công, `npm run lint` frontend thành công, và truy vấn danh sách phiếu nhập qua service trả dữ liệu hợp lệ.

## Update 2026-06-12 ưu tiên chính sách IMEI theo sản phẩm

- Luồng tồn kho vẫn lấy chính sách IMEI theo danh mục khi sản phẩm để `sales_config.imeiPolicy.mode = CATEGORY`.
- Nếu sản phẩm đặt `sales_config.imeiPolicy.mode = MANUAL`, backend ưu tiên `sales_config.imeiPolicy.trackImei` thay cho `categories.inventory_policy`.
- Cách này cho phép danh mục có chính sách mặc định nhưng từng sản phẩm vẫn có thể bật/tắt quản lý IMEI riêng khi nghiệp vụ cần ngoại lệ.

## Update 2026-06-12 tách bước bổ sung IMEI khỏi form lập phiếu nhập

- Form lập phiếu nhập không còn nhập IMEI. Admin chỉ chọn sản phẩm/biến thể, nhập số lượng dự kiến và giá nhập; phiếu mới luôn bắt đầu ở `DRAFT`.
- Vòng đời IMEI mới: `DRAFT -> PROCESSING_IMEI -> APPROVED -> COMPLETED`; trường hợp thiếu IMEI đi qua `PROCESSING_IMEI -> PENDING_SHORTAGE_APPROVAL -> APPROVED -> COMPLETED`.
- Khi chuyển sang `PROCESSING_IMEI`, số lượng dự kiến bị khóa ở cấp phiếu. IMEI được bổ sung qua endpoint riêng `POST /admin/inventory/receipts/{reference_code}/imeis`.
- Backend validate IMEI nghiêm ngặt: làm sạch dữ liệu, bắt đúng 15 chữ số theo regex `^[0-9]{15}$`, chặn trùng trong cùng phiếu và chặn trùng với bảng `product_imeis`.
- Nếu số IMEI hợp lệ bằng số lượng dự kiến, backend lưu IMEI vào metadata dòng phiếu và chuyển phiếu sang `APPROVED`; nút `Hoàn tất nhập kho` mới được mở.
- Nếu số IMEI ít hơn số lượng dự kiến, bắt buộc có lý do thiếu. Phiếu chuyển sang `PENDING_SHORTAGE_APPROVAL`; sau khi admin duyệt thiếu, hoàn tất nhập kho chỉ cộng tồn kho theo `receivedQuantity` thực nhận.
- Frontend màn `Nhập kho` có modal `Bổ sung IMEI` riêng với thanh tiến độ từng dòng, ô nhập tay hàng loạt và import Excel/CSV/TXT bằng thư viện `xlsx`.
- Migration `058_inventory_receipt_imei_workflow.sql` mở rộng trạng thái phiếu và chuẩn hóa metadata dòng phiếu: `tracksImei`, `plannedQuantity`, `receivedQuantity`, `imeis`, `shortageReason`.

## Update 2026-06-12 read-model tồn kho khả dụng theo chuẩn WMS

- Thêm API `GET /admin/inventory/levels` để màn `Quản lý tồn kho` đọc read-model chuyên dụng thay vì chỉ dựa vào danh sách sản phẩm catalog.
- Read-model tách rõ `physicalStock`, `reservedStock` và `availableStock`; `availableStock = max(physicalStock - reservedStock, 0)`.
- `reservedStock` được gom từ `inventory_reservations` còn `ACTIVE` chưa hết hạn và IMEI đang `RESERVED`; backend dùng giá trị lớn hơn để tránh đếm đôi khi một đơn hàng vừa có reservation record vừa khóa IMEI cụ thể.
- Read-model trả thêm `tracksImei` và `imeiSummary` gồm số IMEI `IN_STOCK`, `RESERVED`, `SOLD`, bảo hành và phế phẩm để admin nhìn được trạng thái chi tiết từng biến thể.
- Màn `Quản lý tồn kho` đổi bảng sang các cột `Tồn thực tế`, `Đang giữ`, `Khả dụng`, `IMEI`, `Cảnh báo`, `Trạng thái`; đồng thời sửa lại các nhãn tiếng Việt bị lỗi mã hóa trong component này.
- File export CSV tồn kho cũng đổi sang các cột WMS mới, gồm tồn thực tế, đang giữ, khả dụng, trạng thái, chính sách IMEI và tóm tắt IMEI.
- Migration `059_inventory_imei_enterprise_statuses.sql` mở rộng constraint trạng thái `product_imeis` để hỗ trợ trạng thái chuẩn `IN_WARRANTY` và `SCRAP`, vẫn giữ tương thích với `WARRANTY` và `RETIRED` cũ.
- Verification: `python -m py_compile app\application\services\inventory_service.py app\infrastructure\database\repositories\inventory_repo.py app\api\routers\admin_inventory.py scripts\run_migrations.py` pass; `npm run lint` trong `frontend` pass.

## Update 2026-06-15 - Chỉnh sửa phiếu nhập chưa hoàn tất

- Phiếu nhập có thể chỉnh sửa khi còn trong luồng chưa ghi sổ: `DRAFT`, `PROCESSING_IMEI`, `PENDING_SHORTAGE_APPROVAL`, `APPROVED`.
- Khi lưu thay đổi, backend cập nhật header/dòng phiếu, xóa dòng cũ và đưa phiếu về `DRAFT`; các thông tin duyệt/hủy cũ được xóa để bắt buộc chạy lại quy trình duyệt và nhập IMEI/Serial nếu cần.
- Phiếu đã `COMPLETED`, đã có `posted_at`, `CANCELLED` hoặc `REVERSED` không được chỉnh sửa qua API cập nhật phiếu nhập.
# Update 2026-06-18 - Consolidate database migrations

- Toàn bộ migration tồn kho cũ đến `073` đã được gộp vào `backend/migrations/init_database.sql`.
- Các file migration rời cũ đã được loại bỏ; thay đổi schema tiếp theo bắt đầu từ `001_*.sql`.

## Update 2026-06-27 (7) - Khắc phục hiển thị danh sách kệ xuất và ràng buộc số lượng

- **Sửa lỗi lọc kệ xuất**: Thay đổi điều kiện lọc trong `list_level_issue_candidates` của `inventory_repo.py` từ `GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0` thành `il.on_hand_quantity > 0`. Điều này khắc phục lỗi khi sản phẩm đã được giữ hàng (reserved) cho đơn hàng hiện tại, làm cho tồn khả dụng tạm thời bằng 0 và dẫn tới việc dropdown chọn kệ bị trống (không hiển thị kệ nào để bốc hàng).
- **Cải tiến UI dropdown chọn kệ**: Màn phiếu xuất kho (`AdminInventoryOutboundsTab.tsx`) hiển thị chi tiết cả số lượng thực tế trên kệ (`Tồn`) và số lượng còn dư chưa giữ (`Khả dụng`) theo định dạng `Kệ - Tên kệ (Tồn: X | Khả dụng: Y)` để nhân viên kho nắm thông tin rõ ràng.
- **Ràng buộc số lượng xuất kho**:
  - Bổ sung validation tại frontend chặn việc bấm `Cập nhật` (lưu nháp) nếu tổng số lượng đã chọn trên các kệ vượt quá số lượng yêu cầu của dòng sản phẩm.
  - Hiển thị thêm thông báo cảnh báo màu đỏ trực quan `(Vượt quá số lượng yêu cầu!)` ở dòng trạng thái khi số lượng đã chọn lớn hơn số lượng yêu cầu.
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

# Cập nhật 2026-07-03 - Hàng cũ hoàn về QC riêng

- Đơn hàng cũ đã `SHIPPED` khi đi qua `RETURNING -> RETURNED` không cộng lại `inventory_levels` của hàng mới.
- Thiết bị trong `used_devices` chuyển `SOLD -> RETURNED_QC`; admin phải thẩm định lại trước khi đưa thiết bị quay lại khu bán hàng cũ.
- Nếu QC lại đạt, thiết bị chỉ về `READY_FOR_PRICING` và bài đăng cũ về `DRAFT`; hàng cũ vẫn không tăng tồn bán được cho catalog cho đến khi bài đăng được duyệt lại theo module hàng cũ.
- Kết quả QC lại ghi vào `used_device_inspections` và cập nhật trực tiếp `used_devices`; không tạo phiếu nhập, không cộng `inventory_levels`, không mở FIFO hàng mới.
- Timeline lịch sử thiết bị hàng cũ đọc từ `used_device_events`, `used_device_inspections` và `used_device_prices`; đây là lịch sử nghiệp vụ hàng cũ, không phải sổ kho `inventory_adjustment_logs`.
- Dòng `order_items.used_device_id` tiếp tục bị bỏ qua trong FIFO/restock hàng mới để tránh làm sai tồn kho catalog.

# Cập nhật 2026-07-05 - Phân biệt quota flash sale và tồn kho vật lý

- Checkout đọc thêm flash sale đang hiệu lực khi khóa sản phẩm/biến thể để xác định giá bán, nhưng quota flash sale không thay thế tồn kho vật lý và không đi vào read-model tồn kho.
- Giữ hàng tồn kho vẫn dùng `inventory_reservations`; quota sale được giữ riêng trên `flash_sales.sold_quantity`.
- Khi đơn chưa giao bị hủy/thanh toán thất bại/hoàn trước khi xuất kho, hệ thống vừa đóng reservation tồn kho như cũ vừa hoàn lại quota flash sale nếu đơn từng dùng giá sale.
- Không dùng `remainingQuantity` của flash sale làm số lượng tồn có thể bán; đây chỉ là số suất được hưởng giá sale còn lại.
