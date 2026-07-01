import React, { useMemo } from 'react';
import { Gift, PackageCheck, RotateCcw, ShieldCheck, Truck } from 'lucide-react';
import { formatPrice, plainTextFromHtml } from '../utils/ProductDetailUtils';

export interface ProductDetailProps {
  product: any;
}

export function FeatureHighlights({ product }: { product: any }) {
  const features = useMemo(() => {
    const lines = plainTextFromHtml(product.description)
      .split(/[.\n]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 24);

    const fromSpecs = [
      product.specs?.processor && `Hiệu năng mạnh mẽ với ${product.specs.processor}`,
      product.specs?.screenSize && `Màn hình ${product.specs.screenSize} hiển thị sắc nét`,
      product.specs?.camera && `Camera ${product.specs.camera} hỗ trợ chụp ảnh linh hoạt`,
      product.specs?.battery && `Dung lượng pin ${product.specs.battery} đáp ứng nhu cầu cả ngày`,
    ].filter(Boolean) as string[];

    return (lines.length ? lines : fromSpecs).slice(0, 5);
  }, [product]);

  if (!features.length) return null;

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
      <h2 className="mb-3.5 text-lg font-bold text-gray-900">Đặc điểm nổi bật</h2>
      <div className="space-y-2.5">
        {features.map((feature, index) => (
          <div key={feature} className="flex gap-3 text-sm leading-relaxed text-gray-700 bg-gray-50/40 p-2.5 rounded-xl border border-gray-100/50">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-primary">
              {index + 1}
            </span>
            <span>{feature}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function BundleOffers({
  offers,
  price,
  selectedAccessories,
  onChange
}: {
  offers?: any[];
  price: number;
  selectedAccessories: any[];
  onChange: (offer: any, checked: boolean) => void;
}) {
  if (!offers || offers.length === 0) return null;

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="mb-3.5 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <Gift className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Ưu đãi mua kèm</h2>
      </div>
      <div className="space-y-2.5">
        {offers.map((offer) => {
          const offerPrice = accessoryOfferPrice(offer);
          const basePrice = accessoryBasePrice(offer);
          const detail = offer.discountType === 'PERCENT'
            ? `Giảm ${offer.discountValue}% khi mua cùng sản phẩm`
            : `Giảm ${formatPrice(offer.discountValue)} khi mua cùng sản phẩm`;
          const hasStockQuantity = offer.stockQuantity !== undefined && offer.stockQuantity !== null;
          const stockQuantity = Number(offer.stockQuantity || 0);
          const isSellable = offer.isSellable !== false && (!hasStockQuantity || stockQuantity > 0);
          const isChecked = selectedAccessories.some(acc => acc.productId === offer.productId);
          return (
            <label
              key={offer.productId}
              className={`flex items-center gap-3 rounded-xl border p-3 transition-all ${isSellable ? 'cursor-pointer border-gray-100 hover:border-red-100 hover:bg-red-50/30' : 'cursor-not-allowed border-gray-100 bg-gray-50 opacity-70'}`}
            >
              <input
                type="checkbox"
                disabled={!isSellable}
                checked={isChecked}
                onChange={(e) => onChange(offer, e.target.checked)}
                className="h-4 w-4 accent-primary disabled:cursor-not-allowed"
              />
              {offer.imageUrl && (
                <img src={offer.imageUrl} alt={offer.productName} className="h-10 w-10 rounded-lg border border-gray-100 bg-white object-contain" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <div className="truncate text-sm font-bold text-gray-800">{offer.productName}</div>
                  {offer.flashSale && (
                    <span className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold text-amber-800 shrink-0">
                      ⚡ Flash Sale
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">{detail}</div>
                <div className={`text-[11px] font-bold ${isSellable ? 'text-emerald-600' : 'text-red-600'}`}>
                  {isSellable
                    ? (hasStockQuantity ? `Còn ${stockQuantity.toLocaleString('vi-VN')}` : 'Còn hàng')
                    : 'Hết hàng - tạm khóa mua kèm'}
                </div>
                <div className="text-[11px] text-gray-400 line-through">
                  Giá gốc: {formatPrice(basePrice)}
                </div>
              </div>
              <div className={`text-sm font-bold ${isSellable ? 'text-primary' : 'text-gray-400'}`}>{formatPrice(offerPrice)}</div>
            </label>
          );
        })}
      </div>
      <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50/50 px-3 py-2.5 text-xs leading-relaxed text-gray-500">
        Chỉ sản phẩm mua kèm còn hàng mới được chọn. Sản phẩm hết hàng sẽ bị khóa và tổng tiền được tính tại giỏ hàng. Giá sản phẩm hiện tại: <span className="font-bold text-gray-800">{formatPrice(price)}</span>
      </div>
    </section>
  );
}

export function tieredServicePrice(service: any, productPrice: number) {
  const tiers = Array.isArray(service.metadata?.priceTiers) ? service.metadata.priceTiers : [];
  const price = Number(productPrice || 0);
  if (!tiers.length || !price) return null;

  const matchedTier = tiers.find((tier: any) => {
    const min = Number(tier.min || 0);
    const max = tier.max === null || tier.max === undefined ? Number.POSITIVE_INFINITY : Number(tier.max);
    return price >= min && price <= max;
  });
  const tierPrice = Number(matchedTier?.price);
  return Number.isFinite(tierPrice) && tierPrice > 0 ? tierPrice : null;
}

export function getAttachedServicePriceNumeric(service: any, productPrice: number): number {
  const overridePrice = Number(service.overridePrice);
  if (Number.isFinite(overridePrice) && overridePrice > 0) return overridePrice;

  const priceMode = String(service.priceMode || '').toUpperCase();
  if (priceMode === 'FIXED') return Number(service.fixedPrice || 0);
  if (priceMode === 'PERCENT') {
    const percentValue = Number(service.percentValue || 0);
    const baseAmount = Number(service.baseAmount || productPrice || 0);
    return Math.round((baseAmount * percentValue) / 100);
  }
  if (priceMode === 'TIERED_AMOUNT') {
    const tierPrice = tieredServicePrice(service, productPrice);
    return tierPrice || 0;
  }
  return 0;
}

export function attachedServicePrice(service: any, productPrice: number) {
  const overridePrice = Number(service.overridePrice);
  if (Number.isFinite(overridePrice) && overridePrice > 0) return formatPrice(overridePrice);

  const priceMode = String(service.priceMode || '').toUpperCase();
  if (priceMode === 'FIXED') return formatPrice(Number(service.fixedPrice || 0));
  if (priceMode === 'PERCENT') {
    const percentValue = Number(service.percentValue || 0);
    const baseAmount = Number(service.baseAmount || productPrice || 0);
    return `${percentValue}%${baseAmount ? ` - khoảng ${formatPrice(Math.round(baseAmount * percentValue / 100))}` : ''}`;
  }
  if (priceMode === 'TIERED_AMOUNT') {
    const tierPrice = tieredServicePrice(service, productPrice);
    return tierPrice ? formatPrice(tierPrice) : 'Theo mức giá sản phẩm';
  }
  return 'Liên hệ';
}

export function attachedServiceMeta(service: any) {
  const parts = [
    service.durationMonths ? `${service.durationMonths} tháng` : '',
    service.serviceType === 'SUPPORT_SERVICE' ? 'Hỗ trợ' : 'Dịch vụ sản phẩm',
  ].filter(Boolean);
  return parts.join(' · ');
}

export function positiveNumber(value: any) {
  const numericValue = Number(value || 0);
  return Number.isFinite(numericValue) && numericValue > 0 ? numericValue : 0;
}

export function accessoryBasePrice(offer: any): number {
  return positiveNumber(offer?.salePrice)
    || positiveNumber(offer?.normalDiscountPrice)
    || positiveNumber(offer?.originalPrice)
    || positiveNumber(offer?.price);
}

export function accessoryOfferPrice(offer: any): number {
  const configuredPrice = positiveNumber(offer?.price);
  if (configuredPrice > 0) return Math.round(configuredPrice);

  const basePrice = accessoryBasePrice(offer);
  const discountType = String(offer?.discountType || '').toUpperCase();
  const discountValue = Number(offer?.discountValue || 0);

  if (discountType === 'PERCENT') {
    return Math.max(0, Math.round(basePrice * (1 - discountValue / 100)));
  }
  if (['FIXED', 'AMOUNT', 'FIXED_AMOUNT'].includes(discountType)) {
    return Math.max(0, Math.round(basePrice - discountValue));
  }
  return Math.round(basePrice);
}

export function productPolicyHighlights(product: any) {
  const warrantyPolicy = product.salesConfig?.warrantyPolicy || {};
  const warrantyMonths = positiveNumber(warrantyPolicy.warrantyMonths);
  const returnDays = positiveNumber(warrantyPolicy.oneForOneDays);
  const hasWarranty = warrantyPolicy.hasWarranty !== false && warrantyMonths > 0;
  const allowOneForOne = warrantyPolicy.allowOneForOne !== false && returnDays > 0;

  return [
    [ShieldCheck, 'Máy mới 100%', 'Chính hãng, nguyên seal'],
    [
      RotateCcw,
      allowOneForOne ? `Đổi trả ${returnDays} ngày` : 'Đổi trả theo chính sách',
      allowOneForOne ? 'Áp dụng chính sách 1 đổi 1' : 'Theo điều kiện của cửa hàng',
    ],
    [Truck, 'Giao nhanh 2 giờ', 'Nội thành áp dụng'],
    [
      PackageCheck,
      hasWarranty ? `Bảo hành ${warrantyMonths} tháng` : 'Bảo hành theo hãng',
      hasWarranty ? 'Theo chính sách sản phẩm' : 'Tại trung tâm uỷ quyền',
    ],
  ];
}

export function AttachedServices({
  services,
  price,
  selectedServices,
  onChange
}: {
  services?: any[];
  price: number;
  selectedServices: any[];
  onChange: (service: any, checked: boolean) => void;
}) {
  if (!services || services.length === 0) return null;

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="mb-3.5 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
          <ShieldCheck className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Dịch vụ đi kèm</h2>
      </div>
      <div className="space-y-2.5">
        {services.map((service) => {
          const isChecked = selectedServices.some(s => (s.serviceId || s.code) === (service.serviceId || service.code));
          return (
            <label key={service.serviceId || service.code} className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-100 p-3 transition-all hover:border-blue-100 hover:bg-blue-50/30">
              <input
                type="checkbox"
                checked={isChecked}
                onChange={(e) => onChange(service, e.target.checked)}
                className="mt-1 h-4 w-4 accent-primary"
              />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-bold text-gray-800">{service.name}</div>
                <div className="mt-0.5 text-xs text-gray-500">{attachedServiceMeta(service)}</div>
              </div>
              <div className="shrink-0 text-right text-sm font-bold text-primary">{attachedServicePrice(service, price)}</div>
            </label>
          );
        })}
      </div>
      <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50/50 px-3 py-2.5 text-xs leading-relaxed text-gray-500">
        Có thể chọn thêm khi mua, phí dịch vụ sẽ được tính cùng đơn hàng.
      </div>
    </section>
  );
}
