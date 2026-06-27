import sys
sys.path.append("c:\\Users\\Huynh Nhu\\Downloads\\Project\\backend")

import asyncio
from app.infrastructure.database.session import AsyncSessionFactory
from app.application.services import inventory_service
from sqlalchemy import text
from uuid import UUID

async def test_putaway_suggestions():
    print("--- CHẠY THỬ NGHIỆM GỢI Ý XẾP HÀNG TỰ ĐỘNG ---")
    async with AsyncSessionFactory() as session:
        # 1. Tìm sản phẩm đang hoạt động
        row = (
            await session.execute(
                text("SELECT id, name FROM products LIMIT 1")
            )
        ).mappings().first()
        
        if not row:
            print("❌ Không tìm thấy sản phẩm hoạt động nào.")
            return
            
        product_id = row["id"]
        product_name = row["name"]
        print(f"Sản phẩm thử nghiệm: {product_name} ({product_id})")

        # 2. Gọi gợi ý cho lý do Nhập mua (NK_MUA) với số lượng 5
        print("\n--- Gợi ý cho Nhập Mua (NK_MUA), số lượng 5 ---")
        suggestions_mua = await inventory_service.list_inventory_putaway_suggestions(
            session,
            product_id=product_id,
            quantity=5,
            reason_code="NK_MUA"
        )
        for idx, s in enumerate(suggestions_mua, 1):
            print(f"{idx}. Kệ: {s['locationCode']} ({s['locationName']})")
            print(f"   Độ ưu tiên: {s['priority']} (1: SAME_SKU, 2: EMPTY, 3: MIXED_SKU)")
            print(f"   Thể tích trống: {s['availableVolumeCm3']} cm³")
            print(f"   Tỷ lệ đầy hiện tại: {s['fillRatio'] * 100:.2f}%" if s['fillRatio'] else "   Tỷ lệ đầy hiện tại: N/A")
            print(f"   Tỷ lệ đầy sau khi xếp: {s['fillRatioAfterImport'] * 100:.2f}%" if s['fillRatioAfterImport'] else "   Tỷ lệ đầy sau khi xếp: N/A")
            print(f"   Lý do gợi ý: {s['matchReason']}")
            print("-" * 30)

        # 3. Gọi gợi ý cho lý do Khách hàng trả hàng (NK_TRA) với số lượng 2
        print("\n--- Gợi ý cho Nhập Khách Trả (NK_TRA), số lượng 2 ---")
        suggestions_tra = await inventory_service.list_inventory_putaway_suggestions(
            session,
            product_id=product_id,
            quantity=2,
            reason_code="NK_TRA"
        )
        for idx, s in enumerate(suggestions_tra, 1):
            print(f"{idx}. Kệ: {s['locationCode']} ({s['locationName']})")
            print(f"   Độ ưu tiên: {s['priority']}")
            print(f"   Lý do gợi ý: {s['matchReason']}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_putaway_suggestions())
