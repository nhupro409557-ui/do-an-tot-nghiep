"""Sinh bản Logical ERD toàn hệ thống trên một trang draw.io."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

from generate_enterprise_logical_erd import (
    PAGES,
    SCHEMAS,
    HEADER_HEIGHT,
    ROW_HEIGHT,
    TABLE_WIDTH,
    EntityPlacement,
    Relationship,
    build_page,
)


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "logical_erd_enterprise_full.drawio"

X_STEP = 360


def row(entity_names: tuple[str, ...], y: int) -> list[EntityPlacement]:
    return [
        EntityPlacement(name=name, x=40 + index * X_STEP, y=y)
        for index, name in enumerate(entity_names)
    ]


SUBJECT_ROWS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    (
        "Định danh và khách hàng",
        130,
        (
            "role",
            "permission",
            "role_permission",
            "user",
            "user_address",
            "customer_tag",
            "user_tag",
            "loyalty_tier",
            "loyalty_account",
        ),
    ),
    (
        "Danh mục sản phẩm",
        620,
        (
            "category",
            "brand",
            "brand_category",
            "warranty_policy",
            "product",
            "product_variant",
            "product_attribute",
            "attribute_value",
            "variant_attribute_value",
            "media_asset",
            "product_media",
        ),
    ),
    (
        "Thu mua, kho và định danh",
        1160,
        (
            "supplier",
            "supplier_contact",
            "purchase_order",
            "purchase_order_item",
            "inventory_lot",
            "inventory_location",
            "inventory_identifier",
            "inventory_balance",
            "inventory_transaction",
        ),
    ),
    (
        "Bán hàng, thanh toán, giao vận và sử dụng voucher",
        1710,
        (
            "sales_order",
            "sales_order_address",
            "sales_order_item",
            "payment_method",
            "payment_transaction",
            "shipment",
            "shipment_item",
            "voucher",
            "user_voucher",
            "voucher_redemption",
        ),
    ),
    (
        "Phạm vi voucher, đổi trả và hoàn tiền",
        2310,
        (
            "voucher_product",
            "voucher_category",
            "voucher_brand",
            "voucher_payment_method",
            "voucher_loyalty_tier",
            "return_request",
            "return_request_item",
            "return_item_identifier",
            "refund_transaction",
        ),
    ),
    (
        "Bảo hành, khách hàng thân thiết và đánh giá",
        2870,
        (
            "warranty_request",
            "warranty_request_item",
            "warranty_item_identifier",
            "loyalty_transaction",
            "loyalty_point_lot",
            "loyalty_point_allocation",
            "product_review",
            "review_media",
        ),
    ),
)


ASSOCIATIVE_ENTITIES = {
    "role_permission",
    "user_tag",
    "brand_category",
    "variant_attribute_value",
    "product_media",
    "shipment_item",
    "voucher_product",
    "voucher_category",
    "voucher_brand",
    "voucher_payment_method",
    "voucher_loyalty_tier",
    "return_item_identifier",
    "warranty_item_identifier",
    "loyalty_point_allocation",
    "review_media",
}


def placements() -> list[EntityPlacement]:
    result: list[EntityPlacement] = []
    for _, y, names in SUBJECT_ROWS:
        for placement in row(names, y):
            if placement.name in ASSOCIATIVE_ENTITIES:
                placement = replace(placement, kind="associative")
            result.append(placement)

    placed_names = {placement.name for placement in result}
    missing = set(SCHEMAS) - placed_names
    extra = placed_names - set(SCHEMAS)
    if missing or extra:
        raise ValueError(f"Sai danh sách thực thể. Thiếu={sorted(missing)}, dư={sorted(extra)}")
    return result


def relationships() -> list[Relationship]:
    unique: dict[tuple[str, str, str, str], Relationship] = {}
    for _, _, page_relationships in PAGES:
        for relationship in page_relationships:
            key = (
                relationship.parent,
                relationship.parent_column,
                relationship.child,
                relationship.child_column,
            )
            unique.setdefault(key, replace(relationship, waypoints=None))
    return list(unique.values())


def routed_relationships(
    all_placements: list[EntityPlacement],
    all_relationships: list[Relationship],
) -> list[Relationship]:
    placement_map = {placement.name: placement for placement in all_placements}
    band_y_by_entity = {
        name: y
        for _, y, names in SUBJECT_ROWS
        for name in names
    }
    band_bottom = {
        y: max(
            y + HEADER_HEIGHT + len(SCHEMAS[name]) * ROW_HEIGHT
            for name in names
        )
        for _, y, names in SUBJECT_ROWS
    }

    sides: dict[tuple[int, str], str] = {}
    endpoint_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, relationship in enumerate(all_relationships):
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
        endpoint_groups[(relationship.parent, relationship.parent_column, source_side)].append(index)
        endpoint_groups[(relationship.child, relationship.child_column, target_side)].append(index)

    fractions: dict[tuple[int, str], float] = {}
    for (entity, column, _), indexes in endpoint_groups.items():
        for position, relationship_index in enumerate(indexes, start=1):
            fraction = position / (len(indexes) + 1)
            relationship = all_relationships[relationship_index]
            endpoint = (
                "source"
                if entity == relationship.parent and column == relationship.parent_column
                else "target"
            )
            fractions[(relationship_index, endpoint)] = fraction

    routed: list[Relationship] = []
    lane_offsets = (22, 32, 42, 52, 62)
    gutter_offsets = (34, 46, 58, 70, 82, 94)
    for index, relationship in enumerate(all_relationships):
        source = placement_map[relationship.parent]
        target = placement_map[relationship.child]
        source_side = sides[(index, "source")]
        target_side = sides[(index, "target")]
        source_fraction = fractions.get((index, "source"), 0.5)
        target_fraction = fractions.get((index, "target"), 0.5)
        source_row_index = next(
            position
            for position, column in enumerate(SCHEMAS[relationship.parent])
            if column.name == relationship.parent_column
        )
        target_row_index = next(
            position
            for position, column in enumerate(SCHEMAS[relationship.child])
            if column.name == relationship.child_column
        )
        source_y = round(
            source.y
            + HEADER_HEIGHT
            + source_row_index * ROW_HEIGHT
            + source_fraction * ROW_HEIGHT
        )
        target_y = round(
            target.y
            + HEADER_HEIGHT
            + target_row_index * ROW_HEIGHT
            + target_fraction * ROW_HEIGHT
        )

        lane_offset = lane_offsets[index % len(lane_offsets)]
        source_lane_x = (
            source.x + TABLE_WIDTH + lane_offset
            if source_side == "right"
            else source.x - lane_offset
        )
        target_lane_x = (
            target.x + TABLE_WIDTH + lane_offset
            if target_side == "right"
            else target.x - lane_offset
        )
        source_band_y = band_y_by_entity[relationship.parent]
        target_band_y = band_y_by_entity[relationship.child]
        gutter_offset = gutter_offsets[index % len(gutter_offsets)]
        source_gutter_y = band_bottom[source_band_y] + gutter_offset
        target_gutter_y = band_bottom[target_band_y] + gutter_offset

        waypoints = (
            (source_lane_x, source_y),
            (source_lane_x, source_gutter_y),
            (target_lane_x, source_gutter_y),
            (target_lane_x, target_gutter_y),
            (target_lane_x, target_y),
        )
        routed.append(replace(relationship, waypoints=waypoints))
    return routed


def add_subject_labels(diagram: ET.Element) -> None:
    root = diagram.find("./mxGraphModel/root")
    if root is None:
        raise ValueError("Không tìm thấy mxGraphModel/root")

    for index, (label, y, names) in enumerate(SUBJECT_ROWS, start=1):
        cell = ET.Element(
            "mxCell",
            {
                "id": f"full-subject-label-{index}",
                "value": f"<b>{label}</b>",
                "style": (
                    "text;html=1;strokeColor=none;fillColor=none;align=left;"
                    "verticalAlign=middle;fontSize=15;fontFamily=Arial;fontColor=#315A8A;"
                ),
                "vertex": "1",
                "parent": "1",
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"as": "geometry"})
        geometry.set("x", "40")
        geometry.set("y", str(y - 42))
        geometry.set("width", "260")
        geometry.set("height", "30")
        root.insert(3 + index, cell)


def main() -> None:
    all_placements = placements()
    all_relationships = routed_relationships(all_placements, relationships())
    diagram = build_page(
        1,
        "Toàn bộ hệ thống - Bản chưa phân mảnh",
        all_placements,
        all_relationships,
    )
    add_subject_labels(diagram)

    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Electron",
            "agent": "Codex",
            "version": "30.3.6",
            "pages": "1",
        },
    )
    mxfile.append(diagram)
    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)

    print(f"Created {OUTPUT_PATH}")
    print(f"Entities: {len(all_placements)}")
    print(f"Relationships: {len(all_relationships)}")


if __name__ == "__main__":
    main()
