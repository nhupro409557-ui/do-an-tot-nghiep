from app.application.ai.intent_router import normalize_text


INTENT_REQUIREMENTS = {
    "PRODUCT_SEARCH": (
        "Nêu đúng sản phẩm khớp câu hỏi; tóm tắt giá hiện hành, tình trạng còn hàng, "
        "các biến thể và thông tin bảo hành nếu dữ liệu có cung cấp."
    ),
    "PRODUCT_RECOMMENDATION": (
        "Đề xuất tối đa ba sản phẩm dựa trên nhu cầu và ngân sách đã nêu. Với mỗi lựa chọn, "
        "giải thích lý do phù hợp, giá, tình trạng hàng và một điểm cần cân nhắc từ dữ liệu."
    ),
    "PRODUCT_COMPARISON": (
        "So sánh đúng các sản phẩm được cung cấp theo cùng tiêu chí có dữ liệu như giá, biến thể, "
        "cấu hình, bảo hành và tồn kho; kết luận theo từng nhu cầu, không tuyên bố một máy tốt hơn tuyệt đối."
    ),
    "PRICE_AND_PROMOTION": (
        "Nêu giá bán hiện hành của đúng sản phẩm. Nếu có giá gốc hoặc khuyến mãi thì nêu rõ phần giảm, "
        "điều kiện có trong dữ liệu; nếu không có thì nói chưa ghi nhận ưu đãi thay vì tự tạo voucher."
    ),
    "STOCK_AVAILABILITY": (
        "Nêu rõ đúng sản phẩm còn hàng hay tạm hết dựa trên availableStock. Nếu câu hỏi nhắc biến thể, "
        "chỉ xác nhận biến thể khi dữ liệu biến thể và tồn kho đủ rõ."
    ),
    "USED_PRODUCT_ADVICE": (
        "Với từng máy cũ, nêu giá, hạng ngoại hình, sức khỏe pin, thời hạn bảo hành và tình trạng sẵn sàng bán "
        "nếu các trường này có dữ liệu; không tiết lộ IMEI, serial hoặc vị trí kho."
    ),
    "ORDER_LOOKUP": (
        "Trả mã đơn, trạng thái xử lý, trạng thái thanh toán và tổng tiền nếu có. Chỉ nói bước tiếp theo "
        "khi có dữ liệu; không tự hủy hoặc thay đổi đơn."
    ),
    "SHIPPING_LOOKUP": (
        "Trả mã đơn, trạng thái giao, mã vận đơn, đơn vị vận chuyển và sự kiện mới nhất nếu có. "
        "Không tự đặt ngày giao dự kiến khi dữ liệu không cung cấp."
    ),
    "AFTER_SALES_LOOKUP": (
        "Trả mã hồ sơ, loại bảo hành hoặc đổi trả, trạng thái hiện tại, hướng xử lý, hạn SLA và cập nhật mới nhất "
        "nếu có. Không khẳng định đã đổi máy hoặc hoàn tiền nếu trạng thái chưa thể hiện điều đó."
    ),
    "LOYALTY": (
        "Nêu số điểm, hạng thành viên, trạng thái ví, doanh số xét hạng trong kỳ và số tiền còn thiếu để đạt hạng tiếp theo "
        "nếu dữ liệu có cung cấp; không tự suy đoán điểm sắp cộng hoặc doanh số ngoài kỳ."
    ),
    "STORE_POLICY": (
        "Trả đúng nội dung chính sách đang hoạt động trong dữ liệu cửa hàng và nói rõ khi mục được hỏi chưa cấu hình."
    ),
    "WARRANTY_POLICY": (
        "Trả đúng chính sách bảo hành đang hoạt động; không áp một thời hạn chung nếu còn phụ thuộc sản phẩm hoặc đơn mua."
    ),
    "COMPLAINT": (
        "Xin lỗi ngắn gọn, nhắc lại đúng vấn đề khách gặp và đề nghị chuyển nhân viên; không hứa hoàn tiền hay bồi thường."
    ),
}


def build_answer_requirements(*, intent: str, message: str) -> str:
    requirements = [
        "Trả lời trực tiếp câu khách đang hỏi trước, sau đó mới bổ sung thông tin liên quan.",
        INTENT_REQUIREMENTS.get(
            intent,
            "Chỉ trả lời bằng dữ liệu đã cung cấp và nói rõ thông tin nào chưa có.",
        ),
    ]
    normalized = normalize_text(message)
    if any(term in normalized for term in ("bien the", "phien ban", "ban nao", "256gb", "512gb", "mau")):
        requirements.append("Ưu tiên liệt kê biến thể, dung lượng, RAM hoặc màu có trong dữ liệu; không tự suy ra tồn kho từng biến thể.")
    if any(term in normalized for term in ("khuyen mai", "uu dai", "voucher", "giam gia", "sale")):
        requirements.append("Phân biệt giá bán của sản phẩm với voucher cá nhân; không nói voucher khả dụng nếu context không có voucher đó.")
    if any(term in normalized for term in ("bao lau", "bao gio", "du kien", "khi nao")):
        requirements.append("Chỉ nêu mốc thời gian khi context có thời hạn hoặc sự kiện tương ứng; nếu thiếu phải nói chưa có thời gian xác nhận.")
    if any(term in normalized for term in ("moi nhat", "moi them", "vua them", "hang moi ve")):
        requirements.append("Dùng createdAt để xác định sản phẩm được thêm gần nhất; không nhầm với sản phẩm nổi bật, bán chạy hoặc mới cập nhật giá.")
    return " ".join(requirements)
