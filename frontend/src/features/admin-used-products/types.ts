export type UsedProductEvidence = {
  url: string;
  name?: string;
};

export type UsedProductChecklist = {
  imeiVerified: boolean;
  screen: boolean;
  camera: boolean;
  connectivity: boolean;
  biometric: boolean;
  accountUnlocked: boolean;
  dataErased: boolean;
  charging: boolean;
  audioAndButtons: boolean;
};

export type UsedProductIntakeDraft = {
  sourceType: string;
  productId: string;
  externalProductName: string;
  variantId: string;
  imei: string;
  serialNumber: string;
  sellerName: string;
  sellerPhone: string;
  sellerAddress: string;
  sellerIdentityNumber: string;
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
  manufacturerWarrantyEnabled: boolean;
  manufacturerWarrantyProvider: string;
  manufacturerWarrantyActivatedAt: string;
  manufacturerWarrantyTotalMonths: string;
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
  externalProductName?: string | null;
  imei: string;
  sourceType?: string;
  variantSku?: string;
  colorName?: string;
  storage?: string;
  ram?: string;
  sellerName?: string;
  sellerPhone?: string;
  sellerAddress?: string;
  sellerIdentityNumber?: string;
  ownershipConfirmed?: boolean;
  acquisitionPaymentMethod?: string | null;
  acquisitionPaymentReference?: string | null;
  acquisitionPaidAt?: string | null;
  sellerConfirmedAt?: string | null;
  acceptedAt?: string | null;
  proposedAcquisitionPrice?: number | string | null;
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
  actualSoldPrice?: number | string | null;
  refurbishmentCost?: number | string | null;
  actualRepairCost?: number | string | null;
  repairCount?: number | string | null;
  estimatedProfit?: number | string | null;
  inspectionChecklist?: UsedProductChecklist;
  inspectionEvidence?: UsedProductEvidence[];
  listingId?: string | null;
  listingTitle?: string;
  listingDescription?: string;
  listingHighlights?: string[];
  listingImages?: string[];
  listingWarrantyMonths?: number | string | null;
  manufacturerWarrantyEnabled?: boolean;
  manufacturerWarrantyProvider?: string | null;
  manufacturerWarrantyActivatedAt?: string | null;
  manufacturerWarrantyTotalMonths?: number | string | null;
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
  warrantyMonths?: number | string | null;
  manufacturerWarrantyEnabled?: boolean;
  manufacturerWarrantyProvider?: string | null;
  manufacturerWarrantyActivatedAt?: string | null;
  manufacturerWarrantyTotalMonths?: number | string | null;
  manufacturerWarrantyExpiresAt?: string | null;
  manufacturerWarrantyRemainingMonths?: number | null;
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
  actorId?: string | null;
  actorName?: string | null;
  actorEmail?: string | null;
  actorRole?: string | null;
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

export type UsedProductIntakePayload = Omit<UsedProductIntakeDraft, 'productId' | 'externalProductName' | 'variantId' | 'serialNumber' | 'sellerName' | 'sellerPhone' | 'expectedPrice' | 'note'> & {
  productId: string | null;
  externalProductName: string | null;
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
  manufacturerWarrantyEnabled: boolean;
  manufacturerWarrantyProvider: string | null;
  manufacturerWarrantyActivatedAt: string | null;
  manufacturerWarrantyTotalMonths: number | null;
  priceComparisonNote: string | null;
};

export type UsedProductStatusPayload = {
  status: string;
  note?: string;
  sellerAddress?: string | null;
  sellerIdentityNumber?: string | null;
  ownershipConfirmed?: boolean;
  acquisitionPaymentMethod?: string | null;
  acquisitionPaymentReference?: string | null;
};

export type UsedProductRepairPayload = {
  description: string;
  cost: number;
  repairedAt: string | null;
};

export type UsedProductPricePayload = {
  salePrice: number;
  reason: string;
};
