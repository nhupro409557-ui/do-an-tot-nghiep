import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

import httpx

from app.config import settings


@dataclass
class RefundResult:
    success: bool
    provider_ref: str | None = None
    message: str = ""
    mode: str = "stub"


@dataclass
class ShipmentResult:
    success: bool
    provider: str | None = None
    tracking_code: str | None = None
    message: str = ""
    mode: str = "stub"


@dataclass
class ShippingQuote:
    fee: Decimal
    zone: str
    estimated_days: int
    free_shipping_applied: bool
    note: str = ""


@dataclass
class PaymentInitResult:
    success: bool
    checkout_url: str | None = None
    provider_ref: str | None = None
    message: str = ""
    raw_response: dict | None = None
    mode: str = "stub"


class RefundGateway:
    async def refund(self, *, provider: str, order_code: str, amount: Decimal) -> RefundResult:
        return RefundResult(
            success=True,
            provider_ref=f"stub-refund-{order_code}",
            message=f"Refund stub accepted for {provider}.",
        )


class ShippingGateway:
    async def register_shipment(
        self,
        *,
        provider: str | None,
        order_code: str,
        recipient_name: str,
        recipient_phone: str,
        shipping_address: str,
    ) -> ShipmentResult:
        normalized_provider = (provider or "MANUAL").strip().upper() or "MANUAL"
        return ShipmentResult(
            success=True,
            provider=normalized_provider,
            tracking_code=f"{normalized_provider[:4]}-{order_code[-8:]}",
            message="Shipment stub created.",
        )


class SandboxShippingPricingService:
    INNER_KEYWORDS = ("ho chi minh", "hồ chí minh", "ha noi", "hà nội")
    NEAR_KEYWORDS = ("binh duong", "bình dương", "dong nai", "đồng nai", "da nang", "đà nẵng", "can tho", "cần thơ")

    def quote(self, *, shipping_address: str, subtotal_amount: Decimal, item_count: int) -> ShippingQuote:
        normalized = shipping_address.strip().lower()
        if subtotal_amount >= Decimal(settings.sandbox_shipping_free_threshold):
            return ShippingQuote(
                fee=Decimal("0"),
                zone="FREE",
                estimated_days=2,
                free_shipping_applied=True,
                note="Free shipping threshold reached.",
            )
        if any(keyword in normalized for keyword in self.INNER_KEYWORDS):
            base_fee = Decimal(settings.sandbox_shipping_inner_fee)
            zone = "INNER_CITY"
            estimated_days = 1
        elif any(keyword in normalized for keyword in self.NEAR_KEYWORDS):
            base_fee = Decimal(settings.sandbox_shipping_near_fee)
            zone = "NEAR_CITY"
            estimated_days = 2
        else:
            base_fee = Decimal(settings.sandbox_shipping_far_fee)
            zone = "FAR_CITY"
            estimated_days = 4
        extra_item_fee = Decimal(max(0, item_count - 1) * 3000)
        return ShippingQuote(
            fee=base_fee + extra_item_fee,
            zone=zone,
            estimated_days=estimated_days,
            free_shipping_applied=False,
            note="Sandbox shipping quote based on destination zone and item count.",
        )


class MoMoSandboxGateway:
    async def create_payment(
        self,
        *,
        order_code: str,
        amount: Decimal,
        order_info: str,
        extra_data: dict,
    ) -> PaymentInitResult:
        if not settings.momo_partner_code or not settings.momo_access_key or not settings.momo_secret_key:
            return PaymentInitResult(
                success=True,
                checkout_url=f"https://test-payment.momo.vn/pay/{order_code}",
                provider_ref=order_code,
                message="MoMo sandbox credentials are missing. Fallback checkout URL generated.",
                raw_response={"mode": "fallback"},
                mode="fallback",
            )

        request_id = order_code
        redirect_url = settings.momo_redirect_url
        ipn_url = urljoin(settings.frontend_url.rstrip("/") + "/", settings.momo_ipn_path.lstrip("/")) if settings.momo_ipn_path.startswith("http") else f"http://localhost:8000{settings.momo_ipn_path}"
        encoded_extra_data = base64.b64encode(json.dumps(extra_data, ensure_ascii=True).encode("utf-8")).decode("utf-8")
        amount_int = int(amount)
        raw_signature = (
            f"accessKey={settings.momo_access_key}"
            f"&amount={amount_int}"
            f"&extraData={encoded_extra_data}"
            f"&ipnUrl={ipn_url}"
            f"&orderId={order_code}"
            f"&orderInfo={order_info}"
            f"&partnerCode={settings.momo_partner_code}"
            f"&redirectUrl={redirect_url}"
            f"&requestId={request_id}"
            f"&requestType={settings.momo_request_type}"
        )
        signature = hmac.new(
            settings.momo_secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        payload = {
            "partnerCode": settings.momo_partner_code,
            "partnerName": "ElectroMart Sandbox",
            "storeId": "ElectroMartStore",
            "requestId": request_id,
            "amount": amount_int,
            "orderId": order_code,
            "orderInfo": order_info,
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "requestType": settings.momo_request_type,
            "autoCapture": True,
            "extraData": encoded_extra_data,
            "signature": signature,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(settings.momo_endpoint, json=payload)
            data = response.json()
        pay_url = data.get("payUrl") or data.get("deeplink") or data.get("shortLink")
        return PaymentInitResult(
            success=response.is_success and bool(pay_url),
            checkout_url=pay_url,
            provider_ref=str(data.get("transId") or order_code),
            message=str(data.get("message") or ""),
            raw_response=data,
            mode="momo-sandbox",
        )
