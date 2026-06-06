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
- ToÃ n bá»™ logic truy váº¥n SQL, database transactions, hashing máº­t kháº©u, phÃ¢n quyá»n vÃ  cÃ¡c rÃ ng buá»™c nghiá»‡p vá»¥ khÃ¡c cá»§a KhÃ¡ch hÃ ng Ä‘Ã£ Ä‘Æ°á»£c chuyá»ƒn dá»‹ch hoÃ n toÃ n tá»« Router (`admin_customers.py`) sang Service Layer chuyÃªn biá»‡t: [customer_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/customer_service.py).
- File router [admin_customers.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/api/v1/routers/admin_customers.py) Ä‘Æ°á»£c lÃ m má»ng tá»‘i Ä‘a, chá»‰ chá»‹u trÃ¡ch nhiá»‡m Ä‘á»‹nh nghÄ©a route endpoints, Dependency Injection, nháº­n dá»¯ liá»‡u Ä‘áº§u vÃ o vÃ  chuyá»ƒn tiáº¿p lá»i gá»i cho `customer_service.py`.
- CÃ¡c helper category migration cÅ© (`enqueue_category_cache_refresh`, `process_category_migration_job`, `refresh_category_cache`) Ä‘Æ°á»£c di chuyá»ƒn vÃ o `customer_service.py` vÃ  sá»­a lá»—i tiá»m áº©n `NameError` báº±ng cÃ¡ch import Ä‘áº§y Ä‘á»§ dependencies (`AsyncSessionFactory`), Ä‘á»“ng thá»i sá»­ dá»¥ng import cá»¥c bá»™ Ä‘á»ƒ ngÄƒn lá»—i circular import.

### 2. Frontend Feature-First Architecture
- Module Quáº£n lÃ½ KhÃ¡ch hÃ ng Ä‘Æ°á»£c Ä‘Ã³ng gÃ³i hoÃ n chá»‰nh trong thÆ° má»¥c tÃ­nh nÄƒng Ä‘á»™c láº­p táº¡i: [src/features/admin-customers/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/)
  - **Services**: [adminCustomersApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/services/adminCustomersApi.ts) Ä‘áº£m nháº­n gá»i API.
  - **Hooks**: [useAdminCustomersLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/hooks/useAdminCustomersLogic.ts) xá»­ lÃ½ state vÃ  logic nghiá»‡p vá»¥ UI.
  - **Components**: [AdminCustomersTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-customers/components/AdminCustomersTab.tsx) chá»©a mÃ£ nguá»“n giao diá»‡n chÃ­nh.
- CÃ¡c file chung Ä‘iá»u phá»‘i dá»¯ liá»‡u vÃ  hiá»ƒn thá»‹ tab Admin nhÆ° [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), vÃ  [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx) Ä‘Ã£ Ä‘Æ°á»£c cáº­p nháº­t Ä‘Æ°á»ng dáº«n import má»›i.

### 3. Frontend Feature-First Architecture cho PhÃ¢n quyá»n (Permissions & Roles)
- Module Quáº£n lÃ½ PhÃ¢n quyá»n Ä‘Æ°á»£c tÃ¡ch biá»‡t hoÃ n toÃ n khá»i module khÃ¡ch hÃ ng vÃ  Ä‘Ã³ng gÃ³i Ä‘á»™c láº­p táº¡i: [src/features/admin-permissions/](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/)
  - **Services**: [adminPermissionsApi.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/services/adminPermissionsApi.ts) chá»©a cÃ¡c API gá»i phÃ¢n quyá»n vÃ  vai trÃ² riÃªng biá»‡t.
  - **Hooks**: [useAdminPermissionsLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/hooks/useAdminPermissionsLogic.ts) xá»­ lÃ½ state UI vÃ  tÆ°Æ¡ng tÃ¡c phÃ¢n quyá»n.
  - **Components**: [AdminPermissionsTab.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-permissions/components/AdminPermissionsTab.tsx) lÃ  thÃ nh pháº§n UI chÃ­nh Ä‘iá»u khiá»ƒn ma tráº­n phÃ¢n quyá»n.
- CÃ¡c API phÃ¢n quyá»n cÅ© náº±m trong `adminCustomersApi.ts` Ä‘Ã£ Ä‘Æ°á»£c dá»n dáº¹p sáº¡ch sáº½ Ä‘á»ƒ Ä‘áº£m báº£o Single Responsibility Principle.
- ÄÃ£ cáº­p nháº­t Ä‘áº§y Ä‘á»§ import liÃªn káº¿t táº¡i [apiDb.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/legacy apiDb.ts), [useAdminLogic.ts](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/hooks/useAdminLogic.ts), vÃ  [AdminDashboardTabContent.tsx](file:///c:/Users/Huynh%20Nhu/Downloads/Project/frontend/src/features/admin-shell/components/AdminDashboardTabContent.tsx).
- BiÃªn dá»‹ch toÃ n bá»™ Frontend báº±ng `npx tsc --noEmit` hoÃ n táº¥t thÃ nh cÃ´ng 100% khÃ´ng phÃ¡t sinh lá»—i compile.

### 4. Backend Customer Service Repository Split (June 2026)
- TÃ¡ch má»™t lÆ°á»£ng lá»›n SQL Ä‘á»c dá»¯ liá»‡u khá»i [customer_service.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/application/services/customer_service.py) sang lá»›p [customer_repo.py](file:///c:/Users/Huynh%20Nhu/Downloads/Project/backend/app/infrastructure/database/repositories/customer_repo.py) má»›i.
- CÃ¡c hÃ m Ä‘Ã£ chuyá»ƒn xuá»‘ng Repository gá»“m: Danh sÃ¡ch khÃ¡ch hÃ ng admin, chi tiáº¿t khÃ¡ch hÃ ng, tag khÃ¡ch hÃ ng, tÃ³m táº¯t ghi chÃº (notes), sá»‘ lÆ°á»£ng voucher cá»§a khÃ¡ch hÃ ng, danh sÃ¡ch Ä‘Æ¡n hÃ ng, lá»‹ch sá»­ Ä‘iá»ƒm thÆ°á»Ÿng (loyalty history), ghi chÃº CSKH, nháº­t kÃ½ há»‡ thá»‘ng (audit logs), danh sÃ¡ch quyá»n háº¡n (permissions) vÃ  danh sÃ¡ch vai trÃ² (roles).
- Giá»¯ láº¡i cÃ¡c luá»“ng ghi nháº¡y cáº£m cÃ³ nhiá»u side-effect (nhÆ° cáº­p nháº­t tag, táº¡o ghi chÃº CSKH, Ä‘iá»u chá»‰nh Ä‘iá»ƒm thÆ°á»Ÿng, cáº¥p phÃ¡t voucher, táº¡o nhÃ¢n viÃªn, thay Ä‘á»•i vai trÃ²/quyá»n háº¡n vÃ  vÃ´ hiá»‡u hÃ³a hÃ ng loáº¡t) trá»±c tiáº¿p táº¡i Service Ä‘á»ƒ giá»¯ an toÃ n tá»‘i Ä‘a cho luá»“ng nghiá»‡p vá»¥.
- Káº¿t quáº£ kiá»ƒm tra: biÃªn dá»‹ch toÃ n bá»™ backend báº±ng `.venv` thÃ nh cÃ´ng; náº¡p (import) `app.main`, `customer_service` vÃ  `customer_repo` hoáº¡t Ä‘á»™ng bÃ¬nh thÆ°á»ng.

