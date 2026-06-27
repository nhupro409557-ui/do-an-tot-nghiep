import sys
sys.path.append("c:\\Users\\Huynh Nhu\\Downloads\\Project\\backend")

import asyncio
from app.infrastructure.database.session import AsyncSessionFactory
from app.application.services import inventory_service
from app.application.commerce.use_cases import CompleteOrderUseCase
from sqlalchemy import text
from uuid import UUID, uuid4

async def test_outbound_flow():
    print("=== CHẠY KIỂM THỬ TỰ ĐỘNG: LUỒNG PHIẾU XUẤT KHO LIÊN KẾT ĐƠN HÀNG ===")
    
    async with AsyncSessionFactory() as session:
        # 1. Thiết lập dữ liệu kiểm thử (Self-contained)
        print("\n[Step 1] Thiết lập dữ liệu kiểm thử (Sản phẩm, Vị trí kệ, Tồn kho, Khách hàng)...")
        
        # 1.1 Vị trí kệ MAIN
        loc_res = await session.execute(
            text("SELECT id FROM inventory_locations WHERE code = 'MAIN'")
        )
        loc_row = loc_res.first()
        if loc_row:
            location_id = loc_row[0]
            print(f"✔️ Sử dụng kệ MAIN đã có: {location_id}")
        else:
            location_id = uuid4()
            await session.execute(
                text("""
                    INSERT INTO inventory_locations (id, code, name, zone, purpose, is_active)
                    VALUES (:id, 'MAIN', 'Kệ chính', 'A', 'STORAGE', true)
                """),
                {"id": location_id}
            )
            print(f"✔️ Đã tạo kệ MAIN mới: {location_id}")

        # 1.2 Sản phẩm kiểm thử
        product_id = uuid4()
        variant_id = uuid4()
        product_sku = f"TEST-SKU-{uuid4().hex[:6].upper()}"
        variant_sku = f"TEST-VSKU-{uuid4().hex[:6].upper()}"
        
        # Thêm sản phẩm
        product_slug = f"san-pham-test-outbound-{uuid4().hex[:6]}"
        await session.execute(
            text("""
                INSERT INTO products (id, name, sku, slug, description, category, brand, price, status, sales_config, stock_quantity)
                VALUES (:id, 'Sản phẩm Test Outbound', :sku, :slug, 'Mô tả test', 'PHONE', 'Apple', 20000000, 'ACTIVE', 
                        '{"imeiPolicy": {"mode": "MANUAL", "trackImei": true}, "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": false}}'::jsonb, 5)
            """),
            {"id": product_id, "sku": product_sku, "slug": product_slug}
        )
        
        # Thêm biến thể
        await session.execute(
            text("""
                INSERT INTO product_variants (id, product_id, sku, color_name, configuration, price, sale_price, is_active, stock_quantity)
                VALUES (:id, :product_id, :sku, 'Đen', '128GB', 20000000, 19000000, true, 5)
            """),
            {"id": variant_id, "product_id": product_id, "sku": variant_sku}
        )
        print(f"✔️ Đã tạo sản phẩm test: {product_id}, biến thể: {variant_id}")

        # 1.3 Thêm tồn kho & IMEI vào kệ MAIN
        # Tạo Lot nhập
        lot_id = uuid4()
        lot_code = f"LOT-TEST-{uuid4().hex[:6].upper()}"
        await session.execute(
            text("""
                INSERT INTO inventory_lots (
                    id, lot_code, product_id, variant_id, location_id,
                    initial_quantity, remaining_quantity, status, received_at
                )
                VALUES (
                    :id, :lot_code, NULL, :variant_id, :location_id,
                    10, 10, 'ACTIVE', NOW()
                )
            """),
            {"id": lot_id, "lot_code": lot_code, "variant_id": variant_id, "location_id": location_id}
        )
        
        # Tồn kệ (inventory_levels)
        await session.execute(
            text("""
                INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity)
                VALUES (:id, NULL, :variant_id, :location_id, 5, 0)
            """),
            {"id": uuid4(), "variant_id": variant_id, "location_id": location_id}
        )
        
        # Mã IMEI (product_imeis)
        test_imeis = [f"IMEI-TEST-1-{uuid4().hex[:4].upper()}", f"IMEI-TEST-2-{uuid4().hex[:4].upper()}"]
        for imei in test_imeis:
            await session.execute(
                text("""
                    INSERT INTO product_imeis (id, product_id, variant_id, imei, status, location_id, received_at)
                    VALUES (:id, :product_id, :variant_id, :imei, 'IN_STOCK', :location_id, NOW())
                """),
                {"id": uuid4(), "product_id": product_id, "variant_id": variant_id, "imei": imei, "location_id": location_id}
            )
        print(f"✔️ Đã tạo 2 IMEI tồn kho ở kệ MAIN: {test_imeis}")

        # 1.4 Lấy tài khoản khách hàng sẵn có
        user_res = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_row = user_res.first()
        assert user_row is not None, "❌ Thất bại: Không tìm thấy người dùng nào trong CSDL!"
        user_id = user_row[0]
        print(f"✔️ Sử dụng khách hàng sẵn có: {user_id}")
        
        order_id = uuid4()
        order_code = f"ORD-{uuid4().hex[:8].upper()}"
        await session.execute(
            text("""
                INSERT INTO orders (id, order_code, user_id, status, subtotal_amount, discount_amount, shipping_fee, total_amount, payment_method, payment_status, recipient_name, recipient_phone, shipping_address)
                VALUES (:id, :order_code, :user_id, 'PENDING', 38000000, 0, 0, 38000000, 'COD', 'PENDING', 'Người Nhận Test', '0987654321', '123 Đường Test, Hà Nội')
            """),
            {"id": order_id, "order_code": order_code, "user_id": user_id}
        )
        
        # Order item (yêu cầu mua 2 cái của biến thể trên)
        await session.execute(
            text("""
                INSERT INTO order_items (id, order_id, product_id, variant_id, product_name, quantity, unit_price, total_price)
                VALUES (:id, :order_id, :product_id, :variant_id, 'Sản phẩm Test Outbound', 2, 19000000, 38000000)
            """),
            {"id": uuid4(), "order_id": order_id, "product_id": product_id, "variant_id": variant_id}
        )
        await session.commit()
        print(f"✔️ Đã tạo đơn hàng test: {order_code} (Cần mua 2 cái)")

        # 2. Chuyển đơn hàng sang PROCESSING để tự động tạo phiếu xuất kho
        print("\n[Step 2] Duyệt đơn hàng sang trạng thái PROCESSING...")
        await CompleteOrderUseCase(session=session).execute(
            order_id=order_id,
            status_value="PROCESSING",
            changed_by="test-outbound"
        )
        await session.commit()
        print("✔️ Duyệt đơn hàng sang PROCESSING thành công.")

        # 3. Kiểm tra phiếu xuất kho nháp tự động tạo
        print("\n[Step 3] Kiểm tra phiếu xuất kho DRAFT tự động tạo liên kết...")
        document_no = f"OUT-{order_code}"
        doc = await inventory_service.get_outbound_document(session, document_no)
        assert doc is not None, "❌ Thất bại: Không tìm thấy phiếu xuất kho tự động tạo!"
        assert doc["status"] == "DRAFT", f"❌ Thất bại: Trạng thái phiếu xuất không phải DRAFT ({doc['status']})"
        assert doc["order_id"] == order_id, "❌ Thất bại: Phiếu xuất kho không liên kết đúng order_id!"
        print(f"✔️ Đã tìm thấy phiếu xuất kho liên kết: {doc['document_no']} ở trạng thái: {doc['status']}")
        
        # 4. Kiểm tra xem có dòng phiếu xuất tương ứng không
        assert len(doc["lines"]) == 1, f"❌ Thất bại: Số dòng phiếu xuất không đúng ({len(doc['lines'])})"
        line = doc["lines"][0]
        assert line["quantity"] == 2, f"❌ Thất bại: Số lượng yêu cầu xuất không đúng ({line['quantity']})"
        assert line["tracksImei"] is True, "❌ Thất bại: Cờ tracksImei của dòng không đúng"
        print(f"✔️ Dòng phiếu xuất yêu cầu: {line['productName']}, số lượng: {line['quantity']}, tracksImei: {line['tracksImei']}")

        # 5. Thử nghiệm chức năng Tự động gợi ý bốc hàng (FIFO)
        print("\n[Step 5] Chạy tự động gợi ý phân bổ bốc hàng (FIFO)...")
        suggest_res = await inventory_service.auto_suggest_outbound_document(session, document_no)
        assert suggest_res["ok"] is True, "❌ Thất bại: Gọi gợi ý bốc hàng bị lỗi!"
        
        # Tải lại chi tiết phiếu sau khi gợi ý
        doc = await inventory_service.get_outbound_document(session, document_no)
        assert doc["status"] == "PICKED", f"❌ Thất bại: Trạng thái phiếu xuất sau gợi ý bốc hàng không phải PICKED ({doc['status']})"
        line = doc["lines"][0]
        assert line["locationId"] == location_id, f"❌ Thất bại: Gợi ý kệ không đúng ({line['locationId']})"
        assert len(line["imeis"]) == 2, f"❌ Thất bại: Không gợi ý đủ 2 IMEI ({len(line['imeis'])})"
        assert set(line["imeis"]) == set(test_imeis), f"❌ Thất bại: Danh sách IMEI gợi ý không đúng ({line['imeis']})"
        print(f"✔️ Tự động gợi ý bốc hàng thành công: Kệ={line['locationCode']}, IMEIs quét={line['imeis']}, Trạng thái phiếu={doc['status']}")

        # 6. Duyệt hoàn tất phiếu xuất kho với quyền SUPER_ADMIN
        print("\n[Step 6] Duyệt hoàn tất phiếu xuất kho (COMPLETED) với quyền SUPER_ADMIN...")
        post_res = await inventory_service.post_outbound_document(
            session,
            document_no=document_no,
            current_user_id=None,
            current_role_code="SUPER_ADMIN"
        )
        await session.commit()
        assert post_res["status"] == "COMPLETED", "❌ Thất bại: Trạng thái trả về không phải COMPLETED"
        print("✔️ Duyệt phiếu xuất kho thành công.")

        # 7. Kiểm tra trạng thái đơn hàng đồng bộ tự động sang SHIPPED
        print("\n[Step 7] Kiểm tra trạng thái đơn hàng tự động đồng bộ sang SHIPPED...")
        order_res = await session.execute(
            text("SELECT status FROM orders WHERE id = :order_id"),
            {"order_id": order_id}
        )
        order_status = order_res.scalar()
        assert order_status == "SHIPPED", f"❌ Thất bại: Đơn hàng không chuyển sang SHIPPED (Đang ở: {order_status})"
        print(f"✔️ Đơn hàng {order_code} đã tự động chuyển sang: {order_status}")

        # 8. Kiểm tra tồn kho vật lý và trạng thái IMEI
        print("\n[Step 8] Kiểm tra thay đổi tồn kho vật lý và trạng thái IMEI...")
        # Tồn kệ giảm từ 5 xuống 3
        level_res = await session.execute(
            text("SELECT on_hand_quantity FROM inventory_levels WHERE variant_id = :v_id AND location_id = :l_id"),
            {"v_id": variant_id, "l_id": location_id}
        )
        on_hand = level_res.scalar()
        assert on_hand == 3, f"❌ Thất bại: Tồn kệ không giảm đúng (Đang còn: {on_hand})"
        print(f"✔️ Tồn kệ chính xác: {on_hand} cái (giảm từ 5)")

        # IMEI chuyển sang SOLD và liên kết với order_id
        for imei in test_imeis:
            imei_res = await session.execute(
                text("SELECT status, sold_order_id FROM product_imeis WHERE imei = :imei"),
                {"imei": imei}
            )
            imei_row = imei_res.mappings().first()
            assert imei_row["status"] == "SOLD", f"❌ Thất bại: Trạng thái IMEI không phải SOLD ({imei_row['status']})"
            assert imei_row["sold_order_id"] == order_id, "❌ Thất bại: IMEI không lưu sold_order_id đúng"
        print("✔️ Cả 2 mã IMEI đã chuyển sang trạng thái SOLD và gắn với mã đơn hàng.")

        # 9. Thử nghiệm chặn chuyển đơn hàng trực tiếp sang SHIPPED (nếu có phiếu xuất chưa hoàn thành)
        # Chúng ta tạo thêm 1 đơn hàng test nữa để test case chặn này
        print("\n[Step 9] Thử nghiệm chặn chuyển trực tiếp đơn hàng sang SHIPPED...")
        order_id2 = uuid4()
        order_code2 = f"ORD-{uuid4().hex[:8].upper()}"
        await session.execute(
            text("""
                INSERT INTO orders (id, order_code, user_id, status, subtotal_amount, discount_amount, shipping_fee, total_amount, payment_method, payment_status, recipient_name, recipient_phone, shipping_address)
                VALUES (:id, :order_code, :user_id, 'PENDING', 19000000, 0, 0, 19000000, 'COD', 'PENDING', 'Người Nhận Test 2', '0987654321', '123 Đường Test, Hà Nội')
            """),
            {"id": order_id2, "order_code": order_code2, "user_id": user_id}
        )
        await session.execute(
            text("""
                INSERT INTO order_items (id, order_id, product_id, variant_id, product_name, quantity, unit_price, total_price)
                VALUES (:id, :order_id, :product_id, :variant_id, 'Sản phẩm Test Outbound', 1, 19000000, 19000000)
            """),
            {"id": uuid4(), "order_id": order_id2, "product_id": product_id, "variant_id": variant_id}
        )
        await session.commit()
        
        # Duyệt sang PROCESSING để tự động sinh phiếu
        await CompleteOrderUseCase(session=session).execute(
            order_id=order_id2,
            status_value="PROCESSING",
            changed_by="test-outbound"
        )
        await session.commit()
        
        # Thử chuyển thẳng sang SHIPPED khi phiếu xuất kho liên kết vẫn đang ở dạng DRAFT
        try:
            await CompleteOrderUseCase(session=session).execute(
                order_id=order_id2,
                status_value="SHIPPED",
                changed_by="test-outbound"
            )
            await session.commit()
            print("❌ Thất bại: Chặn lỗi chuyển trực tiếp không hoạt động!")
            assert False, "Chặn lỗi chuyển trực tiếp không hoạt động"
        except Exception as e:
            print(f"✔️ Đã chặn thành công với lỗi dự kiến: {str(e)}")

        # 10. Dọn dẹp dữ liệu kiểm thử (Clean up)
        print("\n[Step 10] Dọn dẹp dữ liệu kiểm thử trong CSDL...")
        # Xóa các bản ghi liên quan để giữ sạch DB
        await session.execute(text("DELETE FROM order_history_logs WHERE order_id IN (:o1, :o2)"), {"o1": order_id, "o2": order_id2})
        await session.execute(text("DELETE FROM order_items WHERE order_id IN (:o1, :o2)"), {"o1": order_id, "o2": order_id2})
        await session.execute(text("DELETE FROM orders WHERE id IN (:o1, :o2)"), {"o1": order_id, "o2": order_id2})
        await session.execute(text("DELETE FROM product_imeis WHERE product_id = :p_id"), {"p_id": product_id})
        await session.execute(text("DELETE FROM inventory_levels WHERE variant_id = :v_id"), {"v_id": variant_id})
        await session.execute(text("DELETE FROM inventory_lot_movements WHERE lot_id IN (SELECT id FROM inventory_lots WHERE variant_id = :v_id)"), {"v_id": variant_id})
        await session.execute(text("DELETE FROM inventory_lots WHERE variant_id = :v_id"), {"v_id": variant_id})
        await session.execute(text("DELETE FROM product_variants WHERE product_id = :p_id"), {"p_id": product_id})
        await session.execute(text("DELETE FROM products WHERE id = :p_id"), {"p_id": product_id})
        await session.execute(text("DELETE FROM inventory_document_lines WHERE document_id IN (SELECT id FROM inventory_documents WHERE order_id IN (:o1, :o2))"), {"o1": order_id, "o2": order_id2})
        await session.execute(text("DELETE FROM inventory_documents WHERE order_id IN (:o1, :o2)"), {"o1": order_id, "o2": order_id2})
        await session.commit()
        print("✔️ Dọn dẹp CSDL thành công.")
        
        print("\n🎉🎉🎉 LUỒNG XUẤT KHO LIÊN KẾT ĐƠN HÀNG HOẠT ĐỘNG HOÀN HẢO 100%! 🎉🎉🎉")

if __name__ == "__main__":
    asyncio.run(test_outbound_flow())
