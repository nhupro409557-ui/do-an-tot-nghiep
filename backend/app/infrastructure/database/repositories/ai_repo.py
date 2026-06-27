from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AIContextLog


async def list_active_products_for_ai(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT p.id::text, p.slug, p.name, p.brand, p.price, p.sale_price AS "salePrice",
                   p.image_url AS "imageUrl", p.description, p.specifications,
                   c.name AS "categoryName", c.slug AS "categorySlug",
                   COALESCE(review_stats.rating, 0) AS rating,
                   COALESCE(review_stats.review_count, 0) AS "reviewCount",
                   COALESCE(favorite_counts.favorite_count, 0) AS "favoriteCount"
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id, ROUND(AVG(rating), 2)::numeric(3, 2) AS rating, COUNT(*) AS review_count
                FROM product_reviews
                WHERE status = 'PUBLISHED'
                GROUP BY product_id
            ) review_stats ON review_stats.product_id = p.id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS favorite_count
                FROM user_favorites
                WHERE is_active = TRUE
                GROUP BY product_id
            ) favorite_counts ON favorite_counts.product_id = p.id
            WHERE p.status = 'ACTIVE'
            ORDER BY p.is_featured DESC, review_stats.rating DESC NULLS LAST, p.created_at DESC
            LIMIT 200
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def get_user_order_for_ai(session: AsyncSession, *, user_id: str, order_code: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT o.order_code AS "orderCode", o.status, o.payment_status AS "paymentStatus",
                       o.total_amount AS "totalAmount", o.loyalty_points_earned AS "pointsEarned",
                       o.loyalty_points_used AS "pointsUsed", o.created_at AS "createdAt",
                       COALESCE(jsonb_agg(jsonb_build_object(
                         'productName', oi.product_name,
                         'quantity', oi.quantity,
                         'totalPrice', oi.total_price
                       )) FILTER (WHERE oi.id IS NOT NULL), '[]'::jsonb) AS items
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.user_id = :user_id AND upper(o.order_code) = :order_code
                GROUP BY o.id
                LIMIT 1
                """
            ),
            {"user_id": user_id, "order_code": order_code},
        )
    ).first()
    return dict(row._mapping) if row else None


async def add_ai_context_log(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    refusal_reason: str | None,
    dynamic_context: dict,
    model_provider: str | None,
    model_name: str | None,
) -> None:
    log = AIContextLog(
        id=uuid4(),
        user_id=user_id,
        conversation_id=conversation_id,
        request_scope="SALES_ASSISTANT",
        user_message=user_message,
        assistant_response=assistant_response,
        refusal_reason=refusal_reason,
        dynamic_context=dynamic_context,
        model_provider=model_provider,
        model_name=model_name,
    )
    session.add(log)
