from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ReportPeriodResponse(BaseModel):
    fromDate: date
    toDate: date
    timezone: str
    bucket: str


class RevenueSummaryResponse(BaseModel):
    completedOrders: int = Field(ge=0)
    grossRevenue: Decimal
    refundAmount: Decimal
    netRevenue: Decimal
    averageOrderValue: Decimal
    costOfGoodsSold: Decimal | None = None
    grossProfit: Decimal | None = None


class RevenueComparisonResponse(BaseModel):
    previousNetRevenue: Decimal
    previousCompletedOrders: int = Field(ge=0)
    revenueChangePercent: Decimal | None = None
    completedOrdersChangePercent: Decimal | None = None


class RevenueSeriesPointResponse(BaseModel):
    periodStart: date
    grossRevenue: Decimal
    refundAmount: Decimal
    netRevenue: Decimal


class RevenueBreakdownItemResponse(BaseModel):
    key: str
    completedOrders: int = Field(ge=0)
    grossRevenue: Decimal
    refundAmount: Decimal
    netRevenue: Decimal


class RevenueBreakdownsResponse(BaseModel):
    channels: list[RevenueBreakdownItemResponse]
    paymentMethods: list[RevenueBreakdownItemResponse]


class AdminRevenueReportResponse(BaseModel):
    period: ReportPeriodResponse
    summary: RevenueSummaryResponse
    comparison: RevenueComparisonResponse
    series: list[RevenueSeriesPointResponse]
    breakdowns: RevenueBreakdownsResponse


class ReportPaginationResponse(BaseModel):
    page: int = Field(ge=1)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    totalPages: int = Field(ge=0)


class OrderReportSummaryResponse(BaseModel):
    totalOrders: int = Field(ge=0)
    completedOrders: int = Field(ge=0)
    cancelledOrders: int = Field(ge=0)
    totalAmount: Decimal
    averageOrderValue: Decimal


class CountBreakdownItemResponse(BaseModel):
    key: str
    count: int = Field(ge=0)
    amount: Decimal


class OrderReportBreakdownsResponse(BaseModel):
    statuses: list[CountBreakdownItemResponse]
    channels: list[CountBreakdownItemResponse]
    paymentMethods: list[CountBreakdownItemResponse]
    paymentStatuses: list[CountBreakdownItemResponse]
    fulfillmentMethods: list[CountBreakdownItemResponse]


class OrderReportItemResponse(BaseModel):
    id: str
    orderCode: str
    customerName: str | None = None
    email: str | None = None
    status: str
    channel: str
    paymentMethod: str
    paymentStatus: str
    fulfillmentMethod: str
    totalAmount: Decimal
    createdAt: str
    completedAt: str | None = None


class AdminOrderReportResponse(BaseModel):
    period: ReportPeriodResponse
    dateBasis: str
    summary: OrderReportSummaryResponse
    breakdowns: OrderReportBreakdownsResponse
    items: list[OrderReportItemResponse]
    pagination: ReportPaginationResponse


class ProductReportSummaryResponse(BaseModel):
    totalProducts: int = Field(ge=0)
    unitsSold: int
    grossRevenue: Decimal
    allocatedDiscount: Decimal
    refundAmount: Decimal
    netRevenue: Decimal
    unallocatedRefundAmount: Decimal


class ProductReportItemResponse(BaseModel):
    productId: str | None = None
    variantId: str | None = None
    sku: str
    productName: str
    unitsSold: int
    orderCount: int = Field(ge=0)
    grossRevenue: Decimal
    allocatedDiscount: Decimal
    refundAmount: Decimal
    netRevenue: Decimal


class AdminProductReportResponse(BaseModel):
    period: ReportPeriodResponse
    summary: ProductReportSummaryResponse
    items: list[ProductReportItemResponse]
    pagination: ReportPaginationResponse


class CustomerReportSummaryResponse(BaseModel):
    newCustomers: int = Field(ge=0)
    activeCustomers: int = Field(ge=0)
    firstTimeBuyers: int = Field(ge=0)
    returningCustomers: int = Field(ge=0)
    repeatPurchaseRate: Decimal


class CustomerTierBreakdownResponse(BaseModel):
    tier: str
    customers: int = Field(ge=0)
    netRevenue: Decimal


class CustomerReportItemResponse(BaseModel):
    id: str
    fullName: str
    email: str
    tier: str
    registeredAt: str
    orderCount: int = Field(ge=0)
    netSpent: Decimal
    segment: str


class AdminCustomerReportResponse(BaseModel):
    period: ReportPeriodResponse
    summary: CustomerReportSummaryResponse
    tiers: list[CustomerTierBreakdownResponse]
    items: list[CustomerReportItemResponse]
    pagination: ReportPaginationResponse


class RetentionCellResponse(BaseModel):
    monthOffset: int = Field(ge=0)
    customers: int = Field(ge=0)
    retentionRate: Decimal


class CustomerRetentionCohortResponse(BaseModel):
    cohortMonth: date
    cohortSize: int = Field(ge=0)
    periods: list[RetentionCellResponse]


class AdminCustomerRetentionResponse(BaseModel):
    timezone: str
    cohorts: list[CustomerRetentionCohortResponse]


class ReportExportRequest(BaseModel):
    reportType: Literal["revenue", "orders", "customers"]
    fromDate: date = Field(alias="from")
    toDate: date = Field(alias="to")
    timezone: str = Field(default="Asia/Bangkok", max_length=80)
    channel: str | None = Field(default=None, max_length=30)
    paymentMethod: str | None = Field(default=None, max_length=30)
    paymentStatus: str | None = Field(default=None, max_length=30)
    fulfillmentMethod: str | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, max_length=40)
    dateBasis: Literal["createdAt", "completedAt"] = "createdAt"
    tier: str | None = Field(default=None, max_length=30)
    segment: Literal["FIRST_TIME", "RETURNING", "NEW_NO_ORDER"] | None = None
    search: str | None = Field(default=None, max_length=120)
