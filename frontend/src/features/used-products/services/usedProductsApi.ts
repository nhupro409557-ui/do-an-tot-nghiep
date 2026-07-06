import { request } from '../../../services/apiClient';
import type { StorefrontUsedProductDetail, StorefrontUsedProductsResponse } from '../types';

export type UsedProductFilters = {
  search?: string;
  grade?: string;
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
};
