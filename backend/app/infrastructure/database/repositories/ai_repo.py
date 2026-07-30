import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AIContextLog


async def list_active_products_for_ai(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH stock_by_product AS (
                SELECT
                    COALESCE(il.product_id, pv.product_id) AS product_id,
                    SUM(GREATEST(
                        il.on_hand_quantity - il.reserved_quantity - il.safety_stock_quantity,
                        0
                    ))::integer AS available_stock,
                    MAX(il.updated_at) AS stock_updated_at
                FROM inventory_levels il
                LEFT JOIN product_variants pv ON pv.id = il.variant_id
                GROUP BY COALESCE(il.product_id, pv.product_id)
            )
            SELECT p.id::text, p.slug, p.name, p.brand, p.price, p.sale_price AS "salePrice",
                   p.image_url AS "imageUrl", p.description, p.specifications,
                   c.name AS "categoryName", c.slug AS "categorySlug",
                   p.promotions, p.warranty_period AS "warrantyPeriod",
                   COALESCE(p.sales_config->'warrantyPolicy', c.warranty_policy, '{}'::jsonb) AS "warrantyPolicy",
                   p.created_at AS "createdAt", p.updated_at AS "updatedAt",
                   COALESCE(stock_by_product.available_stock, p.stock_quantity, 0) AS "availableStock",
                   COALESCE(stock_by_product.stock_updated_at, p.updated_at) AS "stockUpdatedAt",
                   COALESCE(review_stats.rating, 0) AS rating,
                   COALESCE(review_stats.review_count, 0) AS "reviewCount",
                   COALESCE(favorite_counts.favorite_count, 0) AS "favoriteCount",
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                           'id', pv.id::text,
                           'sku', pv.sku,
                           'colorName', pv.color_name,
                           'storage', pv.storage,
                           'ram', pv.ram,
                            'configuration', pv.configuration,
                            'price', pv.price,
                            'salePrice', pv.sale_price,
                            'availableStock', COALESCE((
                                SELECT SUM(GREATEST(
                                    ilv.on_hand_quantity - ilv.reserved_quantity - ilv.safety_stock_quantity,
                                    0
                                ))::integer
                                FROM inventory_levels ilv
                                WHERE ilv.variant_id = pv.id
                            ), pv.stock_quantity, 0),
                            'stockUpdatedAt', COALESCE((
                                SELECT MAX(ilv.updated_at)
                                FROM inventory_levels ilv
                                WHERE ilv.variant_id = pv.id
                            ), pv.updated_at),
                            'updatedAt', pv.updated_at
                       ) ORDER BY pv.is_default DESC, pv.created_at)
                       FROM product_variants pv
                       WHERE pv.product_id = p.id
                         AND pv.is_active = TRUE
                         AND pv.deleted_at IS NULL
                         AND LOWER(COALESCE(pv.status, 'active')) = 'active'
                   ), '[]'::jsonb) AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN stock_by_product ON stock_by_product.product_id = p.id
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
              AND p.deleted_at IS NULL
              AND COALESCE(p.hidden_by_category, FALSE) = FALSE
              AND COALESCE(p.hidden_by_brand, FALSE) = FALSE
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
                       o.updated_at AS "updatedAt", o.shipping_provider AS "shippingProvider",
                       o.tracking_code AS "trackingCode", o.shipped_at AS "shippedAt",
                       o.completed_at AS "completedAt", o.order_purpose AS "orderPurpose",
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


async def get_latest_user_order_for_ai(session: AsyncSession, *, user_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT o.order_code AS "orderCode", o.status, o.payment_status AS "paymentStatus",
                       o.total_amount AS "totalAmount", o.loyalty_points_earned AS "pointsEarned",
                       o.loyalty_points_used AS "pointsUsed", o.created_at AS "createdAt",
                       o.updated_at AS "updatedAt", o.shipping_provider AS "shippingProvider",
                       o.tracking_code AS "trackingCode", o.shipped_at AS "shippedAt",
                       o.completed_at AS "completedAt", o.order_purpose AS "orderPurpose",
                       COALESCE(jsonb_agg(jsonb_build_object(
                         'productName', oi.product_name,
                         'quantity', oi.quantity,
                         'totalPrice', oi.total_price
                       )) FILTER (WHERE oi.id IS NOT NULL), '[]'::jsonb) AS items
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.user_id = :user_id
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    return dict(row._mapping) if row else None


async def get_order_shipping_events_for_ai(
    session: AsyncSession,
    *,
    user_id: str,
    order_code: str,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT se.event_code AS "eventCode", se.title, se.description,
                   se.shipping_provider AS "shippingProvider",
                   se.tracking_code AS "trackingCode", se.occurred_at AS "occurredAt"
            FROM shipment_events se
            JOIN orders o ON o.id = se.order_id
            WHERE o.user_id = :user_id AND upper(o.order_code) = :order_code
            ORDER BY se.occurred_at ASC, se.created_at ASC
            LIMIT 50
            """
        ),
        {"user_id": user_id, "order_code": order_code},
    )
    return [dict(row._mapping) for row in result]


async def get_user_loyalty_for_ai(session: AsyncSession, *, user_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT loyalty_points_balance AS "pointsBalance",
                       loyalty_tier AS tier,
                       loyalty_wallet_status AS "walletStatus",
                       loyalty_tier_period_started_at AS "periodStartedAt",
                       loyalty_tier_period_ends_at AS "periodEndsAt",
                       COALESCE((
                           SELECT SUM(o.total_amount)
                           FROM orders o
                           WHERE o.user_id = users.id
                             AND o.status = 'COMPLETED'
                             AND o.completed_at >= users.loyalty_tier_period_started_at
                             AND o.completed_at < users.loyalty_tier_period_ends_at
                       ), 0)::bigint AS "periodSpendAmount",
                       updated_at AS "updatedAt"
                FROM users
                WHERE id = :user_id AND deleted_at IS NULL AND status = 'ACTIVE'
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    return dict(row._mapping) if row else None


async def get_user_after_sales_for_ai(
    session: AsyncSession,
    *,
    user_id: str,
    request_code: str,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                WITH owned_request AS (
                    SELECT 'WARRANTY'::text AS request_type, wr.id, wr.request_code,
                           wr.status, wr.resolution_type, wr.sla_due_at,
                           wr.created_at, wr.updated_at
                    FROM warranty_requests wr
                    WHERE wr.user_id = :user_id AND upper(wr.request_code) = :request_code
                    UNION ALL
                    SELECT 'RETURN'::text AS request_type, rr.id, rr.request_code,
                           rr.status, rr.resolution_type, rr.sla_due_at,
                           rr.created_at, rr.updated_at
                    FROM return_requests rr
                    WHERE rr.user_id = :user_id AND upper(rr.request_code) = :request_code
                )
                SELECT owned_request.request_type AS "requestType",
                       owned_request.request_code AS "requestCode",
                       owned_request.status,
                       owned_request.resolution_type AS "resolutionType",
                       owned_request.sla_due_at AS "slaDueAt",
                       owned_request.created_at AS "createdAt",
                       owned_request.updated_at AS "updatedAt",
                       COALESCE((
                           SELECT jsonb_agg(jsonb_build_object(
                               'oldStatus', ase.old_status,
                               'newStatus', ase.new_status,
                               'note', ase.note,
                               'createdAt', ase.created_at
                           ) ORDER BY ase.created_at ASC)
                           FROM after_sales_events ase
                           WHERE ase.reference_type = owned_request.request_type
                             AND ase.reference_id = owned_request.id
                       ), '[]'::jsonb) AS events
                FROM owned_request
                LIMIT 1
                """
            ),
            {"user_id": user_id, "request_code": request_code},
        )
    ).first()
    return dict(row._mapping) if row else None


async def get_latest_user_after_sales_for_ai(session: AsyncSession, *, user_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                WITH owned_request AS (
                    SELECT 'WARRANTY'::text AS request_type, wr.id, wr.request_code,
                           wr.status, wr.resolution_type, wr.sla_due_at,
                           wr.created_at, wr.updated_at
                    FROM warranty_requests wr
                    WHERE wr.user_id = :user_id
                    UNION ALL
                    SELECT 'RETURN'::text AS request_type, rr.id, rr.request_code,
                           rr.status, rr.resolution_type, rr.sla_due_at,
                           rr.created_at, rr.updated_at
                    FROM return_requests rr
                    WHERE rr.user_id = :user_id
                )
                SELECT owned_request.request_type AS "requestType",
                       owned_request.request_code AS "requestCode",
                       owned_request.status,
                       owned_request.resolution_type AS "resolutionType",
                       owned_request.sla_due_at AS "slaDueAt",
                       owned_request.created_at AS "createdAt",
                       owned_request.updated_at AS "updatedAt",
                       COALESCE((
                           SELECT jsonb_agg(jsonb_build_object(
                               'oldStatus', ase.old_status,
                               'newStatus', ase.new_status,
                               'note', ase.note,
                               'createdAt', ase.created_at
                           ) ORDER BY ase.created_at ASC)
                           FROM after_sales_events ase
                           WHERE ase.reference_type = owned_request.request_type
                             AND ase.reference_id = owned_request.id
                       ), '[]'::jsonb) AS events
                FROM owned_request
                ORDER BY owned_request.updated_at DESC, owned_request.created_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    return dict(row._mapping) if row else None


async def get_user_account_for_ai(session: AsyncSession, *, user_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT status,
                       regexp_replace(email, '(^.).*(@.*$)', '\\1***\\2') AS "maskedEmail",
                       CASE
                           WHEN phone IS NULL OR phone = '' THEN NULL
                           ELSE regexp_replace(phone, '(^.{2}).*(.{2}$)', '\\1******\\2')
                       END AS "maskedPhone",
                       jsonb_array_length(COALESCE(addresses, '[]'::jsonb)) AS "addressCount",
                       birth_date IS NOT NULL AS "hasBirthDate",
                       birth_date_locked_at IS NOT NULL AS "birthDateLocked",
                       COALESCE((
                           SELECT COUNT(*)
                           FROM refresh_token_sessions sessions
                           WHERE sessions.user_id = users.id
                             AND sessions.revoked_at IS NULL
                             AND sessions.expires_at > NOW()
                       ), 0)::integer AS "activeSessionCount",
                       updated_at AS "updatedAt"
                FROM users
                WHERE id = :user_id AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    return dict(row._mapping) if row else None


async def get_product_review_insights_for_ai(session: AsyncSession, *, product_id: str) -> dict:
    row = (
        await session.execute(
            text(
                """
                WITH published AS (
                    SELECT rating, comment, order_id, shop_reply, created_at
                    FROM product_reviews
                    WHERE product_id = :product_id
                      AND status = 'PUBLISHED'
                      AND is_spam = FALSE
                ), distribution AS (
                    SELECT jsonb_object_agg(rating::text, amount) AS values
                    FROM (
                        SELECT rating, COUNT(*)::integer AS amount
                        FROM published
                        GROUP BY rating
                    ) counts
                )
                SELECT COALESCE(ROUND(AVG(rating), 2), 0) AS "averageRating",
                       COUNT(*)::integer AS "reviewCount",
                       COUNT(*) FILTER (WHERE order_id IS NOT NULL)::integer AS "verifiedPurchaseCount",
                       COUNT(*) FILTER (WHERE shop_reply IS NOT NULL)::integer AS "shopReplyCount",
                       COALESCE((SELECT values FROM distribution), '{}'::jsonb) AS "ratingDistribution",
                       COALESCE((
                           SELECT jsonb_agg(comment)
                           FROM (
                               SELECT comment
                               FROM published
                               WHERE rating >= 4 AND NULLIF(BTRIM(comment), '') IS NOT NULL
                               ORDER BY created_at DESC
                               LIMIT 5
                           ) positive
                       ), '[]'::jsonb) AS "positiveComments",
                       COALESCE((
                           SELECT jsonb_agg(comment)
                           FROM (
                               SELECT comment
                               FROM published
                               WHERE rating <= 2 AND NULLIF(BTRIM(comment), '') IS NOT NULL
                               ORDER BY created_at DESC
                               LIMIT 5
                           ) critical
                       ), '[]'::jsonb) AS "criticalComments",
                       MAX(created_at) AS "updatedAt"
                FROM published
                """
            ),
            {"product_id": product_id},
        )
    ).first()
    return dict(row._mapping) if row else {
        "averageRating": 0,
        "reviewCount": 0,
        "verifiedPurchaseCount": 0,
        "shopReplyCount": 0,
        "ratingDistribution": {},
        "positiveComments": [],
        "criticalComments": [],
    }


async def upsert_user_support_request_for_ai(
    session: AsyncSession,
    *,
    user_id: str,
    conversation_id: str,
    category: str,
    priority: str,
    summary: str,
) -> dict:
    request_code = f"CS{uuid4().hex[:12].upper()}"
    row = (
        await session.execute(
            text(
                """
                INSERT INTO ai_support_requests (
                    id, request_code, user_id, conversation_id, category, priority,
                    summary, status, created_at, updated_at
                ) VALUES (
                    :id, :request_code, :user_id, :conversation_id, :category, :priority,
                    :summary, 'OPEN', NOW(), NOW()
                )
                ON CONFLICT (user_id, conversation_id) DO UPDATE
                SET category = EXCLUDED.category,
                    priority = CASE
                        WHEN ai_support_requests.priority = 'URGENT' THEN 'URGENT'
                        ELSE EXCLUDED.priority
                    END,
                    summary = EXCLUDED.summary,
                    updated_at = NOW()
                RETURNING request_code AS "requestCode", category, priority, status,
                          created_at AS "createdAt", updated_at AS "updatedAt"
                """
            ),
            {
                "id": uuid4(),
                "request_code": request_code,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "category": category,
                "priority": priority,
                "summary": summary[:1000],
            },
        )
    ).first()
    return dict(row._mapping)


async def get_latest_user_support_request_for_ai(session: AsyncSession, *, user_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT request_code AS "requestCode", category, priority, status,
                       summary, resolution_note AS "resolutionNote",
                       created_at AS "createdAt", updated_at AS "updatedAt"
                FROM ai_support_requests
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    return dict(row._mapping) if row else None


async def list_support_requests_for_admin(
    session: AsyncSession,
    *,
    status_value: str | None,
    limit: int,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT requests.id::text, requests.request_code AS "requestCode",
                   requests.category, requests.priority, requests.status,
                   requests.summary, requests.resolution_note AS "resolutionNote",
                   users.full_name AS "customerName", users.email AS "customerEmail",
                   requests.created_at AS "createdAt", requests.updated_at AS "updatedAt"
            FROM ai_support_requests requests
            JOIN users ON users.id = requests.user_id
            WHERE (:status_value IS NULL OR requests.status = :status_value)
            ORDER BY
                CASE requests.priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END,
                requests.updated_at DESC
            LIMIT :limit
            """
        ),
        {"status_value": status_value, "limit": limit},
    )
    return [dict(row._mapping) for row in result]


async def update_support_request_for_admin(
    session: AsyncSession,
    *,
    request_id: UUID,
    status_value: str,
    resolution_note: str | None,
    assigned_to: UUID,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE ai_support_requests
                SET status = :status_value,
                    resolution_note = :resolution_note,
                    assigned_to = :assigned_to,
                    updated_at = NOW()
                WHERE id = :request_id
                RETURNING id::text, request_code AS "requestCode", category, priority,
                          status, summary, resolution_note AS "resolutionNote",
                          created_at AS "createdAt", updated_at AS "updatedAt"
                """
            ),
            {
                "request_id": request_id,
                "status_value": status_value,
                "resolution_note": resolution_note,
                "assigned_to": assigned_to,
            },
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
    log_id: UUID | None = None,
) -> None:
    log = AIContextLog(
        id=log_id or uuid4(),
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


async def get_or_create_ai_conversation_session(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID | None,
    ttl_minutes: int,
) -> dict | None:
    await session.execute(
        text(
            """
            INSERT INTO ai_conversation_sessions (
                conversation_id, user_id, expires_at, created_at, updated_at
            )
            VALUES (
                :conversation_id, :user_id,
                NOW() + make_interval(mins => :ttl_minutes), NOW(), NOW()
            )
            ON CONFLICT (conversation_id) DO NOTHING
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "ttl_minutes": ttl_minutes,
        },
    )
    if user_id is not None:
        await session.execute(
            text(
                """
                UPDATE ai_conversation_sessions
                SET user_id = :user_id, updated_at = NOW()
                WHERE conversation_id = :conversation_id
                  AND user_id IS NULL
                """
            ),
            {"conversation_id": conversation_id, "user_id": user_id},
        )
    await session.execute(
        text(
            """
            UPDATE ai_conversation_sessions
            SET active_intent = NULL,
                active_entities = '{}'::jsonb,
                pending_slots = '{}'::jsonb,
                summary = '',
                unresolved_streak = 0,
                last_failure_reason = NULL,
                handover_offered_at = NULL,
                expires_at = NOW() + make_interval(mins => :ttl_minutes),
                updated_at = NOW()
            WHERE conversation_id = :conversation_id
              AND expires_at <= NOW()
              AND (
                  (user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
                  OR user_id = CAST(:user_id AS uuid)
              )
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "ttl_minutes": ttl_minutes,
        },
    )
    result = await session.execute(
        text(
            """
            SELECT conversation_id::text AS "conversationId",
                   user_id::text AS "userId",
                   active_intent AS "activeIntent",
                   active_entities AS "activeEntities",
                   pending_slots AS "pendingSlots",
                   summary,
                   unresolved_streak AS "unresolvedStreak",
                   last_failure_reason AS "lastFailureReason",
                   handover_offered_at AS "handoverOfferedAt",
                   expires_at AS "expiresAt",
                   updated_at AS "updatedAt"
            FROM ai_conversation_sessions
            WHERE conversation_id = :conversation_id
              AND (
                  (user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
                  OR user_id = CAST(:user_id AS uuid)
              )
            """
        ),
        {"conversation_id": conversation_id, "user_id": user_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def update_ai_conversation_session(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID | None,
    active_intent: str | None,
    active_entities: dict,
    pending_slots: dict,
    summary: str,
    unresolved_streak: int,
    last_failure_reason: str | None,
    handover_offered_at,
    ttl_minutes: int,
) -> bool:
    result = await session.execute(
        text(
            """
            UPDATE ai_conversation_sessions
            SET active_intent = :active_intent,
                active_entities = CAST(:active_entities AS jsonb),
                pending_slots = CAST(:pending_slots AS jsonb),
                summary = :summary,
                unresolved_streak = :unresolved_streak,
                last_failure_reason = :last_failure_reason,
                handover_offered_at = :handover_offered_at,
                expires_at = NOW() + make_interval(mins => :ttl_minutes),
                updated_at = NOW()
            WHERE conversation_id = :conversation_id
              AND (
                  (user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
                  OR user_id = CAST(:user_id AS uuid)
              )
            RETURNING conversation_id
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "active_intent": active_intent,
            "active_entities": json.dumps(active_entities, ensure_ascii=False),
            "pending_slots": json.dumps(pending_slots, ensure_ascii=False),
            "summary": summary[:2000],
            "unresolved_streak": max(0, unresolved_streak),
            "last_failure_reason": last_failure_reason,
            "handover_offered_at": handover_offered_at,
            "ttl_minutes": ttl_minutes,
        },
    )
    return result.first() is not None


async def get_recent_ai_conversation_turns(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID | None,
    limit: int,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT user_message AS "userMessage",
                   assistant_response AS "assistantResponse",
                   dynamic_context->>'intent' AS intent,
                   created_at AS "createdAt"
            FROM ai_context_logs
            WHERE conversation_id = :conversation_id
              AND (
                  user_id = CAST(:user_id AS uuid)
                  OR (user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
              )
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "limit": max(1, min(limit, 12)),
        },
    )
    return [dict(row) for row in reversed(result.mappings().all())]


async def save_ai_feedback(
    session: AsyncSession,
    *,
    response_id: UUID,
    conversation_id: UUID,
    user_id: UUID | None,
    helpful: bool,
    reason: str | None,
) -> bool:
    result = await session.execute(
        text(
            """
            INSERT INTO ai_response_feedback (
                response_id, user_id, helpful, reason, created_at, updated_at
            )
            SELECT logs.id, :user_id, :helpful, :reason, NOW(), NOW()
            FROM ai_context_logs logs
            WHERE logs.id = :response_id
              AND logs.conversation_id = :conversation_id
              AND (
                  (logs.user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
                  OR logs.user_id = CAST(:user_id AS uuid)
              )
            ON CONFLICT (response_id) DO UPDATE
            SET helpful = EXCLUDED.helpful,
                reason = EXCLUDED.reason,
                updated_at = NOW()
            RETURNING response_id
            """
        ),
        {
            "response_id": response_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "helpful": helpful,
            "reason": reason,
        },
    )
    return result.first() is not None


async def get_consecutive_unhelpful_feedback_count(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID | None,
    limit: int = 10,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT feedback.helpful
            FROM ai_response_feedback feedback
            JOIN ai_context_logs logs ON logs.id = feedback.response_id
            WHERE logs.conversation_id = :conversation_id
              AND (
                  (logs.user_id IS NULL AND CAST(:user_id AS uuid) IS NULL)
                  OR logs.user_id = CAST(:user_id AS uuid)
              )
            ORDER BY feedback.updated_at DESC
            LIMIT :limit
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "limit": max(1, min(limit, 20)),
        },
    )
    count = 0
    for row in result:
        if bool(row.helpful):
            break
        count += 1
    return count


async def get_ai_operational_metrics(session: AsyncSession, *, hours: int = 24) -> dict:
    window_hours = max(1, min(hours, 24 * 30))
    summary = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*)::integer AS total_responses,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'answer_mode' = 'DATABASE_FALLBACK'
                    )::integer AS fallback_responses,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'verification_passed' = 'false'
                    )::integer AS verifier_failures,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'needs_clarification' = 'true'
                    )::integer AS clarification_responses,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'provider_used' = 'GEMINI'
                    )::integer AS gemini_responses,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'shadow_intent' IS NOT NULL
                    )::integer AS shadow_evaluations,
                    COUNT(*) FILTER (
                        WHERE dynamic_context->>'shadow_intent' IS NOT NULL
                          AND dynamic_context->>'shadow_intent' = dynamic_context->>'intent'
                    )::integer AS shadow_matches,
                    ROUND(AVG(
                        CASE
                            WHEN dynamic_context->>'confidence' ~ '^[0-9]+([.][0-9]+)?$'
                            THEN (dynamic_context->>'confidence')::numeric
                            ELSE NULL
                        END
                    ), 4) AS average_confidence
                FROM ai_context_logs
                WHERE created_at >= NOW() - make_interval(hours => :hours)
                  AND COALESCE(dynamic_context->>'traffic_origin', 'CUSTOMER') <> 'SYNTHETIC'
                """
            ),
            {"hours": window_hours},
        )
    ).first()

    feedback = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*)::integer AS total_feedback,
                    COUNT(*) FILTER (WHERE feedback.helpful)::integer AS helpful_feedback
                FROM ai_response_feedback feedback
                JOIN ai_context_logs logs ON logs.id = feedback.response_id
                WHERE logs.created_at >= NOW() - make_interval(hours => :hours)
                  AND COALESCE(logs.dynamic_context->>'traffic_origin', 'CUSTOMER') <> 'SYNTHETIC'
                """
            ),
            {"hours": window_hours},
        )
    ).first()

    synthetic_responses = int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)::integer
                    FROM ai_context_logs
                    WHERE created_at >= NOW() - make_interval(hours => :hours)
                      AND dynamic_context->>'traffic_origin' = 'SYNTHETIC'
                    """
                ),
                {"hours": window_hours},
            )
        ).scalar_one()
        or 0
    )

    summary_data = dict(summary._mapping) if summary else {}
    feedback_data = dict(feedback._mapping) if feedback else {}
    total_responses = int(summary_data.get("total_responses") or 0)
    total_feedback = int(feedback_data.get("total_feedback") or 0)
    fallback_responses = int(summary_data.get("fallback_responses") or 0)
    verifier_failures = int(summary_data.get("verifier_failures") or 0)
    helpful_feedback = int(feedback_data.get("helpful_feedback") or 0)
    shadow_evaluations = int(summary_data.get("shadow_evaluations") or 0)
    shadow_matches = int(summary_data.get("shadow_matches") or 0)
    return {
        "window_hours": window_hours,
        "total_responses": total_responses,
        "synthetic_responses": synthetic_responses,
        "gemini_responses": int(summary_data.get("gemini_responses") or 0),
        "fallback_responses": fallback_responses,
        "fallback_rate": fallback_responses / total_responses if total_responses else 0,
        "verifier_failures": verifier_failures,
        "verifier_failure_rate": verifier_failures / total_responses if total_responses else 0,
        "clarification_responses": int(summary_data.get("clarification_responses") or 0),
        "average_confidence": float(summary_data.get("average_confidence") or 0),
        "shadow_evaluations": shadow_evaluations,
        "shadow_matches": shadow_matches,
        "shadow_match_rate": shadow_matches / shadow_evaluations if shadow_evaluations else 0,
        "total_feedback": total_feedback,
        "helpful_feedback": helpful_feedback,
        "helpful_rate": helpful_feedback / total_feedback if total_feedback else 0,
    }
