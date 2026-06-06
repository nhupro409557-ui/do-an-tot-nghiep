import React from 'react';
import { Image, Plus, Trash2 } from 'lucide-react';
import { FileInput, Input, Select } from '../../../admin-shell/components/AdminDashboardParts';

interface ProductAccessoriesSectionProps {
  productForm: any;
  setProductForm: React.Dispatch<React.SetStateAction<any>>;
  accessoryCategoryFilter: string;
  setAccessoryCategoryFilter: (val: string) => void;
  accessoryBrandFilter: string;
  setAccessoryBrandFilter: (val: string) => void;
  accessorySearch: string;
  setAccessorySearch: (val: string) => void;
  categories: any[];
  brands: any[];
  accessoryProductChoices: any[];
  addAccessoryOffer: (product: any) => void;
  removeAccessoryOffer: (productId: string) => void;
  patchAccessoryOffer: (productId: string, patch: any) => void;
  compactId: (id: string) => string;
  uploadFiles: (files: FileList | null, type: string) => Promise<string[]>;
  attachedServiceTypeFilter: string;
  setAttachedServiceTypeFilter: (val: string) => void;
  attachedServiceGroupFilter: string;
  setAttachedServiceGroupFilter: (val: string) => void;
  attachedServiceSearch: string;
  setAttachedServiceSearch: (val: string) => void;
  serviceGroupOptions: string[];
  productAttachedServiceChoices: any[];
  addAttachedService: (service: any) => void;
  removeAttachedService: (serviceId: string) => void;
  currency: { format: (value: number) => string };
}

export default function ProductAccessoriesSection(props: ProductAccessoriesSectionProps) {
  const {
    productForm,
    setProductForm,
    accessoryCategoryFilter,
    setAccessoryCategoryFilter,
    accessoryBrandFilter,
    setAccessoryBrandFilter,
    accessorySearch,
    setAccessorySearch,
    categories,
    brands,
    accessoryProductChoices,
    addAccessoryOffer,
    removeAccessoryOffer,
    patchAccessoryOffer,
    compactId,
    uploadFiles,
    attachedServiceTypeFilter,
    setAttachedServiceTypeFilter,
    attachedServiceGroupFilter,
    setAttachedServiceGroupFilter,
    attachedServiceSearch,
    setAttachedServiceSearch,
    serviceGroupOptions,
    productAttachedServiceChoices,
    addAttachedService,
    removeAttachedService,
    currency,
  } = props;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
      <div className="mb-3 text-sm font-bold text-slate-700">
        Sản phẩm bán kèm và dịch vụ đi kèm
      </div>
      <div className="grid gap-3">
        {/* Sản phẩm mua kèm */}
        <div className="rounded-md border border-slate-200 bg-white p-3">
          <div className="text-sm font-bold text-slate-800">
            Sản phẩm mua kèm giảm giá
          </div>
          <div className="mt-1 text-xs font-medium text-slate-500">
            Chọn từ danh sách sản phẩm sau khi lọc. Giảm giá chỉ áp dụng trong số
            lượng admin đã cấu hình.
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <Select
              label="Danh mục"
              value={accessoryCategoryFilter}
              onChange={setAccessoryCategoryFilter}
              options={[
                ['', 'Tất cả'],
                ...categories.map((item) => [
                  item.id,
                  item.parentName
                    ? `${item.parentName} / ${item.name}`
                    : item.name,
                ] as [string, string]),
              ]}
            />
            <Select
              label="Thương hiệu"
              value={accessoryBrandFilter}
              onChange={setAccessoryBrandFilter}
              options={[
                ['', 'Tất cả'],
                ...brands.map((item) => [item.id, item.name] as [string, string]),
              ]}
            />
            <Input
              label="Tìm sản phẩm"
              value={accessorySearch}
              onChange={setAccessorySearch}
            />
          </div>
          <div className="mt-2 rounded-md border border-slate-200">
            {accessoryCategoryFilter ||
            accessoryBrandFilter ||
            accessorySearch.trim() ? (
              accessoryProductChoices.length > 0 ? (
                <>
                  <button
                    type="button"
                    onClick={() =>
                      accessoryProductChoices.forEach((item) =>
                        addAccessoryOffer(item)
                      )
                    }
                    className="flex w-full items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-3 py-2 text-left text-xs font-bold text-slate-700"
                  >
                    Chọn tất cả sản phẩm đang lọc
                    <Plus className="h-4 w-4" />
                  </button>
                  {accessoryProductChoices.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => addAccessoryOffer(item)}
                      className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-800">
                          {item.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {item.sku || compactId(item.id)}
                        </div>
                      </div>
                      <span className="text-xs font-bold text-red-600">Chọn</span>
                    </button>
                  ))}
                </>
              ) : (
                <div className="px-3 py-4 text-sm font-medium text-slate-500">
                  Không có sản phẩm phù hợp với bộ lọc.
                </div>
              )
            ) : (
              <div className="px-3 py-4 text-sm font-medium text-slate-500">
                Chọn danh mục, thương hiệu hoặc nhập tên/SKU để hiện danh sách
                sản phẩm.
              </div>
            )}
          </div>
          <div className="mt-3 space-y-3">
            {productForm.accessoryOffers.length === 0 && (
              <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">
                Chưa có sản phẩm mua kèm giảm giá.
              </div>
            )}
            {productForm.accessoryOffers.map((item: any) => (
              <div
                key={item.productId}
                className="rounded-md border border-slate-200 bg-slate-50 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {item.imageUrl ? (
                      <img
                        src={item.imageUrl}
                        alt=""
                        className="h-12 w-12 rounded-md border border-slate-200 object-contain"
                      />
                    ) : (
                      <div className="flex h-12 w-12 items-center justify-center rounded-md border border-slate-200 bg-white">
                        <Image className="h-4 w-4 text-slate-300" />
                      </div>
                    )}
                    <div>
                      <div className="text-sm font-bold text-slate-800">
                        {item.productName || 'Sản phẩm mua kèm'}
                      </div>
                      <div className="text-xs text-slate-500">
                        {item.productSku || compactId(item.productId)}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAccessoryOffer(item.productId)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <Select
                    label="Kiểu giảm"
                    value={item.discountType}
                    onChange={(value) =>
                      patchAccessoryOffer(item.productId, {
                        discountType: value as 'FIXED' | 'PERCENT',
                      })
                    }
                    options={[
                      ['PERCENT', 'Theo %'],
                      ['FIXED', 'Theo số tiền'],
                    ]}
                  />
                  <Input
                    label={
                      item.discountType === 'PERCENT'
                        ? 'Giảm giá (%)'
                        : 'Giảm giá (VND)'
                    }
                    type="number"
                    value={item.discountValue}
                    onChange={(value) =>
                      patchAccessoryOffer(item.productId, {
                        discountValue: Number(value),
                      })
                    }
                  />
                  <Input
                    label="Số lượng được giảm"
                    type="number"
                    value={item.maxQuantity}
                    onChange={(value) =>
                      patchAccessoryOffer(item.productId, {
                        maxQuantity: Math.max(1, Number(value) || 1),
                      })
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dịch vụ đi kèm */}
        <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
          <div className="text-sm font-bold text-slate-800 font-bold">
            Dịch vụ đi kèm
          </div>
          <div className="mt-1 text-xs font-medium text-slate-500">
            Chọn từ danh sách dịch vụ admin đã tạo. Với cùng một nhóm bảo hành,
            hệ thống chỉ cho chọn một thời hạn.
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <Select
              label="Loại dịch vụ"
              value={attachedServiceTypeFilter}
              onChange={setAttachedServiceTypeFilter}
              options={[
                ['', 'Tất cả'],
                ['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'],
                ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ'],
              ]}
            />
            <Select
              label="Nhóm dịch vụ"
              value={attachedServiceGroupFilter}
              onChange={setAttachedServiceGroupFilter}
              options={[
                ['', 'Tất cả'],
                ...serviceGroupOptions.map((item) => [item, item] as [string, string]),
              ]}
            />
            <Input
              label="Tìm dịch vụ"
              value={attachedServiceSearch}
              onChange={setAttachedServiceSearch}
            />
          </div>
          <div className="mt-3 rounded-md border border-slate-200">
            {productAttachedServiceChoices.length === 0 ? (
              <div className="px-3 py-4 text-sm font-medium text-slate-500">
                Không có dịch vụ phù hợp hoặc tất cả dịch vụ trong bộ lọc đã được
                chọn.
              </div>
            ) : (
              productAttachedServiceChoices.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  onClick={() => addAttachedService(service)}
                  className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-800">
                      {service.name}{' '}
                      <span className="text-xs text-slate-400">
                        ({service.code})
                      </span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {service.serviceType === 'PRODUCT_SERVICE'
                        ? 'Dịch vụ sản phẩm'
                        : 'Dịch vụ hỗ trợ'}
                      {service.attributeGroup
                        ? ` · Nhóm ${service.attributeGroup}`
                        : ''}
                      {service.durationMonths
                        ? ` · ${service.durationMonths} tháng`
                        : ''}
                      {service.priceMode === 'PERCENT'
                        ? ` · ${service.percentValue || 0}%`
                        : service.priceMode === 'TIERED_AMOUNT'
                        ? ' · Theo biểu phí'
                        : ` · ${currency.format(
                            Number(
                              service.fixedPrice || service.baseAmount || 0
                            )
                          )}`}
                    </div>
                  </div>
                  <Plus className="h-4 w-4 shrink-0 text-red-600" />
                </button>
              ))
            )}
          </div>
          <div className="mt-3 space-y-2">
            {productForm.attachedServices.length === 0 && (
              <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">
                Chưa chọn dịch vụ đi kèm.
              </div>
            )}
            {productForm.attachedServices.map((item: any) => (
              <div
                key={item.serviceId}
                className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 md:grid-cols-[1fr_40px]"
              >
                <div>
                  <div className="text-sm font-bold text-slate-800">
                    {item.name || item.code || 'Dịch vụ'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {item.serviceType === 'PRODUCT_SERVICE'
                      ? 'Dịch vụ sản phẩm'
                      : 'Dịch vụ hỗ trợ'}
                    {item.attributeGroup ? ` · Nhóm ${item.attributeGroup}` : ''}
                    {item.durationMonths ? ` · ${item.durationMonths} tháng` : ''}
                    {item.priceMode === 'PERCENT'
                      ? ` · ${item.percentValue || 0}%`
                      : item.priceMode === 'TIERED_AMOUNT'
                      ? ' · Theo biểu phí chính sách'
                      : ` · ${currency.format(Number(item.fixedPrice || 0))}`}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeAttachedService(item.serviceId)}
                  className="text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
