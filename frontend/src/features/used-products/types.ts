export type UsedProductOriginalSnapshot = {
  newReferencePrice?: number | string | null;
  productSpecs?: Record<string, unknown>;
  variantSpecs?: Record<string, unknown>;
  colorName?: string | null;
  storage?: string | null;
  ram?: string | null;
  configuration?: string | null;
  [key: string]: unknown;
};

export type StorefrontUsedProductListItem = {
  id: string;
  slug: string;
  title: string;
  images?: string[];
  conditionGrade?: string;
  batteryHealth?: number | string | null;
  warrantyMonths?: number | string | null;
  salePrice?: number | string | null;
  originalSnapshot?: UsedProductOriginalSnapshot;
  [key: string]: unknown;
};

export type StorefrontUsedProductsResponse = {
  items: StorefrontUsedProductListItem[];
  total?: number;
  limit?: number;
  offset?: number;
};

export type StorefrontUsedProductDetail = StorefrontUsedProductListItem & {
  description?: string;
  deviceCode: string;
  deviceId: string;
  productId?: string | number | null;
  maskedImei?: string;
  priceComparisonNote?: string | null;
  inspectionChecklist?: Record<string, boolean>;
};
