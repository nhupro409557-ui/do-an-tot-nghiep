# Product Management Notes

## Cập nhật 2026-07-14 - Chuẩn hóa bảo hành sản phẩm điện thoại

- Toàn bộ sản phẩm thuộc cây danh mục Điện thoại được đồng bộ chính sách bảo hành 12 tháng và một đổi một trong 30 ngày.
- Chính sách được ghi đồng thời vào `products.sales_config.warrantyPolicy` và snapshot tương thích `products.specifications._warrantyPolicy`, tránh trang chi tiết tiếp tục hiển thị “Bảo hành theo hãng” do dữ liệu cũ thiếu cấu hình.
- Migration `099_normalize_phone_warranty_policy.sql` bỏ qua sản phẩm đã xóa và bản ghi `MERGED`, nhưng vẫn chuẩn hóa sản phẩm đang bán, tạm ẩn hoặc lưu trữ để khi khôi phục có chính sách đúng.

## Cập nhật 2026-07-14 - Phân biệt biến thể cùng màu theo cấu hình

- Khi dựng `attributes/options`, frontend bổ sung các giá trị dung lượng, RAM và cấu hình đang nằm ở trường tương thích cũ nếu chúng chưa được đại diện bởi thông số biến thể đã chọn.
- Khóa chống trùng biến thể ở backend kết hợp `attributes` với các trường `colorName`, `storage`, `ram`, `configuration` còn thiếu, thay vì bỏ qua toàn bộ trường tương thích khi đã có thuộc tính màu.
- Cho phép nhiều biến thể cùng màu nếu khác dung lượng, RAM hoặc cấu hình; giá bán không được dùng làm khóa phân biệt biến thể.

## Cập nhật 2026-07-14 - Giá trị cấu hình danh mục chỉ dùng để gợi ý

- Danh sách `options` trong `categories.spec_fields` chỉ còn dùng để gợi ý nhập nhanh trên form sản phẩm và biến thể; sản phẩm được phép lưu giá trị thực tế khác danh sách này.
- Backend vẫn kiểm tra các thông số được đánh dấu `required` và định dạng số của trường `number`, kể cả khi thông số nằm ở từng biến thể.
- Loại bỏ kiểm tra thành viên trong danh sách gợi ý khỏi `validate_product_specifications`, tránh báo lỗi sai khi cấu hình thực tế của sản phẩm chưa có trong danh mục.

## Cập nhật 2026-07-14 - Truy xuất phiên bản và tồn khả dụng cho chatbot

- Snapshot catalog AI bổ sung `availableStock` và `stockUpdatedAt` cho từng biến thể active.
- Bộ lọc trạng thái dùng `LOWER(status) = 'active'` để tương thích đúng giá trị đang lưu trong PostgreSQL.
- Chatbot lọc biến thể đồng thời theo màu, dung lượng, RAM hoặc SKU; khi đã yêu cầu biến thể cụ thể, câu trả lời không dùng tổng tồn của sản phẩm.
- Ngữ cảnh trang tiếp tục giới hạn truy vấn vào đúng `id`/`slug` sản phẩm trước khi dựng câu trả lời tồn kho.
- Thay đổi chỉ đọc dữ liệu sản phẩm và tồn hiện hành; không sửa giá, biến thể, reservation hoặc trạng thái bán.

## Cập nhật 2026-07-14 - Truy xuất giá và khuyến mãi cho chatbot

- Truy vấn AI xác định sản phẩm đang giảm bằng dữ liệu live `salePrice < price`; hỗ trợ lọc theo ngưỡng phần trăm, xếp mức giảm lớn nhất và trả nhiều kết quả khi khách yêu cầu ba sản phẩm rẻ nhất.
- Câu trả lời giá nêu riêng giá bán hiện hành, giá gốc, số tiền giảm và tỷ lệ giảm; không suy ra voucher cá nhân từ mô tả khuyến mãi sản phẩm.
- Bộ phân tích ngân sách bỏ giá trị phần trăm và khoản tăng ngân sách tương đối trước khi lọc catalog, tránh hiểu `20%` thành 20 triệu hoặc “thêm 1 triệu” thành mức giá sản phẩm 1 triệu.
- Thay đổi chỉ đọc snapshot sản phẩm active; không sửa giá, flash sale, voucher, tồn kho hoặc cấu hình bán hàng.

## Cập nhật 2026-07-14 - Dùng ngữ cảnh trang sản phẩm cho câu hỏi thông số AI

- Widget chatbot gửi `page_context.product_id` khi người dùng đang ở `/product/:id`.
- Truy xuất catalog AI đối chiếu giá trị này với cả `products.id` và `products.slug`, sau đó ưu tiên đúng một sản phẩm trước khi dựng ngữ cảnh trả lời câu hỏi rút gọn như “Sản phẩm này có bao nhiêu RAM?”.
- Thay đổi chỉ đọc dữ liệu sản phẩm active hiện hành; không sửa trạng thái, giá, tồn kho, biến thể hoặc nghiệp vụ quản trị sản phẩm.

## Cập nhật 2026-07-14 - Mở rộng trường tìm kiếm catalog cho chatbot

- Văn bản tìm kiếm sản phẩm của chatbot gồm thêm `slug` và dữ liệu biến thể active; nhờ đó màu sắc, dung lượng và SKU trong biến thể có thể tham gia xếp hạng kết quả.
- Không thay đổi API quản trị, trạng thái sản phẩm hoặc cách tính tồn; đây chỉ là phần hydrate/tìm kiếm đọc dữ liệu cho trợ lý AI.

## Cập nhật 2026-07-14 - Chuẩn hóa tên thương hiệu trên trang thương hiệu

- Metadata tiêu đề và mô tả của trang thương hiệu dùng thống nhất `ElectroMart Vietnam`.
- Thay đổi chỉ liên quan nội dung hiển thị và SEO; không thay đổi truy vấn, bộ lọc hoặc dữ liệu sản phẩm.

## Cập nhật 2026-07-13 - Hydrate dữ liệu sản phẩm live cho chatbot V2

- Truy vấn AI chỉ lấy sản phẩm active, chưa xóa, không bị ẩn theo danh mục/thương hiệu và trả biến thể active chưa xóa.
- Tồn công khai được tính từ `inventory_levels` theo `on_hand - reserved - safety_stock`, gộp cả tồn biến thể; không trả vị trí kho, IMEI hoặc serial.
- Snapshot sản phẩm cho chatbot có giá hiện hành, khuyến mãi, thời hạn/chính sách bảo hành và timestamp để verifier đối chiếu trước khi dựng card.
- Nhánh hàng cũ tái sử dụng service storefront, chỉ lấy listing đang công khai và thiết bị `READY_FOR_SALE`; card điều hướng về `/used-products/{slug}` thay vì trang sản phẩm mới.
- Semantic index chỉ tìm ứng viên; giá, tồn và trạng thái bán trong câu trả lời vẫn lấy từ PostgreSQL ở lượt hỏi hiện tại.

## Cập nhật 2026-07-13 - Semantic catalog bằng Gemini Embedding 2 và PGVector

- Dữ liệu sản phẩm đã xuất thành 104 tài liệu catalog được backfill sang `gemini-embedding-2` và cột PGVector 768 chiều.
- Chatbot ưu tiên semantic search từ PostgreSQL/PGVector, nhưng dữ liệu giá, tồn kho và trạng thái bán vẫn phải được lấy lại từ bảng nghiệp vụ tại thời điểm trả lời; vector không được dùng làm nguồn sự thật cho dữ liệu động.
- Pipeline giữ fallback JSONB/JSON cache/sparse index khi PGVector gặp sự cố và bỏ qua snapshot chưa hoàn chỉnh để tránh tư vấn từ catalog bị thiếu.

## Cập nhật 2026-07-13 - Xếp hạng sản phẩm cho chatbot

- Truy xuất sản phẩm AI lọc đúng danh mục điện thoại/laptop trước khi xếp hạng.
- Câu hỏi đắt nhất/rẻ nhất so sánh theo giá bán hiệu lực và chỉ trả một sản phẩm, giúp thẻ gợi ý khớp với câu trả lời của chatbot.

## Cập nhật 2026-07-13 - Catalog hàng cũ cho POS

- API danh sách bài đăng quản trị trả thêm `deviceStatus`, `productId`, `categoryId`, `subcategoryId` và `brandId` để POS kiểm tra máy còn sẵn sàng và cung cấp đúng ngữ cảnh voucher.
- POS chỉ hiển thị bài `PUBLISHED` có thiết bị `READY_FOR_SALE`; mỗi thẻ tương ứng một máy duy nhất và dùng giá đã duyệt từ backend.
- Hàng cũ được tách khỏi tồn catalog, biến thể, FIFO và chương trình mua kèm; vòng đời tồn kho dùng trạng thái riêng của `used_devices` và `used_device_listings`.
- Khi hoàn tiền sau bán, thiết bị về `RETURNED_QC` và chỉ được đăng bán lại sau bước QC; không tự cộng vào kho hàng mới hoặc tự chuyển bài đăng về `PUBLISHED`.

## Cập nhật 2026-07-11 - Nguồn hàng cũ từ hoàn/đổi

- Hàng hoàn/đổi được QC chọn chuyển sang hàng cũ sẽ tự tạo intake `RETURNED_USED`, giữ truy vết đơn hàng, hồ sơ hậu mãi và IMEI/serial.
- Luồng này không tạo giao dịch thu mua mới và không nhập trùng vào kho hàng mới.

## Cập nhật 2026-07-11 - Giá bán, bảo hành hãng và duyệt hàng cũ

- Bổ sung API cập nhật giá bán độc lập cho thiết bị cũ; giá mới phải cao hơn tổng giá thu mua và chi phí sửa chữa, đồng thời lưu lịch sử giá và sự kiện thay đổi.
- Nếu cập nhật giá khi bài đang bán, bài tự chuyển về chờ duyệt và thiết bị chuyển sang `LISTING_REVIEW`.
- Bổ sung thông tin bảo hành chính hãng gồm đơn vị bảo hành, ngày kích hoạt và tổng thời hạn; ngày hết hạn và số tháng còn lại được tính động theo ngày hiện tại, làm tròn lên khi còn ngày lẻ.
- Giao diện hàng cũ có thao tác cập nhật giá, khai báo bảo hành hãng, yêu cầu chỉnh sửa và hiển thị thời gian bảo hành còn lại.
- `SUPER_ADMIN` được xem là có toàn quyền ở cả frontend và backend, không phụ thuộc danh sách quyền bị thiếu hoặc cache cũ; chỉ cấp này được phép tự tạo rồi tự duyệt bài đăng.
- Giá mới được ghi là `PROPOSED`; chỉ khi bài đăng được duyệt `PUBLISHED` thì giá gần nhất mới chuyển thành `APPROVED`, các giá đề xuất/đã duyệt cũ chuyển thành `SUPERSEDED`.
- Ngày kích hoạt bảo hành hãng trong tương lai không bị chặn cứng; giao diện cảnh báo và việc lưu bài luôn đưa nội dung về nháp để Super Admin duyệt lại.
- Storefront hiển thị riêng bảo hành cửa hàng và bảo hành chính hãng còn lại; thao tác yêu cầu chỉnh sửa bắt buộc có lý do ở cả frontend và backend.

## Cập nhật 2026-07-10 - Hardening sản phẩm cũ

- Storefront hàng cũ hoạt động với bộ lọc rỗng; nguồn catalog dùng cho intake được lọc theo trạng thái sản phẩm, thương hiệu và biến thể hợp lệ.
- Sửa chữa, QC lại, biên lợi nhuận và trạng thái hậu mãi của `used_devices` được siết theo state machine và có lịch sử sự kiện.
- Nội dung chính sách trên trang chi tiết hàng cũ không còn hard-code cam kết 30 ngày trái với cấu hình bảo hành của từng bài đăng.

## Cập nhật 2026-07-10 - Đồng bộ logic bảng xếp hạng theo kỳ

- Tiêu chí yêu thích sắp xếp theo `periodLikeCount` và hiển thị lượt thích ròng `LIKE - UNLIKE` trong kỳ.
- Tiêu chí đánh giá sắp xếp và hiển thị `periodRating`; phần trăm xu hướng so với `previousPeriodRating` thay vì biến điểm số thành phần trăm trên thang 5.
- Lịch sử bảng xếp hạng bổ sung lượt thích ròng và điểm đánh giá trung bình theo từng bucket thời gian để biểu đồ không dùng dữ liệu phẳng giả.
- Loại sản phẩm có chỉ số được chọn bằng `0` khỏi bảng; nếu kỳ hiện tại chưa có dữ liệu, frontend hiển thị trạng thái rỗng thay vì xếp hạng tùy ý bằng tiêu chí phá hòa.
- Khi toàn bộ kỳ được chọn không có hoạt động cho tiêu chí hiện tại, API tự lùi theo chuỗi `24h → 7d → 30d → 1y`, trả `rankingPeriod` và `isPeriodFallback`; frontend thông báo rõ kỳ thực tế đang dùng.
- Khi dùng kỳ fallback, lịch sử của kỳ gốc được bỏ trống để không trình bày biểu đồ sai khoảng thời gian.

## Cập nhật 2026-07-10 - Đồng bộ lượt xem và lượt thích từ thư viện ảnh

- Khi mở ảnh trong `/images`, frontend gửi heartbeat sản phẩm với nguồn `image_gallery`; sự kiện vẫn dùng cơ chế xác thực và chống đếm trùng của lượt xem sản phẩm.
- API heartbeat và API bật/tắt yêu thích trả thêm `viewCount` và `favoriteCount` thực tế sau khi thao tác thành công.
- `favoriteCount` được đếm từ `user_favorites` đang hoạt động; `viewCount` được đếm từ `product_view_events`, giúp giao diện thư viện ảnh cập nhật ngay mà không dùng số giả.
- Truy vấn chi tiết sản phẩm cũng chỉ đếm các dòng `user_favorites.is_active = TRUE`, tránh lượt thích đã hủy vẫn còn trong tổng số sau khi tải lại trang.
- Danh sách và chi tiết sản phẩm trả `viewCount` tổng hợp từ `product_view_events`; phản hồi heartbeat cũng trả số hiện tại khi sự kiện bị chống đếm trùng.
- `product_row` và `build_product_image_collection` giữ lại `viewCount`/`favoriteCount` ở cả sản phẩm, thẻ ảnh và từng ảnh con; tránh truy vấn có số liệu nhưng lớp ánh xạ response làm mất trường.

## Cập nhật 2026-07-10 (Bổ sung) - Hàng cũ không bắt buộc có sản phẩm catalog

- Hồ sơ `USER_BUYBACK` có thể nhập `externalProductName` thay cho `productId`; `used_devices.product_id` được phép rỗng và lưu tên model ngoài catalog riêng.
- Storefront và checkout vẫn bán đúng thiết bị bằng `used_device_id`; nếu thiếu sản phẩm catalog thì không có category/brand targeting, nhưng tên, giá, IMEI, QC, bảo hành và vòng đời đơn hàng vẫn hoạt động.
- Không tự tạo sản phẩm catalog giả cho model ngoài danh mục, giữ module sản phẩm mới và module hàng cũ tách biệt.

## Cập nhật 2026-07-10 - Siết điều kiện đăng bán và đồng bộ trạng thái hàng cũ

- QC hàng cũ đạt phải có xác minh IMEI, trạng thái khóa tài khoản, xóa dữ liệu và tối thiểu 3 ảnh thực tế trước khi được định giá để đăng bán.
- Giá bán đề xuất không chỉ cao hơn giá thu mua mà phải cao hơn tổng giá thu mua và chi phí sửa dự kiến.
- Khi bán thành công, `used_device_listings.status` chuyển sang `SOLD` cùng `used_devices.status`, tránh bài đăng đã bán vẫn hiện `PUBLISHED` trong màn quản trị.

## Cập nhật 2026-07-08 (Bổ sung 11) - Cộng thời gian bảo hành từ dịch vụ đi kèm cho dữ liệu cũ

- Checkout mới đã lưu `order_items.warranty_months_snapshot` bằng bảo hành gốc cộng tổng `duration_months` của các dịch vụ đi kèm được mua.
- Bổ sung helper SQL dùng chung `warranty_snapshot.py` để các read-model đơn hàng/hậu mãi ưu tiên snapshot; nếu snapshot thiếu thì fallback về bảo hành gốc sản phẩm/hàng cũ và cộng thêm tổng tháng trong `order_items.attached_services`.
- API đơn hàng `GET /orders`, `GET /orders/{id}` và `GET /me/orders` nay trả `items[].warrantyMonthsSnapshot` theo giá trị hiệu lực cho dữ liệu cũ, đồng thời trả thêm `warrantySnapshotMissing` và `attachedServices` để đối soát.
- Luồng tạo yêu cầu bảo hành hậu mãi dùng cùng giá trị hiệu lực, tránh bỏ sót gói gia hạn bảo hành đã mua trong các đơn cũ/manual chưa có snapshot.

## Cập nhật 2026-07-08 (Bổ sung 10) - Kỳ vọng test đúng cho hàng cũ

- Xác nhận module hàng cũ không cung cấp API xóa cứng thiết bị cũ. Luồng đúng là chuyển thiết bị sang `RETIRED` hoặc chuyển bài đăng sang `HIDDEN` để bảo toàn lịch sử kiểm định, kế toán và WMS.
- Kỳ vọng test UP-008 cần đổi sang: thao tác loại bỏ khỏi bán hàng phải làm thiết bị/bài đăng không còn hiển thị trên storefront, không kỳ vọng bản ghi bị xóa khỏi hệ thống.
- Xác nhận IMEI của hồ sơ hàng cũ bắt buộc chuẩn hóa về đúng 15 chữ số; frontend chỉ cho nhập số và giới hạn 15 ký tự, backend tiếp tục chặn nếu sau chuẩn hóa không đủ 15 chữ số.
- Bổ sung test manual cho `COMPARISON_NOTE_REQUIRED`: nếu giá bán hàng cũ lớn hơn hoặc bằng giá máy mới tham chiếu thì bắt buộc nhập ghi chú so sánh giá.
- Bổ sung test manual storefront: API chi tiết hàng cũ chỉ trả `maskedImei`, không trả IMEI gốc; UI phải hiển thị dạng đã che số giữa.

## Cập nhật 2026-07-08 (Bổ sung 9) - Hoàn thiện thao tác media sản phẩm

- Bổ sung kéo thả đổi thứ tự ảnh trong `MediaPreview`; form sản phẩm cập nhật trực tiếp thứ tự mảng `images`, nên thứ tự mới được lưu theo payload sản phẩm hiện có.
- Bổ sung thao tác đặt ảnh trong bộ ảnh chung làm ảnh đại diện bằng cách gán URL được chọn vào `imageUrl`; ảnh vẫn có thể giữ trong gallery.
- Bổ sung giới hạn thời lượng video upload tối đa 5 phút. Frontend đọc metadata video trước khi xin URL upload; backend `admin_uploads.py` yêu cầu `durationSeconds` khi cấp URL upload video và kiểm lại header duration với upload local.
- Xác nhận các test manual nên bổ sung: chặn URL media ngoại lai (`MEDIA_EXTERNAL_NOT_ALLOWED`) và kiểm tra asset claiming/garbage collection của file `/uploads/` không còn được gắn với sản phẩm.

## Cập nhật 2026-07-08 (Bổ sung 8) - Khóa tồn kho khỏi form Sản phẩm/Biến thể

- Xác nhận bảng biến thể trong form sản phẩm không còn cột hoặc ô nhập số lượng tồn kho; phần mô tả UI cũng bỏ nhắc tồn kho để tránh test case hiểu nhầm.
- Frontend không còn khởi tạo, validate hoặc gửi `stockQuantity` trong payload biến thể của form sản phẩm.
- Backend `upsert_product_variants` luôn khởi tạo biến thể catalog mới với `stock_quantity = 0`, bỏ đường nhận số tồn từ payload hoặc fallback từ tồn sản phẩm cha.
- Khi tạo sản phẩm mới qua catalog API, `products.stock_quantity` cũng khởi tạo bằng `0`; tồn kho thực tế phải đi qua module Nhập kho/Tồn kho.

## Cập nhật 2026-07-08 (Bổ sung 7) - Không bắt thông số chung khi trường bắt buộc đã dùng làm biến thể

- Sửa backend validation để trường thông số bắt buộc có `variant=true` như RAM được xem là hợp lệ khi admin đã chọn trường đó làm thuộc tính biến thể và nhập giá trị ở từng biến thể.
- `validate_product_specifications` nay đọc giá trị biến thể từ cả `variant.specs`, `variant.attributes` theo nhãn hiển thị như `RAM`, và field trực tiếp như `variant.ram`, tránh báo sai `Thông số 'RAM' là bắt buộc` khi dữ liệu đang nằm ở biến thể.
- Khi payload chỉ có một biến thể nhưng có `_variantSpecKeys`, backend không tự xóa danh sách biến thể trước bước validate/lưu nữa; quy tắc xóa biến thể đơn vẫn giữ cho sản phẩm không cấu hình thuộc tính biến thể.

## Cập nhật 2026-07-08 (Bổ sung 6) - Chuẩn hóa sản phẩm theo thông số danh mục có đơn vị

- Thêm script `backend/scripts/normalize_products_to_category_specs.py` để chuẩn hóa `products.specifications` và `product_variants.specs/attributes` theo `categories.spec_fields`.
- Script hỗ trợ dry-run mặc định và chỉ ghi DB khi chạy với `--apply`; đã áp dụng trên DB local: quét 103 sản phẩm, cập nhật 93 sản phẩm và 325 biến thể, sau đó dry-run lại còn 0 thay đổi và 0 cảnh báo bắt buộc.
- Đồng bộ `_variantSpecKeys` để RAM/ROM và các thông số biến thể được nhận diện đúng khi mở lại form sản phẩm.
- Bổ sung override dữ liệu cho các SKU thiếu RAM bắt buộc trong dữ liệu cũ: `SAM-ZFLIP5`, `VIV-V30PRO`, `XIM-RN13P5G`.
- Cập nhật backend validation trong `product_helper_service.py` để giá trị cũ có sẵn đơn vị như `8GB` vẫn hợp lệ khi danh mục cấu hình `options` dạng `8, 16, 32` và `unit` là `GB`.
- Cập nhật form sản phẩm và form biến thể để khi chọn gợi ý của trường có `unit`, input nhận giá trị đã kèm đuôi đơn vị như `8 GB`, `5000 mAh`; các option đã tự chứa đơn vị như `512GB SSD` không bị nối thêm đuôi lần nữa.
- Bổ sung chip gợi ý trực tiếp dưới từng ô thông số biến thể để admin có thể bấm chọn giá trị có sẵn kèm đuôi, hoặc nhập tay nếu cấu hình thực tế khác danh sách gợi ý.
- Frontend/backend validation cho thông số kiểu số nay bỏ phần đuôi `unit` trước khi kiểm tra số, tránh chặn các giá trị như `120 Hz` hoặc `5000 mAh`.

## Cập nhật 2026-07-08 (Bổ sung 5) - Kiểm soát nhập liệu Thông số kỹ thuật theo Danh mục cho Sản phẩm

- **Gợi ý chọn nhanh và đơn vị (Frontend)**:
  - Cập nhật form thông số sản phẩm (`ProductFormSection.tsx`) và biến thể (`ProductVariantsSection.tsx`): hiển thị nhãn đi kèm đơn vị cấu hình từ danh mục, đổi loại input theo kiểu số/chữ, và hiển thị các badge/chips gợi ý phía dưới ô nhập để bấm chọn nhanh.
  - Sử dụng thẻ HTML5 `<datalist>` để cung cấp gợi ý chọn tự động hoàn thành trong ô nhập biến thể nhằm tối ưu không gian bảng.
- **Frontend Validation**: Bổ sung kiểm soát dữ liệu trong `validateProductForm` (`useAdminProductsLogic.ts`) kiểm tra các trường bắt buộc (`required`) và kiểm tra số hợp lệ đối với trường kiểu `number`.
- **Backend Validation**:
  - Thêm `get_merged_spec_fields` và `validate_product_specifications` trong `product_helper_service.py` hỗ trợ lấy danh sách thông số kế thừa và chạy kiểm soát bắt buộc, kiểu số, hoặc danh sách tùy chọn cho cả thông số sản phẩm chính và biến thể.
  - Gọi kiểm soát trong `create_product` và `update_product` ở `product_service.py`.
- **Hiển thị Storefront**: Tự động thêm đuôi đơn vị vào giá trị hiển thị trên trang chi tiết sản phẩm nếu giá trị hiện tại chưa có đuôi đó.

## Cập nhật 2026-07-08 (Bổ sung 4) - Gỡ bỏ ràng buộc chéo Thương hiệu - Danh mục và Hỗ trợ sản phẩm gốc không biến thể
- **Gỡ bỏ ràng buộc chéo Thương hiệu - Danh mục**: Loại bỏ kiểm tra chéo điều kiện kết hợp thương hiệu và danh mục qua bảng `brand_categories` trong hàm `resolve_catalog_labels` (ở [product_helper_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/product_helper_service.py)) để cho phép tạo sản phẩm với cặp thương hiệu và danh mục mới tạo chưa liên kết.
- **Động hóa liên kết trên Mega Menu**: Cập nhật hàm `list_active_brands` (ở [catalog_product_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/catalog_product_repo.py)) để tự động gom nhóm `categoryIds` của thương hiệu dựa theo các sản phẩm thực tế có trạng thái `ACTIVE` của thương hiệu đó, thay vì truy cập qua bảng liên kết trung gian `brand_categories`. Điều này giúp thương hiệu tự động xuất hiện ở danh mục tương ứng khi có sản phẩm được đăng bán.
- **Hỗ trợ sản phẩm gốc không biến thể**:
  - Cập nhật `create_product` và `update_product` (ở [product_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/product_service.py)): Nếu số lượng biến thể gửi lên ít hơn 2, hệ thống sẽ xóa sạch danh sách `variants` và `options` nhận vào, cho phép lưu trữ sản phẩm gốc thuần túy mà không tạo bản ghi biến thể nào trong bảng `product_variants`. Nếu có từ 2 biến thể trở lên, hệ thống sẽ yêu cầu thiết lập 1 biến thể mặc định như cũ.
  - Cập nhật logic duyệt Revision `merge_revision_variants` (ở [product_approval_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/product_approval_repo.py)): Chỉ thực hiện kiểm tra biến thể mặc định và chặn áp dụng revision khi không có biến thể hoạt động nếu sản phẩm gốc và bản chỉnh sửa (revision draft) thực sự có định nghĩa biến thể.
  - Cập nhật import CSV `insert_imported_product` (ở [import_jobs.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/product/import_jobs.py)): Loại bỏ việc tự động sinh một biến thể mặc định cho sản phẩm được import, giúp chúng hoạt động như sản phẩm gốc không biến thể.
  - Vô hiệu hóa nhập kho trực tiếp trên UI (ở [ProductVariantsSection.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-products/components/products/ProductVariantsSection.tsx)): Xóa bỏ hoàn toàn cột số lượng tồn kho (`stockQuantity`) trong bảng biến thể sản phẩm và loại bỏ nút "Áp dụng tồn kho" để buộc số lượng tồn kho chỉ được quản lý và cập nhật thông qua quy trình nhập kho (Purchase Receipt / Inventory Receiving).

## Cập nhật 2026-07-08 (Runtime) - Khôi phục khởi động backend khi duyệt Revision
- Sửa đoạn `revision_snapshot` trong `transition_product_status_data` bị ghép lẫn với câu `UPDATE products parent`, gây lỗi cú pháp `SyntaxError: '(' was never closed` khi khởi động backend.
- Khôi phục câu `UPDATE products parent ... FROM products revision` để áp dụng dữ liệu revision lên sản phẩm cha, có cập nhật `price` và `sale_price` nhưng không ghi đè `stock_quantity` thực tế.

## Cập nhật 2026-07-08 (Bổ sung 3) - Sửa lỗi cú pháp merge revision, Ràng buộc xóa biến thể cuối cùng, và tự động map Category/Brand khi import CSV
- **Khôi phục logic merge_revision_variants**: Khắc phục triệt để lỗi cú pháp dở dang làm sập runtime.
- **Tự động map Category/Brand khi import CSV**: Thêm tra cứu `category_id` và `brand_id` trong database theo tên category/brand lấy từ CSV, tránh sản phẩm mồ côi.
- **Ràng buộc xóa biến thể**: Chặn xóa biến thể đang hoạt động duy nhất của sản phẩm.
- **Rollback khi đổi SKU default bị trùng**: Kiểm tra kết quả đổi SKU default của sản phẩm cha khi xóa biến thể default cũ, ném lỗi rollback nếu trùng lặp.
- **Chặn tự mua kèm**: Chặn sản phẩm tự liên kết phụ kiện mua kèm chính nó.

## Cập nhật 2026-07-08 (Bổ sung 2) - Khắc phục lỗi logic tồn kho khi duyệt Revision, Ràng buộc chéo Brand-Category, và Import CSV
- **Không đè tồn kho thực tế của sản phẩm đơn lẻ**: Loại bỏ việc gán `stock_quantity = revision.stock_quantity` khi duyệt Revision tại `transition_product_status_data` (ở `product_approval_repo.py`) để tránh ghi đè tồn kho thực tế đã phát sinh.
- **Khởi tạo đúng tồn kho = 0 cho variant mới**: Khi duyệt Revision tạo thêm biến thể mới tại `merge_revision_variants` (ở `product_approval_repo.py`), đặt cứng tồn kho mặc định bằng 0 để tuân thủ quy tắc nhập kho qua chứng từ.
- **Ràng buộc chéo Brand - Category**: Thêm validation trong `resolve_catalog_labels` (ở `product_helper_service.py`) để kiểm tra chéo xem Brand được chọn có thuộc danh mục (Category) hay không (qua bảng `brand_categories`).
- **Cascade dọn dẹp tồn kho trống cho sản phẩm đơn lẻ**: Sửa lỗi FK constraint khi xóa sản phẩm tại `deactivate_product_data` (ở `product_approval_repo.py`) bằng cách xóa cả các dòng tồn kho trống trong `inventory_levels` liên kết trực tiếp qua `product_id`.
- **Tự động tạo variant mặc định khi import CSV**: Thêm logic tự động insert một variant mặc định vào `product_variants` (với `stock_quantity = 0` và SKU lấy từ sản phẩm cha) sau khi insert product import thành công tại `insert_imported_product` (ở `import_jobs.py`), giải quyết triệt để lỗi không checkout được do thiếu biến thể.

## Cập nhật 2026-07-08 - Khắc phục các lỗi logic duyệt Revision, ràng buộc chéo Danh mục phụ và Bulk Actions
- **Cập nhật thiếu giá và tồn của sản phẩm đơn lẻ khi duyệt Revision**: Bổ sung `price`, `sale_price` và `stock_quantity` vào câu lệnh UPDATE từ revision sang sản phẩm cha tại `transition_product_status_data` (ở `product_approval_repo.py`), sửa lỗi bỏ sót thông tin cho sản phẩm đơn lẻ.
- **Ràng buộc chéo Subcategory**: Nâng cấp hàm `resolve_catalog_labels` (ở `product_helper_service.py`) kiểm tra xem `subcategoryId` có tồn tại và có thuộc về danh mục chính `categoryId` hay không để tránh sai lệch phân cấp cây danh mục.
- **Cascade dọn dẹp các Revision nháp khác khi duyệt**: Bổ sung xóa các liên kết của các bản revision nháp khác (combo, phụ kiện kèm, dịch vụ đi kèm) và giải phóng `media_assets` liên kết của chúng trước khi DELETE cứng trong `transition_product_status_data` (ở `product_approval_repo.py`) nhằm ngăn chặn lỗi vi phạm khoá ngoại (FK constraint violation).
- **Cô lập Transaction cho Bulk Actions**: Sửa đổi `bulk_approve_products` và `product_bulk_action` (ở `product_approval_service.py`) sử dụng nested transaction (`session.begin_nested()`) cô lập lỗi cho từng sản phẩm và gọi các repository helper data thuần túy (`_data`), tránh lỗi poisoned transaction làm sập toàn bộ luồng hàng loạt.

- **Validate trùng lặp SKU ở Schema (Product Payload validation)**:
  - Bổ sung kiểm tra trùng lặp SKU giữa các biến thể trong cùng một sản phẩm ngay tại tầng schema đầu vào `ProductPayload` (sử dụng `@model_validator(mode="after")` của Pydantic), trả về mã lỗi `422 Unprocessable Entity` kèm thông báo tiếng Việt chi tiết nếu có cấu hình trùng SKU.
  - Ngăn chặn request lỗi từ giai đoạn parse payload trước khi xuống database xử lý, giúp tăng tính an toàn và giảm tải cho DB.
  - Test case thực hiện đăng nhập tài khoản Super Admin, chuyển tới tab quản lý sản phẩm, mở form tạo sản phẩm mới, điền các thông tin hợp lệ, tạo 2 biến thể có cùng SKU và bấm lưu. Xác minh UI chặn submit và hiển thị đúng hộp thoại alert chứa thông báo lỗi tiếng Việt `"SKU biến thể không được trùng trong cùng sản phẩm."`.
- **Cấu hình CORS & Cải thiện Test Server**:
  - Bảo đảm endpoint `/health` và tất cả các include_router hoạt động ổn định.

## Cập nhật 2026-07-07 (Bổ sung 2) - Củng cố Bảo mật và Maker-Checker cho Hàng cũ (Used Products)
- **Ràng buộc thông tin người bán**: Bổ sung validation trong `create_intake` tại [used_product_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/used_product_service.py) bắt buộc nhập họ tên và số điện thoại người bán nếu không chọn tài khoản thành viên liên kết, ngăn chặn hồ sơ ẩn danh.
- **Ràng buộc chênh lệch giá đề xuất**: Trong `inspect_intake`, kiểm tra nếu kết quả thẩm định là đạt (`APPRAISED`) thì giá bán đề xuất phải lớn hơn giá thu mua đề xuất (`proposedSalePrice > proposedAcquisitionPrice`) để tránh lỗ hoặc thiếu nhất quán tài chính.
- **Cơ chế khóa dòng chống Race Condition**: Trong `update_listing_status`, bổ sung truy vấn `SELECT ... FOR UPDATE` khóa dòng trên bảng `used_devices` của thiết bị tương ứng trước khi cập nhật. Đồng thời kiểm tra nếu thiết bị đã được bán, được đặt trước hoặc hư hỏng (`SOLD`, `RESERVED`, `RETIRED`, `REPAIRING`), chặn thay đổi trạng thái bài đăng.
- **Chính sách Maker-Checker (Chặn tự phê duyệt)**:
  - Chặn nhân viên thường (ví dụ: `STAFF_ADMIN`) tự duyệt hồ sơ thu mua (`ACCEPTED`) hoặc tự xuất bản bài đăng (`PUBLISHED`) do chính họ tạo hoặc thẩm định.
  - Đối với tài khoản có vai trò tối cao `SUPER_ADMIN`, hệ thống hỗ trợ bypass chính sách Maker-Checker này để cho phép tự phê duyệt khi cần thiết.

## Cập nhật 2026-07-07 - Củng cố Rollback, Concurrency và Ràng buộc chéo cho Sản phẩm

- **Cascade tắt biến thể khi lưu trữ sản phẩm (Archive)**: Cập nhật hàm `transition_product_status_data` gọi `unpublish_product_dependents` để tự động tắt tất cả biến thể (`is_active = FALSE`) và ẩn các listings/thiết bị cũ tương ứng khi sản phẩm chuyển trạng thái sang `ARCHIVED` hoặc `INACTIVE`.
- **Đồng bộ hóa vô hiệu hóa biến thể khi xóa sản phẩm có đơn/review**: Cập nhật hàm `deactivate_product_data` gọi `unpublish_product_dependents` để đảm bảo các biến thể của sản phẩm bị ẩn cũng chuyển sang `is_active = FALSE`, tránh tình trạng sản phẩm cha ngưng bán nhưng biến thể vẫn hoạt động.
- **Ràng buộc chặt chẽ liên kết sản phẩm mua kèm và dịch vụ đi kèm**: Cập nhật hàm `sync_product_relations` trong `product_service.py` để kiểm tra sự tồn tại và trạng thái hoạt động của sản phẩm mua kèm (`status = 'ACTIVE'`) và dịch vụ đi kèm (`is_active = TRUE`), ném ngoại lệ cụ thể thay vì bỏ qua âm thầm khi sai thông tin hoặc sai định dạng.
- **Xử lý lỗi cập nhật SKU trùng lặp**: Cập nhật `update_product_sku` trả về `rowcount` và ném lỗi `HTTPException(400)` ở service `upsert_product_variants` nếu cập nhật SKU theo biến thể default thất bại do trùng lặp SKU của sản phẩm khác.
- **Bảo mật và toàn vẹn Media biến thể**: Cập nhật `create_product` và `update_product` trong `product_service.py` để thu thập, validate và claim toàn bộ hình ảnh biến thể (`variant.imageUrl` và `variant.images`), ngăn chặn bypass đăng ký Media Assets.
- **Khắc phục lỗi poisoned transaction khi import CSV**: Cập nhật `process_product_import_job` sử dụng `session.begin_nested()` để cô lập lỗi cho từng hàng khi import hàng loạt, giúp tiến trình không bị sập nửa chừng khi gặp lỗi DB đơn lẻ.
- **Bảo đảm tính nguyên tử của Variant Delete**: Bổ sung `try ... except ... rollback` cho hàm `delete_product_variant` trong `product_variant_service.py` để tránh treo DB lock hoặc dữ liệu default bị mâu thuẫn khi cập nhật default variant thất bại.
- **Giải phóng tranh chấp Media khi Nhân bản Sản phẩm**: Trong `duplicate_product_record` (ở `duplicate.py`), đặt `image_url`, `images` và `video_url` về mặc định (`NULL` và `'[]'::jsonb`) khi sao chép. Điều này ngăn chặn lỗi xung đột `MEDIA_ASSET_CLAIM_FAILED` (409) do ràng buộc `UNIQUE` trên cột `public_url` của bảng `media_assets` khi thực hiện chỉnh sửa sản phẩm sao chép.
- **Ràng buộc chéo thiết bị cũ khi lưu trữ sản phẩm**: Cập nhật hàm `update_product` trong `product_service.py` ẩn thiết bị cũ tương ứng (`used_device_listings` chuyển sang `HIDDEN`) khi sản phẩm gốc chuyển sang trạng thái `ARCHIVED`.
- **Ràng buộc chéo thiết bị cũ khi ẩn Thương hiệu**: Cập nhật `brand_service.py` gọi `used_product_repo.hide_listings_by_products` để ẩn toàn bộ thiết bị cũ thuộc thương hiệu khi thương hiệu bị vô hiệu hóa (cả đơn lẻ, bulk update và background job).

## Cập nhật 2026-07-07 - Khắc phục lỗ hổng bypass Asset Registry và Transaction Boundaries của Biến thể

- **Chặn Media ngoại lai (Registry Enforcement)**:
  - Hàm `validate_optimized_media` và `media_repo.assert_all_product_media_claimed` ngăn chặn tất cả các URL hình ảnh/video sản phẩm bên ngoài mà không được upload hoặc đăng ký thông qua hệ thống `media_assets`.
  - Chỉ chấp nhận các asset tĩnh bắt đầu bằng `/images/` hoặc asset đã upload chứa `/uploads/` và thuộc quyền sở hữu của sản phẩm. Các URL không hợp lệ sẽ trả về lỗi `400 MEDIA_EXTERNAL_NOT_ALLOWED`.
- **Độc lập ranh giới Transaction của Biến thể**:
  - Gỡ bỏ lệnh `session.rollback()` khỏi hàm helper `upsert_product_variants` trong `product_variant_service.py`. Trách nhiệm rollback/commit transaction lớn hiện tại thuộc về caller chính là `product_service.create_product` hoặc `update_product`.

## Cập nhật 2026-07-07 - Khắc phục các lỗ hổng logic & tối ưu luồng Sản phẩm

- **Gỡ bỏ đường vòng tạo Sản phẩm**:
  - Chuyển đổi route catalog public `POST /api/catalog/products` sang sử dụng trực tiếp schema `ProductPayload` và gọi service chính `product_service.create_product`.
  - Giúp đồng bộ hóa mọi bước kiểm tra bảo mật, kiểm tra categories not migrating, audit logs, ltree categories, v.v.

- **Atomic Media Asset Claim**:
  - Thiết kế và triển khai hàm `media_repo.claim_media_assets` thực hiện cập nhật sở hữu media nguyên tử thông qua transaction và mệnh đề `RETURNING`.
  - Loại bỏ hoàn toàn race condition trong việc xác minh và liên kết media asset cho cả Sản phẩm (Product) và Thiết bị cũ (Used Device).

- **Ràng buộc giá khuyến mãi (Discount / Sale Price)**:
  - Bổ sung `@model_validator(mode="after")` cho `ProductPayload` kiểm tra: giá khuyến mãi phải nhỏ hơn giá niêm yết của cả sản phẩm chính và các biến thể con.

## Cập nhật 2026-07-06 - Optimistic Locking và Quản lý Media Assets tích hợp

- **Optimistic Locking cho Sản phẩm**:
  - Truy vấn `get_product_current_for_update` sử dụng `SELECT ... FOR UPDATE` để khóa dòng sản phẩm trong transaction hiện tại.
  - Hàm `update_product_record` kiểm tra phiên bản dữ liệu bằng cách thêm điều kiện `version = :expected_version` trong lệnh `UPDATE`.
  - Service `update_product` sẽ nâng cấp version đồng thời kiểm tra số dòng bị ảnh hưởng (`updated_count`). Nếu bằng `0` và sản phẩm vẫn tồn tại, hệ thống trả lỗi `409 Conflict` có mã `"PRODUCT_VERSION_CONFLICT"`.

- **Quản lý & Ràng buộc Media Assets**:
  - Tạo bảng `media_assets` lưu trữ metadata của tất cả các file đã upload (bao gồm `folder`, `public_url`, và các trường polymorphic `associated_entity_type`, `associated_entity_id`).
  - Khi thêm mới hoặc cập nhật sản phẩm, hệ thống thực hiện kiểm tra chéo (`validate_media_assets`) để đảm bảo file tồn tại trong đúng thư mục được phép (`products`) và chưa bị sở hữu bởi một thực thể khác.
  - Thiết lập liên kết sở hữu (`associate_assets_with_entity`) cho các file media để dọn dẹp các liên kết mồ côi khi thay đổi.

## Cập nhật 2026-07-06 - Ràng buộc đệ quy danh mục cha của sản phẩm và chặn xóa biến thể có phát sinh nghiệp vụ

- Cập nhật `product_visibility_blocker` đệ quy kiểm tra tất cả các danh mục tổ tiên của sản phẩm bằng toán tử LTREE (`c.path @> tc.path`). Nếu có bất kỳ danh mục cha nào bị ẩn, chặn không cho kích hoạt sản phẩm.
- Bổ sung kiểm tra liên kết tồn kho/đơn hàng trước khi xóa biến thể sản phẩm trong `upsert_product_variants` và `delete_product_variant`. Nếu có ràng buộc nghiệp vụ, trả lỗi `409` yêu cầu admin ẩn biến thể thay vì xóa mềm.

## Cập nhật 2026-07-05 - Siết giá sản phẩm và tổ hợp biến thể

- Payload quản trị sản phẩm và biến thể không còn chấp nhận `price = 0`; giá bán phải lớn hơn 0 để tránh tạo đơn miễn phí ngoài ý muốn.
- Backend chặn trùng tổ hợp thuộc tính biến thể đang hoạt động, kể cả khi SKU khác nhau; ưu tiên so sánh `attributes`, fallback theo màu/dung lượng/RAM/cấu hình.
- Thay đổi nằm ở tầng schema/service trước khi ghi database, giúp admin nhận lỗi nghiệp vụ rõ ràng thay vì để dữ liệu trùng lọt vào catalog.

## Cập nhật 2026-07-05 - Ràng buộc bảo mật checkout/POS và catalog public

- Endpoint public `POST /api/catalog/products` không còn cho anonymous tạo sản phẩm; route này yêu cầu permission `product:create`, đồng bộ với `/api/admin/products`.
- Checkout online không còn tin `user_id` do client tự truyền. Nếu có JWT, backend ép `payload.user_id` về user hiện tại; nếu không có JWT thì chỉ cho đơn guest không dùng tài khoản/điểm thưởng.
- POS offline (`is_offline=true`) bắt buộc user hiện tại là `STAFF_ADMIN` hoặc `SUPER_ADMIN`; chỉ luồng nhân viên mới được gán khách hàng khác và dùng giá POS.
- `Idempotency-Key` của đơn hàng được scope theo actor (`user`, `staff`, hoặc `guest`) trước khi lưu, tránh người khác đoán/trùng key để đọc lại response đơn không thuộc mình.

## Cập nhật 2026-07-04 - Checkout catalog dùng giá và trạng thái sản phẩm từ database

- Đơn online với sản phẩm mới phải tham chiếu `product_id` hoặc `variant_id` hợp lệ; backend kiểm tra sản phẩm active, không bị ẩn bởi danh mục/thương hiệu và biến thể còn active trước khi giữ tồn.
- Giá tính tiền của checkout online lấy từ `products/product_variants` và trả `409` nếu giá client đã cũ hoặc bị sửa.
- POS offline vẫn cần `product_id` thật nhưng được giữ giá đã tính tại quầy để không phá các ưu đãi/dịch vụ nội bộ.
- Sửa chuỗi lỗi bị mojibake trong luồng nhân bản sản phẩm sang tiếng Việt UTF-8 đúng dấu.

## Cập nhật 2026-07-03 - Nhận diện hàng cũ trong đơn hàng

- Chi tiết đơn hàng admin hiển thị badge `Hàng cũ đã thẩm định` cho dòng có `order_items.used_device_id`.
- Dòng hàng cũ trong đơn dùng giá bán đã duyệt theo từng thiết bị và không đại diện cho tồn kho SKU hàng mới.

## Cập nhật 2026-07-03 - Checkout hàng cũ theo từng thiết bị

- Trang chi tiết hàng cũ có thể thêm đúng thiết bị vào giỏ bằng `usedDeviceId`, không dùng SKU/biến thể giả và không tăng số lượng quá 1.
- Checkout gửi dòng hàng cũ bằng `used_device_id`; backend kiểm tra lại giá bán đã duyệt từ database thay vì tin giá client.
- Dòng hàng cũ trong đơn có thể không có `product_id` vì đơn đang bán đúng thiết bị đã thẩm định, còn thông tin so sánh sản phẩm gốc vẫn nằm ở snapshot của thiết bị.

## Cập nhật 2026-07-03 - Storefront điện thoại cũ theo từng thiết bị

- Bổ sung bài đăng riêng cho `used_devices`, dùng ảnh thực tế và snapshot sản phẩm/biến thể gốc thay vì tạo thêm sản phẩm catalog hoặc biến thể giả.
- Chỉ bài đã duyệt và thiết bị ở trạng thái sẵn sàng bán mới xuất hiện trên storefront.
- Trang danh sách/chi tiết hàng cũ hiển thị giá máy mới tham chiếu, giá hàng cũ, mức tiết kiệm, hạng, điểm tình trạng, pin, bảo hành, checklist QC và thông số gốc.
- IMEI đầy đủ không được trả ra API công khai; storefront chỉ nhận IMEI đã che.
- Checkout hàng cũ chưa được nối trong lát cắt này; không thay đổi contract giỏ hàng hoặc FIFO hàng mới.

## Cập nhật 2026-07-03 - Nền tảng quản lý thiết bị cũ theo sản phẩm gốc

- Bổ sung module hàng cũ độc lập theo từng IMEI, không tạo mỗi máy cũ thành một biến thể và không cộng thiết bị cũ vào tồn bán được của sản phẩm mới.
- Mỗi thiết bị cũ tham chiếu sản phẩm/biến thể gốc và lưu snapshot tên, SKU, màu, RAM, dung lượng, thông số, giá niêm yết và giá máy mới tại thời điểm xác nhận thu mua.
- API admin hỗ trợ tạo hồ sơ tiếp nhận, chuyển trạng thái, lưu kết quả thẩm định, xác nhận thu mua và đọc danh sách thiết bị trong kho hàng cũ.
- Màn admin `Hàng cũ` hiển thị giá máy mới, giá hàng cũ và số tiền tiết kiệm theo đúng từng thiết bị.

## Cập nhật 2026-07-01 - Nâng cấp hiển thị card sản phẩm storefront

- `ProductCard` trên storefront dùng icon `Star` từ Lucide cho đánh giá thay vì ký tự sao, đồng bộ ngôn ngữ icon với các thao tác yêu thích/so sánh.
- Giảm độ trễ stagger animation theo vị trí card để danh sách sản phẩm xuất hiện nhanh hơn, nhất là trên trang chủ và danh sách sản phẩm mobile.
- Không thay đổi dữ liệu sản phẩm, API catalog hoặc contract giỏ hàng.

## Cập nhật 2026-07-01 - Nâng cấp bộ lọc mobile trang danh sách sản phẩm

- Frontend `/products` chuyển bộ lọc mobile từ panel chiếm đầu trang sang bottom sheet mở bằng nút `Bộ lọc`, giúp người dùng thấy danh sách sản phẩm/skeleton ngay trong viewport đầu.
- Desktop vẫn giữ sidebar bộ lọc sticky; logic query URL và payload gọi API catalog không thay đổi.

## Cập nhật 2026-06-29 - Kiểm thử tích hợp sản phẩm đến storefront

- Bổ sung luồng admin tạo sản phẩm, gửi duyệt, duyệt, đối chiếu database và đọc lại qua API catalog công khai.

## Cập nhật 2026-06-29 - Dọn dẹp sản phẩm test trong database

- Xóa sạch 13 sản phẩm test (bao gồm sản phẩm `test sản phẩm` và 12 sản phẩm `Sản phẩm Test Outbound`).
- Dọn dẹp toàn bộ dữ liệu liên kết trong các bảng: `product_analytics_events`, `product_favorites`, `product_reviews`, `product_comments`, `user_favorites`, `product_bundles`, `product_accessories`, `product_inventory_idempotency`, `product_audit_logs`, `product_image_comments`, `product_view_events`, `product_search_events`, `user_favorite_events`, `product_attached_services`, `after_sales_allocations`, `inventory_policy_migration_lines`, `product_identifier_pairs`, `inventory_identifier_edit_requests`, `flash_sales`, `inventory_adjustment_logs`, `inventory_reservations`, `content_product_relations`, `inventory_document_lines`, `product_imeis`, `product_serial_numbers`, `return_request_items`, `warranty_request_items`, `inventory_lot_movements`, `inventory_lots`, `inventory_transactions`, `inventory_levels`, `order_items` và `product_variants`.

## Cập nhật 2026-06-29 - Ổn định state chi tiết sản phẩm

- Tách shell lấy variant từ URL và content có `key` theo sản phẩm/variant để reset state đúng vòng đời.
- Khởi tạo màu, RAM, bộ nhớ và cấu hình bằng state initializer; bỏ cập nhật state trực tiếp trong render.
- Ảnh đang chọn được dẫn xuất từ `mediaItems` và chỉ số hiện tại; đổi variant reset gallery ngay trong handler.
- Giữ nguyên contract giỏ hàng, phụ kiện, dịch vụ và điều hướng bàn phím của media viewer.

## Cập nhật 2026-06-28 - Giảm thêm cảnh báo iteration storefront

- Gộp các chuỗi `map/filter/flatMap` trong `ProductDetailUtils` thành vòng lặp một lượt cho danh sách tuỳ chọn, cấu hình biến thể và thông số sản phẩm.
- Tối ưu `smartProductSearch` bằng cách gom dò danh mục/badge trong một lượt và dùng `Set` cho lookup danh mục.
- Gộp filter video trong `VideoPage` và sửa lại mã hóa Unicode của file này sau khi phát hiện chuỗi tiếng Việt bị mojibake.

## C?p nh?t 2026-06-28 - Gi?m c?nh b?o iteration product v? media

- T?i ?u th?m c?c helper bi?n th?, l?a ch?n s?n ph?m mua k?m, l?a ch?n d?ch v? k?m, brand options, validate SKU v? bulk action s?n ph?m b?ng v?ng l?p m?t l??t ho?c `Map`/`Set`.
- S?a c?c lookup trong th? vi?n ?nh ?? resolve ?nh theo `view` b?ng helper m?t l??t thay v? `findIndex` l?p trong danh s?ch card.


- Các thay đổi không đổi contract API hoặc payload sản phẩm; nhóm cảnh báo product còn lại chủ yếu nằm ở hook sản phẩm và utility storefront cần xử lý riêng.


- ÄÆ°a cÃ¡c helper thuáº§n cá»§a POS (`calculateAccessoryPrice`, `tieredServicePrice`, `calculateServicePrice`) ra module scope Ä‘á»ƒ khÃ´ng táº¡o láº¡i sau má»—i render, giá»¯ nguyÃªn cÃ´ng thá»©c Æ°u tiÃªn giÃ¡ override, giÃ¡ fixed/percent/tiered vÃ  fallback giÃ¡ phá»¥ kiá»‡n.
- ÄÆ°a helper Ä‘á»c giÃ¡ trá»‹ spec biáº¿n thá»ƒ (`variantSpecValue`) ra module scope; helper váº«n dÃ¹ng `normalizeOptionKey` chung vÃ  khÃ´ng Ä‘á»•i cÃ¡ch fallback giá»¯a `specs`/`attributes`.
- ÄÆ°a wrapper in Ä‘Æ¡n hÃ ng admin ra module scope, tiáº¿p tá»¥c gá»i `printOrderDocumentPopup` vá»›i bá»™ helper `currency`, `compactId`, `statusLabel` hiá»‡n cÃ³.
- ÄÆ°a quick action vÃ  fallback tráº£ lá»i cá»§a `AIChatWidget` ra module scope; ná»™i dung fallback trong vÃ¹ng sá»­a Ä‘Æ°á»£c chuáº©n hÃ³a sang tiáº¿ng Viá»‡t cÃ³ dáº¥u.


- Tá»‘i Æ°u cÃ¡c luá»“ng dá»±ng danh sÃ¡ch áº£nh, tÃ¹y chá»n, thÃ´ng sá»‘, tá»« khÃ³a tÃ¬m kiáº¿m vÃ  mÃ£ sáº£n pháº©m phÃ¢n tÃ­ch báº±ng `flatMap`, `Set` hoáº·c thÃªm pháº§n tá»­ cÃ³ Ä‘iá»u kiá»‡n Ä‘á»ƒ trÃ¡nh nhiá»u lÆ°á»£t duyá»‡t máº£ng khÃ´ng cáº§n thiáº¿t.
- Thay key theo chá»‰ sá»‘ á»Ÿ skeleton danh sÃ¡ch vÃ  sao Ä‘Ã¡nh giÃ¡ báº±ng key á»•n Ä‘á»‹nh; sá»­a thÃ´ng bÃ¡o lá»—i quyá»n Ä‘Ã¡nh giÃ¡ sang tiáº¿ng Viá»‡t Unicode Ä‘Ãºng dáº¥u.
- Giáº£m render thá»«a á»Ÿ `ProductDetail`, `ImagesModal` vÃ  `VideoPage` báº±ng ref cho dá»¯ liá»‡u chá»‰ phá»¥c vá»¥ handler/reset; cháº¿ Ä‘á»™ giáº£m chuyá»ƒn Ä‘á»™ng cá»§a trÃ¬nh xem áº£nh hiá»‡n táº¯t tá»± Ä‘á»™ng phÃ¡t vÃ  transition.
- ÄÆ°a helper chia sáº» video khÃ´ng phá»¥ thuá»™c state ra module scope Ä‘á»ƒ khÃ´ng táº¡o láº¡i sau má»—i render.
- Thay key theo chá»‰ sá»‘ báº±ng key á»•n Ä‘á»‹nh tá»« ná»™i dung á»Ÿ cÃ¡c báº£ng, bullet, stepper chÃ­nh sÃ¡ch, hÃ³a Ä‘Æ¡n, chi tiáº¿t Ä‘Æ¡n hÃ ng, POS vÃ  trang sao lÆ°u dá»¯ liá»‡u.
- ÄÆ°a cáº¥u hÃ¬nh stepper Ä‘Æ¡n hÃ ng, hÃ£ng váº­n chuyá»ƒn, sá»± kiá»‡n giao hÃ ng, tab khÃ¡ch hÃ ng vÃ  báº£ng mÃ u metric ra module scope Ä‘á»ƒ trÃ¡nh táº¡o láº¡i sau má»—i render.
- Form biáº¿n thá»ƒ dÃ¹ng `_clientKey` á»•n Ä‘á»‹nh khi thÃªm hoáº·c hydrate dá»¯ liá»‡u; helper chung loáº¡i client key khá»i payload trÆ°á»›c khi gá»i API sáº£n pháº©m.
- TÃ¡ch biá»ƒu Ä‘á»“ ranking vÃ  tá»•ng quan admin thÃ nh cÃ¡c component táº£i báº±ng `React.lazy`; Vite táº¡o riÃªng chunk `RankingCharts` vÃ  `AdminOverviewCharts`, giáº£m kÃ­ch thÆ°á»›c chunk trang chÃ­nh tÆ°Æ¡ng á»©ng.
- ÄÆ°a cáº¥u hÃ¬nh overview, badge, tráº¡ng thÃ¡i xuáº¥t báº£n sáº£n pháº©m vÃ  cÃ¡c helper thuáº§n cá»§a notification, loyalty, biáº¿n thá»ƒ, submit/slug sáº£n pháº©m ra module scope Ä‘á»ƒ trÃ¡nh táº¡o láº¡i má»—i render.


- Chuáº©n hÃ³a mÃ u chá»¯ trÃªn cÃ¡c nÃºt/khá»‘i ná»n mÃ u á»Ÿ trang chi tiáº¿t sáº£n pháº©m, báº£ng xáº¿p háº¡ng, giá» hÃ ng vÃ  má»™t sá»‘ mÃ n admin liÃªn quan Ä‘á»ƒ khÃ´ng cÃ²n dÃ¹ng chá»¯ xÃ¡m trÃªn ná»n hoáº·c tráº¡ng thÃ¡i hover cÃ³ mÃ u.
- CÃ¡c thay Ä‘á»•i chá»‰ náº±m á»Ÿ class Tailwind, khÃ´ng Ä‘á»•i logic xá»­ lÃ½ sáº£n pháº©m, giá» hÃ ng hoáº·c POS.
- Gá»¡ cÃ¡c dependency frontend khÃ´ng cÃ²n Ä‘Æ°á»£c import (`dompurify`, `react-leaflet`, `vitest`) vÃ  Ä‘á»•i cÃ¡c Ä‘oáº¡n tÃ¬m thá»i Ä‘iá»ƒm Flash Sale gáº§n nháº¥t tá»« `sort()[0]` sang má»™t lÆ°á»£t `reduce`.
- Tá»‘i Æ°u thÃªm device id voucher dÃ¹ng chung, passive listener an toÃ n, ref initializer cho Set/Map vÃ  animation typing cá»§a chat widget.
- Äá»•i cÃ¡c animation dÃ¹ng `motion` trá»±c tiáº¿p sang `LazyMotion`/`m` Ä‘á»ƒ giáº£m pháº§n animation load eagerly á»Ÿ chat widget, thÃ´ng bÃ¡o, card sáº£n pháº©m, skeleton, Ä‘Ã¡nh giÃ¡, so sÃ¡nh vÃ  giá» hÃ ng.
- Tá»‘i Æ°u `AuthContext` báº±ng provider value á»•n Ä‘á»‹nh, dÃ¹ng API `use()` cá»§a React 19, bá» export ná»™i bá»™ khÃ´ng dÃ¹ng vÃ  khá»Ÿi táº¡o lá»‹ch sá»­ tÃ¬m kiáº¿m trá»±c tiáº¿p trong state initializer.
- Tá»‘i Æ°u tra cá»©u tá»‰nh/phÆ°á»ng trong `AddressForm` báº±ng dá»¯ liá»‡u chuáº©n hÃ³a vÃ  Map Ä‘á»ƒ giáº£m lookup láº·p khi dÃ² Ä‘á»‹a chá»‰.
- Tá»‘i Æ°u file upload trong `AfterSalesTab`: giá»¯ danh sÃ¡ch `File` báº±ng ref, cleanup object URL theo preview state, á»•n Ä‘á»‹nh hÃ m táº£i dá»¯ liá»‡u, Ä‘Æ°a hÃ m tÃ­nh tiáº¿n trÃ¬nh ra module scope vÃ  Ä‘á»•i key index sang key á»•n Ä‘á»‹nh hÆ¡n.
- Tá»‘i Æ°u thÃªm `AdminStoreInfoTab` Ä‘á»ƒ snapshot dá»¯ liá»‡u cá»­a hÃ ng dÃ¹ng ref khi chá»‰ phá»¥c vá»¥ thao tÃ¡c há»§y, trÃ¡nh render thá»«a.
- Tá»‘i Æ°u `ComparePage`: bá» state loading khÃ´ng Ä‘Æ°á»£c render, dÃ¹ng Map/memo cho danh sÃ¡ch so sÃ¡nh, bá» `map().filter(Boolean)` vÃ  thay key index cá»§a cá»™t trá»‘ng báº±ng slot key á»•n Ä‘á»‹nh.
- TÃ¡ch nhÃ¡nh thu há»“i phiÃªn Ä‘Äƒng nháº­p trong `useAccountSessions` Ä‘á»ƒ bá» cáº£nh bÃ¡o await trÆ°á»›c guard mÃ  váº«n giá»¯ thá»© tá»± revoke trÆ°á»›c khi Ä‘Äƒng xuáº¥t/chuyá»ƒn trang.


- Bá»• sung `aria-label` cho cÃ¡c Ã´ nháº­p, checkbox vÃ  nÃºt thao tÃ¡c trong form sáº£n pháº©m, báº£ng sáº£n pháº©m, biáº¿n thá»ƒ, so sÃ¡nh, há»i Ä‘Ã¡p vÃ  Ä‘Ã¡nh giÃ¡ sáº£n pháº©m.
- ThÃªm nhÃ£n truy cáº­p vÃ  track captions rá»—ng cho cÃ¡c video sáº£n pháº©m/Ä‘Ã¡nh giÃ¡ Ä‘á»ƒ xá»­ lÃ½ cáº£nh bÃ¡o media; bá» `autoFocus` á»Ÿ cÃ¡c bá»™ chá»n sáº£n pháº©m Ä‘á»ƒ trÃ¡nh tá»± giÃ nh focus khi má»Ÿ giao diá»‡n.


- ThÃªm `type="button"` cho cÃ¡c nÃºt thao tÃ¡c sáº£n pháº©m khÃ´ng submit form trong `ProductPurchaseActions`, `ProductDetail`, `ProductGallery`, `ProductSpecsTable`, `ProductCard`, `ComparePage` vÃ  `ProductListPage`.
- Siáº¿t helper YouTube trong `ProductDetailUtils` Ä‘á»ƒ chá»‰ nháº­n host YouTube há»£p lá»‡ trÆ°á»›c khi dá»±ng URL embed; iframe sáº£n pháº©m Ä‘Æ°á»£c thÃªm sandbox.
- Thay key dÃ¹ng index trong `ProductCard` vÃ  `TechSpecsTable` báº±ng key á»•n Ä‘á»‹nh hÆ¡n tá»« URL áº£nh hoáº·c ná»™i dung thÃ´ng sá»‘.

## Cáº­p nháº­t 2026-06-27 - KhÃ´i phá»¥c dá»¯ liá»‡u giÃ¡ POS sau khi tÃ¡ch repository

- Kiá»ƒm thá»­ trÃ¬nh duyá»‡t phÃ¡t hiá»‡n `/api/admin/products` lÃ m rÆ¡i cÃ¡c trÆ°á»ng giÃ¡/tá»“n Ä‘Ã£ Ä‘Æ°á»£c repository truy váº¥n khi dá»±ng láº¡i `salesConfig`.
- `attachedServices` giá»¯ láº¡i `overridePrice` vÃ  `metadata`, bao gá»“m `metadata.priceTiers`.
- `accessoryOffers` tráº£ láº¡i `price`, `salePrice`, `discountPrice`, `originalPrice`, `normalDiscountPrice`, `stockQuantity` vÃ  `isSellable`.
- GiÃ¡ offer Ä‘Æ°á»£c tÃ­nh tá»« giÃ¡ bÃ¡n hiá»‡n táº¡i vÃ  `discountType/discountValue` khi cáº¥u hÃ¬nh chÆ°a cÃ³ `price` há»£p lá»‡.

## Cáº­p nháº­t 2026-06-27 - TÃ¡ch repository sáº£n pháº©m vÃ  component chi tiáº¿t sáº£n pháº©m

- TÃ¡ch `product_repo.py` thÃ nh facade tÆ°Æ¡ng thÃ­ch vÃ  cÃ¡c module nhá» trong `app/infrastructure/database/repositories/product/`: `listing`, `export_jobs`, `relations`, `import_jobs`, `crud`, `duplicate`.
- CÃ¡c service hiá»‡n táº¡i váº«n import qua `product_repo`, nÃªn láº§n tÃ¡ch nÃ y khÃ´ng Ä‘á»•i chá»¯ kÃ½ hÃ m hoáº·c transaction boundary.
- TÃ¡ch cÃ¡c helper/subcomponent Ä‘áº§u file `ProductDetail.tsx` sang `ProductDetailSections.tsx`, gá»“m highlight, Æ°u Ä‘Ã£i mua kÃ¨m, dá»‹ch vá»¥ Ä‘i kÃ¨m vÃ  helper tÃ­nh giÃ¡ liÃªn quan.

## Cáº­p nháº­t 2026-06-27 - Sá»­a giÃ¡ sáº£n pháº©m mua kÃ¨m trong Ä‘Æ¡n hÃ ng

- API chi tiáº¿t sáº£n pháº©m storefront vÃ  API danh sÃ¡ch sáº£n pháº©m admin nay fallback giÃ¡ sáº£n pháº©m mua kÃ¨m tá»« biáº¿n thá»ƒ active tháº¥p nháº¥t khi giÃ¡ sáº£n pháº©m cha Ä‘ang báº±ng `0`, trÃ¡nh phá»¥ kiá»‡n cáº¥u hÃ¬nh theo sáº£n pháº©m Ä‘a biáº¿n thá»ƒ bá»‹ Ä‘Æ°a vÃ o giá»/POS vá»›i giÃ¡ `0Ä‘`.
- `/admin/products` tráº£ thÃªm `price` Ä‘Ã£ tÃ­nh theo `discountType/discountValue` cho tá»«ng `salesConfig.accessoryOffers`, thay vÃ¬ giá»¯ nguyÃªn giÃ¡ cÅ© trong JSON cáº¥u hÃ¬nh náº¿u trÆ°á»ng nÃ y thiáº¿u hoáº·c báº±ng 0.
- Trang chi tiáº¿t sáº£n pháº©m khÃ´ng cÃ²n dÃ¹ng trá»±c tiáº¿p `acc.price` khi hiá»ƒn thá»‹/thÃªm phá»¥ kiá»‡n mua kÃ¨m vÃ o giá»; frontend tá»± tÃ­nh láº¡i tá»« `salePrice/normalDiscountPrice/originalPrice` vÃ  má»©c giáº£m Ä‘á»ƒ payload checkout khÃ´ng gá»­i `unit_price = 0`.

## Cáº­p nháº­t 2026-06-27 - Tráº£ Ä‘á»§ dá»¯ liá»‡u giÃ¡ dá»‹ch vá»¥ Ä‘i kÃ¨m cho POS admin

- `GET /admin/products` nay tráº£ thÃªm `overridePrice` vÃ  luÃ´n chuáº©n hÃ³a `metadata` cho tá»«ng `attachedServices`, Ä‘á»ƒ POS admin cÃ³ Ä‘á»§ dá»¯ liá»‡u tÃ­nh giÃ¡ giá»‘ng trang khÃ¡ch hÃ ng.
- Sáº£n pháº©m mua kÃ¨m trong `salesConfig.accessoryOffers` cÅ©ng Ä‘Æ°á»£c hydrate thÃªm `price`, `salePrice/discountPrice`, `originalPrice`, `normalDiscountPrice`, `imageUrl` vÃ  `stockQuantity`, Ä‘á»ƒ POS admin tÃ­nh Ä‘Æ°á»£c giÃ¡ mua kÃ¨m khi offer JSON khÃ´ng cÃ³ sáºµn giÃ¡.
- Repository sáº£n pháº©m Ä‘á»c thÃªm `product_attached_services.override_price`; frontend POS dÃ¹ng trÆ°á»ng nÃ y trÆ°á»›c khi fallback sang `fixedPrice`, `percentValue/baseAmount` hoáº·c `metadata.priceTiers`.
- Thay Ä‘á»•i nÃ y trÃ¡nh lá»—i dá»‹ch vá»¥ Ä‘i kÃ¨m cÃ³ cáº¥u hÃ¬nh giÃ¡ theo tier hoáº·c giÃ¡ override nhÆ°ng hiá»ƒn thá»‹ `0 Ä‘` khi táº¡o Ä‘Æ¡n táº¡i quáº§y.

## Update 2026-06-27 - RÃ ng buá»™c IMEI pháº£i cÃ³ serial

- Product sales config Ä‘Æ°á»£c chuáº©n hÃ³a khi lÆ°u: náº¿u sáº£n pháº©m báº­t `imeiPolicy.trackImei` á»Ÿ cháº¿ Ä‘á»™ `MANUAL`, backend tá»± lÆ°u `serialPolicy` vá» `MANUAL` vÃ  `trackSerialNumber = true`.
- Form sáº£n pháº©m admin khÃ³a checkbox IMEI khi serial hiá»‡u lá»±c chÆ°a báº­t; admin pháº£i báº­t serial trÆ°á»›c rá»“i má»›i báº­t IMEI.
- Náº¿u admin táº¯t serial thá»§ cÃ´ng, form tá»± táº¯t IMEI Ä‘á»ƒ trÃ¡nh tráº¡ng thÃ¡i sáº£n pháº©m cÃ³ IMEI nhÆ°ng khÃ´ng cÃ³ serial.

## Update 2026-06-24 - Hiá»ƒn thá»‹ danh sÃ¡ch sáº£n pháº©m mua kÃ¨m trong form admin

- Form admin pháº§n `Sáº£n pháº©m mua kÃ¨m giáº£m giÃ¡` khÃ´ng cÃ²n báº¯t buá»™c admin pháº£i chá»n danh má»¥c/thÆ°Æ¡ng hiá»‡u hoáº·c nháº­p tá»« khÃ³a trÆ°á»›c má»›i hiá»‡n danh sÃ¡ch; danh sÃ¡ch gá»£i Ã½ Ä‘Æ°á»£c má»Ÿ sáºµn Ä‘á»ƒ trÃ¡nh hiá»ƒu nháº§m lÃ  khÃ´ng cÃ³ dá»¯ liá»‡u.
- Frontend pháº§n chá»n mua kÃ¨m nay gá»i endpoint `GET /admin/products/suggestions` theo bá»™ lá»c hiá»‡n táº¡i vÃ  gá»™p vá»›i danh sÃ¡ch sáº£n pháº©m Ä‘Ã£ táº£i cá»¥c bá»™, thay vÃ¬ chá»‰ phá»¥ thuá»™c vÃ o 20 sáº£n pháº©m Ä‘ang hiá»ƒn thá»‹ á»Ÿ báº£ng quáº£n lÃ½ sáº£n pháº©m.
- API suggestions tráº£ thÃªm `stockQuantity` vÃ  `isSellable`, tÃ­nh tá»« tá»•ng tá»“n biáº¿n thá»ƒ active hoáº·c tá»“n sáº£n pháº©m cha, Ä‘á»ƒ UI lá»c vÃ  hiá»ƒn thá»‹ Ä‘Ãºng sáº£n pháº©m cÃ²n bÃ¡n Ä‘Æ°á»£c.
- Sá»­a lá»—i hydrate cÃ¡c sáº£n pháº©m mua kÃ¨m Ä‘Ã£ chá»n: backend Ä‘Ã£ tÃ­nh `stock_quantity/status` trong truy váº¥n nhÆ°ng chÆ°a Ä‘Æ°a vÃ o lookup, lÃ m form admin luÃ´n nháº­n `stockQuantity = 0` vÃ  bÃ¡o nháº§m `Háº¿t hÃ ng - Ä‘ang khÃ³a bÃ¡n kÃ¨m`.
- Bá»• sung fallback resolve metadata mua kÃ¨m trá»±c tiáº¿p tá»« cÃ¡c `productId` trong `salesConfig.accessoryOffers`, phÃ²ng trÆ°á»ng há»£p dá»¯ liá»‡u cÅ© cÃ³ offer trong JSON nhÆ°ng thiáº¿u dÃ²ng tÆ°Æ¡ng á»©ng trong báº£ng `product_accessories`.
- Bá»™ lá»c danh má»¥c cá»§a endpoint gá»£i Ã½ mua kÃ¨m nay dÃ¹ng nhÃ¡nh `categories.path`, nÃªn chá»n danh má»¥c cha nhÆ° `Phá»¥ kiá»‡n cÃ´ng nghá»‡` sáº½ láº¥y cáº£ sáº£n pháº©m thuá»™c cÃ¡c danh má»¥c con/chÃ¡u thay vÃ¬ chá»‰ so khá»›p trá»±c tiáº¿p `category_id/subcategory_id`.
- Sá»­a lá»—i `500` á»Ÿ `/admin/products/suggestions` sau khi thÃªm lá»c theo nhÃ¡nh danh má»¥c báº±ng cÃ¡ch Ã©p kiá»ƒu rÃµ rÃ ng cÃ¡c tham sá»‘ UUID (`excludeId`, `categoryId`, `brandId`) trong SQL cho PostgreSQL/asyncpg.
- Frontend fallback khi API gá»£i Ã½ lá»—i cÅ©ng lá»c theo toÃ n bá»™ cÃ¢y danh má»¥c con/chÃ¡u thay vÃ¬ chá»‰ láº¥y danh má»¥c con trá»±c tiáº¿p; Ä‘á»“ng thá»i Ä‘á»c tá»“n qua `availableStock/stockQuantity/stock`.
- Luá»“ng lÆ°u biáº¿n thá»ƒ khÃ´ng cÃ²n báº¯t buá»™c ghi SKU sáº£n pháº©m cha báº±ng SKU biáº¿n thá»ƒ máº·c Ä‘á»‹nh náº¿u SKU Ä‘Ã³ Ä‘Ã£ thuá»™c sáº£n pháº©m active khÃ¡c, trÃ¡nh lá»—i unique `idx_unique_active_product_sku` khi chá»‰ sá»­a cáº¥u hÃ¬nh mua kÃ¨m.

## Update 2026-06-24 - Kháº¯c phá»¥c lá»—i tiáº¿ng Viá»‡t hiá»ƒn thá»‹ tÄ©nh trÃªn trang chi tiáº¿t sáº£n pháº©m

- PhÃ¡t hiá»‡n vÃ  sá»­a Ä‘á»•i toÃ n bá»™ cÃ¡c chuá»—i vÄƒn báº£n tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a (Mojibake) dáº¡ng double/triple UTF-8 encode trong file [ProductDetail.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/products/components/ProductDetail.tsx) (nhÆ° cÃ¡c nhÃ£n: `Äáº·c Ä‘iá»ƒm ná»•i báº­t`, `Æ¯u Ä‘Ã£i mua kÃ¨m`, `Dá»‹ch vá»¥ Ä‘i kÃ¨m`, `Báº£o hÃ nh`, `Äá»•i tráº£`, `Giao nhanh`, v.v.).
- KhÃ´i phá»¥c chÃ­nh xÃ¡c 100% tiáº¿ng Viá»‡t cÃ³ dáº¥u chuáº©n Unicode UTF-8 Ä‘á»ƒ hiá»ƒn thá»‹ Ä‘Ãºng giao diá»‡n ngÆ°á»i dÃ¹ng.

## Update 2026-06-24 - Hiá»ƒn thá»‹ Ä‘Ãºng báº£o hÃ nh vÃ  Ä‘á»•i tráº£ trÃªn chi tiáº¿t sáº£n pháº©m

- Trang chi tiáº¿t sáº£n pháº©m nay láº¥y tháº» cam káº¿t `Äá»•i tráº£ ... ngÃ y` vÃ  `Báº£o hÃ nh ... thÃ¡ng` tá»« `salesConfig.warrantyPolicy` thay vÃ¬ hard-code `Äá»•i tráº£ 7 ngÃ y` vÃ  `Báº£o hÃ nh 12 thÃ¡ng`.
- Náº¿u sáº£n pháº©m cÃ³ cáº¥u hÃ¬nh báº£o hÃ nh 6 thÃ¡ng, 18 thÃ¡ng hoáº·c 1 Ä‘á»•i 1/Ä‘á»•i tráº£ 30 ngÃ y, storefront sáº½ hiá»ƒn thá»‹ Ä‘Ãºng theo dá»¯ liá»‡u sáº£n pháº©m.
- Vá»›i sáº£n pháº©m chÆ°a cÃ³ chÃ­nh sÃ¡ch cá»¥ thá»ƒ, UI fallback sang nhÃ£n chung `Äá»•i tráº£ theo chÃ­nh sÃ¡ch` vÃ  `Báº£o hÃ nh theo hÃ£ng` Ä‘á»ƒ trÃ¡nh Ä‘Æ°a sai má»‘c thá»i gian.

## Update 2026-06-24 - Sá»­a tráº¡ng thÃ¡i tá»“n kho sáº£n pháº©m mua kÃ¨m trÃªn trang chi tiáº¿t

- API chi tiáº¿t sáº£n pháº©m nay tÃ­nh `stockQuantity` cá»§a sáº£n pháº©m mua kÃ¨m tá»« cáº£ tá»“n biáº¿n thá»ƒ active, tá»“n thá»±c táº¿ trong `inventory_levels` vÃ  tá»“n sáº£n pháº©m cha, trÃ¡nh trÆ°á»ng há»£p phá»¥ kiá»‡n cÃ²n hÃ ng nhÆ°ng bá»‹ tráº£ vá» háº¿t hÃ ng.
- Äiá»u kiá»‡n lá»c biáº¿n thá»ƒ mua kÃ¨m Ä‘Æ°á»£c chuáº©n hÃ³a tráº¡ng thÃ¡i khÃ´ng phÃ¢n biá»‡t hoa/thÆ°á»ng Ä‘á»ƒ khÃ´ng bá» sÃ³t biáº¿n thá»ƒ `ACTIVE`.
- Trang chi tiáº¿t sáº£n pháº©m khÃ´ng cÃ²n máº·c Ä‘á»‹nh xem payload mua kÃ¨m thiáº¿u `stockQuantity` lÃ  háº¿t hÃ ng; khi backend tráº£ `isSellable=false` hoáº·c tá»“n báº±ng 0 thÃ¬ váº«n khÃ³a Ä‘Ãºng theo yÃªu cáº§u.

## Update 2026-06-24 - Æ¯u tiÃªn sáº£n pháº©m bÃ¡n kÃ¨m Ä‘ang bÃ¡n Ä‘Æ°á»£c

- ThÃªm script `backend/scripts/assign_accessory_offers_for_devices.py` Ä‘á»ƒ gÃ¡n tá»± Ä‘á»™ng sáº£n pháº©m bÃ¡n kÃ¨m cho nhÃ³m Äiá»‡n thoáº¡i, Laptop vÃ  Tablet.
- Script chá»‰ chá»n phá»¥ kiá»‡n Ä‘ang `ACTIVE` vÃ  cÃ²n tá»“n kháº£ dá»¥ng, tá»‘i Ä‘a 4 sáº£n pháº©m bÃ¡n kÃ¨m cho má»—i sáº£n pháº©m chÃ­nh; Ä‘Ã£ cháº¡y local vÃ  cáº­p nháº­t 60 sáº£n pháº©m, táº¡o 240 quan há»‡ `product_accessories`.
- Quy táº¯c giáº£m giÃ¡ bÃ¡n kÃ¨m: phá»¥ kiá»‡n dÆ°á»›i 2.000.000Ä‘ giáº£m 10%; tá»« 2.000.000Ä‘ Ä‘áº¿n dÆ°á»›i 5.000.000Ä‘ giáº£m 300.000Ä‘; tá»« 5.000.000Ä‘ trá»Ÿ lÃªn giáº£m 400.000Ä‘.
- Bá»™ chá»n Ä‘Æ°á»£c cÃ¢n báº±ng Ä‘á»ƒ má»—i sáº£n pháº©m cÃ³ cáº£ phá»¥ kiá»‡n giÃ¡ nhá» vÃ  phá»¥ kiá»‡n giÃ¡ trá»‹ cao thay vÃ¬ chá»‰ toÃ n phá»¥ kiá»‡n ráº».
- Danh sÃ¡ch chá»n `Sáº£n pháº©m mua kÃ¨m giáº£m giÃ¡` trong form sáº£n pháº©m admin nay loáº¡i cÃ¡c sáº£n pháº©m khÃ´ng bÃ¡n Ä‘Æ°á»£c: khÃ´ng `ACTIVE`, Ä‘Ã£ xÃ³a/áº©n/ngá»«ng hoáº·c khÃ´ng cÃ²n tá»“n á»Ÿ sáº£n pháº©m/biáº¿n thá»ƒ.
- Káº¿t quáº£ chá»n bÃ¡n kÃ¨m Ä‘Æ°á»£c sáº¯p xáº¿p theo má»©c liÃªn quan vá»›i sáº£n pháº©m Ä‘ang chá»‰nh sá»­a: cÃ¹ng danh má»¥c/danh má»¥c con, cÃ¹ng thÆ°Æ¡ng hiá»‡u, khá»›p tÃ¬m kiáº¿m vÃ  tá»“n kho kháº£ dá»¥ng cao hÆ¡n sáº½ lÃªn trÆ°á»›c.
- UI danh sÃ¡ch chá»n bÃ¡n kÃ¨m hiá»ƒn thá»‹ nhanh tá»“n kháº£ dá»¥ng dáº¡ng `CÃ²n X` Ä‘á»ƒ admin trÃ¡nh cáº¥u hÃ¬nh sáº£n pháº©m khÃ´ng thá»ƒ bÃ¡n kÃ¨m thá»±c táº¿.
- API chi tiáº¿t sáº£n pháº©m tÃ­nh tá»“n sáº£n pháº©m bÃ¡n kÃ¨m báº±ng tá»•ng tá»“n biáº¿n thá»ƒ active trÆ°á»›c, fallback vá» tá»“n sáº£n pháº©m cha; storefront nháº­n `isSellable` vÃ  `stockQuantity` Ä‘Ã£ chuáº©n hÃ³a.
- Trang chi tiáº¿t sáº£n pháº©m khÃ³a checkbox mua kÃ¨m khi sáº£n pháº©m bÃ¡n kÃ¨m háº¿t hÃ ng vÃ  hiá»ƒn thá»‹ `Háº¿t hÃ ng - táº¡m khÃ³a mua kÃ¨m`; form admin cÅ©ng khÃ³a cÃ¡c Ã´ cáº¥u hÃ¬nh cá»§a dÃ²ng bÃ¡n kÃ¨m Ä‘Ã£ háº¿t hÃ ng.

## Update 2026-06-24 - Bá» thá»‘ng kÃª áº£o khá»i storefront chi tiáº¿t sáº£n pháº©m

- API catalog Ä‘á»c `rating` vÃ  `reviewCount` tá»« báº£ng `product_reviews` cÃ³ tráº¡ng thÃ¡i `PUBLISHED`, khÃ´ng dÃ¹ng cÃ¡c cá»™t seed sáºµn `products.rating` vÃ  `products.review_count` cho storefront.
- `soldCount` tiáº¿p tá»¥c tÃ­nh tá»« `order_items` cá»§a Ä‘Æ¡n `COMPLETED`; khi khÃ´ng cÃ³ dá»¯ liá»‡u tháº­t, trang chi tiáº¿t khÃ´ng hiá»ƒn thá»‹ dÃ²ng `ÄÃ£ bÃ¡n 0`.
- Trang chi tiáº¿t sáº£n pháº©m chá»‰ hiá»ƒn thá»‹ sá»‘ Ä‘Ã¡nh giÃ¡ vÃ  sá»‘ Ä‘Ã£ bÃ¡n khi giÃ¡ trá»‹ lá»›n hÆ¡n 0, trÃ¡nh táº¡o cáº£m giÃ¡c cÃ³ dá»¯ liá»‡u thá»‘ng kÃª giáº£.
- Baseline `init_database.sql` vÃ  cÃ¡c script seed bá»• sung khÃ´ng cÃ²n ghi rating áº£o cho sáº£n pháº©m má»›i; sáº£n pháº©m chÆ°a cÃ³ Ä‘Ã¡nh giÃ¡ tháº­t giá»¯ `rating = NULL`, `review_count = 0`.
- ThÃªm script `backend/scripts/reconcile_product_engagement_stats.py` Ä‘á»ƒ Ä‘á»‘i soÃ¡t láº¡i `products.rating`, `products.review_count` vÃ  `products.favorite_count` tá»« `product_reviews`/`user_favorites`; Ä‘Ã£ cháº¡y local vÃ  cáº­p nháº­t 107 sáº£n pháº©m.

## Update 2026-06-24 - KhÃ³a trÆ°á»ng Ä‘á»‹nh danh biáº¿n thá»ƒ Ä‘Ã£ cÃ³ rÃ ng buá»™c

- Luá»“ng lÆ°u sáº£n pháº©m admin nay kiá»ƒm tra rÃ ng buá»™c dá»¯ liá»‡u trÆ°á»›c khi cáº­p nháº­t biáº¿n thá»ƒ hiá»‡n cÃ³.
- Náº¿u biáº¿n thá»ƒ Ä‘Ã£ cÃ³ tá»“n kho, chá»©ng tá»« kho, giao dá»‹ch kho, Ä‘Æ¡n hÃ ng, reservation, IMEI hoáº·c serial, backend tráº£ `409` khi payload cá»‘ Ä‘á»•i SKU, mÃ u sáº¯c, dung lÆ°á»£ng, RAM, cáº¥u hÃ¬nh, thuá»™c tÃ­nh hoáº·c thÃ´ng sá»‘ Ä‘á»‹nh danh cá»§a biáº¿n thá»ƒ.
- CÃ¡c trÆ°á»ng khÃ´ng phÃ¡ lá»‹ch sá»­ nhÆ° giÃ¡, áº£nh, tráº¡ng thÃ¡i bÃ¡n vÃ  biáº¿n thá»ƒ máº·c Ä‘á»‹nh váº«n Ä‘Æ°á»£c phÃ©p cáº­p nháº­t qua form sáº£n pháº©m.
- Biáº¿n thá»ƒ hiá»‡n cÃ³ khÃ´ng cÃ²n nháº­n `stockQuantity` tá»« payload catalog; tá»“n kho thá»±c táº¿ tiáº¿p tá»¥c do module kho/nháº­p kho/xuáº¥t kho quáº£n lÃ½.
- Biáº¿n thá»ƒ má»›i táº¡o tá»« form sáº£n pháº©m báº¯t Ä‘áº§u vá»›i tá»“n kho `0`, sau Ä‘Ã³ pháº£i nháº­p kho báº±ng chá»©ng tá»« Ä‘á»ƒ cÃ³ lá»‹ch sá»­ truy váº¿t.

## Update 2026-06-24 - Kiá»ƒm tra láº¡i áº£nh vÃ  chuáº©n hÃ³a thÃ´ng sá»‘ ká»¹ thuáº­t

- Kiá»ƒm tra láº¡i áº£nh sáº£n pháº©m báº±ng contact sheet tá»« `frontend/public/images/products/*/auto/cover.*`, Ä‘á»“ng thá»i Ä‘á»‘i soÃ¡t DB Ä‘á»ƒ báº£o Ä‘áº£m 103 sáº£n pháº©m active/draft Ä‘á»u cÃ³ `image_url`, gallery vÃ  file áº£nh local tá»“n táº¡i.
- Cáº­p nháº­t thÃªm áº£nh override Ä‘Ãºng hÆ¡n cho Garmin Forerunner 965 vÃ  Anker Prime 100W GaN trong `backend/scripts/fix_product_image_overrides.py`.
- Táº¡o script `backend/scripts/normalize_product_specifications.py` Ä‘á»ƒ chuáº©n hÃ³a cÃ¡c thÃ´ng sá»‘ cÅ© dÃ¹ng nhÃ£n tiáº¿ng Viá»‡t nhÆ° `MÃ n hÃ¬nh`, `Chip xá»­ lÃ½`, `Äá»™ phÃ¢n giáº£i`, `CÃ´ng suáº¥t tá»‘i Ä‘a` sang cÃ¡c key chuáº©n theo `categories.spec_fields` nhÆ° `screen_size`, `processor`, `resolution`, `power`.
- Cháº¡y chuáº©n hÃ³a cho 56 sáº£n pháº©m, sau Ä‘Ã³ bá»• sung thÃªm override thÃ´ng sá»‘ cho 11 phá»¥ kiá»‡n cÃ³ bá»™ field chung nhÆ°ng thiáº¿u nhiá»u giÃ¡ trá»‹ theo key chuáº©n.

## Update 2026-06-23 - Bá»• sung áº£nh cho sáº£n pháº©m vÃ  biáº¿n thá»ƒ cÃ²n thiáº¿u

- Táº¡o script `backend/scripts/fill_missing_product_images.py` Ä‘á»ƒ tÃ¬m áº£nh sáº£n pháº©m trÃªn web, táº£i áº£nh vá» `frontend/public/images/products/<slug>/auto`, rá»“i cáº­p nháº­t `products.image_url`, `products.images` vÃ  áº£nh cho cÃ¡c biáº¿n thá»ƒ Ä‘ang hoáº¡t Ä‘á»™ng.
- Táº¡o script `backend/scripts/fix_product_image_overrides.py` Ä‘á»ƒ vÃ¡ thá»§ cÃ´ng cÃ¡c sáº£n pháº©m bá»‹ káº¿t quáº£ tÃ¬m kiáº¿m tá»± Ä‘á»™ng chá»n nháº§m áº£nh, gá»“m Mophie 3-in-1 MagSafe, Apple Watch Series 9, Xiaomi Smart Band 8, Xiaomi AW300, Huawei MatePad 12 X vÃ  Samsung Galaxy Tab S11.
- Sá»­a dá»¯ liá»‡u media cÅ© cÃ³ `images` lÆ°u sai dáº¡ng chuá»—i `"[]"`, cÃ¡c sáº£n pháº©m thiáº¿u `image_url`, vÃ  cÃ¡c URL local trá» tá»›i file khÃ´ng tá»“n táº¡i trong thÆ° má»¥c public.
- Äá»“ng bá»™ fallback áº£nh tá»« sáº£n pháº©m cha xuá»‘ng cÃ¡c biáº¿n thá»ƒ active cÃ²n trá»‘ng áº£nh/gallery Ä‘á»ƒ trang chi tiáº¿t sáº£n pháº©m khÃ´ng bá»‹ máº¥t áº£nh khi chá»n biáº¿n thá»ƒ.

## Update 2026-06-23 - Seed thÃªm cÃ¡c Phá»¥ kiá»‡n cÃ´ng nghá»‡ sáº¡c Laptop cháº¥t lÆ°á»£ng cao

- Viáº¿t vÃ  thá»±c thi thÃ nh cÃ´ng script [seed_laptop_accessories.py](file:///c:/Users/Huynh%2520Nhu/Downloads/Project/backend/scripts/seed_laptop_accessories.py) Ä‘á»ƒ bá»• sung cÃ¡c sáº£n pháº©m phá»¥ kiá»‡n sáº¡c cao cáº¥p chuyÃªn dá»¥ng cho cÃ¡c dÃ²ng Laptop cá»§a cÃ¡c hÃ£ng:
  - **CÃ¡p sáº¡c siÃªu cÃ´ng suáº¥t**: CÃ¡p sáº¡c Ugreen USB-C to USB-C 240W 2m (chuáº©n PD 3.1 sáº¡c nhanh cho MacBook/Dell/HP/ThinkPad), CÃ¡p sáº¡c nhanh Anker 765 USB-C to USB-C 140W Nylon 1.8m.
  - **CÃ¡p sáº¡c MagSafe chuyÃªn dá»¥ng**: CÃ¡p sáº¡c Apple USB-C sang MagSafe 3 2m (chuyÃªn dá»¥ng cho Apple MacBook Pro vÃ  MacBook Air).
  - **Cá»§ sáº¡c laptop cÃ´ng suáº¥t cao**: Cá»§ sáº¡c nhanh Anker Prime 100W GaN 3 cá»•ng sáº¡c Ä‘á»“ng thá»i nhiá»u thiáº¿t bá»‹.
- Cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§ thÃ´ng sá»‘ ká»¹ thuáº­t (specifications), Ä‘a biáº¿n thá»ƒ mÃ u sáº¯c, tá»‘i Æ°u hÃ³a SEO.
- Khá»Ÿi táº¡o sá»‘ lÆ°á»£ng tá»“n kho Ä‘áº§y Ä‘á»§ trong báº£ng `inventory_levels` táº¡i kho máº·c Ä‘á»‹nh `MAIN`.
- Tá»± Ä‘á»™ng gÃ¡n cÃ¡c dá»‹ch vá»¥ báº£o hÃ nh phá»¥ kiá»‡n Ä‘i kÃ¨m phÃ¹ há»£p (`VIP-1D1-ACCESSORY-12M`, `S24-ACCESSORY-12M`) vÃ o báº£ng quan há»‡ `product_attached_services` vÃ  cáº­p nháº­t trÆ°á»ng JSONB `sales_config.attachedServices` trong báº£ng `products`.

## Update 2026-06-23 - Seed thÃªm 9 sáº£n pháº©m Camera an ninh, MÃ¡y áº£nh vÃ  Phá»¥ kiá»‡n má»›i

- Viáº¿t vÃ  thá»±c thi thÃ nh cÃ´ng script [seed_more_cameras_accessories.py](file:///c:/Users/Huynh%2520Nhu/Downloads/Project/backend/scripts/seed_more_cameras_accessories.py) Ä‘á»ƒ bá»• sung 9 sáº£n pháº©m cháº¥t lÆ°á»£ng cao thuá»™c cÃ¡c nhÃ³m:
  - **Camera an ninh**: Camera IP Wifi Ezviz C6N 1080p, Camera IP Wifi NgoÃ i Trá»i Imou Bullet 2C, Camera an ninh ngoÃ i trá»i xoay 360 Xiaomi AW300.
  - **MÃ¡y áº£nh**: Sony Alpha A6400 (KÃ¨m Lens 16-50mm), Canon EOS 1500D (KÃ¨m Lens 18-55mm), Fujifilm X-T30 II (Body).
  - **Phá»¥ kiá»‡n cÃ´ng nghá»‡**: Sáº¡c dá»± phÃ²ng Anker PowerCore Slim 10,000mAh PD 20W, Hub chuyá»ƒn Ä‘á»•i Ä‘a nÄƒng Ugreen 6-in-1 USB-C sang HDMI 4K, Cá»§ sáº¡c nhanh Baseus GaN6 Pro 45W.
- Cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§ thÃ´ng sá»‘ ká»¹ thuáº­t (specifications), Ä‘a biáº¿n thá»ƒ mÃ u sáº¯c, tá»‘i Æ°u hÃ³a SEO.
- Khá»Ÿi táº¡o sá»‘ lÆ°á»£ng tá»“n kho Ä‘áº§y Ä‘á»§ trong báº£ng `inventory_levels` táº¡i kho máº·c Ä‘á»‹nh `MAIN`.
- Tá»± Ä‘á»™ng gÃ¡n cÃ¡c dá»‹ch vá»¥ báº£o hÃ nh phá»¥ kiá»‡n Ä‘i kÃ¨m phÃ¹ há»£p (`VIP-1D1-ACCESSORY-12M`, `S24-ACCESSORY-12M`) vÃ o báº£ng quan há»‡ `product_attached_services` vÃ  cáº­p nháº­t trÆ°á»ng JSONB `sales_config.attachedServices` trong báº£ng `products`.

## Update 2026-06-23 - Seed thÃªm 15 sáº£n pháº©m cÃ´ng nghá»‡ Ä‘a dáº¡ng má»›i

- Viáº¿t vÃ  thá»±c thi thÃ nh cÃ´ng script [seed_15_more_products.py](file:///c:/Users/Huynh%2520Nhu/Downloads/Project/backend/scripts/seed_15_more_products.py) Ä‘á»ƒ bá»• sung 15 sáº£n pháº©m cÃ´ng nghá»‡ Ä‘a dáº¡ng thuá»™c cÃ¡c danh má»¥c Äá»“ng há»“ thÃ´ng minh, MÃ¡y tÃ­nh báº£ng, Äiá»‡n thoáº¡i vÃ  Camera tá»« cÃ¡c hÃ£ng Apple, Samsung, Xiaomi, Garmin, GoPro, DJI, Ezviz, realme, vivo.
- Cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§ cÃ¡c biáº¿n thá»ƒ mÃ u sáº¯c (variants) tÆ°Æ¡ng á»©ng, thiáº¿t láº­p thÃ´ng sá»‘ ká»¹ thuáº­t (specifications) chi tiáº¿t vÃ  tá»‘i Æ°u SEO.
- Khá»Ÿi táº¡o sá»‘ lÆ°á»£ng tá»“n kho Ä‘áº§y Ä‘á»§ cho tá»«ng biáº¿n thá»ƒ trong báº£ng `inventory_levels` táº¡i kho máº·c Ä‘á»‹nh `MAIN`.
- GÃ¡n tá»± Ä‘á»™ng cÃ¡c dá»‹ch vá»¥ báº£o hÃ nh Ä‘i kÃ¨m phÃ¹ há»£p theo danh má»¥c sáº£n pháº©m (sáº£n pháº©m di Ä‘á»™ng dÃ¹ng dá»‹ch vá»¥ báº£o hÃ nh di Ä‘á»™ng, camera/Ä‘á»“ Ä‘eo dÃ¹ng dá»‹ch vá»¥ báº£o hÃ nh phá»¥ kiá»‡n/Ä‘á»“ Ä‘eo tÆ°Æ¡ng á»©ng) vÃ o cáº£ báº£ng quan há»‡ `product_attached_services` vÃ  trÆ°á»ng JSONB `sales_config.attachedServices` trong báº£ng `products`.

## Update 2026-06-23 - Seed thÃªm 15 sáº£n pháº©m Phá»¥ kiá»‡n cÃ´ng nghá»‡ má»›i

- Viáº¿t vÃ  thá»±c thi thÃ nh cÃ´ng script [seed_15_accessories.py](file:///c:/Users/Huynh%2520Nhu/Downloads/Project/backend/scripts/seed_15_accessories.py) Ä‘á»ƒ bá»• sung 15 sáº£n pháº©m phá»¥ kiá»‡n cÃ´ng nghá»‡ cháº¥t lÆ°á»£ng cao (cÃ¡p sáº¡c Type-C/Lightning, sáº¡c nhanh GaN, sáº¡c khÃ´ng dÃ¢y MagSafe, tai nghe True Wireless, tai nghe chá»¥p tai, tai nghe gaming, sáº¡c dá»± phÃ²ng, bÃ n phÃ­m vÃ  chuá»™t gaming) tá»« cÃ¡c hÃ£ng Apple, Anker, Ugreen, Belkin, Mophie, Sony, JBL, Razer, Marshall.
- Cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§ cÃ¡c biáº¿n thá»ƒ mÃ u sáº¯c (variants) tÆ°Æ¡ng á»©ng, thiáº¿t láº­p thÃ´ng sá»‘ ká»¹ thuáº­t (specifications), cáº¥u hÃ¬nh tá»‘i Æ°u SEO.
- Khá»Ÿi táº¡o sá»‘ lÆ°á»£ng tá»“n kho Ä‘áº§y Ä‘á»§ cho tá»«ng biáº¿n thá»ƒ trong báº£ng `inventory_levels` táº¡i kho máº·c Ä‘á»‹nh `MAIN`.
- GÃ¡n sáºµn cÃ¡c dá»‹ch vá»¥ báº£o hÃ nh Ä‘i kÃ¨m phÃ¹ há»£p (`VIP-1D1-ACCESSORY-12M`, `S24-ACCESSORY-12M`) vÃ o cáº£ báº£ng quan há»‡ `product_attached_services` vÃ  trÆ°á»ng JSONB `sales_config.attachedServices` trong báº£ng `products`.

## Update 2026-06-23 - GÃ¡n tá»± Ä‘á»™ng dá»‹ch vá»¥ Ä‘i kÃ¨m cho toÃ n bá»™ sáº£n pháº©m

- Viáº¿t vÃ  cháº¡y script `backend/scripts/seed_product_services.py` Ä‘á»ƒ tá»± Ä‘á»™ng gÃ¡n cÃ¡c dá»‹ch vá»¥ Ä‘i kÃ¨m (attached services) phÃ¹ há»£p cho toÃ n bá»™ 64 sáº£n pháº©m Ä‘ang kinh doanh.
- PhÃ¢n loáº¡i sáº£n pháº©m theo danh má»¥c (`Äiá»‡n thoáº¡i`, `MÃ¡y tÃ­nh báº£ng`, `MÃ¡y tÃ­nh xÃ¡ch tay`, `Phá»¥ kiá»‡n cÃ´ng nghá»‡`, `Äá»“ng há»“ thÃ´ng minh`, `Camera`, `MÃ¡y áº£nh`) Ä‘á»ƒ gÃ¡n cÃ¡c dá»‹ch vá»¥ báº£o hÃ nh má»Ÿ rá»™ng, báº£o hÃ nh 1 Ä‘á»•i 1 VIP, dÃ¡n cÆ°á»ng lá»±c, sao lÆ°u dá»¯ liá»‡u, cÃ i Ä‘áº·t tá»‘i Æ°u há»‡ thá»‘ng, nÃ¢ng cáº¥p pháº§n cá»©ng vÃ  vá»‡ sinh mÃ¡y.
- Quy táº¯c gÃ¡n Ä‘áº£m báº£o tÃ­nh duy nháº¥t theo nhÃ³m thuá»™c tÃ­nh (`attribute_group` / unique service group) Ä‘á»ƒ khÃ´ng xáº£y ra xung Ä‘á»™t khi khÃ¡ch hÃ ng lá»±a chá»n dá»‹ch vá»¥ á»Ÿ giá» hÃ ng vÃ  checkout.
- Äá»“ng bá»™ hÃ³a cÃ¡c báº£n ghi trong báº£ng quan há»‡ `product_attached_services` Ä‘á»“ng thá»i cáº­p nháº­t trÆ°á»ng JSONB `sales_config.attachedServices` trong báº£ng `products`.

## Update 2026-06-20 - Chá»‘ng trÃ¹ng lá»‹ch vÃ  Æ°u tiÃªn Flash Sale biáº¿n thá»ƒ

- API cháº·n táº¡o hoáº·c cáº­p nháº­t hai Flash Sale `ACTIVE` chá»“ng thá»i gian cho cÃ¹ng má»™t target: cÃ¹ng toÃ n sáº£n pháº©m hoáº·c cÃ¹ng má»™t biáº¿n thá»ƒ.
- Flash Sale toÃ n sáº£n pháº©m vÃ  Flash Sale biáº¿n thá»ƒ Ä‘Æ°á»£c phÃ©p cÃ¹ng hiá»‡u lá»±c; khi tÃ­nh giÃ¡ cho biáº¿n thá»ƒ, chÆ°Æ¡ng trÃ¬nh riÃªng cá»§a biáº¿n thá»ƒ luÃ´n Æ°u tiÃªn, sau Ä‘Ã³ má»›i fallback vá» chÆ°Æ¡ng trÃ¬nh toÃ n sáº£n pháº©m.
- PostgreSQL dÃ¹ng hai exclusion constraint trÃªn `tstzrange(..., '[)')` Ä‘á»ƒ chá»‘ng race condition khi nhiá»u admin lÆ°u Ä‘á»“ng thá»i; thá»i gian Ä‘á»ƒ trá»‘ng Ä‘Æ°á»£c hiá»ƒu lÃ  biÃªn vÃ´ háº¡n.
- Lá»—i xung Ä‘á»™t tá»« validation hoáº·c database Ä‘á»u Ä‘Æ°á»£c tráº£ vá» dáº¡ng HTTP `409` vá»›i thÃ´ng bÃ¡o tiáº¿ng Viá»‡t rÃµ rÃ ng.
- Metadata thá»i gian Flash Sale trong JSON biáº¿n thá»ƒ Ä‘Æ°á»£c chuáº©n hÃ³a cho cáº£ giÃ¡ trá»‹ `datetime` vÃ  chuá»—i ISO tá»« PostgreSQL JSON aggregation, trÃ¡nh lá»—i 500 khi catalog Ä‘á»c Flash Sale riÃªng cá»§a biáº¿n thá»ƒ.
- Má»—i tháº» sáº£n pháº©m Ä‘ang Flash Sale hiá»ƒn thá»‹ Ä‘á»“ng há»“ Ä‘áº¿m ngÆ°á»£c riÃªng theo `endsAt` cá»§a chÆ°Æ¡ng trÃ¬nh thá»±c táº¿ Ä‘ang Ã¡p dá»¥ng, bao gá»“m cáº£ trÆ°á»ng há»£p Flash Sale riÃªng cá»§a biáº¿n thá»ƒ.
- NhÃ£n trÃªn tháº» Flash Sale hiá»ƒn thá»‹ trá»±c tiáº¿p má»©c Æ°u Ä‘Ã£i theo cáº¥u hÃ¬nh: `Giáº£m X%` hoáº·c `Giáº£m XÄ‘`.

## Update 2026-06-20 - Flash Sale theo tá»«ng biáº¿n thá»ƒ

- `flash_sales` há»— trá»£ `variant_id` nullable: Ä‘á»ƒ trá»‘ng Ã¡p dá»¥ng toÃ n bá»™ sáº£n pháº©m, cÃ³ giÃ¡ trá»‹ chá»‰ giáº£m giÃ¡ biáº¿n thá»ƒ Ä‘Ã£ chá»n.
- Backend kiá»ƒm tra biáº¿n thá»ƒ thuá»™c Ä‘Ãºng sáº£n pháº©m vÃ  tÃ­nh giÃ¡ Flash Sale theo giÃ¡ hiá»‡n táº¡i cá»§a biáº¿n thá»ƒ.
- Catalog tráº£ metadata Flash Sale riÃªng trong tá»«ng biáº¿n thá»ƒ; Flash Sale toÃ n sáº£n pháº©m váº«n Ã¡p dá»¥ng cho toÃ n bá»™ biáº¿n thá»ƒ nhÆ° trÆ°á»›c.
- Tháº» sáº£n pháº©m cÃ³ Flash Sale riÃªng theo biáº¿n thá»ƒ gáº¯n `?variant=<id>` vÃ o Ä‘Æ°á»ng dáº«n; trang chi tiáº¿t tá»± chá»n Ä‘Ãºng biáº¿n thá»ƒ vÃ  hiá»ƒn thá»‹ khá»‘i Flash Sale ná»•i báº­t.
- Popup quáº£n trá»‹ cÃ³ thÃªm lá»±a chá»n pháº¡m vi `ToÃ n bá»™ sáº£n pháº©m` hoáº·c má»™t biáº¿n thá»ƒ cá»¥ thá»ƒ sau khi chá»n sáº£n pháº©m.

## Update 2026-06-20 - Storefront Flash Sale countdown and dedicated listing

- Khá»‘i Flash Sale á»Ÿ trang chá»§ hiá»ƒn thá»‹ Ä‘á»“ng há»“ Ä‘áº¿m ngÆ°á»£c ná»•i báº­t theo chÆ°Æ¡ng trÃ¬nh Ä‘ang hoáº¡t Ä‘á»™ng cÃ³ thá»i gian káº¿t thÃºc gáº§n nháº¥t.
- NÃºt `Xem táº¥t cáº£` vÃ  lá»‘i táº¯t Flash Sale trÃªn menu Ä‘iá»u hÆ°á»›ng tá»›i trang riÃªng `/flash-sale`.
- Trang Flash Sale chá»‰ táº£i cÃ¡c sáº£n pháº©m Ä‘ang cÃ³ chÆ°Æ¡ng trÃ¬nh Flash Sale hiá»‡u lá»±c qua bá»™ lá»c public API `flash_sale=true`, khÃ´ng cÃ²n má»Ÿ danh sÃ¡ch sáº£n pháº©m thÃ´ng thÆ°á»ng.
- Bá»™ lá»c public API khÃ´ng cÃ²n dá»±a vÃ o cá» `products.is_flash_sale` cÅ©; sáº£n pháº©m chá»‰ Ä‘Æ°á»£c xem lÃ  Ä‘ang Flash Sale khi cÃ³ báº£n ghi chÆ°Æ¡ng trÃ¬nh active vÃ  cÃ²n trong khoáº£ng `starts_at` Ä‘áº¿n `ends_at`.

## Update 2026-06-20 - Má»Ÿ rá»™ng danh sÃ¡ch chá»n sáº£n pháº©m Flash Sale

- Popup táº¡o/sá»­a Flash Sale táº£i tá»‘i Ä‘a 200 sáº£n pháº©m thay vÃ¬ chá»‰ dÃ¹ng 20 sáº£n pháº©m Ä‘áº§u tiÃªn tá»« API admin.
- Bá» giá»›i háº¡n hiá»ƒn thá»‹ 8 káº¿t quáº£ trong Ã´ chá»n; toÃ n bá»™ káº¿t quáº£ phÃ¹ há»£p cÃ³ thá»ƒ cuá»™n vÃ  tÃ¬m theo tÃªn, SKU hoáº·c thÆ°Æ¡ng hiá»‡u.
- ThÃªm sá»‘ lÆ°á»£ng sáº£n pháº©m phÃ¹ há»£p ngay trÃªn danh sÃ¡ch Ä‘á»ƒ admin biáº¿t pháº¡m vi tÃ¬m kiáº¿m hiá»‡n táº¡i.

## Update 2026-06-19 - Flash Sale cho sáº£n pháº©m bÃ¡n kÃ¨m vÃ  bá»™ lá»c quáº£n trá»‹

- Sáº£n pháº©m chÃ­nh tiáº¿p tá»¥c dÃ¹ng giÃ¡ Flash Sale cá»§a chÃ­nh nÃ³ khi chÆ°Æ¡ng trÃ¬nh Ä‘ang hiá»‡u lá»±c.
- Sáº£n pháº©m bÃ¡n kÃ¨m nay cÅ©ng láº¥y giÃ¡ Flash Sale Ä‘ang hiá»‡u lá»±c cá»§a chÃ­nh sáº£n pháº©m bÃ¡n kÃ¨m trÆ°á»›c, sau Ä‘Ã³ má»›i Ã¡p dá»¥ng má»©c giáº£m mua kÃ¨m Ä‘Ã£ cáº¥u hÃ¬nh.
- MÃ n quáº£n trá»‹ Flash Sale cÃ³ thÃªm bá»™ lá»c danh má»¥c, thÆ°Æ¡ng hiá»‡u, tráº¡ng thÃ¡i vÃ  Ã´ tÃ¬m riÃªng trong popup chá»n sáº£n pháº©m theo tÃªn, SKU hoáº·c thÆ°Æ¡ng hiá»‡u.
- Tab Flash Sale táº£i kÃ¨m dá»¯ liá»‡u danh má»¥c vÃ  thÆ°Æ¡ng hiá»‡u Ä‘á»ƒ dropdown khÃ´ng cÃ²n chá»‰ hiá»ƒn thá»‹ lá»±a chá»n máº·c Ä‘á»‹nh; vÃ¹ng lá»c Ä‘Æ°á»£c Æ°u tiÃªn lá»›p hiá»ƒn thá»‹ Ä‘á»ƒ menu khÃ´ng bá»‹ láº«n vá»›i tiÃªu Ä‘á» báº£ng.
- Popup táº¡o/sá»­a Flash Sale gá»™p tÃ¬m kiáº¿m vÃ  chá»n sáº£n pháº©m thÃ nh má»™t danh sÃ¡ch trá»±c quan, hiá»ƒn thá»‹ áº£nh, tÃªn, SKU, thÆ°Æ¡ng hiá»‡u vÃ  tráº¡ng thÃ¡i Ä‘ang chá»n; giá»›i háº¡n 8 káº¿t quáº£ má»—i láº§n tÃ¬m Ä‘á»ƒ thao tÃ¡c nhanh vÃ  gá»n.

## Update 2026-06-18 - Consolidate database migrations

- Gá»™p toÃ n bá»™ migration cÅ© tá»« `036` Ä‘áº¿n `073` vÃ o `backend/migrations/init_database.sql`.
- ThÆ° má»¥c migration chá»‰ cÃ²n baseline hoÃ n chá»‰nh; migration má»›i báº¯t Ä‘áº§u láº¡i tá»« `001_*.sql`.
- `scripts/run_migrations.py` tá»± phÃ¡t hiá»‡n cÃ¡c file migration tÄƒng dáº§n, khÃ´ng cÃ²n pháº£i cáº­p nháº­t danh sÃ¡ch cá»‘ Ä‘á»‹nh.
- Quy Æ°á»›c táº¡o migration má»›i náº±m táº¡i `backend/migrations/README.md`.

## Update 2026-06-16 cleanup stale REV products from inventory

- Dá»n dá»¯ liá»‡u local cÃ²n sÃ³t tá»« luá»“ng duyá»‡t revision cÅ©: cÃ¡c sáº£n pháº©m SKU `REV-%` tráº¡ng thÃ¡i `MERGED`/`ARCHIVED` khÃ´ng cÃ²n Ä‘Æ°á»£c giá»¯ trong báº£ng `products` nhÆ° sáº£n pháº©m nghiá»‡p vá»¥ hiá»‡n hÃ nh.
- TrÆ°á»›c khi xÃ³a Ä‘Ã£ xÃ¡c nháº­n cÃ¡c báº£n `REV-%` khÃ´ng cÃ³ Ä‘Æ¡n hÃ ng, bundle/accessory, reservation hoáº·c transaction bÃ¡n hÃ ng tham chiáº¿u.
- Viá»‡c dá»n dá»¯ liá»‡u loáº¡i bá» cÃ¡c báº£n revision khá»i tá»“n kho khá»Ÿi táº¡o Ä‘á»ƒ phiáº¿u nháº­p kho vÃ  bÃ¡o cÃ¡o tá»“n kho chá»‰ tÃ­nh sáº£n pháº©m tháº­t.
- LÆ°u Ã½ nghiá»‡p vá»¥ váº«n giá»¯ nguyÃªn theo cáº­p nháº­t 2026-06-08: lá»‹ch sá»­ duyá»‡t revision náº±m á»Ÿ audit trail, khÃ´ng dÃ¹ng sáº£n pháº©m `REV-%` lÃ m báº£n ghi cÃ²n tháº¥y trong catalog/tá»“n kho.

## Update 2026-06-16 inventory receipt guard for product lifecycle

- Module nháº­p kho nay kiá»ƒm tra vÃ²ng Ä‘á»i sáº£n pháº©m trÆ°á»›c khi cho táº¡o/sá»­a phiáº¿u nháº­p: chá»‰ sáº£n pháº©m `ACTIVE`, chÆ°a xÃ³a vÃ  khÃ´ng bá»‹ áº©n má»›i Ä‘Æ°á»£c nháº­p.
- Sáº£n pháº©m Ä‘ang ngá»«ng kinh doanh (`DISCONTINUED`) hoáº·c cÃ³ báº£n chá»‰nh sá»­a `REVISION_DRAFT`/`PENDING` theo `parent_product_id` sáº½ bá»‹ cháº·n nháº­p kho cho Ä‘áº¿n khi Ä‘Æ°á»£c duyá»‡t hoáº·c há»§y báº£n chá»‰nh sá»­a.
- RÃ ng buá»™c nÃ y giÃºp trÃ¡nh nháº­p tá»“n cho dá»¯ liá»‡u sáº£n pháº©m chÆ°a á»•n Ä‘á»‹nh hoáº·c khÃ´ng cÃ²n kinh doanh, Ä‘á»“ng bá»™ vá»›i quy táº¯c revision khÃ´ng Ä‘Æ°á»£c xem nhÆ° sáº£n pháº©m tháº­t.

## Update 2026-06-15 storefront product detail Q&A section

- ThÃªm component `ProductQuestions` cho trang chi tiáº¿t sáº£n pháº©m Ä‘á»ƒ hiá»ƒn thá»‹ vÃ  gá»­i há»i Ä‘Ã¡p sáº£n pháº©m báº±ng cÃ¡c API cÃ´ng khai `/products/{product_id}/questions` Ä‘Ã£ cÃ³.
- Q&A há»— trá»£ mÃ´ hÃ¬nh 2 táº§ng: cÃ¢u há»i gá»‘c vÃ  pháº£n há»“i, cÃ³ optimistic update khi gá»­i, tráº¡ng thÃ¡i lá»—i khi gá»­i tháº¥t báº¡i vÃ  thao tÃ¡c thu há»“i ná»™i dung qua API hiá»‡n cÃ³.
- NÃºt `Há»i Ä‘Ã¡p` trÃªn header chi tiáº¿t sáº£n pháº©m nay trá» tá»›i anchor `#product-questions` thay vÃ¬ khu Ä‘Ã¡nh giÃ¡.

## Update 2026-06-13 primary and supplemental IMEI support

- Bá»• sung mÃ´ hÃ¬nh IMEI chÃ­nh/phá»¥ á»Ÿ táº§ng tá»“n kho: má»™t sáº£n pháº©m hoáº·c biáº¿n thá»ƒ cÃ³ thá»ƒ cÃ³ nhiá»u IMEI, trong Ä‘Ã³ Ä‘Ãºng má»™t IMEI Ä‘Æ°á»£c Ä‘Ã¡nh dáº¥u chÃ­nh.
- Khi nháº­p kho nhiá»u IMEI, há»‡ thá»‘ng láº¥y IMEI Ä‘áº§u tiÃªn lÃ m IMEI chÃ­nh náº¿u sáº£n pháº©m/biáº¿n thá»ƒ chÆ°a cÃ³ IMEI chÃ­nh; cÃ¡c IMEI cÃ²n láº¡i lÃ  IMEI bá»• sung.
- Báº£ng tá»“n kho admin hiá»ƒn thá»‹ `IMEI chÃ­nh`, sá»‘ IMEI phá»¥ vÃ  tá»•ng tráº¡ng thÃ¡i IMEI Ä‘á»ƒ quáº£n trá»‹ viÃªn kiá»ƒm tra nhanh.
- Migration liÃªn quan: `backend/migrations/061_product_imei_primary.sql`.

## Update 2026-06-13 product-level serial number policy

- Bá»• sung cáº¥u hÃ¬nh `Quáº£n lÃ½ serial number` trong form sáº£n pháº©m, song song vá»›i `Quáº£n lÃ½ IMEI`.
- Cáº¥u hÃ¬nh Ä‘Æ°á»£c lÆ°u trong `products.sales_config.serialPolicy` vá»›i hai cháº¿ Ä‘á»™ `CATEGORY` vÃ  `MANUAL`; khi `MANUAL`, sáº£n pháº©m cÃ³ thá»ƒ tá»± báº­t/táº¯t quáº£n lÃ½ serial number Ä‘á»™c láº­p vá»›i danh má»¥c.
- Sáº£n pháº©m hiá»‡n cÃ³ thá»ƒ rÆ¡i vÃ o cÃ¡c tá»• há»£p: quáº£n lÃ½ cáº£ IMEI vÃ  serial number, chá»‰ quáº£n lÃ½ IMEI, chá»‰ quáº£n lÃ½ serial number hoáº·c khÃ´ng quáº£n lÃ½ mÃ£ Ä‘á»‹nh danh.

## Update 2026-06-10 iPad A16 Wifi video content draft

- Táº¡o script `backend/scripts/seed_ipad_a16_wifi_video_content.py` Ä‘á»ƒ táº¡o hoáº·c cáº­p nháº­t ná»™i dung video nhÃ¡p cho sáº£n pháº©m `iPad A16 Wifi` (SKU `IPADA16`).
- Ná»™i dung video táº­p trung vÃ o mÃ n hÃ¬nh Liquid Retina 10.9 inch, chip Apple A16 Bionic, Apple Pencil USB-C, Touch ID, camera trÆ°á»›c/sau 12MP, loa stereo vÃ  cÃ¡c phiÃªn báº£n A16 Wifi/5G.
- Script gáº¯n video vá»›i sáº£n pháº©m vÃ  cÃ¡c danh má»¥c liÃªn quan qua `content_product_relations` vÃ  `content_category_relations`; video Ä‘Æ°á»£c Ä‘á»ƒ `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- ÄÃ£ cháº¡y script trÃªn DB local, táº¡o/cáº­p nháº­t video ID `f52656f6-6376-4ba0-b254-04f8c5491719`.

## Update 2026-06-10 Samsung Galaxy S26 Ultra video content draft

- Táº¡o script `backend/scripts/seed_samsung_galaxy_s26_ultra_video_content.py` Ä‘á»ƒ táº¡o hoáº·c cáº­p nháº­t ná»™i dung video nhÃ¡p cho sáº£n pháº©m `Samsung Galaxy S26 Ultra` (SKU `S26U`).
- Ná»™i dung video táº­p trung vÃ o khung Titanium, mÃ n hÃ¬nh Dynamic AMOLED 2X QHD+ 1-120Hz, Galaxy AI, S Pen tÃ­ch há»£p, camera 200MP/Space Zoom 100x, Snapdragon 8 Elite Gen 5 for Galaxy, Samsung DeX, Knox Security, pin 5000 mAh vÃ  sáº¡c nhanh 60W.
- Script gáº¯n video vá»›i sáº£n pháº©m vÃ  cÃ¡c danh má»¥c liÃªn quan qua `content_product_relations` vÃ  `content_category_relations`; video Ä‘Æ°á»£c Ä‘á»ƒ `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- ÄÃ£ cháº¡y script trÃªn DB local, táº¡o/cáº­p nháº­t video ID `d7ebad55-33ca-42e7-9cb6-2464593a1e68`.

## Update 2026-06-10 admin product image deletion persistence

- Sá»­a lá»—i trong mÃ n quáº£n trá»‹ sáº£n pháº©m: sau khi xÃ³a toÃ n bá»™ `áº¢nh Ä‘áº¡i diá»‡n chung` vÃ  `Bá»™ áº£nh sáº£n pháº©m chung`, lÆ°u xong má»Ÿ láº¡i váº«n tháº¥y áº£nh cÅ© Ä‘á»‘i vá»›i cÃ¡c SKU cÃ³ áº£nh demo.
- NguyÃªn nhÃ¢n: `adminProductsApi.adminListProducts` dÃ¹ng chung `formatProductDemoData`, hÃ m nÃ y tá»± gÃ¡n áº£nh demo theo SKU vÃ  ghi Ä‘Ã¨ dá»¯ liá»‡u `imageUrl`/`images` tháº­t tá»« backend, lÃ m tráº¡ng thÃ¡i `NULL`/`[]` sau khi xÃ³a bá»‹ hiá»ƒn thá»‹ nhÆ° chÆ°a xÃ³a.
- ThÃªm `formatProductAdminMedia` Ä‘á»ƒ mÃ n admin chá»‰ chuáº©n hÃ³a URL áº£nh tá»« backend, khÃ´ng tá»± fallback áº£nh demo theo SKU. Storefront/public API váº«n giá»¯ `formatProductDemoData`.

## Update 2026-06-10 published product image override fix

- Sá»­a tiáº¿p lá»—i sau khi duyá»‡t báº£n chá»‰nh sá»­a: backend Ä‘Ã£ publish `image_url` vÃ  `images` tá»« `REVISION_DRAFT` sang sáº£n pháº©m gá»‘c, nhÆ°ng storefront/public API váº«n hiá»ƒn thá»‹ áº£nh cÅ© do `formatProductDemoData` ghi Ä‘Ã¨ áº£nh tháº­t báº±ng báº£ng áº£nh demo theo SKU.
- XÃ³a báº£ng fallback áº£nh demo theo SKU khá»i `productMedia.ts`; cáº£ admin vÃ  public formatter nay chá»‰ chuáº©n hÃ³a URL tá»« dá»¯ liá»‡u backend. VÃ¬ váº­y áº£nh má»›i, áº£nh Ä‘Ã£ xÃ³a vÃ  gallery rá»—ng sau duyá»‡t Ä‘á»u Ä‘Æ°á»£c giá»¯ nguyÃªn khi hiá»ƒn thá»‹.

## Update 2026-06-10 batch product image galleries

- ThÃªm script `backend/scripts/update_batch_product_images.py` Ä‘á»ƒ copy áº£nh ngÆ°á»i dÃ¹ng cung cáº¥p vÃ o `frontend/public/images/products/` theo cáº¥u trÃºc URL á»•n Ä‘á»‹nh `cover.*` vÃ  `gallery-xx.*`.
- Script nháº­n diá»‡n áº£nh Ä‘áº¡i diá»‡n theo tÃªn file cÃ³ chá»©a biáº¿n thá»ƒ cá»§a `áº£nh Ä‘áº¡i diá»‡n`/`áº£nh Ä‘á»‹a diá»‡n`; cÃ¡c áº£nh cÃ²n láº¡i Ä‘Æ°á»£c Ä‘Æ°a vÃ o gallery.
- ÄÃ£ cáº­p nháº­t `products.image_url`, `products.images`, `product_variants.image_url` vÃ  `product_variants.images` cho cÃ¡c sáº£n pháº©m: AirPods Pro 2 USB-C, Apple Watch Ultra 2, iPad A16 Wifi, iPad Pro M4 11 inch, MacBook Air M3 13 inch, MacBook Neo 13 inch A18 Pro 2026, Samsung Galaxy A17 5G, Samsung Galaxy A57 5G, Samsung Galaxy S26 vÃ  Samsung Galaxy S26 Ultra.
- CÃ¡c thÆ° má»¥c khÃ´ng phÃ¢n mÃ u Ä‘Æ°á»£c gáº¯n áº£nh dÃ¹ng chung cho toÃ n bá»™ biáº¿n thá»ƒ active; cÃ¡c thÆ° má»¥c phÃ¢n mÃ u Ä‘Æ°á»£c map theo `color_name` trong database.
- LÆ°u Ã½: thÆ° má»¥c `Samsung Galaxy A57 5G/Äen` Ä‘Ã£ Ä‘Æ°á»£c copy vÃ o public assets nhÆ°ng khÃ´ng gáº¯n vÃ o biáº¿n thá»ƒ vÃ¬ DB hiá»‡n khÃ´ng cÃ³ biáº¿n thá»ƒ active mÃ u Äen cho sáº£n pháº©m nÃ y.

## Update 2026-06-10 Samsung Galaxy S26 Ultra color variants update

- Cáº­p nháº­t tÃªn mÃ u sáº¯c cho Samsung Galaxy S26 Ultra (SKU: `S26U`) theo yÃªu cáº§u:
  - Äá»•i `Äen Titan` (#2f3133) â†’ `Äen Classic`
  - Äá»•i `Tráº¯ng Titan` (#f1f0ee) â†’ `Tráº¯ng Classic`
  - Äá»•i `Xanh ThiÃªn Thanh` (#9ebed2) â†’ `Xanh Sky Blue` (#87ceeb)
  - ThÃªm má»›i `TÃ­m Cobalt` (#726b8e)
- ThÃªm 3 biáº¿n thá»ƒ má»›i cho mÃ u `TÃ­m Cobalt`:
  - `S26U-CV-256GB`: 12GB RAM, 256GB, giÃ¡ 33.990.000Ä‘ (sale 31.990.000Ä‘)
  - `S26U-CV-512GB`: 12GB RAM, 512GB, giÃ¡ 37.990.000Ä‘ (sale 35.990.000Ä‘)
  - `S26U-CV-1TB`: 16GB RAM, 1TB, giÃ¡ 44.990.000Ä‘ (sale 42.990.000Ä‘)
- Cáº­p nháº­t `color_name`, `color_code` vÃ  `attributes` JSON trong 9 biáº¿n thá»ƒ cÅ©.
- Tá»•ng biáº¿n thá»ƒ hiá»‡n táº¡i: 12 (4 mÃ u Ã— 3 dung lÆ°á»£ng).
- Script: `backend/scripts/update_s26u_colors.py`.

## Update 2026-06-10 Samsung Galaxy S26 color variants update

- Cáº­p nháº­t tÃªn mÃ u sáº¯c cho Samsung Galaxy S26 (SKU: `S26`) theo yÃªu cáº§u:
  - Äá»•i `Äen` (#1a1a1a) â†’ `Äen Classic`
  - Äá»•i `Tráº¯ng` (#fdfdfd) â†’ `Tráº¯ng Classic`
  - Giá»¯ nguyÃªn `TÃ­m Cobalt` (#726b8e)
  - ThÃªm má»›i `Xanh Sky Blue` (#87ceeb)
- ThÃªm 2 biáº¿n thá»ƒ má»›i cho mÃ u `Xanh Sky Blue`:
  - `S26-SB-256GB`: 12GB RAM, 256GB, giÃ¡ 22.990.000Ä‘ (sale 21.990.000Ä‘)
  - `S26-SB-512GB`: 12GB RAM, 512GB, giÃ¡ 26.990.000Ä‘ (sale 25.990.000Ä‘)
- Cáº­p nháº­t `color_name` vÃ  `attributes` JSON trong 4 biáº¿n thá»ƒ cÅ© (BK, WH) Ä‘á»ƒ Ä‘á»“ng bá»™ tÃªn má»›i.
- Cáº­p nháº­t `products.colors` vÃ  `products.options` vá»›i 4 mÃ u má»›i.
- Cáº­p nháº­t seed data trong `init_database.sql` dÃ²ng sáº£n pháº©m S26.
- Tá»•ng biáº¿n thá»ƒ hiá»‡n táº¡i: 8 (4 mÃ u Ã— 2 dung lÆ°á»£ng).
- Script: `backend/scripts/update_s26_colors.py`.

## Update 2026-06-10 OPPO Find X9 Ultra video content draft

- Táº¡o script `backend/scripts/seed_oppo_find_x9_ultra_video_content.py` Ä‘á»ƒ táº¡o hoáº·c cáº­p nháº­t ná»™i dung video nhÃ¡p cho sáº£n pháº©m `OPPO Find X9 Ultra` (SKU `OP-FX9U`).
- Ná»™i dung video táº­p trung vÃ o máº·t lÆ°ng da sinh thÃ¡i, mÃ n hÃ¬nh LTPO AMOLED QHD+ 144Hz, há»‡ thá»‘ng camera Hasselblad Ä‘a tiÃªu cá»±, quay video 8K/4K, pin 7050 mAh, sáº¡c nhanh 100W vÃ  chuáº©n IP68/IP69.
- Script gáº¯n video vá»›i sáº£n pháº©m vÃ  cÃ¡c danh má»¥c liÃªn quan qua `content_product_relations` vÃ  `content_category_relations`; video Ä‘Æ°á»£c Ä‘á»ƒ `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- ÄÃ£ cháº¡y script trÃªn DB local, táº¡o/cáº­p nháº­t video ID `ecde02d4-a756-472a-be50-c2d42cd70b27`.

## Update 2026-06-10 MacBook Neo A18 Pro video content draft

- Táº¡o script `backend/scripts/seed_macbook_neo_a18_pro_video_content.py` Ä‘á»ƒ táº¡o hoáº·c cáº­p nháº­t ná»™i dung video nhÃ¡p cho sáº£n pháº©m `MacBook Neo 13 inch A18 Pro 2026` (SKU `MBNEOA18P`).
- Ná»™i dung video táº­p trung vÃ o thiáº¿t káº¿ 13 inch gá»n nháº¹, mÃ u sáº¯c tráº» trung, chip Apple A18 Pro, mÃ n hÃ¬nh Liquid Retina, pin dÃ i, Magic Keyboard vá»›i Touch ID vÃ  nhu cáº§u há»c táº­p/vÄƒn phÃ²ng linh hoáº¡t.
- Script gáº¯n video vá»›i sáº£n pháº©m vÃ  cÃ¡c danh má»¥c liÃªn quan qua `content_product_relations` vÃ  `content_category_relations`; video Ä‘Æ°á»£c Ä‘á»ƒ `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- ÄÃ£ cháº¡y script trÃªn DB local, táº¡o/cáº­p nháº­t video ID `1bcbcc60-e15c-4aaf-8085-1dd50882fe8b`.

## Update 2026-06-10 MacBook Air M3 video content draft

- Táº¡o script `backend/scripts/seed_macbook_air_m3_video_content.py` Ä‘á»ƒ táº¡o hoáº·c cáº­p nháº­t ná»™i dung video nhÃ¡p cho sáº£n pháº©m `MacBook Air M3 13 inch` (SKU `MBAIRM3`).
- Ná»™i dung video táº­p trung vÃ o thiáº¿t káº¿ má»ng nháº¹, chip M3, mÃ n hÃ¬nh Liquid Retina 13.6 inch, thá»i lÆ°á»£ng pin dÃ i vÃ  nhu cáº§u há»c táº­p/vÄƒn phÃ²ng/sÃ¡ng táº¡o nháº¹.
- Script gáº¯n video vá»›i sáº£n pháº©m vÃ  cÃ¡c danh má»¥c liÃªn quan qua `content_product_relations` vÃ  `content_category_relations`; video Ä‘Æ°á»£c Ä‘á»ƒ `status = 'DRAFT'`, `is_active = FALSE`, `video_source = 'UPLOAD'`.
- ÄÃ£ cháº¡y script trÃªn DB local, táº¡o/cáº­p nháº­t video ID `be2b41a3-f30a-4e0d-af16-8232edc84370`.

## Update 2026-06-08 product comments and Q&A management split

- TÃ¡ch báº£ng bÃ¬nh luáº­n hÃ¬nh áº£nh sáº£n pháº©m khá»i tab `Dá»‹ch vá»¥`; admin cÃ³ tab riÃªng `BÃ¬nh luáº­n & há»i Ä‘Ã¡p` Ä‘á»ƒ quáº£n lÃ½ bÃ¬nh luáº­n vui vÃ  há»i Ä‘Ã¡p sáº£n pháº©m.
- Bá»• sung cá»™t `product_image_comments.interaction_type`, máº·c Ä‘á»‹nh dá»¯ liá»‡u cÅ© lÃ  `IMAGE_COMMENT`; Q&A dÃ¹ng `PRODUCT_QA` nhÆ°ng váº«n chung cÆ¡ cháº¿ kiá»ƒm duyá»‡t/áº©n/thu há»“i/pháº£n há»“i.
- ThÃªm API cÃ´ng khai `/products/{product_id}/questions` Ä‘á»ƒ liá»‡t kÃª, gá»­i vÃ  thu há»“i há»i Ä‘Ã¡p sáº£n pháº©m.
- Giá»¯ rÃ ng buá»™c nghiá»‡p vá»¥ 2 táº§ng: náº¿u ngÆ°á»i dÃ¹ng hoáº·c admin tráº£ lá»i má»™t pháº£n há»“i con, backend kÃ©o `parent_id` vá» cÃ¢u/cmt gá»‘c, khÃ´ng sinh táº§ng thá»© 3.

## Update 2026-06-08 product approval final status parameter fix

- Sá»­a lá»—i duyá»‡t báº£n chá»‰nh sá»­a sáº£n pháº©m tráº£ 500 do cÃ¢u SQL cáº­p nháº­t sáº£n pháº©m gá»‘c dÃ¹ng `:final_status` nhÆ°ng repository chÆ°a truyá»n tham sá»‘ nÃ y vÃ o Ä‘Ãºng lá»‡nh `execute`.
- Bá» tham sá»‘ `final_status` thá»«a khá»i cÃ¢u insert phá»¥ kiá»‡n bÃ¡n kÃ¨m trong cÃ¹ng nhÃ¡nh publish revision.

## Update 2026-06-07 admin product submit button layout

- Sá»­a nÃºt submit dÃ¹ng chung trong form admin Ä‘á»ƒ nhÃ£n `LÆ°u`/`ThÃªm` hiá»ƒn thá»‹ Ä‘Ãºng Unicode vÃ  khÃ´ng bá»‹ xuá»‘ng dÃ²ng hoáº·c co chá»¯ khi vÃ¹ng hiá»ƒn thá»‹ háº¹p.
- `SubmitButtons` nay giá»¯ nguyÃªn dÃ²ng báº±ng `whitespace-nowrap`, khÃ´ng co nÃºt/icon báº±ng `shrink-0`, giÃºp nÃºt trong popup quáº£n lÃ½ sáº£n pháº©m khÃ´ng cÃ²n bá»‹ vá»¡ chá»¯.
- Bá»• sung cÃ¹ng nguyÃªn táº¯c chá»‘ng xuá»‘ng dÃ²ng cho nÃºt má»Ÿ popup `ThÃªm` trong `CollapsibleSection`.

## Update 2026-06-08 admin product brand selection

- Bá» Ã´ `ThÆ°Æ¡ng hiá»‡u nháº­p tay` trong form thÃªm/sá»­a sáº£n pháº©m Ä‘á»ƒ trÃ¡nh lÆ°u thÆ°Æ¡ng hiá»‡u khÃ´ng tá»“n táº¡i trong báº£ng brands.
- TrÆ°á»ng `ThÆ°Æ¡ng hiá»‡u` trong form sáº£n pháº©m nay lÃ  combobox cÃ³ Ã´ tÃ¬m kiáº¿m: báº¥m vÃ o sáº½ sá»• danh sÃ¡ch thÆ°Æ¡ng hiá»‡u tá»« database vÃ  lá»c theo tÃªn/mÃ£.
- Frontend validate báº¯t buá»™c `brandId` pháº£i khá»›p má»™t thÆ°Æ¡ng hiá»‡u hiá»‡n cÃ³; payload gá»­i backend láº¥y láº¡i `brand` tá»« brand Ä‘Æ°á»£c chá»n thay vÃ¬ dÃ¹ng text tá»± do trong form.
- Má»¥c tiÃªu: dá»¯ liá»‡u sáº£n pháº©m luÃ´n tham chiáº¿u brand há»£p lá»‡, trÃ¡nh lá»‡ch giá»¯a `products.brand` vÃ  `products.brand_id`.

## Update 2026-06-08 admin product category parent-child selection

- Trong form thÃªm/sá»­a sáº£n pháº©m, khi Ä‘Ã£ chá»n `Danh má»¥c cha`, dropdown `Danh má»¥c con` chá»‰ hiá»ƒn thá»‹ cÃ¡c danh má»¥c con thuá»™c cha Ä‘Ã³.
- Náº¿u chÆ°a chá»n cha mÃ  admin chá»n trá»±c tiáº¿p má»™t danh má»¥c con, frontend tá»± gÃ¡n `categoryId` theo `parentId` cá»§a danh má»¥c con vÃ  cáº­p nháº­t mÃ£ danh má»¥c cha tÆ°Æ¡ng á»©ng.

## Update 2026-06-12 product-level IMEI policy

- Form quáº£n lÃ½ sáº£n pháº©m cÃ³ thÃªm cáº¥u hÃ¬nh `Quáº£n lÃ½ IMEI` vá»›i hai cháº¿ Ä‘á»™: `Theo danh má»¥c` vÃ  `Tá»± chá»n cho sáº£n pháº©m`.
- Cáº¥u hÃ¬nh Ä‘Æ°á»£c lÆ°u vÃ o `products.sales_config.imeiPolicy`; khi `mode = CATEGORY`, luá»“ng tá»“n kho giá»¯ nguyÃªn cÃ¡ch xÃ¡c Ä‘á»‹nh theo `categories.inventory_policy`.
- Khi `mode = MANUAL`, backend tá»“n kho Æ°u tiÃªn `imeiPolicy.trackImei` cá»§a sáº£n pháº©m Ä‘á»ƒ quyáº¿t Ä‘á»‹nh phiáº¿u nháº­p cÃ³ báº¯t buá»™c nháº­p IMEI hay khÃ´ng.
- Khi Ä‘á»•i danh má»¥c cha sang cha khÃ¡c, danh má»¥c con Ä‘ang chá»n sáº½ Ä‘Æ°á»£c giá»¯ láº¡i chá»‰ khi váº«n thuá»™c cha má»›i; náº¿u khÃ´ng, form tá»± clear danh má»¥c con vÃ  reset thÃ´ng sá»‘/biáº¿n thá»ƒ theo hÃ nh vi Ä‘á»•i danh má»¥c cha hiá»‡n cÃ³.

## Update 2026-06-08 simplify product draft approval flow

- Äá»•i nhÃ£n tráº¡ng thÃ¡i sáº£n pháº©m `DRAFT` tá»« `NhÃ¡p` thÃ nh `NhÃ¡p thÃªm` Ä‘á»ƒ phÃ¢n biá»‡t rÃµ vá»›i `REVISION_DRAFT` lÃ  `NhÃ¡p chá»‰nh sá»­a`.
- MÃ n danh sÃ¡ch sáº£n pháº©m khÃ´ng cÃ²n hiá»ƒn thá»‹ nÃºt `Gá»­i duyá»‡t` cho `DRAFT`/`REVISION_DRAFT`; giá»¯ luá»“ng duyá»‡t trá»±c tiáº¿p báº±ng nÃºt `Duyá»‡t tháº³ng` cho Super Admin.
- Duyá»‡t hÃ ng loáº¡t trÃªn frontend nay nháº­n cáº£ `DRAFT`, `REVISION_DRAFT` vÃ  `PENDING`, phÃ¹ há»£p vá»›i cÆ¡ cháº¿ duyá»‡t tháº³ng Ä‘Ã£ cÃ³ á»Ÿ backend.
- Backend váº«n giá»¯ endpoint gá»­i duyá»‡t Ä‘á»ƒ tÆ°Æ¡ng thÃ­ch API cÅ©, nhÆ°ng admin UI khÃ´ng cÃ²n dÃ¹ng bÆ°á»›c trung gian nÃ y.

## Update 2026-06-08 split draft workflow from target product status

- Form sáº£n pháº©m Ä‘á»•i trÆ°á»ng `Tráº¡ng thÃ¡i` thÃ nh `Tráº¡ng thÃ¡i sau duyá»‡t` vÃ  chá»‰ cho chá»n tráº¡ng thÃ¡i kinh doanh: `Äang bÃ¡n`, `Táº¡m áº©n`, `Ngá»«ng kinh doanh`.
- Khi thÃªm má»›i, record trong `products.status` luÃ´n lÃ  `DRAFT`; khi chá»‰nh sá»­a sáº£n pháº©m Ä‘ang bÃ¡n, record revision váº«n lÃ  `REVISION_DRAFT`.
- Tráº¡ng thÃ¡i kinh doanh admin chá»n Ä‘Æ°á»£c lÆ°u trong `sales_config.targetProductStatus`; khi duyá»‡t, backend Ã¡p dá»¥ng giÃ¡ trá»‹ nÃ y lÃ m tráº¡ng thÃ¡i cuá»‘i cá»§a sáº£n pháº©m thay vÃ¬ luÃ´n Ã©p vá» `ACTIVE`.
- Báº£ng sáº£n pháº©m hiá»ƒn thá»‹ nhÃ¡p theo dáº¡ng `NhÃ¡p thÃªm -> Äang bÃ¡n` hoáº·c `NhÃ¡p chá»‰nh sá»­a -> Táº¡m áº©n` Ä‘á»ƒ phÃ¢n biá»‡t workflow vÃ  tráº¡ng thÃ¡i sau duyá»‡t.
- CÃ¡ch lÃ m nÃ y tÃ¡ch rÃµ khÃ¡i niá»‡m mÃ  khÃ´ng cáº§n migration schema ngay: `status` váº«n dÃ¹ng cho workflow khi cÃ²n nhÃ¡p, cÃ²n target náº±m trong `sales_config`.

## Update 2026-06-08 attached service delete vs deactivate

- Dá»‹ch vá»¥ Ä‘i kÃ¨m tÃ¡ch rÃµ thao tÃ¡c `XÃ³a`, `Táº¯t` vÃ  `Báº­t láº¡i`.
- `DELETE /admin/attached-services/{id}` nay xÃ³a cá»©ng dá»‹ch vá»¥ chá»‰ khi chÆ°a cÃ³ dÃ²ng liÃªn káº¿t trong `product_attached_services`; náº¿u Ä‘Ã£ Ä‘Æ°á»£c gáº¯n vá»›i sáº£n pháº©m, backend tráº£ `409` vÃ  yÃªu cáº§u dÃ¹ng `Táº¯t`.
- ThÃªm endpoint `PATCH /admin/attached-services/{id}/deactivate` Ä‘á»ƒ táº¯t dá»‹ch vá»¥ (`is_active = FALSE`) vÃ  `PATCH /admin/attached-services/{id}/reactivate` Ä‘á»ƒ báº­t láº¡i.
- UI quáº£n lÃ½ dá»‹ch vá»¥ hiá»ƒn thá»‹ thao tÃ¡c táº¯t/báº­t láº¡i riÃªng, cÃ²n nÃºt xÃ³a Ä‘Ãºng nghÄ©a lÃ  xÃ³a record khi khÃ´ng cÃ³ rÃ ng buá»™c.

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

- ÄÃ£ hoÃ n thÃ nh tÃ¡ch vÃ  cáº¥u trÃºc láº¡i mÃ´-Ä‘un quáº£n lÃ½ biáº¿n thá»ƒ sáº£n pháº©m (`admin_product_variants.py`) theo mÃ´ hÃ¬nh Controller - Service - Repository:
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


- Sá»­a lá»—i hook/runtime khÃ´ng Ä‘á»•i giao diá»‡n trong storefront/admin:
  - `ProductDetail.tsx`: Ä‘Æ°a effect phÃ­m táº¯t media viewer lÃªn trÆ°á»›c nhÃ¡nh return sá»›m, thÃªm cleanup cho timer thÃ´ng bÃ¡o thÃªm vÃ o giá» vÃ  khÃ´i phá»¥c overflow khi unmount.
  - `VerifyEmailPage.tsx`: cleanup timer chuyá»ƒn hÆ°á»›ng sau xÃ¡c nháº­n email, trÃ¡nh cáº­p nháº­t state sau khi rá»i trang.
  - `CheckoutPage.tsx`: chuyá»ƒn nhÃ¡nh giá» hÃ ng trá»‘ng xuá»‘ng sau hook tÃ­nh phÃ­ giao hÃ ng Ä‘á»ƒ giá»¯ thá»© tá»± hook á»•n Ä‘á»‹nh; Ä‘á»“ng thá»i phá»¥c há»“i chá»¯ tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong file.
  - CÃ¡c tab admin khÃ¡ch hÃ ng/phÃ¢n quyá»n/dashboard: Ä‘Æ°a cÃ¡c lá»i gá»i quyá»n ra biáº¿n top-level hoáº·c hÃ m render thÆ°á»ng Ä‘á»ƒ trÃ¡nh gá»i hook/component trong JSX/callback.


- Tiáº¿p tá»¥c xá»­ lÃ½ cÃ¡c lá»—i nhÃ³m Bugs cÃ²n láº¡i mÃ  khÃ´ng Ä‘á»•i layout/giao diá»‡n:
  - `useCatalog.ts`: chá»‘t option ranked featured á»Ÿ láº§n mount Ä‘áº§u, thÃªm cleanup cho async load catalog.
  - `ImagesModal.tsx` vÃ  `ReelsModal.tsx`: tÃ¡ch outer/inner modal Ä‘á»ƒ remount ná»™i dung khi má»Ÿ, thay vÃ¬ reset nhiá»u state trong effect; thÃªm cleanup URL query khi Ä‘Ã³ng modal.
  - `ProductReviews.tsx`: remount theo `productId + user`, thÃªm cleanup async vÃ  Ä‘Æ°a prefill review hiá»‡n cÃ³ vÃ o callback eligibility thay vÃ¬ sync form báº±ng effect riÃªng.
  - `VietnamAddressSelector.tsx`: bá» state `wards`, derive danh sÃ¡ch phÆ°á»ng/xÃ£ tá»« `provinces + provinceId` báº±ng `useMemo`; sá»­a má»™t sá»‘ nhÃ£n tiáº¿ng Viá»‡t cÃ³ dáº¥u.
  - `ProductDetail.tsx`: chuyá»ƒn reset lá»±a chá»n sáº£n pháº©m/media sang cáº­p nháº­t cÃ³ Ä‘iá»u kiá»‡n theo `product.id`/`activeVariant.id`; effect Swiper chá»‰ cÃ²n Ä‘iá»u khiá»ƒn slide, khÃ´ng set state React.

## Update 2026-06-03 revision variant specs persistence

- Sá»­a lá»—i khi chá»‰nh sá»­a sáº£n pháº©m Ä‘ang bÃ¡n Ä‘á»ƒ táº¡o `REVISION_DRAFT`: backend `upsert_product_variants` nay lÆ°u `product_variants.specs` tá»« `var.specs` do frontend gá»­i lÃªn, thay vÃ¬ ghi Ä‘Ã¨ báº±ng `attributes`. Nhá» váº­y cÃ¡c thÃ´ng sá»‘ ká»¹ thuáº­t Ä‘Æ°á»£c chá»n lÃ m biáº¿n thá»ƒ nhÆ° RAM/ROM/cáº¥u hÃ¬nh giá»¯ Ä‘Ãºng thay Ä‘á»•i trong báº£n nhÃ¡p chá»‰nh sá»­a.
- `attributes` váº«n Ä‘Æ°á»£c dÃ¹ng riÃªng cho há»£p Ä‘á»“ng `options` vÃ  validate lá»±a chá»n biáº¿n thá»ƒ; `specs` giá»¯ key ká»¹ thuáº­t cá»§a form admin Ä‘á»ƒ khi má»Ÿ láº¡i báº£n nhÃ¡p khÃ´ng bá»‹ Ä‘á»c nháº§m vá» dá»¯ liá»‡u cÅ© hoáº·c nhÃ£n hiá»ƒn thá»‹.

## Update 2026-06-03 admin product form controlled popup close

- Popup thÃªm/sá»­a sáº£n pháº©m trÃªn admin nay cÃ³ tráº¡ng thÃ¡i má»Ÿ/Ä‘Ã³ng riÃªng (`productFormOpen`) thay vÃ¬ chá»‰ dá»±a vÃ o `closeSignal`; sau khi thÃªm hoáº·c lÆ°u thÃ nh cÃ´ng, popup Ä‘Æ°á»£c Ä‘Ã³ng ngay trÆ°á»›c khi reset form Ä‘á»ƒ trÃ¡nh hiá»‡n tÆ°á»£ng modal váº«n má»Ÿ nhÆ°ng ná»™i dung bá»‹ nháº£y vá» form thÃªm má»›i/trá»‘ng.
- `CollapsibleSection` há»— trá»£ thÃªm cháº¿ Ä‘á»™ controlled qua `open` vÃ  `onOpenChange`, trong khi váº«n giá»¯ tÆ°Æ¡ng thÃ­ch vá»›i cÃ¡c popup khÃ¡c Ä‘ang dÃ¹ng tráº¡ng thÃ¡i ná»™i bá»™ vÃ  `closeSignal`.

## Update 2026-06-03 admin merged revision action guard (legacy)

- Ghi chÃº lá»‹ch sá»­: trÆ°á»›c ngÃ y 2026-06-08, báº£n chá»‰nh sá»­a sáº£n pháº©m sau khi duyá»‡t vÃ  merge vÃ o sáº£n pháº©m gá»‘c cÃ³ tráº¡ng thÃ¡i `MERGED`.
- CÆ¡ cháº¿ nÃ y Ä‘Ã£ Ä‘Æ°á»£c thay tháº¿: sau khi publish `REVISION_DRAFT`, backend ghi audit `REVISION_PUBLISHED` rá»“i xÃ³a record revision khá»i báº£ng `products`, khÃ´ng táº¡o thÃªm dÃ²ng `MERGED` má»›i.
- CÃ¡c thao tÃ¡c gá»­i duyá»‡t, duyá»‡t, khÃ´i phá»¥c vÃ  lÆ°u trá»¯ trong `useAdminProductsLogic.ts` Ä‘Æ°á»£c bá»c lá»—i Ä‘á»ƒ admin nháº­n thÃ´ng bÃ¡o rÃµ rÃ ng, khÃ´ng cÃ²n lá»—i promise chÆ°a báº¯t trÃªn console.
- Backend váº«n tá»« chá»‘i cáº­p nháº­t/xÃ³a trá»±c tiáº¿p cÃ¡c record `MERGED` cÅ© cÃ²n tá»“n táº¡i, nhÆ°ng sáº£n pháº©m `ARCHIVED` hiá»‡n Ä‘Æ°á»£c phÃ©p khÃ´i phá»¥c qua endpoint reactivate chuáº©n náº¿u khÃ´ng bá»‹ blocker danh má»¥c/thÆ°Æ¡ng hiá»‡u.
- Khi táº¡o `REVISION_DRAFT`, `upsert_product_variants` khÃ´ng cÃ²n Ä‘á»“ng bá»™ `products.sku` cá»§a báº£n revision theo SKU biáº¿n thá»ƒ máº·c Ä‘á»‹nh, trÃ¡nh lá»—i trÃ¹ng unique SKU vá»›i sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang active.
- Sau khi chá»‰nh sá»­a sáº£n pháº©m Ä‘ang bÃ¡n, frontend thÃ´ng bÃ¡o rÃµ lÃ  Ä‘Ã£ táº¡o báº£n chá»‰nh sá»­a cáº§n duyá»‡t, tá»± chuyá»ƒn bá»™ lá»c danh sÃ¡ch sang `REVISION_DRAFT` vÃ  Ä‘Ã³ng form trÆ°á»›c khi reset Ä‘á»ƒ khÃ´ng cÃ²n cáº£m giÃ¡c popup bá»‹ Ä‘á»•i sang form thÃªm má»›i.
- Backend `extract_product_metadata` nay nháº­n Ä‘Ãºng cÃ¡c key frontend gá»­i trong `specifications`: `_variantSpecKeys`, `_accessoryOffers`, `_attachedServices`, `_warrantyPolicy`, rá»“i lÆ°u vÃ o `sales_config` chuáº©n. Frontend cÅ©ng fallback Ä‘á»c cÃ¡c key cÅ© nÃ y tá»« `specifications` khi má»Ÿ báº£n nhÃ¡p chá»‰nh sá»­a Ä‘Ã£ táº¡o trÆ°á»›c Ä‘Ã³.
- Sá»­a thá»© tá»± Ä‘Ã³ng popup sáº£n pháº©m: `closeSignal` dÃ¹ng layout effect vÃ  `handleProductSubmit` chá» má»™t frame trÆ°á»›c khi reset form, trÃ¡nh modal cÃ²n má»Ÿ nhÆ°ng ná»™i dung Ä‘Ã£ nháº£y sang form thÃªm má»›i.
- Sá»­a lÆ°u/má»Ÿ láº¡i ROM biáº¿n thá»ƒ trong báº£n chá»‰nh sá»­a: frontend chuáº©n hÃ³a key biáº¿n thá»ƒ tá»« label tiáº¿ng Viá»‡t nhÆ° `Bá»™ nhá»› trong` vá» key `storage`, backend validate option/attribute báº±ng Unicode normalized vÃ  fallback map `Bá»™ nhá»› trong`/`ROM` vÃ o cá»™t `product_variants.storage`. ÄÃ£ test táº¡o revision táº¡m vá»›i ROM `999GB`, DB lÆ°u Ä‘Ãºng `storage = 999GB`, rá»“i xÃ³a revision test.

## Update 2026-06-03 storefront shared product video

- Trang chi tiáº¿t sáº£n pháº©m nay Æ°u tiÃªn hiá»ƒn thá»‹ video dÃ¹ng chung á»Ÿ Ä‘áº§u gallery náº¿u sáº£n pháº©m cÃ³ `videoUrl`, giá»‘ng cÃ¡ch CellphoneS Ä‘áº·t thumbnail "Video" lÃ m media Ä‘áº§u tiÃªn.
- Khi gallery má»Ÿ báº±ng video, áº£nh dÃ¹ng cho giá» hÃ ng váº«n fallback sang áº£nh sáº£n pháº©m hoáº·c áº£nh biáº¿n thá»ƒ Ä‘áº§u tiÃªn Ä‘á»ƒ khÃ´ng lÆ°u URL video lÃ m áº£nh sáº£n pháº©m trong cart.

## Update 2026-06-03 Revert image card UI

- ÄÃ£ tráº£ láº¡i giao diá»‡n tháº» áº£nh sáº£n pháº©m trÃªn `frontend/src/features/media/pages/ImagesPage.tsx` vá» kiá»ƒu cÅ© theo yÃªu cáº§u: khung áº£nh gradient, nhÃ£n ná»•i, khu thÃ´ng tin dÆ°á»›i áº£nh vÃ  nÃºt mua nhá» hiá»‡n theo hover.

## Update 2026-06-03 Product image card UI

- Chá»‰nh láº¡i tháº» áº£nh sáº£n pháº©m trÃªn trang thÆ° viá»‡n áº£nh (`frontend/src/features/media/pages/ImagesPage.tsx`) Ä‘á»ƒ áº£nh sáº£n pháº©m hiá»ƒn thá»‹ thoÃ¡ng hÆ¡n, giáº£m khoáº£ng tráº¯ng xáº¥u quanh áº£nh cao/dá»c.
- LÃ m pháº§n thÃ´ng tin dÆ°á»›i áº£nh gá»n hÆ¡n: tÃªn sáº£n pháº©m, giÃ¡, lÆ°á»£t xem/lÆ°á»£t thÃ­ch vÃ  nÃºt "Xem sáº£n pháº©m" hiá»ƒn thá»‹ cá»‘ Ä‘á»‹nh thay vÃ¬ áº©n khi hover.
- NhÃ£n danh má»¥c vÃ  sá»‘ lÆ°á»£ng áº£nh Ä‘Æ°á»£c thu gá»n Ä‘á»ƒ khÃ´ng láº¥n vÃ o áº£nh sáº£n pháº©m.

## Update 2026-05-22

- Giá»¯ láº¡i cÃ¡c thÃ´ng tin chÃ­nh cá»§a sáº£n pháº©m nhÆ° cÅ©.
- HÃ¬nh áº£nh Ä‘áº¡i diá»‡n chung lÃ  áº£nh duy nháº¥t á»Ÿ cáº¥p sáº£n pháº©m.
- Bá» pháº§n gallery hÃ¬nh áº£nh chung trong form admin Ä‘á»ƒ trÃ¡nh trÃ¹ng vá»›i hÃ¬nh áº£nh theo biáº¿n thá»ƒ.
- Video sáº£n pháº©m lÃ  video dÃ¹ng chung cho toÃ n bá»™ sáº£n pháº©m, lÆ°u á»Ÿ cáº¥p `products.video_url`.
- Form admin bá»• sung preview cho:
  - áº£nh Ä‘áº¡i diá»‡n chung
  - video dÃ¹ng chung
  - hÃ¬nh áº£nh biáº¿n thá»ƒ theo mÃ u sáº¯c
- Biáº¿n thá»ƒ Æ°u tiÃªn trá»¥c mÃ u sáº¯c trÆ°á»›c, sau Ä‘Ã³ má»›i Ä‘áº¿n thÃ´ng sá»‘ ká»¹ thuáº­t vÃ  giÃ¡.
- Mua kÃ¨m giáº£m giÃ¡:
  - admin chá»n sáº£n pháº©m mua kÃ¨m tá»« danh sÃ¡ch sáº£n pháº©m
  - cáº¥u hÃ¬nh giáº£m theo `FIXED` hoáº·c `PERCENT`
  - cáº¥u hÃ¬nh sá»‘ lÆ°á»£ng tá»‘i Ä‘a Ä‘Æ°á»£c giáº£m giÃ¡ theo tá»«ng sáº£n pháº©m mua kÃ¨m
  - cáº¥u hÃ¬nh Ä‘Æ°á»£c lÆ°u trong `products.sales_config.accessoryOffers`
  - báº£ng `product_accessories` tiáº¿p tá»¥c giá»¯ vai trÃ² quan há»‡ Ä‘á»ƒ tra cá»©u nhanh
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

- Quy táº¯c tÃ­nh giÃ¡ á»Ÿ checkout cáº§n Ã¡p dá»¥ng:
  - chá»‰ giáº£m cho sá»‘ lÆ°á»£ng náº±m trong `maxQuantity`
  - sá»‘ lÆ°á»£ng vÆ°á»£t má»©c giáº£m giÃ¡ sáº½ tÃ­nh theo giÃ¡ gá»‘c
  - sáº£n pháº©m mua kÃ¨m chá»‰ Ä‘Æ°á»£c giáº£m khi cÃ¹ng hÃ³a Ä‘Æ¡n vá»›i sáº£n pháº©m chÃ­nh

## Ghi chÃº pháº¡m vi

- Báº£n cáº­p nháº­t nÃ y hoÃ n thiá»‡n pháº§n quáº£n trá»‹ sáº£n pháº©m vÃ  API lÆ°u cáº¥u hÃ¬nh.
- Náº¿u cáº§n Ã¡p dá»¥ng giÃ¡ mua kÃ¨m trÃªn giá» hÃ ng/checkout, tiáº¿p tá»¥c Ä‘á»c file nÃ y trÆ°á»›c khi sá»­a logic Ä‘Æ¡n hÃ ng.

## Update 2026-05-23

- Bá» pháº§n SEO khá»i form quáº£n trá»‹ sáº£n pháº©m; product SEO metadata cÅ© váº«n Ä‘Æ°á»£c Ä‘á»c náº¿u tá»“n táº¡i nhÆ°ng admin khÃ´ng nháº­p má»›i á»Ÿ mÃ n hÃ¬nh nÃ y.
- Sáº£n pháº©m bÃ¡n kÃ¨m tiáº¿p tá»¥c lÆ°u trong `products.sales_config.accessoryOffers`, nhÆ°ng UI chá»n báº±ng bá»™ lá»c danh má»¥c, thÆ°Æ¡ng hiá»‡u vÃ  tÃ¬m kiáº¿m sáº£n pháº©m.
- UI cho phÃ©p chá»n táº¥t cáº£ sáº£n pháº©m trong káº¿t quáº£ lá»c hiá»‡n táº¡i; má»—i sáº£n pháº©m mua kÃ¨m cÃ³ giÃ¡/Æ°u Ä‘Ã£i do admin set riÃªng báº±ng `discountType`, `discountValue`, `maxQuantity`.
- Biáº¿n thá»ƒ Ä‘Æ°á»£c sáº¯p xáº¿p vÃ  nháº­p theo mÃ u sáº¯c lÃ  trá»¥c chÃ­nh. CÃ¡c cáº¥u hÃ¬nh khÃ¡c nhau cá»§a cÃ¹ng mÃ u váº«n náº±m trong danh sÃ¡ch biáº¿n thá»ƒ nhÆ°ng UI Æ°u tiÃªn nhÃ³m theo mÃ u Ä‘á»ƒ admin dá»… nháº­p hÆ¡n.
- SKU biáº¿n thá»ƒ cÃ³ thá»ƒ do admin nháº­p; náº¿u Ä‘á»ƒ trá»‘ng thÃ¬ frontend/backend tá»± táº¡o theo viáº¿t táº¯t tÃªn sáº£n pháº©m + viáº¿t táº¯t mÃ u + sá»‘ thá»© tá»±, vÃ­ dá»¥ `IPM-DT-01`.
- Dá»‹ch vá»¥ Ä‘i kÃ¨m Ä‘Ã£ cÃ³ ná»n dá»¯ liá»‡u qua `attached_services` vÃ  `product_attached_services`:
  - `PRODUCT_SERVICE`: báº£o hÃ nh/má»Ÿ rá»™ng báº£o hÃ nh gáº¯n vá»›i sáº£n pháº©m/IMEI, tÃ­nh giÃ¡ theo tiá»n cá»‘ Ä‘á»‹nh, pháº§n trÄƒm, hoáº·c Ä‘á»‹nh má»©c.
  - `SUPPORT_SERVICE`: láº¯p Ä‘áº·t, vá»‡ sinh, há»— trá»£... do admin set giÃ¡ cá»‘ Ä‘á»‹nh hoáº·c cáº¥u hÃ¬nh riÃªng.
- Khi lÃ m tiáº¿p giá» hÃ ng/checkout, cáº§n xá»­ lÃ½ rule má»›i: trong cÃ¹ng má»™t `attribute_group` cá»§a dá»‹ch vá»¥ sáº£n pháº©m, ngÆ°á»i mua chá»‰ Ä‘Æ°á»£c chá»n má»™t lá»±a chá»n.
- Admin Ä‘Ã£ cÃ³ mÃ n `Dá»‹ch vá»¥` Ä‘á»ƒ táº¡o/sá»­a/áº©n danh sÃ¡ch dá»‹ch vá»¥ Ä‘i kÃ¨m.
- Form sáº£n pháº©m Ä‘Ã£ cÃ³ khu `Dá»‹ch vá»¥ Ä‘i kÃ¨m`, cho chá»n nhiá»u dá»‹ch vá»¥ tá»« danh sÃ¡ch Ä‘Ã£ táº¡o vÃ  Ä‘áº·t `overridePrice` riÃªng theo sáº£n pháº©m náº¿u cáº§n.
- Product form cÃ³ thÃªm `sales_config.warrantyPolicy` Ä‘á»ƒ sáº£n pháº©m cÃ³ thá»ƒ:
  - láº¥y máº·c Ä‘á»‹nh báº£o hÃ nh/1 Ä‘á»•i 1 tá»« danh má»¥c
  - hoáº·c admin override tháº³ng báº£o hÃ nh vÃ  sá»‘ ngÃ y 1 Ä‘á»•i 1 riÃªng theo sáº£n pháº©m
- Khi chá»n danh má»¥c cha/con, náº¿u sáº£n pháº©m Ä‘ang báº­t "theo danh má»¥c" thÃ¬ UI tá»± náº¡p `warrantyPolicy` tá»« danh má»¥c Æ°u tiÃªn cao nháº¥t.
- Khi chá»n dá»‹ch vá»¥ Ä‘i kÃ¨m trong product form, UI cháº·n viá»‡c chá»n hai dá»‹ch vá»¥ cÃ¹ng `serviceType + attributeGroup`; backend cÅ©ng bá» qua dá»‹ch vá»¥ trÃ¹ng nhÃ³m khi Ä‘á»“ng bá»™ báº±ng `product_attached_services`.
- ÄÃ£ thÃªm `AGENTS.md` vÃ o gá»‘c project Ä‘á»ƒ ghi nhá»› cÃ¡ch dÃ¹ng CodeGraph vÃ  cÃ¡c file notes cáº§n Ä‘á»c trÆ°á»›c khi sá»­a module nÃ y.

## Update 2026-05-23 bá»• sung

- Form sáº£n pháº©m Ä‘Ã£ bá» Ã´ nháº­p tay `Combo/bundle: SKU/ID`; luá»“ng bÃ¡n kÃ¨m chuyá»ƒn sang chá»n sáº£n pháº©m tá»« danh sÃ¡ch lá»c.
- Khu sáº£n pháº©m mua kÃ¨m hiá»‡n danh sÃ¡ch chá»n ngay sau khi admin lá»c theo danh má»¥c, thÆ°Æ¡ng hiá»‡u hoáº·c tÃ¬m theo tÃªn/SKU; cÃ³ nÃºt chá»n táº¥t cáº£ káº¿t quáº£ Ä‘ang lá»c.
- Khu dá»‹ch vá»¥ Ä‘i kÃ¨m trong form sáº£n pháº©m khÃ´ng cho nháº­p tay. Admin lá»c/chá»n tá»« danh sÃ¡ch `attached_services` Ä‘Ã£ táº¡o theo loáº¡i dá»‹ch vá»¥, nhÃ³m dá»‹ch vá»¥ vÃ  tá»« khÃ³a.
- Khi chá»n dá»‹ch vá»¥ Ä‘i kÃ¨m, UI hiá»‡n loáº¡i dá»‹ch vá»¥, nhÃ³m, thá»i háº¡n báº£o hÃ nh vÃ  giÃ¡ Ä‘á»ƒ admin phÃ¢n biá»‡t cÃ¡c gÃ³i 3/6/9/12/18/24/36 thÃ¡ng.
- Danh sÃ¡ch sáº£n pháº©m mua kÃ¨m trong form admin hiá»‡n tá»« dá»¯ liá»‡u sáº£n pháº©m Ä‘Ã£ load sáºµn, khÃ´ng phá»¥ thuá»™c API suggest nÃªn lá»c danh má»¥c/thÆ°Æ¡ng hiá»‡u sáº½ cÃ³ káº¿t quáº£ ngay náº¿u dá»¯ liá»‡u trÃªn báº£ng Ä‘ang cÃ³ sáº£n pháº©m phÃ¹ há»£p.
- Popup thÃªm/sá»­a sáº£n pháº©m, danh má»¥c, thÆ°Æ¡ng hiá»‡u, voucher vÃ  ná»™i dung cÃ³ `forceOpenKey` theo id Ä‘ang sá»­a Ä‘á»ƒ khi chuyá»ƒn sang item khÃ¡c popup tá»± má»Ÿ láº¡i, trÃ¡nh pháº£i reload trang.
- Popup thÃªm/sá»­a cÅ©ng gá»i hÃ m reset form khi Ä‘Ã³ng, Ä‘á»ƒ admin cÃ³ thá»ƒ Ä‘Ã³ng rá»“i báº¥m sá»­a láº¡i Ä‘Ãºng cÃ¹ng item mÃ  khÃ´ng cáº§n reload trang.

## Update 2026-05-23 chÃ­nh sÃ¡ch dá»‹ch vá»¥ má»›i

- Danh sÃ¡ch dá»‹ch vá»¥ báº£o hÃ nh má»Ÿ rá»™ng Ä‘Ã£ cáº­p nháº­t theo chÃ­nh sÃ¡ch ElectroMart Viá»‡t Nam:
  - 1 Ä‘á»•i 1 VIP
  - RÆ¡i vá»¡ - rÆ¡i nÆ°á»›c
  - S24+
- CÃ¡c gÃ³i báº£o hÃ nh nÃ y khÃ´ng cÃ²n tÃ­nh theo pháº§n trÄƒm cá»‘ Ä‘á»‹nh; Ä‘Ã£ chuyá»ƒn sang `TIERED_AMOUNT` vÃ  lÆ°u biá»ƒu phÃ­ trong `attached_services.metadata.priceTiers`.
- Product form vÃ  báº£ng dá»‹ch vá»¥ hiá»ƒn thá»‹ gÃ³i `TIERED_AMOUNT` lÃ  "Theo biá»ƒu phÃ­" Ä‘á»ƒ admin khÃ´ng hiá»ƒu nháº§m lÃ  gia 0 Ä‘á»“ng.
- UI thÃªm/sá»­a dá»‹ch vá»¥ bá»• sung nhÃ³m `ACCIDENTAL_DAMAGE` cho gÃ³i rÆ¡i vá»¡ - rÆ¡i nÆ°á»›c.

## Update 2026-05-23 khÃ³a giÃ¡ dá»‹ch vá»¥ theo chÃ­nh sÃ¡ch

- Product form Ä‘Ã£ bá» Ã´ `overridePrice` trong khu dá»‹ch vá»¥ Ä‘i kÃ¨m; sáº£n pháº©m chá»‰ gÃ¡n mÃ£ gÃ³i dá»‹ch vá»¥, khÃ´ng nháº­p giÃ¡ riÃªng theo sáº£n pháº©m.
- Backend bá» qua giÃ¡ override khi Ä‘á»“ng bá»™ `product_attached_services` vÃ  luÃ´n lÆ°u `override_price = NULL`.
- GiÃ¡ cÃ¡c gÃ³i báº£o hÃ nh/dá»‹ch vá»¥ sáº£n pháº©m láº¥y theo chÃ­nh sÃ¡ch trong `attached_services`, Ä‘áº·c biá»‡t cÃ¡c gÃ³i `PRODUCT_SERVICE` dÃ¹ng `TIERED_AMOUNT` vÃ  `metadata.priceTiers`.

## Update 2026-05-30 product view analytics

- LÆ°á»£t xem sáº£n pháº©m khÃ´ng cÃ²n Ä‘Æ°á»£c cá»™ng ngay khi má»Ÿ trang chi tiáº¿t.
- Frontend dÃ¹ng `useViewTracker` gá»­i heartbeat khi tab Ä‘ang active, kÃ¨m `activeSeconds`, `scrollDepth`, `sessionId` vÃ  `deviceId`.
- Backend endpoint `POST /api/v1/catalog/products/{product_id}/view` chá»‰ ghi `product_view_events` khi Ä‘á»§ 30 giÃ¢y active hoáº·c scroll tá»‘i thiá»ƒu 50%.
- Khi Redis kháº£ dá»¥ng, backend tÃ­ch lÅ©y state theo key `product_view:state:{product_id}:{identity}` vÃ  khÃ³a trÃ¹ng 24 giá» báº±ng `product_view:valid:{product_id}:{identity}`.
- Náº¿u Redis khÃ´ng kháº£ dá»¥ng trong mÃ´i trÆ°á»ng local, backend fallback sang rule DB: chá»‰ ghi khi heartbeat Ä‘Ã£ Ä‘áº¡t ngÆ°á»¡ng vÃ  váº«n dedupe trong 24 giá» theo device/session/IP/user-agent.
- Báº£ng `product_view_events` cÃ³ thÃªm `device_id`, `duration_seconds`, `scroll_depth`; rankings láº¥y `viewCount` tá»« valid event thay vÃ¬ dá»¯ liá»‡u admin/giáº£ láº­p.

## Update 2026-05-30 admin upload refactor

- Admin upload routes Ä‘Æ°á»£c tÃ¡ch khá»i `backend/app/api/v1/routers/admin.py` sang `backend/app/api/v1/routers/admin_uploads.py`.
- Endpoint upload local tiáº¿p tá»¥c giá»¯ URL cÅ© `/api/v1/admin/uploads/local/{folder}/{filename}` nhÆ°ng nay yÃªu cáº§u quyá»n `product:create`, Ä‘á»“ng bá»™ vá»›i bÆ°á»›c táº¡o presigned upload.

## Update 2026-05-30 frontend refactor

- ÄÃ£ tÃ¡ch pháº§n logic vÃ  state quáº£n lÃ½ sáº£n pháº©m ra khá»i `useAdminLogic.ts` sang hook riÃªng biá»‡t `useAdminProductsLogic.ts` Ä‘á»ƒ lÃ m sáº¡ch vÃ  mÃ´-Ä‘un hÃ³a frontend code.

## Update 2026-05-30 flat variant completion

- Product create/update/revision now persists `products.options` so variant `attributes` can be validated against the saved option contract.
- Simple products without explicit variants use the product-level price, discount price, and stock to create the default variant instead of always creating a zero-price/zero-stock variant.
- Publishing a product revision now copies `options` and variant metadata (`compare_at_price`, `is_default`, `status`, `attributes`, `deleted_at`, `stock_quantity`) back to the parent product.
- Duplicating a product now preserves `options` and active variant metadata while generating new SKUs.
- Parent product price and stock are synchronized from active, non-deleted variants.
- Catalog product detail now exposes `options`, variant `attributes`, `isDefault`, `status`, and `compareAtPrice`.
- Admin product form validates duplicate SKU, one default variant, non-negative price/stock, and option/attribute consistency before submit.

## Update 2026-05-30 flat variants & default variant refactor

- Thá»‘ng nháº¥t mÃ´-Ä‘un quáº£n lÃ½ sáº£n pháº©m vÃ  biáº¿n thá»ƒ:
  - Má»—i sáº£n pháº©m cÃ³ Ã­t nháº¥t má»™t biáº¿n thá»ƒ.
  - Sáº£n pháº©m Ä‘Æ¡n giáº£n khÃ´ng cÃ³ lá»±a chá»n Ä‘Æ°á»£c tá»± Ä‘á»™ng táº¡o má»™t default variant trong DB.
  - SKU cá»§a biáº¿n thá»ƒ Ä‘ang active lÃ  duy nháº¥t trong toÃ n há»‡ thá»‘ng, nhÆ°ng SKU cá»§a biáº¿n thá»ƒ Ä‘Ã£ bá»‹ xÃ³a má»m cÃ³ thá»ƒ Ä‘Æ°á»£c tÃ¡i sá»­ dá»¥ng.
  - Báº¯t buá»™c má»—i sáº£n pháº©m chá»‰ cÃ³ Ä‘Ãºng má»™t biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = true`) táº¡i má»—i thá»i Ä‘iá»ƒm.
  - Há»— trá»£ xÃ³a má»m biáº¿n thá»ƒ (`deleted_at IS NULL`). NgÄƒn cháº·n xÃ³a biáº¿n thá»ƒ cuá»‘i cÃ¹ng cá»§a sáº£n pháº©m (`CANNOT_DELETE_LAST_VARIANT`). Tá»± Ä‘á»™ng gÃ¡n biáº¿n thá»ƒ hoáº¡t Ä‘á»™ng tiáº¿p theo lÃ m máº·c Ä‘á»‹nh náº¿u biáº¿n thá»ƒ máº·c Ä‘á»‹nh bá»‹ xÃ³a.
  - Bá»™ lá»c `deleted_at IS NULL` Ä‘Æ°á»£c Ã¡p dá»¥ng Ä‘á»“ng bá»™ á»Ÿ storefront catalog (`catalog.py`), quáº£n lÃ½ tá»“n kho (`admin_inventory.py`), vÃ  quáº£n lÃ½ sáº£n pháº©m (`admin_products.py`).

## Update 2026-05-31 admin product pagination

- Admin product list now loads 20 products per page from `useAdminLogic.ts`.
- `GET /api/v1/admin/products` keeps the default `limit=20` and returns paged `{ items, totalRecords, totalPages, page, limit }` when `page` is provided.
- Fixed PostgreSQL ambiguous null parameters in admin product filters by casting `status_filter` to `TEXT` and `category_id`/`brand_id` to `UUID` in `admin_products.py`.
- Product admin list no longer falls back to the storefront catalog list when the paged admin endpoint fails; this prevents a hidden API error from showing all products as one page.

## Update 2026-05-31 revision draft discard

- Editing an existing active product creates a separate `REVISION_DRAFT`; this draft must be discardable without changing the parent product.
- `DELETE /api/v1/admin/products/{id}` now detects `REVISION_DRAFT` with `parent_product_id` and discards only that revision:
  - deletes relation rows owned by the revision in `product_bundles`, `product_accessories`, and `product_attached_services`
  - soft-deletes revision variants
  - marks the revision product `ARCHIVED` and sets `deleted_at`
- `POST /api/v1/admin/products/{id}/archive` now accepts `REVISION_DRAFT`.
- Admin product UI now allows `REVISION_DRAFT` to be sent for approval or archived, but does not show the restore action for revision drafts.

## Update 2026-05-31 smart revision merge

- Publishing a product revision no longer deletes all live variants and reinserts variants from the revision.
- Added delta merge by SKU in `admin_products.py`:
  - revision variant with matching live SKU updates live variant descriptive fields, price, media, specs, attributes, status, and default flag
  - live variant stock is preserved during updates; stock remains controlled by inventory/order flows
  - revision variant with new SKU inserts a new live variant
  - live variant missing from the revision is soft-disabled instead of physically deleted
- Missing live variants with inventory history become `inactive`; variants without inventory history become `archived`.
- Ghi chÃº lá»‹ch sá»­: trÆ°á»›c ngÃ y 2026-06-08, revision records tá»«ng trá»Ÿ thÃ nh `MERGED` sau khi publish. CÆ¡ cháº¿ má»›i khÃ´ng táº¡o `MERGED`; audit trail lÆ°u snapshot trÆ°á»›c/sau vÃ  record revision bá»‹ xÃ³a khá»i `products` sau khi Ã¡p dá»¥ng.
- Fixed revision variant creation so draft variants receive new IDs instead of reusing live variant IDs.

## Update 2026-05-31 complete enterprise revision design

- Added migration `047_enterprise_product_revision_merge.sql`.
- `product_variants.parent_variant_id` stores durable lineage from revision variants to live variants; SKU remains a fallback matching key.
- `order_items.variant_id` stores the exact sold variant for audit, restock, and safe variant deactivation decisions.
- Commerce order creation now writes `variant_id` to `order_items` when checkout provides a variant.
- Order restock now prefers `order_items.variant_id` and only falls back to inventory adjustment logs for old orders.
- Revision merge now matches live variants by `parent_variant_id` first, then SKU.
- Missing live variants now check both `order_items.variant_id` and `inventory_adjustment_logs.variant_id`; variants with history become `inactive`, otherwise `archived`.
- Local database has been migrated with the new columns and indexes.

## Update 2026-05-31 archived product visibility

- Admin product list now hides `ARCHIVED` products by default, the same way it hides `MERGED` revision history.
- `ARCHIVED` products remain in the database for audit/safety, but only appear when the admin explicitly filters status `ARCHIVED`.

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
- Frontend khÃ´ng cÃ²n thay áº£nh sáº£n pháº©m theo báº£ng áº£nh demo cÅ©; áº£nh sáº£n pháº©m láº¥y tá»« dá»¯ liá»‡u backend/database vÃ  chá»‰ Ä‘Æ°á»£c chuáº©n hÃ³a URL.
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
- Sau khi tÃ¡ch thÃªm hook product/variant, `useAdminProductVariants.ts` tráº£ thÃªm `colorOptionName` Ä‘á»ƒ `useAdminProductsLogic.ts` map láº¡i mÃ u biáº¿n thá»ƒ khi má»Ÿ form chá»‰nh sá»­a. Sá»­a import thiáº¿u `youtubeEmbedUrl` vÃ  `ImageWithFallback` á»Ÿ `ProductDetail.tsx` sau khi tÃ¡ch helper media.

## Update 2026-06-05 Frontend feature-first refactor for Products & Brands

- HoÃ n thÃ nh di chuyá»ƒn toÃ n bá»™ module **ThÆ°Æ¡ng hiá»‡u (Brands)** vÃ  **Sáº£n pháº©m (Products)** á»Ÿ Frontend sang cáº¥u trÃºc hÆ°á»›ng tÃ­nh nÄƒng (**Feature-First Architecture**):
  - **Module ThÆ°Æ¡ng hiá»‡u (Brands)**: Di chuyá»ƒn sang `src/features/admin-brands/` gá»“m API (`services/adminBrandsApi.ts`), logic hooks (`hooks/useAdminBrandsLogic.ts`) vÃ  giao diá»‡n (`components/AdminBrandsTab.tsx`).
  - **Module Sáº£n pháº©m (Products)**: Di chuyá»ƒn sang `src/features/admin-products/` gá»“m API (`services/adminProductsApi.ts`), logic hooks (`hooks/useAdminProductsLogic.ts`, `useAdminProductOffers.ts`, `useAdminProductVariants.ts`) vÃ  cÃ¡c UI Components (`components/AdminProductsTab.tsx`, `components/products/ProductAccessoriesSection.tsx`, `ProductFormSection.tsx`, `ProductTableSection.tsx`, `ProductVariantsSection.tsx`).
  - **XÃ¡c minh**: Cháº¡y thÃ nh cÃ´ng lá»‡nh kiá»ƒm tra kiá»ƒu `npx tsc --noEmit` trÃªn toÃ n bá»™ frontend mÃ  khÃ´ng phÃ¡t sinh báº¥t ká»³ lá»—i compile nÃ o.

## Update 2026-06-05 Refactor Attached Services to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥ vÃ  truy váº¥n SQL cá»§a Dá»‹ch vá»¥ Ä‘i kÃ¨m (Attached Services) ra khá»i `admin_products.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/attached_service.py` Ä‘á»ƒ giá»¯ router sáº¡ch sáº½, dá»… báº£o trÃ¬. CÃ¡c route `/attached-services` chá»‰ lÃ m nhiá»‡m vá»¥ Ä‘iá»u hÆ°á»›ng vÃ  gá»i hÃ m tá»« service.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module Dá»‹ch vá»¥ vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-services/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
- Káº¿t quáº£ kiá»ƒm tra:
  - Frontend: compile thÃ nh cÃ´ng báº±ng `npx tsc --noEmit`.
  - Backend: compile thÃ nh cÃ´ng báº±ng `py_compile`, import `app.main` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng, khÃ´ng xáº£y ra import vÃ²ng láº·p.

## Update 2026-06-05 Refactor Flash Sales to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥, tÃ­nh toÃ¡n giÃ¡ sale vÃ  truy váº¥n SQL cá»§a Flash Sales ra khá»i `admin_flash_sales.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/flash_sale_service.py`. Class pydantic `FlashSalePayload` Ä‘Æ°á»£c di chuyá»ƒn sang `admin_schemas.py` Ä‘á»ƒ thá»‘ng nháº¥t cáº¥u trÃºc schema.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module Flash Sales vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-flash-sales/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
- Káº¿t quáº£ kiá»ƒm tra:
  - Frontend: compile thÃ nh cÃ´ng báº±ng `npx tsc --noEmit`.
  - Backend: compile thÃ nh cÃ´ng báº±ng `py_compile`, import `app.main` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng, khÃ´ng xáº£y ra import vÃ²ng láº·p.

## Update 2026-06-05 Refactor Reviews to Service Layer & Feature-First

- Backend: TÃ¡ch logic nghiá»‡p vá»¥, kiá»ƒm duyá»‡t vÃ  truy váº¥n SQL cá»§a ÄÃ¡nh giÃ¡ (Reviews) ra khá»i `admin_reviews.py` sang má»™t Service Layer chuyÃªn biá»‡t táº¡i `app/application/services/review_service.py`.
- Frontend: ÄÃ³ng gÃ³i toÃ n bá»™ module ÄÃ¡nh giÃ¡ vÃ o thÆ° má»¥c tÃ­nh nÄƒng chuyÃªn biá»‡t `src/features/admin-reviews/` theo kiáº¿n trÃºc hÆ°á»›ng tÃ­nh nÄƒng (Feature-First Architecture).
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

## Update 2026-06-08 archived product hard delete fix

- Sá»­a luá»“ng `DELETE /admin/products/{id}` Ä‘á»ƒ sáº£n pháº©m `ARCHIVED` khÃ´ng bá»‹ cháº·n máº·c Ä‘á»‹nh báº±ng lá»—i "Sáº£n pháº©m Ä‘Ã£ Ä‘Æ°á»£c lÆ°u trá»¯ trÆ°á»›c Ä‘Ã³".
- Sáº£n pháº©m Ä‘Ã£ lÆ°u trá»¯ nay váº«n Ä‘i qua cÃ¹ng bá»™ kiá»ƒm tra rÃ ng buá»™c nhÆ° cÃ¡c tráº¡ng thÃ¡i khÃ¡c: cÃ³ Ä‘Æ¡n hÃ ng/Ä‘Ã¡nh giÃ¡ thÃ¬ chuyá»ƒn `INACTIVE`, cÃ³ nháº­p kho tháº­t thÃ¬ tráº£ `409`, khÃ´ng cÃ³ rÃ ng buá»™c thÃ¬ xÃ³a cá»©ng.
- Dá»n Ä‘á»‹nh nghÄ©a trÃ¹ng `deactivate_product_data` trong `product_approval_repo.py` Ä‘á»ƒ chá»‰ cÃ²n má»™t luá»“ng xÃ³a cÃ³ hiá»‡u lá»±c.

## Update 2026-06-08 archived restore and no-MERGED revision publish

- Sáº£n pháº©m `ARCHIVED` nay Ä‘Æ°á»£c phÃ©p báº­t láº¡i báº±ng luá»“ng khÃ´i phá»¥c chuáº©n `POST /admin/products/{id}/reactivate`, cÃ³ kiá»ƒm tra danh má»¥c/thÆ°Æ¡ng hiá»‡u Ä‘ang áº©n vÃ  validate giÃ¡/biáº¿n thá»ƒ nhÆ° `INACTIVE`/`DISCONTINUED`.
- Frontend hiá»ƒn thá»‹ thao tÃ¡c khÃ´i phá»¥c cho `ARCHIVED` vÃ  cho phÃ©p bulk restore vá»›i tráº¡ng thÃ¡i `ARCHIVED`.
- Bá» cÆ¡ cháº¿ Ä‘á»ƒ láº¡i báº£n revision vá»›i tráº¡ng thÃ¡i `MERGED` trong báº£ng `products` sau khi duyá»‡t báº£n chá»‰nh sá»­a.
- Khi duyá»‡t `REVISION_DRAFT`, backend váº«n Ã¡p dá»¥ng dá»¯ liá»‡u revision vÃ o sáº£n pháº©m gá»‘c, merge variants/bundle/accessory nhÆ° cÅ©, nhÆ°ng ghi snapshot trÆ°á»›c/sau vÃ o `product_audit_logs` qua action `REVISION_PUBLISHED`, rá»“i xÃ³a record revision khá»i `products`.
- Má»¥c tiÃªu kiáº¿n trÃºc: báº£ng `products` chá»‰ giá»¯ báº£n nghiá»‡p vá»¥ hiá»‡n hÃ nh/Ä‘ang thao tÃ¡c, cÃ²n lá»‹ch sá»­ chá»‰nh sá»­a náº±m á»Ÿ audit trail thay vÃ¬ nhÃ¢n báº£n sáº£n pháº©m thÃ nh `MERGED`.

## Update 2026-06-08 remove catalog general stock input

- Form quáº£n trá»‹ sáº£n pháº©m Ä‘Ã£ bá» Ã´ `Tá»“n kho chung` vÃ¬ tá»“n kho Ä‘Æ°á»£c quáº£n lÃ½ qua module Tá»“n kho/Nháº­p kho.
- Khi lÆ°u sáº£n pháº©m, backend giá»¯ nguyÃªn `products.stock_quantity` hiá»‡n cÃ³ thay vÃ¬ ghi Ä‘Ã¨ báº±ng payload tá»« form catalog.
- Biáº¿n thá»ƒ má»›i táº¡o trong form sáº£n pháº©m máº·c Ä‘á»‹nh tá»“n kho `0`; sá»‘ lÆ°á»£ng thá»±c táº¿ pháº£i Ä‘Æ°á»£c nháº­p/Ä‘iá»u chá»‰nh trong module tá»“n kho.
- Sá»­a lá»—i há»“i quy trong `create_product`: táº¡o sáº£n pháº©m má»›i dÃ¹ng `payload.stock`, cÃ²n cáº­p nháº­t sáº£n pháº©m cÅ© má»›i giá»¯ `current["stock_quantity"]`; trÃ¡nh lá»—i `NameError: current is not defined` khi `POST /admin/products`.

## Update 2026-06-08 product detail attached services display

- API chi tiáº¿t sáº£n pháº©m catalog nay náº¡p `product_attached_services` vÃ  tráº£ vá» trong `salesConfig.attachedServices` Ä‘á»ƒ storefront cÃ³ dá»¯ liá»‡u hiá»ƒn thá»‹ dá»‹ch vá»¥ Ä‘i kÃ¨m.
- Náº¿u sáº£n pháº©m cÅ© chá»‰ cÃ²n `serviceId` trong `sales_config.attachedServices` nhÆ°ng thiáº¿u dÃ²ng quan há»‡, API chi tiáº¿t fallback resolve theo danh sÃ¡ch `serviceId` Ä‘á»ƒ váº«n hiá»ƒn thá»‹ Ä‘Æ°á»£c.
- Trang chi tiáº¿t sáº£n pháº©m hiá»ƒn thá»‹ thÃªm khá»‘i `Dá»‹ch vá»¥ Ä‘i kÃ¨m` dÆ°á»›i khu `Æ¯u Ä‘Ã£i mua kÃ¨m`, chá»‰ hiá»‡n khi sáº£n pháº©m cÃ²n kinh doanh vÃ  cÃ³ dá»‹ch vá»¥ active.
- Luá»“ng duyá»‡t `REVISION_DRAFT` Ä‘Ã£ copy thÃªm quan há»‡ `product_attached_services` tá»« revision sang sáº£n pháº©m gá»‘c, Ä‘á»“ng bá»™ vá»›i bundle/accessory; trÃ¡nh viá»‡c admin chá»n dá»‹ch vá»¥ trong báº£n chá»‰nh sá»­a nhÆ°ng sau khi duyá»‡t storefront khÃ´ng cÃ³ dá»¯ liá»‡u.

## Update 2026-06-08 attached service tier price restore

- Trang chi tiáº¿t sáº£n pháº©m tá»± tÃ­nh giÃ¡ dá»‹ch vá»¥ `TIERED_AMOUNT` theo `metadata.priceTiers` vÃ  giÃ¡ sáº£n pháº©m/biáº¿n thá»ƒ Ä‘ang chá»n, thay vÃ¬ chá»‰ hiá»‡n â€œTheo má»©c giÃ¡ sáº£n pháº©mâ€.
- Sá»­a luá»“ng cáº­p nháº­t dá»‹ch vá»¥ Ä‘i kÃ¨m Ä‘á»ƒ form admin khÃ´ng ghi Ä‘Ã¨ `metadata` rá»—ng lÃªn dá»‹ch vá»¥ sáº£n pháº©m Ä‘Ã£ cÃ³ biá»ƒu phÃ­.
- Cháº¡y láº¡i seed `scripts/seed_attached_services.py` Ä‘á»ƒ khÃ´i phá»¥c biá»ƒu phÃ­ báº£o hÃ nh vÃ  cáº­p nháº­t reference cÅ© `BHMR-PHONE-12M` sang dá»‹ch vá»¥ active `S24-MOBILE-12M`; API iPhone 16 Pro Max hiá»‡n tráº£ 17 tier vÃ  phÃ­ 1.600.000Ä‘ cho giÃ¡ 33.990.000Ä‘.

## Update 2026-06-10 Add iPad Pro M4 11 inch Wi-Fi + Cellular (5G) Variants

- Cáº­p nháº­t dÃ²ng sáº£n pháº©m iPad Pro M4 11 inch (SKU gá»‘c: `IPADM4`) trÃªn cáº£ cÆ¡ sá»Ÿ dá»¯ liá»‡u (PostgreSQL) vÃ  tá»‡p khá»Ÿi táº¡o dá»¯ liá»‡u seed (`init_database.sql`):
  - Cáº­p nháº­t `products.options` cá»§a sáº£n pháº©m cha Ä‘á»ƒ bá»• sung tuá»³ chá»n "Káº¿t ná»‘i" vá»›i 2 giÃ¡ trá»‹ `"Wi-Fi"` vÃ  `"Wi-Fi + Cellular"`.
  - Cáº­p nháº­t `capacities` cá»§a sáº£n pháº©m cha bao gá»“m 6 má»©c dung lÆ°á»£ng: `"256GB"`, `"512GB"`, `"1TB"`, `"1TB Nano"`, `"2TB"`, `"2TB Nano"`.
  - Äá»“ng bá»™ hÃ³a 12 biáº¿n thá»ƒ Wi-Fi cÅ©: Cáº­p nháº­t `configuration` thÃ nh `"Wi-Fi"`, Ä‘á»“ng thá»i chuáº©n hÃ³a `specs` vÃ  `attributes` Ä‘á»ƒ cÃ³ key `"Káº¿t ná»‘i": "Wi-Fi"` vÃ  `"ram": "8GB"` (hoáº·c `"16GB"` cho báº£n 1TB/2TB).
  - ThÃªm má»›i 12 biáº¿n thá»ƒ Wi-Fi + Cellular (5G) má»›i (vÃ­ dá»¥ SKU `IPADM4-256-SILVER-5G`) vá»›i giÃ¡ bÃ¡n cao hÆ¡n báº£n Wi-Fi tÆ°Æ¡ng á»©ng **6.000.000Ä‘**, sá»‘ lÆ°á»£ng tá»“n kho máº·c Ä‘á»‹nh lÃ  **10** chiáº¿c, tráº¡ng thÃ¡i hoáº¡t Ä‘á»™ng.
- Sá»­a Ä‘á»•i tá»‡p `init_database.sql`: KhÃ´i phá»¥c pháº§n chÃ¨n thÆ°Æ¡ng hiá»‡u, sáº£n pháº©m vÃ  biáº¿n thá»ƒ bá»‹ há»ng cÃº phÃ¡p trÆ°á»›c Ä‘Ã³, Ä‘á»“ng bá»™ hÃ³a 24 biáº¿n thá»ƒ cá»§a iPad Pro M4 vÃ o dá»¯ liá»‡u seed ban Ä‘áº§u.
- Káº¿t quáº£ kiá»ƒm tra:
  - Backend compile thÃ nh cÃ´ng khÃ´ng cÃ³ lá»—i cÃº phÃ¡p.
  - CSDL thá»±c táº¿ Ä‘Æ°á»£c cáº­p nháº­t Ä‘áº§y Ä‘á»§ vÃ  chÃ­nh xÃ¡c 24 biáº¿n thá»ƒ thÃ´ng qua script `update_ipad_m4_variants.py`.

## Update 2026-06-10 Add Apple Watch Ultra 2 Variants and Options

- Cáº­p nháº­t sáº£n pháº©m Apple Watch Ultra 2 (SKU gá»‘c: `AWU2`) trÃªn cÆ¡ sá»Ÿ dá»¯ liá»‡u (PostgreSQL) vÃ  tá»‡p seed `init_database.sql`:
  - Cáº­p nháº­t sáº£n pháº©m cha `AWU2`: Thiáº¿t láº­p `colors` thÃ nh mÃ u `"Titan Äen"` (`#2a2b2d`), bá»• sung tÃ¹y chá»n `"PhiÃªn báº£n"` gá»“m 9 giÃ¡ trá»‹ tÆ°Æ¡ng á»©ng vá»›i 9 loáº¡i dÃ¢y Ä‘eo kÃ­ch thÆ°á»›c 49mm, vÃ  Ä‘á»“ng bá»™ `capacities` chá»©a danh sÃ¡ch 9 tÃªn dÃ¢y Ä‘eo. Cáº­p nháº­t giÃ¡ bÃ¡n lÃ  `16.990.000Ä‘` vÃ  tá»“n kho lÃ  `90`.
  - Bá»• sung 9 biáº¿n thá»ƒ má»›i trong báº£ng `product_variants` á»©ng vá»›i cÃ¡c loáº¡i dÃ¢y Ä‘eo:
    1. `AWU2-49-BLACK-ALPINEL` (49mm DÃ¢y Alpine Size L)
    2. `AWU2-49-BLACK-ALPINES` (49mm DÃ¢y Alpine Size S) - Biáº¿n thá»ƒ máº·c Ä‘á»‹nh (`is_default = true`)
    3. `AWU2-49-BLACK-TRAILSM` (49mm DÃ¢y Trail Size S/M)
    4. `AWU2-49-BLACK-CAOSU` (49mm DÃ¢y Cao Su)
    5. `AWU2-49-BLACK-TRAILML` (49mm DÃ¢y Trail Size M/L)
    6. `AWU2-49-BLACK-TITANM` (49mm DÃ¢y Titan Size M)
    7. `AWU2-49-BLACK-TITANS` (49mm DÃ¢y Titan Size S)
    8. `AWU2-49-BLACK-TITANL` (49mm DÃ¢y Titan Size L)
    9. `AWU2-49-BLACK-ALPINEM` (49mm DÃ¢y Alpine Size M)
  - Má»—i biáº¿n thá»ƒ Ä‘Æ°á»£c gÃ¡n mÃ u sáº¯c `"Titan Äen"`, tá»“n kho máº·c Ä‘á»‹nh lÃ  `10` chiáº¿c, tráº¡ng thÃ¡i `"active"`, vÃ  Ä‘á»“ng bá»™ hÃ³a chi tiáº¿t trong trÆ°á»ng `specs` vÃ  `attributes` theo Ä‘á»‹nh dáº¡ng cá»§a frontend.
- Äá»“ng bá»™ hÃ³a dá»¯ liá»‡u seed: ChÃ¨n 9 biáº¿n thá»ƒ nÃ y vÃ o pháº§n `variant_seed` vÃ  cáº­p nháº­t thÃ´ng sá»‘ sáº£n pháº©m cha trong pháº§n `product_seed` cá»§a tá»‡p `init_database.sql`.
- Káº¿t quáº£ kiá»ƒm tra:
  - CSDL thá»±c táº¿ Ä‘Æ°á»£c cáº­p nháº­t Ä‘áº§y Ä‘á»§ vÃ  chÃ­nh xÃ¡c thÃ´ng qua ká»‹ch báº£n `update_awu2_variants.py`.
  - Cháº¡y thá»­ nghiá»‡m thÃ nh cÃ´ng, frontend hiá»ƒn thá»‹ Ä‘Ãºng bá»™ chá»n dÃ¢y Ä‘eo vÃ  giÃ¡ tiá»n.

## Update 2026-06-10 Update iPad A16 Wifi Variants and Options

- Cáº­p nháº­t cáº¥u hÃ¬nh vÃ  biáº¿n thá»ƒ cho dÃ²ng sáº£n pháº©m iPad A16 Wifi (SKU gá»‘c: `IPADA16`) trÃªn cÆ¡ sá»Ÿ dá»¯ liá»‡u (PostgreSQL) vÃ  tá»‡p seed `init_database.sql`:
  - Cáº­p nháº­t sáº£n pháº©m cha `IPADA16`:
    - Thiáº¿t láº­p `colors` gá»“m 4 mÃ u má»›i: `"Báº¡c"` (`#d1d5db`), `"VÃ ng"` (`#f5e08c`), `"Há»“ng"` (`#e57c91`), `"Xanh"` (`#4b9cd3`).
    - Bá»• sung tÃ¹y chá»n `"PhiÃªn báº£n"` gá»“m 5 cáº¥u hÃ¬nh má»›i: `"A16 Wifi 128GB"`, `"A16 Wifi 256GB"`, `"A16 5G 128GB"`, `"A16 5G 256GB"`, `"A16 Wifi 512GB"`.
    - Äá»“ng bá»™ `capacities` chá»©a danh sÃ¡ch 5 cáº¥u hÃ¬nh trÃªn.
    - Cáº­p nháº­t giÃ¡ cÆ¡ báº£n cá»§a sáº£n pháº©m cha thÃ nh `9.290.000Ä‘` vÃ  tá»•ng tá»“n kho lÃ  `200` (20 variants * 10).
  - Quáº£n lÃ½ biáº¿n thá»ƒ cÅ©: ÄÃ¡nh dáº¥u xÃ³a (soft-delete báº±ng cÃ¡ch Ä‘áº·t `deleted_at = NOW()`, `status = 'archived'`) Ä‘á»‘i vá»›i 4 biáº¿n thá»ƒ cÅ© (báº£n 64GB vÃ  báº£n mÃ u XÃ¡m Space Gray).
  - Bá»• sung 20 biáº¿n thá»ƒ má»›i á»©ng vá»›i 5 cáº¥u hÃ¬nh Ã— 4 mÃ u sáº¯c:
    - CÃ¡c SKU má»›i theo Ä‘á»‹nh dáº¡ng `IPADA16-[CONFIG_CODE]-[COLOR_SUFFIX]` (vÃ­ dá»¥: `IPADA16-W128-SILVER`).
    - Thiáº¿t láº­p giÃ¡ bÃ¡n: `A16 Wifi 128GB` cÃ³ giÃ¡ lÃ  `9.290.000Ä‘`, cÃ¡c báº£n cao hÆ¡n láº§n lÆ°á»£t lÃ  `11.290.000Ä‘`, `12.290.000Ä‘`, `14.290.000Ä‘` vÃ  `15.290.000Ä‘`.
    - Má»—i biáº¿n thá»ƒ Ä‘Æ°á»£c gÃ¡n tá»“n kho máº·c Ä‘á»‹nh lÃ  `10` chiáº¿c, tráº¡ng thÃ¡i `"active"`, vÃ  Ä‘á»“ng bá»™ hÃ³a `specs`/`attributes` tÆ°Æ¡ng thÃ­ch vá»›i frontend.
    - Äáº·t biáº¿n thá»ƒ `IPADA16-W128-SILVER` (A16 Wifi 128GB mÃ u Báº¡c) lÃ m máº·c Ä‘á»‹nh (`is_default = true`).
- Äá»“ng bá»™ hÃ³a dá»¯ liá»‡u seed: Cáº­p nháº­t thÃ´ng sá»‘ sáº£n pháº©m cha trong pháº§n `product_seed` vÃ  thay tháº¿ cÃ¡c biáº¿n thá»ƒ cÅ© báº±ng 20 biáº¿n thá»ƒ má»›i trong pháº§n `variant_seed` cá»§a tá»‡p `init_database.sql`.
- Káº¿t quáº£ kiá»ƒm tra:
  - CSDL thá»±c táº¿ Ä‘Æ°á»£c cáº­p nháº­t Ä‘áº§y Ä‘á»§ vÃ  chÃ­nh xÃ¡c thÃ´ng qua ká»‹ch báº£n `update_ipad_a16_variants.py`.
  - Cháº¡y thá»­ nghiá»‡m thÃ nh cÃ´ng, cÃ¡c tÃ¹y chá»n mÃ u vÃ  phiÃªn báº£n hiá»ƒn thá»‹ khá»›p vá»›i hÃ¬nh áº£nh.

## Update 2026-07-05 flash sale quantity limit

- Bổ sung quota cho flash sale qua `flash_sales.quantity_limit`, `sold_quantity`, `quota_exhausted_at`; `quantity_limit = NULL` nghĩa là không giới hạn số lượng sale.
- Checkout web chỉ áp dụng giá flash sale khi quota còn đủ cho số lượng mua. Khi giữ hết quota, backend tự chuyển flash sale sang `INACTIVE` và catalog/ranking/search không còn trả giá sale cho sản phẩm đó.
- `order_items` lưu `flash_sale_id`, `flash_sale_quantity`, `flash_sale_released_at` để biết đơn nào đã tiêu quota flash sale và tránh hoàn trả quota trùng lặp.
- Khi đơn chưa giao bị hủy, hoàn, hoặc thanh toán thất bại, hệ thống hoàn lại quota flash sale; nếu flash sale trước đó bị tắt do hết quota và vẫn còn trong thời gian hiệu lực, backend tự bật lại.
- Storefront trả thêm `quantityLimit`, `soldQuantity`, `remainingQuantity`, `isLimited` trong `flashSale`; frontend hiển thị số suất sale còn lại trên card và trang chi tiết.
- Giỏ hàng storefront lưu thêm `variantId` và checkout gửi `variant_id`, tránh trường hợp chọn biến thể có flash sale nhưng backend lại xử lý như sản phẩm cha.
- Admin flash sale có thêm ô `Số lượng sale`; để trống là không giới hạn. Danh sách admin hiển thị số lượng còn lại/đã bán sale và trạng thái `Đã hết suất`.

## Update 2026-07-05 warranty snapshot at sale time

- `products.warranty_period` vẫn là cấu hình hiện tại của sản phẩm, nhưng quyền bảo hành của đơn đã bán được snapshot vào `order_items.warranty_months_snapshot`.
- Checkout online/POS ghi snapshot này khi tạo dòng đơn, tránh việc admin đổi thời hạn bảo hành sản phẩm sau này làm sai quyền lợi của khách cũ.
- Hậu mãi warranty ưu tiên đọc snapshot trên order item; chỉ fallback sang `products.warranty_period` cho dữ liệu cũ/manual chưa có snapshot.
- Migration `052_order_item_warranty_snapshot.sql` backfill các order item cũ theo warranty hiện tại của sản phẩm để giảm dữ liệu trống.

## Update 2026-07-08 cart manual test alignment

- Trang giỏ hàng (`CartPage.tsx`) không có form nhập voucher; voucher được nhập và validate ở bước checkout (`CheckoutPage.tsx`). Các test case áp dụng mã giảm giá phải chạy tại `/checkout`, còn `/cart` chỉ hiển thị nhắc nhở có thể áp dụng ưu đãi ở bước sau.
- Máy cũ là thiết bị đơn chiếc theo IMEI/usedDeviceId nên giỏ hàng luôn khóa số lượng ở `1`; `cartStore` ép quantity về `1` và checkout cũng gửi `quantity = 1` cho item máy cũ. UI giỏ hàng đã disable nút tăng số lượng cho máy cũ để tránh thao tác bấm nhưng không đổi.
- Khi tick/bỏ tick sản phẩm chính trong giỏ hàng, `toggleCheckItem` tự đồng bộ trạng thái tick cho các phụ kiện mua kèm cùng `parentProductId`. Bộ test manual cần có case kiểm tra phụ kiện được tick/bỏ tick theo sản phẩm chính.
- Ngưỡng miễn phí vận chuyển của giỏ hàng lấy động từ API cấu hình vận chuyển, không hard-code cố định ở frontend. Test manual cần kiểm tra thanh tiến trình và số tiền cần mua thêm thay đổi theo tổng tiền giỏ hàng.

## Update 2026-07-08 checkout manual test alignment

- Backend tạo đơn online đã hỗ trợ khách vãng lai qua `get_optional_current_user_id` và `CreateOrderRequest.user_id = None`; frontend checkout không còn chặn đăng nhập trước khi tạo đơn. Khách vãng lai có thể nhập địa chỉ giao hàng tạm thời, email tùy chọn và gửi đơn với `user_id: null`.
- Địa chỉ khách vãng lai chỉ dùng cho đơn hiện tại, không ghi vào hồ sơ. Người dùng đã đăng nhập vẫn dùng luồng sổ địa chỉ và lưu địa chỉ mới vào profile như trước.
- Backend vẫn validate chặt đơn giá sản phẩm, giá máy cũ và giá dịch vụ đính kèm theo dữ liệu hệ thống khi tạo đơn online; test manual cần có case sửa payload lệch giá sản phẩm/dịch vụ để xác nhận lỗi 400/409.
- Nếu tài khoản đang có đơn PENDING chứa flash sale, backend chặn tạo thêm đơn flash sale mới để tránh giữ suất ảo. Test manual cần bổ sung case tạo đơn flash sale thứ hai khi đơn đầu chưa thanh toán.
- Checkout frontend lấy danh sách phương thức thanh toán khả dụng từ cấu hình database; nếu COD mặc định đang bảo trì, UI tự chuyển sang phương thức khả dụng đầu tiên. Test manual cần kiểm tra kịch bản tắt/bảo trì COD.
# Cập nhật 2026-07-13 - Tìm sản phẩm đổi trong hậu mãi

- Biểu mẫu đổi trả phía khách hàng tìm sản phẩm theo từ khóa, debounce 300 ms và giới hạn 20 kết quả thay vì tải sẵn 100 sản phẩm.
- Migration `088_fix_smoke_test_product_encoding.sql` sửa tên và màu của dữ liệu kiểm thử `SMOKE-USED-*` bị lỗi mã hóa.

## Cập nhật 2026-07-13 - Tải dữ liệu storefront ổn định hơn

- API client frontend tự thử lại đúng một lần khi request `GET` hoặc `HEAD` thất bại ở tầng mạng; các thao tác ghi không tự gửi lại để tránh tạo dữ liệu trùng.
- Request bị hủy bằng `AbortController` không được thử lại.
- Khối hỏi đáp sản phẩm phân biệt rõ lỗi tải với trạng thái chưa có câu hỏi.

## Cập nhật 2026-07-14 - Dọn dữ liệu kiểm thử cục bộ

- Đã xóa 3 sản phẩm kiểm thử (`TEST-SKU-*`, `SMOKE-USED-*`, `test test`) cùng biến thể, lô kho test, chuỗi thu mua máy cũ và dữ liệu tìm kiếm/embedding liên quan.
- Đã xóa mã giảm giá `TESTPAY-0626`, 2 video nháp dùng để kiểm thử và các phiên AI bị nhiễm dữ liệu test; dữ liệu danh mục, thương hiệu, nhà cung cấp và sản phẩm thật được giữ nguyên.
- Lịch sử migration `091_reconcile_admin_pos_test_order.sql` được giữ lại vì đây là dấu vết phiên bản lược đồ, không phải dữ liệu nghiệp vụ test.
