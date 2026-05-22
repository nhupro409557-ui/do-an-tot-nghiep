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
- Khi doi ma tran quyen role: ghi `admin_role_permissions_updated`.
- Khi cap nhat tag/ghi chu/diem/voucher khach hang: ghi security audit log tuong ung.
- UI tab phan quyen co khu vuc hien thi nhat ky doi quyen gan day.

### 4. Van hanh hang loat

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

## Huong mo rong tiep theo

- Chinh sua/xoa ghi chu CSKH co versioning.
- Soft delete cho tag neu can bao toan lich su gan/bo tag.
- Bulk role update co workflow xac nhan.
- Timeline hop nhat don hang, diem, voucher, ghi chu, log bao mat tren cung mot truc thoi gian.
