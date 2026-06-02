# Product Management Notes

## Update 2026-05-22

- Giu lai cac thong tin chinh cua san pham nhu cu.
- Hinh anh dai dien chung la anh duy nhat o cap san pham.
- Bo phan gallery hinh anh chung trong form admin de tranh trung voi hinh anh theo bien the.
- Video san pham la video dung chung cho toan bo san pham, luu o cap `products.video_url`.
- Form admin bo sung preview cho:
  - anh dai dien chung
  - video dung chung
  - hinh anh bien the theo mau sac
- Bien the uu tien truc mau sac truoc, sau do moi den thong so ky thuat va gia.
- Mua kem giam gia:
  - admin chon san pham mua kem tu danh sach san pham
  - cau hinh giam theo `FIXED` hoac `PERCENT`
  - cau hinh so luong toi da duoc giam gia theo tung san pham mua kem
  - cau hinh duoc luu trong `products.sales_config.accessoryOffers`
  - bang `product_accessories` tiep tuc giu vai tro quan he de tra cuu nhanh
- Cau truc `sales_config.accessoryOffers`:

```json
[
  {
    "productId": "uuid-san-pham-mua-kem",
    "discountType": "PERCENT",
    "discountValue": 25,
    "maxQuantity": 2
  }
]
```

- Quy tac tinh gia o checkout can ap dung:
  - chi giam cho so luong nam trong `maxQuantity`
  - so luong vuot muc giam gia se tinh theo gia goc
  - san pham mua kem chi duoc giam khi cung hoa don voi san pham chinh

## Ghi chu pham vi

- Ban cap nhat nay hoan thien phan quan tri san pham va API luu cau hinh.
- Neu can ap dung gia mua kem tren gio hang/checkout, tiep tuc doc file nay truoc khi sua logic don hang.

## Update 2026-05-23

- Bo phan SEO khoi form quan tri san pham; product SEO metadata cu van duoc doc neu ton tai nhung admin khong nhap moi o man hinh nay.
- San pham ban kem tiep tuc luu trong `products.sales_config.accessoryOffers`, nhung UI chon bang bo loc danh muc, thuong hieu va tim kiem san pham.
- UI cho phep chon tat ca san pham trong ket qua loc hien tai; moi san pham mua kem co gia/uu dai do admin set rieng bang `discountType`, `discountValue`, `maxQuantity`.
- Bien the duoc sap xep va nhap theo mau sac la truc chinh. Cac cau hinh khac nhau cua cung mau van nam trong danh sach bien the nhung UI uu tien nhom theo mau de admin de nhap hon.
- SKU bien the co the do admin nhap; neu de trong thi frontend/backend tu tao theo viet tat ten san pham + viet tat mau + so thu tu, vi du `IPM-DT-01`.
- Dich vu di kem da co nen du lieu qua `attached_services` va `product_attached_services`:
  - `PRODUCT_SERVICE`: bao hanh/mo rong bao hanh gan voi san pham/IMEI, tinh gia theo tien co dinh, phan tram, hoac dinh muc.
  - `SUPPORT_SERVICE`: lap dat, ve sinh, ho tro... do admin set gia co dinh hoac cau hinh rieng.
- Khi lam tiep gio hang/checkout, can xu ly rule moi: trong cung mot `attribute_group` cua dich vu san pham, nguoi mua chi duoc chon mot lua chon.
- Admin da co man `Dich vu` de tao/sua/an danh sach dich vu di kem.
- Form san pham da co khu `Dich vu di kem`, cho chon nhieu dich vu tu danh sach da tao va dat `overridePrice` rieng theo san pham neu can.
- Product form co them `sales_config.warrantyPolicy` de san pham co the:
  - lay mac dinh bao hanh/1 doi 1 tu danh muc
  - hoac admin override thang bao hanh va so ngay 1 doi 1 rieng theo san pham
- Khi chon danh muc cha/con, neu san pham dang bat "theo danh muc" thi UI tu nap `warrantyPolicy` tu danh muc uu tien cao nhat.
- Khi chon dich vu di kem trong product form, UI chan viec chon hai dich vu cung `serviceType + attributeGroup`; backend cung bo qua dich vu trung nhom khi dong bo bang `product_attached_services`.
- Da them `AGENTS.md` vao goc project de ghi nho cach dung CodeGraph va cac file notes can doc truoc khi sua module nay.

## Update 2026-05-23 bo sung

- Form san pham da bo o nhap tay `Combo/bundle: SKU/ID`; luong ban kem chuyen sang chon san pham tu danh sach loc.
- Khu san pham mua kem hien danh sach chon ngay sau khi admin loc theo danh muc, thuong hieu hoac tim theo ten/SKU; co nut chon tat ca ket qua dang loc.
- Khu dich vu di kem trong form san pham khong cho nhap tay. Admin loc/chon tu danh sach `attached_services` da tao theo loai dich vu, nhom dich vu va tu khoa.
- Khi chon dich vu di kem, UI hien loai dich vu, nhom, thoi han bao hanh va gia de admin phan biet cac goi 3/6/9/12/18/24/36 thang.
- Danh sach san pham mua kem trong form admin hien tu du lieu san pham da load san, khong phu thuoc API suggest nen loc danh muc/thuong hieu se co ket qua ngay neu du lieu tren bang dang co san pham phu hop.
- Popup them/sua san pham, danh muc, thuong hieu, voucher va noi dung co `forceOpenKey` theo id dang sua de khi chuyen sang item khac popup tu mo lai, tranh phai reload trang.
- Popup them/sua cung goi ham reset form khi dong, de admin co the dong roi bam sua lai dung cung item ma khong can reload trang.

## Update 2026-05-23 chinh sach dich vu moi

- Danh sach dich vu bao hanh mo rong da cap nhat theo chinh sach ElectroMart Viet Nam:
  - 1 doi 1 VIP
  - Roi vo - roi nuoc
  - S24+
- Cac goi bao hanh nay khong con tinh theo phan tram co dinh; da chuyen sang `TIERED_AMOUNT` va luu bieu phi trong `attached_services.metadata.priceTiers`.
- Product form va bang dich vu hien thi goi `TIERED_AMOUNT` la "Theo bieu phi" de admin khong hieu nham la gia 0 dong.
- UI them/sua dich vu bo sung nhom `ACCIDENTAL_DAMAGE` cho goi roi vo - roi nuoc.

## Update 2026-05-23 khoa gia dich vu theo chinh sach

- Product form da bo o `overridePrice` trong khu dich vu di kem; san pham chi gan ma goi dich vu, khong nhap gia rieng theo san pham.
- Backend bo qua gia override khi dong bo `product_attached_services` va luon luu `override_price = NULL`.
- Gia cac goi bao hanh/dich vu san pham lay theo chinh sach trong `attached_services`, dac biet cac goi `PRODUCT_SERVICE` dung `TIERED_AMOUNT` va `metadata.priceTiers`.
