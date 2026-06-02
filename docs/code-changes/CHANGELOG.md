# Change Log

## 2026-05-30 - Thong bao ket qua duyet danh gia

- Hoan thien de xuat trong `REVIEW_MANAGEMENT_NOTES.md`: khi admin doi review sang `PUBLISHED` hoac `REJECTED`, backend tao notification type `review` cho khach hang neu review co `user_id`.
- Notification chi duoc tao khi trang thai thuc su thay doi de tranh lap thong bao khi admin cap nhat ghi chu/phan hoi.
- Dong bo lai ban sao notes trong `docs/code-changes/existing-docs/backend/REVIEW_MANAGEMENT_NOTES.md`.

## 2026-05-30 - Them LangGraph cho backend

- Them dependency `langgraph>=1.0.0` vao `backend/pyproject.toml`.
- Cai dat thanh cong `langgraph 1.2.2` vao moi truong ao `backend/.venv`.
- Sua pip trong `.venv` bang bootstrap pip moi vi pip cu bi loi resolver noi bo.
- Kiem tra import va chay graph toi thieu thanh cong voi `StateGraph`.

## 2026-05-30 - Chinh lai thu vien anh kieu pixel

- Giu lai tinh than pixel/mosaic cua trang `/images` thay vi grid bang phang.
- Doi layout tu CSS `columns` masonry sang CSS grid mosaic co `row-span` de cac o cao thap khac nhau nhung it bi ho khoang trang lon.
- Backend loc bo cac URL anh placeholder nhu `placehold.co` va cac URL rong khoi thu vien anh.
- Sau khi loc placeholder, API `/catalog/images` tra 23 san pham co anh that va 63 anh.
- Frontend skeleton va image tile duoc dieu chinh theo mosaic grid moi.
- Kiem tra lai `npm run build` thanh cong va console khong co loi tren `/images`.

## 2026-05-29 - Catalog, rankings va trang hinh anh

### Bo sung nang cap modal anh va deep-link

- Them endpoint `GET /api/v1/catalog/images/resolve/{viewId}` de tim dung san pham, anh va trang theo link chia se.
- `ImagesPage` co the mo modal tu `?view=...` ngay ca khi anh khong nam trong 30 san pham cua trang hien tai.
- `ImagesModal` tach che do anh don va carousel:
  - san pham it hon 3 anh hien viewer anh lon dang tinh
  - san pham tu 3 anh tro len moi hien carousel/360
- Auto-rotate cua carousel da chuyen tu `setInterval` sang `requestAnimationFrame`.
- Modal ton trong `prefers-reduced-motion` va tat tu xoay neu nguoi dung giam chuyen dong.

### Muc tieu

- Giam tinh toan o frontend bang cach dua loc, sap xep, xep hang va tong hop hinh anh ve backend.
- Sua trang `http://localhost:3000/images` de hien danh sach hinh anh san pham theo phan trang 30 san pham moi trang.
- Sap xep thu vien anh theo diem xu huong thay vi chi dua vao thu tu du lieu frontend.
- Sua loi endpoint `/api/v1/catalog/images` khong ton tai/tra loi sai lam frontend mat danh sach hinh anh.
- Giam log loi thong bao khi nguoi dung chua dang nhap hoac phien dang nhap da het han.

### Backend

- Them loc va sap xep cho `GET /api/v1/catalog/products`.
- Them tham so xep hang cho `GET /api/v1/catalog/rankings`.
- Them endpoint `GET /api/v1/catalog/images`.
- Backend tinh cac chi so nhu gia hien tai, diem tim kiem, diem xu huong va tong so anh.
- Endpoint hinh anh tra ve `items`, `categories`, `totalImages`, `totalProducts`, `page`, `limit`, `totalPages`, `hasMore`.

### Frontend

- `ImagesPage` goi endpoint backend moi thay vi tu tong hop toan bo san pham tren client.
- `ProductListPage`, `RankingsPage`, `HomePage`, `FlashSale`, `SuggestedProducts` chuyen sang dung tham so backend de loc/lay du lieu.
- `apiDb` ho tro tham so moi cho catalog, rankings va images.
- `NotificationDropdown` khong goi notifications khi chua co token dang nhap.

### Kiem tra

- `GET /api/v1/catalog/images?page=1&limit=30` tra `200`.
- CORS tra `Access-Control-Allow-Origin: http://localhost:3000`.
- Trang dau tra 30 san pham, tong 61 san pham, 3 trang, 158 anh.
- `npm run build` frontend thanh cong.

### Ghi chu tiep theo

- Neu du lieu anh tang len rat lon, nen toi uu endpoint resolve bang truy van truc tiep theo product id/image index thay vi build lai collection.
- Can nhac doi text "Thu Vien Anh 3D" thanh "Thu Vien Anh San Pham" neu phan lon san pham chi co anh thuong.
