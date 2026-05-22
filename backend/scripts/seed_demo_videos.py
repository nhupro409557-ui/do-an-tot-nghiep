import asyncio

from sqlalchemy import text

from app.infrastructure.database.session import AsyncSessionFactory


DEMO_VIDEOS = [
    ("[DEMO] Trên tay iPhone 16 Pro Max - màu titan mới", "Giới thiệu thiết kế, màn hình, camera và trải nghiệm cầm nắm của điện thoại cao cấp.", "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] So sánh Samsung Galaxy Z Fold6 và flagship thường", "Tư vấn nhanh về màn hình gập, đa nhiệm, pin và nhóm khách hàng phù hợp.", "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Laptop cho sinh viên IT tầm 20 triệu", "Gợi ý cấu hình laptop học lập trình: CPU, RAM, SSD, màn hình và thời lượng pin.", "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Cách chọn sạc nhanh an toàn cho điện thoại", "Mẹo chọn củ sạc, cáp Type-C, công suất phù hợp và lưu ý bảo vệ pin.", "https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Review nhanh AirPods Pro 2 USB-C", "Giới thiệu chống ồn, xuyên âm, thời lượng pin và khả năng kết nối hệ sinh thái Apple.", "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Apple Watch Ultra 2 có phù hợp đi tập không?", "Nội dung demo về đồng hồ thông minh: cảm biến sức khỏe, GPS, độ bền và thời lượng pin.", "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Mẹo quay vlog bằng DJI Pocket 3", "Video demo cho nhóm máy ảnh/camera: chống rung, lấy nét, âm thanh và gợi ý phụ kiện.", "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Chính sách bảo hành và đổi trả tại Echophone", "Giúp khách hiểu nhanh quy trình bảo hành, đổi trả và chuẩn bị thông tin đơn hàng.", "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] OPPO Find N3 - điện thoại gập cho công việc", "Ưu điểm màn hình gập, camera và đa nhiệm khi dùng cho công việc.", "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Samsung S24 Ultra chụp ảnh đêm ra sao?", "Demo về camera, zoom và khả năng xử lý ảnh thiếu sáng.", "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] MacBook Air M3 cho học tập và văn phòng", "Gợi ý laptop mỏng nhẹ, pin lâu, phù hợp học tập và làm việc.", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] ASUS ROG Zephyrus G14 cho game và đồ họa", "Giới thiệu hiệu năng, màn hình, tản nhiệt và nhóm người dùng phù hợp.", "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] iPad Pro M4 thay laptop được không?", "Video demo về màn hình, chip M4, bàn phím và nhu cầu sáng tạo nội dung.", "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Chọn tai nghe chống ồn cho đi học và đi làm", "Mẹo chọn tai nghe theo chống ồn, pin, micro và độ thoải mái.", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Phân biệt cáp Type-C sạc nhanh và cáp thường", "Hướng dẫn đọc công suất, chuẩn sạc và cách chọn cáp an toàn.", "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Garmin Fenix 7 Pro dành cho thể thao ngoài trời", "Demo về GPS, bản đồ, pin và các chế độ luyện tập.", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Camera an ninh Ezviz C6N lắp trong nhà", "Giới thiệu góc xoay, đàm thoại hai chiều và quan sát ban đêm.", "https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Sony Alpha A7 IV cho người mới quay video", "Demo về cảm biến, lấy nét, quay 4K và chống rung.", "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Mẹo kiểm tra máy khi nhận hàng", "Hướng dẫn quay video mở hộp, kiểm tra IMEI, phụ kiện và ngoại hình sản phẩm.", "https://images.unsplash.com/photo-1586880244406-556ebe35f282?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Cách dùng điểm tích lũy để giảm giá đơn hàng", "Quy trình xem điểm, đổi điểm và áp dụng ưu đãi khi thanh toán.", "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Top điện thoại pin trâu cho sinh viên", "Tư vấn nhanh các tiêu chí pin, sạc, màn hình và giá bán.", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Laptop màn đẹp cho thiết kế cơ bản", "Gợi ý thông số màn hình, màu sắc, RAM và card đồ họa cho thiết kế nhẹ.", "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Cách chọn smartwatch theo cổ tay", "Tư vấn kích thước mặt, dây đeo, pin và tính năng sức khỏe.", "https://images.unsplash.com/photo-1544117519-31a4b719223d?auto=format&fit=crop&w=900&q=80"),
    ("[DEMO] Voucher và flash sale cần lưu ý gì?", "Giải thích điều kiện áp mã, đơn tối thiểu và thời hạn sử dụng voucher.", "https://images.unsplash.com/photo-1607083206968-13611e3d76db?auto=format&fit=crop&w=900&q=80"),
]


async def main() -> None:
    async with AsyncSessionFactory() as session:
        await session.execute(text("DELETE FROM videos WHERE title LIKE '[DEMO]%'"))
        for index, (title, description, thumbnail_url) in enumerate(DEMO_VIDEOS):
            video_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" if index % 2 == 0 else "https://www.w3schools.com/html/mov_bbb.mp4"
            await session.execute(
                text(
                    """
                    INSERT INTO videos (title, description, video_url, thumbnail_url, is_active, created_at)
                    VALUES (:title, :description, :video_url, :thumbnail_url, TRUE, NOW() - (:offset_minutes * INTERVAL '1 minute'))
                    """
                ),
                {
                    "title": title,
                    "description": description,
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url,
                    "offset_minutes": 10 + index * 15,
                },
            )
        await session.commit()
        count = await session.scalar(text("SELECT COUNT(*) FROM videos WHERE is_active = TRUE AND title LIKE '[DEMO]%'"))
        print(f"Seeded {count} demo videos.")


if __name__ == "__main__":
    asyncio.run(main())
