# Quan ly khach hang va phan quyen

## Pham vi hien tai

- Danh sach khach hang trong Admin ho tro tim theo ten, email, vai tro, hang va trang thai.
- Danh sach khach hang da bo sung phan trang voi `page`, `limit`, `total`.
- Trang chi tiet khach hang duoc to chuc theo mo hinh "Khach hang 360 do".
- Phan quyen van theo huong RBAC + PBAC:
  - role quyet dinh nhom quyen
  - permission quyet dinh thao tac cu the

## Phan mo rong da them

### 1. Khach hang 360 do

- API `GET /admin/customers/{user_id}/overview` tra ve tong quan nhanh:
  - thong tin co ban
  - tong chi tieu
  - so don
  - diem hien co
  - so voucher
  - so ghi chu
  - tag
- Du lieu chi tiet duoc tai treo theo tab UI:
  - `orders`
  - `loyalty-history`
  - `notes`
  - `audit-logs`

### 2. Ho tro CSKH

- Gan tag khach hang bang `customer_tags`.
- Ghi chu CSKH bang `customer_notes`.
- Cong/tru diem thu cong co ly do, ghi vao `loyalty_transactions` voi `type = ADJUST`.
- Gui voucher rieng cho khach bang `user_vouchers`.

### 3. Nhat ky va truy vet

- Khi doi vai tro/trang thai user: ghi `admin_user_access_updated`.
- Khi tao nhan vien admin: ghi `admin_staff_created`.
- Khi cap quyen bo sung rieng cho nhan vien: ghi `admin_user_permissions_updated`.
- Khi doi ma tran quyen role: ghi `admin_role_permissions_updated`.
- Khi cap nhat tag/ghi chu/diem/voucher khach hang: ghi security audit log tuong ung.
- UI tab phan quyen co khu vuc hien thi nhat ky doi quyen gan day.

### 4. Quan ly nhan vien admin

- Tab Phan quyen co khu tao tai khoan nhan vien va danh sach nhan vien admin.
- Tai khoan nhan vien moi luon co role `STAFF_ADMIN` va chi nhan quyen co ban tu `role_permissions`.
- Backend `POST /admin/staff` bo qua `permissionCodes` khi tao moi de tranh cap quyen cao ngay luc tao.
- Super Admin cap them quyen rieng sau qua `user_permissions` bang `PUT /admin/users/{user_id}/permissions`.
- Super Admin khong duoc tao/promote tu luong quan ly nhan vien; thao tac nay van bi chan o backend.
- Man nhan vien khong hien thi tai khoan `SUPER_ADMIN`; backend cung chan sua role/trang thai/quyen rieng cua `SUPER_ADMIN` qua cac API quan ly nhan vien.
- Ma tran phan quyen chi hien/cap nhat role `STAFF_ADMIN`; checkbox mac dinh bi khoa, chi mo sau khi bam nut chinh sua quyen de tranh bam nham.
- Quyen rieng chi duoc cap cho user co role `STAFF_ADMIN`, khong cap truc tiep cho khach hang.

### 5. Van hanh hang loat

- Khoa nhieu tai khoan cung luc.
- Gan tag cho nhieu khach hang cung luc.
- Cac thao tac hang loat deu ghi audit log rieng.

## Quyen dang su dung

- `customer:read`
- `customer:update`
- `customer:loyalty_adjust`
- `customer:issue_voucher`
- `sys:manage_users`
- `sys:manage_roles`

## Ghi chu ky thuat quan trong

### 1. Concurrency control

- Cong/tru diem thu cong su dung `SELECT ... FOR UPDATE` tren bang `users`.
- Cap voucher rieng khoa ca `users` va `vouchers` bang `FOR UPDATE` truoc khi ghi.
- Muc tieu:
  - tranh race condition khi 2 admin cung thao tac tren 1 khach
  - dam bao so du diem va trang thai cap voucher nhat quan

### 2. Pagination va performance

- API danh sach khach hang da co:
  - `page`
  - `limit`
  - `total`
- Tim kiem duoc day xuong SQL thay vi loc toan bo o frontend.
- Huong toi uu tiep theo:
  - B-Tree index cho `email`
  - lower index hoac trigram index cho `full_name`
  - toi uu them cho `role`, `status`, `loyalty_tier` neu du lieu lon

### 3. Soft delete va toan ven du lieu

- User van theo huong soft delete nghiep vu:
  - `status = DELETED`
  - `deleted_at`
- Danh sach Admin bo qua user da xoa.
- Tag hien tai la du lieu phu tro, dang xoa-thay the truc tiep khi admin luu lai bo tag.
- Ghi chu CSKH hien dang append-only, chua mo chuc nang xoa/sua de tranh mat lich su.

### 4. Validation va anti-fraud

- Ghi chu CSKH gioi han `max_length = 4000`.
- Dieu chinh diem:
  - khong cho `delta = 0`
  - khong cho am so du
  - co gioi han tong bien dong thu cong theo admin moi ngay
- Voucher rieng:
  - khong cap trung voucher con hieu luc cho cung khach

### 5. Session va permission cache

- Khi doi role hoac role-permission:
  - revoke refresh sessions lien quan
  - ghi `auth_session_revocations`
  - xoa cache `admin_permissions:{user_id}`

## API hien co

### Danh sach va tong quan

- `GET /admin/customers`
- `GET /admin/customers/{user_id}`
- `GET /admin/customers/{user_id}/overview`

### Chi tiet theo tab

- `GET /admin/customers/{user_id}/orders`
- `GET /admin/customers/{user_id}/loyalty-history`
- `GET /admin/customers/{user_id}/notes`
- `GET /admin/customers/{user_id}/audit-logs`

### Cap nhat don le

- `PUT /admin/customers/{user_id}/tags`
- `POST /admin/customers/{user_id}/notes`
- `POST /admin/customers/{user_id}/loyalty-adjustments`
- `POST /admin/customers/{user_id}/vouchers`
- `PATCH /admin/users/{user_id}/role`

### Cap nhat hang loat

- `PUT /admin/customers/tags/bulk`
- `PATCH /admin/users/status/bulk`

### Phan quyen

- `GET /admin/permissions`
- `GET /admin/roles`
- `GET /admin/roles/{role_id}/permissions`
- `PUT /admin/roles/{role_id}/permissions`
- `POST /admin/staff`
- `GET /admin/users/{user_id}/permissions`
- `PUT /admin/users/{user_id}/permissions`

## Huong mo rong tiep theo

- Chinh sua/xoa ghi chu CSKH co versioning.
- Soft delete cho tag neu can bao toan lich su gan/bo tag.
- Bulk role update co workflow xac nhan.
- Timeline hop nhat don hang, diem, voucher, ghi chu, log bao mat tren cung mot truc thoi gian.

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
- Các file chung điều phối dữ liệu và hiển thị tab Admin như [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), và [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx) đã được cập nhật đường dẫn import mới.

### 3. Frontend Feature-First Architecture cho Phân quyền (Permissions & Roles)
- Module Quản lý Phân quyền được tách biệt hoàn toàn khỏi module khách hàng và đóng gói độc lập tại: [src/features/admin-permissions/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/)
  - **Services**: [adminPermissionsApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/services/adminPermissionsApi.ts) chứa các API gọi phân quyền và vai trò riêng biệt.
  - **Hooks**: [useAdminPermissionsLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/hooks/useAdminPermissionsLogic.ts) xử lý state UI và tương tác phân quyền.
  - **Components**: [AdminPermissionsTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/components/AdminPermissionsTab.tsx) là thành phần UI chính điều khiển ma trận phân quyền.
- Các API phân quyền cũ nằm trong `adminCustomersApi.ts` đã được dọn dẹp sạch sẽ để đảm bảo Single Responsibility Principle.
- Đã cập nhật đầy đủ import liên kết tại [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), và [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx).
- Biên dịch toàn bộ Frontend bằng `npx tsc --noEmit` hoàn tất thành công 100% không phát sinh lỗi compile.

### 4. Backend Customer Service Repository Split (June 2026)
- Tách một lượng lớn SQL đọc dữ liệu khỏi [customer_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/customer_service.py) sang lớp [customer_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/customer_repo.py) mới.
- Các hàm đã chuyển xuống Repository gồm: Danh sách khách hàng admin, chi tiết khách hàng, tag khách hàng, tóm tắt ghi chú (notes), số lượng voucher của khách hàng, danh sách đơn hàng, lịch sử điểm thưởng (loyalty history), ghi chú CSKH, nhật ký hệ thống (audit logs), danh sách quyền hạn (permissions) và danh sách vai trò (roles).
- Giữ lại các luồng ghi nhạy cảm có nhiều side-effect (như cập nhật tag, tạo ghi chú CSKH, điều chỉnh điểm thưởng, cấp phát voucher, tạo nhân viên, thay đổi vai trò/quyền hạn và vô hiệu hóa hàng loạt) trực tiếp tại Service để giữ an toàn tối đa cho luồng nghiệp vụ.
- Kết quả kiểm tra: biên dịch toàn bộ backend bằng `.venv` thành công; nạp (import) `app.main`, `customer_service` và `customer_repo` hoạt động bình thường.

