from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories import catalog_product_repo
from app.api.routers.catalog_categories import router as catalog_categories_router
from app.api.routers.catalog_products import router as catalog_products_router
from app.api.routers.catalog_search import router as catalog_search_router
from app.api.routers.catalog_utils import product_row

router = APIRouter(prefix="/catalog", tags=["Catalog"])
router.include_router(catalog_categories_router)
router.include_router(catalog_products_router)
router.include_router(catalog_search_router)

@router.get("/brands")
async def list_brands(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await catalog_product_repo.list_active_brands(session)

@router.get("/products")
async def list_products(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=50),
    brand: str | None = Query(default=None, max_length=50),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    flash_sale: bool | None = Query(default=None, alias="flash_sale"),
    featured: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    query_params = {}
    has_keyword_search = bool(q and q.strip())
    where_clauses = ["p.status IN ('ACTIVE', 'DISCONTINUED')" if has_keyword_search else "p.status = 'ACTIVE'", "p.deleted_at IS NULL"]

    if q and q.strip():
        # Will do python search scoring for keyword q
        pass

    if brand and brand.lower() != "all":
        where_clauses.append("(p.brand = :brand OR b.slug = :brand)")
        query_params["brand"] = brand

    if min_price is not None:
        where_clauses.append("COALESCE(p.sale_price, p.price) >= :min_price")
        query_params["min_price"] = min_price

    if max_price is not None:
        where_clauses.append("COALESCE(p.sale_price, p.price) <= :max_price")
        query_params["max_price"] = max_price

    if featured is not None:
        where_clauses.append("p.is_featured = :featured")
        query_params["featured"] = featured

    where_sql = " AND ".join(where_clauses)
    rows = await catalog_product_repo.list_active_product_rows(session, where_sql=where_sql, params=query_params)
    
    items = [product_row(row) for row in rows]
    
    from app.api.routers.catalog_utils import product_matches_category, product_search_score, approximate_trend_score, current_price
    
    # Category filter in python
    if category and category.lower() != "all":
        items = [item for item in items if product_matches_category(item, category)]

    # Flash sale filter in python
    if flash_sale is not None:
        items = [item for item in items if item.get("isFlashSale") == flash_sale]

    # Keyword search filter in python
    if q and q.strip():
        scored_items = []
        for item in items:
            score = product_search_score(item, q)
            if score > 0:
                item["_search_score"] = score
                scored_items.append(item)
        items = scored_items
        
    # Sort in python
    if q and q.strip():
        items.sort(key=lambda item: (-item["_search_score"], -approximate_trend_score(item)))
    elif sort == "price_asc":
        items.sort(key=lambda item: current_price(item))
    elif sort == "price_desc":
        items.sort(key=lambda item: current_price(item), reverse=True)
    elif sort == "trending":
        items.sort(key=lambda item: approximate_trend_score(item), reverse=True)
    elif sort == "rating":
        items.sort(key=lambda item: (item.get("rating") or 0.0, item.get("reviewCount") or 0), reverse=True)
    elif sort == "newest":
        items.sort(key=lambda item: item.get("id", ""), reverse=True)
    else:
        # Default sort by approximate trend score
        items.sort(key=lambda item: approximate_trend_score(item), reverse=True)

    return items[offset : offset + limit]
