from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def delete_content_comments(session: AsyncSession, content_id: UUID) -> None:
    await session.execute(text("DELETE FROM content_comments WHERE content_id = :content_id"), {"content_id": content_id})


async def insert_admin_content_comment(
    session: AsyncSession,
    *,
    id: UUID,
    content_id: UUID,
    user_name: str,
    body: str,
    parent_id: UUID | None,
    is_hidden: bool,
    created_by: UUID,
    updated_by: UUID,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO content_comments (
                id, content_id, user_name, body, parent_id, is_hidden, created_by, updated_by
            )
            VALUES (
                :id, :content_id, :user_name, :body, :parent_id, :is_hidden, :created_by, :updated_by
            )
            """
        ),
        {
            "id": id,
            "content_id": content_id,
            "user_name": user_name,
            "body": body,
            "parent_id": parent_id,
            "is_hidden": is_hidden,
            "created_by": created_by,
            "updated_by": updated_by,
        },
    )


async def get_video_comment_parent(session: AsyncSession, *, parent_id: UUID, video_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, parent_id, user_name
                FROM content_comments
                WHERE id = :parent_id
                  AND content_id = :video_id
                  AND deleted_at IS NULL
                """
            ),
            {"parent_id": parent_id, "video_id": video_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_video_comment(
    session: AsyncSession,
    *,
    comment_id: UUID,
    video_id: UUID,
    user_id: UUID,
    user_name: str,
    body: str,
    parent_id: UUID | None,
    reply_to_user_name: str | None,
    is_hidden: bool,
    moderation_reason: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO content_comments (
                id, content_id, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, moderation_reason, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :id, :video_id, :user_id, :user_name, :body, :parent_id, :reply_to_user_name,
                :is_hidden, :moderation_reason, :user_id, :user_id, NOW(), NOW()
            )
            """
        ),
        {
            "id": comment_id,
            "video_id": video_id,
            "user_id": user_id,
            "user_name": user_name,
            "body": body,
            "parent_id": parent_id,
            "reply_to_user_name": reply_to_user_name,
            "is_hidden": is_hidden,
            "moderation_reason": moderation_reason,
        },
    )


async def retract_video_comment(session: AsyncSession, *, video_id: UUID, comment_id: UUID, user_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            UPDATE content_comments
            SET is_retracted = TRUE,
                retracted_at = NOW(),
                updated_by = :user_id,
                updated_at = NOW()
            WHERE id = :comment_id
              AND content_id = :video_id
              AND user_id = :user_id
              AND deleted_at IS NULL
              AND is_retracted = FALSE
            """
        ),
        {"comment_id": comment_id, "video_id": video_id, "user_id": user_id},
    )
    return int(result.rowcount or 0)


async def list_product_image_comments(session: AsyncSession, product_id: UUID, interaction_type: str = "IMAGE_COMMENT") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                user_name AS "userName",
                CASE WHEN is_retracted THEN 'Bình luận này đã bị thu hồi' ELSE body END AS content,
                parent_id::text AS "parentId",
                reply_to_user_name AS "replyToUserName",
                is_hidden AS "isHidden",
                is_retracted AS "isRetracted",
                created_at AS "createdAt"
            FROM product_image_comments
            WHERE product_id = :product_id
              AND is_hidden = FALSE
              AND interaction_type = :interaction_type
            ORDER BY created_at ASC
            """
        ),
        {"product_id": product_id, "interaction_type": interaction_type},
    )
    return [dict(row._mapping) for row in result]


async def get_product_image_comment_parent(session: AsyncSession, *, parent_id: UUID, product_id: UUID, interaction_type: str = "IMAGE_COMMENT") -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, parent_id, user_name
                FROM product_image_comments
                WHERE id = :parent_id
                  AND product_id = :product_id
                  AND is_hidden = FALSE
                  AND interaction_type = :interaction_type
                """
            ),
            {"parent_id": parent_id, "product_id": product_id, "interaction_type": interaction_type},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_product_image_comment(
    session: AsyncSession,
    *,
    comment_id: UUID,
    product_id: UUID,
    image_url: str | None,
    user_id: UUID,
    user_name: str,
    body: str,
    parent_id: UUID | None,
    reply_to_user_name: str | None,
    is_hidden: bool,
    moderation_reason: str | None,
    interaction_type: str = "IMAGE_COMMENT",
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_image_comments (
                id, product_id, image_url, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, is_retracted, moderation_reason, interaction_type, created_at, updated_at
            )
            VALUES (
                :id, :product_id, :image_url, :user_id, :user_name, :body, :parent_id, :reply_to_user_name,
                :is_hidden, FALSE, :moderation_reason, :interaction_type, NOW(), NOW()
            )
            """
        ),
        {
            "id": comment_id,
            "product_id": product_id,
            "image_url": image_url,
            "user_id": user_id,
            "user_name": user_name,
            "body": body,
            "parent_id": parent_id,
            "reply_to_user_name": reply_to_user_name,
            "is_hidden": is_hidden,
            "moderation_reason": moderation_reason,
            "interaction_type": interaction_type,
        },
    )


async def retract_product_image_comment(session: AsyncSession, *, product_id: UUID, comment_id: UUID, user_id: UUID, interaction_type: str = "IMAGE_COMMENT") -> int:
    result = await session.execute(
        text(
            """
            UPDATE product_image_comments
            SET is_retracted = TRUE, body = '', updated_at = NOW()
            WHERE id = :comment_id
              AND product_id = :product_id
              AND user_id = :user_id
              AND interaction_type = :interaction_type
            """
        ),
        {"comment_id": comment_id, "product_id": product_id, "user_id": user_id, "interaction_type": interaction_type},
    )
    return int(result.rowcount or 0)


async def get_video_comment_for_reply(session: AsyncSession, *, comment_id: UUID, video_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT cc.id, cc.parent_id, cc.user_name, v.id AS video_id
                FROM content_comments cc
                JOIN videos v ON v.id = cc.content_id
                WHERE cc.id = :comment_id
                  AND cc.content_id = :video_id
                  AND v.content_type = 'VIDEO'
                  AND cc.deleted_at IS NULL
                """
            ),
            {"comment_id": comment_id, "video_id": video_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_admin_video_comment_reply(
    session: AsyncSession,
    *,
    id: UUID,
    video_id: UUID,
    actor_id: UUID,
    user_name: str,
    body: str,
    parent_id: UUID,
    reply_to_user_name: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO content_comments (
                id, content_id, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :id, :video_id, :actor_id, :user_name, :body, :parent_id, :reply_to_user_name,
                FALSE, :actor_id, :actor_id, NOW(), NOW()
            )
            """
        ),
        {
            "id": id,
            "video_id": video_id,
            "actor_id": actor_id,
            "user_name": user_name,
            "body": body,
            "parent_id": parent_id,
            "reply_to_user_name": reply_to_user_name,
        },
    )


async def update_video_comment_visibility_in_db(
    session: AsyncSession,
    *,
    comment_id: UUID,
    video_id: UUID,
    is_hidden: bool,
    actor_id: UUID,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE content_comments
            SET is_hidden = :is_hidden, updated_by = :actor_id, updated_at = NOW()
            WHERE id = :comment_id
              AND content_id = :video_id
              AND deleted_at IS NULL
            """
        ),
        {"comment_id": comment_id, "video_id": video_id, "is_hidden": is_hidden, "actor_id": actor_id},
    )
    return int(result.rowcount or 0)


async def list_admin_image_comments(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pic.id::text,
                pic.product_id::text AS "productId",
                p.name AS "productName",
                pic.image_url AS "imageUrl",
                pic.user_name AS "userName",
                CASE WHEN pic.is_retracted THEN 'Bình luận này đã bị thu hồi' ELSE pic.body END AS content,
                pic.parent_id::text AS "parentId",
                pic.reply_to_user_name AS "replyToUserName",
                pic.is_hidden AS "isHidden",
                pic.is_retracted AS "isRetracted",
                pic.moderation_reason AS "moderationReason",
                pic.interaction_type AS "interactionType",
                pic.created_at AS "createdAt"
            FROM product_image_comments pic
            JOIN products p ON p.id = pic.product_id
            ORDER BY pic.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def get_image_comment_for_reply(session: AsyncSession, comment_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, product_id, image_url, parent_id, user_name, interaction_type
                FROM product_image_comments
                WHERE id = :comment_id
                """
            ),
            {"comment_id": comment_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_admin_image_comment_reply(
    session: AsyncSession,
    *,
    id: UUID,
    product_id: UUID,
    image_url: str | None,
    actor_id: UUID,
    user_name: str,
    body: str,
    parent_id: UUID,
    reply_to_user_name: str,
    interaction_type: str = "IMAGE_COMMENT",
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_image_comments (
                id, product_id, image_url, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, is_retracted, interaction_type, created_at, updated_at
            )
            VALUES (
                :id, :product_id, :image_url, :actor_id, :user_name, :body, :parent_id, :reply_to_user_name,
                FALSE, FALSE, :interaction_type, NOW(), NOW()
            )
            """
        ),
        {
            "id": id,
            "product_id": product_id,
            "image_url": image_url,
            "actor_id": actor_id,
            "user_name": user_name,
            "body": body,
            "parent_id": parent_id,
            "reply_to_user_name": reply_to_user_name,
            "interaction_type": interaction_type,
        },
    )


async def update_image_comment_visibility_in_db(
    session: AsyncSession,
    *,
    comment_id: UUID,
    is_hidden: bool,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE product_image_comments
            SET is_hidden = :is_hidden, updated_at = NOW()
            WHERE id = :comment_id
            """
        ),
        {"comment_id": comment_id, "is_hidden": is_hidden},
    )
    return int(result.rowcount or 0)
