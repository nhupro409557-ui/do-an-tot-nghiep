import { API_BASE_URL } from './apiClient';

const REAL_IMAGES_BY_SKU: Record<string, { imageUrl: string; images: string[] }> = {
  IP16PM: {
    imageUrl: 'https://images.unsplash.com/photo-1727371978250-b0c6114eb384?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1727371978250-b0c6114eb384?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1727371978280-bc9b0e2730b6?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1727371978240-a15d0124ea4d?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1726853744654-be743df03264?w=600&auto=format&fit=crop',
    ],
  },
  S24U: {
    imageUrl: 'https://images.unsplash.com/photo-1708649290066-5f617003b930?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1708649290066-5f617003b930?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490710-fa9d6bfd2b0e?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490802-53a5fb4feee6?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1707920490787-8d266e74b5b7?w=600&auto=format&fit=crop',
    ],
  },
  ZFOLD6: {
    imageUrl: 'https://images.unsplash.com/photo-1658219491763-718bf41160a2?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1658219491763-718bf41160a2?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1695759904263-d343df8996b9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop',
    ],
  },
  X14U: {
    imageUrl: 'https://images.unsplash.com/photo-1715006020121-cc6672322cb1?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1715006020121-cc6672322cb1?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1715006020138-0a09e02319ef?w=600&auto=format&fit=crop',
    ],
  },
  OPPFN3: {
    imageUrl: 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop',
    ],
  },
  IPADM4: {
    imageUrl: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1589739900243-4b52cd9b104e?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&auto=format&fit=crop',
    ],
  },
  MBAIRM3: {
    imageUrl: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1504707748692-419802cf939d?w=600&auto=format&fit=crop',
    ],
  },
  ROGG14: {
    imageUrl: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop',
    ],
  },
  APP2USBC: {
    imageUrl: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1588449668365-d15e397f6787?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1505236271233-2f3b9cdb5768?w=600&auto=format&fit=crop',
    ],
  },
  ANK100W: {
    imageUrl: 'https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop',
    ],
  },
  AWU2: {
    imageUrl: 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=600&auto=format&fit=crop',
    ],
  },
  GFENIX7P: {
    imageUrl: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=600&auto=format&fit=crop',
    ],
  },
  SONYA7IV: {
    imageUrl: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1452784444945-3f422708fe5e?w=600&auto=format&fit=crop',
    ],
  },
  DJIPOCKET3: {
    imageUrl: 'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&auto=format&fit=crop',
    ],
  },
  EZC6N: {
    imageUrl: 'https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop',
    images: [
      'https://images.unsplash.com/photo-1558002038-1055907df827?w=600&auto=format&fit=crop',
      'https://images.unsplash.com/photo-1528319725582-ddc096101511?w=600&auto=format&fit=crop',
    ],
  },
};

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  if (url.startsWith('/images/')) {
    return url;
  }
  const base = API_BASE_URL.replace('/api', '');
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
    product.variants = product.variants.map((variant: any) => ({
      ...variant,
      imageUrl: resolveImageUrl(variant.imageUrl),
      images: (variant.images || []).map(resolveImageUrl),
    }));
  }
  return product;
}
