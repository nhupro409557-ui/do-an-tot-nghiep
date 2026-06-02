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
