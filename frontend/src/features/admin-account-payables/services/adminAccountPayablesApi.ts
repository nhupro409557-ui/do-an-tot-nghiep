import { request } from '../../../services/apiClient';

export const adminAccountPayablesApi = {
  adminListAccountPayables: (params: { search?: string; status?: string; supplierId?: string; page?: number; pageSize?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set('search', params.search);
    if (params.status && params.status !== 'ALL') query.set('status', params.status);
    if (params.supplierId) query.set('supplierId', params.supplierId);
    query.set('page', String(params.page || 1));
    query.set('pageSize', String(params.pageSize || 50));
    return request<{ items: any[]; page: number; pageSize: number; total: number }>(`/admin/account-payables?${query.toString()}`);
  },
  adminGetAccountPayableSummary: () => request<any>('/admin/account-payables/summary'),
  adminGetAccountPayableDetail: (id: string) => request<any>(`/admin/account-payables/${encodeURIComponent(id)}`),
  adminCreateSupplierPayment: (id: string, data: any, idempotencyKey: string) => request<any>(`/admin/account-payables/${encodeURIComponent(id)}/payments`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(data),
  }),
  adminReverseSupplierPayment: (id: string, paymentId: string, reason: string) => request<any>(`/admin/account-payables/${encodeURIComponent(id)}/payment-reversals`, {
    method: 'POST',
    body: JSON.stringify({ paymentId, reason }),
  }),
  adminCreateAccountPayableAdjustment: (id: string, data: { type: 'DEBIT' | 'CREDIT'; amount: string; reason: string }) => request<any>(`/admin/account-payables/${encodeURIComponent(id)}/adjustments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};
