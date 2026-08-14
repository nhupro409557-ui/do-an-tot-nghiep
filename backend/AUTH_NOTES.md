# Ghi chú xác thực

## JWT trên môi trường serverless

- Luôn ưu tiên cấu hình `JWT_SECRET_KEY` từ biến môi trường.
- Khi biến này chưa có, `default_jwt_secret_key()` tạo khóa dự phòng ổn định bằng SHA-256 từ `DATABASE_URL` và chuỗi phân tách cố định.
- Không dùng khóa ngẫu nhiên theo từng tiến trình: các instance serverless khác nhau phải xác minh được token do nhau phát hành.
- Kiểm thử hồi quy nằm tại `tests/test_config_jwt_secret.py`.
