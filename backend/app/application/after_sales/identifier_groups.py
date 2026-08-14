from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class LockedIdentifier:
    id: UUID
    value: str
    status: str
    kind: str


@dataclass(frozen=True)
class LockedIdentifierGroup:
    pair_id: UUID | None
    imeis: tuple[LockedIdentifier, ...]
    serials: tuple[LockedIdentifier, ...]

    @property
    def imei_values(self) -> tuple[str, ...]:
        return tuple(identifier.value for identifier in self.imeis)

    @property
    def serial_values(self) -> tuple[str, ...]:
        return tuple(identifier.value for identifier in self.serials)

    @property
    def identifiers(self) -> tuple[LockedIdentifier, ...]:
        return self.imeis + self.serials


async def lock_identifier_group(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    imei: str | None = None,
    serial_number: str | None = None,
) -> LockedIdentifierGroup:
    """Khóa một thiết bị vật lý theo thứ tự cặp -> IMEI -> serial."""
    normalized_imei = str(imei or "").strip() or None
    normalized_serial = str(serial_number or "").strip() or None
    if not normalized_imei and not normalized_serial:
        raise HTTPException(status_code=400, detail="Thiết bị phải có IMEI hoặc serial để cập nhật trạng thái.")

    pair_rows = (
        await session.execute(
            text(
                """
                SELECT id, imei1, imei2, serial_number
                FROM product_identifier_pairs
                WHERE product_id = :product_id
                  AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
                  AND (
                    (CAST(:imei AS VARCHAR) IS NOT NULL
                     AND (imei1 = CAST(:imei AS VARCHAR) OR imei2 = CAST(:imei AS VARCHAR)))
                    OR
                    (CAST(:serial AS VARCHAR) IS NOT NULL
                     AND serial_number = CAST(:serial AS VARCHAR))
                  )
                ORDER BY id
                FOR UPDATE
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "imei": normalized_imei,
                "serial": normalized_serial,
            },
        )
    ).mappings().all()
    if len(pair_rows) > 1:
        raise HTTPException(status_code=409, detail="IMEI và serial không thuộc cùng một thiết bị vật lý.")

    pair = pair_rows[0] if pair_rows else None
    imei_values = tuple(
        value
        for value in (
            (pair["imei1"], pair.get("imei2"))
            if pair
            else (normalized_imei,)
        )
        if value
    )
    serial_values = tuple(
        value
        for value in (
            (pair["serial_number"],)
            if pair
            else (normalized_serial,)
        )
        if value
    )

    imei_rows = []
    if imei_values:
        imei_rows = (
            await session.execute(
                text(
                    """
                    SELECT id, imei AS identifier, status
                    FROM product_imeis
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
                      AND imei = ANY(:values)
                    ORDER BY imei
                    FOR UPDATE
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "values": list(imei_values)},
            )
        ).mappings().all()
    serial_rows = []
    if serial_values:
        serial_rows = (
            await session.execute(
                text(
                    """
                    SELECT id, serial_number AS identifier, status
                    FROM product_serial_numbers
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
                      AND serial_number = ANY(:values)
                    ORDER BY serial_number
                    FOR UPDATE
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "values": list(serial_values)},
            )
        ).mappings().all()

    if len(imei_rows) != len(imei_values) or len(serial_rows) != len(serial_values):
        raise HTTPException(status_code=409, detail="Không tìm thấy đầy đủ IMEI/serial của thiết bị cần xử lý.")

    return LockedIdentifierGroup(
        pair_id=pair["id"] if pair else None,
        imeis=tuple(
            LockedIdentifier(id=row["id"], value=row["identifier"], status=row["status"], kind="IMEI")
            for row in imei_rows
        ),
        serials=tuple(
            LockedIdentifier(id=row["id"], value=row["identifier"], status=row["status"], kind="SERIAL")
            for row in serial_rows
        ),
    )


async def update_locked_identifier_group_status(
    session: AsyncSession,
    *,
    group: LockedIdentifierGroup,
    target_status: str,
    allowed_statuses: set[str],
    clear_location: bool = False,
) -> tuple[LockedIdentifier, ...]:
    changed: list[LockedIdentifier] = []
    for identifier in group.identifiers:
        if identifier.status == target_status:
            continue
        if identifier.status not in allowed_statuses:
            raise HTTPException(
                status_code=409,
                detail=f"Mã liên kết {identifier.value} đang ở trạng thái không thể thay đổi.",
            )
        changed.append(identifier)

    imei_ids = [identifier.id for identifier in changed if identifier.kind == "IMEI"]
    serial_ids = [identifier.id for identifier in changed if identifier.kind == "SERIAL"]
    location_sql = ", location_id = NULL" if clear_location else ""
    if imei_ids:
        await session.execute(
            text(f"UPDATE product_imeis SET status = :status{location_sql}, updated_at = NOW() WHERE id = ANY(:ids)"),
            {"status": target_status, "ids": imei_ids},
        )
    if serial_ids:
        await session.execute(
            text(f"UPDATE product_serial_numbers SET status = :status{location_sql}, updated_at = NOW() WHERE id = ANY(:ids)"),
            {"status": target_status, "ids": serial_ids},
        )
    return tuple(changed)
