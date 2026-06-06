from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.admin import ProductBulkActionPayload
from app.infrastructure.database.repositories import product_approval_repo
from app.infrastructure.database.repositories import product_repo
from app.application.services.product_helper_service import (
    sync_parent_price_from_variants,
    sync_parent_price_if_variants_exist,
)


async def merge_revision_variants(session: AsyncSession, *, parent_id: UUID, revision_id: UUID) -> None:
    await product_approval_repo.merge_revision_variants(session, parent_id=parent_id, revision_id=revision_id)


async def transition_product_status(
    session: AsyncSession,
    product_id: UUID,
    *,
    allowed_from: set[str],
    next_status: str,
) -> dict:
    if next_status == "ACTIVE":
        blocker = await product_repo.product_visibility_blocker(session, product_id=product_id)
        if blocker:
            raise HTTPException(status_code=400, detail=blocker)
        await sync_parent_price_if_variants_exist(session, product_id)
    result = await product_approval_repo.transition_product_status_data(
        session,
        product_id,
        allowed_from=allowed_from,
        next_status=next_status,
    )
    published_product_id = result.get("publishedProductId")
    if next_status == "ACTIVE" and published_product_id:
        await sync_parent_price_from_variants(session, UUID(published_product_id))
    return result


async def submit_product(product_id: UUID, session: AsyncSession) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "REVISION_DRAFT"}, next_status="PENDING")


async def approve_product(
    product_id: UUID,
    session: AsyncSession,
    role_code: str,
) -> dict:
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    return await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")


async def reactivate_product(product_id: UUID, session: AsyncSession) -> dict:
    blocker = await product_repo.product_visibility_blocker(session, product_id=product_id)
    if blocker:
        raise HTTPException(status_code=400, detail=blocker)
    return await product_approval_repo.reactivate_product_data(product_id, session)


async def bulk_approve_products(
    payload: ProductBulkActionPayload,
    session: AsyncSession,
    role_code: str,
) -> dict:
    ids = payload.ids or payload.productIds or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "updated": updated, "skipped": skipped}


async def product_bulk_action(
    payload: ProductBulkActionPayload,
    session: AsyncSession,
    role_code: str,
) -> dict:
    ids = payload.productIds or payload.ids or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})

    for product_id in ids:
        try:
            if payload.action == "APPROVE":
                await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            elif payload.action == "ARCHIVE":
                await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")
            elif payload.action == "HIDE":
                await product_approval_repo.hide_product_data(product_id, session)
            elif payload.action == "RESTORE":
                await reactivate_product(product_id, session)
            elif payload.action == "DELETE":
                await product_approval_repo.deactivate_product_data(product_id, session)
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "action": payload.action, "updated": updated, "skipped": skipped}


async def archive_product(product_id: UUID, session: AsyncSession) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE", "REVISION_DRAFT"}, next_status="ARCHIVED")


async def hide_product(product_id: UUID, session: AsyncSession) -> dict:
    return await product_approval_repo.hide_product_data(product_id, session)


async def deactivate_product(product_id: UUID, session: AsyncSession) -> dict:
    return await product_approval_repo.deactivate_product_data(product_id, session)
