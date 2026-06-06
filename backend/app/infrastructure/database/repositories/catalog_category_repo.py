from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_active_root_categories(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                c.id::text,
                c.parent_id::text AS "parentId",
                c.code,
                c.slug,
                c.name,
                c.icon,
                c.icon_url AS "iconUrl",
                c.banner_url AS "bannerUrl",
                COALESCE(c.spec_fields, '[]'::jsonb) AS "specFields",
                c.filter_config AS "filterConfig",
                c.sort_order AS "order",
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', child.id::text,
                            'code', child.code,
                            'slug', child.slug,
                            'name', child.name,
                            'sortOrder', child.sort_order
                        )
                    ) FILTER (WHERE child.id IS NOT NULL AND COALESCE(child.is_deleted, FALSE) = FALSE AND child.status = 'ACTIVE'),
                    '[]'::jsonb
                ) AS children
            FROM categories c
            LEFT JOIN categories child ON child.parent_id = c.id
            WHERE c.parent_id IS NULL
              AND c.is_active = TRUE
              AND c.status = 'ACTIVE'
              AND COALESCE(c.is_deleted, FALSE) = FALSE
            GROUP BY c.id
            ORDER BY c.sort_order, c.name
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def get_category_redirect(session: AsyncSession, old_slug: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT source_path AS "sourcePath", target_path AS "targetPath", status_code AS "statusCode"
                FROM url_redirects
                WHERE source_path = :source_path
                  AND entity_type = 'category'
                """
            ),
            {"source_path": f"/category/{old_slug}"},
        )
    ).mappings().first()
    return dict(row) if row else None
