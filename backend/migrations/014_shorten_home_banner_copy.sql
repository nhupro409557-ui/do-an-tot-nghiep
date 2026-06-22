-- Rút gọn nội dung banner trang chủ để dễ đọc trên thanh chuyển banner.

UPDATE videos
SET title = CASE sort_order
        WHEN 1 THEN 'ĐIỆN THOẠI NỔI BẬT'
        WHEN 2 THEN 'MÁY TÍNH BẢNG'
        WHEN 3 THEN 'LAPTOP HIỆU NĂNG'
        WHEN 4 THEN 'PHỤ KIỆN CHÍNH HÃNG'
        WHEN 5 THEN 'CAMERA AN NINH'
        WHEN 94 THEN 'MÁY ẢNH SÁNG TẠO'
        WHEN 95 THEN 'ĐỒNG HỒ THÔNG MINH'
        ELSE title
    END,
    description = CASE sort_order
        WHEN 1 THEN 'Smartphone chính hãng, nhiều ưu đãi.'
        WHEN 2 THEN 'Học tập, làm việc, giải trí.'
        WHEN 3 THEN 'Mạnh mẽ cho mọi nhu cầu.'
        WHEN 4 THEN 'Tiện ích, đồng bộ, bền bỉ.'
        WHEN 5 THEN 'Giám sát an toàn, thông minh.'
        WHEN 94 THEN 'Ghi lại mọi khoảnh khắc.'
        WHEN 95 THEN 'Theo dõi sức khỏe mỗi ngày.'
        ELSE description
    END,
    updated_at = NOW()
WHERE content_type = 'BANNER'
  AND sort_order IN (1, 2, 3, 4, 5, 94, 95);
