-- Bổ sung cột recipient_email vào bảng orders để lưu email khách hàng khi tạo đơn hàng (online/offline)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS recipient_email VARCHAR(255);
