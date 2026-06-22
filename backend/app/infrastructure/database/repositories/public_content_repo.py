from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_existing_review(session: AsyncSession, *, product_id: UUID, user_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    product_id::text AS "productId",
                    order_id::text AS "orderId",
                    user_name AS "userName",
                    rating,
                    comment,
                    media_urls AS "mediaUrls",
                    status,
                    moderation_note AS "moderationNote",
                    review_window_expires_at AS "reviewWindowExpiresAt",
                    edited_at AS "editedAt",
                    created_at AS "createdAt",
                    updated_at AS "updatedAt"
                FROM product_reviews
                WHERE user_id = :user_id
                  AND product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_reviews(session: AsyncSession, product_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pr.id::text,
                pr.product_id::text AS "productId",
                pr.user_id::text AS "userId",
                pr.user_name AS "userName",
                pr.rating,
                pr.comment,
                pr.media_urls AS "mediaUrls",
                pr.shop_reply AS "shopReply",
                pr.shop_replied_at AS "shopRepliedAt",
                CASE
                    WHEN o.status = 'REFUNDED' THEN 'DA_HOAN_TIEN'
                    WHEN o.status = 'RETURNED' THEN 'DA_TRA_HANG'
                    ELSE NULL
                END AS "orderOutcome",
                pr.created_at AS "createdAt"
            FROM product_reviews pr
            LEFT JOIN orders o ON o.id = pr.order_id
            WHERE pr.product_id = :product_id AND pr.status = 'PUBLISHED'
            ORDER BY pr.created_at DESC
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row._mapping) for row in result]


async def has_duplicate_review(
    session: AsyncSession,
    *,
    user_id: UUID,
    product_id: UUID,
    normalized_comment: str,
    exclude_review_id: UUID | None = None,
) -> bool:
    if exclude_review_id:
        return bool(
            await session.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM product_reviews
                        WHERE user_id = :user_id
                          AND product_id = :product_id
                          AND id <> :review_id
                          AND lower(trim(comment)) = :normalized_comment
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "product_id": product_id,
                    "review_id": exclude_review_id,
                    "normalized_comment": normalized_comment,
                },
            )
        )
    return bool(
        await session.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM product_reviews
                    WHERE user_id = :user_id
                      AND product_id = :product_id
                      AND lower(trim(comment)) = :normalized_comment
                )
                """
            ),
            {
                "user_id": user_id,
                "product_id": product_id,
                "normalized_comment": normalized_comment,
            },
        )
    )


async def insert_review(
    session: AsyncSession,
    *,
    review_id: UUID,
    product_id: UUID,
    order_id: UUID | None,
    user_id: UUID,
    user_name: str,
    rating: int,
    comment: str,
    media_urls: str,
    moderation_note: str,
    is_spam: bool,
    spam_reason: str | None,
    review_window_expires_at: object,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_reviews (
                id, product_id, order_id, user_id, user_name, rating, comment, media_urls,
                status, moderation_note, is_spam, spam_reason, review_window_expires_at
            )
            VALUES (
                :id, :product_id, :order_id, :user_id, :user_name, :rating, :comment, CAST(:media_urls AS jsonb),
                'PENDING', :moderation_note, :is_spam, :spam_reason, :review_window_expires_at
            )
            """
        ),
        {
            "id": review_id,
            "product_id": product_id,
            "order_id": order_id,
            "user_id": user_id,
            "user_name": user_name,
            "rating": rating,
            "comment": comment,
            "media_urls": media_urls,
            "moderation_note": moderation_note,
            "is_spam": is_spam,
            "spam_reason": spam_reason,
            "review_window_expires_at": review_window_expires_at,
        },
    )


async def get_own_review_for_edit(session: AsyncSession, *, review_id: UUID, product_id: UUID, user_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, review_window_expires_at
                FROM product_reviews
                WHERE id = :review_id
                  AND product_id = :product_id
                  AND user_id = :user_id
                """
            ),
            {"review_id": review_id, "product_id": product_id, "user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_review_for_moderation(
    session: AsyncSession,
    *,
    review_id: UUID,
    user_name: str,
    rating: int,
    comment: str,
    media_urls: str,
    moderation_note: str,
    is_spam: bool,
    spam_reason: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE product_reviews
            SET
                user_name = :user_name,
                rating = :rating,
                comment = :comment,
                media_urls = CAST(:media_urls AS jsonb),
                status = 'PENDING',
                moderation_note = :moderation_note,
                is_spam = :is_spam,
                spam_reason = :spam_reason,
                edited_at = NOW(),
                updated_at = NOW()
            WHERE id = :review_id
            """
        ),
        {
            "review_id": review_id,
            "user_name": user_name,
            "rating": rating,
            "comment": comment,
            "media_urls": media_urls,
            "moderation_note": moderation_note,
            "is_spam": is_spam,
            "spam_reason": spam_reason,
        },
    )


async def delete_review(session: AsyncSession, review_id: UUID) -> int:
    result = await session.execute(text("DELETE FROM product_reviews WHERE id = :review_id"), {"review_id": review_id})
    return int(result.rowcount or 0)


async def list_notifications(session: AsyncSession, user_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, type, title, message, read, created_at AS "createdAt"
            FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


async def mark_notifications_read(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text("UPDATE notifications SET read = TRUE WHERE user_id = :user_id"),
        {"user_id": user_id},
    )


async def list_rewards(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, title, description, cost, image_url AS "imageUrl", is_active AS "isActive"
            FROM rewards
            WHERE is_active = TRUE
            ORDER BY cost, created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def list_banners(session: AsyncSession, limit: int) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                v.id::text,
                v.title,
                v.description,
                v.banner_image_url AS "imageUrl",
                v.sort_order AS "sortOrder",
                COALESCE(
                    (
                        SELECT json_build_object(
                            'id', p.id::text,
                            'slug', p.slug,
                            'name', p.name
                        )
                        FROM content_product_relations cpr
                        JOIN products p ON p.id = cpr.product_id
                        WHERE cpr.content_id = v.id
                          AND p.status = 'ACTIVE'
                          AND p.deleted_at IS NULL
                        ORDER BY p.name ASC
                        LIMIT 1
                    ),
                    NULL
                ) AS product,
                COALESCE(
                    (
                        SELECT json_build_object(
                            'id', c.id::text,
                            'slug', c.slug,
                            'name', c.name
                        )
                        FROM content_category_relations ccr
                        JOIN categories c ON c.id = ccr.category_id
                        WHERE ccr.content_id = v.id
                          AND c.deleted_at IS NULL
                        ORDER BY c.name ASC
                        LIMIT 1
                    ),
                    NULL
                ) AS category
            FROM videos v
            WHERE v.is_active = TRUE
              AND v.deleted_at IS NULL
              AND v.content_type = 'BANNER'
              AND v.status = 'PUBLISHED'
              AND (v.scheduled_at IS NULL OR v.scheduled_at <= NOW())
            ORDER BY v.sort_order ASC, COALESCE(v.published_at, v.created_at) DESC, v.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in result]


async def list_videos(session: AsyncSession, *, limit: int, offset: int) -> list[dict]:
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
                CASE WHEN v.video_source = 'YOUTUBE' THEN v.video_url ELSE NULL END AS "youtubeUrl",
                v.thumbnail_url AS "thumbnailUrl",
                v.banner_image_url AS "bannerImageUrl",
                COALESCE((SELECT COUNT(*) FROM video_likes vl WHERE vl.video_id = v.id), 0)::int AS "likeCount",
                v.view_count AS "viewCount",
                v.sort_order AS "sortOrder",
                v.published_at AS "publishedAt",
                v.is_active AS "isActive",
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
                        SELECT json_agg(
                            json_build_object(
                                'id', p.id::text,
                                'name', p.name,
                                'imageUrl', p.image_url,
                                'price', p.price,
                                'discountPrice', p.sale_price,
                                'brand', b.name,
                                'categoryId', p.category_id::text
                            )
                            ORDER BY p.name ASC
                        )
                        FROM content_product_relations cpr
                        JOIN products p ON p.id = cpr.product_id
                        LEFT JOIN brands b ON b.id = p.brand_id
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS products,
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
                                'content', CASE WHEN cc.is_retracted THEN 'Bình luận này đã bị thu hồi' ELSE cc.body END,
                                'parentId', cc.parent_id::text,
                                'replyToUserName', cc.reply_to_user_name,
                                'isHidden', cc.is_hidden,
                                'isRetracted', cc.is_retracted,
                                'createdAt', cc.created_at
                            )
                            ORDER BY cc.created_at ASC
                        )
                        FROM content_comments cc
                        WHERE cc.content_id = v.id
                          AND cc.deleted_at IS NULL
                          AND cc.is_hidden = FALSE
                    ),
                    '[]'::json
                ) AS comments
            FROM videos v
            WHERE v.is_active = TRUE
              AND v.deleted_at IS NULL
              AND v.content_type = 'VIDEO'
              AND v.status = 'PUBLISHED'
              AND (v.scheduled_at IS NULL OR v.scheduled_at <= NOW())
            ORDER BY v.sort_order ASC, COALESCE(v.published_at, v.created_at) DESC, v.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    )
    return [dict(row._mapping) for row in result]


async def count_published_videos(session: AsyncSession) -> int:
    total = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM videos
            WHERE is_active = TRUE
              AND deleted_at IS NULL
              AND content_type = 'VIDEO'
              AND status = 'PUBLISHED'
              AND (scheduled_at IS NULL OR scheduled_at <= NOW())
            """
        )
    )
    return int(total or 0)


async def published_video_exists(session: AsyncSession, video_id: UUID) -> bool:
    return bool(
        await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM videos
                WHERE id = :video_id
                  AND content_type = 'VIDEO'
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                  AND status = 'PUBLISHED'
                """
            ),
            {"video_id": video_id},
        )
    )


async def video_exists(session: AsyncSession, video_id: UUID) -> bool:
    return bool(
        await session.scalar(
            text("SELECT COUNT(*) FROM videos WHERE id = :video_id AND content_type = 'VIDEO' AND deleted_at IS NULL"),
            {"video_id": video_id},
        )
    )


async def increment_video_view_count(session: AsyncSession, video_id: UUID) -> int | None:
    result = await session.execute(
        text(
            """
            UPDATE videos
            SET view_count = view_count + 1, updated_at = NOW()
            WHERE id = :video_id
              AND content_type = 'VIDEO'
              AND deleted_at IS NULL
              AND is_active = TRUE
              AND status = 'PUBLISHED'
            RETURNING view_count
            """
        ),
        {"video_id": video_id},
    )
    view_count = result.scalar_one_or_none()
    return int(view_count) if view_count is not None else None


async def user_liked_video(session: AsyncSession, *, video_id: UUID, user_id: UUID) -> bool:
    return bool(
        await session.scalar(
            text("SELECT COUNT(*) FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
            {"video_id": video_id, "user_id": user_id},
        )
    )


async def delete_video_like(session: AsyncSession, *, video_id: UUID, user_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM video_likes WHERE video_id = :video_id AND user_id = :user_id"),
        {"video_id": video_id, "user_id": user_id},
    )


async def insert_video_like(session: AsyncSession, *, video_id: UUID, user_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO video_likes (video_id, user_id)
            VALUES (:video_id, :user_id)
            ON CONFLICT (video_id, user_id) DO NOTHING
            """
        ),
        {"video_id": video_id, "user_id": user_id},
    )


async def count_video_likes(session: AsyncSession, video_id: UUID) -> int:
    like_count = await session.scalar(text("SELECT COUNT(*) FROM video_likes WHERE video_id = :video_id"), {"video_id": video_id})
    return int(like_count or 0)


async def product_exists(session: AsyncSession, product_id: UUID) -> bool:
    return bool(await session.scalar(text("SELECT COUNT(*) FROM products WHERE id = :product_id"), {"product_id": product_id}))


async def get_user_full_name(session: AsyncSession, user_id: UUID) -> str | None:
    return await session.scalar(text("SELECT full_name FROM users WHERE id = :user_id"), {"user_id": user_id})
