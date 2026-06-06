import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_attached_services(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, name, service_type AS "serviceType",
                   attribute_group AS "attributeGroup", duration_months AS "durationMonths",
                   price_mode AS "priceMode", fixed_price AS "fixedPrice",
                   percent_value AS "percentValue", base_amount AS "baseAmount",
                   is_active AS "isActive", metadata, created_at AS "createdAt", updated_at AS "updatedAt"
            FROM attached_services
            ORDER BY service_type, attribute_group NULLS LAST, name
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def insert_attached_service(
    session: AsyncSession,
    *,
    service_id: UUID,
    code: str,
    name: str,
    service_type: str,
    attribute_group: str | None,
    duration_months: int | None,
    price_mode: str,
    fixed_price: float | int | None,
    percent_value: float | int | None,
    base_amount: float | int | None,
    is_active: bool,
    metadata: dict,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO attached_services (
                id, code, name, service_type, attribute_group, duration_months,
                price_mode, fixed_price, percent_value, base_amount, is_active, metadata
            )
            VALUES (
                :id, :code, :name, :service_type, :attribute_group, :duration_months,
                :price_mode, :fixed_price, :percent_value, :base_amount, :is_active, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": service_id,
            "code": code,
            "name": name,
            "service_type": service_type,
            "attribute_group": attribute_group,
            "duration_months": duration_months,
            "price_mode": price_mode,
            "fixed_price": fixed_price,
            "percent_value": percent_value,
            "base_amount": base_amount,
            "is_active": is_active,
            "metadata": json.dumps(metadata),
        },
    )


async def update_attached_service(
    session: AsyncSession,
    *,
    service_id: UUID,
    code: str,
    name: str,
    service_type: str,
    attribute_group: str | None,
    duration_months: int | None,
    price_mode: str,
    fixed_price: float | int | None,
    percent_value: float | int | None,
    base_amount: float | int | None,
    is_active: bool,
    metadata: dict,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE attached_services
            SET code = :code, name = :name, service_type = :service_type,
                attribute_group = :attribute_group, duration_months = :duration_months,
                price_mode = :price_mode, fixed_price = :fixed_price,
                percent_value = :percent_value, base_amount = :base_amount,
                is_active = :is_active, metadata = CAST(:metadata AS jsonb), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": service_id,
            "code": code,
            "name": name,
            "service_type": service_type,
            "attribute_group": attribute_group,
            "duration_months": duration_months,
            "price_mode": price_mode,
            "fixed_price": fixed_price,
            "percent_value": percent_value,
            "base_amount": base_amount,
            "is_active": is_active,
            "metadata": json.dumps(metadata),
        },
    )
    return int(result.rowcount or 0)


async def deactivate_attached_service(session: AsyncSession, service_id: UUID) -> int:
    result = await session.execute(
        text("UPDATE attached_services SET is_active = FALSE, updated_at = NOW() WHERE id = :id"),
        {"id": service_id},
    )
    return int(result.rowcount or 0)
