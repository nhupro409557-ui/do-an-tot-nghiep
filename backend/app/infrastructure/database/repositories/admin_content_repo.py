import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def audit_admin_event(
    session: AsyncSession,
    *,
    actor_id: UUID,
    event_type: str,
    resource: str,
    metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:actor_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": event_type,
            "metadata": json.dumps(
                {"resource": resource, **(metadata or {})},
                ensure_ascii=False,
                default=str,
            ),
        },
    )


async def delete_content_product_relations(session: AsyncSession, content_id: UUID) -> None:
    await session.execute(text("DELETE FROM content_product_relations WHERE content_id = :content_id"), {"content_id": content_id})


async def insert_content_product_relation(session: AsyncSession, content_id: UUID, product_id: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO content_product_relations (content_id, product_id)
            VALUES (:content_id, :product_id)
            ON CONFLICT (content_id, product_id) DO NOTHING
            """
        ),
        {"content_id": content_id, "product_id": product_id},
    )


async def delete_content_category_relations(session: AsyncSession, content_id: UUID) -> None:
    await session.execute(text("DELETE FROM content_category_relations WHERE content_id = :content_id"), {"content_id": content_id})


async def insert_content_category_relation(session: AsyncSession, content_id: UUID, category_id: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO content_category_relations (content_id, category_id)
            VALUES (:content_id, :category_id)
            ON CONFLICT (content_id, category_id) DO NOTHING
            """
        ),
        {"content_id": content_id, "category_id": category_id},
    )


async def list_admin_content(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                v.id::text,
                v.title,
                v.description,
                v.content_type AS "contentType",
                v.video_source AS "videoSource",
                v.video_category AS "videoCategory",
                v.status,
                v.video_url AS "videoUrl",
                v.thumbnail_url AS "thumbnailUrl",
                v.banner_image_url AS "bannerImageUrl",
                v.content_body AS "contentBody",
                LEFT(COALESCE(v.content_body, ''), 320) AS "contentBodyPreview",
                v.cta_label AS "ctaLabel",
                v.cta_url AS "ctaUrl",
                COALESCE((SELECT COUNT(*) FROM video_likes vl WHERE vl.video_id = v.id), 0)::int AS "likeCount",
                v.view_count AS "viewCount",
                v.sort_order AS "sortOrder",
                v.scheduled_at AS "scheduledAt",
                v.published_at AS "publishedAt",
                v.is_active AS "isActive",
                v.created_by::text AS "createdBy",
                v.updated_by::text AS "updatedBy",
                v.deleted_at AS "deletedAt",
                v.version,
                v.created_at AS "createdAt",
                v.updated_at AS "updatedAt",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', p.id::text, 'name', p.name, 'brand', b.name, 'categoryId', p.category_id::text, 'imageUrl', p.image_url, 'price', p.sale_price))
                        FROM content_product_relations cpr
                        JOIN products p ON p.id = cpr.product_id
                        LEFT JOIN brands b ON b.id = p.brand_id
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS products,
                COALESCE(
                    (
                        SELECT json_agg(cpr.product_id::text)
                        FROM content_product_relations cpr
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "productIds",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', c.id::text, 'name', c.name))
                        FROM content_category_relations ccr
                        JOIN categories c ON c.id = ccr.category_id
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS categories,
                COALESCE(
                    (
                        SELECT json_agg(ccr.category_id::text)
                        FROM content_category_relations ccr
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "categoryIds",
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', cc.id::text,
                                'userName', cc.user_name,
                                'content', cc.body,
                                'parentId', cc.parent_id::text,
                                'replyToUserName', cc.reply_to_user_name,
                                'isHidden', cc.is_hidden,
                                'moderationReason', cc.moderation_reason,
                                'createdAt', cc.created_at
                            )
                            ORDER BY cc.created_at ASC
                        )
                        FROM content_comments cc
                        WHERE cc.content_id = v.id
                          AND cc.deleted_at IS NULL
                    ),
                    '[]'::json
                ) AS comments,
                (
                    SELECT COUNT(*)
                    FROM content_comments cc
                    WHERE cc.content_id = v.id
                      AND cc.deleted_at IS NULL
                ) AS "commentCount"
            FROM videos v
            WHERE v.deleted_at IS NULL
            ORDER BY v.sort_order ASC, COALESCE(v.scheduled_at, v.created_at) DESC, v.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def insert_content_record(session: AsyncSession, *, id: UUID, created_by: UUID, updated_by: UUID, data: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO videos (
                id, title, description, content_type, video_source, video_category, status, video_url, thumbnail_url, banner_image_url,
                content_body, cta_label, cta_url,
                like_count, view_count, sort_order, scheduled_at, published_at,
                is_active, version, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :id, :title, :description, :content_type, :video_source, :video_category, :status, :video_url, :thumbnail_url, :banner_image_url,
                :content_body, :cta_label, :cta_url,
                0, 0, :sort_order, :scheduled_at, :published_at,
                :is_active, 1, :created_by, :updated_by, NOW(), NOW()
            )
            """
        ),
        {"id": id, "created_by": created_by, "updated_by": updated_by, **data},
    )


async def update_content_record(session: AsyncSession, *, id: UUID, updated_by: UUID, expected_version: int, data: dict) -> int:
    result = await session.execute(
        text(
            """
            UPDATE videos
            SET
                title = :title,
                description = :description,
                content_type = :content_type,
                video_source = :video_source,
                video_category = :video_category,
                status = :status,
                video_url = :video_url,
                thumbnail_url = :thumbnail_url,
                banner_image_url = :banner_image_url,
                content_body = :content_body,
                cta_label = :cta_label,
                cta_url = :cta_url,
                sort_order = :sort_order,
                scheduled_at = :scheduled_at,
                published_at = :published_at,
                is_active = :is_active,
                version = version + 1,
                updated_by = :updated_by,
                updated_at = NOW()
            WHERE id = :id
              AND deleted_at IS NULL
              AND version = :expected_version
            """
        ),
        {"id": id, "updated_by": updated_by, "expected_version": expected_version, **data},
    )
    return int(result.rowcount or 0)


async def check_content_exists(session: AsyncSession, content_id: UUID) -> bool:
    return bool(await session.scalar(text("SELECT COUNT(*) FROM videos WHERE id = :id AND deleted_at IS NULL"), {"id": content_id}))


async def soft_delete_content_record(session: AsyncSession, *, id: UUID, actor_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            UPDATE videos
            SET deleted_at = NOW(), is_active = FALSE, status = 'ARCHIVED', version = version + 1, updated_by = :actor_id, updated_at = NOW()
            WHERE id = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": id, "actor_id": actor_id},
    )
    return int(result.rowcount or 0)


async def soft_delete_admin_video_record(session: AsyncSession, *, id: UUID, actor_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            UPDATE videos
            SET deleted_at = NOW(),
                is_active = FALSE,
                status = 'ARCHIVED',
                version = version + 1,
                updated_by = :actor_id,
                updated_at = NOW()
            WHERE id = :id
              AND content_type = 'VIDEO'
              AND deleted_at IS NULL
            """
        ),
        {"id": id, "actor_id": actor_id},
    )
    return int(result.rowcount or 0)
