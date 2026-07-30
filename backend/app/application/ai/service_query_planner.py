from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai.intent_router import normalize_text


SERVICE_PLANNABLE_INTENTS = {
    "ORDER_LOOKUP",
    "SHIPPING_LOOKUP",
    "AFTER_SALES_LOOKUP",
    "LOYALTY",
    "VOUCHER_SUPPORT",
    "STORE_POLICY",
    "WARRANTY_POLICY",
}

ServicePlannerStep = Literal[
    "get_order",
    "get_shipping_timeline",
    "get_after_sales",
    "get_loyalty",
    "list_public_vouchers",
    "get_my_vouchers",
    "get_store_policy",
]


class ServiceQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_intent: str
    intents: list[str] = Field(min_length=2, max_length=7)
    steps: list[ServicePlannerStep] = Field(min_length=2, max_length=7)
    requires_auth: bool = False
    confidence: float = Field(ge=0, le=1)


INTENT_SIGNALS = {
    "ORDER_LOOKUP": (
        "don hang",
        "don cua toi",
        "trang thai don",
        "don mua",
    ),
    "SHIPPING_LOOKUP": (
        "giao toi dau",
        "giao den dau",
        "van chuyen",
        "ma van don",
        "khi nao toi",
        "khi nao giao",
        "dang giao",
        "theo doi giao hang",
    ),
    "AFTER_SALES_LOOKUP": (
        "ho so bao hanh",
        "ho so doi tra",
        "bao hanh cua toi",
        "doi tra cua toi",
        "hau mai",
        "tien do bao hanh",
        "tien do doi tra",
    ),
    "LOYALTY": (
        "diem tich luy",
        "diem cua toi",
        "vi diem",
        "hang thanh vien",
        "len hang",
        "bao nhieu diem",
        "doanh so xet hang",
    ),
    "VOUCHER_SUPPORT": (
        "voucher",
        "ma giam gia",
        "uu dai cua toi",
        "phieu giam gia",
    ),
    "STORE_POLICY": (
        "chinh sach cua hang",
        "chinh sach doi tra",
        "chinh sach giao hang",
        "chinh sach thanh toan",
    ),
    "WARRANTY_POLICY": (
        "chinh sach bao hanh",
        "dieu kien bao hanh",
        "bao hanh bao lau",
        "bao hanh the nao",
    ),
}

PERSONAL_INTENTS = {
    "ORDER_LOOKUP",
    "SHIPPING_LOOKUP",
    "AFTER_SALES_LOOKUP",
    "LOYALTY",
}

INTENT_STEPS: dict[str, tuple[ServicePlannerStep, ...]] = {
    "ORDER_LOOKUP": ("get_order",),
    "SHIPPING_LOOKUP": ("get_order", "get_shipping_timeline"),
    "AFTER_SALES_LOOKUP": ("get_after_sales",),
    "LOYALTY": ("get_loyalty",),
    "VOUCHER_SUPPORT": ("list_public_vouchers", "get_my_vouchers"),
    "STORE_POLICY": ("get_store_policy",),
    "WARRANTY_POLICY": ("get_store_policy",),
}


def build_service_query_plan(message: str, *, base_intent: str) -> ServiceQueryPlan | None:
    if base_intent not in SERVICE_PLANNABLE_INTENTS:
        return None

    normalized = normalize_text(message)
    detected = [
        intent
        for intent, signals in INTENT_SIGNALS.items()
        if any(signal in normalized for signal in signals)
    ]

    if base_intent in SERVICE_PLANNABLE_INTENTS:
        detected.insert(0, base_intent)
    detected = list(dict.fromkeys(detected))
    if "SHIPPING_LOOKUP" in detected and "ORDER_LOOKUP" in detected:
        detected.remove("ORDER_LOOKUP")
    if len(detected) < 2:
        return None

    primary_intent = base_intent if base_intent in detected else detected[0]
    ordered_intents = [primary_intent, *(intent for intent in detected if intent != primary_intent)]
    steps = list(
        dict.fromkeys(
            step
            for intent in ordered_intents
            for step in INTENT_STEPS[intent]
        )
    )
    requires_auth = bool(PERSONAL_INTENTS.intersection(ordered_intents))
    if "VOUCHER_SUPPORT" in ordered_intents:
        requires_auth = True

    return ServiceQueryPlan(
        primary_intent=primary_intent,
        intents=ordered_intents,
        steps=steps,
        requires_auth=requires_auth,
        confidence=0.94 if len(ordered_intents) == 2 else 0.91,
    )
