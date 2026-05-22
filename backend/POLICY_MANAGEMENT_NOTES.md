# Policy Management Notes

## 1. Muc tieu nang cap
- Nang cap module `policies` tu CRUD co ban thanh mot phan he quan tri noi dung chinh sach co day du vong doi.
- Ho tro bien tap noi dung rich text, preview truoc khi xuat ban, SEO theo tung chinh sach, hẹn lich cong khai, scope theo danh muc hoac san pham.
- Ghi nhan lich su thay doi, phien ban va audit log de phuc vu truy vet nghiep vu va kiem soat thay doi.

## 2. Dac ta quy trinh nghiep vu

### 2.1. Luong khoi tao / cap nhat chinh sach
1. Quan tri vien truy cap khu vuc Quan Ly Chinh Sach.
2. He thong tai danh sach chinh sach hien co de quan tri vien tra cuu va thao tac.
3. Quan tri vien nhap thong tin co ban gom ma chinh sach, tieu de, tom tat va noi dung.
4. Quan tri vien cau hinh pham vi ap dung: toan cuc, theo danh muc, theo san pham, hoac hon hop.
5. Quan tri vien cau hinh metadata SEO cho tung chinh sach.
6. Quan tri vien chon mot trong cac trang thai: `DRAFT`, `SCHEDULED`, `PUBLISHED`, `ARCHIVED`.
7. Neu chon `SCHEDULED`, quan tri vien khai bao thoi diem cong khai.
8. He thong render khu vuc preview de kiem tra noi dung truoc khi luu.
9. He thong validate du lieu, luu ban ghi vao bang `policies`, dong thoi ghi audit log.

### 2.2. Luong versioning va lich su cap nhat
1. Khi quan tri vien sua mot chinh sach ton tai, he thong doi chieu `version` hien tai.
2. Neu `version` khong khop, he thong tu choi cap nhat de tranh xung dot ghi de.
3. Neu hop le, he thong tang `version = version + 1`.
4. He thong tao snapshot du lieu sau cap nhat va luu vao bang `policy_versions`.
5. He thong ghi nhan actor thuc hien, hanh dong va thoi diem cap nhat.

### 2.3. Luong xuat ban va hien thi storefront
1. Khach hang truy cap trang chinh sach.
2. API doc chi thuc hien truy van, khong phat sinh cap nhat trang thai trong luong `GET`.
3. He thong chi tra ve cac chinh sach:
   - `is_active = TRUE`
   - `status = 'PUBLISHED'` hoac `(status = 'SCHEDULED' AND scheduled_at <= NOW())`
4. Frontend sanitize HTML va render noi dung sau khi da loai bo script nguy hiem.

### 2.4. Luong luu tru / an chinh sach
1. Quan tri vien chon an hoac luu tru chinh sach.
2. He thong khong xoa cung du lieu.
3. Ban ghi duoc chuyen sang `ARCHIVED`, `is_active = FALSE`, tang `version`, luu snapshot va audit log.

## 3. Tu dien du lieu (Data Dictionary)

| Thuoc tinh | Kieu du lieu | Mo ta | Rang buoc |
|---|---|---|---|
| `code` | `VARCHAR(80)` | Ma dinh danh chinh sach | `UNIQUE`, `NOT NULL` |
| `title` | `VARCHAR(255)` | Tieu de chinh sach | `NOT NULL` |
| `summary` | `TEXT` | Mo ta ngan dung cho preview va listing | Default `''` |
| `content` | `TEXT` | Noi dung rich text dang HTML | Default `''` |
| `is_active` | `BOOLEAN` | Co cho phep hien thi hay khong | Default `TRUE` |
| `status` | `VARCHAR(30)` | Trang thai vong doi | `DRAFT`, `SCHEDULED`, `PUBLISHED`, `ARCHIVED` |
| `scheduled_at` | `TIMESTAMPTZ` | Thoi diem hen cong khai | Nullable |
| `published_at` | `TIMESTAMPTZ` | Thoi diem public thuc te | Nullable |
| `seo_title` | `VARCHAR(255)` | Tieu de SEO | Default `''` |
| `seo_description` | `VARCHAR(500)` | Mo ta SEO | Default `''` |
| `seo_keywords` | `VARCHAR(500)` | Tu khoa SEO | Default `''` |
| `scope_type` | `VARCHAR(30)` | Pham vi ap dung | `GLOBAL`, `CATEGORY`, `PRODUCT`, `MIXED` |
| `product_ids` | `JSONB` | Danh sach ID san pham ap dung | Default `[]` |
| `category_ids` | `JSONB` | Danh sach ID danh muc ap dung | Default `[]` |
| `version` | `INTEGER` | Phien ban hien tai, dung cho optimistic locking | Default `1` |

## 4. Dau vao va dau ra cua he thong

### 4.1. Dau vao
- Thong tin chinh sach do quan tri vien nhap:
  - ma chinh sach
  - tieu de
  - tom tat
  - noi dung HTML
  - trang thai
  - lich cong khai
  - metadata SEO
  - danh sach danh muc / san pham ap dung
  - quy tac ap dung cho `MIXED`: logic `OR`

### 4.2. Dau ra
- Giao dien Admin:
  - danh sach chinh sach
  - form bien tap rich text
  - preview truoc xuat ban
  - lich su phien ban
- Tang he thong:
  - ban ghi chinh trong bang `policies`
  - snapshot lich su trong bang `policy_versions`
  - audit log thao tac
- Giao dien khach hang:
  - danh sach chinh sach dang cong khai tai trang `/policy`

## 5. Yeu cau phi chuc nang va cong nghe su dung

### 5.1. Backend
- Xay dung RESTful API bang `FastAPI`.
- Validate payload bang `Pydantic`.
- Truy cap CSDL bang `SQLAlchemy AsyncSession`.
- He quan tri CSDL: `PostgreSQL`.

### 5.2. Frontend
- Xay dung giao dien bang `React` + `TypeScript`.
- Hien tai editor rich text dang la toolbar nhe dua tren `contentEditable`.
- De huong enterprise ro hon, co the nang cap sau sang `Quill`, `TinyMCE`, `TipTap` hoac `Slate`.

### 5.3. Bao mat va toan ven du lieu
- Ap dung `Optimistic Locking` thong qua truong `version` de ngan `Lost Update`.
- Frontend su dung `DOMPurify` de sanitize HTML truoc khi render preview va storefront, giam rui ro `XSS`.
- Luu `audit log` va `snapshot history` de truy vet thay doi.

### 5.4. Co che tu dong hoa cho SCHEDULED
- Trong phien ban hien tai da bo co che `publish on read` de tranh anti-pattern Read/Write trong `GET`.
- Read path storefront va AI chi truy van theo dieu kien:
  - `status = 'PUBLISHED'`
  - hoac `status = 'SCHEDULED' AND scheduled_at <= NOW()`
- Trang thai vat ly trong database nen duoc dong bo bang worker nen:
  - `Cronjob`
  - `Celery Beat`
  - hoac background scheduler tuong duong
- Cach tiep can nay giu dung chuan RESTful, than thien voi cache, va de mo rong quy mo he thong.

### 5.5. Quy tac nghiep vu cho `scope_type = MIXED`
- Rule duoc chot la logic `OR`.
- Nghia la chinh sach se ap dung neu:
  - doi tuong thuoc mot trong cac `category_ids`
  - hoac doi tuong nam trong danh sach `product_ids`
- He thong khong ap dung logic `AND`.
- Ly do chon `OR`:
  - de phu hop ngu canh marketing/van hanh thuc te
  - de tranh bo sot san pham le can gan chinh sach dac biet
  - de de giai thich va de kiem thu hon khi mo rong

## 6. Ghi chu ky thuat bo sung
- Bang `policy_versions` luu snapshot sau moi lan `CREATED`, `UPDATED`, `ARCHIVED`.
- Storefront va AI chi doc cac policy da `PUBLISHED` hoac `SCHEDULED` nhung da toi lich.
- Cac thay doi lien quan den module nay can tiep tuc cap nhat tai file note nay thay vi tao tai lieu roi rac moi.

## 7. Tep lien quan
- `backend/app/api/v1/routers/admin.py`
- `backend/app/api/v1/routers/storefront.py`
- `backend/app/application/ai/use_cases.py`
- `backend/migrations/040_policy_management_upgrade.sql`
- `frontend/src/pages/AdminDashboard.tsx`
- `frontend/src/pages/PolicyPage.tsx`
- `frontend/src/services/apiDb.ts`
