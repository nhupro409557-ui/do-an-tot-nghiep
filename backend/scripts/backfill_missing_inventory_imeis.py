from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from app.infrastructure.database.session import AsyncSessionFactory


SOURCE_REFERENCE = f"BACKFILL-IMEI-{datetime.utcnow():%Y%m%d}"


def _numeric_seed(value: str) -> str:
    digits = "".join(str(ord(ch) % 10) for ch in value)
    return (digits or "0")[:8]


def _luhn_check_digit(first_14_digits: str) -> str:
    total = 0
    for index, raw_digit in enumerate(first_14_digits):
        digit = int(raw_digit)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - (total % 10)) % 10)


def generate_imei(seed: str, sequence: int) -> str:
    prefix = _numeric_seed(seed)
    body = f"{prefix}{sequence:06d}"[-14:]
    return f"{body}{_luhn_check_digit(body)}"


def generate_serial_number(seed: str, sequence: int) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "", seed.upper())[:28] or "SN"
    return f"SN-{prefix}-{sequence:06d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bổ sung IMEI/serial number còn thiếu cho các dòng inventory_levels đang có tồn."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi dữ liệu thật. Nếu không có cờ này, script chỉ xem trước.",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Bổ sung cả sản phẩm chưa bật policy IMEI. Dùng cho dữ liệu seed/demo đã nhập kho nhưng chưa có IMEI.",
    )
    parser.add_argument(
        "--source-reference",
        default=SOURCE_REFERENCE,
        help="Mã nguồn ghi vào source_reference của IMEI và cặp mã.",
    )
    return parser.parse_args()


async def _existing_imeis(session) -> set[str]:
    rows = (await session.execute(text("SELECT imei FROM product_imeis"))).scalars().all()
    return {str(row) for row in rows}


async def _existing_serial_numbers(session) -> set[tuple[UUID, str]]:
    rows = (
        await session.execute(text("SELECT product_id, serial_number FROM product_serial_numbers"))
    ).mappings().all()
    return {(row["product_id"], str(row["serial_number"])) for row in rows}


async def _candidate_rows(session, include_untracked: bool) -> list[dict]:
    policy_filter = "" if include_untracked else "AND (tracks_imei = TRUE OR tracks_serial_number = TRUE)"
    rows = (
        await session.execute(
            text(
                f"""
                WITH level_rows AS (
                    SELECT
                        COALESCE(il.product_id, v.product_id) AS product_id,
                        il.variant_id,
                        il.location_id,
                        loc.code AS location_code,
                        p.name AS product_name,
                        p.sku AS product_sku,
                        v.sku AS variant_sku,
                        il.on_hand_quantity,
                        CASE
                            WHEN COALESCE(p.sales_config->'imeiPolicy'->>'mode', '') = 'MANUAL'
                                THEN COALESCE((p.sales_config->'imeiPolicy'->>'trackImei')::boolean, FALSE)
                            ELSE COALESCE((c.inventory_policy->>'trackImei')::boolean, FALSE)
                        END AS tracks_imei,
                        CASE
                            WHEN COALESCE(p.sales_config->'serialPolicy'->>'mode', '') = 'MANUAL'
                                THEN COALESCE((p.sales_config->'serialPolicy'->>'trackSerialNumber')::boolean, FALSE)
                            ELSE COALESCE((c.inventory_policy->>'trackSerialNumber')::boolean, FALSE)
                        END AS tracks_serial_number,
                        COALESCE(ic.imei_count, 0) AS imei_count
                        ,COALESCE(sc.serial_count, 0) AS serial_count
                    FROM inventory_levels il
                    LEFT JOIN product_variants v ON v.id = il.variant_id
                    JOIN products p ON p.id = COALESCE(il.product_id, v.product_id)
                    LEFT JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
                    JOIN inventory_locations loc ON loc.id = il.location_id
                    LEFT JOIN (
                        SELECT product_id, variant_id, location_id, COUNT(*)::int AS imei_count
                        FROM product_imeis
                        WHERE status = 'IN_STOCK'
                        GROUP BY product_id, variant_id, location_id
                    ) ic ON ic.product_id = COALESCE(il.product_id, v.product_id)
                        AND ic.variant_id IS NOT DISTINCT FROM il.variant_id
                        AND ic.location_id = il.location_id
                    LEFT JOIN (
                        SELECT product_id, variant_id, location_id, COUNT(*)::int AS serial_count
                        FROM product_serial_numbers
                        WHERE status = 'IN_STOCK'
                        GROUP BY product_id, variant_id, location_id
                    ) sc ON sc.product_id = COALESCE(il.product_id, v.product_id)
                        AND sc.variant_id IS NOT DISTINCT FROM il.variant_id
                        AND sc.location_id = il.location_id
                    WHERE il.on_hand_quantity > 0
                      AND p.deleted_at IS NULL
                )
                SELECT *,
                    GREATEST(on_hand_quantity - imei_count, 0)::int AS missing_imei_count,
                    GREATEST(on_hand_quantity - serial_count, 0)::int AS missing_serial_count
                FROM level_rows
                WHERE (
                    GREATEST(on_hand_quantity - imei_count, 0) > 0
                    OR GREATEST(on_hand_quantity - serial_count, 0) > 0
                )
                {policy_filter}
                ORDER BY product_name, variant_sku NULLS FIRST, location_code
                """
            )
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def _available_serial_numbers(
    session,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    limit: int,
) -> list[str]:
    rows = (
        await session.execute(
            text(
                """
                SELECT psn.serial_number
                FROM product_serial_numbers psn
                LEFT JOIN product_identifier_pairs pair
                    ON pair.product_id = psn.product_id
                    AND pair.serial_number = psn.serial_number
                WHERE psn.product_id = :product_id
                  AND psn.variant_id IS NOT DISTINCT FROM :variant_id
                  AND psn.location_id = :location_id
                  AND psn.status = 'IN_STOCK'
                  AND pair.id IS NULL
                ORDER BY psn.serial_number
                LIMIT :limit
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "limit": limit,
            },
        )
    ).scalars().all()
    return [str(row) for row in rows]


async def main() -> None:
    args = parse_args()
    async with AsyncSessionFactory() as session:
        rows = await _candidate_rows(session, args.include_untracked)
        existing = await _existing_imeis(session)
        existing_serial_numbers = await _existing_serial_numbers(session)
        created_imeis = 0
        created_serial_numbers = 0
        created_pairs = 0
        preview: list[dict] = []
        sequence = random.randint(1000, 9000)

        for row in rows:
            missing_imei_count = int(row["missing_imei_count"])
            missing_serial_count = int(row["missing_serial_count"])
            serial_numbers = await _available_serial_numbers(
                session,
                row["product_id"],
                row["variant_id"],
                row["location_id"],
                missing_imei_count,
            )
            generated: list[str] = []
            for _ in range(missing_imei_count):
                sequence += 1
                while True:
                    imei = generate_imei(
                        f"{row.get('variant_sku') or row.get('product_sku') or row['product_id']}-{sequence}",
                        sequence,
                    )
                    if imei not in existing:
                        existing.add(imei)
                        generated.append(imei)
                        break
                    sequence += 1
            generated_serial_numbers: list[str] = []
            for _ in range(missing_serial_count):
                sequence += 1
                while True:
                    serial_number = generate_serial_number(
                        str(row.get("variant_sku") or row.get("product_sku") or row["product_id"]),
                        sequence,
                    )
                    key = (row["product_id"], serial_number)
                    if key not in existing_serial_numbers:
                        existing_serial_numbers.add(key)
                        generated_serial_numbers.append(serial_number)
                        break
                    sequence += 1

            pairable_serial_numbers = serial_numbers + generated_serial_numbers

            preview.append(
                {
                    "productName": row["product_name"],
                    "productSku": row["product_sku"],
                    "variantSku": row["variant_sku"],
                    "locationCode": row["location_code"],
                    "missingImeiCount": missing_imei_count,
                    "missingSerialCount": missing_serial_count,
                    "pairableSerialCount": len(pairable_serial_numbers),
                    "sampleImeis": generated[:3],
                    "sampleSerialNumbers": generated_serial_numbers[:3],
                }
            )

            if not args.apply:
                continue

            for imei in generated:
                await session.execute(
                    text(
                        """
                        INSERT INTO product_imeis (
                            id, product_id, variant_id, imei, status,
                            source_reference, received_at, is_primary, location_id
                        )
                        VALUES (
                            :id, :product_id, :variant_id, :imei, 'IN_STOCK',
                            :source_reference, NOW(), FALSE, :location_id
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "product_id": row["product_id"],
                        "variant_id": row["variant_id"],
                        "imei": imei,
                        "source_reference": args.source_reference,
                        "location_id": row["location_id"],
                    },
                )
                created_imeis += 1

            for serial_number in generated_serial_numbers:
                await session.execute(
                    text(
                        """
                        INSERT INTO product_serial_numbers (
                            id, product_id, variant_id, serial_number, status,
                            source_reference, received_at, location_id
                        )
                        VALUES (
                            :id, :product_id, :variant_id, :serial_number, 'IN_STOCK',
                            :source_reference, NOW(), :location_id
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "product_id": row["product_id"],
                        "variant_id": row["variant_id"],
                        "serial_number": serial_number,
                        "source_reference": args.source_reference,
                        "location_id": row["location_id"],
                    },
                )
                created_serial_numbers += 1

            for imei, serial_number in zip(generated, pairable_serial_numbers, strict=False):
                await session.execute(
                    text(
                        """
                        INSERT INTO product_identifier_pairs (
                            id, product_id, variant_id, imei1, serial_number, source_reference
                        )
                        VALUES (
                            :id, :product_id, :variant_id, :imei, :serial_number, :source_reference
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "id": uuid4(),
                        "product_id": row["product_id"],
                        "variant_id": row["variant_id"],
                        "imei": imei,
                        "serial_number": serial_number,
                        "source_reference": args.source_reference,
                    },
                )
                created_pairs += 1

        if args.apply:
            await session.commit()

        print(
            json.dumps(
                {
                    "ok": True,
                    "applied": bool(args.apply),
                    "includeUntracked": bool(args.include_untracked),
                    "sourceReference": args.source_reference,
                    "candidateRows": len(rows),
                    "missingImeiTotal": sum(int(row["missing_imei_count"]) for row in rows),
                    "missingSerialTotal": sum(int(row["missing_serial_count"]) for row in rows),
                    "createdImeis": created_imeis,
                    "createdSerialNumbers": created_serial_numbers,
                    "createdPairs": created_pairs,
                    "preview": preview,
                },
                ensure_ascii=False,
                default=str,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
