import React from 'react';
import { ChevronDown, Image, Search } from 'lucide-react';
import {
  Checkbox,
  FileInput,
  Input,
  MediaPreview,
  Select,
  SubmitButtons,
  VideoPreview,
} from '../../../admin-shell/components/AdminDashboardParts';
import ProductAccessoriesSection from './ProductAccessoriesSection';
import ProductVariantsSection from './ProductVariantsSection';

function SearchableBrandSelect({
  brands,
  value,
  onChange,
}: {
  brands: any[];
  value: string;
  onChange: (brandId: string) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const selectedBrand = brands.find((item) => item.id === value);
  const normalizedSearch = search.trim().toLowerCase();
  const filteredBrands = React.useMemo(() => {
    if (!normalizedSearch) return brands;
    return brands.filter((item) => {
      const name = String(item.name || '').toLowerCase();
      const code = String(item.code || '').toLowerCase();
      return name.includes(normalizedSearch) || code.includes(normalizedSearch);
    });
  }, [brands, normalizedSearch]);

  React.useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event: MouseEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleSelect = (brandId: string) => {
    onChange(brandId);
    setSearch('');
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative block w-full sm:w-auto">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">Thương hiệu</span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="flex h-10 w-full min-w-44 items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 text-left text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      >
        <span className={selectedBrand ? 'truncate' : 'truncate text-slate-400'}>
          {selectedBrand?.name || 'Chọn thương hiệu'}
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-2 w-full min-w-72 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
          <div className="border-b border-slate-100 p-2">
            <div className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2">
              <Search className="h-4 w-4 shrink-0 text-slate-400" />
              <input
                autoFocus
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm thương hiệu"
                className="h-full min-w-0 flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
            </div>
          </div>
          <div role="listbox" aria-label="Thương hiệu" className="max-h-72 overflow-y-auto p-1">
            {filteredBrands.length === 0 ? (
              <div className="px-3 py-2 text-sm text-slate-500">Không có thương hiệu phù hợp</div>
            ) : (
              filteredBrands.map((brand) => {
                const selected = brand.id === value;
                return (
                  <button
                    key={brand.id}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => handleSelect(brand.id)}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-semibold transition ${
                      selected ? 'bg-red-50 text-red-700' : 'text-slate-700 hover:bg-slate-50 hover:text-slate-950'
                    }`}
                  >
                    <span className="truncate">{brand.name}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface ProductFormSectionProps {
  productForm: any;
  setProductForm: React.Dispatch<React.SetStateAction<any>>;
  editingProductId: string | null;
  handleProductSubmit: (e: React.FormEvent) => void;
  resetProductForm: () => void;
  rootCategories: any[];
  subCategories: any[];
  categories: any[];
  brands: any[];
  categoryWarrantyPolicy: (cat: any, parent?: any) => any;
  uploadFiles: (files: FileList | null, type: string) => Promise<string[]>;
  productSpecFields: any[];
  groupedProductSpecFields: any[];
  currency: { format: (value: number) => string };
  compactId: (id: string) => string;

  // Accessories Props
  accessoryCategoryFilter: string;
  setAccessoryCategoryFilter: (val: string) => void;
  accessoryBrandFilter: string;
  setAccessoryBrandFilter: (val: string) => void;
  accessorySearch: string;
  setAccessorySearch: (val: string) => void;
  accessoryProductChoices: any[];
  addAccessoryOffer: (product: any) => void;
  removeAccessoryOffer: (productId: string) => void;
  patchAccessoryOffer: (productId: string, patch: any) => void;
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

  // Variants Props
  variantFields: any[];
  toggleVariantSpecField: (key: string, checked: boolean) => void;
  addVariant: () => void;
  activeVariantFields: any[];
  patchVariant: (index: number, patch: any) => void;
  confirmDelete: (name: string, onDelete: () => Promise<any>) => Promise<any>;
}

export default function ProductFormSection(props: ProductFormSectionProps) {
  const {
    productForm,
    setProductForm,
    editingProductId,
    handleProductSubmit,
    resetProductForm,
    rootCategories,
    subCategories,
    categories,
    brands,
    categoryWarrantyPolicy,
    uploadFiles,
    productSpecFields,
    groupedProductSpecFields,
    currency,
    compactId,

    // Accessories
    accessoryCategoryFilter,
    setAccessoryCategoryFilter,
    accessoryBrandFilter,
    setAccessoryBrandFilter,
    accessorySearch,
    setAccessorySearch,
    accessoryProductChoices,
    addAccessoryOffer,
    removeAccessoryOffer,
    patchAccessoryOffer,
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

    // Variants
    variantFields,
    toggleVariantSpecField,
    addVariant,
    activeVariantFields,
    patchVariant,
    confirmDelete,
  } = props;
  const filteredSubCategories = productForm.categoryId
    ? subCategories.filter((item) => item.parentId === productForm.categoryId)
    : subCategories;
  const productPublicationStatusOptions: [string, string][] = [
    ['ACTIVE', 'Đang bán'],
    ['INACTIVE', 'Tạm ẩn'],
    ['DISCONTINUED', 'Ngừng kinh doanh'],
  ];

  return (
    <form
      onSubmit={handleProductSubmit}
      className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4"
    >
      <Input
        label="Tên sản phẩm"
        value={productForm.name}
        required
        onChange={(value) => setProductForm({ ...productForm, name: value })}
      />
      <Input
        label="Giá gốc chung"
        type="number"
        value={productForm.price}
        onChange={(value) =>
          setProductForm({ ...productForm, price: Number(value) })
        }
      />
      <Input
        label="Giá bán chung"
        type="number"
        value={productForm.discountPrice}
        onChange={(value) =>
          setProductForm({ ...productForm, discountPrice: Number(value) })
        }
      />
      <Select
        label="Danh mục cha"
        value={productForm.categoryId}
        onChange={(value) => {
          const category = rootCategories.find((item) => item.id === value);
          const selectedChild = subCategories.find((item) => item.id === productForm.subcategoryId);
          const keepSubcategory = Boolean(value && selectedChild?.parentId === value);
          const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy
            ? categoryWarrantyPolicy(keepSubcategory ? selectedChild : category, category)
            : productForm.warrantyPolicy;
          setProductForm({
            ...productForm,
            categoryId: value,
            subcategoryId: keepSubcategory ? productForm.subcategoryId : '',
            category: (category?.code || category?.slug || productForm.category).toUpperCase(),
            warrantyPolicy: nextWarranty,
            specifications: {},
            variantSpecKeys: [],
            variants: productForm.variants.map((variant: any) => ({
              ...variant,
              specs: {},
            })),
          });
        }}
        options={[
          ['', 'Chưa chọn'],
          ...rootCategories.map((item) => [item.id, item.name] as [string, string]),
        ]}
      />
      <Select
        label="Danh mục con"
        value={productForm.subcategoryId}
        onChange={(value) => {
          const child = subCategories.find((item) => item.id === value);
          const parent = rootCategories.find(
            (item) => item.id === (child?.parentId || productForm.categoryId)
          );
          const parentChanged = Boolean(child?.parentId && child.parentId !== productForm.categoryId);
          const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy
            ? categoryWarrantyPolicy(child || parent, parent)
            : productForm.warrantyPolicy;
          setProductForm({
            ...productForm,
            categoryId: parent?.id || productForm.categoryId,
            category: (parent?.code || parent?.slug || productForm.category).toUpperCase(),
            subcategoryId: value,
            warrantyPolicy: nextWarranty,
            specifications: parentChanged ? {} : productForm.specifications,
            variantSpecKeys: parentChanged ? [] : productForm.variantSpecKeys,
            variants: parentChanged
              ? productForm.variants.map((variant: any) => ({
                  ...variant,
                  specs: {},
                }))
              : productForm.variants,
          });
        }}
        options={[
          ['', 'Chưa chọn'],
          ...filteredSubCategories.map((item) => [
            item.id,
            `${item.parentName || 'Khác'} / ${item.name}`,
          ] as [string, string]),
        ]}
      />
      <SearchableBrandSelect
        brands={brands}
        value={productForm.brandId}
        onChange={(value) => {
          const brand = brands.find((item) => item.id === value);
          setProductForm({
            ...productForm,
            brandId: value,
            brand: brand?.name || '',
          });
        }}
      />
      <Select
        label="Trạng thái sau duyệt"
        value={productForm.status}
        onChange={(value) => setProductForm({ ...productForm, status: value })}
        options={productPublicationStatusOptions}
      />
      <FileInput
        label="Ảnh đại diện chung"
        accept="image/*"
        onFiles={async (files) =>
          setProductForm({
            ...productForm,
            imageUrl:
              (await uploadFiles(files, 'products'))[0] || productForm.imageUrl,
          })
        }
      />
      <FileInput
        label="Bộ ảnh sản phẩm chung"
        accept="image/*"
        multiple
        onFiles={async (files) => {
          const urls = await uploadFiles(files, 'products');
          setProductForm({
            ...productForm,
            images: [...(productForm.images || []), ...urls].slice(0, 20),
          });
        }}
      />
      <FileInput
        label="Video sản phẩm dùng chung"
        accept="video/*"
        onFiles={async (files) =>
          setProductForm({
            ...productForm,
            videoUrl:
              (await uploadFiles(files, 'products'))[0] || productForm.videoUrl,
          })
        }
      />
      <MediaPreview
        title="Ảnh đại diện chung"
        items={productForm.imageUrl ? [productForm.imageUrl] : []}
        onRemove={() => setProductForm({ ...productForm, imageUrl: '' })}
      />
      <MediaPreview
        title="Bộ ảnh sản phẩm chung"
        items={productForm.images || []}
        onRemove={(url) =>
          setProductForm({
            ...productForm,
            images: (productForm.images || []).filter(
              (item: string) => item !== url
            ),
          })
        }
      />
      {productForm.videoUrl && (
        <VideoPreview
          title="Video sản phẩm dùng chung"
          url={productForm.videoUrl}
          onRemove={() => setProductForm({ ...productForm, videoUrl: '' })}
        />
      )}

      {/* Bảo hành */}
      <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
        <div className="mb-3 text-sm font-bold text-slate-700">
          Bảo hành sản phẩm
        </div>
        <div className="grid gap-3 md:grid-cols-5">
          <Checkbox
            label="Theo danh mục"
            checked={productForm.warrantyPolicy.inheritWarrantyPolicy}
            onChange={(checked) => {
              const parent = rootCategories.find(
                (item) => item.id === productForm.categoryId
              );
              const child = subCategories.find(
                (item) => item.id === productForm.subcategoryId
              );
              setProductForm({
                ...productForm,
                warrantyPolicy: checked
                  ? categoryWarrantyPolicy(child || parent, parent)
                  : { ...productForm.warrantyPolicy, inheritWarrantyPolicy: false },
              });
            }}
          />
          <Checkbox
            label="Có bảo hành"
            checked={productForm.warrantyPolicy.hasWarranty}
            disabled={productForm.warrantyPolicy.inheritWarrantyPolicy}
            onChange={(checked) =>
              setProductForm({
                ...productForm,
                warrantyPolicy: {
                  ...productForm.warrantyPolicy,
                  hasWarranty: checked,
                  inheritWarrantyPolicy: false,
                },
              })
            }
          />
          <Input
            label="Tháng bảo hành"
            type="number"
            disabled={productForm.warrantyPolicy.inheritWarrantyPolicy}
            value={productForm.warrantyPolicy.warrantyMonths}
            onChange={(value) =>
              setProductForm({
                ...productForm,
                warrantyPolicy: {
                  ...productForm.warrantyPolicy,
                  warrantyMonths: Math.max(0, Number(value)),
                  inheritWarrantyPolicy: false,
                },
              })
            }
          />
          <Checkbox
            label="Có 1 đổi 1"
            checked={productForm.warrantyPolicy.allowOneForOne}
            disabled={productForm.warrantyPolicy.inheritWarrantyPolicy}
            onChange={(checked) =>
              setProductForm({
                ...productForm,
                warrantyPolicy: {
                  ...productForm.warrantyPolicy,
                  allowOneForOne: checked,
                  inheritWarrantyPolicy: false,
                },
              })
            }
          />
          <Input
            label="Ngày 1 đổi 1"
            type="number"
            disabled={productForm.warrantyPolicy.inheritWarrantyPolicy}
            value={productForm.warrantyPolicy.oneForOneDays}
            onChange={(value) =>
              setProductForm({
                ...productForm,
                warrantyPolicy: {
                  ...productForm.warrantyPolicy,
                  oneForOneDays: Math.max(0, Number(value)),
                  inheritWarrantyPolicy: false,
                },
              })
            }
          />
        </div>
      </div>

      {/* Thông số kỹ thuật */}
      {productSpecFields.length > 0 && (
        <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
          <div className="mb-3">
            <div className="text-sm font-bold text-slate-700">
              Thông số kỹ thuật theo danh mục
            </div>
            <p className="mt-1 text-xs font-medium text-slate-500">
              Các thông số này lấy từ danh mục cha và áp dụng cho sản phẩm.
            </p>
          </div>
          <div className="space-y-4">
            {groupedProductSpecFields.map((group) => (
              <div key={group.title}>
                <div className="mb-2 text-xs font-bold uppercase text-slate-500">
                  {group.title}
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {group.fields.map((field: any) => (
                    <Input
                      key={field.key}
                      label={field.label || field.key}
                      value={productForm.specifications[field.key] || ''}
                      required={field.required}
                      onChange={(value) =>
                        setProductForm({
                          ...productForm,
                          specifications: {
                            ...productForm.specifications,
                            [field.key]: value,
                          },
                        })
                      }
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mô tả ngắn */}
      <textarea
        className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-4"
        placeholder="Mô tả ngắn"
        value={productForm.description}
        onChange={(event) =>
          setProductForm({ ...productForm, description: event.target.value })
        }
      />

      {/* Section phụ kiện & dịch vụ */}
      <ProductAccessoriesSection
        productForm={productForm}
        setProductForm={setProductForm}
        accessoryCategoryFilter={accessoryCategoryFilter}
        setAccessoryCategoryFilter={setAccessoryCategoryFilter}
        accessoryBrandFilter={accessoryBrandFilter}
        setAccessoryBrandFilter={setAccessoryBrandFilter}
        accessorySearch={accessorySearch}
        setAccessorySearch={setAccessorySearch}
        categories={categories}
        brands={brands}
        accessoryProductChoices={accessoryProductChoices}
        addAccessoryOffer={addAccessoryOffer}
        removeAccessoryOffer={removeAccessoryOffer}
        patchAccessoryOffer={patchAccessoryOffer}
        compactId={compactId}
        uploadFiles={uploadFiles}
        attachedServiceTypeFilter={attachedServiceTypeFilter}
        setAttachedServiceTypeFilter={setAttachedServiceTypeFilter}
        attachedServiceGroupFilter={attachedServiceGroupFilter}
        setAttachedServiceGroupFilter={setAttachedServiceGroupFilter}
        attachedServiceSearch={attachedServiceSearch}
        setAttachedServiceSearch={setAttachedServiceSearch}
        serviceGroupOptions={serviceGroupOptions}
        productAttachedServiceChoices={productAttachedServiceChoices}
        addAttachedService={addAttachedService}
        removeAttachedService={removeAttachedService}
        currency={currency}
      />

      {/* Section biến thể */}
      <ProductVariantsSection
        productForm={productForm}
        setProductForm={setProductForm}
        variantFields={variantFields}
        toggleVariantSpecField={toggleVariantSpecField}
        addVariant={addVariant}
        activeVariantFields={activeVariantFields}
        patchVariant={patchVariant}
        uploadFiles={uploadFiles}
        editingProductId={editingProductId}
        confirmDelete={confirmDelete}
        currency={currency}
        compactId={compactId}
      />

      {/* Nút submit */}
      <SubmitButtons
        editing={Boolean(editingProductId)}
        onCancel={resetProductForm}
      />
    </form>
  );
}
