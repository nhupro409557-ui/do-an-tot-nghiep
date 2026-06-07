from fastapi import APIRouter

from app.api.routers.admin_audit import router as admin_audit_router
from app.api.routers.admin_brands import router as admin_brands_router
from app.api.routers.admin_categories import router as admin_categories_router
from app.api.routers.admin_content import router as admin_content_router
from app.api.routers.admin_customers import router as admin_customers_router
from app.api.routers.admin_flash_sales import router as admin_flash_sales_router
from app.api.routers.admin_inventory import router as admin_inventory_router
from app.api.routers.admin_overview import router as admin_overview_router
from app.api.routers.admin_products import router as admin_products_router
from app.api.routers.admin_product_variants import router as admin_product_variants_router
from app.api.routers.admin_product_approvals import router as admin_product_approvals_router
from app.api.routers.admin_reviews import router as admin_reviews_router
from app.api.routers.admin_uploads import router as admin_uploads_router
from app.api.routers.admin_vouchers import router as admin_vouchers_router


router = APIRouter(prefix="/admin", tags=["Admin"])
router.include_router(admin_overview_router)
router.include_router(admin_uploads_router)
router.include_router(admin_audit_router)
router.include_router(admin_brands_router)
router.include_router(admin_categories_router)
router.include_router(admin_content_router)
router.include_router(admin_customers_router)
router.include_router(admin_flash_sales_router)
router.include_router(admin_inventory_router)
router.include_router(admin_products_router)
router.include_router(admin_product_variants_router)
router.include_router(admin_product_approvals_router)
router.include_router(admin_reviews_router)
router.include_router(admin_vouchers_router)
