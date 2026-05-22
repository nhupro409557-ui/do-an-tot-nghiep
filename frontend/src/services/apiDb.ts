import { getAccessToken, refreshSession } from './authDb';
import { normalizeVietnameseEncoding } from '../utils/textEncoding';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let token = getAccessToken();
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  if (response.status === 401) {
    try {
      await refreshSession();
      token = getAccessToken();
      const retryHeaders: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' };
      if (token) retryHeaders.Authorization = `Bearer ${token}`;
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: 'include',
        headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
      });
    } catch {
      // Keep the original 401 response for normal error handling below.
    }
  }
  const body = normalizeVietnameseEncoding(await response.json().catch(() => ({})));
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : body.detail ? JSON.stringify(body.detail) : 'Không thể tải dữ liệu từ hệ thống.');
  }
  return body as T;
}

async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  let token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  if (response.status === 401) {
    await refreshSession().catch(() => undefined);
    token = getAccessToken();
    const retryHeaders: Record<string, string> = {};
    if (token) retryHeaders.Authorization = `Bearer ${token}`;
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
    });
  }
  if (!response.ok) {
    throw new Error('Không thể xuất dữ liệu tồn kho.');
  }
  return response.blob();
}

function deriveCategoriesFromProducts(products: any[]) {
  return Array.from(
    new Map(
      products.map((product: any) => {
        const slug = product.categorySlug || slugify(product.category || 'san-pham');
        return [slug, {
          id: product.categoryId || slug,
          parentId: null,
          code: slug.toUpperCase().replace(/-/g, '_'),
          slug,
          name: product.category || slug,
          icon: slug,
          iconUrl: null,
          bannerUrl: null,
          seoTitle: null,
          seoDescription: null,
          seoKeywords: null,
          specFields: product.specFields || [],
          filterConfig: null,
          order: 99,
          children: [],
        }];
      }),
    ).values(),
  );
}

function deriveBrandsFromProducts(products: any[]) {
  const byBrand = new Map<string, any>();
  products.forEach((product: any) => {
    const name = String(product.brand || '').trim();
    if (!name) return;
    const slug = slugify(name);
    const existing = byBrand.get(slug);
    const categoryEntry = product.categorySlug && product.category
      ? { id: product.categorySlug, code: String(product.category).toUpperCase(), slug: product.categorySlug, name: product.category }
      : null;
    if (!existing) {
      byBrand.set(slug, {
        id: slug,
        code: slug.toUpperCase().replace(/-/g, '_'),
        slug,
        name,
        logoUrl: null,
        logoAltText: null,
        landingTitle: `San pham ${name}`,
        seoTitle: null,
        seoDescription: null,
        categoryIds: categoryEntry ? [categoryEntry.id] : [],
        categorySlugs: categoryEntry ? [categoryEntry.slug] : [],
        categories: categoryEntry ? [categoryEntry] : [],
      });
      return;
    }
    if (categoryEntry && !existing.categories.some((item: any) => item.slug === categoryEntry.slug)) {
      existing.categories.push(categoryEntry);
    }
    if (categoryEntry && !existing.categoryIds.includes(categoryEntry.id)) {
      existing.categoryIds.push(categoryEntry.id);
    }
    if (categoryEntry && !existing.categorySlugs.includes(categoryEntry.slug)) {
      existing.categorySlugs.push(categoryEntry.slug);
    }
  });
  return Array.from(byBrand.values());
}

function deriveBrandLanding(slug: string, products: any[], brands: any[], params: { page?: number; limit?: number } = {}) {
  const brand = brands.find((item: any) => item.slug === slug || slugify(item.name || '') === slug);
  if (!brand) return null;
  const brandProducts = products.filter((product: any) => slugify(product.brand || '') === brand.slug);
  const page = params.page || 1;
  const limit = params.limit || 24;
  const start = (page - 1) * limit;
  const pagedProducts = brandProducts.slice(start, start + limit);
  return {
    brand: {
      ...brand,
      cacheVersion: 1,
      order: brand.order || 0,
    },
    products: pagedProducts,
    pagination: {
      page,
      limit,
      total: brandProducts.length,
    },
  };
}

async function listProductsFallback() {
  return request<any[]>('/catalog/products');
}

export const apiDb = {
  listCategories: async () => {
    try {
      return await request<any[]>('/catalog/categories');
    } catch {
      const products = await listProductsFallback();
      return deriveCategoriesFromProducts(products);
    }
  },
  listBrands: async () => {
    try {
      return await request<any[]>('/catalog/brands');
    } catch {
      const products = await listProductsFallback();
      return deriveBrandsFromProducts(products);
    }
  },
  getBrandLanding: async (slug: string, params: { page?: number; limit?: number } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    try {
      return await request<any>(`/storefront/brands/${encodeURIComponent(slug)}${query ? `?${query}` : ''}`);
    } catch {
      const products = await listProductsFallback();
      const brands = deriveBrandsFromProducts(products);
      const fallback = deriveBrandLanding(slug, products, brands, params);
      if (!fallback) throw new Error('Khong tim thay thuong hieu.');
      return fallback;
    }
  },
  listProducts: () => request<any[]>('/catalog/products'),
  listRankings: (period = 'month') => request<any[]>(`/catalog/rankings?period=${encodeURIComponent(period)}`),
  parseSearchIntent: (data: any) => request<any>('/catalog/search-intent', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminOverview: () => request<any>('/admin/overview'),
  adminListCategories: () => request<any[]>('/admin/categories'),
  adminCheckCategorySlug: (data: any) => request<{ available: boolean }>('/admin/categories/check-slug', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateCategory: (data: any) => request<{ id: string }>('/admin/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateCategory: (id: string, data: any) => request(`/admin/categories/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminReorderCategories: (items: any[]) => request('/admin/categories/reorder', {
    method: 'PATCH',
    body: JSON.stringify({ items }),
  }),
  adminBulkUpdateCategories: (data: any) => request<{ updated: number }>('/admin/categories/bulk', {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  getCategoryRedirect: (slug: string) => request<any>(`/catalog/redirects/${encodeURIComponent(slug)}`),
  adminRestoreCategory: (id: string) => request(`/admin/categories/${encodeURIComponent(id)}/restore`, { method: 'PATCH' }),
  adminDeleteCategory: (id: string) => request(`/admin/categories/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminCategoryMetrics: () => request<any>('/admin/categories/ops/metrics'),
  adminCategoryAuditLogs: (id: string) => request<any[]>(`/admin/categories/${encodeURIComponent(id)}/audit-logs`),
  adminCategoryMigrationJobs: (id: string) => request<any[]>(`/admin/categories/${encodeURIComponent(id)}/migration-jobs`),
  adminListBrands: (params: { page?: number; limit?: number; search?: string; status?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(params.limit));
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
  adminUpdateBrand: (id: string, data: any) => request(`/admin/brands/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminUpdateBrandStatus: (id: string, isActive: boolean) => request(`/admin/brands/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ isActive }),
  }),
  adminUpdateBrandsStatus: (ids: string[], isActive: boolean) => request<{ updated: number; failed: any[] }>('/admin/brands/status', {
    method: 'PATCH',
    body: JSON.stringify({ ids, isActive }),
  }),
  adminDeleteBrand: (id: string) => request(`/admin/brands/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminListProducts: () => request<any[]>('/admin/products'),
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
  adminBulkApproveProducts: (ids: string[]) => request<{ updated: number; skipped: any[] }>('/admin/products/bulk-approve', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  }),
  adminBulkProductAction: (action: 'APPROVE' | 'ARCHIVE' | 'DELETE', productIds: string[]) => request<{ updated: number; skipped: any[] }>('/admin/products/bulk-action', {
    method: 'POST',
    body: JSON.stringify({ action, productIds }),
  }),
  adminSuggestProducts: (search: string, excludeId?: string) => {
    const query = new URLSearchParams();
    if (search) query.set('search', search);
    if (excludeId) query.set('excludeId', excludeId);
    return request<any[]>(`/admin/products/suggestions${query.toString() ? `?${query.toString()}` : ''}`);
  },
  adminDuplicateProduct: (id: string) => request<{ id: string }>(`/admin/products/${encodeURIComponent(id)}/duplicate`, { method: 'POST' }),
  adminArchiveProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}/archive`, { method: 'POST' }),
  adminGetProductInventory: (id: string) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory`),
  adminAdjustInventory: (id: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory/adjust`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateInventoryPolicy: (id: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory/policy`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminExportInventory: (search = '') => requestBlob(`/admin/inventory/export${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminSetVariantInventory: (productId: string, variantId: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}/inventory`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeactivateProduct: (id: string) => request(`/admin/products/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminListVouchers: () => request<any[]>('/admin/vouchers'),
  adminCreateVoucher: (data: any) => request<{ id: string }>('/admin/vouchers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateVoucher: (id: string, data: any) => request(`/admin/vouchers/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteVoucher: (id: string) => request(`/admin/vouchers/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  claimVoucher: (voucherId: string, userId: string) => request<any>(`/vouchers/${encodeURIComponent(voucherId)}/claim`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  }),
  listUserVouchers: (userId: string) => request<any[]>(`/users/${encodeURIComponent(userId)}/vouchers`),
  adminListPolicies: () => request<any[]>('/admin/policies'),
  adminGetPolicyHistory: (id: string) => request<any[]>(`/admin/policies/${encodeURIComponent(id)}/history`),
  adminCreatePolicy: (data: any) => request<{ id: string }>('/admin/policies', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdatePolicy: (id: string, data: any) => request(`/admin/policies/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeletePolicy: (id: string) => request(`/admin/policies/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  listStorefrontPolicies: (params: { code?: string; productId?: string; categoryId?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.code) searchParams.set('code', params.code);
    if (params.productId) searchParams.set('product_id', params.productId);
    if (params.categoryId) searchParams.set('category_id', params.categoryId);
    const query = searchParams.toString();
    return request<any[]>(`/storefront/policies${query ? `?${query}` : ''}`);
  },
  adminListCustomers: (params: { search?: string; page?: number; limit?: number } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.set('search', params.search);
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return request<{ items: any[]; page: number; limit: number; total: number }>(`/admin/customers${query ? `?${query}` : ''}`);
  },
  adminGetCustomerDetail: (id: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}`),
  adminGetCustomerOverview: (id: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}/overview`),
  adminGetCustomerOrders: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/orders`),
  adminGetCustomerLoyaltyHistory: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/loyalty-history`),
  adminGetCustomerNotes: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/notes`),
  adminGetCustomerAuditLogs: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/audit-logs`),
  adminUpdateCustomerTags: (id: string, tags: string[]) => request<any>(`/admin/customers/${encodeURIComponent(id)}/tags`, {
    method: 'PUT',
    body: JSON.stringify({ tags }),
  }),
  adminBulkUpdateCustomerTags: (userIds: string[], tags: string[]) => request<any>('/admin/customers/tags/bulk', {
    method: 'PUT',
    body: JSON.stringify({ userIds, tags }),
  }),
  adminCreateCustomerNote: (id: string, content: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}/notes`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  }),
  adminAdjustCustomerLoyalty: (id: string, data: { delta: number; reason: string }) => request<any>(`/admin/customers/${encodeURIComponent(id)}/loyalty-adjustments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminIssueCustomerVoucher: (id: string, data: { voucherId: string; note?: string }) => request<any>(`/admin/customers/${encodeURIComponent(id)}/vouchers`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminBulkUpdateUserStatus: (userIds: string[], status: string) => request<any>('/admin/users/status/bulk', {
    method: 'PATCH',
    body: JSON.stringify({ userIds, status }),
  }),
  adminUpdateUserRole: (id: string, data: any) => request(`/admin/users/${encodeURIComponent(id)}/role`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListPermissions: () => request<any[]>('/admin/permissions'),
  adminListRoles: () => request<any[]>('/admin/roles'),
  adminGetRolePermissions: (id: string) => request<any>(`/admin/roles/${encodeURIComponent(id)}/permissions`),
  adminUpdateRolePermissions: (id: string, permissionCodes: string[]) => request<any>(`/admin/roles/${encodeURIComponent(id)}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissionCodes }),
  }),
  adminListAuditLogs: (params: Record<string, string | number> = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== '').map(([key, value]) => [key, String(value)]));
    return request<any[]>(`/admin/audit-logs${query.toString() ? `?${query.toString()}` : ''}`);
  },
  adminListReviews: () => request<any[]>('/admin/reviews'),
  adminListReviewSummary: () => request<any[]>('/admin/reviews/summary'),
  adminUpdateReview: (id: string, data: any) => request(`/admin/reviews/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteReview: (id: string) => request(`/admin/reviews/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminListContent: () => request<any[]>('/admin/content'),
  adminCreateContent: (data: any) => request<{ id: string }>('/admin/content', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateContent: (id: string, data: any) => request(`/admin/content/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteContent: (id: string) => request(`/admin/content/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  getProduct: (id: string) => request<any>(`/catalog/products/${encodeURIComponent(id)}`),
  createProduct: (data: any) => request<{ id: string }>('/catalog/products', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  listOrders: (userId?: string) => request<any[]>(`/orders${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`),
  getOrderDetail: (id: string) => request<any>(`/orders/${encodeURIComponent(id)}`),
  quoteShipping: (data: any) => request<any>('/orders/shipping-quote', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  createOrder: (data: any) => request<any>('/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateOrderStatus: (id: string, status: string) => request(`/orders/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  adminUpdateOrder: (id: string, data: any) => request(`/orders/${encodeURIComponent(id)}/admin`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  validateVoucher: (code: string, subtotalAmount: number, context: Record<string, unknown> = {}) => request<any>('/vouchers/validate', {
    method: 'POST',
    body: JSON.stringify({ code, subtotal_amount: subtotalAmount, ...context }),
  }),
  listReviews: (productId: string) => request<any[]>(`/products/${productId}/reviews`),
  reviewEligibility: (productId: string) => request<any>(`/products/${productId}/reviews/eligibility`),
  createReview: (productId: string, data: any) => request<{ id: string; status: string; message: string }>(`/products/${productId}/reviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateOwnReview: (productId: string, reviewId: string, data: any) => request<{ ok: boolean; status: string; message: string }>(`/products/${productId}/reviews/${encodeURIComponent(reviewId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteOwnReview: (productId: string, reviewId: string) => request<{ ok: boolean }>(`/products/${productId}/reviews/${encodeURIComponent(reviewId)}`, {
    method: 'DELETE',
  }),
  listNotifications: () => request<any[]>('/notifications'),
  markNotificationsRead: () => request('/notifications/read-all', { method: 'PATCH' }),
  listRewards: () => request<any[]>('/rewards'),
  listVideos: async () => {
    try {
      const data = await request<any>('/videos');
      return Array.isArray(data) ? data : data.items || [];
    } catch {
      return [];
    }
  },
  listAuthSessions: () => request<any[]>('/auth/sessions'),
  revokeAuthSession: (id: string) => request(`/auth/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
