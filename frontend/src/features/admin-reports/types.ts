export type ReportView = 'revenue' | 'orders' | 'products' | 'customers' | 'inventory';

export type ReportFilters = {
  from: string;
  to: string;
  channel: string;
  paymentMethod: string;
  paymentStatus: string;
  fulfillmentMethod: string;
  status: string;
  dateBasis: 'createdAt' | 'completedAt';
  tier: string;
  segment: string;
  search: string;
};

export type Pagination = {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
};

export type RevenueReport = {
  period: { fromDate: string; toDate: string; timezone: string; bucket: string };
  summary: {
    completedOrders: number;
    grossRevenue: number | string;
    refundAmount: number | string;
    netRevenue: number | string;
    averageOrderValue: number | string;
    costOfGoodsSold?: number | string;
    grossProfit?: number | string;
  };
  comparison: {
    previousNetRevenue: number | string;
    previousCompletedOrders: number;
    revenueChangePercent: number | string | null;
  };
  breakdowns: {
    channels: Array<{
      key: string;
      completedOrders: number;
      netRevenue: number | string;
    }>;
    paymentMethods: Array<{
      key: string;
      completedOrders: number;
      netRevenue: number | string;
    }>;
  };
};

export type OrderReport = {
  summary: {
    totalOrders: number;
    completedOrders: number;
    cancelledOrders: number;
    totalAmount: number | string;
    averageOrderValue: number | string;
  };
  breakdowns: {
    statuses: Array<{ key: string; count: number; amount: number | string }>;
  };
  items: Array<{
    id: string;
    orderCode: string;
    customerName?: string;
    status: string;
    channel: string;
    paymentMethod: string;
    paymentStatus: string;
    fulfillmentMethod: string;
    totalAmount: number | string;
    createdAt: string;
  }>;
  pagination: Pagination;
};

export type ProductReport = {
  summary: {
    totalProducts: number;
    unitsSold: number;
    grossRevenue: number | string;
    allocatedDiscount: number | string;
    refundAmount: number | string;
    netRevenue: number | string;
    unallocatedRefundAmount: number | string;
  };
  items: Array<{
    productId?: string;
    variantId?: string;
    sku: string;
    productName: string;
    unitsSold: number;
    orderCount: number;
    grossRevenue: number | string;
    refundAmount: number | string;
    netRevenue: number | string;
  }>;
  pagination: Pagination;
};

export type CustomerReport = {
  summary: {
    newCustomers: number;
    activeCustomers: number;
    firstTimeBuyers: number;
    returningCustomers: number;
    repeatPurchaseRate: number | string;
  };
  tiers: Array<{ tier: string; customers: number; netRevenue: number | string }>;
  items: Array<{
    id: string;
    fullName: string;
    email: string;
    tier: string;
    registeredAt: string;
    orderCount: number;
    netSpent: number | string;
    segment: string;
  }>;
  pagination: Pagination;
};

export type CustomerRetentionReport = {
  timezone: string;
  cohorts: Array<{
    cohortMonth: string;
    cohortSize: number;
    periods: Array<{
      monthOffset: number;
      customers: number;
      retentionRate: number | string;
    }>;
  }>;
};

export type InventoryAgingReport = {
  asOf: string;
  buckets: Array<{
    bucket: string;
    label: string;
    skuCount: number;
    quantity: number;
    totalCost: number;
  }>;
  items: Array<{
    bucket: string;
    bucketLabel: string;
    productId: string;
    variantId?: string;
    productName: string;
    productSku?: string;
    variantSku?: string;
    locationCode?: string;
    quantity: number;
    totalCost: number;
    maxAgeDays: number;
  }>;
  totalQuantity: number;
  totalCost: number;
  pagination: Pagination;
};

export type InventoryReconciliationReport = {
  asOf: string;
  summary: Array<{ issueType: string; label: string; count: number }>;
  totalIssues: number;
  pagination: Pagination;
  items: Array<{
    issueType: string;
    productId?: string;
    variantId?: string;
    productName?: string;
    productSku?: string;
    variantSku?: string;
    locationCode?: string;
    onHandQuantity?: number;
    identifierQuantity?: number;
    identifierValue?: string;
    message?: string;
  }>;
};

export type ReportExportJob = {
  id: string;
  reportType: 'revenue' | 'orders' | 'customers';
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'EXPIRED';
  filters: Record<string, string>;
  totalRows: number;
  filename?: string;
  expiresAt?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
};
