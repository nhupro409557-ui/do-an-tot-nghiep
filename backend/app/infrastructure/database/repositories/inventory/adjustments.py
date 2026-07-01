from .stock_mutation_common import *

async def insert_inventory_adjustment_log(
    session: AsyncSession,
    *,
    log_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    old_quantity: int,
    new_quantity: int,
    delta: int,
    transaction_type: str,
    reference_code: str,
    reason: str,
    note: str | None,
    supplier_name: str | None,
    unit_cost: float | None,
    location_code: str | None,
    location_name: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta, transaction_type, reference_code, reason, note,
                supplier_name, unit_cost, location_code, location_name
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta, :transaction_type, :reference_code, :reason, :note,
                :supplier_name, :unit_cost, :location_code, :location_name
            )
            """
        ),
        {
            "id": log_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": transaction_type,



            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "supplier_name": supplier_name,
            "unit_cost": unit_cost,
            "location_code": location_code,
            "location_name": location_name,
        },
    )


async def insert_inventory_idempotency_response(session: AsyncSession, *, key: str, product_id: UUID, response_payload: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_inventory_idempotency (idempotency_key, product_id, response_payload)
            VALUES (:key, :product_id, CAST(:response_payload AS jsonb))
            ON CONFLICT DO NOTHING
            """
        ),
        {"key": key, "product_id": product_id, "response_payload": json.dumps(response_payload, ensure_ascii=False)},
    )
