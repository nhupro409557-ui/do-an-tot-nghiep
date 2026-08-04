import argparse
import asyncio
from uuid import UUID

from sqlalchemy import text

from app.application.after_sales.fulfillment import ensure_after_sales_order
from app.infrastructure.database.repositories import after_sales_repo
from app.infrastructure.database.session import AsyncSessionFactory


async def run(*, apply: bool) -> None:
    async with AsyncSessionFactory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT wr.id
                    FROM warranty_requests wr
                    WHERE wr.resolution_type = 'REPLACEMENT'
                      AND wr.status = 'COMPLETED'
                      AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.warranty_request_id = wr.id)
                    ORDER BY wr.created_at
                    """
                )
            )
        ).scalars().all()
        print(f"Tìm thấy {len(rows)} hồ sơ bảo hành đổi máy cũ chưa có đơn giao hậu mãi.")
        for request_id in rows:
            request = await after_sales_repo.get_request_for_update(
                session, kind="WARRANTY", request_id=UUID(str(request_id))
            )
            items = await after_sales_repo.get_request_items(
                session, kind="WARRANTY", request_id=UUID(str(request_id))
            )
            print(f"- {request['request_code']}: {len(items)} dòng thiết bị")
            if not apply:
                continue
            outbound_id = await session.scalar(
                text(
                    """
                    SELECT id FROM inventory_documents
                    WHERE warranty_request_id = :request_id
                      AND document_type = 'OUTBOUND' AND status = 'COMPLETED'
                    LIMIT 1 FOR UPDATE
                    """
                ),
                {"request_id": request_id},
            )
            if not outbound_id:
                raise RuntimeError(f"{request['request_code']}: thiếu phiếu xuất lịch sử, dừng để tránh trừ tồn lần hai.")
            order_id = await ensure_after_sales_order(
                session, kind="WARRANTY", request=request, items=items
            )
            await session.execute(
                text(
                    """
                    UPDATE inventory_documents
                    SET order_id = :order_id,
                        metadata = COALESCE(metadata, '{}'::jsonb)
                            || jsonb_build_object('historicalBackfill', TRUE)
                    WHERE id = :document_id
                    """
                ),
                {"order_id": order_id, "document_id": outbound_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE product_imeis pi
                    SET sold_order_id = :order_id, updated_at = NOW()
                    WHERE pi.imei IN (
                        SELECT jsonb_array_elements_text(COALESCE(wi.replacement_imeis, '[]'::jsonb))
                        FROM warranty_request_items wi WHERE wi.request_id = :request_id
                    )
                    """
                ),
                {"order_id": order_id, "request_id": request_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE product_serial_numbers psn
                    SET service_payload = COALESCE(service_payload, '{}'::jsonb)
                        || jsonb_build_object('soldOrderId', CAST(CAST(:order_id AS UUID) AS TEXT)),
                        updated_at = NOW()
                    WHERE psn.serial_number IN (
                        SELECT jsonb_array_elements_text(COALESCE(wi.replacement_serial_numbers, '[]'::jsonb))
                        FROM warranty_request_items wi WHERE wi.request_id = :request_id
                    )
                    """
                ),
                {"order_id": order_id, "request_id": request_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE orders o
                    SET status = 'COMPLETED', payment_status = 'PAID',
                        shipped_at = COALESCE(o.shipped_at, wr.updated_at),
                        completed_at = COALESCE(o.completed_at, wr.updated_at), updated_at = NOW()
                    FROM warranty_requests wr
                    WHERE o.id = :order_id AND wr.id = :request_id
                    """
                ),
                {"order_id": order_id, "request_id": request_id},
            )
        if apply:
            await session.commit()
            print("Đã backfill đơn giao hậu mãi và liên kết phiếu xuất lịch sử.")
        else:
            await session.rollback()
            print("Chỉ xem trước; chưa thay đổi dữ liệu. Dùng --apply để thực hiện.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))
