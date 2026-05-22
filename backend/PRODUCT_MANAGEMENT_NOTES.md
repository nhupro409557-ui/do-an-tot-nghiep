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
