import type { CartItem } from '../../../store/cartStore';

export function flashSaleQuantityParts(item: CartItem, remainingQuota?: number | null) {
  const limit = item.isFlashSale && item.flashSalePerUserLimit
    ? Math.max(Number(item.flashSalePerUserLimit), 0)
    : item.quantity;
  const effectiveLimit = remainingQuota === undefined || remainingQuota === null
    ? limit
    : Math.min(limit, Math.max(Number(remainingQuota), 0));
  const saleQuantity = Math.min(item.quantity, effectiveLimit);
  return {
    saleQuantity,
    regularQuantity: Math.max(item.quantity - saleQuantity, 0),
  };
}

export function cartItemEffectiveTotal(item: CartItem, remainingQuota?: number | null) {
  const servicePrice = item.attachedServices?.reduce((sum, service) => sum + service.price, 0) || 0;
  const saleUnitPrice = item.price + servicePrice;
  const regularUnitPrice = Number(item.originalPrice || item.price) + servicePrice;
  const { saleQuantity, regularQuantity } = flashSaleQuantityParts(item, remainingQuota);
  return saleUnitPrice * saleQuantity + regularUnitPrice * regularQuantity;
}

export function flashSalePriceBreakdown(item: CartItem, remainingQuota?: number | null) {
  const servicePrice = item.attachedServices?.reduce((sum, service) => sum + service.price, 0) || 0;
  const { saleQuantity, regularQuantity } = flashSaleQuantityParts(item, remainingQuota);
  return {
    saleQuantity,
    regularQuantity,
    saleUnitPrice: item.price + servicePrice,
    regularUnitPrice: Number(item.originalPrice || item.price) + servicePrice,
  };
}
