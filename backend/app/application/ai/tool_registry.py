import asyncio
import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.database.repositories import ai_repo
from app.infrastructure.database.repositories import voucher_repo
from app.application.commerce.use_cases.voucher_service import VoucherService
from app.application.services.public_content_service import get_review_eligibility
from app.application.services import used_product_service


class EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_code: str = Field(pattern=r"^[A-Z0-9-]{6,40}$")


class AfterSalesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_code: str = Field(pattern=r"^(WR|RT)[A-Z0-9]{10,38}$")


class SearchUsedProductsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str = Field(default="", max_length=120)
    grade: str = Field(default="", pattern=r"^(|A|B|C)$")
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=10)


class ProductArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID


class ToolExecutionError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _clean(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=_jsonable))


class AIReadToolRegistry:
    ALLOWED_TOOLS = {
        "get_my_order",
        "get_my_latest_order",
        "get_shipping_timeline",
        "get_my_loyalty",
        "get_after_sales_status",
        "get_my_latest_after_sales",
        "search_used_products",
        "list_public_vouchers",
        "get_my_vouchers",
        "get_my_account",
        "get_product_review_insights",
        "get_my_review_eligibility",
        "get_my_latest_support_request",
    }
    PUBLIC_TOOLS = {"search_used_products", "list_public_vouchers", "get_product_review_insights"}

    def __init__(self, *, session: AsyncSession, timeout_seconds: float = 3.0) -> None:
        self._session = session
        self._timeout_seconds = timeout_seconds

    async def execute(self, *, name: str, arguments: dict, user_id: str | None) -> Any:
        if name not in self.ALLOWED_TOOLS:
            raise ToolExecutionError("TOOL_NOT_ALLOWED")
        if name not in self.PUBLIC_TOOLS and not user_id:
            return {"needs_auth": True}

        try:
            async with asyncio.timeout(self._timeout_seconds):
                if name == "get_my_order":
                    args = OrderArgs.model_validate(arguments)
                    row = await ai_repo.get_user_order_for_ai(
                        self._session,
                        user_id=user_id,
                        order_code=args.order_code,
                    )
                    return _clean(row) if row else None
                if name == "get_my_latest_order":
                    EmptyArgs.model_validate(arguments)
                    row = await ai_repo.get_latest_user_order_for_ai(
                        self._session,
                        user_id=user_id,
                    )
                    return _clean(row) if row else None
                if name == "get_shipping_timeline":
                    args = OrderArgs.model_validate(arguments)
                    rows = await ai_repo.get_order_shipping_events_for_ai(
                        self._session,
                        user_id=user_id,
                        order_code=args.order_code,
                    )
                    return _clean(rows)
                if name == "get_after_sales_status":
                    args = AfterSalesArgs.model_validate(arguments)
                    row = await ai_repo.get_user_after_sales_for_ai(
                        self._session,
                        user_id=user_id,
                        request_code=args.request_code,
                    )
                    return _clean(row) if row else None
                if name == "get_my_latest_after_sales":
                    EmptyArgs.model_validate(arguments)
                    row = await ai_repo.get_latest_user_after_sales_for_ai(
                        self._session,
                        user_id=user_id,
                    )
                    return _clean(row) if row else None
                if name == "search_used_products":
                    args = SearchUsedProductsArgs.model_validate(arguments)
                    result = await used_product_service.list_public_listings(
                        self._session,
                        search=args.search,
                        grade=args.grade,
                        brand_id=None,
                        category_id=None,
                        min_price=args.min_price,
                        max_price=args.max_price,
                        sort="newest",
                        page=1,
                        limit=args.limit,
                    )
                    return _clean(result)
                if name == "list_public_vouchers":
                    EmptyArgs.model_validate(arguments)
                    return _clean(await voucher_repo.list_public_vouchers(self._session))
                if name == "get_my_vouchers":
                    EmptyArgs.model_validate(arguments)
                    responses = await VoucherService(session=self._session).list_user_vouchers(
                        user_id=UUID(str(user_id)),
                    )
                    return _clean([response.model_dump(mode="json") for response in responses])
                if name == "get_my_account":
                    EmptyArgs.model_validate(arguments)
                    row = await ai_repo.get_user_account_for_ai(self._session, user_id=str(user_id))
                    return _clean(row) if row else None
                if name == "get_product_review_insights":
                    args = ProductArgs.model_validate(arguments)
                    row = await ai_repo.get_product_review_insights_for_ai(
                        self._session,
                        product_id=str(args.product_id),
                    )
                    return _clean(row)
                if name == "get_my_review_eligibility":
                    args = ProductArgs.model_validate(arguments)
                    row = await get_review_eligibility(args.product_id, UUID(str(user_id)), self._session)
                    return _clean(row)
                if name == "get_my_latest_support_request":
                    EmptyArgs.model_validate(arguments)
                    row = await ai_repo.get_latest_user_support_request_for_ai(
                        self._session,
                        user_id=str(user_id),
                    )
                    return _clean(row) if row else None
                EmptyArgs.model_validate(arguments)
                row = await ai_repo.get_user_loyalty_for_ai(self._session, user_id=user_id)
                return _clean(row) if row else None
        except ValidationError as error:
            raise ToolExecutionError("INVALID_INPUT") from error
        except TimeoutError as error:
            raise ToolExecutionError("TIMEOUT") from error
        except SQLAlchemyError as error:
            raise ToolExecutionError("DEPENDENCY_UNAVAILABLE") from error

        raise ToolExecutionError("TOOL_NOT_ALLOWED")
