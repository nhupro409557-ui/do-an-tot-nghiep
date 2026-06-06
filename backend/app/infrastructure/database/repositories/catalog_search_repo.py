from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def execute_rankings_query(session: AsyncSession, sql: str, params: dict) -> list:
    result = await session.execute(text(sql), params)
    return result.all()


async def get_active_product_image_source(session: AsyncSession, product_id: UUID):
    result = await session.execute(
        text(
            """
            SELECT id::text, name, brand, category, image_url AS "imageUrl", images, colors, capacities, promotions
            FROM products
            WHERE id = :id AND status = 'ACTIVE' AND deleted_at IS NULL
            """
        ),
        {"id": product_id},
    )
    return result.first()


async def list_related_products_by_category(
    session: AsyncSession,
    *,
    product_id: UUID,
    category: str | None,
    limit: int,
) -> list:
    result = await session.execute(
        text(
            """
            SELECT id::text, name, brand, category, image_url AS "imageUrl", images,
                   price, sale_price AS "discountPrice", stock_quantity AS stock, status, rating
            FROM products
            WHERE category = :category AND id != :id AND status = 'ACTIVE' AND deleted_at IS NULL
            LIMIT :limit
            """
        ),
        {"category": category, "id": product_id, "limit": limit},
    )
    return list(result)


async def insert_product_search_event(
    session: AsyncSession,
    *,
    query: str,
    normalized_query: str,
    product_id: UUID | None,
    session_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
    result_count: int,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_search_events
                (query, normalized_query, product_id, session_id, ip_address, user_agent, result_count)
            VALUES
                (:query, :normalized_query, :product_id, :session_id, :ip_address, :user_agent, :result_count)
            """
        ),
        {
            "query": query,
            "normalized_query": normalized_query,
            "product_id": product_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "result_count": result_count,
        },
    )
