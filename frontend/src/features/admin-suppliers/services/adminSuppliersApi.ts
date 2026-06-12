import { request } from '../../../services/apiClient';

export const adminSuppliersApi = {
  adminListSuppliers: (params: { page?: number; limit?: number; search?: string; status?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(Math.min(params.limit, 100)));
    if (params.search) searchParams.set('search', params.search);
    if (params.status && params.status !== 'all') searchParams.set('status', params.status);
    const query = searchParams.toString();
    return request<{ items: any[]; page: number; limit: number; total: number }>(`/admin/suppliers${query ? `?${query}` : ''}`);
  },
  adminCheckSupplierCode: (data: any) => request<{ available: boolean }>('/admin/suppliers/check-code', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateSupplier: (data: any) => request<{ id: string }>('/admin/suppliers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateSupplier: (id: string, data: any) => request(`/admin/suppliers/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminUpdateSupplierStatus: (id: string, isActive: boolean) => request(`/admin/suppliers/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ isActive }),
  }),
  adminUpdateSuppliersStatus: (ids: string[], isActive: boolean) => request<{ updated: number; failed: any[] }>('/admin/suppliers/status', {
    method: 'PATCH',
    body: JSON.stringify({ ids, isActive }),
  }),
  adminDeleteSupplier: (id: string) => request(`/admin/suppliers/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  }),
};
