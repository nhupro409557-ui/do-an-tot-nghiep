import { getAccessToken, refreshSession } from './authDb';
import { adminCategoriesApi } from './api/adminCategoriesApi';
import { adminProductsApi } from './api/adminProductsApi';
import { adminBrandsApi } from './api/adminBrandsApi';
import { adminVouchersApi } from './api/adminVouchersApi';
import { adminCustomersApi } from './api/adminCustomersApi';
import { adminContentApi } from './api/adminContentApi';
import { normalizeVietnameseEncoding } from '../utils/textEncoding';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const REAL_IMAGES_BY_SKU: Record<string, { imageUrl: string; images: string[] }> = {
  'IP16PM': {
    imageUrl: 'https://images.unsplash.com/photo-1727371978250-b0c6114eb384?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1727371978250-b0c6114eb384?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1727371978280-bc9b0e2730b6?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1727371978240-a15d0124ea4d?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1726853744654-be743df03264?w=600&auto=format&fit=crop'
    ]
  },
  'S24U': {
    imageUrl: 'https://images.unsplash.com/photo-1708649290066-5f617003b930?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1708649290066-5f617003b930?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490710-fa9d6bfd2b0e?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490802-53a5fb4feee6?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490787-8d266e74b5b7?w=600&auto=format&fit=crop'
    ]
  },
  'ZFOLD6': {
    imageUrl: 'https://images.unsplash.com/photo-1658219491763-718bf41160a2?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1658219491763-718bf41160a2?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1695759904263-d343df8996b9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop'
    ]
  },
  'X14U': {
    imageUrl: 'https://images.unsplash.com/photo-1715006020121-cc6672322cb1?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1715006020121-cc6672322cb1?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1715006020138-0a09e02319ef?w=600&auto=format&fit=crop'
    ]
  },
  'OPPFN3': {
    imageUrl: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop'
    ]
  },
  'IPADM4': {
    imageUrl: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1589739900243-4b52cd9b104e?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&auto=format&fit=crop'
    ]
  },
  'MBAIRM3': {
    imageUrl: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1504707748692-419802cf939d?w=600&auto=format&fit=crop'
    ]
  },
  'ROGG14': {
    imageUrl: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop'
    ]
  },
  'APP2USBC': {
    imageUrl: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1588449668365-d15e397f6787?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1505236271233-2f3b9cdb5768?w=600&auto=format&fit=crop'
    ]
  },
  'ANK100W': {
    imageUrl: 'https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop'
    ]
  },
  'AWU2': {
    imageUrl: 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=600&auto=format&fit=crop'
    ]
  },
  'GFENIX7P': {
    imageUrl: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=600&auto=format&fit=crop'
    ]
  },
  'SONYA7IV': {
    imageUrl: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1452784444945-3f422708fe5e?w=600&auto=format&fit=crop'
    ]
  },
  'DJIPOCKET3': {
    imageUrl: 'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&auto=format&fit=crop'
    ]
  },
  'EZC6N': {
    imageUrl: 'https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1528319725582-ddc096101511?w=600&auto=format&fit=crop'
    ]
  }
};

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  if (url.startsWith('/images/')) {
    return url;
  }
  const base = API_BASE_URL.replace('/api/v1', '');
  return `${base}/${url.startsWith('/') ? url.slice(1) : url}`;
}

export function formatProductDemoData(product: any): any {
  if (!product) return product;
  const sku = product.sku;
  const match = REAL_IMAGES_BY_SKU[sku];
  if (match) {
    product.imageUrl = match.imageUrl;
    product.images = match.images;
  } else {
    product.imageUrl = resolveImageUrl(product.imageUrl);
    product.images = (product.images || []).map(resolveImageUrl);
  }
  if (product.variants) {
    product.variants = product.variants.map((v: any) => ({
      ...v,
      imageUrl: resolveImageUrl(v.imageUrl),
      images: (v.images || []).map(resolveImageUrl)
    }));
  }
  return product;
}

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

function getAnalyticsSessionId() {
  const key = 'catalog_analytics_session_id';
  try {
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    const next = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    window.localStorage.setItem(key, next);
    return next;
  } catch {
    return undefined;
  }
}

function getAnalyticsDeviceId() {
  const key = 'catalog_analytics_device_id';
  try {
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    const next = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    window.localStorage.setItem(key, next);
    return next;
  } catch {
    return undefined;
  }
}

function sendAnalyticsEvent(path: string, body: Record<string, unknown>) {
  request(path, {
    method: 'POST',
    body: JSON.stringify({
      sessionId: getAnalyticsSessionId(),
      deviceId: getAnalyticsDeviceId(),
      ...body,
    }),
  }).catch(() => undefined);
}

function normalizeImageSearch(value: unknown) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .toLowerCase()
    .trim();
}

function fallbackTrendScore(product: any) {
  const soldCount = Number(product?.soldCount || 0);
  const favoriteCount = Number(product?.favoriteCount || 0);
  const reviewCount = Number(product?.reviewCount || 0);
  const rating = Number(product?.rating || 0);
  return soldCount * 0.55 + favoriteCount * 0.2 + reviewCount * 0.15 + rating * 5;
}

export const apiDb = {
  ...adminCategoriesApi,
  ...adminProductsApi,
  ...adminBrandsApi,
  ...adminVouchersApi,
  ...adminCustomersApi,
  ...adminContentApi,

  listProducts: async (params: { q?: string; category?: string; brand?: string; minPrice?: number; maxPrice?: number; sort?: string; limit?: number; offset?: number; flashSale?: boolean; featured?: boolean } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.category && params.category !== 'all') search.set('category', params.category);
    if (params.brand && params.brand !== 'all') search.set('brand', params.brand);
    if (params.minPrice !== undefined) search.set('min_price', String(params.minPrice));
    if (params.maxPrice !== undefined && Number.isFinite(params.maxPrice)) search.set('max_price', String(params.maxPrice));
    if (params.sort && params.sort !== 'default') search.set('sort', params.sort);
    if (params.limit !== undefined) search.set('limit', String(params.limit));
    if (params.offset !== undefined) search.set('offset', String(params.offset));
    if (params.flashSale !== undefined) search.set('flash_sale', String(params.flashSale));
    if (params.featured !== undefined) search.set('featured', String(params.featured));
    const list = await request<any[]>(`/catalog/products${search.toString() ? `?${search.toString()}` : ''}`);
    const formatted = list.map(formatProductDemoData);
    if (params.q?.trim()) {
      sendAnalyticsEvent('/catalog/search-events', {
        query: params.q.trim(),
        resultCount: formatted.length,
        productIds: formatted.map((product: any) => product.id).filter(Boolean).slice(0, 50),
      });
    }
    return formatted;
  },
  listRankings: async (params: { period?: string; criteria?: string; category?: string; limit?: number } = {}) => {
    const search = new URLSearchParams();
    search.set('period', params.period || 'month');
    if (params.criteria) search.set('criteria', params.criteria);
    if (params.category && params.category !== 'all') search.set('category', params.category);
    if (params.limit) search.set('limit', String(params.limit));
    const list = await request<any[]>(`/catalog/rankings?${search.toString()}`);
    return list.map(formatProductDemoData);
  },
  listProductImages: async (params: { q?: string; category?: string; page?: number; limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.category && params.category !== 'all') search.set('category', params.category);
    if (params.page) search.set('page', String(params.page));
    if (params.limit) search.set('limit', String(params.limit));
    try {
      return await request<any>(`/catalog/images${search.toString() ? `?${search.toString()}` : ''}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (!message.includes('404')) throw error;

      const page = params.page || 1;
      const limit = params.limit || 30;
      const keyword = normalizeImageSearch(params.q || '');
      const categoryFilter = normalizeImageSearch(params.category || '');
      const products = await apiDb.listProducts();

      const categoriesMap = new Map<string, { label: string; count: number }>();
      const items = products
        .map((product: any) => {
          const baseUrls = Array.isArray(product.images) && product.images.length > 0
            ? product.images
            : product.imageUrl
              ? [product.imageUrl]
              : [];
          const variantUrls = Array.isArray(product.variants)
            ? product.variants.map((variant: any) => variant.imageUrl).filter(Boolean)
            : [];
          const allUrls = Array.from(new Set([...baseUrls, ...variantUrls]));
          if (allUrls.length === 0) return null;

          const categoryName = String(product.categoryName || product.category || '').trim();
          const normalizedCategory = normalizeImageSearch(categoryName);
          if (categoryFilter && normalizedCategory !== categoryFilter) return null;

          const haystack = normalizeImageSearch([product.name, product.brand, categoryName].filter(Boolean).join(' '));
          if (keyword && !haystack.includes(keyword)) return null;

          if (categoryName) {
            const existing = categoriesMap.get(normalizedCategory);
            if (existing) existing.count += 1;
            else categoriesMap.set(normalizedCategory, { label: categoryName, count: 1 });
          }

          return {
            id: product.id,
            productId: product.id,
            productName: product.name,
            brand: product.brand,
            category: categoryName,
            mainUrl: allUrls[0],
            imageCount: allUrls.length,
            trendScore: fallbackTrendScore(product),
            product,
            images: allUrls.map((url, index) => ({
              id: `${product.id}-${index}`,
              url,
              productId: product.id,
              productName: product.name,
              brand: product.brand,
              category: categoryName,
              product,
            })),
          };
        })
        .filter(Boolean)
        .sort((a: any, b: any) => b.trendScore - a.trendScore);

      const totalProducts = items.length;
      const totalImages = items.reduce((sum: number, item: any) => sum + Number(item.imageCount || 0), 0);
      const totalPages = Math.max(1, Math.ceil(totalProducts / limit));
      const start = (page - 1) * limit;
      return {
        items: items.slice(start, start + limit),
        categories: Array.from(categoriesMap.values()).sort((a, b) => b.count - a.count),
        totalImages,
        totalProducts,
        page,
        limit,
        totalPages,
        hasMore: page < totalPages,
      };
    }
  },
  resolveProductImage: async (viewId: string, params: { limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.limit) search.set('limit', String(params.limit));
    return request<any>(`/catalog/images/resolve/${encodeURIComponent(viewId)}${search.toString() ? `?${search.toString()}` : ''}`);
  },
  parseSearchIntent: (data: any) => request<any>('/catalog/search-intent', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminOverview: () => request<any>('/admin/overview'),

  adminListAttachedServices: () => request<any[]>('/admin/attached-services'),
  adminCreateAttachedService: (data: any) => request<{ id: string }>('/admin/attached-services', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateAttachedService: (id: string, data: any) => request(`/admin/attached-services/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteAttachedService: (id: string) => request(`/admin/attached-services/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  getProduct: async (id: string) => {
    const p = await request<any>(`/catalog/products/${encodeURIComponent(id)}`);
    return formatProductDemoData(p);
  },
  recordProductViewHeartbeat: (id: string, data: { activeSeconds: number; scrollDepth: number; source?: string; clientTimestamp?: number }) => request<any>(`/catalog/products/${encodeURIComponent(id)}/view`, {
    method: 'POST',
    body: JSON.stringify({
      sessionId: getAnalyticsSessionId(),
      deviceId: getAnalyticsDeviceId(),
      source: data.source || 'product_detail',
      activeSeconds: data.activeSeconds,
      scrollDepth: data.scrollDepth,
      clientTimestamp: data.clientTimestamp || Date.now(),
    }),
  }),
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
  listProductImageComments: (productId: string) => request<any[]>(`/products/${productId}/image-comments`),
  createProductImageComment: (productId: string, data: any) => request<any>(`/products/${productId}/image-comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  retractProductImageComment: (productId: string, commentId: string) => request<any>(`/products/${productId}/image-comments/${encodeURIComponent(commentId)}`, {
    method: 'DELETE',
  }),
  listNotifications: () => request<any[]>('/notifications'),
  markNotificationsRead: () => request('/notifications/read-all', { method: 'PATCH' }),
  listRewards: () => request<any[]>('/rewards'),
  listVideos: async (params: { page?: number; limit?: number} = {}) => {
    try {
      const search = new URLSearchParams();
      if (params.page) search.set('page', String(params.page));
      if (params.limit) search.set('limit', String(params.limit));
      const data = await request<any>(`/videos${search.toString() ? `?${search.toString()}` : ''}`);
      const items = Array.isArray(data) ? data : data.items || [];
      return items.map((video: any) => {
        if (video.product) {
          video.product = formatProductDemoData(video.product);
        }
        if (video.videoUrl) video.videoUrl = resolveImageUrl(video.videoUrl);
        if (video.thumbnailUrl) video.thumbnailUrl = resolveImageUrl(video.thumbnailUrl);
        return video;
      });
    } catch {
      return [];
    }
  },
  listVideosPage: async (params: { page?: number; limit?: number } = {}) => {
    const search = new URLSearchParams();
    search.set('page', String(params.page || 1));
    search.set('limit', String(params.limit || 24));
    return request<any>(`/videos?${search.toString()}`);
  },
  recordVideoView: (videoId: string, data: any = {}, deviceId?: string) => request<any>(`/videos/${encodeURIComponent(videoId)}/view`, {
    method: 'POST',
    headers: deviceId ? { 'X-Device-Id': deviceId } : undefined,
    body: JSON.stringify(data),
  }),
  toggleVideoLike: (videoId: string) => request<any>(`/videos/${encodeURIComponent(videoId)}/like`, { method: 'POST' }),
  createVideoComment: (videoId: string, data: any) => request<any>(`/videos/${encodeURIComponent(videoId)}/comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  retractVideoComment: (videoId: string, commentId: string) => request<any>(`/videos/${encodeURIComponent(videoId)}/comments/${encodeURIComponent(commentId)}`, { method: 'DELETE' }),
  listAuthSessions: () => request<any[]>('/auth/sessions'),
  revokeAuthSession: (id: string) => request(`/auth/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  toggleFavorite: (productId: string) => request<any>(`/catalog/products/${encodeURIComponent(productId)}/favorite`, { method: 'POST' }),
  listFavorites: async () => {
    const list = await request<any[]>('/catalog/favorites');
    return list.map(formatProductDemoData);
  },
};
