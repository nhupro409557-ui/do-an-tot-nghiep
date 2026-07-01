"""Category repository helpers split by subdomain."""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def enqueue_sitemap_refresh(session: AsyncSession, entity_type: str, entity_id: UUID | None, reason: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO sitemap_refresh_events (entity_type, entity_id, reason)
            VALUES (:entity_type, :entity_id, :reason)
            """
        ),
        {"entity_type": entity_type, "entity_id": entity_id, "reason": reason},
    )


async def audit_product_event(
    session: AsyncSession,
    product_id: UUID,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_audit_logs (product_id, actor_id, action, old_value, new_value)
            VALUES (:product_id, :actor_id, :action, CAST(:old_value AS jsonb), CAST(:new_value AS jsonb))
            """
        ),
        {
            "product_id": product_id,
            "actor_id": actor_id,
            "action": action,
            "old_value": json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
            "new_value": json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
        },
    )


async def audit_category_event(
    session: AsyncSession,
    category_id: UUID,
    action_type: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO category_audit_logs (category_id, actor_id, action_type, old_value, new_value)
            VALUES (:category_id, :actor_id, :action_type, CAST(:old_value AS jsonb), CAST(:new_value AS jsonb))
            """
        ),
        {
            "category_id": category_id,
            "actor_id": actor_id,
            "action_type": action_type,
            "old_value": json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
            "new_value": json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
        },
    )


async def category_redirect_loop_exists(session: AsyncSession, *, source_path: str, target_path: str) -> bool:
    return bool(
        (
            await session.execute(
                text(
                    """
                    WITH RECURSIVE chain AS (
                        SELECT source_path, target_path, ARRAY[source_path::text] AS visited
                        FROM url_redirects
                        WHERE source_path = :target_path
                          AND entity_type = 'category'
                        UNION ALL
                        SELECT r.source_path, r.target_path, chain.visited || r.source_path::text
                        FROM url_redirects r
                        JOIN chain ON r.source_path = chain.target_path
                        WHERE r.entity_type = 'category'
                          AND NOT r.source_path = ANY(chain.visited)
                          AND array_length(chain.visited, 1) < 20
                    )
                    SELECT 1
                    FROM chain
                    WHERE target_path = :source_path
                    LIMIT 1
                    """
                ),
                {"source_path": source_path, "target_path": target_path},
            )
        ).first()
    )


async def update_upstream_category_redirects(session: AsyncSession, *, category_id: UUID, source_path: str, target_path: str) -> None:
    await session.execute(
        text(
            """
            UPDATE url_redirects
            SET target_path = :target_path,
                entity_id = :entity_id,
                updated_at = NOW()
            WHERE source_path IN (
                WITH RECURSIVE upstream AS (
                    SELECT source_path, target_path, ARRAY[source_path::text] AS visited
                    FROM url_redirects
                    WHERE target_path = :source_path
                      AND entity_type = 'category'
                    UNION ALL
                    SELECT r.source_path, r.target_path, upstream.visited || r.source_path::text
                    FROM url_redirects r
                    JOIN upstream ON r.target_path = upstream.source_path
                    WHERE r.entity_type = 'category'
                      AND NOT r.source_path = ANY(upstream.visited)
                      AND array_length(upstream.visited, 1) < 20
                )
                SELECT source_path
                FROM upstream
            )
              AND entity_type = 'category'
            """
        ),
        {"source_path": source_path, "target_path": target_path, "entity_id": category_id},
    )


async def delete_category_redirect_by_source(session: AsyncSession, target_path: str) -> None:
    await session.execute(
        text("DELETE FROM url_redirects WHERE source_path = :target_path AND entity_type = 'category'"),
        {"target_path": target_path},
    )


async def upsert_category_redirect(session: AsyncSession, *, category_id: UUID, source_path: str, target_path: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO url_redirects (source_path, target_path, status_code, entity_type, entity_id)
            VALUES (:source_path, :target_path, 301, 'category', :entity_id)
            ON CONFLICT (source_path)
            DO UPDATE SET target_path = EXCLUDED.target_path, entity_id = EXCLUDED.entity_id, updated_at = NOW()
            """
        ),
        {"source_path": source_path, "target_path": target_path, "entity_id": category_id},
    )
