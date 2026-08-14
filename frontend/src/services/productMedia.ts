import { API_BASE_URL } from './apiClient';
import { resolveMediaUrl } from './resolveMediaUrl';

export function resolveImageUrl(url: string | null | undefined): string {
  return resolveMediaUrl(url, API_BASE_URL);
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
