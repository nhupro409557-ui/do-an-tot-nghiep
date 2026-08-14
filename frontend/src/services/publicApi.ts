import { request } from './apiClient';
import { formatVideoMediaData } from './contentMedia';
import { formatProductDemoData, formatProductImageGalleryData, resolveImageUrl } from './productMedia';

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

export const publicApi = {
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
        productIds: formatted.flatMap((product: any) => product.id ? [product.id] : []).slice(0, 50),
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
      const data = await request<any>(`/catalog/images${search.toString() ? `?${search.toString()}` : ''}`);
      return formatProductImageGalleryData(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (!message.includes('404')) throw error;

      const page = params.page || 1;
      const limit = params.limit || 30;
      const keyword = normalizeImageSearch(params.q || '');
      const categoryFilter = normalizeImageSearch(params.category || '');
      const products = await publicApi.listProducts();

      const categoriesMap = new Map<string, { label: string; count: number }>();
      const items = products
        .flatMap((product: any) => {
          const baseUrls = Array.isArray(product.images) && product.images.length > 0
            ? product.images
            : product.imageUrl
              ? [product.imageUrl]
              : [];
          const variantUrls = Array.isArray(product.variants)
            ? product.variants.flatMap((variant: any) => variant.imageUrl ? [variant.imageUrl] : [])
            : [];
          const allUrls = Array.from(new Set([...baseUrls, ...variantUrls]));
          if (allUrls.length === 0) return [];

          const categoryName = String(product.categoryName || product.category || '').trim();
          const normalizedCategory = normalizeImageSearch(categoryName);
          if (categoryFilter && normalizedCategory !== categoryFilter) return [];

          const haystack = normalizeImageSearch([product.name, product.brand, categoryName].flatMap(value => value ? [value] : []).join(' '));
          if (keyword && !haystack.includes(keyword)) return [];

          if (categoryName) {
            const existing = categoriesMap.get(normalizedCategory);
            if (existing) existing.count += 1;
            else categoriesMap.set(normalizedCategory, { label: categoryName, count: 1 });
          }

          return [{
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
          }];
        })
        .sort((a: any, b: any) => b.trendScore - a.trendScore);

      const totalProducts = items.length;
      const totalImages = items.reduce((sum: number, item: any) => sum + Number(item.imageCount || 0), 0);
      const totalPages = Math.max(1, Math.ceil(totalProducts / limit));
      const start = (page - 1) * limit;
      return formatProductImageGalleryData({
        items: items.slice(start, start + limit),
        categories: Array.from(categoriesMap.values()).sort((a, b) => b.count - a.count),
        totalImages,
        totalProducts,
        page,
        limit,
        totalPages,
        hasMore: page < totalPages,
      });
    }
  },

  resolveProductImage: async (viewId: string, params: { limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.limit) search.set('limit', String(params.limit));
    const data = await request<any>(`/catalog/images/resolve/${encodeURIComponent(viewId)}${search.toString() ? `?${search.toString()}` : ''}`);
    return formatProductImageGalleryData(data);
  },

  parseSearchIntent: (data: any) => request<any>('/catalog/search-intent', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  adminOverview: () => request<any>('/admin/overview'),

  getProduct: async (id: string) => {
    const product = await request<any>(`/catalog/products/${encodeURIComponent(id)}`);
    return formatProductDemoData(product);
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

  listReviews: (productId: string) => request<any[]>(`/products/${productId}/reviews`),
  reviewEligibility: (productId: string) => request<any>(`/products/${productId}/reviews/eligibility`),
  createReview: (productId: string, data: any) => request<{ id: string; status: string; message: string }>(`/products/${productId}/reviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  uploadReviewImages: (productId: string, files: File[]) => {
    const body = new FormData();
    files.forEach(file => body.append('files', file));
    return request<Array<{ url: string }>>(`/products/${encodeURIComponent(productId)}/reviews/images`, {
      method: 'POST',
      body,
    });
  },
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
  listProductQuestions: (productId: string) => request<any[]>(`/products/${productId}/questions`),
  createProductQuestion: (productId: string, data: any) => request<any>(`/products/${productId}/questions`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  retractProductQuestion: (productId: string, commentId: string) => request<any>(`/products/${productId}/questions/${encodeURIComponent(commentId)}`, {
    method: 'DELETE',
  }),

  listNotifications: () => request<any[]>('/notifications'),
  markNotificationsRead: () => request('/notifications/read-all', { method: 'PATCH' }),
  listRewards: () => request<any[]>('/rewards'),

  listVideos: async (params: { page?: number; limit?: number } = {}) => {
    try {
      const search = new URLSearchParams();
      if (params.page) search.set('page', String(params.page));
      if (params.limit) search.set('limit', String(params.limit));
      const data = await request<any>(`/videos${search.toString() ? `?${search.toString()}` : ''}`);
      const items = Array.isArray(data) ? data : data.items || [];
      return items.map(formatVideoMediaData);
    } catch {
      return [];
    }
  },
  listVideosPage: async (params: { page?: number; limit?: number } = {}) => {
    const search = new URLSearchParams();
    search.set('page', String(params.page || 1));
    search.set('limit', String(params.limit || 24));
    const data = await request<any>(`/videos?${search.toString()}`);
    const items = (Array.isArray(data) ? data : data.items || []).map(formatVideoMediaData);
    return Array.isArray(data) ? items : { ...data, items };
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
  getShippingConfig: () => request<{ free_shipping_threshold: number }>('/shipping-config'),
  listMyFlashSaleQuotas: () => request<any[]>('/flash-sales/me/quotas'),
};
