def order_item_extra_warranty_months_lateral_sql(
    *,
    order_item_alias: str = "oi",
    alias: str = "oi_service_warranty",
) -> str:
    return f"""
        LEFT JOIN LATERAL (
            SELECT COALESCE(SUM(
                CASE
                    WHEN service_item ->> 'duration_months' ~ '^[0-9]+$'
                        THEN (service_item ->> 'duration_months')::integer
                    WHEN service_item ->> 'durationMonths' ~ '^[0-9]+$'
                        THEN (service_item ->> 'durationMonths')::integer
                    ELSE 0
                END
            ), 0) AS extra_warranty_months
            FROM jsonb_array_elements(COALESCE({order_item_alias}.attached_services, '[]'::jsonb)) AS service_item
        ) {alias} ON TRUE
    """


def order_item_effective_warranty_months_sql(
    *,
    order_item_alias: str = "oi",
    product_alias: str = "p",
    used_device_alias: str = "ud",
    extra_warranty_alias: str = "oi_service_warranty",
) -> str:
    return f"""
        COALESCE(
            {order_item_alias}.warranty_months_snapshot,
            GREATEST(COALESCE({product_alias}.warranty_period, 0), COALESCE({used_device_alias}.warranty_months, 0), 0)
            + COALESCE({extra_warranty_alias}.extra_warranty_months, 0),
            0
        )
    """
