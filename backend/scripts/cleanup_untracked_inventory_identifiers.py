from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import text

from app.application.services.inventory.common import (
    _policy_tracks_imei,
    _policy_tracks_serial_number,
)
from app.infrastructure.database.repositories import inventory_repo
from app.infrastructure.database.session import AsyncSessionFactory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dọn IMEI/serial đang IN_STOCK nhưng sản phẩm không còn bật chính sách quản lý tương ứng. "
            "Dữ liệu đã bán, bảo hành, giữ chỗ hoặc phế phẩm luôn được giữ lại."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi thay đổi vào cơ sở dữ liệu. Không có cờ này thì chỉ xem trước.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    async with AsyncSessionFactory() as session:
        product_ids = (
            await session.execute(
                text("SELECT id FROM products WHERE deleted_at IS NULL AND status <> 'MERGED' ORDER BY id")
            )
        ).scalars().all()

        untracked_imei_products = []
        untracked_serial_products = []
        for product_id in product_ids:
            policy = await inventory_repo.get_product_inventory_policy(session, product_id)
            if not _policy_tracks_imei(policy):
                untracked_imei_products.append(product_id)
            if not _policy_tracks_serial_number(policy):
                untracked_serial_products.append(product_id)

        params = {
            "imei_product_ids": untracked_imei_products,
            "serial_product_ids": untracked_serial_products,
        }
        counts = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM product_imeis
                         WHERE status = 'IN_STOCK' AND product_id = ANY(CAST(:imei_product_ids AS uuid[]))) AS imei_count,
                        (SELECT COUNT(*) FROM product_serial_numbers
                         WHERE status = 'IN_STOCK' AND product_id = ANY(CAST(:serial_product_ids AS uuid[]))) AS serial_count,
                        (SELECT COUNT(*) FROM product_identifier_pairs pair
                         WHERE EXISTS (
                             SELECT 1 FROM product_imeis pi
                             WHERE pi.product_id = pair.product_id AND pi.imei IN (pair.imei1, pair.imei2)
                               AND pi.status = 'IN_STOCK'
                               AND pi.product_id = ANY(CAST(:imei_product_ids AS uuid[]))
                         ) OR EXISTS (
                             SELECT 1 FROM product_serial_numbers psn
                             WHERE psn.product_id = pair.product_id AND psn.serial_number = pair.serial_number
                               AND psn.status = 'IN_STOCK'
                               AND psn.product_id = ANY(CAST(:serial_product_ids AS uuid[]))
                         )) AS pair_count
                    """
                ),
                params,
            )
        ).mappings().one()

        if args.apply:
            await session.execute(
                text(
                    """
                    DELETE FROM product_identifier_pairs pair
                    WHERE EXISTS (
                        SELECT 1 FROM product_imeis pi
                        WHERE pi.product_id = pair.product_id AND pi.imei IN (pair.imei1, pair.imei2)
                          AND pi.status = 'IN_STOCK'
                          AND pi.product_id = ANY(CAST(:imei_product_ids AS uuid[]))
                    ) OR EXISTS (
                        SELECT 1 FROM product_serial_numbers psn
                        WHERE psn.product_id = pair.product_id AND psn.serial_number = pair.serial_number
                          AND psn.status = 'IN_STOCK'
                          AND psn.product_id = ANY(CAST(:serial_product_ids AS uuid[]))
                    )
                    """
                ),
                params,
            )
            await session.execute(
                text(
                    "DELETE FROM product_imeis WHERE status = 'IN_STOCK' "
                    "AND product_id = ANY(CAST(:imei_product_ids AS uuid[]))"
                ),
                params,
            )
            await session.execute(
                text(
                    "DELETE FROM product_serial_numbers WHERE status = 'IN_STOCK' "
                    "AND product_id = ANY(CAST(:serial_product_ids AS uuid[]))"
                ),
                params,
            )
            await session.commit()

        print(
            json.dumps(
                {
                    "ok": True,
                    "applied": bool(args.apply),
                    "productsWithoutImeiPolicy": len(untracked_imei_products),
                    "productsWithoutSerialPolicy": len(untracked_serial_products),
                    "inStockImeisToRemove": int(counts["imei_count"] or 0),
                    "inStockSerialsToRemove": int(counts["serial_count"] or 0),
                    "identifierPairsToRemove": int(counts["pair_count"] or 0),
                    "historicalStatusesPreserved": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
