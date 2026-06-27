-- Làm sạch các từ ngữ Sandbox/thử nghiệm trong tên và mô tả phương thức thanh toán
UPDATE payment_methods
SET name = 'Ví điện tử MoMo',
    description = 'Thanh toán trực tuyến qua ứng dụng ví điện tử MoMo.'
WHERE code = 'MOMO';

UPDATE payment_methods
SET name = 'Ví điện tử ZaloPay',
    description = 'Thanh toán trực tuyến qua ứng dụng ví điện tử ZaloPay.'
WHERE code = 'ZALOPAY';

UPDATE payment_methods
SET name = 'Cổng thanh toán VNPAY',
    description = 'Thanh toán trực tuyến qua cổng thanh toán VNPAY.'
WHERE code = 'VNPAY';
