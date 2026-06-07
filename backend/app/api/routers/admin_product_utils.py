"""Compatibility exports for product helper functions.

New code should import these helpers from
``app.application.services.product_helper_service``.
"""

from app.application.services.product_helper_service import (
    extract_product_metadata,
    normalize_product_options,
    normalized_option_key,
    persisted_sales_config,
    resolve_catalog_labels,
    sync_parent_price_from_variants,
    sync_parent_price_if_variants_exist,
    validate_optimized_media,
)


__all__ = [
    "extract_product_metadata",
    "normalize_product_options",
    "normalized_option_key",
    "persisted_sales_config",
    "resolve_catalog_labels",
    "sync_parent_price_from_variants",
    "sync_parent_price_if_variants_exist",
    "validate_optimized_media",
]
