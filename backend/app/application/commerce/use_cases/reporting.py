from .common import *

class ReportUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def revenue(self) -> RevenueReportResponse:
        report = await commerce_repo.get_revenue_report(self._session)
        return RevenueReportResponse(
            total_orders=report["total_orders"],
            completed_orders=report["completed_orders"],
            total_revenue=report["total_revenue"],
            ai_interactions=report["ai_interactions"],
            loyalty_points_used=report["loyalty_points_used"],
        )


class ShippingQuoteUseCase:
    def __init__(self) -> None:
        self._shipping_pricing = SandboxShippingPricingService()

    async def execute(
        self,
        session: AsyncSession,
        *,
        shipping_address: str,
        subtotal_amount: Decimal,
        item_count: int,
        provider: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ShippingQuoteResponse:
        quote = await self._shipping_pricing.quote(
            session,
            shipping_address=shipping_address,
            subtotal_amount=subtotal_amount,
            item_count=item_count,
            provider=provider,
            lat=lat,
            lng=lng,
        )

        return ShippingQuoteResponse(
            shipping_fee=quote.fee,
            zone=quote.zone,
            estimated_days=quote.estimated_days,
            free_shipping_applied=quote.free_shipping_applied,
            provider=quote.provider,
            service_name=quote.service_name,
            note=quote.note,
        )
