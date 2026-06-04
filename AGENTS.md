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

### Có tiêu chí hoàn tất

- Với bug, cố gắng tái hiện lỗi hoặc xác định điều kiện lỗi trước khi sửa.
- Với logic quan trọng, xác định cách kiểm tra cụ thể rồi mới báo hoàn tất.
- Sau khi sửa, chạy kiểm tra phù hợp với phạm vi thay đổi nếu môi trường cho phép.
- Không báo xong chỉ vì đã sửa file; phải biết thay đổi đã được kiểm tra bằng cách nào hoặc nói rõ vì sao chưa kiểm tra được.

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
- Trước khi hoàn tất các thay đổi có chữ tiếng Việt, kiểm tra nhanh nội dung vừa sửa để bảo đảm không có lỗi ký tự như `Ä`, `á»`, `Æ`.

## Git Constraints (Quy định Git)

- TUYỆT ĐỐI KHÔNG tự ý dùng bất kỳ lệnh git nào, kể cả status, diff, add, commit, push, trong phiên làm việc. Chỉ thực hiện các lệnh git khi có yêu cầu trực tiếp từ user.

## Notes Workflow

- Khi sửa một chức năng có notes riêng, dùng CodeGraph để nắm cấu trúc, caller/callee và vùng ảnh hưởng trước khi code.
- Đọc file notes `.md` của chức năng đó trước khi sửa.
- Sau khi sửa và kiểm tra, ghi lại thay đổi quan trọng vào file notes.
- Nếu notes chưa có cho chức năng đó, tạo file notes mới trong khu vực phù hợp.
- Khi phát hiện ghi chú hoặc code cũ không còn đúng với hệ thống, cập nhật/xóa phần lỗi thời sau khi đã xác minh.
