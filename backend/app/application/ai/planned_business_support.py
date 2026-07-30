from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.application.ai.intent_router import normalize_text


def _contains(value: str, *terms: str) -> bool:
    return any(term in value for term in terms)


def _money(value: Any) -> str:
    try:
        amount = int(Decimal(str(value or 0)))
    except (ArithmeticError, ValueError):
        amount = 0
    return f"{amount:,}đ".replace(",", ".")


def _date(value: Any) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.strftime("%d/%m/%Y")


def render_cart_support_answer(context: dict) -> str:
    message = normalize_text(str(context.get("message") or ""))
    items = context.get("cart_items") or []
    item_count = sum(int(item.get("quantity") or 0) for item in items)
    total = sum(Decimal(str(item.get("price") or 0)) * int(item.get("quantity") or 0) for item in items)
    order = context.get("order") or {}
    cart_summary = (
        f" Giỏ hiện có {item_count} sản phẩm, tạm tính {_money(total)}."
        if items
        else " Giỏ hiện chưa có sản phẩm."
    )

    if _contains(message, "khong the them", "so luong trong gio khong cap nhat"):
        return (
            "Bạn hãy tải lại trang, chọn lại đúng màu/phiên bản và kiểm tra số lượng khả dụng. "
            "Nếu số lượng vẫn không cập nhật, hãy xóa dòng sản phẩm đó rồi thêm lại; hệ thống sẽ kiểm tra tồn kho khi đặt đơn."
            + cart_summary
        )
    if _contains(message, "gia trong gio khac", "voucher bien mat"):
        return (
            "Giá và voucher được tính lại theo biến thể, thời hạn chương trình, tồn kho và điều kiện thanh toán tại bước xác nhận. "
            "Bạn nên mở chi tiết tổng tiền để xem dòng giảm giá; nếu vẫn lệch, chưa xác nhận đơn và gửi ảnh màn hình cho hỗ trợ."
        )
    if _contains(message, "bam dat hang", "khong nhan duoc ma don", "tao hai don", "trang thanh toan bi treo"):
        return (
            "Bạn không nên bấm đặt hàng lặp lại. Hãy kiểm tra mục Đơn hàng và trạng thái thanh toán trước; "
            "chỉ thử lại khi chưa có mã đơn hoặc giao dịch. Nếu xuất hiện hai đơn hay đã bị trừ tiền, hãy cung cấp mã đơn/giao dịch cho hỗ trợ."
        )
    if _contains(message, "con hang nhung khong the dat", "san pham trong gio lai het hang"):
        return (
            "Tồn hiển thị có thể thay đổi vì khách khác vừa giữ hoặc mua đúng biến thể. Hãy chọn lại màu/dung lượng, giảm số lượng và tải lại trang; "
            "đơn chỉ giữ tồn sau khi hệ thống xác nhận."
        )

    if _contains(message, "huy don", "huy mot san pham", "nut huy"):
        if order.get("orderCode"):
            status = str(order.get("status") or "").upper()
            if status == "PENDING":
                return (
                    f"Đơn {order['orderCode']} đang chờ xử lý nên chủ đơn có thể mở Chi tiết đơn hàng, chọn Hủy đơn và nhập lý do. "
                    "Chatbot không tự hủy thay bạn."
                )
            return (
                f"Đơn {order['orderCode']} đang ở trạng thái {status or 'đã được xử lý'}, nên không còn thuộc trường hợp tự hủy. "
                "Bạn cần liên hệ hỗ trợ; đơn đã thanh toán phải xử lý hoàn tiền theo trạng thái giao dịch."
            )
        return (
            "Bạn chỉ có thể tự hủy toàn bộ đơn khi đơn còn Chờ xử lý: mở Tài khoản → Đơn hàng → Chi tiết → Hủy đơn và nhập lý do. "
            "Không hỗ trợ hủy riêng một sản phẩm; đơn đã xử lý hoặc đã thanh toán cần liên hệ cửa hàng."
        )
    if _contains(message, "sua don", "doi dia chi", "thay doi dia chi", "doi mau", "thay doi so luong", "them san pham vao don", "doi so dien thoai"):
        return (
            "Bạn có thể sửa giỏ, biến thể, số lượng, người nhận và địa chỉ trước khi xác nhận. Sau khi đã tạo đơn, hệ thống không tự sửa các dòng hàng; "
            "hãy kiểm tra trạng thái đơn và liên hệ hỗ trợ sớm. Chatbot không thay đổi đơn thay bạn."
        )
    if _contains(message, "tien da thanh toan", "voucher co duoc hoan", "diem thuong co duoc hoan"):
        return (
            "Khi đơn được hủy hợp lệ, hoàn tiền, voucher và điểm được xử lý theo trạng thái giao dịch và chính sách của mã. "
            "Bạn nên theo dõi đơn, ví voucher và lịch sử điểm; nếu chưa cập nhật, cung cấp mã đơn cho hỗ trợ."
        )

    if _contains(message, "lam sao dat hang", "thong tin nao", "phuong thuc thanh toan", "ap dung voucher", "dung diem", "tong tien"):
        return (
            "Tại giỏ hàng, chọn sản phẩm cần mua rồi sang Thanh toán; kiểm tra người nhận, số điện thoại, địa chỉ, ghi chú, "
            "phương thức thanh toán, voucher/điểm và tổng tiền trước khi xác nhận."
            + cart_summary
        )
    if _contains(message, "tu cach khach", "khong can tai khoan"):
        return (
            "Bạn có thể đặt hàng không đăng nhập, nhưng đăng nhập giúp theo dõi đơn, voucher, điểm và hậu mãi đầy đủ hơn. "
            "Đơn khách có thể được liên kết khi thông tin nhận diện phù hợp."
        )
    if _contains(message, "cho nguoi khac"):
        return "Bạn có thể đặt cho người khác bằng cách nhập đúng tên, số điện thoại và địa chỉ người nhận tại bước Thanh toán."
    if _contains(message, "gio cu the"):
        return "Bạn có thể ghi chú khung giờ mong muốn, nhưng thời gian chính xác còn phụ thuộc đơn vị vận chuyển và chưa được bảo đảm cho đến khi xác nhận."
    if _contains(message, "nhieu dia chi", "tach don"):
        return "Mỗi đơn hiện dùng một địa chỉ nhận. Muốn giao nhiều địa chỉ, bạn cần tách sản phẩm và tạo các đơn riêng."
    if _contains(message, "nhan tai cua hang"):
        return "Bạn chỉ chọn nhận tại cửa hàng khi tùy chọn này xuất hiện ở bước giao nhận; khả năng áp dụng phụ thuộc sản phẩm và điểm nhận."

    if _contains(message, "them san pham", "xem gio", "thay doi so luong", "xoa mot san pham", "chon lai mau"):
        return (
            "Chọn đúng màu/phiên bản rồi bấm Thêm vào giỏ. Trong biểu tượng Giỏ hàng, bạn có thể tăng giảm số lượng, "
            "xóa từng dòng hoặc quay lại trang sản phẩm để chọn biến thể khác."
            + cart_summary
        )
    if _contains(message, "nhieu mau"):
        return "Bạn có thể thêm từng màu hoặc phiên bản thành các dòng riêng trong giỏ, miễn mỗi biến thể còn đủ tồn kho."
    if _contains(message, "luu san pham de mua sau"):
        return "Giỏ chưa có nút “mua sau” riêng; bạn có thể thêm sản phẩm vào Yêu thích rồi xóa khỏi giỏ."
    if _contains(message, "dang xuat", "gio hang duoc luu"):
        return "Giỏ được lưu trên trình duyệt hiện tại nên thường vẫn còn sau khi tải lại hoặc đăng xuất; xóa dữ liệu trình duyệt hoặc đổi thiết bị có thể làm mất giỏ."
    if _contains(message, "giu hang", "giu nguyen", "het hang"):
        return "Sản phẩm và giá trong giỏ chưa được giữ chắc chắn. Giá, ưu đãi và tồn kho được kiểm tra lại khi bạn xác nhận đơn."
    if _contains(message, "gioi han so luong"):
        return "Mỗi dòng tối đa 99 sản phẩm, đồng thời không được vượt tồn khả dụng hoặc giới hạn riêng của chương trình bán hàng."
    return "Bạn có thể quản lý biến thể và số lượng trong giỏ, sau đó kiểm tra toàn bộ địa chỉ, ưu đãi, phí giao và tổng tiền trước khi đặt."


def _voucher_value(voucher: dict, subtotal: Decimal) -> Decimal:
    discount_type = str(voucher.get("discountType") or voucher.get("discount_type") or "").upper()
    value = Decimal(str(voucher.get("discountAmount") or voucher.get("discount_amount") or 0))
    discount = subtotal * value / 100 if "PERCENT" in discount_type else value
    maximum = voucher.get("maxDiscount") if "maxDiscount" in voucher else voucher.get("max_discount")
    if maximum is not None:
        discount = min(discount, Decimal(str(maximum)))
    minimum = Decimal(str(voucher.get("minOrderValue") or voucher.get("min_order_value") or 0))
    return max(Decimal(0), discount) if subtotal >= minimum else Decimal(0)


def _voucher_line(voucher: dict, subtotal: Decimal) -> str:
    code = str(voucher.get("code") or "")
    discount = _voucher_value(voucher, subtotal)
    minimum = Decimal(str(voucher.get("minOrderValue") or voucher.get("min_order_value") or 0))
    expiry = _date(voucher.get("expiresAt") or voucher.get("expires_at"))
    parts = [code, f"ước tính giảm {_money(discount)}" if subtotal else str(voucher.get("displayTitle") or voucher.get("display_title") or "đang khả dụng")]
    if minimum:
        parts.append(f"đơn từ {_money(minimum)}")
    if expiry:
        parts.append(f"hết hạn {expiry}")
    return " – ".join(parts)


def render_voucher_support_answer(context: dict) -> str:
    message = normalize_text(str(context.get("message") or ""))
    public_vouchers = context.get("public_vouchers") or []
    user_vouchers = context.get("user_vouchers")
    cart_items = context.get("cart_items") or []
    subtotal = sum(Decimal(str(item.get("price") or 0)) * int(item.get("quantity") or 0) for item in cart_items)
    vouchers = list(user_vouchers or public_vouchers)
    matched = next((item for item in vouchers if normalize_text(str(item.get("code") or "")) in message), None)

    if _contains(message, "trong tai khoan", "voucher nao dung duoc", "co voucher nao", "ma giam gia nao"):
        if user_vouchers is None and _contains(message, "tai khoan", "cua toi"):
            return "Bạn vui lòng đăng nhập để mình đọc ví voucher cá nhân. Các mã công khai vẫn được hiển thị tại giỏ hoặc trang voucher."
        if not vouchers:
            return "Hiện mình chưa tìm thấy voucher khả dụng trong phạm vi tài khoản hoặc chương trình công khai."
        lines = "; ".join(_voucher_line(item, subtotal) for item in vouchers[:5])
        return f"Các voucher đang khả dụng: {lines}. Điều kiện cuối cùng được kiểm tra theo giỏ và phương thức thanh toán."
    if _contains(message, "ma nao giup", "ma phan tram hay", "giam nhieu nhat", "co loi hon"):
        if not vouchers:
            return "Mình chưa có voucher khả dụng để so sánh. Bạn hãy đăng nhập hoặc cung cấp mã cần kiểm tra."
        if subtotal <= 0:
            return "Bạn cần có sản phẩm trong giỏ để mình tính mã có lợi nhất theo tổng tiền và giới hạn giảm."
        ranked = sorted(vouchers, key=lambda item: _voucher_value(item, subtotal), reverse=True)
        best = ranked[0]
        return f"Với giỏ tạm tính {_money(subtotal)}, mã {_voucher_line(best, subtotal)}. Kết quả còn phụ thuộc sản phẩm, kênh và phương thức thanh toán."
    if _contains(message, "khong ap dung", "khong ton tai", "het han", "het luot", "bao da dung", "khong du dieu kien", "chua dat", "khong nhan"):
        if matched:
            return f"Mã {_voucher_line(matched, subtotal)}. Hãy kiểm tra thêm phạm vi sản phẩm, kênh, phương thức thanh toán và giới hạn mỗi người; hệ thống sẽ hiển thị lý do chính xác khi áp dụng."
        return "Bạn hãy gửi đúng mã voucher và kiểm tra ngày hết hạn, giá trị đơn tối thiểu, sản phẩm áp dụng, số lượt, kênh và phương thức thanh toán. Không nên tạo lại đơn chỉ để thử mã."
    if _contains(message, "bao nhieu voucher", "cung luc", "cong don", "cung diem", "uu dai ngan hang"):
        return "Chỉ các voucher có thuộc tính cho phép cộng dồn mới dùng chung được; điểm hoặc ưu đãi thanh toán cũng phải qua kiểm tra tại giỏ. Tổng giảm chính xác luôn hiển thị trước khi xác nhận."
    if _contains(message, "don bi huy", "tra hang", "cho hoan", "cap lai", "hoan voucher"):
        return "Voucher được trả lại hay không phụ thuộc trạng thái đơn và chính sách hoàn của chính mã. Hãy theo dõi Ví voucher sau khi đơn hoàn tất hủy/hoàn; mã đã hết hạn không mặc nhiên được cấp lại."
    if _contains(message, "chuyen cho", "ban hoac trao doi", "quy doi thanh tien"):
        return "Voucher gắn với tài khoản không được tự chuyển, bán hoặc quy đổi thành tiền, trừ khi điều khoản công khai của mã ghi rõ khác."
    if _contains(message, "luu ma", "nhan voucher"):
        return "Bạn có thể nhận/lưu voucher từ trang chương trình hoặc ví voucher khi mã còn lượt và tài khoản đủ điều kiện; mã công khai cũng có thể nhập trực tiếp tại giỏ."
    if _contains(message, "sau khi da dat"):
        return "Không thể áp dụng voucher sau khi đơn đã được tạo; bạn cần kiểm tra mã và tổng giảm trước khi xác nhận."
    if matched:
        return f"Thông tin hiện có của mã {_voucher_line(matched, subtotal)}. Điều kiện cuối cùng được kiểm tra tại giỏ hàng."
    if _contains(message, "nhap ma o dau"):
        return "Bạn nhập hoặc chọn voucher tại phần ưu đãi ở Giỏ hàng/Thanh toán, rồi kiểm tra dòng giảm giá trước khi đặt đơn."
    if vouchers:
        return "Các mã hiện có: " + "; ".join(_voucher_line(item, subtotal) for item in vouchers[:5]) + "."
    return "Mình chưa tìm thấy mã phù hợp. Bạn có thể cung cấp mã voucher hoặc đăng nhập để kiểm tra ví cá nhân."


def render_account_support_answer(context: dict) -> str:
    message = normalize_text(str(context.get("message") or ""))
    account = context.get("account")

    if _contains(message, "dang ky"):
        if "so dien thoai" in message:
            return "Hệ thống hiện đăng ký bằng email và mã xác minh; số điện thoại được bổ sung trong Hồ sơ sau khi đăng ký."
        return "Chọn Đăng ký, nhập tên, email và mật khẩu, sau đó nhập mã xác minh gửi qua email. Mã đăng ký có hiệu lực 15 phút."
    if _contains(message, "google"):
        return "Hệ thống có hỗ trợ đăng nhập Google bằng email đã được Google xác minh."
    if _contains(message, "apple"):
        return "Hệ thống hiện chưa hỗ trợ đăng nhập Apple; bạn có thể dùng email/mật khẩu hoặc Google."
    if _contains(message, "khong can tai khoan"):
        return "Bạn có thể mua hàng với tư cách khách, nhưng cần đăng nhập để theo dõi đầy đủ đơn, voucher, điểm và hậu mãi."
    if _contains(message, "otp", "xac minh"):
        return "Mã xác minh đăng ký có hiệu lực 15 phút; mã đặt lại mật khẩu có hiệu lực 30 phút. Không cung cấp OTP cho chatbot hoặc nhân viên. Nếu không nhận được, kiểm tra Spam rồi dùng Gửi lại; hệ thống giới hạn số lần gửi/nhập."
    if _contains(message, "email da ton tai", "so dien thoai da duoc su dung"):
        return "Nếu email đã tồn tại, hãy dùng Đăng nhập hoặc Quên mật khẩu thay vì tạo tài khoản mới. Số điện thoại là thông tin hồ sơ; trường hợp trùng cần liên hệ hỗ trợ để xác minh chủ sở hữu."
    if _contains(message, "khong the dang nhap", "tai khoan bi khoa"):
        return "Hãy kiểm tra email, mật khẩu và trạng thái xác minh, rồi thử Quên mật khẩu. Tài khoản bị tạm ngưng cần nhân viên xác minh; không gửi mật khẩu hoặc OTP qua chat."

    if _contains(message, "quen mat khau", "dat lai mat khau", "email dat lai", "lien ket dat lai"):
        return "Tại Đăng nhập, chọn Quên mật khẩu, nhập email rồi dùng mã hoặc liên kết được gửi. Yêu cầu có hiệu lực 30 phút; đặt lại thành công sẽ thu hồi các phiên đăng nhập cũ."
    if _contains(message, "doi mat khau"):
        return "Sau khi đăng nhập, mở Cài đặt tài khoản và chọn Đổi mật khẩu. Nếu không nhớ mật khẩu hiện tại, dùng quy trình Quên mật khẩu."
    if _contains(message, "truy cap trai phep", "otp du khong dang nhap", "hoat dong dang ngo"):
        return "Không cung cấp OTP. Hãy đổi mật khẩu ngay, mở danh sách Phiên đăng nhập để thu hồi thiết bị lạ và liên hệ hỗ trợ nếu có giao dịch bất thường."
    if _contains(message, "dang xuat khoi tat ca", "xoa thiet bi", "lich su dang nhap"):
        return "Trong Cài đặt bảo mật, bạn có thể xem các phiên đang hoạt động theo thiết bị/IP và thu hồi từng phiên. Đặt lại mật khẩu sẽ thu hồi toàn bộ phiên cũ."
    if _contains(message, "hai buoc", "2fa"):
        return "Xác thực hai bước hiện chưa mở cho tài khoản khách hàng; quản trị viên có MFA riêng. Bạn nên dùng mật khẩu mạnh và kiểm tra các phiên đăng nhập."
    if _contains(message, "luu thong tin the"):
        return "Cửa hàng không yêu cầu chatbot lưu số thẻ đầy đủ, CVV, PIN hoặc OTP. Thanh toán thẻ được xử lý qua cổng thanh toán; không gửi các mã bảo mật qua chat."

    if _contains(message, "doi ten", "doi so dien thoai", "cap nhat gioi tinh", "thong tin tuy chon"):
        return "Sau khi đăng nhập, mở Tài khoản → Cài đặt, chọn Chỉnh sửa hồ sơ rồi lưu tên, số điện thoại hoặc thông tin tùy chọn."
    if _contains(message, "doi email"):
        return "Email đăng nhập hiện không tự đổi trong hồ sơ. Bạn cần liên hệ hỗ trợ để xác minh danh tính và phương án xử lý."
    if _contains(message, "ngay sinh"):
        return "Ngày sinh chỉ nhập một lần và sau đó bị khóa. Nếu nhập sai, bạn cần liên hệ chăm sóc khách hàng để xác minh trước khi điều chỉnh."
    if _contains(message, "dia chi"):
        count = int((account or {}).get("addressCount") or 0)
        suffix = f" Tài khoản hiện có {count} địa chỉ đã lưu." if account else ""
        return "Mở Tài khoản → Địa chỉ để thêm nhiều địa chỉ, chỉnh sửa, xóa hoặc đặt một địa chỉ mặc định. Địa chỉ của đơn đã tạo không tự thay đổi theo hồ sơ." + suffix
    if _contains(message, "xoa tai khoan"):
        return "Bạn có thể yêu cầu xóa tại phần Cài đặt tài khoản. Thao tác cần đăng nhập và xác nhận; chatbot không tự xóa tài khoản thay bạn."
    if _contains(message, "tai du lieu", "an lich su"):
        return "Hệ thống chưa có nút tải toàn bộ dữ liệu hoặc ẩn lịch sử mua hàng. Bạn có thể gửi yêu cầu hỗ trợ quyền dữ liệu; đơn và giao dịch vẫn được lưu theo nghĩa vụ vận hành/pháp lý."
    if _contains(message, "muc dich gi"):
        return "Thông tin cá nhân được dùng để xác thực tài khoản, xử lý giao nhận, thanh toán, chăm sóc sau bán và chống gian lận theo chính sách bảo mật."

    if _contains(message, "hai tai khoan", "gop", "chuyen don hang", "chuyen bao hanh"):
        return "Hệ thống không tự gộp tài khoản, điểm, đơn hàng hoặc hồ sơ bảo hành. Nhân viên phải xác minh quyền sở hữu trước khi xem xét; chatbot không chuyển dữ liệu thay bạn."
    if _contains(message, "mat so dien thoai cu", "khong con truy cap email", "lay lai tai khoan", "khoi phuc"):
        return "Nếu còn truy cập email, hãy dùng Quên mật khẩu để giữ nguyên lịch sử. Nếu mất cả email hoặc tài khoản bị vô hiệu hóa, liên hệ hỗ trợ để xác minh; không cung cấp OTP/mật khẩu qua chat."
    if account:
        return (
            f"Tài khoản đang ở trạng thái {account.get('status') or 'ACTIVE'}, email {account.get('maskedEmail') or 'đã ẩn'}, "
            f"có {int(account.get('addressCount') or 0)} địa chỉ và {int(account.get('activeSessionCount') or 0)} phiên đăng nhập hoạt động."
        )
    return "Bạn có thể hỏi về đăng ký, đăng nhập, mật khẩu, phiên đăng nhập, hồ sơ, địa chỉ hoặc khôi phục tài khoản. Thông tin riêng tư chỉ được đọc sau khi đăng nhập."


def render_product_review_answer(context: dict) -> str:
    message = normalize_text(str(context.get("message") or ""))
    product = context.get("product") or {}
    insights = context.get("review_insights") or {}
    eligibility = context.get("review_eligibility")
    name = str(product.get("name") or "sản phẩm này")
    count = int(insights.get("reviewCount") or product.get("reviewCount") or 0)
    rating = float(insights.get("averageRating") or product.get("rating") or 0)
    distribution = insights.get("ratingDistribution") or {}
    positive = insights.get("positiveComments") or []
    critical = insights.get("criticalComments") or []

    if _contains(message, "lam sao danh gia", "can mua hang", "sua danh gia", "xoa danh gia", "dang hinh", "chua hien thi", "noi dung nao", "cua hang co tra loi", "cap nhat danh gia"):
        if eligibility:
            return str(eligibility.get("message") or "") + " Đánh giá mới được gửi ở trạng thái chờ duyệt; trong thời hạn cho phép bạn có thể sửa hoặc xóa từ trang sản phẩm/tài khoản."
        return "Chỉ khách có đơn đã thanh toán và hoàn thành mới được đánh giá trong thời hạn quy định. Đánh giá có thể kèm ảnh, sẽ chờ kiểm duyệt; chủ đánh giá có thể sửa hoặc xóa khi còn thời hạn."
    if _contains(message, "bao cao danh gia", "danh gia an danh", "danh gia dich vu", "danh gia chi nhanh", "nhan diem"):
        return "Hệ thống hiện hỗ trợ đánh giá sản phẩm bằng tên tài khoản; chưa có luồng riêng để chấm điểm giao hàng/chi nhánh hoặc thưởng điểm mặc định. Nội dung không phù hợp có thể chuyển hỗ trợ để kiểm tra."
    if _contains(message, "kiem duyet", "danh gia that", "nguoi da mua"):
        verified = int(insights.get("verifiedPurchaseCount") or 0)
        return f"{name} có {verified}/{count} đánh giá công khai gắn với đơn mua đã xác minh. Đánh giá mới qua trạng thái chờ duyệt; cửa hàng không nên coi mọi nhận xét là kết luận kỹ thuật."
    if _contains(message, "mot sao", "1 sao"):
        one_star = int(distribution.get("1") or distribution.get(1) or 0)
        return f"{name} hiện có {one_star} đánh giá 1 sao trên tổng {count} đánh giá công khai."
    if _contains(message, "diem danh gia", "bao nhieu luot", "danh gia tot"):
        if not count:
            return f"{name} chưa có đánh giá công khai đủ để kết luận chất lượng thực tế."
        return f"{name} đang đạt {rating:.1f}/5 từ {count} đánh giá công khai. Đây là dữ liệu người dùng, không phải kết quả kiểm nghiệm độc lập."
    if _contains(message, "thuong khen", "tich cuc"):
        if positive:
            return f"Nhận xét tích cực gần đây về {name}: " + "; ".join(str(item) for item in positive[:3]) + "."
        return f"Chưa có đủ nhận xét tích cực bằng văn bản về {name} để tổng hợp mà không suy đoán."
    if _contains(message, "phan nan", "tieu cuc", "nhuoc diem", "thuong bi loi"):
        if critical:
            return f"Nhận xét cần lưu ý về {name}: " + "; ".join(str(item) for item in critical[:3]) + ". Trải nghiệm có thể khác theo cách sử dụng."
        return f"Chưa có đủ nhận xét tiêu cực bằng văn bản về {name} để kết luận lỗi phổ biến."
    if _contains(message, "ty le doi tra", "mua lai"):
        return "Dữ liệu công khai hiện không có chỉ số tỷ lệ đổi trả hoặc mua lại theo sản phẩm; mình không suy đoán các con số này."
    if _contains(message, "pin thuc te", "nong", "camera", "de su dung", "ben sau", "am thanh", "ngoai troi", "nang", "do on", "ve sinh", "thuc te"):
        excerpts = [*positive[:2], *critical[:2]]
        if excerpts:
            return f"Trải nghiệm công khai gần đây về {name}: " + "; ".join(str(item) for item in excerpts) + ". Đây là trải nghiệm cá nhân, phụ thuộc điều kiện sử dụng."
        return f"Chưa có đủ nhận xét thực tế bằng văn bản về {name}. Mình có thể cung cấp thông số hãng, nhưng không nên biến thông số thành trải nghiệm giả định."
    if count:
        return f"{name} hiện có {rating:.1f}/5 từ {count} đánh giá công khai. Mình có thể tách nhận xét tích cực và tiêu cực nếu dữ liệu văn bản đủ."
    return f"{name} chưa có đánh giá công khai đủ để tổng hợp."
