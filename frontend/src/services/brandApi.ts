import { request } from './apiClient';

export const brandApi = {
  listBrands: () => request<any[]>('/catalog/brands'),
  adminListBrands: (params: { page?: number; limit?: number; search?: string; status?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(Math.min(params.limit, 100)));
    if (params.search) searchParams.set('search', params.search);
    if (params.status && params.status !== 'all') searchParams.set('status', params.status);
    const query = searchParams.toString();
    return request<{ items: any[]; page: number; limit: number; total: number }>(`/admin/brands${query ? `?${query}` : ''}`);
  },
  adminCheckBrandCode: (data: any) => request<{ available: boolean }>('/admin/brands/check-code', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateBrand: (data: any) => request<{ id: string }>('/admin/brands', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateBrand: (id: string, data: any) => request(`/admin/brands/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminImportBrands: (file: File, mode = 'skip') => {
    const formData = new FormData();
    formData.append('mode', mode);
    formData.append('file', file);
    return request<{ jobId: string; status: string }>('/admin/brands/import', {
      method: 'POST',
      body: formData,
    });
  },
  adminListBrandImportJobs: () => request<any[]>('/admin/brands/import-jobs'),
  adminGetBrandImportJob: (id: string) => request<any>(`/admin/brands/import-jobs/${encodeURIComponent(id)}`),
  adminUpdateBrandStatus: (id: string, isActive: boolean) => request(`/admin/brands/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ isActive }),
  }),
  adminUpdateBrandsStatus: (ids: string[], isActive: boolean) => request<{ updated: number; failed: any[] }>('/admin/brands/status', {
    method: 'PATCH',
    body: JSON.stringify({ ids, isActive }),
  }),
  adminDeleteBrand: (id: string) => request(`/admin/brands/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  }),
};
