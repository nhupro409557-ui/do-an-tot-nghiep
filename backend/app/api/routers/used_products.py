from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import used_product_service
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/storefront/used-products", tags=["Storefront - Hàng cũ"])


@router.get("")
async def list_used_products(
    search: str = Query(default="", max_length=120),
    grade: str = Query(default="", max_length=1),
    min_price: Decimal | None = Query(default=None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(default=None, alias="maxPrice", ge=0),
    sort: str = Query(default="newest", max_length=30),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=60),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.list_public_listings(
        session,
        search=search,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        limit=limit,
    )


@router.get("/{slug}")
async def get_used_product(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.get_public_listing(session, slug)
