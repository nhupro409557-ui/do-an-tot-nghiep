export type UsedProductEvidence = {
  url: string;
  name?: string;
};

export type UsedProductChecklist = {
  screen: boolean;
  camera: boolean;
  connectivity: boolean;
  biometric: boolean;
  accountUnlocked: boolean;
};

export type UsedProductIntakeDraft = {
  sourceType: string;
  productId: string;
  variantId: string;
  imei: string;
  serialNumber: string;
  sellerName: string;
  sellerPhone: string;
  expectedPrice: string;
  note: string;
};

export type UsedProductInspectionDraft = {
  outcome: string;
  conditionGrade: string;
  conditionScore: string;
  batteryHealth: string;
  repairCostEstimate: string;
  proposedAcquisitionPrice: string;
  proposedSalePrice: string;
  note: string;
  evidence: UsedProductEvidence[];
  checklist: UsedProductChecklist;
};

export type UsedProductListingDraft = {
  title: string;
  description: string;
  highlightsText: string;
  images: string[];
  warrantyMonths: string;
  priceComparisonNote: string;
};

export type SourceProductVariant = {
  id: string | number;
  sku?: string;
  colorName?: string;
  storage?: string;
  ram?: string;
  configuration?: string;
  [key: string]: unknown;
};

export type SourceProduct = {
  id: string | number;
  name: string;
  variants?: SourceProductVariant[];
  [key: string]: unknown;
};

export type UsedProductIntake = {
  id: string;
  requestCode: string;
  productName: string;
  imei: string;
  sourceType?: string;
  variantSku?: string;
  colorName?: string;
  storage?: string;
  ram?: string;
  sellerName?: string;
  sellerPhone?: string;
  expectedPrice?: number | string | null;
  conditionGrade?: string;
  conditionScore?: number | string | null;
  batteryHealth?: number | string | null;
  proposedSalePrice?: number | string | null;
  status?: string;
  [key: string]: unknown;
};

export type UsedProductDevice = {
  id: string;
  deviceCode: string;
  productName: string;
  imei: string;
  status: string;
  conditionGrade?: string;
  conditionScore?: number | string | null;
  batteryHealth?: number | string | null;
  approvedSalePrice?: number | string | null;
  refurbishmentCost?: number | string | null;
  inspectionChecklist?: UsedProductChecklist;
  inspectionEvidence?: UsedProductEvidence[];
  listingId?: string | null;
  listingTitle?: string;
  listingDescription?: string;
  listingHighlights?: string[];
  listingImages?: string[];
  listingWarrantyMonths?: number | string | null;
  priceComparisonNote?: string;
  locationCode?: string;
  locationName?: string;
  originalSnapshot?: {
    newReferencePrice?: number | string | null;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

export type UsedProductListing = {
  id: string;
  title: string;
  slug: string;
  deviceCode: string;
  conditionGrade?: string;
  imei: string;
  salePrice?: number | string | null;
  images?: string[];
  status: string;
  [key: string]: unknown;
};

export type UsedProductHistoryEntry = {
  entryType: string;
  title: string;
  createdAt?: string | null;
  oldStatus?: string | null;
  newStatus?: string | null;
  note?: string | null;
  outcome?: string | null;
  conditionGrade?: string | null;
  conditionScore?: number | string | null;
  batteryHealth?: number | string | null;
  repairCostEstimate?: number | string | null;
  proposedSalePrice?: number | string | null;
  approvedSalePrice?: number | string | null;
  [key: string]: unknown;
};

export type UsedProductHistory = {
  device?: Partial<UsedProductDevice>;
  items?: UsedProductHistoryEntry[];
};

export type UsedProductIntakeListResponse = {
  items: UsedProductIntake[];
  total?: number;
  limit?: number;
  offset?: number;
};

export type UsedProductIntakePayload = Omit<UsedProductIntakeDraft, 'variantId' | 'serialNumber' | 'sellerName' | 'sellerPhone' | 'expectedPrice' | 'note'> & {
  variantId: string | null;
  serialNumber: string | null;
  sellerName: string | null;
  sellerPhone: string | null;
  expectedPrice: number | null;
  note: string | null;
};

export type UsedProductInspectionPayload = Omit<
  UsedProductInspectionDraft,
  'conditionScore' | 'batteryHealth' | 'repairCostEstimate' | 'proposedAcquisitionPrice' | 'proposedSalePrice'
> & {
  conditionScore: number | null;
  batteryHealth: number | null;
  repairCostEstimate: number;
  proposedAcquisitionPrice: number | null;
  proposedSalePrice: number | null;
};

export type UsedProductListingPayload = {
  title: string;
  description: string;
  highlights: string[];
  images: string[];
  warrantyMonths: number;
  priceComparisonNote: string | null;
};

export type UsedProductStatusPayload = {
  status: string;
  note?: string;
};
