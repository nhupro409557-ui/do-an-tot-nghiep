from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.api.schemas.admin import AttachedServicePayload, ProductPayload
from app.application.services import attached_service, product_service
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/products", dependencies=[Depends(require_permission("product:read"))])
async def list_admin_products(
    page: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=80),
    search: str = Query(default="", max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict] | dict:
    return await product_service.list_admin_products(
        page=page,
        limit=limit,
        cursor=cursor,
        search=search,
        status_filter=status_filter,
        categoryId=categoryId,
        brandId=brandId,
        session=session,
    )


@router.get("/products/suggestions", dependencies=[Depends(require_permission("product:read"))])
async def suggest_admin_products(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    excludeId: UUID | None = None,
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await product_service.suggest_admin_products(
        search=search,
        limit=limit,
        excludeId=excludeId,
        categoryId=categoryId,
        brandId=brandId,
        session=session,
    )


@router.get("/attached-services", dependencies=[Depends(require_permission("service:read"))])
async def list_attached_services(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await attached_service.list_attached_services(session)


@router.post("/attached-services", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("service:create"))])
async def create_attached_service(payload: AttachedServicePayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await attached_service.create_attached_service(session, payload)


@router.patch("/attached-services/{service_id}", dependencies=[Depends(require_permission("service:update"))])
async def update_attached_service(service_id: UUID, payload: AttachedServicePayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await attached_service.update_attached_service(session, service_id, payload)


@router.delete("/attached-services/{service_id}", dependencies=[Depends(require_permission("service:delete"))])
async def delete_attached_service(service_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await attached_service.delete_attached_service(session, service_id)


@router.patch("/attached-services/{service_id}/deactivate", dependencies=[Depends(require_permission("service:update"))])
async def deactivate_attached_service(service_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await attached_service.deactivate_attached_service(session, service_id)


@router.patch("/attached-services/{service_id}/reactivate", dependencies=[Depends(require_permission("service:update"))])
async def reactivate_attached_service(service_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await attached_service.reactivate_attached_service(session, service_id)


@router.post("/products/import", dependencies=[Depends(require_permission("product:create"))])
async def import_products(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await product_service.import_products(background_tasks=background_tasks, file=file, session=session)


@router.get("/products/import-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await product_service.list_product_import_jobs(session=session)


@router.post("/products/export", dependencies=[Depends(require_permission("product:read"))])
async def export_products(
    background_tasks: BackgroundTasks,
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await product_service.export_products(background_tasks=background_tasks, filters=filters, session=session)


@router.get("/products/export-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_export_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await product_service.list_product_export_jobs(session=session)


@router.get("/products/kpis", dependencies=[Depends(require_permission("product:read"))])
async def product_catalog_kpis(session: AsyncSession = Depends(get_session)) -> dict:
    return await product_service.product_catalog_kpis(session=session)


@router.get("/products/{product_id}/audit-logs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_audit_logs(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await product_service.list_product_audit_logs(product_id=product_id, session=session)


@router.post("/products", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:create"))])
async def create_product(payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_service.create_product(payload=payload, session=session)


@router.patch("/products/{product_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_product(product_id: UUID, payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_service.update_product(product_id=product_id, payload=payload, session=session)


@router.post("/products/{product_id}/duplicate", dependencies=[Depends(require_permission("product:create"))])
async def duplicate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_service.duplicate_product(product_id=product_id, session=session)
