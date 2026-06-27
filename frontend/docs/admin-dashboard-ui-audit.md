# Admin dashboard UI audit

## Mục tiêu sử dụng chính

Người quản trị vào dashboard để nắm nhanh tình hình vận hành cửa hàng, phát hiện cảnh báo cần xử lý ngay và đi nhanh vào các luồng quan trọng.

## 3 hành động quan trọng nhất

- Xử lý đơn hàng đang chờ.
- Cập nhật sản phẩm, tồn kho và danh mục.
- Kiểm tra cảnh báo về voucher, đánh giá, tồn kho và doanh thu.

## Cảnh báo cần nổi bật

- Đơn hàng chờ xử lý.
- Tồn kho âm hoặc sắp hết hàng.
- Voucher đã dùng gần hết ngân sách.
- Đánh giá mới cần kiểm duyệt.

## Kiểm tra theo 5 tiêu chí

- Phân cấp thị giác: phần tổng quan cũ có nhiều thẻ (card) cùng độ nặng, không có tầng ưu tiên rõ.
- Mật độ thông tin: nhiều khối cạnh nhau ngang cấp, mắt người dùng phải quét qua nhiều vùng.
- Tính nhất quán: padding, radius, màu trạng thái và shadow chưa có quy tắc chung.
- Tốc độ quét mắt: thanh bên (sidebar) quá nhiều mục ngang cấp, ô tìm kiếm chưa thay đổi theo ngữ cảnh.
- Độ rõ của hành động chính: các hành động nhập (import), xuất (export), thêm mới, sửa, xóa đang nằm gần nhau và cần tách cấp ưu tiên.

## Ưu tiên cao

- Sửa các văn bản lỗi mã hóa ở vùng admin hiển thị chính.
- Tạo mini design system cho card, metric, alert, table và form.
- Rút gọn điều hướng (navigation) thành nhóm: Tổng quan, Kinh doanh, Catalog, Vận hành, Khách hàng, Hệ thống.
- Tái cấu trúc tổng quan thành KPI, cảnh báo, biểu đồ và danh sách vận hành.

## Ưu tiên trung bình

- Chia biểu mẫu (form) dài thành các phần rõ ràng hơn.
- Làm sticky header và các nút hành động trên dòng gọn hơn cho bảng.
- Chuẩn hóa microcopy trạng thái và hành động.

## Ưu tiên thấp

- Tinh chỉnh hiệu ứng động (animation) nhỏ.
- Thêm dashboard theo vai trò sau khi các mô-đun chính đã ổn định.

## Giữ lại

- Logic API và phân quyền (permission) hiện có.
- Recharts cho biểu đồ doanh thu.
- Ant Design cho shell, menu, input và action bar.
- Màu đỏ thương hiệu cho CTA và điểm cần chú ý.

## Cần thay đổi

- Thanh bên phẳng chuyển thành các nhóm điều hướng.
- Tổng quan không còn là tập hợp thẻ ngang cấp.
- Tìm kiếm phải có placeholder theo tab.
- Card, alert và metric dùng chung một nhịp spacing và border.

## Cập nhật 2026-05-22

- Đã nhóm lại điều hướng admin theo: Tổng quan, Kinh doanh, Catalog, Vận hành, Khách hàng, Hệ thống.
- Đã đổi sidebar sang bề mặt sáng, bo góc lớn hơn và dùng accent indigo để giảm cảm giác nặng của màu đỏ.
- Đã nâng cấp thanh công cụ phía trên (top bar) để thanh tìm kiếm thay đổi theo tab và làm nổi bật thao tác quan trọng.
- Đã làm mới thẻ KPI tổng quan theo hướng thẻ trắng, gradient nhẹ, huy hiệu icon và xu hướng (trend chip).
- Đã chuẩn hóa thêm nội dung hiển thị cho shell admin và một phần tiêu đề dashboard để giảm lỗi font ở vùng nhìn thấy ngay.
- Đã tăng độ tương phản (contrast) cho bảng dữ liệu bằng nền header màu slate nhẹ và đường tách border rõ hơn.
- Đã bắt đầu đồng bộ nút kêu gọi hành động (CTA) chính sang tông màu indigo để gần gũi hơn với trạng thái kích hoạt thanh bên và ngôn ngữ hành động chính.
- Đã bổ sung thêm một lớp bo góc lớn hơn cho bảng và nút hành động để tổng thể gần gũi hơn với giao diện quản trị dạng SaaS.
- Đã đổi top bar va sidebar sang tông đỏ rất nhạt để gần với định hướng màu thương hiệu nhưng vẫn giữ nền giao diện nhẹ nhàng.
- Đã làm dịu màu nút bấm và ô tìm kiếm theo hướng rose nhạt để giảm cảm giác nặng nề của CTA.
- Đã giảm độ đậm của trạng thái kích hoạt trong thanh bên, ưu tiên nền màu rất nhạt và chữ slate đậm vừa phải thay vị đen/trắng quá tương phản.
- Đã đổi biểu tượng của mục đang hoạt động sang nền sáng hơn và icon màu slate đậm để tránh bị mờ khi đang chọn.
- Đã gom bớt thao tác bảng thành nút chỉnh sửa bên ngoài và menu thao tác gọn hơn để tiết kiệm chiều ngang cột.
- Đã bổ sung thanh trạng thái/giao diện phân trang ở đáy bảng để sẵn sàng cho việc mở rộng dữ liệu sau này.
- Đã tách vùng cuộn riêng cho thanh bên và nội dung chính để khi rê chuột vào khu vực nào thì khu vực đó tự cuộn độc lập.
- Đã ẩn thanh cuộn ở thanh bên và nội dung chính, nhưng vẫn giữ cơ chế cuộn độc lập theo từng vùng.

## Bước tiếp theo để hoàn thiện

- Rà soát tiếp các chuỗi tiếng Việt còn lỗi mã hóa (encoding) bên trong các popup, biểu mẫu và bảng chi tiết.
- Chuẩn hóa bảng hành động theo icon/dropdown để giảm mật độ nút.
- Tách bộ component KPI, alert và tiêu đề phần (section header) thành file riêng khi dashboard ổn định hình thức.
- Hoàn thiện breadcrumb động cho top bar và căn chỉnh lại cụm tìm kiếm, thông báo, avatar ở mọi điểm phản hồi (breakpoint).
- Tiếp tục đổi nhỏ các nút CTA chính còn lại sang tông màu indigo thay vì đen/đỏ nếu nó còn xuất hiện trong form popup.
- Tiếp tục dọn sạch các chuỗi tiếng Việt còn lỗi mã hóa trong các nhãn thao tác và phần chân (footer) bảng.
- Theo dõi thêm trải nghiệm cuộn (scroll) trên máy tính xách tay/màn hình thấp để căn chỉnh thêm độ cao của top bar nếu cần.
