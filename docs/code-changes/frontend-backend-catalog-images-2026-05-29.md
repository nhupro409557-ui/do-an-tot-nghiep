# Frontend Backend Catalog Images - 2026-05-29

## Tom tat

Dot thay doi nay tap trung vao viec dua cac phep tinh catalog tu frontend ve backend, dong thoi khoi phuc va nang cap trang `/images`.

Ket qua chinh:

- Frontend khong con phai tu loc/sap xep/tong hop danh sach anh san pham o quy mo lon.
- Backend co endpoint rieng cho thu vien hinh anh san pham.
- Trang `/images` phan trang 30 san pham moi trang.
- Danh sach anh duoc sap theo diem xu huong.
- CORS va loi 404/500 cua `/catalog/images` da duoc xu ly.

## Thay doi backend

File chinh:

- `backend/app/api/v1/routers/catalog.py`

Noi dung:

- Mo rong `list_products` de nhan tham so loc va sap xep:
  - `q`
  - `category`
  - `brand`
  - `min_price`
  - `max_price`
  - `sort`
  - `limit`
  - `offset`
  - `flash_sale`
  - `featured`
- Mo rong `list_rankings` de backend tinh du lieu xep hang theo:
  - `period`
  - `criteria`
  - `category`
  - `limit`
- Them `list_product_images` cho route `/catalog/images`.
- Them cac helper tinh toan:
  - chuan hoa tu khoa tim kiem
  - chuan hoa danh muc
  - tinh diem khop tu khoa
  - tinh gia hien tai
  - tinh diem xu huong xap xi

## Thay doi frontend

File chinh:

- `frontend/src/services/apiDb.ts`
- `frontend/src/pages/ImagesPage.tsx`
- `frontend/src/pages/ProductListPage.tsx`
- `frontend/src/pages/RankingsPage.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/components/home/FlashSale.tsx`
- `frontend/src/components/product/SuggestedProducts.tsx`
- `frontend/src/components/layout/NotificationDropdown.tsx`

Noi dung:

- `apiDb.listProducts` nhan them tham so loc/sap xep va truyen ve backend.
- `apiDb.listRankings` dung tham so backend thay vi tinh gia lap o frontend.
- `apiDb.listProductImages` goi `/catalog/images`.
- `ImagesPage` chi render du lieu backend da phan trang.
- `NotificationDropdown` bo qua request thong bao neu chua co token dang nhap.

## API `/catalog/images`

Request mau:

```text
GET /api/v1/catalog/images?page=1&limit=30
```

Response chinh:

```json
{
  "items": [],
  "categories": [],
  "totalImages": 158,
  "totalProducts": 61,
  "page": 1,
  "limit": 30,
  "totalPages": 3,
  "hasMore": true
}
```

## Loi da sua

- Frontend goi `/api/v1/catalog/images` nhung backend chua co route nen bi `404`.
- Sau khi them route, backend tung bi `500` do goi truc tiep function FastAPI co default `Query(...)`.
- Khi backend tra `500`, browser bao CORS vi response loi khong co header mong doi.
- Da sua bang cach truyen ro tham so khi endpoint images tai danh sach san pham noi bo.
- Da restart backend va kiem tra lai response `200` co CORS dung.

## Danh gia hieu nang

Thay doi nay giup frontend muot hon vi:

- Giam so san pham/anh can tai va xu ly trong mot lan render.
- Giam viec loc/sap xep lap lai tren client khi nguoi dung tim kiem, doi danh muc hoac doi trang.
- Backend co the toi uu them bang SQL/index/cache ma khong can sua UI nhieu.

Frontend van co the toi uu tiep:

- Dung virtualized masonry neu so luong anh tang len hang tram/hang nghin.
- Toi uu modal 3D de khong auto-rotate bang interval lien tuc.
- Chi preload anh can thiet trong modal.

## Kiem tra da thuc hien

- Backend `/health` hoat dong.
- `GET /api/v1/catalog/images?page=1&limit=30` tra `200`.
- Response co CORS cho `http://localhost:3000`.
- Trang dau co 30 item.
- Tong du lieu kiem tra: 61 san pham, 3 trang, 158 anh.
- `npm run build` frontend thanh cong.

## Viec nen lam tiep

- Can nhac doi text "Thu Vien Anh 3D" thanh "Thu Vien Anh San Pham" neu du lieu khong phai anh 3D that.

## Bo sung sau review modal

- Da them API resolve image by `viewId` de link chia se `/images?view=...` mo dung anh o moi trang.
- San pham co it hon 3 anh hien viewer anh don thay vi carousel 360.
- San pham co tu 3 anh tro len moi hien carousel/360.
- Auto rotate modal da chuyen sang `requestAnimationFrame`.
- Modal ton trong `prefers-reduced-motion` va khong tu xoay khi nguoi dung bat giam chuyen dong.

## Bo sung layout pixel/mosaic

- Giao dien `/images` tiep tuc giu phong cach pixel/mosaic voi cac the anh cao thap khac nhau.
- Thay `columns` masonry bang CSS grid `auto-rows` + `row-span` de han che khoang trong lon giua cac cot.
- Backend khong dua anh placeholder vao thu vien anh, giup trang khong con nhieu the "Chua co anh".
- Trang hien chi dem san pham co anh that trong `totalProducts` va `totalImages`.
- Sau khi sua, endpoint `/catalog/images?page=1&limit=30` tra 23 san pham va 63 anh.

## Viec nen lam tiep sau bo sung

- Neu du lieu anh tang len hang nghin san pham, toi uu endpoint resolve de truy van truc tiep thay vi build collection day du.
- Bo sung nut chuyen anh trai/phai cho truong hop san pham co 2 anh nhung chua can carousel 360.
