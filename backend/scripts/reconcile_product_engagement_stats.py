"""Recalculate product engagement counters from real source tables.

This removes legacy/demo values from products.rating, products.review_count and
products.favorite_count. Storefront APIs should read live aggregates, but these
denormalized columns are still used by some admin/reporting paths.
"""

import asyncio

from sqlalchemy import text

from app.infrastructure.database.session import AsyncSessionFactory


async def main() -> None:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            text(
                """
                WITH review_stats AS (
                    SELECT
                        product_id,
                        ROUND(AVG(rating) FILTER (WHERE status = 'PUBLISHED'), 2)::numeric(3, 2) AS rating,
                        COUNT(*) FILTER (WHERE status = 'PUBLISHED') AS review_count
                    FROM product_reviews
                    GROUP BY product_id
                ),
                favorite_stats AS (
                    SELECT product_id, COUNT(*) AS favorite_count
                    FROM user_favorites
                    WHERE is_active = TRUE
                    GROUP BY product_id
                )
                UPDATE products p
                SET rating = rs.rating,
                    review_count = COALESCE(rs.review_count, 0),
                    favorite_count = COALESCE(fs.favorite_count, 0),
                    updated_at = NOW()
                FROM products target
                LEFT JOIN review_stats rs ON rs.product_id = target.id
                LEFT JOIN favorite_stats fs ON fs.product_id = target.id
                WHERE p.id = target.id
                RETURNING p.id
                """
            )
        )
        changed_count = len(result.fetchall())
        await session.commit()
        print(f"Reconciled engagement stats for {changed_count} products.")


if __name__ == "__main__":
    asyncio.run(main())
