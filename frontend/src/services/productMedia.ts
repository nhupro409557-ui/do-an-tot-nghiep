import { API_BASE_URL } from './apiClient';
import { resolveMediaUrl } from './resolveMediaUrl';

export function resolveImageUrl(url: string | null | undefined): string {
  return resolveMediaUrl(url, API_BASE_URL);
}

export function formatProductMediaDataForBase(product: any, apiBaseUrl: string): any {
  if (!product) return product;
  const resolve = (url: string | null | undefined) => resolveMediaUrl(url, apiBaseUrl);
  product.imageUrl = resolve(product.imageUrl);
  product.images = (product.images || []).map(resolve);
  product.videoUrl = resolve(product.videoUrl);
  if (product.variants) {
    product.variants = product.variants.map((variant: any) => ({
      ...variant,
      imageUrl: resolve(variant.imageUrl),
      images: (variant.images || []).map(resolve),
    }));
  }
  return product;
}

export function formatProductDemoData(product: any): any {
  return formatProductMediaDataForBase(product, API_BASE_URL);
}

export function formatProductAdminMedia(product: any): any {
  return formatProductMediaDataForBase(product, API_BASE_URL);
}

function formatProductImageGalleryItemForBase(item: any, apiBaseUrl: string): any {
  if (!item) return item;
  const resolve = (url: string | null | undefined) => resolveMediaUrl(url, apiBaseUrl);
  return {
    ...item,
    mainUrl: resolve(item.mainUrl),
    url: resolve(item.url),
    product: item.product
      ? formatProductMediaDataForBase({ ...item.product }, apiBaseUrl)
      : item.product,
    images: Array.isArray(item.images)
      ? item.images.map((image: any) => formatProductImageGalleryItemForBase(image, apiBaseUrl))
      : item.images,
    relatedProducts: Array.isArray(item.relatedProducts)
      ? item.relatedProducts.map((product: any) => formatProductMediaDataForBase({ ...product }, apiBaseUrl))
      : item.relatedProducts,
  };
}

export function formatProductImageGalleryDataForBase(data: any, apiBaseUrl: string): any {
  if (!data) return data;
  if (Array.isArray(data)) {
    return data.map((item) => formatProductImageGalleryItemForBase(item, apiBaseUrl));
  }
  if (Array.isArray(data.items)) {
    return {
      ...data,
      items: data.items.map((item: any) => formatProductImageGalleryItemForBase(item, apiBaseUrl)),
      relatedProducts: Array.isArray(data.relatedProducts)
        ? data.relatedProducts.map((product: any) => formatProductMediaDataForBase({ ...product }, apiBaseUrl))
        : data.relatedProducts,
    };
  }
  return formatProductImageGalleryItemForBase(data, apiBaseUrl);
}

export function formatProductImageGalleryData(data: any): any {
  return formatProductImageGalleryDataForBase(data, API_BASE_URL);
}
