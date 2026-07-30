from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.payment_method_service import list_public_payment_methods
from app.config import settings
from app.infrastructure.database.repositories.store_info_repo import (
    get_store_info,
    list_store_policies,
)


def _normalize(value: str) -> str:
    from app.application.ai.intent_router import normalize_text

    return normalize_text(value)


def _contains(value: str, *terms: str) -> bool:
    return any(term in value for term in terms)


def _policy_topic(message: str) -> str:
    normalized = _normalize(message)
    if _contains(
        normalized,
        "gio hang",
        "trong gio",
        "them san pham",
        "xoa san pham",
        "dat hang",
        "checkout",
    ):
        return "CART_ORDER"
    if _contains(
        normalized,
        "dang ky tai khoan", "dang nhap", "mat khau", "ma otp", "xac minh tai khoan",
        "khoa tai khoan", "thong tin ca nhan", "dia chi mac dinh",
    ):
        return "ACCOUNT"
    if _contains(normalized, "voucher", "ma giam", "ma mien phi", "ma qua tang"):
        return "VOUCHER"
    if _contains(normalized, "danh gia", "nhan xet", "luot danh gia"):
        return "REVIEW"
    if _contains(
        normalized,
        "dan kinh", "chuyen du lieu", "cai dat may", "lap dat", "ve sinh san pham",
        "phu kien", "bao hanh mo rong", "bao hiem",
    ):
        return "ACCESSORY_SERVICE"
    if _contains(normalized, "hoan tien", "tien hoan"):
        return "REFUND"
    if _contains(normalized, "dieu khoan", "quyen loi nguoi mua", "trach nhiem", "cookie"):
        return "TERMS"
    if _contains(normalized, "hotline", "email ho tro", "fanpage", "zalo", "goi lai"):
        return "STORE_CONTACT"
    if _contains(normalized, "bao hanh", "may thay the"):
        return "WARRANTY"
    if _contains(normalized, "o dau", "dia chi", "chi nhanh", "cua hang nao"):
        return "STORE_ADDRESS"
    if _contains(normalized, "may gio", "mo cua", "dong cua", "gio lam viec"):
        return "OPENING_HOURS"
    if _contains(normalized, "tra gop"):
        return "INSTALLMENT"
    if _contains(normalized, "hoa don", "vat"):
        return "VAT_INVOICE"
    if _contains(normalized, "cod", "nhan hang tra tien", "thanh toan khi nhan"):
        return "COD"
    if _contains(normalized, "thanh toan", "hinh thuc tra tien", "phuong thuc"):
        return "PAYMENT_METHODS"
    if _contains(normalized, "chinh hang", "hang that", "hang gia", "xach tay"):
        return "AUTHENTICITY"
    if _contains(normalized, "doi tra", "tra hang", "doi may", "bao nhieu ngay", "mot doi mot", "1 doi 1"):
        return "RETURN_EXCHANGE"
    if _contains(normalized, "bao mat", "du lieu ca nhan", "thong tin ca nhan"):
        return "PRIVACY"
    if _contains(normalized, "kiem tra hang", "dong kiem", "mo hop"):
        return "INSPECTION"
    if _contains(normalized, "giao hang", "van chuyen", "ship", "phi giao", "toan quoc"):
        return "DELIVERY"
    return "GENERAL"


async def get_store_policy_context(session: AsyncSession, message: str) -> dict:
    store = await get_store_info(session)
    methods = await list_public_payment_methods(session)
    policy_rows = await list_store_policies(session)
    active_methods = [method for method in methods if method.get("is_active")]
    active_policies = {
        policy.code.lower(): policy.content
        for policy in policy_rows
        if policy.is_active
    }
    latest_policy_update = max(
        (policy.updated_at for policy in policy_rows if policy.updated_at),
        default=None,
    )
    return {
        "topic": _policy_topic(message),
        "store": {
            "name": getattr(store, "name", None),
            "hotline": getattr(store, "hotline", None),
            "email": getattr(store, "email", None),
            "address": getattr(store, "address", None),
            "description": getattr(store, "description", None),
            "updated_at": (
                store.updated_at.isoformat()
                if store is not None and getattr(store, "updated_at", None)
                else None
            ),
        },
        "payment_methods": active_methods,
        "delivery": {
            "free_shipping_threshold": settings.sandbox_shipping_free_threshold,
            "inner_fee": settings.sandbox_shipping_inner_fee,
            "near_fee": settings.sandbox_shipping_near_fee,
            "far_fee": settings.sandbox_shipping_far_fee,
        },
        "policies": active_policies,
        "source_version": latest_policy_update.isoformat() if latest_policy_update else None,
    }


def render_store_policy_answer(context: dict) -> str:
    topic = context.get("topic")
    store = context.get("store") or {}
    delivery = context.get("delivery") or {}
    policies = context.get("policies") or {}
    methods = [
        method
        for method in (context.get("payment_methods") or [])
        if method.get("is_available")
    ]
    method_names = ", ".join(str(method.get("name") or method.get("code")) for method in methods)

    if topic == "CART_ORDER":
        return (
            "Bạn có thể quản lý sản phẩm, số lượng và biến thể trong giỏ rồi kiểm tra lại địa chỉ, ưu đãi, "
            "phí giao và tổng tiền tại bước xác nhận. Sản phẩm trong giỏ chưa được xem là đã giữ chắc chắn; "
            "tồn kho chỉ được xác nhận theo trạng thái đơn hàng."
        )
    if topic == "ACCOUNT":
        return (
            "Bạn hãy dùng chức năng đăng ký, đăng nhập hoặc Quên mật khẩu trên trang tài khoản. "
            "Không cung cấp mật khẩu, OTP, PIN hoặc CVV cho chatbot hay người tự xưng là nhân viên. "
            "Thông tin đơn hàng, điểm và hậu mãi riêng tư chỉ được tra cứu sau khi đăng nhập."
        )
    if topic == "VOUCHER":
        return (
            "Điều kiện, thời hạn, sản phẩm áp dụng và giới hạn lượt dùng của voucher cần được kiểm tra ngay tại giỏ hàng. "
            "Chatbot hiện không tự áp dụng, giữ hoặc khôi phục voucher cá nhân; tổng giảm chính xác phải hiển thị trước khi xác nhận đơn."
        )
    if topic == "REVIEW":
        return (
            "Điểm và số lượt đánh giá chỉ được nêu khi có dữ liệu công khai của đúng sản phẩm. "
            "Việc đăng, sửa, xóa hoặc kiểm duyệt đánh giá thực hiện theo trạng thái hiển thị trong tài khoản; "
            "chatbot không tự tạo nhận xét hay số liệu trải nghiệm."
        )
    if topic == "ACCESSORY_SERVICE":
        hotline = store.get("hotline")
        suffix = f" Bạn có thể gọi {hotline} để xác nhận dịch vụ tại chi nhánh." if hotline else ""
        return (
            "Khả năng tương thích phụ kiện phụ thuộc đúng model và phiên bản; dịch vụ dán kính, cài đặt, chuyển dữ liệu "
            "hoặc lắp đặt còn phụ thuộc sản phẩm và chi nhánh. Bạn cần cung cấp model và nơi dự kiến nhận hàng."
            + suffix
        )
    if topic == "REFUND":
        return (
            policies.get("return_exchange", "Chính sách hoàn tiền và đổi trả đang được cập nhật.")
            + " Thời điểm và phương thức hoàn thực tế phụ thuộc trạng thái đơn và giao dịch; chatbot không tự thực hiện hoàn tiền."
        )
    if topic == "TERMS":
        return policies.get("privacy", "Chính sách điều khoản và bảo mật đang được cập nhật.")
    if topic == "STORE_CONTACT":
        contacts = [value for value in (store.get("hotline"), store.get("email")) if value]
        return "Thông tin liên hệ cửa hàng: " + ", ".join(contacts) + "." if contacts else "Cửa hàng chưa cập nhật thông tin liên hệ công khai."

    if topic == "STORE_ADDRESS":
        address = store.get("address")
        return f"Địa chỉ cửa hàng: {address}." if address else "Cửa hàng chưa cập nhật địa chỉ công khai."
    if topic == "OPENING_HOURS":
        hotline = store.get("hotline")
        suffix = f" Bạn có thể gọi {hotline} để xác nhận trước khi đến." if hotline else ""
        return policies.get("opening_hours", "Chính sách giờ mở cửa đang được cập nhật.") + suffix
    if topic == "INSTALLMENT":
        return policies.get("installment", "Chính sách trả góp đang được cập nhật.")
    if topic == "VAT_INVOICE":
        return policies.get("vat_invoice", "Chính sách hóa đơn VAT đang được cập nhật.")
    if topic == "COD":
        cod = next((method for method in methods if str(method.get("code") or "").upper() == "COD"), None)
        return "Cửa hàng có hỗ trợ thanh toán khi nhận hàng (COD)." if cod else "COD hiện chưa khả dụng; bạn có thể chọn phương thức khác tại bước thanh toán."
    if topic == "PAYMENT_METHODS":
        return f"Các phương thức thanh toán đang khả dụng: {method_names}." if method_names else "Hiện chưa có phương thức thanh toán khả dụng."
    if topic == "AUTHENTICITY":
        return policies.get("authenticity", "Thông tin nguồn gốc sản phẩm đang được cập nhật.")
    if topic == "RETURN_EXCHANGE":
        return policies.get("return_exchange", "Chính sách đổi trả đang được cập nhật.")
    if topic == "WARRANTY":
        return policies.get("warranty", "Chính sách bảo hành đang được cập nhật.")
    if topic == "PRIVACY":
        return policies.get("privacy", "Chính sách bảo mật đang được cập nhật.")
    if topic == "INSPECTION":
        return policies.get("inspection", "Chính sách kiểm tra hàng đang được cập nhật.")
    if topic == "DELIVERY":
        threshold = int(delivery.get("free_shipping_threshold") or 0)
        fees = [
            int(delivery.get("inner_fee") or 0),
            int(delivery.get("near_fee") or 0),
            int(delivery.get("far_fee") or 0),
        ]
        fee_text = f"{min(fees):,}đ–{max(fees):,}đ".replace(",", ".")
        threshold_text = f"{threshold:,}đ".replace(",", ".")
        policy_text = policies.get("delivery", "Chính sách giao hàng đang được cập nhật.")
        answer = f"{policy_text} Phí tham khảo {fee_text}; đơn từ {threshold_text} được miễn phí vận chuyển."
        if "phi chinh xac" not in _normalize(policy_text):
            answer += " Phí chính xác sẽ hiển thị theo địa chỉ trước khi xác nhận đơn."
        return answer
    return "Bạn có thể hỏi mình về giao hàng, thanh toán, hóa đơn, đổi trả, bảo mật hoặc địa chỉ cửa hàng."
