from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_purchase_orders(session: AsyncSession, search: str = "", status: str = "") -> list[dict]:
    rows = (await session.execute(
        text("""
            SELECT po.id, po.code, po.supplier_id AS "supplierId", s.name AS "supplierName",
                   po.status, po.expected_date AS "expectedDate", po.note,
                   po.discount_amount AS "discountAmount", po.shipping_fee AS "shippingFee",
                   po.created_by AS "createdBy", po.approved_by AS "approvedBy",
                   po.approved_at AS "approvedAt", po.created_at AS "createdAt",
                   COALESCE(SUM(pol.ordered_quantity), 0)::int AS "orderedQuantity",
                   COALESCE(SUM(pol.received_quantity), 0)::int AS "receivedQuantity",
                   COALESCE(SUM(pol.ordered_quantity * pol.unit_cost), 0) AS subtotal
            FROM purchase_orders po
            JOIN suppliers s ON s.id = po.supplier_id
            LEFT JOIN purchase_order_lines pol ON pol.purchase_order_id = po.id
            WHERE (:search = '' OR po.code ILIKE :search_like OR s.name ILIKE :search_like)
              AND (:status = '' OR po.status = :status)
            GROUP BY po.id, s.name
            ORDER BY po.created_at DESC
        """), {"search": search, "search_like": f"%{search}%", "status": status})).mappings().all()
    return [dict(row) for row in rows]


async def get_purchase_order(session: AsyncSession, order_id: UUID, *, for_update: bool = False) -> dict | None:
    lock = " FOR UPDATE OF po" if for_update else ""
    header = (await session.execute(text(f"""
        SELECT po.id, po.code, po.supplier_id AS "supplierId", s.name AS "supplierName",
               po.status, po.expected_date AS "expectedDate", po.note,
               po.discount_amount AS "discountAmount", po.shipping_fee AS "shippingFee",
               po.created_by AS "createdBy", po.approved_by AS "approvedBy",
               po.approved_at AS "approvedAt", po.created_at AS "createdAt"
        FROM purchase_orders po JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.id = :id{lock}
    """), {"id": order_id})).mappings().first()
    if not header:
        return None
    lines = (await session.execute(text("""
        SELECT pol.id, pol.product_id AS "productId", pol.variant_id AS "variantId",
               p.name AS "productName", p.sku AS "productSku", pv.sku AS "variantSku",
               pol.ordered_quantity AS quantity, pol.received_quantity AS "receivedQuantity",
               (pol.ordered_quantity - pol.received_quantity) AS "remainingQuantity",
               pol.unit_cost AS "unitCost", pol.note
        FROM purchase_order_lines pol
        JOIN products p ON p.id = pol.product_id
        LEFT JOIN product_variants pv ON pv.id = pol.variant_id
        WHERE pol.purchase_order_id = :id ORDER BY pol.created_at, pol.id
    """), {"id": order_id})).mappings().all()
    result = dict(header)
    result["lines"] = [dict(row) for row in lines]
    return result


async def insert_purchase_order(session: AsyncSession, order: dict, lines: list[dict]) -> None:
    await session.execute(text("""
        INSERT INTO purchase_orders (
            id, code, supplier_id, expected_date, note, discount_amount, shipping_fee, created_by
        ) VALUES (
            :id, :code, :supplier_id, :expected_date, :note, :discount_amount, :shipping_fee, :created_by
        )
    """), order)
    for line in lines:
        await session.execute(text("""
            INSERT INTO purchase_order_lines (
                id, purchase_order_id, product_id, variant_id, ordered_quantity, unit_cost, note
            ) VALUES (
                :id, :purchase_order_id, :product_id, :variant_id, :quantity, :unit_cost, :note
            )
        """), line)


async def replace_purchase_order(session: AsyncSession, order_id: UUID, order: dict, lines: list[dict]) -> None:
    await session.execute(text("""
        UPDATE purchase_orders
        SET supplier_id = :supplier_id, expected_date = :expected_date, note = :note,
            discount_amount = :discount_amount, shipping_fee = :shipping_fee, updated_at = NOW()
        WHERE id = :id
    """), {"id": order_id, **order})
    await session.execute(text("DELETE FROM purchase_order_lines WHERE purchase_order_id = :id"), {"id": order_id})
    for line in lines:
        await session.execute(text("""
            INSERT INTO purchase_order_lines (
                id, purchase_order_id, product_id, variant_id, ordered_quantity, unit_cost, note
            ) VALUES (:id, :purchase_order_id, :product_id, :variant_id, :quantity, :unit_cost, :note)
        """), line)


async def update_purchase_order_status(
    session: AsyncSession, order_id: UUID, status: str, actor_id: UUID | None, note: str | None = None
) -> None:
    await session.execute(text("""
        UPDATE purchase_orders
        SET status = CAST(:status AS VARCHAR),
            note = CASE WHEN CAST(:note AS VARCHAR) IS NULL THEN note ELSE CAST(:note AS VARCHAR) END,
            approved_by = CASE WHEN CAST(:status AS VARCHAR) = 'APPROVED' THEN CAST(:actor_id AS UUID) ELSE approved_by END,
            approved_at = CASE WHEN CAST(:status AS VARCHAR) = 'APPROVED' THEN NOW() ELSE approved_at END,
            updated_at = NOW()
        WHERE id = :id
    """), {"id": order_id, "status": status, "actor_id": actor_id, "note": note})


async def receive_purchase_order_lines(session: AsyncSession, order_id: UUID, receipts: list[dict]) -> str:
    for item in receipts:
        result = await session.execute(text("""
            UPDATE purchase_order_lines
            SET received_quantity = received_quantity + :quantity
            WHERE id = :line_id AND purchase_order_id = :order_id
              AND received_quantity + :quantity <= ordered_quantity
            RETURNING id
        """), {"line_id": item["lineId"], "order_id": order_id, "quantity": item["quantity"]})
        if result.scalar_one_or_none() is None:
            raise ValueError("Số lượng nhận vượt quá số lượng còn lại của đơn mua hàng.")
    remaining = int((await session.execute(text("""
        SELECT COALESCE(SUM(ordered_quantity - received_quantity), 0)
        FROM purchase_order_lines WHERE purchase_order_id = :id
    """), {"id": order_id})).scalar_one())
    next_status = "COMPLETED" if remaining == 0 else "PARTIALLY_RECEIVED"
    await session.execute(text("UPDATE purchase_orders SET status = :status, updated_at = NOW() WHERE id = :id"), {"id": order_id, "status": next_status})
    return next_status


async def reverse_purchase_order_lines(session: AsyncSession, order_id: UUID, receipts: list[dict]) -> str:
    for item in receipts:
        result = await session.execute(text("""
            UPDATE purchase_order_lines
            SET received_quantity = received_quantity - :quantity
            WHERE id = :line_id AND purchase_order_id = :order_id
              AND received_quantity >= :quantity
            RETURNING id
        """), {"line_id": item["lineId"], "order_id": order_id, "quantity": item["quantity"]})
        if result.scalar_one_or_none() is None:
            raise ValueError("Số lượng đã nhận trên đơn mua không đủ để đảo phiếu.")
    received = int((await session.execute(text("""
        SELECT COALESCE(SUM(received_quantity), 0)
        FROM purchase_order_lines WHERE purchase_order_id = :id
    """), {"id": order_id})).scalar_one())
    next_status = "APPROVED" if received == 0 else "PARTIALLY_RECEIVED"
    await session.execute(text("UPDATE purchase_orders SET status = :status, updated_at = NOW() WHERE id = :id"), {"id": order_id, "status": next_status})
    return next_status
