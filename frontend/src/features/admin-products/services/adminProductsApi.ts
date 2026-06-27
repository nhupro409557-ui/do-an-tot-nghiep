import { request, requestBlob } from '../../../services/apiClient';
import { formatProductAdminMedia } from '../../../services/productMedia';

export const adminProductsApi = {
  adminListProducts: async (params: { page?: number; limit?: number; search?: string; status?: string; categoryId?: string; brandId?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.limit) query.set('limit', String(params.limit));
    if (params.search) query.set('search', params.search);
    if (params.status) query.set('status', params.status);
    if (params.categoryId) query.set('categoryId', params.categoryId);
    if (params.brandId) query.set('brandId', params.brandId);
    const result = await request<any[] | { items: any[]; totalRecords?: number; totalPages?: number; page?: number; limit?: number }>(`/admin/products${query.toString() ? `?${query.toString()}` : ''}`);
    if (Array.isArray(result)) return result.map(formatProductAdminMedia);
    return {
      ...result,
      items: (result.items || []).map(formatProductAdminMedia),
    };
  },
  adminCreatePresignedUpload: (data: any) => request<any>('/admin/uploads/presigned-url', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateProduct: (data: any) => request<{ id: string }>('/admin/products', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminImportProducts: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<{ jobId: string; status: string }>('/admin/products/import', {
      method: 'POST',
      body: formData,
    });
  },
  adminListProductImportJobs: () => request<any[]>('/admin/products/import-jobs'),
  adminExportProducts: (filters: Record<string, string> = {}) => request<{ jobId: string; status: string }>('/admin/products/export', {
    method: 'POST',
    body: JSON.stringify(filters),
  }),
  adminListProductExportJobs: () => request<any[]>('/admin/products/export-jobs'),
  adminProductKpis: () => request<any>('/admin/products/kpis'),
  adminUpdateProduct: (id: string, data: any) => request(`/admin/products/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminSubmitProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/submit`, { method: 'POST' }),
  adminApproveProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
  adminReactivateProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/reactivate`, { method: 'POST' }),
  adminHideProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/hide`, { method: 'POST' }),
  adminBulkApproveProducts: (ids: string[]) => request<{ updated: number; skipped: any[] }>('/admin/products/bulk-approve', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  }),
  adminBulkProductAction: (action: 'APPROVE' | 'ARCHIVE' | 'HIDE' | 'RESTORE' | 'DELETE', productIds: string[]) => request<{ updated: number; skipped: any[] }>('/admin/products/bulk-action', {
    method: 'POST',
    body: JSON.stringify({ action, productIds }),
  }),
  adminSuggestProducts: (search: string, excludeId?: string, filters?: { categoryId?: string; brandId?: string }) => {
    const query = new URLSearchParams();
    if (search) query.set('search', search);
    query.set('limit', '50');
    if (excludeId) query.set('excludeId', excludeId);
    if (filters?.categoryId) query.set('categoryId', filters.categoryId);
    if (filters?.brandId) query.set('brandId', filters.brandId);
    return request<any[]>(`/admin/products/suggestions${query.toString() ? `?${query.toString()}` : ''}`);
  },
  adminDuplicateProduct: (id: string) => request<{ id: string }>(`/admin/products/${encodeURIComponent(id)}/duplicate`, { method: 'POST' }),
  adminArchiveProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/archive`, { method: 'POST' }),
  adminDeactivateProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminDeleteProductVariant: (productId: string, variantId: string) => request(`/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}`, { method: 'DELETE' }),
};
