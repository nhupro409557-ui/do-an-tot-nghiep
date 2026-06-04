import React from 'react';
import { Check, ShoppingCart, Minus, Plus, Zap, Gift } from 'lucide-react';
import {
  formatPrice,
  variantConfigLabel,
  variantSpecValue,
  sameOptionValue,
  colorFallback,
} from './ProductDetailUtils';

interface ProductPurchaseActionsProps {
  product: any;
  activeVariant: any;
  displayPrice: number;
  displayOriginalPrice: number | null;
  monthlyPrice: number;
  discount: number;
  activeFlashSale: any;
  ramOptions: any[];
  storageOptions: any[];
  configurationOptions: any[];
  colorOptions: any[];
  selectedRam: string;
  selectedStorage: string;
  selectedConfiguration: string;
  selectedColor: string;
  selectRam: (ram: string) => void;
  selectStorage: (storage: string) => void;
  selectConfiguration: (config: string) => void;
  selectColor: (color: string) => void;
  quantity: number;
  setQuantity: (qty: number) => void;
  handleBuyNow: () => void;
  handleAddToCart: () => void;
  addedToCart: boolean;
  variantsForColor: any[];
  selectedCapacity?: string;
}

export function ProductPurchaseActions({
  product,
  activeVariant,
  displayPrice,
  displayOriginalPrice,
  monthlyPrice,
  discount,
  activeFlashSale,
  ramOptions,
  storageOptions,
  configurationOptions,
  colorOptions,
  selectedRam,
  selectedStorage,
  selectedConfiguration,
  selectedColor,
  selectRam,
  selectStorage,
  selectConfiguration,
  selectColor,
  quantity,
  setQuantity,
  handleBuyNow,
  handleAddToCart,
  addedToCart,
  variantsForColor,
  selectedCapacity = '',
}: ProductPurchaseActionsProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-red-100 bg-red-50/40 p-3.5">
        {activeFlashSale && discount > 0 && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-primary px-3 py-2 text-white">
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-wide">
              <Zap className="h-4 w-4 fill-white" />
              Flash sale đang diễn ra
            </div>
            <div className="text-xs font-semibold">
              Giảm {activeFlashSale.discountType === 'PERCENT' ? `${activeFlashSale.discountValue}%` : formatPrice(displayOriginalPrice ? displayOriginalPrice - displayPrice : 0)}
              {activeFlashSale.endsAt ? ` · Kết thúc ${new Date(activeFlashSale.endsAt).toLocaleString('vi-VN')}` : ' · Không có thời hạn'}
            </div>
          </div>
        )}
        <div className="flex flex-wrap items-end gap-2">
          <span className="text-3xl font-black text-primary">{formatPrice(displayPrice)}</span>
          {displayOriginalPrice && displayOriginalPrice > displayPrice && (
            <span className="pb-1 text-base font-medium text-gray-400 line-through">
              {formatPrice(displayOriginalPrice)}
            </span>
          )}
        </div>
        <div className="mt-1.5 text-xs text-gray-500">
          Trả góp từ <span className="font-bold text-gray-900">{formatPrice(monthlyPrice)}/tháng</span> qua thẻ hoặc công ty tài chính.
        </div>
      </div>

      {(ramOptions.length > 0 || storageOptions.length > 0 || configurationOptions.length > 0) && (
        <div className="mt-4">
          <div className="mb-2 text-sm font-bold text-gray-800">
            Cấu hình đang chọn: <span className="font-semibold text-primary">{variantConfigLabel(activeVariant) || selectedCapacity}</span>
          </div>
          <div className="space-y-3">
            {ramOptions.length > 0 && (
              <div>
                <div className="mb-1.5 text-xs font-bold uppercase text-gray-500">RAM</div>
                <div className="grid grid-cols-3 gap-2">
                  {ramOptions.map((ram) => (
                    <button
                      key={`ram-${ram}`}
                      onClick={() => selectRam(ram)}
                      className={`relative min-h-[46px] rounded-xl border px-3 py-2 text-center text-sm font-bold transition-all duration-200 cursor-pointer ${sameOptionValue(selectedRam, ram) ? 'border-primary bg-red-50 text-primary ring-1 ring-primary' : 'border-gray-200 text-gray-700 hover:border-gray-300'}`}
                    >
                      {ram}
                      {sameOptionValue(selectedRam, ram) && <Check className="absolute right-2 top-1.5 h-3 w-3" />}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {storageOptions.length > 0 && (
              <div>
                <div className="mb-1.5 text-xs font-bold uppercase text-gray-500">ROM</div>
                <div className="grid grid-cols-3 gap-2">
                  {storageOptions.map((storage) => {
                    const variantForStorage = variantsForColor.find((variant: any) => {
                      if (selectedRam && !sameOptionValue(variantSpecValue(variant, 'ram'), selectedRam)) return false;
                      return sameOptionValue(variantSpecValue(variant, 'storage'), storage);
                    });
                    const priceForStorage = variantForStorage ? (variantForStorage.salePrice || variantForStorage.price) : null;
                    return (
                      <button
                        key={`storage-${storage}`}
                        onClick={() => selectStorage(storage)}
                        className={`relative flex min-h-[62px] flex-col items-center justify-center rounded-xl border px-2 py-2 text-center transition-all duration-200 cursor-pointer ${sameOptionValue(selectedStorage, storage) ? 'border-primary bg-red-50 text-primary ring-1 ring-primary' : 'border-gray-200 text-gray-700 hover:border-gray-300'}`}
                      >
                        <span className="text-sm font-bold">{storage}</span>
                        {priceForStorage && (
                          <span className={`mt-0.5 text-[11px] ${sameOptionValue(selectedStorage, storage) ? 'font-bold text-primary' : 'font-medium text-gray-500'}`}>
                            {formatPrice(priceForStorage)}
                          </span>
                        )}
                        {sameOptionValue(selectedStorage, storage) && <Check className="absolute right-2 top-1.5 h-3 w-3" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {configurationOptions.length > 0 && (
              <div>
                <div className="mb-1.5 text-xs font-bold uppercase text-gray-500">Cấu hình</div>
                <div className="grid grid-cols-2 gap-2">
                  {configurationOptions.map((configuration) => (
                    <button
                      key={`configuration-${configuration}`}
                      onClick={() => selectConfiguration(configuration)}
                      className={`relative min-h-[46px] rounded-xl border px-3 py-2 text-center text-sm font-bold transition-all duration-200 cursor-pointer ${sameOptionValue(selectedConfiguration, configuration) ? 'border-primary bg-red-50 text-primary ring-1 ring-primary' : 'border-gray-200 text-gray-700 hover:border-gray-300'}`}
                    >
                      {configuration}
                      {sameOptionValue(selectedConfiguration, configuration) && <Check className="absolute right-2 top-1.5 h-3 w-3" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {colorOptions.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-sm font-bold text-gray-800">Màu sắc: <span className="font-semibold text-primary">{selectedColor}</span></div>
          <div className="grid grid-cols-2 gap-2">
            {colorOptions.map((color) => {
              const colorCode = color.raw?.code || colorFallback[color.label.toLowerCase()] || '#e5e7eb';
              return (
                <button
                  key={color.key}
                  onClick={() => selectColor(color.label)}
                  className={`relative flex items-center gap-3 rounded-xl border px-3.5 py-3.5 text-left transition-all duration-200 cursor-pointer ${selectedColor === color.label ? 'border-primary bg-red-50 ring-1 ring-primary' : 'border-gray-200 hover:border-gray-300'}`}
                >
                  <span className="h-6 w-6 shrink-0 rounded-full border border-gray-200" style={{ backgroundColor: colorCode }} />
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="text-sm font-bold text-gray-800 truncate">{color.label}</span>
                  </div>
                  {selectedColor === color.label && <Check className="ml-auto h-4 w-4 text-primary shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {product.promotions?.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-red-200/60 bg-white">
          <div className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 px-3.5 py-2 text-white">
            <Gift className="h-4 w-4" />
            <h3 className="text-sm font-bold text-white">Khuyến mãi</h3>
          </div>
          <div className="divide-y divide-gray-100">
            {product.promotions.map((promotion: string, index: number) => (
              <div key={`${promotion}-${index}`} className="flex gap-2.5 px-3 py-2.5 text-xs text-gray-700 bg-white">
                <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full bg-green-100 text-[10px] font-bold text-green-700">
                  {index + 1}
                </span>
                <span className="leading-relaxed">{promotion}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <hr className="border-gray-100 my-2" />

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-800">Số lượng</h2>
        <div className="flex overflow-hidden rounded-xl border border-gray-200">
          <button onClick={() => setQuantity(Math.max(1, quantity - 1))} className="flex h-9 w-9 items-center justify-center text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer">
            <Minus className="h-4 w-4" />
          </button>
          <div className="flex h-9 w-10 items-center justify-center border-x border-gray-200 text-sm font-bold bg-gray-50/30">{quantity}</div>
          <button onClick={() => setQuantity(quantity + 1)} className="flex h-9 w-9 items-center justify-center text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer">
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_58px] gap-2">
        <button onClick={handleBuyNow} className="rounded-xl bg-primary px-4 py-3 text-center text-white shadow-md hover:bg-red-700 transition-colors duration-200 cursor-pointer">
          <span className="block text-base font-extrabold">MUA NGAY</span>
          <span className="block text-xs font-medium opacity-90">Giao tận nơi hoặc nhận tại cửa hàng</span>
        </button>
        <button
          onClick={handleAddToCart}
          className={`flex items-center justify-center rounded-xl border-2 transition-all duration-200 cursor-pointer ${addedToCart ? 'border-green-500 bg-green-50 text-green-600' : 'border-primary text-primary hover:bg-red-50'}`}
          title="Thêm vào giỏ hàng"
        >
          {addedToCart ? <Check className="h-6 w-6" /> : <ShoppingCart className="h-6 w-6" />}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button className="flex flex-col items-center justify-center rounded-xl border border-amber-200 bg-amber-50/50 px-2 py-2 text-center transition-all hover:bg-amber-100/60 shadow-sm cursor-pointer">
          <span className="text-xs font-bold text-amber-800">TRẢ GÓP 0%</span>
          <span className="text-[10px] text-amber-600 font-medium mt-0.5">Duyệt hồ sơ nhanh 5 phút</span>
        </button>
        <button className="flex flex-col items-center justify-center rounded-xl border border-blue-200 bg-blue-50/50 px-2 py-2 text-center transition-all hover:bg-blue-100/60 shadow-sm cursor-pointer">
          <span className="text-xs font-bold text-blue-800">TRẢ GÓP QUA THẺ</span>
          <span className="text-[10px] text-blue-600 font-medium mt-0.5">Visa, Mastercard, JCB</span>
        </button>
      </div>
    </div>
  );
}
