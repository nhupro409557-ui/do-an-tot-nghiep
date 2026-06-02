# Admin dashboard UI audit

## Muc tieu su dung chinh

Nguoi quan tri vao dashboard de nam nhanh tinh hinh van hanh cua hang, phat hien canh bao can xu ly ngay va di nhanh vao cac luong quan trong.

## 3 hanh dong quan trong nhat

- Xu ly don hang dang cho.
- Cap nhat san pham, ton kho va danh muc.
- Kiem tra canh bao ve voucher, review, ton kho va doanh thu.

## Canh bao can noi bat

- Don hang cho xu ly.
- Ton kho am hoac sap het hang.
- Voucher da dung gan het ngan sach.
- Danh gia moi can kiem duyet.

## Audit theo 5 tieu chi

- Phan cap thi giac: overview cu co nhieu card cung do nang, khong co tang uu tien ro.
- Mat do thong tin: nhieu khoi canh nhau ngang cap, mat nguoi dung phai quet qua nhieu vung.
- Tinh nhat quan: padding, radius, mau trang thai va shadow chua co quy tac chung.
- Toc do quet mat: sidebar qua nhieu muc ngang cap, search chua thay doi theo ngu canh.
- Do ro cua hanh dong chinh: cac action import, export, them moi, sua, xoa dang nam gan nhau va can tach cap uu tien.

## Uu tien cao

- Sua cac text loi encoding o vung admin hien thi chinh.
- Tao mini design system cho card, metric, alert, table va form.
- Rut gon navigation thanh nhom: Tong quan, Kinh doanh, Catalog, Van hanh, Khach hang, He thong.
- Tai cau truc overview thanh KPI, canh bao, bieu do va danh sach van hanh.

## Uu tien trung binh

- Chia form dai thanh section ro hon.
- Lam sticky header va row action gon hon cho bang.
- Chuan hoa microcopy trang thai va hanh dong.

## Uu tien thap

- Tinh chinh animation nho.
- Them dashboard theo vai tro sau khi cac module chinh da on dinh.

## Giu lai

- Logic API va permission hien co.
- Recharts cho bieu do doanh thu.
- Ant Design cho shell, menu, input va action bar.
- Mau do thuong hieu cho CTA va diem can chu y.

## Can thay doi

- Sidebar phang thanh cac nhom dieu huong.
- Overview khong con la tap hop card ngang cap.
- Search phai co placeholder theo tab.
- Card, alert va metric dung chung mot nhip spacing va border.

## Cap nhat 2026-05-22

- Da nhom lai dieu huong admin theo: Tong quan, Kinh doanh, Catalog, Van hanh, Khach hang, He thong.
- Da doi sidebar sang be mat sang, bo goc lon hon va dung accent indigo de giam cam giac nang cua mau do.
- Da nang cap top bar de search thay doi theo tab va lam noi bat thao tac quan trong.
- Da lam moi KPI card overview theo huong card trang, gradient nhe, badge icon va trend chip.
- Da chuan hoa them copy hien thi cho shell admin va mot phan tieu de dashboard de giam loi font o vung nhin thay ngay.
- Da tang contrast cho data table bang nen header slate nhe va duong tach border ro hon.
- Da bat dau dong bo CTA chinh sang tone indigo de gan voi sidebar active va ngon ngu hanh dong chinh.
- Da bo sung them mot lop bo goc lon hon cho bang va action de tong the gan hon voi giao dien SaaS admin.
- Da doi top bar va sidebar sang tone do nhat nhat hon de gan voi dinh huong mau thuong hieu nhung van giu nen giao dien nhe.
- Da lam diu mau nut bam va o tim kiem theo huong rose nhat de giam cam giac nang cua CTA.
- Da giam do dam cua trang thai active trong sidebar, uu tien nen mau rat nhat va chu slate dam vua phai thay vi den/trang gay.
- Da doi icon cua item active sang nen sang hon va icon slate dam de tranh bi mo khi dang chon.
- Da gom bot thao tac bang thanh edit ben ngoai va menu thao tac gon hon de tiet kiem chieu ngang cot.
- Da bo sung thanh trang thai/pagination UI o day bang de san cho viec no rong du lieu sau nay.
- Da tach vung cuon rieng cho sidebar va content de khi re chuot vao khu nao thi khu do tu cuon doc lap.
- Da an thanh cuon o sidebar va content, nhung van giu co che cuon doc lap theo tung vung.

## Buoc tiep theo de hoan thien

- Rà tiep cac chuoi tieng Viet con loi encoding ben trong cac popup, form va bang chi tiet.
- Chuan hoa action table theo icon/dropdown de giam mat do nut.
- Tach bo component KPI, alert va section header thanh file rieng khi dashboard on dinh hinh thuc.
- Hoan thien breadcrumb dong cho top bar va can lai cum search, thong bao, avatar o moi breakpoint.
- Tiep tuc doi nho cac nut CTA chinh con lai sang tone indigo thay vi den/do neu no con xuat hien trong form popup.
- Tiep tuc don sach cac chuoi tieng Viet con loi encoding trong cac label thao tac va footer bang.
- Theo doi them trai nghiem scroll tren laptop/man hinh thap de can chinh them do cao top bar neu can.
