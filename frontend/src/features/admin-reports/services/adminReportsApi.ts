import { request, requestBlob } from '../../../services/apiClient';
import type {
  CustomerReport,
  CustomerRetentionReport,
  OrderReport,
  ProductReport,
  ReportFilters,
  ReportExportJob,
  ReportView,
  RevenueReport,
} from '../types';

function periodParams(filters: ReportFilters) {
  return new URLSearchParams({
    from: filters.from,
    to: filters.to,
    timezone: 'Asia/Bangkok',
  });
}

function revenueParams(filters: ReportFilters) {
  const params = periodParams(filters);
  if (filters.channel) params.set('channel', filters.channel);
  if (filters.paymentMethod) params.set('paymentMethod', filters.paymentMethod);
  return params;
}

function orderParams(filters: ReportFilters) {
  const params = revenueParams(filters);
  params.set('dateBasis', filters.dateBasis);
  if (filters.status) params.set('status', filters.status);
  if (filters.paymentStatus) params.set('paymentStatus', filters.paymentStatus);
  if (filters.fulfillmentMethod) {
    params.set('fulfillmentMethod', filters.fulfillmentMethod);
  }
  if (filters.search) params.set('search', filters.search);
  return params;
}

function customerParams(filters: ReportFilters) {
  const params = periodParams(filters);
  if (filters.tier) params.set('tier', filters.tier);
  if (filters.segment) params.set('segment', filters.segment);
  if (filters.search) params.set('search', filters.search);
  return params;
}

export const adminReportsApi = {
  getRevenue(filters: ReportFilters, signal?: AbortSignal) {
    const params = revenueParams(filters);
    params.set('bucket', 'day');
    return request<RevenueReport>(`/admin/reports/revenue?${params}`, { signal });
  },

  getOrders(filters: ReportFilters, page: number, signal?: AbortSignal) {
    const params = orderParams(filters);
    params.set('page', String(page));
    params.set('limit', '20');
    return request<OrderReport>(`/admin/reports/orders?${params}`, { signal });
  },

  getProducts(filters: ReportFilters, page: number, signal?: AbortSignal) {
    const params = periodParams(filters);
    params.set('page', String(page));
    params.set('limit', '20');
    params.set('sortBy', 'netRevenue');
    params.set('sortOrder', 'desc');
    if (filters.search) params.set('search', filters.search);
    return request<ProductReport>(`/admin/reports/products?${params}`, { signal });
  },

  getCustomers(filters: ReportFilters, page: number, signal?: AbortSignal) {
    const params = customerParams(filters);
    params.set('page', String(page));
    params.set('limit', '20');
    return request<CustomerReport>(`/admin/reports/customers?${params}`, { signal });
  },

  getCustomerRetention(signal?: AbortSignal) {
    return request<CustomerRetentionReport>(
      '/admin/reports/customers/retention?timezone=Asia%2FBangkok&cohortLimit=12',
      { signal },
    );
  },

  exportReport(view: Exclude<ReportView, 'products' | 'inventory'>, filters: ReportFilters) {
    const params = view === 'orders'
      ? orderParams(filters)
      : view === 'customers'
        ? customerParams(filters)
        : revenueParams(filters);
    return requestBlob(`/admin/reports/${view}/export?${params}`);
  },

  createExportJob(
    reportType: 'revenue' | 'orders' | 'customers',
    filters: ReportFilters,
  ) {
    return request<{ jobId: string; status: string }>('/admin/reports/exports', {
      method: 'POST',
      body: JSON.stringify({
        reportType,
        from: filters.from,
        to: filters.to,
        timezone: 'Asia/Bangkok',
        channel: reportType !== 'customers' ? filters.channel || undefined : undefined,
        paymentMethod: reportType !== 'customers'
          ? filters.paymentMethod || undefined
          : undefined,
        status: reportType === 'orders' ? filters.status || undefined : undefined,
        paymentStatus: reportType === 'orders'
          ? filters.paymentStatus || undefined
          : undefined,
        fulfillmentMethod: reportType === 'orders'
          ? filters.fulfillmentMethod || undefined
          : undefined,
        dateBasis: reportType === 'orders' ? filters.dateBasis : undefined,
        tier: reportType === 'customers' ? filters.tier || undefined : undefined,
        segment: reportType === 'customers' ? filters.segment || undefined : undefined,
        search: reportType === 'orders' || reportType === 'customers'
          ? filters.search || undefined
          : undefined,
      }),
    });
  },

  getExportJobs(signal?: AbortSignal) {
    return request<ReportExportJob[]>('/admin/reports/exports', { signal });
  },

  downloadExportJob(jobId: string) {
    return requestBlob(
      `/admin/reports/exports/${encodeURIComponent(jobId)}/download`,
    );
  },
};
