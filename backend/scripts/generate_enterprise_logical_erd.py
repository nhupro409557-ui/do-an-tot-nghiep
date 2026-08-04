"""Sinh Logical ERD chuẩn 3NF dưới dạng draw.io nhiều trang."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "logical_erd_enterprise.drawio"

TABLE_WIDTH = 280
HEADER_HEIGHT = 34
ROW_HEIGHT = 28


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityPlacement:
    name: str
    x: int
    y: int
    kind: str = "entity"
    fields: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Relationship:
    parent: str
    parent_column: str
    child: str
    child_column: str
    parent_cardinality: str = "one"
    child_cardinality: str = "zero_many"
    waypoints: tuple[tuple[int, int], ...] | None = None


def col(name: str, data_type: str, *keys: str) -> Column:
    return Column(name, data_type, tuple(keys))


SCHEMAS: dict[str, tuple[Column, ...]] = {
    "role": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
    ),
    "permission": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
    ),
    "role_permission": (
        col("role_id", "String", "PK", "FK"),
        col("permission_id", "String", "PK", "FK"),
    ),
    "user": (
        col("id", "String", "PK"),
        col("role_id", "String", "FK"),
        col("email", "String", "UK"),
        col("password_hash", "String"),
        col("full_name", "String"),
        col("phone", "String"),
        col("status", "String"),
        col("created_at", "DateTime"),
    ),
    "user_address": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("label", "String"),
        col("recipient_name", "String"),
        col("recipient_phone", "String"),
        col("address_line", "Text"),
        col("is_default", "Boolean"),
    ),
    "customer_tag": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
    ),
    "user_tag": (
        col("user_id", "String", "PK", "FK"),
        col("tag_id", "String", "PK", "FK"),
        col("assigned_at", "DateTime"),
    ),
    "loyalty_tier": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("minimum_points", "Integer"),
    ),
    "loyalty_account": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK", "UK"),
        col("tier_id", "String", "FK"),
        col("points_balance", "Integer"),
        col("period_started_at", "DateTime"),
        col("period_ends_at", "DateTime"),
    ),
    "category": (
        col("id", "String", "PK"),
        col("parent_id", "String", "FK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("status", "String"),
    ),
    "brand": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String", "UK"),
        col("is_active", "Boolean"),
    ),
    "brand_category": (
        col("brand_id", "String", "PK", "FK"),
        col("category_id", "String", "PK", "FK"),
    ),
    "warranty_policy": (
        col("id", "String", "PK"),
        col("name", "String"),
        col("warranty_months", "Integer"),
        col("one_for_one_days", "Integer"),
    ),
    "product": (
        col("id", "String", "PK"),
        col("category_id", "String", "FK"),
        col("brand_id", "String", "FK"),
        col("warranty_policy_id", "String", "FK"),
        col("sku", "String", "UK"),
        col("name", "String"),
        col("description", "Text"),
        col("base_price", "Decimal"),
        col("status", "String"),
    ),
    "product_variant": (
        col("id", "String", "PK"),
        col("product_id", "String", "FK"),
        col("sku", "String", "UK"),
        col("price", "Decimal"),
        col("status", "String"),
    ),
    "product_attribute": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("data_type", "String"),
    ),
    "attribute_value": (
        col("id", "String", "PK"),
        col("attribute_id", "String", "FK"),
        col("value", "String"),
    ),
    "variant_attribute_value": (
        col("variant_id", "String", "PK", "FK"),
        col("attribute_value_id", "String", "PK", "FK"),
    ),
    "media_asset": (
        col("id", "String", "PK"),
        col("url", "String", "UK"),
        col("media_type", "String"),
        col("alt_text", "String"),
    ),
    "product_media": (
        col("product_id", "String", "PK", "FK"),
        col("media_asset_id", "String", "PK", "FK"),
        col("sort_order", "Integer"),
        col("is_primary", "Boolean"),
    ),
    "supplier": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("status", "String"),
    ),
    "supplier_contact": (
        col("id", "String", "PK"),
        col("supplier_id", "String", "FK"),
        col("contact_name", "String"),
        col("phone", "String"),
        col("email", "String"),
        col("is_primary", "Boolean"),
    ),
    "purchase_order": (
        col("id", "String", "PK"),
        col("supplier_id", "String", "FK"),
        col("created_by_user_id", "String", "FK"),
        col("approved_by_user_id", "String", "FK"),
        col("code", "String", "UK"),
        col("status", "String"),
        col("expected_date", "Date"),
        col("created_at", "DateTime"),
    ),
    "purchase_order_item": (
        col("id", "String", "PK"),
        col("purchase_order_id", "String", "FK"),
        col("variant_id", "String", "FK"),
        col("ordered_quantity", "Integer"),
        col("received_quantity", "Integer"),
        col("unit_cost", "Decimal"),
    ),
    "inventory_location": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("location_type", "String"),
        col("status", "String"),
    ),
    "inventory_lot": (
        col("id", "String", "PK"),
        col("purchase_order_item_id", "String", "FK"),
        col("location_id", "String", "FK"),
        col("lot_code", "String", "UK"),
        col("received_quantity", "Integer"),
        col("unit_cost", "Decimal"),
        col("received_at", "DateTime"),
    ),
    "inventory_balance": (
        col("variant_id", "String", "PK", "FK"),
        col("location_id", "String", "PK", "FK"),
        col("on_hand_quantity", "Integer"),
        col("reserved_quantity", "Integer"),
        col("safety_stock_quantity", "Integer"),
    ),
    "inventory_identifier": (
        col("id", "String", "PK"),
        col("lot_id", "String", "FK"),
        col("location_id", "String", "FK"),
        col("identifier_type", "String"),
        col("identifier_value", "String", "UK"),
        col("status", "String"),
    ),
    "inventory_transaction": (
        col("id", "String", "PK"),
        col("variant_id", "String", "FK"),
        col("location_id", "String", "FK"),
        col("lot_id", "String", "FK"),
        col("identifier_id", "String", "FK"),
        col("movement_type", "String"),
        col("quantity", "Integer"),
        col("occurred_at", "DateTime"),
    ),
    "sales_order": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("order_code", "String", "UK"),
        col("status", "String"),
        col("ordered_at", "DateTime"),
        col("subtotal_amount", "Decimal"),
        col("discount_amount", "Decimal"),
        col("shipping_fee", "Decimal"),
        col("total_amount", "Decimal"),
    ),
    "sales_order_address": (
        col("sales_order_id", "String", "PK", "FK"),
        col("recipient_name", "String"),
        col("recipient_phone", "String"),
        col("address_line", "Text"),
    ),
    "sales_order_item": (
        col("id", "String", "PK"),
        col("sales_order_id", "String", "FK"),
        col("variant_id", "String", "FK"),
        col("quantity", "Integer"),
        col("unit_price", "Decimal"),
        col("discount_amount", "Decimal"),
        col("total_amount", "Decimal"),
    ),
    "payment_method": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("name", "String"),
        col("status", "String"),
    ),
    "payment_transaction": (
        col("id", "String", "PK"),
        col("sales_order_id", "String", "FK"),
        col("payment_method_id", "String", "FK"),
        col("amount", "Decimal"),
        col("status", "String"),
        col("provider_reference", "String"),
        col("paid_at", "DateTime"),
    ),
    "shipment": (
        col("id", "String", "PK"),
        col("sales_order_id", "String", "FK"),
        col("carrier", "String"),
        col("tracking_code", "String"),
        col("status", "String"),
        col("shipped_at", "DateTime"),
        col("delivered_at", "DateTime"),
    ),
    "shipment_item": (
        col("shipment_id", "String", "PK", "FK"),
        col("sales_order_item_id", "String", "PK", "FK"),
        col("quantity", "Integer"),
    ),
    "voucher": (
        col("id", "String", "PK"),
        col("code", "String", "UK"),
        col("discount_type", "String"),
        col("discount_value", "Decimal"),
        col("minimum_order_value", "Decimal"),
        col("maximum_discount", "Decimal"),
        col("usage_limit", "Integer"),
        col("starts_at", "DateTime"),
        col("ends_at", "DateTime"),
        col("status", "String"),
    ),
    "user_voucher": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("voucher_id", "String", "FK"),
        col("claimed_at", "DateTime"),
        col("expires_at", "DateTime"),
        col("status", "String"),
    ),
    "voucher_redemption": (
        col("id", "String", "PK"),
        col("user_voucher_id", "String", "FK"),
        col("sales_order_id", "String", "FK"),
        col("discount_amount", "Decimal"),
        col("redeemed_at", "DateTime"),
    ),
    "voucher_product": (
        col("voucher_id", "String", "PK", "FK"),
        col("product_id", "String", "PK", "FK"),
        col("is_included", "Boolean"),
    ),
    "voucher_category": (
        col("voucher_id", "String", "PK", "FK"),
        col("category_id", "String", "PK", "FK"),
        col("is_included", "Boolean"),
    ),
    "voucher_brand": (
        col("voucher_id", "String", "PK", "FK"),
        col("brand_id", "String", "PK", "FK"),
        col("is_included", "Boolean"),
    ),
    "voucher_payment_method": (
        col("voucher_id", "String", "PK", "FK"),
        col("payment_method_id", "String", "PK", "FK"),
    ),
    "voucher_loyalty_tier": (
        col("voucher_id", "String", "PK", "FK"),
        col("loyalty_tier_id", "String", "PK", "FK"),
    ),
    "return_request": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("sales_order_id", "String", "FK"),
        col("request_code", "String", "UK"),
        col("status", "String"),
        col("reason", "Text"),
        col("resolution_type", "String"),
        col("created_at", "DateTime"),
    ),
    "return_request_item": (
        col("id", "String", "PK"),
        col("return_request_id", "String", "FK"),
        col("sales_order_item_id", "String", "FK"),
        col("quantity", "Integer"),
        col("reason", "Text"),
        col("refundable_amount", "Decimal"),
    ),
    "return_item_identifier": (
        col("return_request_item_id", "String", "PK", "FK"),
        col("inventory_identifier_id", "String", "PK", "FK"),
    ),
    "refund_transaction": (
        col("id", "String", "PK"),
        col("return_request_id", "String", "FK"),
        col("payment_transaction_id", "String", "FK"),
        col("amount", "Decimal"),
        col("status", "String"),
        col("processed_at", "DateTime"),
    ),
    "warranty_request": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("sales_order_id", "String", "FK"),
        col("request_code", "String", "UK"),
        col("status", "String"),
        col("reason", "Text"),
        col("resolution_type", "String"),
        col("created_at", "DateTime"),
    ),
    "warranty_request_item": (
        col("id", "String", "PK"),
        col("warranty_request_id", "String", "FK"),
        col("sales_order_item_id", "String", "FK"),
        col("quantity", "Integer"),
        col("diagnosis", "Text"),
        col("resolution", "String"),
    ),
    "warranty_item_identifier": (
        col("warranty_request_item_id", "String", "PK", "FK"),
        col("inventory_identifier_id", "String", "PK", "FK"),
    ),
    "loyalty_transaction": (
        col("id", "String", "PK"),
        col("loyalty_account_id", "String", "FK"),
        col("sales_order_id", "String", "FK"),
        col("transaction_type", "String"),
        col("points", "Integer"),
        col("balance_after", "Integer"),
        col("occurred_at", "DateTime"),
    ),
    "loyalty_point_lot": (
        col("id", "String", "PK"),
        col("loyalty_account_id", "String", "FK"),
        col("source_transaction_id", "String", "FK"),
        col("original_points", "Integer"),
        col("remaining_points", "Integer"),
        col("earned_at", "DateTime"),
        col("expires_at", "DateTime"),
    ),
    "loyalty_point_allocation": (
        col("transaction_id", "String", "PK", "FK"),
        col("point_lot_id", "String", "PK", "FK"),
        col("points", "Integer"),
    ),
    "product_review": (
        col("id", "String", "PK"),
        col("user_id", "String", "FK"),
        col("sales_order_item_id", "String", "FK", "UK"),
        col("rating", "Integer"),
        col("comment", "Text"),
        col("status", "String"),
        col("created_at", "DateTime"),
    ),
    "review_media": (
        col("product_review_id", "String", "PK", "FK"),
        col("media_asset_id", "String", "PK", "FK"),
        col("sort_order", "Integer"),
    ),
}


def ep(
    name: str,
    x: int,
    y: int,
    kind: str = "entity",
    fields: tuple[str, ...] | None = None,
) -> EntityPlacement:
    return EntityPlacement(name, x, y, kind, fields)


def rel(
    parent: str,
    child: str,
    child_column: str,
    *,
    parent_column: str = "id",
    parent_cardinality: str = "one",
    child_cardinality: str = "zero_many",
    waypoints: tuple[tuple[int, int], ...] | None = None,
) -> Relationship:
    return Relationship(
        parent,
        parent_column,
        child,
        child_column,
        parent_cardinality,
        child_cardinality,
        waypoints,
    )


PAGES = [
    (
        "01 - Định danh và khách hàng",
        [
            ep("role", 40, 100),
            ep("permission", 40, 330),
            ep("customer_tag", 40, 590),
            ep("loyalty_tier", 40, 850),
            ep("user", 420, 120),
            ep("role_permission", 420, 430, "associative"),
            ep("user_address", 820, 100),
            ep("user_tag", 820, 470, "associative"),
            ep("loyalty_account", 820, 760),
        ],
        [
            rel("role", "user", "role_id"),
            rel("role", "role_permission", "role_id"),
            rel("permission", "role_permission", "permission_id"),
            rel("user", "user_address", "user_id"),
            rel("user", "user_tag", "user_id"),
            rel("customer_tag", "user_tag", "tag_id"),
            rel("user", "loyalty_account", "user_id", child_cardinality="zero_one"),
            rel("loyalty_tier", "loyalty_account", "tier_id"),
        ],
    ),
    (
        "02 - Danh mục sản phẩm",
        [
            ep("category", 40, 100),
            ep("brand", 40, 380),
            ep("warranty_policy", 40, 650),
            ep("product_attribute", 40, 930),
            ep("media_asset", 40, 1210),
            ep("brand_category", 420, 250, "associative"),
            ep("product", 420, 560),
            ep("attribute_value", 420, 980),
            ep("product_variant", 820, 520),
            ep("product_media", 820, 1190, "associative"),
            ep("variant_attribute_value", 1180, 830, "associative"),
        ],
        [
            rel("category", "category", "parent_id", parent_cardinality="zero_one"),
            rel("category", "brand_category", "category_id"),
            rel("brand", "brand_category", "brand_id"),
            rel("category", "product", "category_id"),
            rel("brand", "product", "brand_id"),
            rel("warranty_policy", "product", "warranty_policy_id"),
            rel("product", "product_variant", "product_id", child_cardinality="one_many"),
            rel("product_attribute", "attribute_value", "attribute_id", child_cardinality="one_many"),
            rel("product_variant", "variant_attribute_value", "variant_id"),
            rel("attribute_value", "variant_attribute_value", "attribute_value_id"),
            rel("product", "product_media", "product_id"),
            rel("media_asset", "product_media", "media_asset_id"),
        ],
    ),
    (
        "03 - Thu mua",
        [
            ep("supplier", 40, 100),
            ep("user", 40, 390, fields=("id", "email", "full_name", "status")),
            ep("product_variant", 40, 720, fields=("id", "product_id", "sku", "price", "status")),
            ep("inventory_location", 40, 1020),
            ep("supplier_contact", 420, 80),
            ep("purchase_order", 420, 380),
            ep("purchase_order_item", 820, 560),
            ep("inventory_lot", 1200, 760),
        ],
        [
            rel("supplier", "supplier_contact", "supplier_id", child_cardinality="one_many"),
            rel("supplier", "purchase_order", "supplier_id"),
            rel("user", "purchase_order", "created_by_user_id"),
            rel("user", "purchase_order", "approved_by_user_id", parent_cardinality="zero_one"),
            rel("purchase_order", "purchase_order_item", "purchase_order_id", child_cardinality="one_many"),
            rel("product_variant", "purchase_order_item", "variant_id"),
            rel("purchase_order_item", "inventory_lot", "purchase_order_item_id"),
            rel("inventory_location", "inventory_lot", "location_id"),
        ],
    ),
    (
        "04 - Kho và định danh",
        [
            ep("product_variant", 40, 100, fields=("id", "product_id", "sku", "price", "status")),
            ep("inventory_location", 40, 430),
            ep("inventory_lot", 40, 780),
            ep("inventory_balance", 460, 180),
            ep("inventory_identifier", 460, 600),
            ep("inventory_transaction", 940, 380),
        ],
        [
            rel("product_variant", "inventory_balance", "variant_id"),
            rel("inventory_location", "inventory_balance", "location_id"),
            rel("inventory_lot", "inventory_identifier", "lot_id"),
            rel("inventory_location", "inventory_identifier", "location_id"),
            rel(
                "product_variant",
                "inventory_transaction",
                "variant_id",
                waypoints=((360, 153), (360, 130), (860, 130), (860, 456)),
            ),
            rel("inventory_location", "inventory_transaction", "location_id"),
            rel(
                "inventory_lot",
                "inventory_transaction",
                "lot_id",
                parent_cardinality="zero_one",
                waypoints=((380, 833), (380, 960), (860, 960), (860, 512)),
            ),
            rel("inventory_identifier", "inventory_transaction", "identifier_id", parent_cardinality="zero_one"),
        ],
    ),
    (
        "05 - Bán hàng và thanh toán",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("product_variant", 40, 430, fields=("id", "product_id", "sku", "price", "status")),
            ep("payment_method", 40, 760),
            ep("sales_order", 420, 180),
            ep("sales_order_address", 820, 80, "detail"),
            ep("sales_order_item", 820, 400, "detail"),
            ep("payment_transaction", 820, 760),
            ep("shipment", 820, 1080),
            ep("shipment_item", 1200, 980, "associative"),
        ],
        [
            rel("user", "sales_order", "user_id", parent_cardinality="zero_one"),
            rel("sales_order", "sales_order_address", "sales_order_id", child_cardinality="one"),
            rel("sales_order", "sales_order_item", "sales_order_id", child_cardinality="one_many"),
            rel("product_variant", "sales_order_item", "variant_id"),
            rel("sales_order", "payment_transaction", "sales_order_id"),
            rel("payment_method", "payment_transaction", "payment_method_id"),
            rel("sales_order", "shipment", "sales_order_id"),
            rel("shipment", "shipment_item", "shipment_id", child_cardinality="one_many"),
            rel("sales_order_item", "shipment_item", "sales_order_item_id"),
        ],
    ),
    (
        "06 - Tiếp nhận và sử dụng voucher",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("voucher", 40, 430),
            ep("sales_order", 40, 860, fields=("id", "user_id", "order_code", "status", "total_amount")),
            ep("user_voucher", 480, 300),
            ep("voucher_redemption", 920, 520),
        ],
        [
            rel("user", "user_voucher", "user_id"),
            rel("voucher", "user_voucher", "voucher_id"),
            rel("user_voucher", "voucher_redemption", "user_voucher_id", child_cardinality="zero_one"),
            rel("sales_order", "voucher_redemption", "sales_order_id"),
        ],
    ),
    (
        "07 - Phạm vi áp dụng voucher",
        [
            ep("voucher", 40, 480),
            ep("voucher_product", 480, 100, "associative"),
            ep("voucher_category", 480, 350, "associative"),
            ep("voucher_brand", 480, 600, "associative"),
            ep("voucher_payment_method", 480, 850, "associative"),
            ep("voucher_loyalty_tier", 480, 1100, "associative"),
            ep("product", 900, 80, fields=("id", "sku", "name", "status")),
            ep("category", 900, 340, fields=("id", "code", "name", "status")),
            ep("brand", 900, 600),
            ep("payment_method", 900, 850),
            ep("loyalty_tier", 900, 1100),
        ],
        [
            rel("voucher", "voucher_product", "voucher_id"),
            rel("product", "voucher_product", "product_id"),
            rel("voucher", "voucher_category", "voucher_id"),
            rel("category", "voucher_category", "category_id"),
            rel("voucher", "voucher_brand", "voucher_id"),
            rel("brand", "voucher_brand", "brand_id"),
            rel("voucher", "voucher_payment_method", "voucher_id"),
            rel("payment_method", "voucher_payment_method", "payment_method_id"),
            rel("voucher", "voucher_loyalty_tier", "voucher_id"),
            rel("loyalty_tier", "voucher_loyalty_tier", "loyalty_tier_id"),
        ],
    ),
    (
        "08 - Đổi trả và hoàn tiền",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("sales_order", 40, 370, fields=("id", "user_id", "order_code", "status", "total_amount")),
            ep("sales_order_item", 40, 700),
            ep("inventory_identifier", 40, 1080, fields=("id", "lot_id", "identifier_type", "identifier_value", "status")),
            ep("payment_transaction", 40, 1410, fields=("id", "sales_order_id", "amount", "status", "provider_reference")),
            ep("return_request", 480, 260),
            ep("return_request_item", 900, 670, "detail"),
            ep("return_item_identifier", 1300, 1010, "associative"),
            ep("refund_transaction", 900, 1320),
        ],
        [
            rel("user", "return_request", "user_id"),
            rel("sales_order", "return_request", "sales_order_id"),
            rel("return_request", "return_request_item", "return_request_id", child_cardinality="one_many"),
            rel("sales_order_item", "return_request_item", "sales_order_item_id"),
            rel("return_request_item", "return_item_identifier", "return_request_item_id"),
            rel("inventory_identifier", "return_item_identifier", "inventory_identifier_id"),
            rel("return_request", "refund_transaction", "return_request_id"),
            rel("payment_transaction", "refund_transaction", "payment_transaction_id"),
        ],
    ),
    (
        "09 - Bảo hành",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("sales_order", 40, 390, fields=("id", "user_id", "order_code", "status", "total_amount")),
            ep("sales_order_item", 40, 730),
            ep("inventory_identifier", 40, 1110, fields=("id", "lot_id", "identifier_type", "identifier_value", "status")),
            ep("warranty_request", 480, 300),
            ep("warranty_request_item", 900, 700, "detail"),
            ep("warranty_item_identifier", 1300, 1040, "associative"),
        ],
        [
            rel("user", "warranty_request", "user_id"),
            rel("sales_order", "warranty_request", "sales_order_id"),
            rel("warranty_request", "warranty_request_item", "warranty_request_id", child_cardinality="one_many"),
            rel("sales_order_item", "warranty_request_item", "sales_order_item_id"),
            rel("warranty_request_item", "warranty_item_identifier", "warranty_request_item_id"),
            rel("inventory_identifier", "warranty_item_identifier", "inventory_identifier_id"),
        ],
    ),
    (
        "10 - Khách hàng thân thiết",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("loyalty_tier", 40, 390),
            ep("sales_order", 40, 690, fields=("id", "user_id", "order_code", "status", "total_amount")),
            ep("loyalty_account", 440, 220),
            ep("loyalty_transaction", 840, 480),
            ep("loyalty_point_lot", 1240, 300),
            ep("loyalty_point_allocation", 1640, 600, "associative"),
        ],
        [
            rel("user", "loyalty_account", "user_id", child_cardinality="zero_one"),
            rel("loyalty_tier", "loyalty_account", "tier_id"),
            rel("loyalty_account", "loyalty_transaction", "loyalty_account_id"),
            rel("sales_order", "loyalty_transaction", "sales_order_id", parent_cardinality="zero_one"),
            rel("loyalty_account", "loyalty_point_lot", "loyalty_account_id"),
            rel("loyalty_transaction", "loyalty_point_lot", "source_transaction_id"),
            rel("loyalty_transaction", "loyalty_point_allocation", "transaction_id"),
            rel("loyalty_point_lot", "loyalty_point_allocation", "point_lot_id"),
        ],
    ),
    (
        "11 - Đánh giá sản phẩm",
        [
            ep("user", 40, 100, fields=("id", "email", "full_name", "status")),
            ep("sales_order_item", 40, 390, fields=("id", "sales_order_id", "variant_id", "quantity", "total_amount")),
            ep("media_asset", 40, 730),
            ep("product_review", 480, 300),
            ep("review_media", 900, 600, "associative"),
        ],
        [
            rel("user", "product_review", "user_id"),
            rel("sales_order_item", "product_review", "sales_order_item_id", child_cardinality="zero_one"),
            rel("product_review", "review_media", "product_review_id"),
            rel("media_asset", "review_media", "media_asset_id"),
        ],
    ),
]


CARDINALITY_ARROWS = {
    "one": "ERmandOne",
    "zero_one": "ERzeroToOne",
    "one_many": "ERoneToMany",
    "zero_many": "ERzeroToMany",
}


def visible_columns(placement: EntityPlacement) -> tuple[Column, ...]:
    columns = SCHEMAS[placement.name]
    if placement.fields is None:
        return columns
    by_name = {column.name: column for column in columns}
    return tuple(by_name[name] for name in placement.fields)


def add_geometry(
    parent: ET.Element,
    *,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    relative: bool = False,
) -> ET.Element:
    attrs = {"as": "geometry"}
    if x is not None:
        attrs["x"] = str(x)
    if y is not None:
        attrs["y"] = str(y)
    if width is not None:
        attrs["width"] = str(width)
    if height is not None:
        attrs["height"] = str(height)
    if relative:
        attrs["relative"] = "1"
    return ET.SubElement(parent, "mxGeometry", attrs)


def row_label(column: Column) -> str:
    key_text = ", ".join(column.keys)
    key_prefix = f"<b>{key_text}</b>&nbsp;&nbsp;" if key_text else "&nbsp;&nbsp;&nbsp;&nbsp;"
    return (
        f"{key_prefix}{column.name}"
        f"&nbsp;&nbsp;<font color=\"#666666\">: {column.data_type}</font>"
    )


def build_page(
    page_number: int,
    page_name: str,
    placements: list[EntityPlacement],
    relationships: list[Relationship],
) -> ET.Element:
    diagram = ET.Element(
        "diagram",
        {"id": f"logical-page-{page_number}", "name": page_name},
    )
    graph = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1422",
            "dy": "794",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "0",
            "pageScale": "1",
            "pageWidth": "2100",
            "pageHeight": "1400",
            "math": "0",
            "shadow": "0",
            "background": "#FFFFFF",
        },
    )
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"p{page_number}-title",
            "value": (
                f"<b>LOGICAL ERD — {page_name}</b><br>"
                "<font color=\"#666666\" size=\"2\">"
                "Chuẩn 3NF • Kiểu dữ liệu trừu tượng • Crow's Foot"
                "</font>"
            ),
            "style": (
                "text;html=1;strokeColor=none;fillColor=none;align=left;"
                "verticalAlign=middle;whiteSpace=wrap;fontSize=18;fontFamily=Arial;"
            ),
            "vertex": "1",
            "parent": "1",
        },
    )
    add_geometry(title, x=40, y=20, width=900, height=60)

    placement_map = {placement.name: placement for placement in placements}
    row_ids: dict[tuple[str, str], str] = {}
    row_indexes: dict[tuple[str, str], int] = {}

    for placement in placements:
        columns = visible_columns(placement)
        table_id = f"p{page_number}-table-{placement.name}"
        is_associative = placement.kind == "associative"
        fill_color = "#d5e8d4" if is_associative else "#dae8fc"
        stroke_color = "#82b366" if is_associative else "#6c8ebf"
        height = HEADER_HEIGHT + len(columns) * ROW_HEIGHT
        table = ET.SubElement(
            root,
            "mxCell",
            {
                "id": table_id,
                "value": placement.name,
                "style": (
                    "shape=table;startSize=34;container=1;collapsible=0;"
                    "childLayout=tableLayout;fixedRows=1;rowLines=1;html=1;"
                    f"fillColor={fill_color};strokeColor={stroke_color};"
                    "fontStyle=1;fontSize=14;fontFamily=Arial;align=center;"
                    "verticalAlign=middle;whiteSpace=wrap;"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        add_geometry(
            table,
            x=placement.x,
            y=placement.y,
            width=TABLE_WIDTH,
            height=height,
        )

        for index, column in enumerate(columns):
            row_id = f"p{page_number}-row-{placement.name}-{column.name}"
            row_ids[(placement.name, column.name)] = row_id
            row_indexes[(placement.name, column.name)] = index
            row = ET.SubElement(
                root,
                "mxCell",
                {
                    "id": row_id,
                    "value": row_label(column),
                    "style": (
                        "shape=tableRow;horizontal=1;startSize=0;swimlaneHead=0;"
                        "swimlaneBody=0;fillColor=#FFFFFF;collapsible=0;dropTarget=0;"
                        "points=[[0,0.5],[1,0.5]];portConstraint=eastwest;"
                        "html=1;fontSize=11;fontFamily=Arial;align=left;"
                        "spacingLeft=8;verticalAlign=middle;whiteSpace=wrap;"
                        f"strokeColor={stroke_color};"
                    ),
                    "vertex": "1",
                    "parent": table_id,
                },
            )
            add_geometry(
                row,
                x=0,
                y=HEADER_HEIGHT + index * ROW_HEIGHT,
                width=TABLE_WIDTH,
                height=ROW_HEIGHT,
            )

    endpoint_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    sides: dict[tuple[int, str], str] = {}
    for index, relationship in enumerate(relationships):
        if relationship.parent not in placement_map or relationship.child not in placement_map:
            raise ValueError(f"Quan hệ tham chiếu thực thể không có trên trang: {relationship}")
        if (relationship.parent, relationship.parent_column) not in row_ids:
            raise ValueError(f"Thiếu cột nguồn trên trang: {relationship}")
        if (relationship.child, relationship.child_column) not in row_ids:
            raise ValueError(f"Thiếu cột đích trên trang: {relationship}")

        parent_x = placement_map[relationship.parent].x
        child_x = placement_map[relationship.child].x
        if relationship.parent == relationship.child:
            source_side = target_side = "right"
        elif parent_x <= child_x:
            source_side, target_side = "right", "left"
        else:
            source_side, target_side = "left", "right"
        sides[(index, "source")] = source_side
        sides[(index, "target")] = target_side
        endpoint_groups[
            (relationship.parent, relationship.parent_column, source_side)
        ].append(index)
        endpoint_groups[
            (relationship.child, relationship.child_column, target_side)
        ].append(index)

    endpoint_fraction: dict[tuple[int, str], float] = {}
    for group, indexes in endpoint_groups.items():
        for position, relationship_index in enumerate(indexes, start=1):
            fraction = position / (len(indexes) + 1)
            relationship = relationships[relationship_index]
            endpoint = "source" if group[0] == relationship.parent and group[1] == relationship.parent_column else "target"
            endpoint_fraction[(relationship_index, endpoint)] = fraction

    for index, relationship in enumerate(relationships):
        source_placement = placement_map[relationship.parent]
        target_placement = placement_map[relationship.child]
        source_row_index = row_indexes[(relationship.parent, relationship.parent_column)]
        target_row_index = row_indexes[(relationship.child, relationship.child_column)]
        source_fraction = endpoint_fraction.get((index, "source"), 0.5)
        target_fraction = endpoint_fraction.get((index, "target"), 0.5)
        source_y = (
            source_placement.y
            + HEADER_HEIGHT
            + source_row_index * ROW_HEIGHT
            + source_fraction * ROW_HEIGHT
        )
        target_y = (
            target_placement.y
            + HEADER_HEIGHT
            + target_row_index * ROW_HEIGHT
            + target_fraction * ROW_HEIGHT
        )

        source_side = sides[(index, "source")]
        target_side = sides[(index, "target")]
        source_x = source_placement.x + (TABLE_WIDTH if source_side == "right" else 0)
        target_x = target_placement.x + (TABLE_WIDTH if target_side == "right" else 0)
        if relationship.parent == relationship.child:
            corridor_x = source_placement.x + TABLE_WIDTH + 100
        else:
            corridor_x = round(((source_x + target_x) / 2) / 10) * 10

        source_exit_x = "1" if source_side == "right" else "0"
        target_entry_x = "1" if target_side == "right" else "0"
        edge = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"p{page_number}-edge-{index + 1}",
                "value": "",
                "style": (
                    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                    "jettySize=auto;html=1;strokeColor=#444444;strokeWidth=1.4;"
                    f"startArrow={CARDINALITY_ARROWS[relationship.parent_cardinality]};"
                    f"endArrow={CARDINALITY_ARROWS[relationship.child_cardinality]};"
                    "startSize=16;endSize=16;"
                    f"exitX={source_exit_x};exitY={source_fraction:.3f};exitDx=0;exitDy=0;"
                    f"entryX={target_entry_x};entryY={target_fraction:.3f};entryDx=0;entryDy=0;"
                ),
                "edge": "1",
                "parent": "1",
                "source": row_ids[(relationship.parent, relationship.parent_column)],
                "target": row_ids[(relationship.child, relationship.child_column)],
            },
        )
        geometry = add_geometry(edge, relative=True)
        points = ET.SubElement(geometry, "Array", {"as": "points"})
        route_points = relationship.waypoints or (
            (corridor_x, round(source_y)),
            (corridor_x, round(target_y)),
        )
        for point_x, point_y in route_points:
            ET.SubElement(points, "mxPoint", {"x": str(point_x), "y": str(point_y)})

    max_bottom = max(
        placement.y + HEADER_HEIGHT + len(visible_columns(placement)) * ROW_HEIGHT
        for placement in placements
    )
    route_bottom = max(
        (
            point_y
            for relationship in relationships
            for _, point_y in (relationship.waypoints or ())
        ),
        default=0,
    )
    legend = ET.SubElement(
        root,
        "mxCell",
        {
            "id": f"p{page_number}-legend",
            "value": (
                "<b>Ký hiệu:</b>&nbsp;&nbsp; PK = Khóa chính&nbsp;&nbsp;•&nbsp;&nbsp;"
                "FK = Khóa ngoại&nbsp;&nbsp;•&nbsp;&nbsp; UK = Khóa duy nhất"
                "<br><b>Crow's Foot:</b>&nbsp;&nbsp; || = 1..1&nbsp;&nbsp;•&nbsp;&nbsp;"
                "|O = 0..1&nbsp;&nbsp;•&nbsp;&nbsp; |&lt; = 1..N&nbsp;&nbsp;•&nbsp;&nbsp;"
                "O&lt; = 0..N"
            ),
            "style": (
                "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;"
                "strokeColor=#b3b3b3;fontSize=11;fontFamily=Arial;"
                "align=left;verticalAlign=middle;spacingLeft=10;"
            ),
            "vertex": "1",
            "parent": "1",
        },
    )
    add_geometry(
        legend,
        x=40,
        y=max(max_bottom, route_bottom) + 50,
        width=780,
        height=64,
    )
    return diagram


def main() -> None:
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Electron",
            "agent": "Codex",
            "version": "30.3.6",
            "pages": str(len(PAGES)),
        },
    )
    for page_number, (page_name, placements, relationships) in enumerate(PAGES, start=1):
        mxfile.append(build_page(page_number, page_name, placements, relationships))

    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(
        OUTPUT_PATH,
        encoding="utf-8",
        xml_declaration=True,
    )
    print(f"Created {OUTPUT_PATH}")
    print(f"Pages: {len(PAGES)}")
    print(f"Unique entities: {len(SCHEMAS)}")


if __name__ == "__main__":
    main()
