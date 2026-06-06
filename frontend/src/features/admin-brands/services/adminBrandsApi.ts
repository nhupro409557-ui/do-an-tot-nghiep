import { request } from '../../../services/apiClient';

const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

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
        landingTitle: `Sản phẩm ${name}`,
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

export const adminBrandsApi = {
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
};
