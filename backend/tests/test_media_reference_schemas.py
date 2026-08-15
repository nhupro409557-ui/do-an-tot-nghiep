from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.schemas.admin.brand import BrandPayload
from app.api.schemas.admin.category import CategoryPayload
from app.api.schemas.admin.content import ContentPayload
from app.api.schemas.admin.inventory import (
    InventoryReceiptAttachmentPayload,
    InventoryReceiptLineQualityPayload,
)
from app.api.schemas.admin.product import ProductPayload, ProductVariantPayload
from app.api.schemas.admin.used_product import UsedDeviceInspectionPayload, UsedDeviceListingPayload
from app.api.schemas.content import ProductImageCommentRequest, ReviewRequest
from app.application.services.product_helper_service import validate_optimized_media


def test_catalog_payloads_store_managed_media_as_file_keys():
    product = ProductPayload(
        name="Điện thoại thử nghiệm",
        price=10_000_000,
        imageUrl="https://api.example.com/media/products/main.webp",
        images=["/uploads/products/gallery.webp"],
        videoUrl="products/demo.mp4",
        variants=[
            ProductVariantPayload(
                price=10_000_000,
                imageUrl="/media/products/variant.webp",
                images=["https://api.example.com/uploads/products/variant-gallery.webp"],
            )
        ],
    )
    category = CategoryPayload(
        name="Điện thoại",
        iconUrl="/media/categories/icon.webp",
        bannerUrl="/uploads/categories/banner.webp",
    )
    brand = BrandPayload(
        name="Thương hiệu thử nghiệm",
        code="TEST",
        logoUrl="https://api.example.com/media/brands/logo.webp",
    )

    assert product.imageUrl == "products/main.webp"
    assert product.images == ["products/gallery.webp"]
    assert product.videoUrl == "products/demo.mp4"
    assert product.variants[0].imageUrl == "products/variant.webp"
    assert product.variants[0].images == ["products/variant-gallery.webp"]
    assert category.iconUrl == "categories/icon.webp"
    assert category.bannerUrl == "categories/banner.webp"
    assert brand.logoUrl == "brands/logo.webp"


def test_content_and_review_payloads_keep_external_urls_but_store_managed_keys():
    content = ContentPayload(
        title="Video hướng dẫn",
        videoUrl="https://www.youtube.com/watch?v=demo",
        thumbnailUrl="/media/content/thumbnail.webp",
        bannerImageUrl="/uploads/content/banner.webp",
    )
    review = ReviewRequest(
        userName="Khách hàng",
        rating=5,
        comment="Sản phẩm hoạt động tốt.",
        mediaUrls=["/media/reviews/user/product/photo.webp"],
    )
    comment = ProductImageCommentRequest(
        body="Ảnh thực tế",
        imageUrl="products/gallery.webp",
    )

    assert content.videoUrl == "https://www.youtube.com/watch?v=demo"
    assert content.thumbnailUrl == "content/thumbnail.webp"
    assert content.bannerImageUrl == "content/banner.webp"
    assert review.mediaUrls == ["reviews/user/product/photo.webp"]
    assert comment.imageUrl == "products/gallery.webp"


def test_inventory_and_used_product_payloads_store_nested_media_keys():
    attachment = InventoryReceiptAttachmentPayload(
        name="Hóa đơn",
        url="/media/inventory/invoice.pdf",
    )
    quality = InventoryReceiptLineQualityPayload(
        lineId=uuid4(),
        passedQuantity=1,
        failedQuantity=0,
        images=[
            "/uploads/inventory/box.webp",
            {"url": "/media/inventory/device.webp", "caption": "Mặt trước"},
        ],
    )
    inspection = UsedDeviceInspectionPayload(
        outcome="APPRAISED",
        evidence=[{"url": "/media/used-products/inspection.webp", "name": "Kiểm định"}],
    )
    listing = UsedDeviceListingPayload(
        title="Điện thoại cũ còn đẹp",
        description="Thiết bị đã được kiểm tra đầy đủ và hoạt động ổn định.",
        images=["https://api.example.com/uploads/used-products/listing.webp"],
    )

    assert attachment.url == "inventory/invoice.pdf"
    assert quality.images == [
        "inventory/box.webp",
        {"url": "inventory/device.webp", "caption": "Mặt trước"},
    ]
    assert inspection.evidence[0]["url"] == "used-products/inspection.webp"
    assert listing.images == ["used-products/listing.webp"]


@pytest.mark.parametrize(
    "reference",
    [
        "products/../secret.txt",
        "/media/products/%2e%2e/secret.txt",
        "https://api.example.com/uploads/products/../../secret.txt",
    ],
)
def test_rejects_unsafe_managed_media_references(reference):
    with pytest.raises(ValidationError, match="Đường dẫn media không hợp lệ"):
        ProductPayload(
            name="Sản phẩm thử nghiệm",
            price=1_000_000,
            imageUrl=reference,
        )


def test_product_service_accepts_canonical_storage_keys():
    payload = ProductPayload(
        name="Sản phẩm thử nghiệm",
        price=1_000_000,
        images=["products/gallery.webp"],
    )

    validate_optimized_media(payload)
