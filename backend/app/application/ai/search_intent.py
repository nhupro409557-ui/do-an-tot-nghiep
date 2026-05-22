import json
import re

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings


class ProductSearchIntentRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    categories: list[dict] = Field(default_factory=list, max_length=50)
    brands: list[str] = Field(default_factory=list, max_length=100)


class ProductSearchIntentResponse(BaseModel):
    categoryIds: list[str] = Field(default_factory=list)
    brand: str | None = None
    minPrice: int | None = Field(default=None, ge=0)
    maxPrice: int | None = Field(default=None, ge=0)
    useCases: list[str] = Field(default_factory=list)
    preferredSpecs: list[str] = Field(default_factory=list)
    searchableTerms: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = "gemini"


def _json_from_text(value: str) -> dict:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_price(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


async def parse_product_search_intent(
    request: ProductSearchIntentRequest,
) -> ProductSearchIntentResponse:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured.",
        )

    category_options = [
        {
            "id": item.get("id"),
            "slug": item.get("slug"),
            "name": item.get("name"),
            "slugs": item.get("slugs", []),
        }
        for item in request.categories
    ]

    prompt = (
        "Bạn là middleware parser cho tìm kiếm sản phẩm điện tử. "
        "Chỉ trả về JSON hợp lệ, không markdown. "
        "Hãy phân tích câu tìm kiếm tiếng Việt của khách hàng thành intent có cấu trúc. "
        "Quy đổi giá: 1 củ = 1 triệu VND, 1 tr = 1 triệu VND, 'đổ lại' nghĩa là maxPrice. "
        "categoryIds chỉ được lấy từ id/slug/slugs trong danh mục được cung cấp. "
        "Nếu người dùng nói máy tính/laptop cho sinh viên IT/code/lập trình, ưu tiên category laptop và specs như ram 16gb, core i5/i7, ryzen 5/7, ssd. "
        "Đừng đưa các từ mô tả nhu cầu như sinh viên, code, mượt vào searchableTerms nếu chúng đã nằm trong useCases/preferredSpecs. "
        "Schema JSON bắt buộc: "
        '{"categoryIds":[],"brand":null,"minPrice":null,"maxPrice":null,'
        '"useCases":[],"preferredSpecs":[],"searchableTerms":[],"confidence":0.0}\n'
        f"Danh mục: {json.dumps(category_options, ensure_ascii=False)}\n"
        f"Hãng có thể có: {json.dumps(request.brands[:100], ensure_ascii=False)}\n"
        f"Câu tìm kiếm: {request.query}"
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": settings.gemini_api_key,
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = _json_from_text(text)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini could not parse the search intent.",
        ) from exc

    return ProductSearchIntentResponse(
        categoryIds=_as_string_list(parsed.get("categoryIds")),
        brand=str(parsed["brand"]).strip() if parsed.get("brand") else None,
        minPrice=_as_price(parsed.get("minPrice")),
        maxPrice=_as_price(parsed.get("maxPrice")),
        useCases=_as_string_list(parsed.get("useCases")),
        preferredSpecs=_as_string_list(parsed.get("preferredSpecs")),
        searchableTerms=_as_string_list(parsed.get("searchableTerms")),
        confidence=float(parsed.get("confidence") or 0),
    )
