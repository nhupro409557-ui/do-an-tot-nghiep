import argparse
import asyncio

from sqlalchemy import text

from app.application.services.inventory.outbounds import create_outbound_document_from_order
from app.application.commerce.use_cases import CompleteOrderUseCase
from app.infrastructure.database.session import AsyncSessionFactory


async def run(*, apply: bool) -> None:
    async with AsyncSessionFactory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT o.id, o.order_code, o.payment_status,
                           EXISTS(
                               SELECT 1 FROM inventory_documents d
                               WHERE d.order_id = o.id AND d.document_type = 'OUTBOUND'
                                 AND d.status <> 'CANCELLED'
                           ) AS has_outbound
                    FROM orders o
                    WHERE o.status = 'PAID'
                    ORDER BY o.created_at
                    """
                )
            )
        ).mappings().all()
        missing = [row for row in rows if not row["has_outbound"]]
        print(f"Có {len(rows)} đơn trạng thái PAID; {len(missing)} đơn chưa có phiếu xuất hiệu lực.")
        for row in missing:
            action = "TẠO PHIẾU XUẤT NHÁP" if row["payment_status"] == "PAID" else "ĐỒNG BỘ ĐƠN SANG ĐÃ HOÀN TIỀN"
            print(f"- {row['order_code']} | payment={row['payment_status']} | {action}")
            if apply and row["payment_status"] == "PAID":
                await create_outbound_document_from_order(session, row["id"])
            elif apply and row["payment_status"] == "REFUNDED":
                await CompleteOrderUseCase(session=session).execute(
                    order_id=row["id"],
                    status_value="REFUNDED",
                    refund_payment=False,
                    changed_by="paid-order-reconciliation",
                    run_external_side_effects=False,
                )
        if apply:
            await session.commit()
            print("Đã tạo phiếu xuất còn thiếu và đồng bộ các đơn đã hoàn tiền.")
        else:
            await session.rollback()
            print("Chỉ xem trước; chưa thay đổi dữ liệu. Dùng --apply để tạo phiếu phù hợp.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))
