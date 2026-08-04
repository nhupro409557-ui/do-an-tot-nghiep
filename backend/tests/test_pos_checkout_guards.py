from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

import app.application.commerce.use_cases.create_order as create_order_module
import app.application.commerce.use_cases.complete_order_fulfillment as fulfillment_module
from app.application.commerce.schemas import CheckoutItem
from app.application.commerce.use_cases.complete_order import CompleteOrderUseCase
from app.application.commerce.use_cases.create_order import (
    CreateOrderUseCase as CreateCheckoutUseCase,
    _pos_shipping_fee,
    _validate_pos_cash_received,
)


def _request(*, is_offline: bool, payment_method: str = "COD", cash_received: str | None = None):
    return SimpleNamespace(
        is_offline=is_offline,
        payment_method=payment_method,
        cash_received=None if cash_received is None else Decimal(cash_received),
    )


def test_pos_order_never_charges_shipping_fee():
    request = _request(is_offline=True, cash_received="850000")

    assert _pos_shipping_fee(request, Decimal("42000")) == Decimal("0.00")


def test_online_order_keeps_quoted_shipping_fee():
    request = _request(is_offline=False)

    assert _pos_shipping_fee(request, Decimal("42000")) == Decimal("42000.00")


def test_pos_cash_payment_rejects_missing_or_insufficient_amount():
    for cash_received in (None, "849999"):
        with pytest.raises(HTTPException) as exc_info:
            _validate_pos_cash_received(
                _request(is_offline=True, cash_received=cash_received),
                Decimal("850000"),
            )

        assert exc_info.value.status_code == 400
        assert "Số tiền khách đưa" in str(exc_info.value.detail)


def test_pos_cash_payment_accepts_exact_amount():
    _validate_pos_cash_received(
        _request(is_offline=True, cash_received="850000"),
        Decimal("850000"),
    )


@pytest.mark.asyncio
async def test_pos_resolves_one_available_used_device(monkeypatch):
    device_id = UUID("3bfd38fb-ac64-4407-8c32-cfe299ab8333")

    async def fake_get_checkout_device(_session, requested_device_id):
        assert requested_device_id == device_id
        return {
            "productId": None,
            "variantId": None,
            "salePrice": 10900000,
            "warrantyMonths": 6,
            "title": "Điện thoại smoke test hàng cũ hạng B",
            "categoryId": None,
            "subcategoryId": None,
            "brandId": None,
        }

    monkeypatch.setattr(create_order_module.used_product_repo, "get_checkout_device", fake_get_checkout_device)
    use_case = object.__new__(CreateCheckoutUseCase)
    use_case._session = object()
    request = SimpleNamespace(items=[CheckoutItem(
        used_device_id=device_id,
        product_name="Tên hiển thị từ POS",
        quantity=1,
        unit_price=Decimal("10900000"),
    )])

    lines = await use_case._resolve_checkout_lines(request, for_update=True)

    assert len(lines) == 1
    assert lines[0].used_device_id == device_id
    assert lines[0].product_id is None
    assert lines[0].product_name == "Điện thoại smoke test hàng cũ hạng B"
    assert lines[0].warranty_months_snapshot == 6


@pytest.mark.asyncio
async def test_pos_rejects_used_device_quantity_greater_than_one():
    use_case = object.__new__(CreateCheckoutUseCase)
    use_case._session = object()
    request = SimpleNamespace(items=[CheckoutItem(
        used_device_id=UUID("3bfd38fb-ac64-4407-8c32-cfe299ab8333"),
        product_name="Điện thoại hàng cũ",
        quantity=2,
        unit_price=Decimal("10900000"),
    )])

    with pytest.raises(HTTPException) as exc_info:
        await use_case._resolve_checkout_lines(request, for_update=True)

    assert exc_info.value.status_code == 400
    assert "số lượng 1" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_pos_rejects_changed_used_device_price(monkeypatch):
    async def fake_get_checkout_device(_session, _requested_device_id):
        return {"salePrice": 11000000, "title": "Điện thoại hàng cũ"}

    monkeypatch.setattr(create_order_module.used_product_repo, "get_checkout_device", fake_get_checkout_device)
    use_case = object.__new__(CreateCheckoutUseCase)
    use_case._session = object()
    request = SimpleNamespace(items=[CheckoutItem(
        used_device_id=UUID("3bfd38fb-ac64-4407-8c32-cfe299ab8333"),
        product_name="Điện thoại hàng cũ",
        quantity=1,
        unit_price=Decimal("10900000"),
    )])

    with pytest.raises(HTTPException) as exc_info:
        await use_case._resolve_checkout_lines(request, for_update=True)

    assert exc_info.value.status_code == 409
    assert "Giá thiết bị cũ đã thay đổi" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_refunded_used_only_order_runs_returned_qc_restock(monkeypatch):
    async def no_catalog_shipment(*_args, **_kwargs):
        return False

    async def has_sold_used_device(*_args, **_kwargs):
        return True

    monkeypatch.setattr(
        fulfillment_module.commerce_repo,
        "order_has_inventory_adjustment_reason",
        no_catalog_shipment,
    )
    monkeypatch.setattr(
        fulfillment_module.used_product_repo,
        "order_has_sold_device",
        has_sold_used_device,
    )
    use_case = object.__new__(CompleteOrderUseCase)
    use_case._session = object()
    restocked_order_ids = []

    async def fake_restock(order):
        restocked_order_ids.append(order.id)

    use_case._restock_order_items = fake_restock
    order = SimpleNamespace(
        id=UUID("7fd22898-41ea-4bf3-806d-73490537466b"),
        order_code="EMV2093217402",
    )

    await use_case._release_or_restock_unshipped_order(order, reservation_status="RELEASED")

    assert restocked_order_ids == [order.id]
