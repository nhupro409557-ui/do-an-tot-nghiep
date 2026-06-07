from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.application.services.product_variant_service import delete_product_variant
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.delete("/products/{product_id}/variants/{variant_id}", dependencies=[Depends(require_permission("product:delete"))])
async def delete_product_variant_route(
    product_id: UUID,
    variant_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await delete_product_variant(product_id=product_id, variant_id=variant_id, session=session)
