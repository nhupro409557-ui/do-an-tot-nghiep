import re
import unicodedata
from dataclasses import dataclass


INTENTS = {
    "SMALL_TALK",
    "PRODUCT_SEARCH",
    "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON",
    "PRICE_AND_PROMOTION",
    "STOCK_AVAILABILITY",
    "USED_PRODUCT_ADVICE",
    "ORDER_LOOKUP",
    "SHIPPING_LOOKUP",
    "LOYALTY",
    "CART_SUPPORT",
    "VOUCHER_SUPPORT",
    "PRODUCT_REVIEW",
    "ACCOUNT_SUPPORT",
    "STORE_POLICY",
    "WARRANTY_POLICY",
    "AFTER_SALES_LOOKUP",
    "COMPLAINT",
    "NEEDS_CLARIFICATION",
    "NO_RESULT",
    "OUT_OF_SCOPE",
    "UNSUPPORTED_REQUEST",
    "UNSAFE_REQUEST",
}


UNSAFE_TERMS = (
    "chinh tri",
    "ton giao",
    "khieu dam",
    "hack",
    "lua dao",
    "vu khi",
    "thu ghet",
    "tu tu",
    "ma tuy",
)

OUT_OF_SCOPE_TERMS = (
    "phuong trinh",
    "thoi tiet",
    "bai van",
    "tong thong",
    "dich doan van",
    "chuyen cuoi",
    "chung khoan",
    "nau pho",
    "bong da",
    "hoc python",
    "email xin viec",
    "tao anh",
    "bai tho",
    "dao ham",
    "nhac nao",
    "may in van phong",
    "trong hoa",
    "tom tat phim",
    "kham benh",
    "luat giao thong",
    "ty gia",
)

SENSITIVE_OR_DESTRUCTIVE_TERMS = (
    "toan bo database",
    "system prompt",
    "api key",
    "access token",
    "select * from",
    "imei cua tat ca",
    "serial cua tat ca",
    "vi tri ke",
    "so dien thoai khach",
    "email cua khach",
    "dia chi giao hang cua moi nguoi",
    "xoa toan bo",
)

SHOP_TERMS = (
    "dien thoai",
    "smartphone",
    "laptop",
    "may tinh",
    "tablet",
    "phu kien",
    "tai nghe",
    "ban phim",
    "chuot",
    "dong ho",
    "camera",
    "may anh",
    "sac du phong",
    "sac",
    "san pham",
    "gia",
    "khuyen mai",
    "ton kho",
    "con hang",
    "mua",
    "don hang",
    "giao hang",
    "van chuyen",
    "thanh toan",
    "bao hanh",
    "doi tra",
    "hoan tien",
    "loyalty",
    "voucher",
    "hang cu",
    "may cu",
    "iphone",
    "ipad",
    "macbook",
    "samsung",
    "galaxy",
    "oppo",
    "xiaomi",
    "realme",
    "vivo",
    "honor",
    "meizu",
    "asus",
    "acer",
    "lenovo",
    "dell",
    "nokia",
    "airpods",
    "apple",
    "sony",
    "jbl",
    "logitech",
    "sku",
    "ma san pham",
    "ma vach",
)

SPECIFIC_CATALOG_TERMS = (
    "dien thoai",
    "smartphone",
    "laptop",
    "may tinh",
    "tablet",
    "tai nghe",
    "dong ho",
    "camera",
    "may anh",
    "sac du phong",
    "iphone",
    "ipad",
    "macbook",
    "samsung",
    "oppo",
    "xiaomi",
    "sony",
    "jbl",
    "logitech",
)

COMPARISON_BRAND_TERMS = (
    "apple",
    "samsung",
    "sony",
    "lg",
    "dell",
    "hp",
    "asus",
    "lenovo",
    "oppo",
    "xiaomi",
    "vivo",
    "honor",
    "acer",
)

TECHNICAL_SPEC_TERMS = (
    "thong so",
    "cau hinh",
    "kich thuoc",
    "trong luong",
    "chat lieu",
    "cong suat",
    "dien ap",
    "tan so",
    "pin",
    "sac",
    "bo xu ly",
    "chip",
    "card do hoa",
    "ram",
    "bo nho",
    "ssd",
    "man hinh",
    "do phan giai",
    "camera",
    "loa",
    "micro",
    "wi-fi",
    "wifi",
    "bluetooth",
    "nfc",
    "4g",
    "5g",
    "sim",
    "usb",
    "hdmi",
    "gps",
    "he dieu hanh",
    "chong nuoc",
    "chong bui",
    "ip68",
    "tuong thich",
    "model",
    "phien ban",
    "phu kien di kem",
    "lop son",
    "tieu thu dien",
    "ton dien",
    "bo chuyen doi",
    "day nguon",
    "thoi luong",
    "hieu nang",
    "toc do xu ly",
    "ghz",
    "tan nhiet",
    "o cung",
    "the nho",
    "dung luong",
    "khe cam",
    "sata",
    "nvme",
    "do sang",
    "nit",
    "do phu mau",
    "cam ung",
    "but cam ung",
    "chong choi",
    "mat do diem anh",
    "che do doc sach",
    "lay net",
    "zoom",
    "quay video",
    "den flash",
    "am thanh",
    "dinh dang am thanh",
    "esim",
    "cong mang",
    "lan",
    "ung dung",
    "macos",
    "nha thong minh",
    "google assistant",
    "giong noi",
    "firmware",
    "nang cap",
    "do on",
    "nhe",
    "ket noi",
    "tai lieu ky thuat",
    "nha san xuat cong bo",
    "dung on",
    "moi gio su dung",
    "video 4k",
    "quay cham",
    "ghi am",
    "am luong",
    "khoang cach dieu khien",
    "moi truong am",
    "mat kinh chiu luc",
    "phan mem",
    "phi dang ky",
    "cai dat goc",
    "sao luu du lieu",
    "thiet bi khac hang",
    "cua hang tu kiem tra",
    "san pham nay manh",
    "may nang",
)

COMMERCE_POLICY_TERMS = (
    "hoa don",
    "xuat hoa don",
    "thue",
    "phi van chuyen",
    "phi giao hang",
    "mien phi van chuyen",
    "mien phi giao hang",
    "phi lap dat",
    "giao hang hoa toc",
    "nhan hang tai cua hang",
    "phuong thuc thanh toan",
    "thanh toan bang",
    "thanh toan tien mat",
    "thanh toan truc tuyen",
    "the ngan hang",
    "the ghi no",
    "vi dien tu",
    "chuyen khoan",
    "tra gop",
    "tra truoc",
    "moi thang toi phai tra",
    "bao lau toi nhan duoc tien hoan",
    "tien hoan duoc tra",
    "quy dinh hoan tien",
    "chinh sach hoan tien",
    "phuong thuc hoan tien",
    "muc hoan tien",
    "tach don hang",
    "tra hang",
    "khi tra lai san pham",
    "neu tra lai san pham",
    "toi muon tra lai san pham",
    "doi sang san pham",
    "doi san pham",
    "san pham flash sale co duoc doi",
    "hang thanh ly co duoc hoan",
)

PRICE_PROMOTION_TERMS = (
    "khuyen mai",
    "uu dai",
    "ma giam",
    "voucher",
    "flash sale",
    "sale",
    "chiet khau",
    "gia si",
    "gia thanh vien",
    "gia bao nhieu",
    "gia hien tai",
    "gia ban",
    "gia niem yet",
    "gia goc",
    "gia giam",
    "gia sau",
    "gia truoc",
    "gia cuoi cung",
    "gia tot nhat",
    "gia da giam",
    "dang giam",
    "duoc giam",
    "giam gia",
    "giam them",
    "muc giam",
    "giam tren",
    "giam nhieu nhat",
    "combo",
    "mua mot tang mot",
    "mua 1 tang 1",
    "tong tien",
    "tong so tien",
    "thanh tien",
    "cashback",
)

LOYALTY_PROMOTION_TERMS = (
    "diem thuong",
    "diem thanh vien",
    "diem tich luy",
    "tich diem",
    "hang thanh vien",
    "hang bac",
    "hang vang",
    "hang kim cuong",
    "len hang thanh vien",
    "nang hang thanh vien",
    "khach hang than thiet",
    "dung toan bo diem",
    "nhan duoc diem",
    "diem sau khi mua",
    "diem co duoc hoan",
    "diem duoc hoan",
    "chuyen diem",
    "quy doi diem",
    "diem co het han",
    "mua bao nhieu tien duoc mot diem",
    "mot diem tri gia bao nhieu",
    "dung diem the nao",
    "so diem toi thieu",
    "gioi han so diem",
    "kiem tra lich su diem",
    "diem bi thieu",
    "diem chua duoc cong",
    "diem bi mat",
    "duy tri hang",
    "quyen loi tung hang",
    "hang thanh vien cua toi",
    "vi diem",
    "quyen loi tai moi chi nhanh",
    "quen cung cap so dien thoai khi mua hang",
    "khoa tai khoan thanh vien",
    "don bi huy thi diem",
    "hang duoc xet lai",
    "diem hien thi khong dung",
    "cong diem bo sung",
    "dung diem nhung don khong thanh cong",
    "diem da bi tru nhung don bi huy",
    "lich su tich va su dung diem",
    "thanh vien co duoc bao hanh uu tien",
    "diem moi se duoc cong",
)

AMBIGUOUS_PRICE_PROMOTION_QUERIES = {
    "san pham nay co re khong",
    "co giam khong",
    "gia tot nhat la bao nhieu",
    "co ma nao khong",
    "mua nhieu co re hon khong",
    "toi duoc uu dai gi",
    "co gia thanh vien khong",
    "thanh toan the nao thi re nhat",
    "co chuong trinh gi khong",
    "gia cuoi cung bao nhieu",
    "co mien phi khong",
    "co the bot them khong",
    "toi muon mua gia tot",
    "co uu dai cho toi khong",
    "lam sao mua san pham nay re nhat",
}

STOCK_POLICY_TERMS = (
    "dat truoc",
    "dat coc",
    "giu hang",
    "giu san pham",
    "ma giu hang",
    "gia han thoi gian giu",
    "suat dat truoc",
    "danh sach dat truoc",
    "thoi gian nhap hang",
    "ngay nhap hang",
    "lich nhap hang",
    "hang ve tre",
    "dang ky nhan thong bao khi co hang",
    "thong bao cho toi khi co hang",
    "chuyen hang giua cac chi nhanh",
    "chuyen san pham tu chi nhanh",
    "gom hang tu nhieu chi nhanh",
    "tien coc",
    "doi mau sau khi dat",
    "doi sang mau khac sau khi dat",
    "phi chuyen chi nhanh",
    "nhan o chi nhanh khac",
    "xac nhan hang truoc khi toi den",
    "uu tien toi khi hang ve",
    "giu hai san pham",
    "doi noi nhan hang sau khi giu",
    "hang dang kiem ke",
    "chua kiem duyet",
    "xac nhan lai voi chi nhanh",
    "them vao gio co duoc giu",
    "cho nhap hang thay vi hoan tien",
    "chuyen hang tu noi khac de hoan thanh don",
    "dat hang truoc",
    "hang ve muon",
)

STOCK_QUERY_TERMS = (
    "con hang",
    "het hang",
    "tam het hang",
    "ton kho",
    "tinh trang ton",
    "hien co san",
    "dang co san",
    "mua ngay",
    "giao ngay",
    "nhan hom nay",
    "con bao nhieu",
    "con chinh xac bao nhieu",
    "con du",
    "du hang",
    "so luong ton",
    "so luong hien thi",
    "ngung kinh doanh",
    "ngung ban",
    "chi nhanh nao con",
    "cua hang nao con",
    "ban nao dang co",
    "ban nao dang con",
    "mau nao dang co",
    "mau nao da het",
    "mau nao sap het",
    "con nhieu khong",
    "sap het hang",
    "co o chi nhanh nao",
    "co hang lai",
    "sap co hang",
    "se duoc nhap lai",
    "vua nhap kho",
    "het roi",
    "con o chi nhanh nao",
    "ngay nao hang moi ve",
    "tren duong ve kho",
    "sap ve co bao nhieu",
    "chi nhanh gan toi con khong",
)

AMBIGUOUS_STOCK_QUERIES = {
    "con hang khong",
    "con ban do khong",
    "co mau khac khong",
    "ban nao dang co",
    "bao gio co hang",
    "co the giu giup toi khong",
    "co ban moi hon khong",
    "co mau thay the khong",
    "con o cua hang nao",
    "co giao ngay duoc khong",
    "con nhieu khong",
    "co dung phien ban toi can khong",
    "ban nay co khac gi khong",
    "mau nay het roi a",
    "khi nao co lai",
}

URGENT_SAFETY_TERMS = (
    "phat no", "boc chay", "pin bi phong", "dien giat", "mui khet", "gay thuong tich",
    "thong tin the bi lo", "tai khoan bi chiem quyen", "giao dich toi khong thuc hien",
    "gia mao cua hang", "cung cap otp", "hang gia", "gian lan tra gop",
    "lo hong bao mat", "khoa tai khoan ngay", "dung giao dich",
)

COMPLAINT_SUPPORT_TERMS = (
    "toi muon gap nhan vien", "chuyen toi den bo phan", "khong muon noi chuyen voi chatbot",
    "nhan vien truc tuyen", "yeu cau goi lai", "noi chuyen voi quan ly", "ho tro khan cap",
    "bo phan khieu nai", "phan anh", "gui bang chung khieu nai", "ma khieu nai",
    "khieu nai da duoc tiep nhan", "theo doi tien do khieu nai", "xem xet lai",
    "nhan sai san pham", "nhan sai mau", "thieu phu kien", "khong giong mo ta",
    "khong chinh hang", "tinh sai gia", "giao qua tre", "huy khong co ly do",
    "da giao nhung", "thu them phi", "thanh toan sai so tien", "giao nham nguoi",
    "tru tien hai lan", "nhan vien tu van sai", "thai do khong tot", "chi phi ngoai quy dinh",
    "san pham toi nhan bi loi", "dau hieu da qua su dung", "hop san pham bi mo",
    "hong ngay khi su dung", "sua bao hanh nhieu lan", "khong dong y voi ket qua",
    "tu choi doi tra", "qua tang khong dung", "khong duoc ap dung gia giam",
    "bao lau nhan vien se phan hoi", "gap bo phan bao hanh", "gap bo phan thanh toan",
    "chon ngon ngu ho tro", "khong nhan duoc tien hoan", "diem thuong bi tru sai",
    "nhan vien giao hang co thai do", "don bi tao hai lan", "voucher khong duoc hoan",
    "thong tin ca nhan bi giao", "nhan vien khong ho tro doi tra", "lam lo thong tin",
    "gui hinh anh hoac video", "theo doi tien do",
    "voucher va diem thuong cung chua duoc tra lai", "lien he hai lan nhung chua duoc xu ly",
    "can ho tro ve don hang",
)

CART_ORDER_POLICY_TERMS = (
    "gio hang", "them san pham vao gio", "xem gio", "xoa mot san pham khoi gio",
    "luu san pham de mua sau", "chon lai mau", "gioi han so luong san pham",
    "lam sao dat hang", "dat hang voi tu cach khach", "thong tin nao de dat hang",
    "ghi chu cho don hang", "giao den nhieu dia chi", "sua don hang sau khi dat",
    "them san pham vao don da dat", "huy mot san pham trong don", "nut huy don",
    "trang thanh toan bi treo", "bam dat hang", "khong nhan duoc ma don",
    "them nhieu san pham cung luc", "thay doi so luong san pham", "chon nhieu mau",
    "nhap nhung thong tin nao", "dat hang cho nguoi khac", "giao vao gio cu the",
    "thay doi dia chi giao hang", "doi dia chi sau khi dat", "doi mau san pham trong don",
    "thay doi so luong san pham", "don dang giao co huy", "don tu dong bi huy",
    "khong the them san pham", "so luong trong gio khong cap nhat", "tao hai don",
    "huy don co mat phi", "so dien thoai nhan hang", "tach don hang",
    "dat hang truc tuyen va nhan tai cua hang", "lam sao huy don hang",
    "don hang tu dong bi huy",
    "dat hai chiec dien thoai", "mot chiec mau den va mot chiec mau trang",
    "sau khi dat, toi co the doi dia chi",
)

SHIPPING_SUPPORT_TERMS = (
    "ngay giao du kien", "tai xe se giao", "giao som hon", "giao tre", "hen giao",
    "lien he tai xe", "so dien thoai tai xe", "ma van don", "don vi van chuyen",
    "dang giao", "da giao nhung", "giao lai", "giao nham", "that lac",
    "giao den huyen", "giao den xa", "giao den chung cu", "giao den van phong",
    "giao cuoi tuan", "giao buoi toi", "giao ngoai gio", "giao trong ngay",
    "nhan tai cua hang", "lay hang tai cua hang", "doi nguoi nhan", "kiem tra khi nhan",
    "doi ngay giao", "giao vao buoi toi", "cuoc goi giao hang", "tai xe goi",
    "tai xe bao khong tim thay", "chi dan duong di", "nguoi khac co the nhan",
    "giay to gi khi nhan", "giao that bai", "nhan nham san pham", "nhan duoc hang",
    "giao hoa toc", "giao trong hai gio", "khung gio giao", "bao lau toi nhan duoc hang",
    "thoi gian giao", "dia chi nhan hang", "phi giao", "phu phi giao",
    "chon chi nhanh nhan hang", "khi nao toi co the den nhan", "giu don trong bao lau",
    "kiem tra san pham truoc khi nhan", "cai dat khi nhan", "san sang nhan",
    "khong den dung han", "mo niem phong", "video mo hop", "hop bi mop",
    "sai mau hoac sai phien ban", "tu choi nhan", "xac nhan da nhan du",
    "kiem tra nhung gi khi nhan", "san pham cong kenh",
    "chua nhan duoc cuoc goi nao", "roi nha luc", "dia chi cua toi o ngoai thanh",
    "phi bao nhieu",
)

PAYMENT_SUPPORT_TERMS = (
    "momo", "zalopay", "vnpay", "thong tin the", "ma otp", "ma cvv", "ma pin",
    "thanh toan bi loi", "bi tru tien", "thanh toan hai lan", "giao dich bi tu choi",
    "bien lai thanh toan", "thanh toan mot phan", "tat toan som", "ho so tra gop",
    "duyet tra gop", "lai suat", "phi tra gop", "ky han tra gop", "no xau",
    "thanh toan bi tu choi", "trang thanh toan bi dong", "chuyen thua tien",
    "chuyen thieu tien", "giao dich dang cho", "trang thai thanh toan",
    "thanh toan lai", "bang chung thanh toan", "ky han nao", "phi ho so",
    "giay to gi", "tien chua duoc hoan", "hoan ve tai khoan nao", "hoan mot phan",
    "chung minh thu nhap", "tat toan truoc han", "tra cham mot ky", "tien duoc hoan ve dau",
    "tien hoan chua ve", "phi chuyen doi tra gop",
    "tra trong 12 thang", "tong phi va so tien moi thang", "that su la 0%",
    "tat toan sau sau thang",
)

ACCOUNT_POLICY_TERMS = (
    "dang ky tai khoan", "dang nhap", "quen mat khau", "doi mat khau", "dat lai mat khau",
    "xac thuc hai buoc", "ma xac minh", "so dien thoai da duoc su dung", "email da ton tai",
    "tai khoan bi khoa", "dang xuat khoi tat ca", "lich su dang nhap", "thiet bi la",
    "thay doi email", "thay doi so dien thoai", "cap nhat thong tin ca nhan",
    "them dia chi", "dia chi mac dinh", "xoa tai khoan", "khoi phuc tai khoan",
    "gop tai khoan", "mat du lieu tai khoan", "lay lai tai khoan",
    "dang ky bang so dien thoai", "dang ky bang email", "mua hang ma khong can tai khoan",
    "xac minh tai khoan", "nhap sai otp", "truy cap trai phep", "khoa tai khoan tam thoi",
    "hoat dong dang ngo", "doi ten tai khoan", "doi so dien thoai", "doi email",
    "bao nhieu dia chi", "dong bo gio hang", "don hang cu", "diem thuong co mat",
    "luu nhieu dia chi", "nhap sai ngay sinh", "doi thong tin nguoi nhan",
    "khong the xoa dia chi", "cap nhat gioi tinh", "thong tin tuy chon",
    "thong tin ca nhan duoc dung", "an lich su mua hang", "mat so dien thoai cu",
    "truy cap duoc email", "doi dia chi giao hang", "cap nhat thong tin xuat hoa don", "tai du lieu tai khoan",
    "hai tai khoan", "tai khoan bi vo hieu hoa", "chuyen don hang sang tai khoan",
    "chuyen bao hanh sang tai khoan",
)

STORE_INFORMATION_TERMS = (
    "cua hang gan toi", "dia chi chi nhanh", "mo cua luc", "dong cua luc", "mo chu nhat",
    "mo ngay le", "gio lam viec", "chi nhanh nao", "hotline", "email ho tro",
    "kenh chat", "facebook chinh thuc", "zalo chinh thuc", "ban do cua hang",
    "cho dau", "bai do", "nha ve sinh", "wifi mien phi", "khu vuc trai nghiem",
    "ho tro nguoi khuyet tat", "nhan vien ky thuat tai chi nhanh",
    "ngay le cua hang", "hoat dong 24 gio", "gan tram xe buyt", "gui toi chi duong",
    "nam o tang nao", "dat lich den cua hang", "so dien thoai rieng cua chi nhanh",
    "lien he qua zalo", "fanpage chinh thuc", "tro chuyen voi nhan vien",
    "khu vuc doi", "cho ngoi", "cau thang may", "dich vu tai chi nhanh",
    "yeu cau cua hang goi lai", "thu cu doi moi", "nhan don truc tuyen tai day",
    "dat lich truoc",
)

ACCESSORY_SERVICE_TERMS = (
    "loai op", "op chinh hang", "kinh cuong luc", "cu sac", "cap sac", "sac khong day",
    "cong tai nghe", "phu kien cua phien ban", "phu kien cua hang khac", "but cam ung",
    "phu kien cho o to", "phu kien bao ve", "phu kien trong hop", "dan kinh",
    "chuyen du lieu", "cai dat may", "lap dat tai nha", "ve sinh san pham",
    "bao hanh mo rong", "bao hiem mat cap", "bao hanh roi vo", "bao hanh vao nuoc",
    "op cua ban", "kem op bao ve", "phu kien nao giup bao ve", "kem phu kien",
    "loai chong soc",
)

USED_PRODUCT_CONTEXT_TERMS = (
    "loai a, b va c", "bi tray xuoc", "am hoac luu anh", "pin con bao nhieu phan tram",
    "da su dung bao lau", "tung sua chua", "da thay linh kien", "bi vao nuoc",
    "hinh anh thuc te", "bao cao kiem dinh", "nguon goc tu dau",
    "thu cu cua khach", "lich su sua chua", "du lieu cua chu cu", "may cu hay may moi",
    "ngoai hinh gan nhu moi", "pin tren 90%", "rui ro lon nhat khi mua",
    "kiem tra bao nhieu buoc", "kiem tra so imei", "hang mat cap", "tai khoan icloud",
    "sua main", "ve sinh truoc khi ban", "loai a va loai b", "may con bao hanh chinh hang",
    "khong duoc thay man hinh",
)

REVIEW_SUPPORT_TERMS = (
    "diem danh gia trung binh", "luot danh gia", "nguoi dung thuong khen",
    "nguoi dung thuong phan nan", "danh gia mot sao", "danh gia huu ich",
    "danh gia tu nguoi da mua", "danh gia that", "danh gia co duoc kiem duyet",
    "ty le doi tra", "nguoi dung lau dai", "chat luong thuc te", "pin thuc te",
    "nong khi su dung", "chup thieu sang", "am thanh thuc te", "do on thuc te",
    "lam sao danh gia san pham", "sua danh gia", "xoa danh gia", "danh gia chua hien thi",
    "danh gia cua toi chua hien thi",
    "bao cao danh gia", "danh gia an danh", "danh gia tieu cuc",
    "thuong bi loi", "dang hinh anh hoac video", "noi dung nao khong duoc phep dang",
    "quan tam den pin va do nong",
    "san pham nay duoc danh gia tot", "danh gia nao huu ich", "dung nhu mo ta",
    "nhieu khach mua lai", "san pham co de su dung", "ben sau mot nam", "nang khi su dung lau",
    "san pham co de ve sinh", "can mua hang moi duoc danh gia", "cua hang co tra loi danh gia",
    "nhan diem khi viet danh gia", "danh gia dich vu giao hang", "danh gia chi nhanh",
    "tom tat ca nhan xet", "nguoi mua that", "nhuoc diem nao dang lo",
    "cap nhat danh gia sau", "danh gia co nhieu",
)

GENERAL_POLICY_TERMS = (
    "dieu kien mua hang", "quyen huy don", "don hang duoc xem la xac nhan",
    "chinh sach gia", "gia tren website", "chinh sach dat coc", "quyen loi nguoi mua",
    "dieu khoan su dung", "du lieu ca nhan", "luu du lieu", "cookie", "xoa du lieu",
    "chia se du lieu", "tieu chi duyet tra gop", "phap ly tra gop", "lich su tin dung",
    "chatbot thu thap", "noi dung chatbot", "cam ket phap ly", "bao tri website",
    "du 18 tuoi", "gioi han so luong mua", "ban cho doanh nghiep", "tu choi giao dich",
    "thu thap nhung du lieu", "du lieu duoc dung", "chia se voi ben thu ba",
    "yeu cau xem du lieu", "chinh sach bao mat", "luu thong tin thanh toan",
    "trach nhiem cua cua hang", "trach nhiem nguoi mua", "giai quyet tranh chap",
    "san pham trong gio co duoc giu", "san pham nao khong duoc mua so luong lon", "cung cap thong tin chinh xac",
    "yeu cau sua du lieu", "tu choi nhan quang cao", "theo doi hanh vi tim kiem",
    "xem lich su mua hang", "luu o nuoc ngoai", "vi pham du lieu", "ben cung cap khoan vay",
    "ngan hang quyet dinh ho so", "nhung loai phi", "tra cham", "phi phat",
    "thong tin tin dung", "diem tin dung", "tai lieu nao truoc khi ky",
    "chatbot co thay the", "cam ket chinh thuc", "luu noi dung tro chuyen",
    "xoa lich su tro chuyen", "du lieu de ca nhan hoa", "tu choi tu van tu dong",
    "chuyen sang nhan vien", "chatbot cung cap sai thong tin",
    "den sau 19 gio",
)

VOUCHER_SUPPORT_TERMS = (
    "ma co thoi han", "don toi thieu", "moi nguoi dung duoc dung", "ma cho khach hang moi",
    "ma sinh nhat", "ma rieng", "ma bi mat", "ma da het luot", "ma khong dung dieu kien",
    "ma da su dung", "ma bi khoa", "ma tot nhat", "ket hop hai ma", "tra lai voucher",
    "voucher trong tai khoan", "voucher bi mat", "voucher het han", "lich su su dung voucher",
    "ma co yeu cau phuong thuc thanh toan",
    "ma bao khong ton tai", "he thong bao da dung", "san pham nao trong gio khong du dieu kien",
    "gioi han khu vuc", "ma san pham va ma van chuyen", "ma qua tang", "luu ma de dung sau",
    "ma nao co loi hon", "cac ma co duoc tra lai",
)

RETURN_WARRANTY_SUPPORT_TERMS = (
    "chinh sach doi tra", "da mo hop co doi", "da su dung co tra", "hang trung bay co duoc doi",
    "doi sang mau khac", "doi sang phien ban", "doi tai chi nhanh", "phi doi tra",
    "ho so doi tra", "bien ban doi tra", "gui san pham bao hanh", "trung tam bao hanh",
    "bao hanh tai chi nhanh", "khong con hoa don", "kiem tra tinh trang bao hanh",
    "tu choi bao hanh", "bien ban bao hanh", "linh kien thay the", "nhan may thay the",
    "theo doi tien do sua", "muon may dung tam", "bao duong dinh ky", "ve sinh mien phi",
    "mua truc tuyen co the doi", "doi o chi nhanh khac", "mang theo giay to",
    "mat hop san pham", "bao hanh bat dau", "bao hanh o dau", "gui bao hanh tai cua hang",
    "giay to gi de bao hanh", "loi nao duoc bao hanh", "roi vo co duoc bao hanh",
    "vao nuoc co duoc bao hanh", "thoi gian sua", "phi kiem tra bao hanh",
    "bao lau thi sua xong", "muon san pham dung tam", "sua nhieu lan van loi",
    "kiem tra san pham mien phi", "cai dat lai phan mem", "nhac lich bao duong",
    "thu cu doi moi",
    "pin chai co duoc bao hanh", "phu kien co duoc bao hanh", "sua ngoai bao hanh",
    "mua them bao hanh", "sua chua tai nha", "chinh sach bao hanh", "bao hanh dien thoai",
    "bao hanh may cu",
    "khong roi va khong vao nuoc", "gui tai chi nhanh gan nhat",
)


@dataclass(frozen=True)
class IntentDecision:
    intent: str
    confidence: float
    route: str
    needs_clarification: bool = False


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d")
    noisy_replacements = (
        (r"\bsam\s+sung\b", "samsung"),
        (r"\biphon\b", "iphone"),
        (r"\blap\s+top\b", "laptop"),
        (r"\btai\s+nge\b", "tai nghe"),
        (r"\b(\d+(?:[.,]\d+)?)\s+chieu\b", r"\1 trieu"),
    )
    for pattern, replacement in noisy_replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_any(value: str, terms: tuple[str, ...] | list[str]) -> bool:
    for term in terms:
        start = value.find(term)
        while start >= 0:
            end = start + len(term)
            left_is_word = start > 0 and ("a" <= value[start - 1] <= "z" or value[start - 1].isdigit())
            right_is_word = end < len(value) and ("a" <= value[end] <= "z" or value[end].isdigit())
            if not left_is_word and not right_is_word:
                return True
            start = value.find(term, start + 1)
    return False


def _looks_like_product_comparison(value: str) -> bool:
    if _contains_any(value, ("hang cu", "may cu", "dien thoai cu", "laptop cu")):
        return False
    if _contains_any(
        value,
        (
            "danh sach dat truoc", "vi tri cua toi trong danh sach", "giu hai san pham",
            "giam gia", "hoan phan chenh lech", "doi sang san pham", "doi sang phien ban",
        ),
    ):
        return False
    if _contains_any(
        value,
        (
            "so sanh",
            "hai san pham",
            "hai mau",
            "hai may",
            "hai cai",
            "san pham a",
            "san pham b",
            "tung san pham",
            "tung mau",
            "trong ba san pham",
            "trong bon san pham",
            "trong danh sach",
            "phan khuc",
            "mau dat hon",
            "mau re hon",
            "san pham dat hon",
            "san pham re hon",
            "mau cao hon",
            "tra them tien",
            "tinh nang chenh lech",
            "khach hang thuong chon",
            "cau hinh manh nhat",
            "loai khoi danh sach",
            "uu diem noi bat nhat",
            "bo qua gia ban",
            "chi xet gia tri su dung",
            "so sanh khach quan",
            "thong tin nao chua the xac minh",
            "hai san pham tuong duong",
            "thong so ky thuat va nhan xet chu quan",
            "ly do cho ket luan",
            "tap trung vao nhu cau cua toi",
            "khong cung phan khuc",
            "nen chon cai nao",
            "cai nao nhieu nguoi mua",
            "khong biet nen chon cai nao",
            "tinh nang nao chi mang tinh quang cao",
            "loi ich tuong xung",
            "chi phi phu kien bao tri va sua chua",
            "tieu chi cua toi khong duoc dap ung",
            "cho diem tung tieu chi",
            "tom tat nhu cau cua toi",
            "khong du can cu",
            "khong co du can cu",
            "xep hang cac san pham",
            "chi phi phu kien",
            "bao tri va sua chua",
        ),
    ):
        return True
    if re.search(r"\b(?:mau|san pham|cai|loai|hang|thuong hieu) nao\b.{0,120}\bhon\b", value):
        return True
    if re.search(r"\bnen\s+(?:mua|chon)\b.{0,80}\b(?:hay|hoac)\b", value):
        return True
    if re.search(r"\b(?:phan van|lua chon)\b.{0,50}\bgiua\b", value):
        return True
    if _contains_any(value, ("phien ban cu",)) and _contains_any(value, ("phien ban moi",)):
        return True
    if _contains_any(value, ("ban tieu chuan",)) and _contains_any(value, ("ban pro", "ban cao cap")):
        return True
    if _contains_any(value, ("hang a",)) and _contains_any(value, ("hang b",)):
        return True
    brand_mentions = sum(1 for brand in COMPARISON_BRAND_TERMS if _contains_any(value, (brand,)))
    return brand_mentions >= 2 and _contains_any(value, ("va", "hay", "voi"))


def _looks_like_technical_specification(value: str) -> bool:
    if _contains_any(
        value,
        (
            "co mau nang cap",
            "nen uu tien",
            "toi can san pham",
            "mua mot lan",
            "mau nao",
            "san pham nao",
            "dien thoai nao",
            "laptop nao",
        ),
    ) and not _contains_any(value, ("thong so", "cau hinh")):
        return False
    if not _contains_any(value, TECHNICAL_SPEC_TERMS):
        return False
    if "?" in value:
        return True
    return _contains_any(
        value,
        (
            "bao nhieu",
            "bao lau",
            "la gi",
            "loai nao",
            "chuan nao",
            "the nao",
            "co ho tro",
            "co the",
            "co duoc",
            "co bi",
            "co de",
            "co can",
            "dung duoc",
            "su dung",
            "toi da",
            "khac",
            "y nghia",
            "tac dung",
            "loi ich",
            "tot khong",
            "lau khong",
            "manh khong",
            "dep khong",
            "nhe khong",
            "lon khong",
            "du khong",
            "dang chu y",
            "xem thong so",
            "xem cau hinh",
            "hay cho biet",
            "hay chi ra",
            "hay tom tat",
        ),
    )


def _looks_like_commerce_policy(value: str) -> bool:
    return _contains_any(value, COMMERCE_POLICY_TERMS)


def _looks_like_loyalty_promotion(value: str) -> bool:
    if _contains_any(value, LOYALTY_PROMOTION_TERMS):
        return True
    return _contains_any(value, ("hang thanh vien", "xet hang", "ha hang", "duy tri hang"))


def urgent_support_topic(value: str) -> str | None:
    if _contains_any(value, ("phat no", "boc chay", "pin bi phong", "mui khet")) or re.search(
        r"\bpin\b.{0,25}\bphong\b", value
    ):
        return "FIRE_BATTERY"
    if _contains_any(value, ("dien giat", "gay thuong tich")):
        return "INJURY_ELECTRIC"
    if _contains_any(
        value,
        (
            "thong tin the bi lo", "tai khoan bi chiem quyen", "giao dich toi khong thuc hien",
            "gia mao cua hang", "cung cap otp", "gian lan tra gop", "lo hong bao mat",
            "khoa tai khoan ngay", "dung giao dich",
        ),
    ):
        return "ACCOUNT_FRAUD"
    if "hang gia" in value:
        return "COUNTERFEIT"
    return None


def _looks_like_complaint_support(value: str) -> bool:
    return _contains_any(value, COMPLAINT_SUPPORT_TERMS) or bool(
        _contains_any(value, ("khieu nai", "phan anh", "gap quan ly"))
        or re.search(r"\bsan pham\b.{0,40}\b(?:bi loi|bi hong|khong giong|thieu)\b", value)
    )


def _looks_like_after_sales_lookup(value: str) -> bool:
    return _contains_any(
        value,
        (
            "ho so bao hanh", "ho so doi tra", "ho so hau mai", "yeu cau bao hanh cua toi",
            "yeu cau doi tra", "tinh trang bao hanh", "tinh trang doi tra", "bao hanh cua toi",
            "may bao hanh cua toi", "may thay the", "tra may bao hanh", "serial may bao hanh",
        ),
    ) or re.search(r"\b(?:wr|rt)[a-z0-9]{10,}\b", value) is not None


def _looks_like_order_lookup(value: str) -> bool:
    if re.search(r"\bemv[0-9]{10}\b", value):
        return True
    return _contains_any(
        value,
        ("don hang cua toi", "don cua toi", "ma don", "tinh trang don", "trang thai don", "don gan nhat cua toi"),
    )


def _looks_like_business_policy(value: str) -> bool:
    if _looks_like_loyalty_promotion(value) or _looks_like_voucher_support(value):
        return False
    if _looks_like_order_lookup(value) or _contains_any(
        value,
        ("de su dung", "phi dang ky hang thang", "sao luu du lieu", "tinh la con hang", "con du hang", "ton kho"),
    ):
        return False
    if _contains_any(
        value,
        CART_ORDER_POLICY_TERMS
        + PAYMENT_SUPPORT_TERMS
        + ACCOUNT_POLICY_TERMS
        + STORE_INFORMATION_TERMS
        + GENERAL_POLICY_TERMS,
    ):
        return True
    if _contains_any(value, ("tai khoan", "mat khau", "dang nhap", "dang ky")):
        return True
    if _contains_any(value, ("thanh toan", "giao dich", "tra gop", "hoan tien")):
        return True
    if _contains_any(value, ("chinh sach", "dieu khoan", "quyen loi nguoi mua")):
        return True
    return bool(
        _contains_any(value, ("cua hang", "chi nhanh"))
        and _contains_any(
            value,
            ("mo", "dong", "hoat dong", "lien he", "dich vu", "dia chi", "hotline", "zalo", "fanpage", "cho dau", "cho ngoi"),
        )
    )


def _looks_like_shipping_support(value: str) -> bool:
    return _contains_any(value, SHIPPING_SUPPORT_TERMS) or bool(
        _contains_any(value, ("giao", "nhan hang"))
        and _contains_any(value, ("bao lau", "khi nao", "co the", "phi", "phu phi", "dia chi", "khung gio", "tai xe", "that bai"))
    )


def _looks_like_accessory_service(value: str) -> bool:
    return _contains_any(value, ACCESSORY_SERVICE_TERMS)


def _looks_like_review_support(value: str) -> bool:
    return _contains_any(value, REVIEW_SUPPORT_TERMS)


def _looks_like_voucher_support(value: str) -> bool:
    return _contains_any(value, VOUCHER_SUPPORT_TERMS) or _contains_any(
        value,
        ("voucher", "ma giam gia", "ma mien phi van chuyen", "ma qua tang"),
    )


def _looks_like_cart_support(value: str) -> bool:
    if _contains_any(
        value,
        (
            "gia trong gio khac", "voucher bien mat", "so luong trong gio khong cap nhat",
            "khong the them san pham", "khong nhan duoc ma don",
        ),
    ):
        return True
    if _looks_like_voucher_support(value) or _looks_like_price_promotion(value):
        return False
    return _contains_any(value, CART_ORDER_POLICY_TERMS)


def _looks_like_account_support(value: str) -> bool:
    return _contains_any(value, ACCOUNT_POLICY_TERMS) or _contains_any(
        value,
        ("tai khoan cua toi", "mat khau", "dang nhap", "dang ky", "ma otp", "phien dang nhap"),
    )


def _review_needs_clarification(value: str) -> bool:
    management_terms = (
        "lam sao danh gia", "can mua hang", "sua danh gia", "xoa danh gia", "dang hinh",
        "danh gia chua hien thi", "noi dung nao", "bao cao danh gia", "danh gia an danh",
        "danh gia dich vu", "danh gia chi nhanh", "nhan diem khi viet", "kiem duyet",
    )
    if _contains_any(value, management_terms):
        return False
    return not _contains_any(value, SPECIFIC_CATALOG_TERMS)


def _looks_like_return_warranty_support(value: str) -> bool:
    if "chuyen doi tra gop" in value or _looks_like_review_support(value) or _contains_any(
        value,
        (
            "so sanh", "mau nao", "thuong hieu", "hang nao", "dai hon", "thap hon", "tot hon",
            "tuong duong", "de tim", "con hang", "het hang", "tra them",
        ),
    ):
        return False
    return _contains_any(value, RETURN_WARRANTY_SUPPORT_TERMS)


def _looks_like_stock_policy(value: str) -> bool:
    return _contains_any(value, STOCK_POLICY_TERMS)


def _looks_like_variant_catalog_query(value: str) -> bool:
    normalized_value = value.strip(" ?.!\t\r\n")
    return bool(re.fullmatch(r"ban\s+\d+\s*(?:gb|tb)", normalized_value)) or _contains_any(
        value,
        (
            "ban gioi han",
            "mau doc quyen",
            "mau chi ban",
            "co cung mau",
            "ma danh cho thi truong",
        ),
    )


def _looks_like_used_product_query(value: str) -> bool:
    if _contains_any(
        value,
        ("khach hang cu", "hang cu the", "chuyen du lieu tu may cu", "khoa tai khoan tam thoi", "so dien thoai cu"),
    ):
        return False
    return _contains_any(
        value,
        ("may cu", "dien thoai cu", "laptop cu", "iphone cu", "oppo cu", "hang trung bay", "hang mo hop", "hang doi tra"),
    ) or _contains_any(value, USED_PRODUCT_CONTEXT_TERMS) or bool(re.search(r"\bhang cu\b", value))


def _looks_like_stock_query(value: str) -> bool:
    if _contains_any(
        value,
        (
            "mau tuong tu",
            "mau thay the",
            "san pham thay the",
            "tuong duong dang co san",
            "xep hang cac phuong an",
            "lua chon thu hai",
            "qua tang het hang",
            "phuong an thay the",
        ),
    ):
        return False
    if _looks_like_used_product_query(value):
        return False
    if value.strip(" ?.!\t\r\n") in AMBIGUOUS_STOCK_QUERIES:
        return True
    return _contains_any(value, STOCK_QUERY_TERMS) or bool(
        _contains_any(value, ("phien ban", "mau", "so luong", "sku"))
        and _contains_any(value, ("chi nhanh", "thoi gian nhan hang"))
    )


def _stock_query_needs_clarification(value: str) -> bool:
    if value.strip(" ?.!\t\r\n") in AMBIGUOUS_STOCK_QUERIES:
        return True
    if _contains_any(value, ("chi nhanh", "gan toi", "cua hang nao", "kho tong", "noi nhan")):
        return True
    has_specific_model = bool(
        re.search(r"\b(?:iphone|galaxy|oppo|xiaomi|macbook)\s*[a-z]*\s*\d+", value)
        or re.search(r"\b(?:sku|ma san pham|ma model)\b.{0,25}\b[a-z0-9]+[-_][a-z0-9_-]+\b", value)
    )
    if _contains_any(value, ("san pham nay", "mau nay", "ban nay", "ban do", "mau do", "cai nay")):
        return not has_specific_model
    has_variant_without_product = _contains_any(
        value,
        ("mau den", "mau trang", "mau xanh", "gb", "ram", "ssd", "phien ban"),
    ) and not has_specific_model and not _contains_any(value, SPECIFIC_CATALOG_TERMS)
    return has_variant_without_product


def _looks_like_price_promotion(value: str) -> bool:
    normalized_query = value.strip(" ?.!\t\r\n")
    if normalized_query in AMBIGUOUS_PRICE_PROMOTION_QUERIES:
        return True
    if _contains_any(value, ("ma san pham", "ma vach", "ma model", "ma qr", "sku")):
        return False
    if _contains_any(value, ("nen mua", "nen uu tien", "dap ung", "tinh nang nao")):
        return False
    price_context = re.sub(r"\bdanh gia\b", "", value)
    if _contains_any(price_context, PRICE_PROMOTION_TERMS):
        return True
    if re.search(r"\b(?:dung|nhap|giu lai)\s+(?:them\s+)?ma\b", value):
        return True
    if re.search(r"\bma\b.{0,35}\b(?:su dung|ap dung|het han|giam|don hang)\b", value):
        return True
    if re.search(r"\bgiam\s+\d{1,3}\s*%", value):
        return True
    if "chuong trinh" in value and _contains_any(
        value,
        ("ap dung", "ket thuc", "bat dau", "keo dai", "gioi han", "tu dong", "het", "loai khoi"),
    ):
        return True
    if "chi nhanh" in value and "ap dung" in value:
        return True
    return _contains_any(
        value,
        (
            "co ma nao",
            "ma nay con su dung",
            "ma nay ap dung",
            "ma nay yeu cau",
            "ma nay chi danh",
            "dung duoc nhieu ma",
            "co chuong trinh gi",
            "chuong trinh nay",
            "chuong trinh con",
            "con ap dung khong",
            "con keo dai bao lau",
            "gio vang",
            "mua nhieu co re",
            "co mien phi khong",
            "co the bot them",
            "moi thang phai tra bao nhieu",
            "phat sinh them chi phi",
            "mua toi thieu bao nhieu tien",
            "co re khong",
        ),
    )


def _price_promotion_needs_clarification(value: str) -> bool:
    if value.strip(" ?.!\t\r\n") in AMBIGUOUS_PRICE_PROMOTION_QUERIES:
        return True
    if _contains_any(
        value,
        (
            "san pham nay",
            "mau nay",
            "gia nay",
            "khuyen mai nay",
            "chuong trinh nay",
            "ma nay",
            "phien ban nao",
            "ngan sach cua toi",
            "tam gia nay",
            "tong so tien cuoi cung",
            "tong tien cuoi cung",
            "tong gia sau uu dai",
        ),
    ) and not _contains_any(value, SPECIFIC_CATALOG_TERMS):
        return True
    return False


def route_intent_v1(message: str) -> IntentDecision:
    """Classifier tối giản dùng riêng cho rollback/canary so sánh với V2."""
    normalized = normalize_text(message)
    if _contains_any(normalized, UNSAFE_TERMS):
        return IntentDecision("UNSAFE_REQUEST", 0.8, "POLICY")
    if _contains_any(normalized, OUT_OF_SCOPE_TERMS) or not _contains_any(normalized, SHOP_TERMS):
        return IntentDecision("OUT_OF_SCOPE", 0.8, "POLICY")
    if _contains_any(normalized, ("don hang", "ma don", "order")) or re.search(r"\bemv[0-9]{10}\b", normalized):
        return IntentDecision("ORDER_LOOKUP", 0.8, "MODEL")
    if _contains_any(normalized, ("tich diem", "diem cua toi", "loyalty")):
        return IntentDecision("LOYALTY", 0.8, "MODEL")
    return IntentDecision("PRODUCT_ADVICE", 0.8, "MODEL")


def route_intent(message: str) -> IntentDecision:
    normalized = normalize_text(message)

    if urgent_support_topic(normalized):
        return IntentDecision("COMPLAINT", 0.99, "DETERMINISTIC")

    if _contains_any(normalized, UNSAFE_TERMS):
        return IntentDecision("UNSAFE_REQUEST", 0.99, "POLICY")

    if _contains_any(normalized, OUT_OF_SCOPE_TERMS):
        return IntentDecision("OUT_OF_SCOPE", 0.99, "POLICY")

    if _contains_any(normalized, SENSITIVE_OR_DESTRUCTIVE_TERMS):
        return IntentDecision("UNSUPPORTED_REQUEST", 0.99, "POLICY")

    if _contains_any(
        normalized,
        ("hay huy don", "huy don giup", "hoan tien giup", "tao voucher", "doi trang thai don"),
    ) or re.search(r"\bthanh toan\b.{0,30}\bgiup\b", normalized):
        return IntentDecision("UNSUPPORTED_REQUEST", 0.98, "POLICY")

    greeting = _contains_any(
        normalized,
        ("xin chao", "chao shop", "chao buoi", "hello", "hi shop", "alo", "cam on", "thanks", "shop khoe khong"),
    )
    business_request = _contains_any(
        normalized,
        ("tu van", "may", "san pham", "gia", "don", "bao hanh", "doi tra", "khuyen mai", "voucher"),
    )
    if greeting and not business_request:
        return IntentDecision("SMALL_TALK", 0.98, "DETERMINISTIC")

    if _looks_like_product_comparison(normalized):
        has_specific_pair = bool(re.search(r"\b(?:iphone|galaxy|oppo|xiaomi|macbook)\s*[a-z]*\s*\d+", normalized))
        return IntentDecision("PRODUCT_COMPARISON", 0.96, "MODEL", not has_specific_pair)

    if _looks_like_complaint_support(normalized):
        return IntentDecision("COMPLAINT", 0.98, "DETERMINISTIC")

    if _looks_like_after_sales_lookup(normalized):
        return IntentDecision("AFTER_SALES_LOOKUP", 0.97, "DETERMINISTIC")

    if re.search(r"\b(?:don hang cua toi la|toi muon mua don hang)\b.{0,30}\b\d+(?:[.,]\d+)?\s*(?:trieu|dong)\b", normalized):
        return IntentDecision("PRICE_AND_PROMOTION", 0.95, "DETERMINISTIC")

    if _looks_like_cart_support(normalized):
        return IntentDecision("CART_SUPPORT", 0.97, "DETERMINISTIC")

    if _looks_like_order_lookup(normalized):
        if _contains_any(
            normalized,
            ("dang o dau", "dang giao", "giao hang", "van don", "tai xe", "da giao", "bao gio", "van chuyen", "tracking", "shipper", "giao toi dau"),
        ):
            return IntentDecision("SHIPPING_LOOKUP", 0.97, "DETERMINISTIC")
        return IntentDecision("ORDER_LOOKUP", 0.97, "DETERMINISTIC")

    if _looks_like_review_support(normalized):
        return IntentDecision("PRODUCT_REVIEW", 0.97, "DETERMINISTIC", _review_needs_clarification(normalized))

    if normalized.strip(" ?.!\t\r\n") in AMBIGUOUS_PRICE_PROMOTION_QUERIES:
        return IntentDecision("PRICE_AND_PROMOTION", 0.97, "DETERMINISTIC", True)

    if _contains_any(normalized, ("tuong duong dang co san",)):
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.95, "MODEL", True)

    if _contains_any(normalized, ("san pham moi hay phien ban cu",)):
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.94, "MODEL", True)

    if _looks_like_variant_catalog_query(normalized):
        return IntentDecision("PRODUCT_SEARCH", 0.95, "MODEL", True)

    if "tra gop" in normalized and "chuong trinh" in normalized:
        return IntentDecision("STORE_POLICY", 0.96, "DETERMINISTIC")

    if _looks_like_voucher_support(normalized):
        return IntentDecision("VOUCHER_SUPPORT", 0.97, "DETERMINISTIC")

    if _looks_like_price_promotion(normalized):
        return IntentDecision(
            "PRICE_AND_PROMOTION",
            0.97,
            "DETERMINISTIC",
            _price_promotion_needs_clarification(normalized),
        )

    if _looks_like_loyalty_promotion(normalized):
        return IntentDecision("LOYALTY", 0.97, "DETERMINISTIC")

    if _looks_like_account_support(normalized):
        return IntentDecision("ACCOUNT_SUPPORT", 0.97, "DETERMINISTIC")

    if _looks_like_stock_policy(normalized):
        return IntentDecision("STORE_POLICY", 0.96, "DETERMINISTIC")

    if _looks_like_stock_query(normalized):
        return IntentDecision(
            "STOCK_AVAILABILITY",
            0.97,
            "DETERMINISTIC",
            _stock_query_needs_clarification(normalized),
        )

    if _looks_like_return_warranty_support(normalized):
        return IntentDecision("WARRANTY_POLICY", 0.97, "MODEL")

    if _looks_like_used_product_query(normalized):
        return IntentDecision("USED_PRODUCT_ADVICE", 0.95, "MODEL")

    if _looks_like_business_policy(normalized):
        return IntentDecision("STORE_POLICY", 0.97, "DETERMINISTIC")

    if _looks_like_accessory_service(normalized):
        if _contains_any(
            normalized,
            ("dan kinh", "chuyen du lieu", "cai dat may", "lap dat", "ve sinh", "bao hanh mo rong", "bao hiem"),
        ):
            return IntentDecision("STORE_POLICY", 0.95, "DETERMINISTIC")
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.94, "MODEL", True)

    if _looks_like_commerce_policy(normalized):
        return IntentDecision("STORE_POLICY", 0.97, "DETERMINISTIC")

    if _looks_like_technical_specification(normalized):
        has_specific_product = bool(
            re.search(r"\b(?:iphone|galaxy|oppo|xiaomi|macbook)\s*[a-z]*\s*\d+", normalized)
        )
        return IntentDecision("PRODUCT_SEARCH", 0.95, "MODEL", not has_specific_product)

    if _looks_like_shipping_support(normalized):
        if not _looks_like_order_lookup(normalized) and _contains_any(
            normalized,
            ("thoi gian giao hang du kien", "giao hang du kien", "chinh sach giao hang"),
        ):
            return IntentDecision("STORE_POLICY", 0.96, "DETERMINISTIC")
        return IntentDecision("SHIPPING_LOOKUP", 0.96, "DETERMINISTIC")

    if _contains_any(normalized, ("khieu nai", "buc", "qua te", "that vong", "nhan vien ho tro", "gap nhan vien")):
        return IntentDecision("COMPLAINT", 0.96, "DETERMINISTIC")

    if _contains_any(
        normalized,
        (
            "ho so bao hanh",
            "ho so doi tra",
            "ho so hau mai",
            "yeu cau bao hanh",
            "yeu cau doi tra",
            "tinh trang bao hanh",
            "tinh trang doi tra",
            "bao hanh cua toi",
            "may bao hanh",
            "may thay the",
            "tra may bao hanh",
            "serial may bao hanh",
        ),
    ) or re.search(r"\b(?:wr|rt)[a-z0-9]{10,}\b", normalized):
        return IntentDecision("AFTER_SALES_LOOKUP", 0.97, "DETERMINISTIC")

    if _contains_any(
        normalized,
        (
            "chinh sach bao hanh",
            "bao hanh bao lau",
            "thoi han bao hanh",
            "dieu kien bao hanh",
            "bao hanh may cu",
            "doi may moi",
            "quy trinh tiep nhan bao hanh",
            "chinh sach doi tra khi may loi",
            "bao hanh co bao gom",
            "che do bao hanh co bao gom",
        ),
    ) or re.search(r"\bbao hanh\b.{0,35}\bbao lau\b", normalized):
        needs_product = _contains_any(normalized, ("may nay", "san pham nay", "cai nay"))
        return IntentDecision("WARRANTY_POLICY", 0.95, "MODEL", needs_product)

    if _contains_any(
        normalized,
        (
            "cua hang o dau",
            "shop o dau",
            "dia chi cua hang",
            "dia chi shop",
            "chi nhanh o dau",
            "may gio mo cua",
            "mo cua may gio",
            "gio mo cua",
            "gio lam viec",
            "giao hang toan quoc",
            "ship toan quoc",
            "phi giao hang",
            "phi ship",
            "phi van chuyen",
            "thanh toan khi nhan hang",
            "nhan hang tra tien",
            "cod",
            "tra gop",
            "hang chinh hang",
            "san pham chinh hang",
            "chinh hang",
            "doi tra bao nhieu ngay",
            "doi tra trong bao lau",
            "tra hang bao nhieu ngay",
            "phuong thuc thanh toan",
            "hinh thuc thanh toan",
            "thanh toan bang",
            "hoa don vat",
            "xuat hoa don",
            "chinh sach giao hang",
            "thoi gian giao hang",
            "ho tro goi qua",
            "goi qua",
            "nguoi nhan co the doi san pham",
        ),
    ):
        return IntentDecision("STORE_POLICY", 0.98, "DETERMINISTIC")

    if _contains_any(
        normalized,
        ("ma van don", "tracking", "dang giao", "da giao", "van chuyen", "giao toi", "giao trong hom nay", "toi dau", "dang o dau", "shipper", "hanh trinh giao"),
    ):
        return IntentDecision("SHIPPING_LOOKUP", 0.96, "DETERMINISTIC")

    if _contains_any(normalized, ("don hang", "ma don", "don cua", "don nguoi", "order")) or re.search(r"\bemv[0-9]{10}\b", normalized):
        return IntentDecision("ORDER_LOOKUP", 0.96, "DETERMINISTIC")

    if _contains_any(
        normalized,
        (
            "tich diem",
            "diem cua toi",
            "bao nhieu diem",
            "loyalty",
            "hang thanh vien",
            "vi diem",
            "len hang",
            "nang hang",
            "thang hang",
            "doanh so xet hang",
            "tien nua de len hang",
        ),
    ):
        return IntentDecision("LOYALTY", 0.96, "DETERMINISTIC")

    if _contains_any(normalized, ("hang cu", "may cu", "dien thoai cu", "laptop cu", "iphone cu", "oppo cu")):
        return IntentDecision("USED_PRODUCT_ADVICE", 0.95, "MODEL")

    if _contains_any(
        normalized,
        ("mau hien tai hay cho mau moi", "san pham moi hay phien ban cu"),
    ):
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.94, "MODEL", True)

    if _contains_any(
        normalized,
        (
            "san pham moi nhat",
            "san pham moi",
            "mau moi",
            "moi them",
            "vua them",
            "moi cap nhat",
            "hang moi ve",
            "danh sach san pham",
            "nhung loai san pham nao",
            "loai san pham nao",
        ),
    ):
        return IntentDecision("PRODUCT_SEARCH", 0.97, "MODEL")

    if _contains_any(normalized, ("ma san pham", "sku", "ma vach")) or re.search(
        r"\b(?:(?:sp|lap|nkd)[-_]?[a-z0-9]*\d[a-z0-9]*(?:[-_][a-z0-9]+)*|ip\d{1,2}(?:[-_][a-z0-9]+)+)\b",
        normalized,
    ):
        return IntentDecision("PRODUCT_SEARCH", 0.97, "MODEL")

    if (
        _contains_any(normalized, ("mau do", "mau nay", "san pham do", "san pham nay", "may do", "may nay"))
        and _contains_any(normalized, ("ban", "gb", "dung luong", "ram", "ssd", "phien ban"))
    ) or (
        re.search(r"\b(?:ram|ssd)\s*\d+\s*gb\b", normalized)
        and not _contains_any(normalized, SPECIFIC_CATALOG_TERMS)
    ):
        return IntentDecision("PRODUCT_SEARCH", 0.94, "MODEL", True)

    if _contains_any(
        normalized,
        (
            "mau thay the",
            "san pham thay the",
            "thay the phu hop",
            "thay the tuong duong",
            "tuong tu nhung",
            "giong mau nay",
            "giong san pham nay",
            "cung tinh nang",
            "phien ban moi hon",
            "mau nang cap",
            "san pham tuong duong",
            "mau tuong tu",
            "phuong an thay the",
            "co mau nao thay the",
        ),
    ):
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.95, "MODEL", True)

    context_dependent_recommendation = _contains_any(
        normalized,
        (
            "san pham tot",
            "mau nao dep",
            "tu van cho toi mot cai",
            "san pham gia re",
            "loai tot hon",
            "can mua qua",
            "qua sinh nhat",
            "qua tang",
            "san pham phu hop",
            "loai ben",
            "vua tui tien",
            "khong biet nen chon",
            "san pham cao cap",
            "giong mau nay",
            "mau thay the",
            "thay the tuong duong",
            "tot nhat nhung",
            "danh gia tot nhung",
            "tong gia",
            "dua tren nhung gi toi vua noi",
            "nguoi lon tuoi",
            "nguoi moi bat dau",
        ),
    )
    if context_dependent_recommendation:
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.93, "MODEL", True)

    if _contains_any(
        normalized,
        (
            "con hang",
            "het hang",
            "ton kho",
            "kho con",
            "dang co san",
            "co san de mua",
            "mua ngay duoc",
            "mua duoc ngay",
            "mua ngay hom nay",
            "con bao nhieu",
            "nhan tai cua hang",
        ),
    ) or re.search(
        r"\bcon\s+(?:ip|iphone|galaxy|samsung|oppo|xiaomi|macbook|laptop|tai nghe)[a-z0-9 ]{0,35}\s+(?:ko|khong)\b",
        normalized,
    ) or re.search(
        r"\bmua\b.{0,45}\bngay hom nay\b",
        normalized,
    ):
        return IntentDecision("STOCK_AVAILABILITY", 0.95, "DETERMINISTIC")

    if not _contains_any(normalized, ("gia", "khuyen mai", "giam gia", "uu dai")) and _contains_any(
        normalized,
        ("mau den", "mau trang", "mau xanh", "day du mau"),
    ):
        return IntentDecision("PRODUCT_SEARCH", 0.92, "MODEL", True)

    if re.match(r"^ss\s+", normalized) or re.search(r"\bkhac\b.{1,100}\bo diem\b", normalized) or _contains_any(
        normalized,
        (
            "so sanh",
            "so voi",
            "tot hon",
            "phan tich",
            "co gi hon",
            "nao re hon",
            "cau hinh tot hon",
            "chup anh tot hon",
            "danh gia cao hon",
            "pin tot hon",
            "diem khac biet",
            "mat tinh nang gi",
            "ly do gi de chon",
            "ty le gia tren chat luong",
        ),
    ) or re.search(
        r"\bnen\s+(?:mua|chon)\b.{0,45}\b(?:hay|hoac)\b",
        normalized,
    ) or re.search(
        r"\b(?:mau|san pham|thuong hieu|lua chon) nao\b.{0,100}\bhon\b",
        normalized,
    ) or re.search(
        r"\b(?:trong cac san pham nay|trong ba san pham|mau a va mau b|giua hai san pham)\b",
        normalized,
    ) or (
        _contains_any(normalized, ("khac nhau",))
        and _contains_any(normalized, ("hai san pham", "hai mau", "iphone", "samsung", "oppo", "xiaomi", "macbook"))
    ):
        missing_models = _contains_any(normalized, ("may kia", "cai kia", "san pham kia")) or normalized in {
            "so sanh",
            "so voi may kia",
            "so voi cai kia",
        }
        return IntentDecision("PRODUCT_COMPARISON", 0.94, "MODEL", missing_models)

    if _contains_any(
        normalized,
        (
            "quy dinh hoan tien",
            "dieu kien doi tra",
            "dieu khoan mua hang",
            "chinh sach bao mat",
            "quy dinh kiem tra hang",
            "tra hang khi doi y",
            "chinh sach thanh toan",
            "thoi han xu ly doi tra",
        ),
    ):
        return IntentDecision("STORE_POLICY", 0.95, "DETERMINISTIC")

    if _contains_any(normalized, ("dang sale", "giam tren", "giam nhieu nhat", "giam gia", "khuyen mai", "uu dai")):
        return IntentDecision("PRICE_AND_PROMOTION", 0.95, "DETERMINISTIC")

    if _contains_any(
        normalized,
        (
            "dua tren nhu cau",
            "uu tien hieu nang",
            "de xuat ba san pham",
            "tinh nang nao thuc su",
            "bo qua de tiet kiem",
            "dap ung it nhat",
            "can bang tot nhat",
            "uu diem va nhuoc diem",
            "khong quan tam thuong hieu",
            "it phai sua chua",
            "nang cap trong tuong lai",
            "mua mot lan",
            "tong chi phi su dung",
            "it nguoi biet den",
            "khong phu hop voi nhu cau",
            "tong hop lai truoc khi tu van",
            "xep hang cac lua chon",
            "phu hop voi toi o muc bao nhieu phan tram",
            "neu mot yeu cau cua toi",
        ),
    ):
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.94, "MODEL", True)

    generic_budget_advice = not _contains_any(normalized, SPECIFIC_CATALOG_TERMS) and _contains_any(
        normalized,
        (
            "ngan sach",
            "tam gia",
            "muc gia nay",
            "gia re nhung",
            "gia tri tot",
            "them 1 trieu",
            "tong chi phi",
            "ngoai gia san pham",
            "phat sinh chi phi",
            "gia vua phai",
            "gia hop ly",
            "khong qua dat",
            "mua san pham khoang",
            "toi co toi da",
            "qua duoi",
            "qua khoang",
        ),
    )
    if generic_budget_advice:
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.93, "MODEL", True)

    price_signal_text = re.sub(r"\b(?:danh gia|gia tri|gia dinh)\b", "", normalized)
    has_compact_budget = bool(
        re.search(r"\b\d+(?:[.,]\d+)?\s*(?:tr|trieu|cu)\b", normalized)
        or re.search(r"\b\d{1,3}(?:[.,]\d+)?\s*m\b", normalized)
        or re.search(r"\b\d{1,3}(?:[.,]\d{3})+\s*dong\b", normalized)
    )
    if has_compact_budget or _contains_any(
        price_signal_text,
        ("gia", "khuyen mai", "giam gia", "uu dai", "voucher", "dat nhat", "re nhat", "re hon", "trieu"),
    ):
        return IntentDecision("PRICE_AND_PROMOTION", 0.94, "DETERMINISTIC")

    generic_advice_signal = _contains_any(
        normalized,
        (
            "tu van",
            "de xuat",
            "gioi thieu",
            "lua chon",
            "dang mua",
            "chat luong",
            "de su dung",
            "de dung",
            "de mang theo",
            "de lap dat",
            "de ve sinh",
            "phuc vu cong viec",
            "de giai tri",
            "di du lich",
            "ngoai troi",
            "nhieu muc dich",
            "tiet kiem dien",
            "hoat dong on dinh",
            "do ben",
            "nho gon",
            "thiet ke",
            "sang trong",
            "nhieu tinh nang",
            "pin lau",
            "sac nhanh",
            "chong nuoc",
            "chong bui",
            "it gay tieng on",
            "de sua chua",
            "linh kien",
            "bao hanh dai",
            "nhieu mau",
            "chat lieu",
            "va dap",
            "than thien voi moi truong",
            "an toan",
            "thuong hieu nao",
            "dang tin cay",
            "giu gia",
            "trung tam bao hanh",
            "nhieu phu kien",
            "qua sinh nhat",
            "qua tang",
            "mua qua",
            "qua cho",
            "lam qua",
            "thiet thuc",
            "nhan xet",
            "nhuoc diem",
            "thuong gap loi",
            "tra lai san pham",
            "hai long",
            "dung nhu quang cao",
            "diem danh gia",
            "bao nhieu nguoi da mua",
            "han che lon nhat",
            "dung duoc lau",
            "tuoi tho",
            "chi phi bao tri",
            "gia tri ban lai",
            "nhanh loi thoi",
            "tong chi phi so huu",
            "tieu hao",
            "mua them dich vu",
            "dang tien",
            "cao cap",
            "nhieu nguoi mua",
            "ban chay",
            "ua chuong",
            "phu hop",
            "san pham cho",
            "loai ben",
            "san pham nao tot",
            "san pham nao ben",
            "san pham re",
            "loai dep",
            "mau nao on",
            "duoc danh gia tot",
            "san pham nay co ben",
            "phien ban nao",
            "mau nao duoc mua",
            "duoc khach hang danh gia",
            "con duoc ho tro",
            "thuong xuyen duoc cap nhat",
            "cho mau moi",
            "do cho gia dinh",
            "dung trong gia dinh",
            "dung trong thoi gian dai",
            "khong chiem nhieu dien tich",
            "su dung ngay",
            "dung cho doanh nghiep",
            "san pham nhe",
            "mang may",
            "dung on dinh",
            "toi muon loai tot",
            "mau nao re ma tot",
            "chinh sua video",
            "mang di hoc",
            "may nhe",
        ),
    )
    has_specific_catalog_subject = _contains_any(normalized, SPECIFIC_CATALOG_TERMS)
    if generic_advice_signal and not has_specific_catalog_subject:
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.91, "MODEL", True)

    if _contains_any(
        normalized,
        (
            "tu van",
            "phu hop",
            "nen mua",
            "nen chon",
            "dang mua",
            "may nao tot",
            "pin tot",
            "pin khoe",
            "pin trau",
            "choi game",
            "chup anh",
            "chup hinh dep",
            "hoc tap",
            "hoc lap trinh",
            "thiet ke do hoa",
            "tap the thao",
            "sinh vien",
            "nhan vien van phong",
            "camera tot",
            "uu tien camera",
            "ban chay",
        ),
    ):
        needs_requirements = normalized in {
            "may nao tot",
            "may nao tot?",
            "tu van may",
            "tu van giup toi",
            "minh uu tien camera",
            "uu tien camera",
        }
        return IntentDecision("PRODUCT_RECOMMENDATION", 0.92, "MODEL", needs_requirements)

    if _contains_any(normalized, SHOP_TERMS):
        return IntentDecision("PRODUCT_SEARCH", 0.90, "MODEL")

    return IntentDecision("OUT_OF_SCOPE", 0.98, "POLICY")
