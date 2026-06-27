# Quản lý khách hàng và phân quyền

## Phạm vi hiện tại

- Danh sách khách hàng trong Admin hỗ trợ tìm theo tên, email, vai trò, hạng và trạng thái.
- Danh sách khách hàng đã bổ sung phân trang với `page`, `limit`, `total`.
- Trang chi tiết khách hàng được tổ chức theo mô hình "Khách hàng 360 độ".
- Phân quyền vẫn theo hướng RBAC + PBAC:
  - role quyết định nhóm quyền
  - permission quyết định thao tác cụ thể

## Phần mở rộng đã thêm

### 1. Khách hàng 360 độ

- API `GET /admin/customers/{user_id}/overview` trả về tổng quan nhanh:
  - thông tin cơ bản
  - tổng chi tiêu
  - số đơn
  - điểm hiện có
  - số voucher
  - số ghi chú
  - tag
- Dữ liệu chi tiết được tải treo theo tab UI:
  - `orders`
  - `loyalty-history`
  - `notes`
  - `audit-logs`

### 2. Hỗ trợ CSKH

- Gán tag khách hàng bằng `customer_tags`.
- Ghi chú CSKH bằng `customer_notes`.
- Cộng/trừ điểm thủ công có lý do, ghi vào `loyalty_transactions` với `type = ADJUST`.
- Gửi voucher riêng cho khách bằng `user_vouchers`.

### 3. Nhật ký và truy vết

- Khi đổi vai trò/trạng thái user: ghi `admin_user_access_updated`.
- Khi tạo nhân viên admin: ghi `admin_staff_created`.
- Khi cấp quyền bổ sung riêng cho nhân viên: ghi `admin_user_permissions_updated`.
- Khi đổi ma trận quyền role: ghi `admin_role_permissions_updated`.
- Khi cập nhật tag/ghi chú/điểm/voucher khách hàng: ghi security audit log tương ứng.
- UI tab phân quyền có khu vực hiển thị nhật ký đổi quyền gần đây.

### 4. Quản lý nhân viên admin

- Tab Phân quyền có khu tạo tài khoản nhân viên và danh sách nhân viên admin.
- Tài khoản nhân viên mới luôn có role `STAFF_ADMIN` và chỉ nhận quyền cơ bản từ `role_permissions`.
- Backend `POST /admin/staff` bỏ qua `permissionCodes` khi tạo mới để tránh cấp quyền cao ngay lúc tạo.
- Super Admin cấp thêm quyền riêng sau qua `user_permissions` bằng `PUT /admin/users/{user_id}/permissions`.
- Super Admin không được tạo/promote từ luồng quản lý nhân viên; thao tác này vẫn bị chặn ở backend.
- Màn nhân viên không hiển thị tài khoản `SUPER_ADMIN`; backend cũng chặn sửa role/trạng thái/quyền riêng của `SUPER_ADMIN` qua các API quản lý nhân viên.
- Ma trận phân quyền chỉ hiện/cập nhật role `STAFF_ADMIN`; checkbox mặc định bị khóa, chỉ mở sau khi bấm nút chỉnh sửa quyền để tránh bấm nhầm.
- Quyền riêng chỉ được cấp cho user có role `STAFF_ADMIN`, không cấp trực tiếp cho khách hàng.

### 5. Vận hành hàng loạt

- Khóa nhiều tài khoản cùng lúc.
- Gán tag cho nhiều khách hàng cùng lúc.
- Các thao tác hàng loạt đều ghi audit log riêng.

## Quyền đang sử dụng

- `customer:read`
- `customer:update`
- `customer:loyalty_adjust`
- `customer:issue_voucher`
- `sys:manage_users`
- `sys:manage_roles`

## Ghi chú kỹ thuật quan trọng

### 1. Kiểm soát đồng thời (Concurrency control)

- Cộng/trừ điểm thủ công sử dụng `SELECT ... FOR UPDATE` trên bảng `users`.
- Cấp voucher riêng khóa cả `users` và `vouchers` bằng `FOR UPDATE` trước khi ghi.
- Mục tiêu:
  - Tránh race condition khi 2 admin cùng thao tác trên 1 khách
  - Đảm bảo số dư điểm và trạng thái cấp voucher nhất quán

### 2. Phân trang và hiệu năng (Pagination & Performance)

- API danh sách khách hàng đã có:
  - `page`
  - `limit`
  - `total`
- Tìm kiếm được đẩy xuống SQL thay vì lọc toàn bộ ở frontend.
- Hướng tối ưu tiếp theo:
  - B-Tree index cho `email`
  - Lower index hoặc trigram index cho `full_name`
  - Tối ưu thêm cho `role`, `status`, `loyalty_tier` nếu dữ liệu lớn

### 3. Soft delete và toàn vẹn dữ liệu

- User vẫn theo hướng soft delete nghiệp vụ:
  - `status = DELETED`
  - `deleted_at`
- Danh sách Admin bỏ qua user đã xóa.
- Tag hiện tại là dữ liệu phụ trợ, đang xóa-thay thế trực tiếp khi admin lưu lại bộ tag.
- Ghi chú CSKH hiện đang append-only, chưa mở chức năng xóa/sửa để tránh mất lịch sử.

### 4. Xác thực và chống gian lận (Validation & Anti-fraud)

- Ghi chú CSKH giới hạn `max_length = 4000`.
- Điều chỉnh điểm:
  - Không cho `delta = 0`
  - Không cho âm số dư
  - Có giới hạn tổng biến động thủ công theo admin mỗi ngày
- Voucher riêng:
  - Không cấp trùng voucher còn hiệu lực cho cùng khách

### 5. Phiên làm việc và bộ nhớ đệm quyền (Session & Permission cache)

- Khi đổi role hoặc role-permission:
  - Thu hồi (revoke) refresh sessions liên quan
  - Ghi `auth_session_revocations`
  - Xóa cache `admin_permissions:{user_id}`

## API hiện có

### Danh sách và tổng quan

- `GET /admin/customers`
- `GET /admin/customers/{user_id}`
- `GET /admin/customers/{user_id}/overview`

### Chi tiết theo tab

- `GET /admin/customers/{user_id}/orders`
- `GET /admin/customers/{user_id}/loyalty-history`
- `GET /admin/customers/{user_id}/notes`
- `GET /admin/customers/{user_id}/audit-logs`

### Cập nhật đơn lẻ

- `PUT /admin/customers/{user_id}/tags`
- `POST /admin/customers/{user_id}/notes`
- `POST /admin/customers/{user_id}/loyalty-adjustments`
- `POST /admin/customers/{user_id}/vouchers`
- `PATCH /admin/users/{user_id}/role`

### Cập nhật hàng loạt

- `PUT /admin/customers/tags/bulk`
- `PATCH /admin/users/status/bulk`

### Phân quyền

- `GET /admin/permissions`
- `GET /admin/roles`
- `GET /admin/roles/{role_id}/permissions`
- `PUT /admin/roles/{role_id}/permissions`
- `POST /admin/staff`
- `GET /admin/users/{user_id}/permissions`
- `PUT /admin/users/{user_id}/permissions`

## Hướng mở rộng tiếp theo

- Chỉnh sửa/xóa ghi chú CSKH có versioning.
- Soft delete cho tag nếu cần bảo toàn lịch sử gán/bỏ tag.
- Bulk role update có workflow xác nhận.
- Timeline hợp nhất đơn hàng, điểm, voucher, ghi chú, log bảo mật trên cùng một trục thời gian.

## Update 2026-06-18 Staff Admin theo quyền riêng từng tài khoản

- `STAFF_ADMIN` chỉ còn là loại tài khoản nhân viên nội bộ, không còn là nhóm quyền nghiệp vụ dùng chung.
- Migration `073_staff_admin_per_account_permissions.sql` thu hồi toàn bộ `role_permissions` của role `STAFF_ADMIN`.
- Seed tổng `init_database.sql` có bước cleanup cuối để bảo đảm dữ liệu khởi tạo mới cũng không cấp quyền hàng loạt cho tất cả Staff Admin.
- Backend chặn cập nhật ma trận quyền cho role `STAFF_ADMIN`; Super Admin phải cấp quyền trực tiếp cho từng nhân viên qua `user_permissions`.
- Màn hình phân quyền bỏ ma trận checkbox theo role, chỉ giữ danh sách nhân viên và nút chỉnh quyền riêng cho từng tài khoản.
- Nhân viên mới tạo mặc định chưa có quyền nghiệp vụ. Tài khoản vẫn đăng nhập được khu vực admin bằng role staff, nhưng chỉ thấy/sử dụng chức năng sau khi được cấp permission riêng.

## Refactor Structure Notes (June 2026)

### 1. Backend Service Layer Pattern
- Toàn bộ logic truy vấn SQL, database transactions, hashing mật khẩu, phân quyền và các ràng buộc nghiệp vụ khác của Khách hàng đã được chuyển dịch hoàn toàn từ Router (`admin_customers.py`) sang Service Layer chuyên biệt: [customer_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/customer_service.py).
- File router [admin_customers.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_customers.py) được làm mỏng tối đa, chỉ chịu trách nhiệm định nghĩa route endpoints, Dependency Injection, nhận dữ liệu đầu vào và chuyển tiếp lời gọi cho `customer_service.py`.
- Các helper category migration cũ (`enqueue_category_cache_refresh`, `process_category_migration_job`, `refresh_category_cache`) được di chuyển vào `customer_service.py` và sửa lỗi tiềm ẩn `NameError` bằng cách import đầy đủ dependencies (`AsyncSessionFactory`), đồng thời sử dụng import cục bộ để ngăn lỗi circular import.

### 2. Frontend Feature-First Architecture
- Module Quản lý Khách hàng được đóng gói hoàn chỉnh trong thư mục tính năng độc lập tại: [src/features/admin-customers/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/)
  - **Services**: [adminCustomersApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/services/adminCustomersApi.ts) đảm nhận gọi API.
  - **Hooks**: [useAdminCustomersLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/hooks/useAdminCustomersLogic.ts) xử lý state và logic nghiệp vụ UI.
  - **Components**: [AdminCustomersTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/components/AdminCustomersTab.tsx) chứa mã nguồn giao diện chính.

### 3. Frontend Feature-First Architecture cho Phân quyền (Permissions & Roles)
- Module Quản lý Phân quyền được tách biệt hoàn toàn khỏi module khách hàng và đóng gói độc lập tại: [src/features/admin-permissions/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/)
  - **Services**: [adminPermissionsApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/services/adminPermissionsApi.ts) chứa các API gọi phân quyền và vai trò riêng biệt.
  - **Hooks**: [useAdminPermissionsLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/hooks/useAdminPermissionsLogic.ts) xử lý state UI và tương tác phân quyền.
  - **Components**: [AdminPermissionsTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/components/AdminPermissionsTab.tsx) là thành phần UI chính điều khiển ma trận phân quyền.
- Các API phân quyền cũ nằm trong `adminCustomersApi.ts` đã được dọn dẹp sạch sẽ để đảm bảo Single Responsibility Principle.
- Biên dịch toàn bộ Frontend bằng `npx tsc --noEmit` hoàn tất thành công 100% không phát sinh lỗi compile.

### 4. Backend Customer Service Repository Split (June 2026)
- Tách một lượng lớn SQL đọc dữ liệu khỏi [customer_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/customer_service.py) sang lớp [customer_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/customer_repo.py) mới.
- Các hàm đã chuyển xuống Repository gồm: Danh sách khách hàng admin, chi tiết khách hàng, tag khách hàng, tóm tắt ghi chú (notes), số lượng voucher của khách hàng, danh sách đơn hàng, lịch sử điểm thưởng (loyalty history), ghi chú CSKH, nhật ký hệ thống (audit logs), danh sách quyền hạn (permissions) và danh sách vai trò (roles).
- Giữ lại các luồng ghi nhạy cảm có nhiều side-effect (như cập nhật tag, tạo ghi chú CSKH, điều chỉnh điểm thưởng, cấp phát voucher, tạo nhân viên, thay đổi vai trò/quyền hạn và vô hiệu hóa hàng loạt) trực tiếp tại Service để giữ an toàn tối đa cho luồng nghiệp vụ.
- Kết quả kiểm tra: biên dịch toàn bộ backend bằng `.venv` thành công; nạp (import) `app.main`, `customer_service` và `customer_repo` hoạt động bình thường.
