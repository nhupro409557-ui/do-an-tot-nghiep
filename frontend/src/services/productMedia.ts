import { API_BASE_URL } from './apiClient';

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return '';
  if (url.startsWith('data:') || url.startsWith('/images/')) {
    return url;
  }
  const base = API_BASE_URL.replace('/api', '');
  if (url.startsWith('http://localhost:') || url.startsWith('http://127.0.0.1:')) {
    return `${base}${new URL(url).pathname}`;
  }
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  return `${base}/${url.startsWith('/') ? url.slice(1) : url}`;
}

export function formatProductDemoData(product: any): any {
  if (!product) return product;
  product.imageUrl = resolveImageUrl(product.imageUrl);
  product.images = (product.images || []).map(resolveImageUrl);
  if (product.variants) {
    product.variants = product.variants.map((variant: any) => ({
      ...variant,
      imageUrl: resolveImageUrl(variant.imageUrl),
      images: (variant.images || []).map(resolveImageUrl),
    }));
  }
  return product;
}

export function formatProductAdminMedia(product: any): any {
  if (!product) return product;
  product.imageUrl = resolveImageUrl(product.imageUrl);
  product.images = (product.images || []).map(resolveImageUrl);
  if (product.variants) {
    product.variants = product.variants.map((variant: any) => ({
      ...variant,
      imageUrl: resolveImageUrl(variant.imageUrl),
      images: (variant.images || []).map(resolveImageUrl),
    }));
  }
  return product;
}
