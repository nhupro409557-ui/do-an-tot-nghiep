# AGENTS.md

## CodeGraph

Project này đã được khởi tạo CodeGraph trong thư mục `.codegraph/`.

Dùng CodeGraph cho câu hỏi cấu trúc code:

- Tìm symbol, function, class: `codegraph_search`
- Xem ngữ cảnh một tính năng: `codegraph_context`
- Xem source nhiều symbol liên quan: `codegraph_explore`
- Xem file tree theo index: `codegraph_files`
- Xem caller/callee/impact: `codegraph_callers`, `codegraph_callees`, `codegraph_impact`

Khi cần đọc text thường, log, nội dung hiển thị UI, vẫn dùng `rg`/đọc file trực tiếp.

Nếu cần index lại, tránh để CodeGraph quét các thư mục sinh tự động như:

- `backend/.venv`
- `backend/venv`
- `**/__pycache__`
- `.codegraph`
- `*.log`

## Testing Preference

- Không tự chạy test sau mỗi lần sửa nhỏ.
- Chỉ chạy test khi user yêu cầu trực tiếp hoặc khi đã hoàn thành toàn bộ cụm chức năng/đồ án và user đồng ý.
- Nếu thay đổi có rủi ro cao, chỉ báo nên test phần đó, không tự chạy test khi chưa được user cho phép.
- Vẫn được đọc file, tìm code, phân tích cấu trúc và chạy các lệnh nhẹ cần thiết để hiểu vấn đề; tránh các lệnh test/verify tốn thời gian cho đến giai đoạn kiểm tra tổng thể.

## Coding Discipline

Các nguyên tắc này được chắt lọc từ bộ hướng dẫn `andrej-karpathy-skills` để giảm lỗi thường gặp khi agent sửa code.

### Nghĩ trước khi code

- Không tự âm thầm chọn một cách hiểu nếu yêu cầu còn mơ hồ.
- Nêu rõ giả định quan trọng trước khi triển khai.
- Nếu có nhiều cách hiểu hợp lý, trình bày ngắn gọn các hướng và hỏi lại khi lựa chọn đó ảnh hưởng lớn đến kết quả.
- Nếu phát hiện yêu cầu có rủi ro, mâu thuẫn hoặc có cách đơn giản hơn rõ ràng, nói thẳng và đề xuất hướng tốt hơn.

### Ưu tiên đơn giản

- Viết lượng code tối thiểu đủ giải quyết đúng yêu cầu.
- Không thêm tính năng, cấu hình, framework, abstraction hoặc xử lý ngoại lệ ngoài phạm vi cần thiết.
- Không tạo abstraction cho code chỉ dùng một lần.
- Nếu một thay đổi có thể làm bằng cách nhỏ, rõ, dễ kiểm tra thì ưu tiên cách đó.

### Sửa đúng phạm vi

- Chỉ sửa những dòng/file liên quan trực tiếp đến yêu cầu.
- Không refactor, đổi format, đổi comment hoặc “dọn dẹp” code lân cận nếu không cần để hoàn thành việc chính.
- Giữ phong cách code hiện có của project, kể cả khi có thể viết theo style khác.
- Nếu thay đổi của mình làm phát sinh import/biến/hàm không dùng nữa thì dọn phần đó.
- Nếu thấy code chết hoặc vấn đề không liên quan, chỉ ghi nhận hoặc báo lại, không tự xóa khi chưa được yêu cầu.

### Tách module mới khỏi luồng chính

- Trước khi code, kiểm tra chức năng được yêu cầu đã thuộc module nào trong hệ thống hay chưa.
- Nếu chức năng thuộc phạm vi của module hiện có, mở rộng đúng module đó và tái sử dụng service, model, API, component hoặc dữ liệu hiện có; không tạo module mới trùng trách nhiệm.
- Nếu đây là một module nghiệp vụ mới, độc lập và chưa tồn tại trong hệ thống, tạo file hoặc thư mục module riêng theo cấu trúc hiện có của project thay vì viết toàn bộ logic trực tiếp vào file luồng chính.
- File luồng chính như entrypoint, router tổng, dashboard tổng hoặc file cấu hình chỉ nên chứa phần đăng ký, điều phối, import và kết nối tối thiểu tới module mới.
- Không đưa logic nghiệp vụ lớn, truy vấn dữ liệu, xử lý trạng thái hoặc giao diện phức tạp của module mới vào file luồng chính.
- Chỉ tách file khi có ranh giới trách nhiệm rõ ràng; thay đổi rất nhỏ, chỉ dùng một lần và không làm nặng luồng chính thì không cần tạo module riêng máy móc.

### Có tiêu chí hoàn tất

- Với bug, cố gắng tái hiện lỗi hoặc xác định điều kiện lỗi trước khi sửa.
- Với logic quan trọng, xác định cách kiểm tra cụ thể rồi mới báo hoàn tất.
- Sau khi sửa, chạy kiểm tra phù hợp với phạm vi thay đổi nếu môi trường cho phép.
- Không báo xong chỉ vì đã sửa file; phải biết thay đổi đã được kiểm tra bằng cách nào hoặc nói rõ vì sao chưa kiểm tra được.

### Tự đánh giá sau khi code

- Sau mỗi lần sửa code, tự đánh giá ngắn gọn phần vừa làm trước khi báo hoàn tất.
- Bắt buộc trong phản hồi hoàn tất sau mỗi lần sửa code phải có mục `Tự đánh giá`, gồm `Điểm`, `Chưa được` và `Hướng giải quyết`; không chờ user hỏi mới đánh giá.
- Đánh giá phải nghiêm khắc, thực chất, không qua loa cho có; nếu còn rủi ro, thiếu kiểm thử, code chưa gọn hoặc có giả định yếu thì phải nói thẳng.
- Báo điểm chất lượng cho lần sửa đó, ví dụ `8/10`, dựa trên độ đúng yêu cầu, độ gọn, mức độ rủi ro và mức kiểm tra đã chạy.
- Chỉ ra rõ chỗ chưa được, rủi ro còn lại hoặc phần chưa kiểm tra được.
- Đưa hướng giải quyết hoặc cải thiện tiếp theo cho các điểm chưa tốt, ưu tiên hướng đơn giản và đúng phạm vi.

## Maintenance Notes

- Trước khi sửa product/category/inventory/service, đọc các file:
  - `backend/PRODUCT_MANAGEMENT_NOTES.md`
  - `backend/CATEGORY_MANAGEMENT_NOTES.md`
  - `backend/INVENTORY_MANAGEMENT_NOTES.md`
- Mỗi lần sửa logic quan trọng, cập nhật file notes tương ứng để lần sau dễ tiếp tục.

## Vietnamese Text Quality

- Khi tạo hoặc sửa code, giao diện, thông báo lỗi, tài liệu `.md`, seed data hoặc dữ liệu hiển thị cho người dùng, phải dùng tiếng Việt có dấu đầy đủ.
- Không viết tiếng Việt không dấu cho nội dung mới, trừ khi đó là mã định danh kỹ thuật bắt buộc như tên biến, tên file, slug, key JSON hoặc lệnh hệ thống.
- Tránh làm hỏng mã hóa tiếng Việt. Nếu thấy nội dung bị lỗi font/mã hóa, sửa lại sang Unicode UTF-8 đúng dấu khi đang chỉnh cùng khu vực đó.
- Sau mỗi lần sửa code, trước khi báo hoàn tất, kiểm tra nhanh các file vừa chỉnh để bảo đảm nội dung tiếng Việt có dấu đầy đủ và không có lỗi ký tự như `Ä`, `á»`, `Æ`.

## UTF-8 Runtime Defaults

- Mọi file văn bản trong repo phải được lưu bằng UTF-8 theo `.editorconfig`.
- Khi chạy backend/frontend trên Windows, ưu tiên dùng:
  - `.\scripts\run-backend.ps1`
  - `.\scripts\run-frontend.ps1`
- Khi phải chạy Python trực tiếp trong PowerShell, đặt encoding trước lệnh:
  - `$env:PYTHONUTF8="1"`
  - `$env:PYTHONIOENCODING="utf-8"`
  - `[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)`
  - `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`
- Không ghi log hoặc xuất file tiếng Việt bằng encoding mặc định của Windows nếu có thể chỉ định UTF-8 rõ ràng.

## Git Constraints (Quy định Git)

- TUYỆT ĐỐI KHÔNG tự ý dùng bất kỳ lệnh git nào, kể cả status, diff, add, commit, push, trong phiên làm việc. Chỉ thực hiện các lệnh git khi có yêu cầu trực tiếp từ user.

## Notes Workflow

- Khi sửa một chức năng có notes riêng, dùng CodeGraph để nắm cấu trúc, caller/callee và vùng ảnh hưởng trước khi code.
- Đọc file notes `.md` của chức năng đó trước khi sửa.
- Sau khi sửa và kiểm tra, ghi lại thay đổi quan trọng vào file notes.
- Nếu notes chưa có cho chức năng đó, tạo file notes mới trong khu vực phù hợp.
- Khi phát hiện ghi chú hoặc code cũ không còn đúng với hệ thống, cập nhật/xóa phần lỗi thời sau khi đã xác minh.

## Runtime IPN / Cloudflare Tunnel

- Trước mỗi lần chạy đồ án có kiểm thử thanh toán/IPN, bắt buộc bật Cloudflare Tunnel trước backend/frontend để có URL public nhận webhook:
  - `cloudflared tunnel --url http://localhost:8000`
- Sau khi Cloudflare in ra URL dạng `https://<subdomain>.trycloudflare.com`, cập nhật lại các IPN/callback trong `backend/.env` cho đúng URL mới trước khi tạo giao dịch thanh toán:
  - `MOMO_IPN_PATH=https://<subdomain>.trycloudflare.com/api/payments/momo/ipn`
  - `ZALOPAY_CALLBACK_URL=https://<subdomain>.trycloudflare.com/api/payments/zalopay/callback`
  - Với SePay, cấu hình webhook/IPN trên dashboard hoặc môi trường tích hợp trỏ về `https://<subdomain>.trycloudflare.com/api/payments/sepay/ipn`.
- Sau khi sửa `backend/.env`, phải restart backend bằng `.\scripts\run-backend.ps1` để backend nạp lại URL IPN/callback mới.
- Không dùng URL Cloudflare cũ cho lần chạy mới; tunnel tạm thời thường đổi domain, nếu env còn domain cũ thì IPN sẽ không chạy về máy local.
