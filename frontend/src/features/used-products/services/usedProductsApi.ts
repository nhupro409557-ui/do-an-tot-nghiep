import { request } from '../../../services/apiClient';
import type { StorefrontUsedProductDetail, StorefrontUsedProductsResponse } from '../types';

export type UsedProductFilters = {
  search?: string;
  grade?: string;
  brandId?: string | number;
  categoryId?: string | number;
  minPrice?: number;
  maxPrice?: number;
  sort?: string;
  page?: number;
  limit?: number;
};

export const usedProductsApi = {
  list: (filters: UsedProductFilters = {}) => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') query.set(key, String(value));
    });
    return request<StorefrontUsedProductsResponse>(`/storefront/used-products${query.size ? `?${query.toString()}` : ''}`);
  },
  detail: (slug: string) => request<StorefrontUsedProductDetail>(`/storefront/used-products/${encodeURIComponent(slug)}`),
  createBuybackRequest: (data: any) => request<{ id: string; requestCode: string }>('/storefront/used-products/buyback-requests', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  listBuybackRequests: (params: { page?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.limit) query.set('limit', String(params.limit));
    return request<any>(`/storefront/used-products/buyback-requests${query.size ? `?${query.toString()}` : ''}`);
  },
};
