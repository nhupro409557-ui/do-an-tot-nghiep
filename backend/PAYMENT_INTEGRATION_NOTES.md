# Ghi chú tích hợp thanh toán

## MoMo sandbox

- Production cần cấu hình `MOMO_PARTNER_CODE`, `MOMO_ACCESS_KEY`, `MOMO_SECRET_KEY`,
  `MOMO_REDIRECT_URL` và `MOMO_IPN_PATH` bằng URL HTTPS công khai.
- MoMo sandbox có thể không gửi IPN khi người dùng từ chối thanh toán (`resultCode=1006`).
- Khi giao dịch còn `PENDING`, API đọc trạng thái sẽ đối soát với MoMo. Các mã thất bại
  cuối cùng `1001-1007`, `1017` và `1026` phải chuyển giao dịch sang `FAILED`, đồng thời
  chuyển đơn đang chờ thanh toán sang `PAYMENT_FAILED` để giải phóng tài nguyên giữ chỗ.
- Không chuyển trạng thái thất bại cho mã thành công `0` hoặc các mã đang chờ như `1000`,
  `7002`.

## ZaloPay sandbox

- Production cần cấu hình `ZALOPAY_APP_ID`, `ZALOPAY_KEY1`, `ZALOPAY_KEY2` và
  `ZALOPAY_CALLBACK_URL` bằng URL HTTPS công khai.
- Callback phải được xác minh bằng `KEY2`; không tin dữ liệu trả về từ trình duyệt.
