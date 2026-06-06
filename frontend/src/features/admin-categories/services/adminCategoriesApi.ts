import { request } from '../../../services/apiClient';

const slugify = (value: string) =>
  value
    .replace(/\u0111/g, 'd')
    .replace(/\u0110/g, 'D')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

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
          specFields: product.specFields || [],
          filterConfig: null,
          order: 99,
          children: [],
        }];
      }),
    ).values(),
  );
}

export const adminCategoriesApi = {
  listCategories: async () => {
    try {
      return await request<any[]>('/catalog/categories');
    } catch {
      const products = await request<any[]>('/catalog/products');
      return deriveCategoriesFromProducts(products);
    }
  },
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
};
