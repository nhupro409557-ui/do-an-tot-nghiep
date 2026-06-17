# Inventory Management Notes

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
## Update 2026-06-13 xem phiếu nhập kho theo IMEI/Serial

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

## Update 2026-06-13 qu?n l? serial number song song IMEI

- Th?m migration `060_product_serial_number_management.sql` ?? t?o b?ng `product_serial_numbers` v? m? r?ng `categories.inventory_policy` v?i `inheritSerialPolicy`/`trackSerialNumber`.
- Backend t?n kho x?c ??nh ch?nh s?ch serial number theo c?ng th? t? ?u ti?n c?a IMEI: s?n ph?m `sales_config.serialPolicy` ? ch? ?? `MANUAL` ???c ?u ti?n, n?u kh?ng th? l?y theo danh m?c con/cha.
- Phi?u nh?p kho l?u metadata d?ng phi?u g?m `tracksSerialNumber` v? `serialNumbers`; b??c x? l? m? ??nh danh hi?n nh?n c? IMEI v? serial number. N?u m?t d?ng y?u c?u c? hai, s? l??ng th?c nh?n ???c t?nh theo s? c?p m? ??y ?? nh? nh?t.
- Khi ho?n t?t phi?u nh?p, backend ghi serial number v?o `product_serial_numbers` v?i tr?ng th?i `IN_STOCK`, ??ng th?i v?n c?ng t?n kho v? ghi log nh?p kho nh? tr??c.
- Read-model t?n kho v? export CSV tr? th?m `tracksSerialNumber` v? `serialNumberSummary` ?? admin theo d?i serial trong kho/?ang gi?/?? b?n/b?o h?nh/ph? ph?m.
- Frontend nh?p kho hi?n th? s?n ph?m c?n serial, modal b? sung m? ??nh danh cho ph?p nh?p/import IMEI v? serial number theo t?ng d?ng, b?ng t?n kho hi?n th? t?m t?t c? IMEI v? serial.
- Verification: `python -m py_compile backend/app/application/services/inventory_service.py backend/app/infrastructure/database/repositories/inventory_repo.py backend/app/api/schemas/admin/inventory.py backend/scripts/run_migrations.py` pass; `npm run lint` trong `frontend` pass.

﻿# Inventory Management Notes

## 1. Document purpose
- This file upgrades the inventory module notes from feature bullets into a combined BRD/SRS style reference.
- It separates business process, system design, data model, API direction, and phased implementation.
- It also records the gap between the current implementation and the enterprise-grade target architecture.

## 2. Current-state critique

### 2.1 Business logic mixed with UI flow
- The old description leaned on UI actions such as opening a popup or clicking inventory actions.
- For thesis-grade or enterprise documentation, inventory must be modeled as business processes and state transitions, not screen steps.

### 2.2 Single-stock-column bottleneck
- The current runtime still stores stock in `products.stock_quantity` and `product_variants.stock_quantity`.
- This is acceptable for a single logical warehouse, but it is not structurally sufficient for multi-warehouse inventory.

### 2.3 Costing model gap
- The current stock log can already capture `unit_cost`, but outgoing valuation and COGS are not yet controlled by a formal costing method.
- The target design standardizes on `MOVING_AVERAGE` first, with room to evolve to `FIFO` later if needed.

### 2.4 Internal control gap
- Direct inventory adjustment by one actor is fast, but it does not satisfy maker-checker control for high-risk operations such as stock count adjustments or reversals.

### 2.5 Concurrency gap
- The current implementation already uses transactional writes and row locking.
- The next enterprise step is to supplement direct deduction with `inventory_reservations` so checkout and payment flows can reserve stock first and post final issue later.

## 3. Target business process model

### 3.1 Inbound inventory process
1. Warehouse staff creates inbound document.
2. Document captures supplier, location, item lines, quantity, and unit cost.
3. Document stays `DRAFT` or `PENDING_APPROVAL`.
4. Checker approves document.
5. System posts inventory transaction.
6. On-hand quantity increases at `(item, location)`.
7. Moving-average cost is recalculated.
8. Immutable ledger entry is stored.

### 3.2 Outbound inventory process
1. Sales order or internal request creates reservation.
2. Reservation reduces allocable stock but does not reduce posted stock yet.
3. When shipment or issue is confirmed, reservation is consumed.
4. System posts outbound inventory transaction.
5. On-hand quantity decreases at `(item, location)`.
6. COGS is derived from the active costing method.

### 3.3 Stock count and adjustment process
1. Counter creates count sheet for a location.
2. Expected quantity is loaded from system balance.
3. Counted quantity is entered.
4. Variance is reviewed.
5. Checker approves variance posting.
6. Adjustment ledger entries are generated.

### 3.4 Reversal process
1. Authorized maker requests reversal of an existing posted document.
2. Checker approves reversal.
3. System posts compensating entries instead of editing old rows.

## 4. System requirements

### 4.1 Functional requirements
- Support inventory by product or variant and by warehouse location.
- Support inbound, outbound, transfer-ready, count, adjustment, reversal, and reservation flows.
- Support minimum stock, reorder point, cycle count period, and sale blocking rule.
- Support immutable transaction logs.
- Support approval workflow for high-risk inventory movements.
- Support inventory export for audit and operational use.

### 4.2 Non-functional requirements
- ACID transaction handling for all posted stock movements.
- Idempotency for API requests that can be retried.
- Row-level locking for balance updates.
- Clear audit trail for who created, approved, posted, and reversed stock documents.
- Backward compatibility during migration from single-warehouse to multi-warehouse mode.

## 5. Technical architecture

### 5.1 Current implementation
- Backend: FastAPI + Pydantic + async SQLAlchemy.
- Database: PostgreSQL.
- Admin UI: React + TypeScript.
- Current stock mutation safety: transaction boundary, pessimistic locking, append-only adjustment logs.

### 5.2 Enterprise target architecture
- Inventory balance source of truth moves to `inventory_levels`.
- Stock movement source of truth moves to `inventory_transactions`.
- Human workflow source of truth moves to `inventory_documents` and `inventory_document_lines`.
- Checkout and payment race mitigation moves to `inventory_reservations`.
- Cost valuation is controlled explicitly through `costing_method`.

## 6. Database design direction

### 6.1 New normalized entities
- `inventory_locations`
  - master data for warehouse, branch, or virtual fulfillment location
- `inventory_levels`
  - stock by `(product or variant, location)`
  - stores `on_hand_quantity`, `reserved_quantity`, `safety_stock_quantity`, `reorder_point_quantity`
- `inventory_documents`
  - document header for inbound, count, adjustment, reversal, transfer, reservation release
- `inventory_document_lines`
  - item-level quantities and costing context
- `inventory_transactions`
  - immutable posted ledger rows
- `inventory_reservations`
  - temporary allocation for cart, checkout, or order payment flow

### 6.2 Costing rule
- Standardized initial costing method: `MOVING_AVERAGE`
- Why this first:
  - easier to operate than FIFO in the current codebase
  - sufficient for thesis and mid-market commerce scope
  - compatible with multi-location inventory if cost is tracked per item/location or consolidated by rule set

## 7. Approval and control model

### 7.1 Maker-checker
- Maker creates draft or pending inventory document.
- Checker approves or rejects.
- Only approved documents can post stock movements.

### 7.2 Segregation of duties
- `inventory:adjust` is no longer the only future permission.
- Additional permissions are introduced for:
  - `inventory:approve`
  - `inventory:count`
  - `inventory:reserve`

## 8. Concurrency and risk handling

### 8.1 Current control
- `SELECT ... FOR UPDATE` is already used for direct stock updates.

### 8.2 Next control layer
- Introduce reservation records with expiration windows.
- Post final issue only after payment or fulfillment checkpoint.
- Handle lock timeout or retry logic at service layer.
- Preserve compensating transactions for reversals instead of editing posted rows.

## 9. API design direction

### 9.1 Current endpoints retained
- `GET /admin/products/{product_id}/inventory`
- `POST /admin/products/{product_id}/inventory/adjust`
- `PATCH /admin/products/{product_id}/inventory/settings`
- `GET /admin/inventory/export`

### 9.2 Next endpoints to add
- `POST /admin/inventory/documents`
- `POST /admin/inventory/documents/{id}/submit`
- `POST /admin/inventory/documents/{id}/approve`
- `POST /admin/inventory/documents/{id}/reject`
- `POST /admin/inventory/reservations`
- `POST /admin/inventory/reservations/{id}/release`
- `GET /admin/inventory/levels`
- `GET /admin/inventory/transactions`

## 10. What is implemented now
- Product and variant inventory view.
- Adjustment popup and manual inventory transaction capture.
- Supplier, unit cost, location code, and location name on inventory adjustments.
- Product-level minimum stock and sale-block setting.
- CSV export compatible with Excel.
- Automatic stock restoration on order cancellation in order flow.
- Immutable-style inventory log through append-only API behavior.

## 11. What is added in this phase
- Formal documentation restructure to BRD/SRS style.
- Non-breaking schema foundation for:
  - multi-warehouse inventory levels
  - inventory documents and approval workflow
  - posted transaction ledger
  - reservation handling
  - moving-average costing metadata

## 12. Migration strategy

### Phase A: Compatibility mode
- Keep existing `stock_quantity` columns active.
- Mirror initial balances into default location `MAIN`.
- Keep current UI running while new tables are introduced.

### Phase B: Dual-write mode
- New inventory services write to both legacy stock columns and new normalized inventory tables.
- Read models can still use legacy fields until validation is complete.

### Phase C: Full normalized mode
- Balance reads move to `inventory_levels`.
- Outbound flows use reservation plus posting.
- Legacy stock columns become derived or deprecated fields.

## 13. Files touched in this phase
- `backend/INVENTORY_MANAGEMENT_NOTES.md`
- `backend/migrations/036_inventory_settings_and_receipt_metadata.sql`
- `backend/migrations/037_inventory_enterprise_foundation.sql`
- `backend/migrations/017_admin_rbac_permissions.sql`
- `backend/migrations/init_database.sql`

## 14. Open decisions
- Whether product-level inventory should remain supported long-term or all stock should move to variant-only control.
- Whether moving-average cost is tracked globally or per location.
- Whether reservation happens at cart stage, checkout stage, or payment-initiation stage.

## 15. Update 2026-05-23

- Nhap kho co them danh sach IMEI tuy chon trong payload/UI.
- Neu giao dich la `RECEIPT`, co `variantId`, so luong tang > 0 va admin de thieu/bo trong IMEI, backend tu sinh IMEI theo `SKU bien the + 10 so ngau nhien`.
- Neu admin da nhap IMEI thi backend giu nguyen, chi bo qua IMEI trung bang `ON CONFLICT DO NOTHING`.
- Nen du lieu IMEI nam o bang `product_imeis`, gan duoc voi `product_id`, `variant_id`, trang thai ton kho va `service_payload` cho bao hanh/dich vu sau ban.
- Chinh sach danh muc nao can/khong can quan ly IMEI nam o `categories.inventory_policy`; danh muc con co the ke thua cha hoac override.
- File migration lien quan: `backend/migrations/040_catalog_inventory_services_foundation.sql`.

## 16. Update 2026-05-23 bo sung dich vu

- Man quan ly dich vu di kem co cac lua chon nhanh cho nhom dich vu:
  - `WARRANTY`
  - `EXTENDED_WARRANTY`
  - `ONE_FOR_ONE`
  - `INSTALLATION`
  - `CLEANING`
  - `SUPPORT`
- Thoi han dich vu chon theo cac moc 0/3/6/9/12/18/24/36 thang de phu hop yeu cau bao hanh va 1 doi 1, han che nhap tay sai.
- San pham chi gan dich vu tu danh sach admin da tao trong `attached_services`; khong nhap dich vu truc tiep trong form san pham.
- Man them/sua dich vu di kem trong admin da chuyen sang popup rieng, dong/moi/sua nhieu dich vu lien tiep khong can reload trang.
- Da them script `backend/scripts/seed_attached_services.py` de seed cac goi dich vu pho bien tren thi truong:
  - Bao hanh mo rong dien thoai/laptop 12-24 thang.
  - VIP 1 doi 1 dien thoai/laptop 12 thang.
  - Bao ve roi vo vao nuoc dien thoai 12 thang.
  - Ve sinh laptop, cai dat/chuyen du lieu, lap dat tai nha va ho tro ky thuat tai nha.
- `backend/scripts/run_migrations.py` da them migration `040_catalog_inventory_services_foundation.sql` de tao bang `attached_services` truoc khi seed.
- Lan seed moi nhat co 25 dich vu:
  - `PRODUCT_SERVICE`: 6 goi bao hanh mo rong, 4 goi VIP 1 doi 1, 2 goi bao ve roi vo/vao nuoc.
  - `SUPPORT_SERVICE`: 3 goi ve sinh, 5 goi lap dat, 5 goi ho tro/cai dat/chuyen du lieu.
- Ngay 2026-05-23 da sua truy van danh sach don hang de group them thong tin khach hang, tranh loi SQL lam admin khong tai duoc quy trinh sau ban.

## 17. Update 2026-05-23 chinh sach bao hanh mo rong ElectroMart

- `backend/scripts/seed_attached_services.py` da duoc cap nhat theo chinh sach bao hanh mo rong ElectroMart Viet Nam.
- Cac goi bao hanh san pham hien dung `price_mode = TIERED_AMOUNT`, bieu phi theo khoang gia nam trong `attached_services.metadata.priceTiers`.
- Danh sach goi bao hanh san pham dang seed:
  - `VIP-1D1-MOBILE-6M`, `VIP-1D1-MOBILE-12M`: 1 doi 1 VIP dien thoai/may tinh bang theo 17 bac gia.
  - `RVVN-MOBILE-12M`: roi vo - roi nuoc dien thoai/may tinh bang, ho tro toi da 90% chi phi sua chua.
  - `S24-MOBILE-12M`: S24+ dien thoai/may tinh bang moi theo 17 bac gia.
  - `VIP-1D1-LAPTOP-12M`: 1 doi 1 VIP laptop/MacBook theo 8 bac gia.
  - `S24-LAPTOP-12M`, `S24-LAPTOP-24M`: S24+ laptop/MacBook theo 8 bac gia.
  - `VIP-1D1-ACCESSORY-12M`, `S24-ACCESSORY-12M`: phu kien cao cap theo 11 bac gia.
  - `VIP-1D1-TV-12M`: 1 doi 1 VIP Tivi theo 17 bac gia.
- Metadata moi co cac truong chinh: `policyName`, `appliesTo`, `bindsToImei`, `priceTiers`, `processingTime`, `benefits`, `exclusions`, `refundRule`, `transferable`.
- Cac ma seed bao hanh cu dang dung percent da duoc an (`is_active = FALSE`) de tranh admin chon nham goi cu.

## 18. Update 2026-05-23 khoa bieu phi dich vu san pham

- Man dich vu khoa `PRODUCT_SERVICE` ve `price_mode = TIERED_AMOUNT`; admin khong con chon cach tinh gia hoac nhap gia/%/dinh muc cho nhom dich vu san pham.
- API admin cung enforce rule nay khi tao/sua `attached_services`, tranh payload cu ghi de ve gia thu cong.
- Khi gan dich vu vao san pham, he thong chi luu `service_id`; phi bao hanh se tra theo bieu phi chinh sach cua goi dich vu.

## 19. Update 2026-05-31 tự động phân giải tồn kho cấp sản phẩm

- Khắc phục lỗi điều chỉnh tồn kho cấp sản phẩm (khi `variantId` là NULL) bị ghi đè trở lại giá trị cũ bởi hàm `sync_parent_price_from_variants`.
- Khi nhận yêu cầu điều chỉnh tồn kho không chứa `variantId`:
  - Hệ thống tự động truy vấn danh sách các biến thể hoạt động của sản phẩm.
  - Nếu sản phẩm chỉ có duy nhất 1 biến thể hoạt động (sản phẩm đơn giản): tự động áp dụng điều chỉnh lên chính biến thể đó và đồng bộ ngược lại sản phẩm cha.
  - Nếu sản phẩm có từ 2 biến thể hoạt động trở lên: ném lỗi `HTTPException(400)` yêu cầu người dùng phải chỉ định biến thể cụ thể cần nhập/điều chỉnh kho nhằm đảm bảo tính chính xác nghiệp vụ.
  - Nếu không có biến thể hoạt động nào: ném lỗi `HTTPException(400)`.

## 20. Update 2026-06-01 admin service form completion feedback

- Sau khi thêm hoặc chỉnh sửa dịch vụ đi kèm thành công, popup dịch vụ được đóng như cũ và nay có thêm thông báo thành công rõ ràng.
- Thay đổi này giữ nhất quán với các form quản trị khác sau khi lưu xong, tránh để admin phải tự suy đoán thao tác đã hoàn tất hay chưa.

## 21. Update 2026-06-04 nhập kho một chi nhánh

- Màn nhập kho admin đã bỏ hai ô `Mã kho / chi nhánh` và `Tên kho / chi nhánh` vì cửa hàng đang vận hành một chi nhánh.
- Frontend không còn lưu cấu hình `preferredLocationCode` và `preferredLocationName` trong phần cài đặt tồn kho của sản phẩm.
- Backend không còn nhận/trả hai trường kho ưu tiên trong payload cấu hình tồn kho và file xuất CSV tồn kho.
- Các cột `location_code` và `location_name` trong lịch sử điều chỉnh kho vẫn được giữ lại để ghi nhận mặc định `MAIN` / `Kho chính` cho giao dịch nhập/xuất, tránh mất khả năng truy vết dữ liệu cũ.

## 22. Update 2026-06-08 tách tồn kho khỏi form sản phẩm

- Form quản trị sản phẩm không còn nhập `Tồn kho chung`.
- Lưu sản phẩm không được ghi đè `products.stock_quantity`; số lượng tồn kho do module Tồn kho/Nhập kho và luồng đơn hàng cập nhật.
- Biến thể mới tạo từ form catalog bắt đầu với tồn kho `0`, sau đó nhập kho qua màn tồn kho để đảm bảo có lịch sử giao dịch.

## 23. Update 2026-06-11 phiếu nhập kho nhiều dòng và IMEI bắt buộc theo chính sách

- Thêm API `POST /admin/inventory/receipts` để tạo một phiếu nhập kho có nhiều dòng sản phẩm/biến thể trong cùng một giao dịch.
- Mỗi dòng nhập kho cập nhật tồn kho biến thể, ghi `inventory_adjustment_logs` với `transaction_type = RECEIPT`, ghi nhà cung cấp, giá nhập, ghi chú và mã phiếu tham chiếu chung.
- Backend xác định sản phẩm có cần IMEI theo `categories.inventory_policy`: danh mục con được ưu tiên nếu không kế thừa, còn mặc định lấy theo danh mục cha.
- Nếu sản phẩm cần quản lý IMEI, số IMEI nhập phải đúng bằng số lượng của dòng nhập, không được trùng trong phiếu và không được trùng với `product_imeis` hiện có.
- Nếu sản phẩm không bật quản lý IMEI, backend từ chối payload có IMEI để tránh nhập dữ liệu serial sai nghiệp vụ.
- Luồng điều chỉnh tồn kho cũ cũng không còn tự sinh IMEI cho sản phẩm cần IMEI; admin phải nhập IMEI thật để phục vụ bán hàng và bảo hành sau này.
- Frontend tab Tồn kho có nút `Tạo phiếu nhập`, form phiếu nhập nhiều dòng, chọn sản phẩm/biến thể theo từng dòng và chỉ hiển thị vùng nhập IMEI khi sản phẩm thuộc nhóm cần theo dõi IMEI.
- Form phiếu nhập tự sinh mã theo dạng `NKyyyyMMdd-HHmmss`, ví dụ `NK20260611-153000`, để admin không phải nhập tay mã phiếu.
- Nhà cung cấp trong phiếu nhập được chọn từ danh sách nhà cung cấp đang hoạt động thay vì nhập text tự do; backend hiện vẫn lưu tên nhà cung cấp vào log để tương thích schema cũ.
- Bổ sung khối chọn nhanh sản phẩm trong form phiếu nhập: lọc theo danh mục, thương hiệu, từ khóa; tick nhiều sản phẩm rồi thêm vào phiếu. Nếu sản phẩm có nhiều biến thể, UI tự sinh một dòng nhập cho từng biến thể.
- Tách màn `Nhập kho` khỏi màn `Tồn kho`: `Nhập kho` quản lý danh sách phiếu nhập và tạo phiếu nhập mới; `Tồn kho` chỉ còn theo dõi số lượng, cảnh báo và xuất báo cáo tồn kho sản phẩm.
- Bổ sung API `GET /admin/inventory/receipts` để đọc danh sách phiếu nhập bằng cách gom các log `RECEIPT` theo `reference_code`, hiển thị nhà cung cấp, ngày nhập, tổng dòng, tổng số lượng, tổng giá trị và các dòng sản phẩm.
- Cập nhật UX chọn sản phẩm trong phiếu nhập: không còn tick sản phẩm cha rồi tự sinh toàn bộ biến thể. Admin chọn một sản phẩm cha, sau đó tick đúng các biến thể thực tế cần nhập; hệ thống chỉ sinh dòng cho các biến thể đã chọn để tránh rác dòng nhập và giảm tải giao diện.
- Cập nhật lưới dòng phiếu nhập từ card dọc sang table ngang để hiển thị được nhiều dòng cùng lúc. Các trường nhập thường xuyên (`Sản phẩm`, `Biến thể`, `Số lượng`, `Giá nhập`) nằm cùng hàng; `Lý do`, `Ghi chú`, `IMEI` được giữ gọn trong từng dòng.

## Refactor Structure Notes (June 2026)

### 1. Backend Service Layer Pattern
- Logic nghiệp vụ, các truy vấn database SQL, xử lý đồng bộ giá trị, quản lý IMEI, idempotency và xuất báo cáo tồn kho (CSV) đã được tách hoàn toàn ra khỏi Router Layer (`admin_inventory.py`) và chuyển giao sang Service Layer chuyên biệt: [inventory_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/inventory_service.py).
- Router [admin_inventory.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_inventory.py) được tối giản hóa tối đa, chỉ giữ vai trò định nghĩa endpoints FastAPI, Dependency Injection và chuyển tiếp lời gọi cho `inventory_service.py`.

### 2. Frontend Feature-First Architecture
- Module Quản lý Tồn kho được đóng gói hoàn chỉnh về thư mục tính năng độc lập tại: [src/features/admin-inventory/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-inventory/)
  - **Services**: [adminInventoryApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-inventory/services/adminInventoryApi.ts) chứa các hàm API tồn kho (được bóc tách từ `adminProductsApi.ts`).
  - **Hooks**: [useAdminInventoryLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-inventory/hooks/useAdminInventoryLogic.ts) xử lý logic nghiệp vụ và state của UI.
  - **Components**: [AdminInventoryTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-inventory/components/AdminInventoryTab.tsx) chứa UI tab Tồn kho.
- Các file điều phối chung như [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), và [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx) đã được cập nhật đường dẫn import mới.
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
