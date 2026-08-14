import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin

import httpx

from app.config import settings
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession



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
    carrier_status: str = "CREATED"
    label_url: str | None = None
    message: str = ""
    mode: str = "mock"


@dataclass
class ShippingQuote:
    fee: Decimal
    zone: str
    estimated_days: int
    free_shipping_applied: bool
    provider: str = "MOCK_GHN"
    service_name: str = "Giao hàng tiêu chuẩn"
    note: str = ""


MOCK_CARRIER_PROFILES: dict[str, dict[str, Decimal | int | str]] = {
    "MOCK_GHN": {
        "name": "GHN Mock",
        "inner_fee": Decimal("22000"),
        "near_fee": Decimal("30000"),
        "far_fee": Decimal("42000"),
        "extra_item_fee": Decimal("3500"),
        "day_offset": 0,
    },
    "MOCK_GHTK": {
        "name": "GHTK Mock",
        "inner_fee": Decimal("20000"),
        "near_fee": Decimal("28000"),
        "far_fee": Decimal("39000"),
        "extra_item_fee": Decimal("3000"),
        "day_offset": 1,
    },
    "MANUAL": {
        "name": "Vận chuyển thủ công",
        "inner_fee": Decimal("18000"),
        "near_fee": Decimal("26000"),
        "far_fee": Decimal("35000"),
        "extra_item_fee": Decimal("2500"),
        "day_offset": 1,
    },
}


def normalize_mock_carrier(provider: str | None) -> str:
    value = (provider or "MOCK_GHN").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "GHN": "MOCK_GHN",
        "GIAO_HANG_NHANH": "MOCK_GHN",
        "GHTK": "MOCK_GHTK",
        "GIAO_HANG_TIET_KIEM": "MOCK_GHTK",
        "GIAO_HÀNG_TIẾT_KIỆM": "MOCK_GHTK",
    }
    return aliases.get(value, value if value in MOCK_CARRIER_PROFILES else "MOCK_GHN")


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
            provider_ref=f"sandbox-refund-{order_code}",
            message=f"Đã ghi nhận chứng từ hoàn tiền cho đơn {order_code} qua {provider}; hệ thống không thực hiện chuyển tiền thật.",
            mode="sandbox-manual",
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
        normalized_provider = normalize_mock_carrier(provider)
        return ShipmentResult(
            success=True,
            provider=normalized_provider,
            tracking_code=f"{normalized_provider.replace('MOCK_', '')}-{order_code[-8:]}",
            label_url=f"/mock-carriers/{normalized_provider.lower()}/labels/{order_code}",
            message="Vận đơn nội bộ đã được khởi tạo trong hệ thống; không gửi sang đơn vị vận chuyển thật.",
        )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, cos, sin, asin, sqrt
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371.0
    return c * r


async def get_driving_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float | None:
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if "routes" in data and len(data["routes"]) > 0:
                    return float(data["routes"][0]["distance"]) / 1000.0
    except Exception as e:
        print(f"[Warning] Failed to fetch OSRM driving distance: {e}")
    return None


class SandboxShippingPricingService:
    INNER_KEYWORDS = ("ho chi minh", "hồ chí minh", "ha noi", "hà nội")
    NEAR_KEYWORDS = ("binh duong", "bình dương", "dong nai", "đồng nai", "da nang", "đà nẵng", "can tho", "cần thơ")

    async def quote(
        self,
        session: AsyncSession,
        *,
        shipping_address: str,
        subtotal_amount: Decimal,
        item_count: int,
        provider: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ShippingQuote:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.infrastructure.database.repositories import store_info_repo

        normalized_provider = normalize_mock_carrier(provider)
        profile = MOCK_CARRIER_PROFILES[normalized_provider]
        
        if subtotal_amount >= Decimal(settings.sandbox_shipping_free_threshold):
            return ShippingQuote(
                fee=Decimal("0"),
                zone="FREE",
                estimated_days=2 + int(profile["day_offset"]),
                free_shipping_applied=True,
                provider=normalized_provider,
                service_name=str(profile["name"]),
                note=f"{profile['name']}: Đơn hàng đạt điều kiện miễn phí vận chuyển.",
            )

        # Trích xuất tọa độ cửa hàng từ DB
        store_info = await store_info_repo.get_store_info(session)
        store_lat = store_info.lat if store_info else None
        store_lng = store_info.lng if store_info else None

        has_coords = (
            lat is not None and lng is not None and 
            store_lat is not None and store_lng is not None
        )

        if has_coords:
            driving_dist = await get_driving_distance(store_lat, store_lng, lat, lng)
            if driving_dist is not None:
                distance = driving_dist
                is_driving = True
            else:
                distance = haversine_distance(store_lat, store_lng, lat, lng)
                is_driving = False

            # Tính phí dựa trên khoảng cách (km) thực tế
            if normalized_provider == "MOCK_GHN":
                # GHN: 20.000đ cho 2km đầu, 4.500đ/km tiếp theo (tối đa 10km), 3.500đ/km từ km thứ 10
                if distance <= 2.0:
                    base_fee = Decimal("20000")
                elif distance <= 10.0:
                    base_fee = Decimal("20000") + Decimal(str(round((distance - 2) * 4500)))
                else:
                    base_fee = Decimal("56000") + Decimal(str(round((distance - 10) * 3500)))
            elif normalized_provider == "MOCK_GHTK":
                # GHTK: 18.000đ cho 2km đầu, 4.000đ/km tiếp theo (tối đa 10km), 3.000đ/km từ km thứ 10
                if distance <= 2.0:
                    base_fee = Decimal("18000")
                elif distance <= 10.0:
                    base_fee = Decimal("18000") + Decimal(str(round((distance - 2) * 4000)))
                else:
                    base_fee = Decimal("50000") + Decimal(str(round((distance - 10) * 3000)))
            else:
                # MANUAL: 15.000đ cho 2km đầu, 3.500đ/km tiếp theo (tối đa 10km), 2.500đ/km từ km thứ 10
                if distance <= 2.0:
                    base_fee = Decimal("15000")
                elif distance <= 10.0:
                    base_fee = Decimal("15000") + Decimal(str(round((distance - 2) * 3500)))
                else:
                    base_fee = Decimal("43000") + Decimal(str(round((distance - 10) * 2500)))

            zone = f"DISTANCE_{round(distance)}KM"
            # Ước tính số ngày vận chuyển dựa trên khoảng cách
            if distance <= 5.0:
                estimated_days = 1
            elif distance <= 20.0:
                estimated_days = 2
            elif distance <= 100.0:
                estimated_days = 3
            else:
                estimated_days = 4
            
            dist_type = "quãng đường di chuyển" if is_driving else "đường chim bay"
            note_msg = f"{profile['name']}: Phí vận chuyển tính theo định vị ({dist_type} ~{distance:.1f} km), vận đơn nội bộ."

        else:
            # Fallback tính phí theo từ khóa địa chỉ truyền thống
            normalized = shipping_address.strip().lower()
            if any(keyword in normalized for keyword in self.INNER_KEYWORDS):
                base_fee = Decimal(profile["inner_fee"])
                zone = "INNER_CITY"
                estimated_days = 1
            elif any(keyword in normalized for keyword in self.NEAR_KEYWORDS):
                base_fee = Decimal(profile["near_fee"])
                zone = "NEAR_CITY"
                estimated_days = 2
            else:
                base_fee = Decimal(profile["far_fee"])
                zone = "FAR_CITY"
                estimated_days = 4
            note_msg = f"{profile['name']}: Phí vận chuyển tính theo vùng địa chỉ (chưa có định vị chính xác), vận đơn nội bộ."

        extra_item_fee = Decimal(max(0, item_count - 1)) * Decimal(profile["extra_item_fee"])
        return ShippingQuote(
            fee=base_fee + extra_item_fee,
            zone=zone,
            estimated_days=estimated_days + int(profile["day_offset"]),
            free_shipping_applied=False,
            provider=normalized_provider,
            service_name=str(profile["name"]),
            note=note_msg,
        )



class MoMoSandboxGateway:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.momo_partner_code and settings.momo_access_key and settings.momo_secret_key)

    @staticmethod
    def verify_ipn_signature(payload: dict) -> bool:
        signature = str(payload.get("signature") or "")
        if not signature or not MoMoSandboxGateway.is_configured():
            return False
        raw_signature = (
            f"accessKey={settings.momo_access_key}"
            f"&amount={payload.get('amount', '')}"
            f"&extraData={payload.get('extraData', '')}"
            f"&message={payload.get('message', '')}"
            f"&orderId={payload.get('orderId', '')}"
            f"&orderInfo={payload.get('orderInfo', '')}"
            f"&orderType={payload.get('orderType', '')}"
            f"&partnerCode={payload.get('partnerCode', '')}"
            f"&payType={payload.get('payType', '')}"
            f"&requestId={payload.get('requestId', '')}"
            f"&responseTime={payload.get('responseTime', '')}"
            f"&resultCode={payload.get('resultCode', '')}"
            f"&transId={payload.get('transId', '')}"
        )
        expected = hmac.new(
            settings.momo_secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    async def create_payment(
        self,
        *,
        order_code: str,
        amount: Decimal,
        order_info: str,
        extra_data: dict,
        request_id: str | None = None,
    ) -> PaymentInitResult:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cổng thanh toán MoMo chưa được cấu hình. Vui lòng bổ sung Partner Code, Access Key và Secret Key.",
            )

        request_id = request_id or order_code
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
            "partnerName": "ElectroMart",
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
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(settings.momo_endpoint, json=payload)
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Không thể kết nối MoMo: {exc}",
            ) from exc
        pay_url = data.get("payUrl") or data.get("deeplink") or data.get("shortLink")
        if not response.is_success or not pay_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(data.get("message") or "Cổng thanh toán MoMo không tạo được phiên thanh toán."),
            )
        return PaymentInitResult(
            success=response.is_success and bool(pay_url),
            checkout_url=pay_url,
            provider_ref=str(data.get("transId") or order_code),
            message=str(data.get("message") or ""),
            raw_response=data,
            mode="momo-sandbox",
        )

    async def query_payment(self, *, order_code: str, request_id: str | None = None) -> dict:
        if not self.is_configured():
            return {"resultCode": -1, "message": "MoMo chưa được cấu hình."}
        req_id = request_id or order_code
        raw_signature = (
            f"accessKey={settings.momo_access_key}"
            f"&orderId={order_code}"
            f"&partnerCode={settings.momo_partner_code}"
            f"&requestId={req_id}"
        )
        signature = hmac.new(
            settings.momo_secret_key.encode("utf-8"),
            raw_signature.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        payload = {
            "partnerCode": settings.momo_partner_code,
            "requestId": req_id,
            "orderId": order_code,
            "signature": signature,
        }
        query_endpoint = settings.momo_endpoint.replace("api/create", "api/query")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(query_endpoint, json=payload)
                if response.status_code == 200:
                    return response.json()
                return {"resultCode": -1, "message": f"HTTP error {response.status_code}"}
        except Exception as e:
            import logging
            logger = logging.getLogger("uvicorn.error")
            logger.error("Lỗi khi truy vấn MoMo: %s", e)
            return {"resultCode": -1, "message": str(e)}


class ZaloPaySandboxGateway:
    @staticmethod
    def is_configured() -> bool:
        return bool(settings.zalopay_app_id and settings.zalopay_key1 and settings.zalopay_key2)

    @staticmethod
    def verify_callback(data: str, mac: str) -> bool:
        if not ZaloPaySandboxGateway.is_configured() or not data or not mac:
            return False
        expected = hmac.new(
            settings.zalopay_key2.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(mac, expected)

    async def create_payment(
        self,
        *,
        app_trans_id: str,
        amount: Decimal,
        app_user: str,
        description: str,
        callback_url: str,
        redirect_url: str,
    ) -> PaymentInitResult:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cổng thanh toán ZaloPay chưa được cấu hình App ID, Key1 và Key2.",
            )
        app_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        item = "[]"
        embed_data = json.dumps(
            {
                "redirecturl": redirect_url,
                "preferred_payment_method": ["zalopay_wallet"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        mac_input = (
            f"{settings.zalopay_app_id}|{app_trans_id}|{app_user}|{int(amount)}|"
            f"{app_time}|{embed_data}|{item}"
        )
        mac = hmac.new(
            settings.zalopay_key1.encode("utf-8"),
            mac_input.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        payload = {
            "app_id": settings.zalopay_app_id,
            "app_user": app_user[:50],
            "app_time": app_time,
            "amount": int(amount),
            "app_trans_id": app_trans_id,
            "expire_duration_seconds": max(300, settings.zalopay_payment_timeout_minutes * 60),
            "bank_code": "",
            "embed_data": embed_data,
            "item": item,
            "callback_url": callback_url,
            "description": description[:256],
            "mac": mac,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(settings.zalopay_create_endpoint, json=payload)
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Không thể kết nối ZaloPay: {exc}",
            ) from exc
        checkout_url = data.get("order_url")
        if not response.is_success or int(data.get("return_code") or 0) != 1 or not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(data.get("sub_return_message") or data.get("return_message") or "ZaloPay không tạo được đơn thanh toán."),
            )
        return PaymentInitResult(
            success=True,
            checkout_url=checkout_url,
            provider_ref=app_trans_id,
            message=str(data.get("return_message") or ""),
            raw_response={**data, "mode": "zalopay-sandbox"},
            mode="zalopay-sandbox",
        )


class SePayPaymentGateway:
    SIGNED_FIELDS = {
        "merchant",
        "env",
        "operation",
        "payment_method",
        "order_amount",
        "currency",
        "order_invoice_number",
        "order_description",
        "customer_id",
        "agreement_id",
        "agreement_name",
        "agreement_type",
        "agreement_payment_frequency",
        "agreement_amount_per_payment",
        "success_url",
        "error_url",
        "cancel_url",
        "order_id",
    }

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.sepay_merchant_id and settings.sepay_secret_key)

    @staticmethod
    def checkout_url() -> str:
        version = settings.sepay_checkout_version or "v1"
        if (settings.sepay_env or "sandbox").lower() == "sandbox":
            return f"https://pay-sandbox.sepay.vn/{version}/checkout/init"
        return f"https://pay.sepay.vn/{version}/checkout/init"

    @staticmethod
    def verify_ipn_secret(secret_key: str | None) -> bool:
        configured = settings.sepay_secret_key
        return bool(configured and secret_key and hmac.compare_digest(secret_key, configured))

    def create_checkout(
        self,
        *,
        order_invoice_number: str,
        order_amount: Decimal,
        order_description: str,
        success_url: str,
        error_url: str,
        cancel_url: str,
        customer_id: str | None = None,
    ) -> PaymentInitResult:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cổng thanh toán SePay chưa được cấu hình Merchant ID và Secret Key.",
            )
        fields: dict[str, str | int] = {
            "payment_method": "BANK_TRANSFER",
            "order_invoice_number": order_invoice_number,
            "order_amount": int(order_amount),
            "currency": "VND",
            "order_description": order_description,
            "success_url": success_url,
            "error_url": error_url,
            "cancel_url": cancel_url,
        }
        if customer_id:
            fields["customer_id"] = customer_id
        fields["merchant"] = settings.sepay_merchant_id
        fields["operation"] = "PURCHASE"
        fields["signature"] = self._sign_fields(fields)
        return PaymentInitResult(
            success=True,
            checkout_url=self.checkout_url(),
            provider_ref=order_invoice_number,
            message="Đã tạo form thanh toán SePay.",
            raw_response={
                "mode": "sepay-sandbox" if (settings.sepay_env or "sandbox").lower() == "sandbox" else "sepay-live",
                "checkout_method": "POST_FORM",
                "checkout_fields": fields,
            },
            mode="sepay-sandbox",
        )

    def _sign_fields(self, fields: dict[str, str | int]) -> str:
        signed = [
            f"{field}={fields.get(field) or ''}"
            for field in fields.keys()
            if field in self.SIGNED_FIELDS and fields.get(field) is not None
        ]
        digest = hmac.new(
            settings.sepay_secret_key.encode("utf-8"),
            ",".join(signed).encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")
