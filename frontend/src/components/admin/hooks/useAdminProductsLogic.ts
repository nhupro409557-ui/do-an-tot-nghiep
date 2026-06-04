import { useState, useMemo, type FormEvent } from 'react';
import { productApi } from '../../../services/productApi';
import { useAdminProductVariants } from './useAdminProductVariants';
import { useAdminProductOffers } from './useAdminProductOffers';
import {
  type AccessoryOfferForm,
  type AttachedServiceForm,
  type SpecField,
  type VariantForm,
  buildVariantSku,
  emptyProduct,
  emptyVariant,
  productExtraKeys,
  normalizeWarrantyPolicy,
  defaultWarrantyPolicy,
  matchesSearch,
  sameId,
  groupSpecFields,
} from '../AdminDashboardConfig';

type UseAdminProductsLogicParams = {
  tab: string;
  query: string;
  products: any[];
  categories: any[];
  brands: any[];
  attachedServices: any[];
  loadData: (targetTab?: any, options?: any) => Promise<void>;
  productCategoryFilter: string;
  setProductCategoryFilter: (value: string) => void;
  productBrandFilter: string;
  setProductBrandFilter: (value: string) => void;
  setProductStatusFilter: (value: string) => void;
  setProductPage: (value: number) => void;
};

export function useAdminProductsLogic({
  tab,
  query,
  products,
  categories,
  brands,
  attachedServices,
  loadData,
  productCategoryFilter,
  setProductCategoryFilter,
  productBrandFilter,
  setProductBrandFilter,
  setProductStatusFilter,
  setProductPage,
}: UseAdminProductsLogicParams) {
  const [productForm, setProductForm] = useState(emptyProduct);
  const [accessorySearch, setAccessorySearch] = useState('');
  const [accessoryCategoryFilter, setAccessoryCategoryFilter] = useState('');
  const [accessoryBrandFilter, setAccessoryBrandFilter] = useState('');
  const [attachedServiceTypeFilter, setAttachedServiceTypeFilter] = useState('');
  const [attachedServiceGroupFilter, setAttachedServiceGroupFilter] = useState('');
  const [attachedServiceSearch, setAttachedServiceSearch] = useState('');
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [previewProduct, setPreviewProduct] = useState<any | null>(null);
  const [editingProductId, setEditingProductId] = useState<string | null>(null);
  const [productFormOpen, setProductFormOpen] = useState(false);
  const [productCloseSignal, setProductCloseSignal] = useState(0);

  const selectedCategory = useMemo(() => categories.find((item) => item.id === productForm.categoryId), [categories, productForm.categoryId]);
  const selectedSubCategory = useMemo(() => categories.find((item) => item.id === productForm.subcategoryId), [categories, productForm.subcategoryId]);
  
  const specFields: SpecField[] = useMemo(() => {
    const childOwnFields = selectedSubCategory?.ownSpecFields || [];
    const merged = [...(selectedCategory?.specFields || []), ...childOwnFields];
    const seen = new Set<string>();
    return merged.filter((field) => {
      if (!field.key || seen.has(field.key)) return false;
      seen.add(field.key);
      return true;
    });
  }, [selectedCategory, selectedSubCategory]);

  const variantFields = specFields.filter((item) => item.variant);
  const activeVariantFields = variantFields.filter((item) => productForm.variantSpecKeys.includes(item.key));
  const productSpecFields = specFields.filter((item) => !item.variant || !productForm.variantSpecKeys.includes(item.key));
  const groupedProductSpecFields = useMemo(() => groupSpecFields(productSpecFields), [productSpecFields]);
  const groupedActiveVariantFields = useMemo(() => groupSpecFields(activeVariantFields), [activeVariantFields]);

  const productBrandOptions = useMemo(() => {
    return [['', 'Tất cả thương hiệu'] as [string, string], ...brands.filter((b: any) => {
      if (!productCategoryFilter) return true;
      if (b.categoryIds && (b.categoryIds.includes(productCategoryFilter) || categories.some((c: any) => c.parentId === productCategoryFilter && b.categoryIds.includes(c.id)))) return true;
      return products.some((p: any) => (p.brandId === b.id || p.brand === b.name) && (p.categoryId === productCategoryFilter || p.subcategoryId === productCategoryFilter || categories.some((c: any) => c.parentId === productCategoryFilter && (p.categoryId === c.id || p.subcategoryId === c.id))));
    }).map((b: any) => [b.id, b.name])];
  }, [brands, productCategoryFilter, categories, products]);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const ms = matchesSearch(product, query, ['name', 'brand', 'categoryName', 'category', 'sku', 'status']);
      const mc = !productCategoryFilter || String(product.categoryId) === productCategoryFilter || String(product.subcategoryId) === productCategoryFilter;
      const mb = !productBrandFilter || String(product.brandId) === productBrandFilter || (product.brand && brands.find(b => String(b.id) === productBrandFilter)?.name === product.brand);
      return ms && mc && mb;
    });
  }, [products, query, productCategoryFilter, productBrandFilter, brands]);

  const {
    colorOptionName,
    normalizeOptionKey,
    activeVariantOptionName,
    variantSpecValue,
    resolveVariantSpecKey,
    buildVariantAttributes,
    deriveOptionsFromVariants,
    addVariant,
    patchVariant,
    toggleVariantSpecField,
  } = useAdminProductVariants({
    productForm,
    setProductForm,
    variantFields,
    activeVariantFields,
  });

  const {
    accessoryProductChoices,
    productAttachedServiceChoices,
    serviceGroupOptions,
    addAccessoryOffer,
    patchAccessoryOffer,
    removeAccessoryOffer,
    addAttachedService,
    removeAttachedService,
  } = useAdminProductOffers({
    productForm,
    setProductForm,
    categories,
    products,
    brands,
    attachedServices,
    editingProductId,
    accessorySearch,
    setAccessorySearch,
    accessoryCategoryFilter,
    accessoryBrandFilter,
    attachedServiceTypeFilter,
    attachedServiceGroupFilter,
    attachedServiceSearch,
  });

  function resetProductForm() {
    setProductFormOpen(false);
    setEditingProductId(null);
    setProductForm({ ...emptyProduct, images: [], specifications: {}, variants: [] });
    setAccessorySearch('');
    setAccessoryCategoryFilter('');
    setAccessoryBrandFilter('');
  }

  function productPayload() {
    const hasVariants = productForm.variants.length > 0;
    const specifications = {
      ...productForm.specifications,
      _variantSpecKeys: hasVariants ? productForm.variantSpecKeys : [],
      _accessoryOffers: productForm.accessoryOffers.map((item) => ({
        productId: item.productId,
        discountType: item.discountType,
        discountValue: item.discountValue,
        maxQuantity: item.maxQuantity,
      })),
      _attachedServices: productForm.attachedServices.map((item) => ({
        serviceId: item.serviceId,
      })),
      _warrantyPolicy: productForm.warrantyPolicy,
    };
    const sortedVariants = [...productForm.variants].sort((left, right) => {
      const leftColor = `${left.colorName || ''}`.toLowerCase();
      const rightColor = `${right.colorName || ''}`.toLowerCase();
      if (leftColor !== rightColor) return leftColor.localeCompare(rightColor);
      return JSON.stringify(left.specs || {}).localeCompare(JSON.stringify(right.specs || {}));
    });
    const derivedOptions = hasVariants ? deriveOptionsFromVariants(sortedVariants) : [];
    return {
      name: productForm.name,
      price: productForm.price,
      brand: productForm.brand,
      category: productForm.category,
      stock: Number(productForm.stock || 0),
      imageUrl: productForm.imageUrl || null,
      images: productForm.images || [],
      description: productForm.description || null,
      isFeatured: productForm.isFeatured,
      isFlashSale: productForm.isFlashSale,
      status: productForm.status,
      specifications,
      discountPrice: productForm.discountPrice || null,
      categoryId: productForm.categoryId || null,
      subcategoryId: productForm.subcategoryId || null,
      brandId: productForm.brandId || null,
      videoUrl: productForm.videoUrl || null,
      variants: sortedVariants.map((item) => ({
        ...item,
        sku: item.sku || buildVariantSku(productForm.name, item.colorName, sortedVariants.indexOf(item)),
        storage: String(variantSpecValue(item, 'storage', 'Bộ nhớ trong') || item.storage || ''),
        ram: String(variantSpecValue(item, 'ram', 'RAM') || item.ram || ''),
        configuration: String(variantSpecValue(item, 'configuration', 'Cấu hình') || item.configuration || ''),
        salePrice: item.salePrice || null,
        compareAtPrice: item.compareAtPrice || null,
        isDefault: item.isDefault || false,
        status: item.status || 'active',
        attributes: buildVariantAttributes(item),
        specs: Object.fromEntries(Object.entries(item.specs || {}).filter(([key]) => productForm.variantSpecKeys.includes(key))),
        images: item.images || [],
      })),
      options: derivedOptions,
      updatedAt: productForm.updatedAt || null,
      version: productForm.version || null,
    };
  }

  function validateProductForm(): string | null {
    if (!productForm.name.trim()) {
      return 'Tên sản phẩm không được trống.';
    }

    const activeOptions = deriveOptionsFromVariants(productForm.variants || [])
      .map((option: any) => ({
        name: String(option.name || '').trim(),
        values: (option.values || []).map((value: any) => String(value || '').trim()).filter(Boolean),
      }))
      .filter((option: any) => option.name && option.values.length > 0);

    const variants = productForm.variants || [];

    const normalizedSkus = variants
      .map((variant, index) => (variant.sku || buildVariantSku(productForm.name, variant.colorName, index)).trim().toLowerCase())
      .filter(Boolean);
    if (normalizedSkus.length !== new Set(normalizedSkus).size) {
      return 'SKU biến thể không được trùng trong cùng sản phẩm.';
    }

    const defaultCount = variants.filter((variant) => variant.isDefault).length;
    if (variants.length > 0 && defaultCount !== 1) {
      return 'Mỗi sản phẩm phải có đúng một biến thể mặc định.';
    }

    const optionMap = new Map(activeOptions.map((option: any) => [option.name, new Set(option.values)]));
    for (const variant of variants) {
      if (Number(variant.price || 0) < 0 || Number(variant.salePrice || 0) < 0 || Number(variant.stockQuantity || 0) < 0) {
        return 'Giá và tồn kho của biến thể không được âm.';
      }
      const attributes = buildVariantAttributes(variant);
      for (const option of activeOptions) {
        if (!Object.prototype.hasOwnProperty.call(attributes, option.name)) {
          return `Biến thể thiếu thuộc tính ${option.name}.`;
        }
        if (!optionMap.get(option.name)?.has(String(attributes[option.name] || '').trim())) {
          return `Giá trị ${attributes[option.name]} không hợp lệ cho thuộc tính ${option.name}.`;
        }
      }
      for (const attrName of Object.keys(attributes)) {
        if (!optionMap.has(attrName)) {
          return `Thuộc tính ${attrName} không nằm trong cấu hình sản phẩm.`;
        }
      }
    }

    return null;
  }

  function productSubmitErrorMessage(error: unknown): string {
    const fallback = 'Không thể lưu sản phẩm. Vui lòng kiểm tra dữ liệu và thử lại.';
    if (!(error instanceof Error) || !error.message) return fallback;
    try {
      const parsed = JSON.parse(error.message);
      if (Array.isArray(parsed)) {
        return parsed
          .map((item) => item?.msg || item?.message || item?.detail || JSON.stringify(item))
          .join('\n');
      }
      if (parsed && typeof parsed === 'object') {
        return parsed.message || parsed.detail || JSON.stringify(parsed);
      }
    } catch {
      // API errors are usually plain Vietnamese messages; keep them as-is.
    }
    return error.message;
  }

  async function handleProductSubmit(event: FormEvent) {
    event.preventDefault();
    const validationError = validateProductForm();
    if (validationError) {
      window.alert(validationError);
      return;
    }
    const currentEditingProductId = editingProductId;
    let result: any;
    try {
      if (currentEditingProductId) {
        result = await productApi.adminUpdateProduct(currentEditingProductId, productPayload());
      } else {
        result = await productApi.adminCreateProduct(productPayload());
      }
    } catch (error) {
      const action = currentEditingProductId ? 'lưu thay đổi' : 'thêm sản phẩm';
      window.alert(`Không thể ${action}:\n${productSubmitErrorMessage(error)}`);
      return;
    }
    setProductFormOpen(false);
    setProductCloseSignal((value) => value + 1);
    window.setTimeout(resetProductForm, 250);
    if (result?.status === 'REVISION_DRAFT') {
      setProductPage(1);
      setProductStatusFilter('REVISION_DRAFT');
      await loadData(tab, { force: true });
      window.setTimeout(() => {
        window.alert('Đã lưu thành bản chỉnh sửa. Bản này cần được gửi duyệt và duyệt trước khi áp dụng vào sản phẩm đang bán.');
      }, 0);
      return;
    }
    await loadData(tab, { force: true });
    window.setTimeout(() => {
      window.alert(currentEditingProductId ? 'Đã lưu thay đổi sản phẩm thành công.' : 'Đã thêm sản phẩm thành công.');
    }, 0);
  }

  function editProduct(product: any) {
    setProductFormOpen(true);
    setEditingProductId(product.id);
    const rawVariantSpecKeys = Array.isArray(product.salesConfig?.variantSpecKeys)
      ? product.salesConfig.variantSpecKeys
      : Array.isArray(product.specifications?._variantSpecKeys)
      ? product.specifications._variantSpecKeys
      : Array.from(new Set((product.variants || []).flatMap((item: any) => Object.keys(item.specs || {}))));
    const savedVariantSpecKeys = Array.from(new Set((rawVariantSpecKeys as string[]).map((key) => resolveVariantSpecKey(key))));
    const cleanSpecifications = { ...(product.specifications || {}) };
    const accessoryOffers = product.salesConfig?.accessoryOffers || product.specifications?._accessoryOffers || [];
    const attachedServices = product.salesConfig?.attachedServices || product.specifications?._attachedServices || [];
    const warrantyPolicy = product.salesConfig?.warrantyPolicy || product.specifications?._warrantyPolicy || defaultWarrantyPolicy;
    productExtraKeys.forEach((key) => delete cleanSpecifications[key]);
    setProductForm({
      ...emptyProduct,
      name: product.name || '',
      price: Number(product.price || 0),
      discountPrice: Number(product.discountPrice || 0),
      stock: Number(product.stockQuantity ?? product.stock ?? 0),
      brand: product.brand || '',
      category: product.category || 'ACCESSORY',
      categoryId: product.categoryId || '',
      subcategoryId: product.subcategoryId || '',
      brandId: product.brandId || '',
      imageUrl: product.imageUrl || '',
      images: product.images || [],
      videoUrl: product.videoUrl || '',
      description: product.description || '',
      specifications: cleanSpecifications,
      seoTitle: product.seoMetadata?.title || product.specifications?._seoTitle || '',
      seoDescription: product.seoMetadata?.description || product.specifications?._seoDescription || '',
      seoSlug: product.seoMetadata?.slug || product.specifications?._seoSlug || product.slug || '',
      accessoryOffers: accessoryOffers.map((item: any) => ({
        productId: item.productId || '',
        productName: item.productName || '',
        productSku: item.productSku || '',
        imageUrl: item.imageUrl || '',
        images: item.images || [],
        discountType: item.discountType === 'FIXED' ? 'FIXED' : 'PERCENT',
        discountValue: Number(item.discountValue || 0),
        maxQuantity: Number(item.maxQuantity || 1),
      })),
      attachedServices: attachedServices.map((item: any) => ({
        serviceId: item.serviceId || '',
        name: item.name || '',
        code: item.code || '',
        serviceType: item.serviceType || 'SUPPORT_SERVICE',
        attributeGroup: item.attributeGroup || '',
        durationMonths: Number(item.durationMonths || 0),
        priceMode: item.priceMode || 'FIXED',
        fixedPrice: Number(item.fixedPrice || 0),
        percentValue: Number(item.percentValue || 0),
      })),
      warrantyPolicy: normalizeWarrantyPolicy(warrantyPolicy),
      updatedAt: product.updatedAt || '',
      version: Number(product.version || 1),
      variantSpecKeys: savedVariantSpecKeys,
      variants: (product.variants || []).map((item: any) => {
        const attributes = item.attributes || {};
        const rawSpecs = item.specs || {};
        const normalizedSpecs = { ...rawSpecs };
        savedVariantSpecKeys.forEach((key: string) => {
          const optionName = variantFields.find((field) => field.key === key)?.label || key;
          const value = variantSpecValue(item, key, optionName);
          if (value) normalizedSpecs[key] = value;
        });
        return {
          ...emptyVariant,
          id: item.id,
          sku: item.sku || '',
          colorName: item.colorName || String(variantSpecValue(item, 'color', colorOptionName) || ''),
          colorCode: item.colorCode || '#111827',
          storage: item.storage || String(variantSpecValue(item, 'storage', 'Bộ nhớ trong') || ''),
          ram: item.ram || String(variantSpecValue(item, 'ram', 'RAM') || ''),
          configuration: item.configuration || String(variantSpecValue(item, 'configuration', 'Cấu hình') || ''),
          specs: normalizedSpecs,
          imageUrl: item.imageUrl || '',
          images: item.images || [],
          price: Number(item.price || 0),
          salePrice: Number(item.salePrice ?? item.discountPrice ?? item.price ?? 0),
          stockQuantity: Number(item.stockQuantity ?? item.stock ?? 0),
          isActive: item.isActive !== false,
          compareAtPrice: Number(item.compareAtPrice || 0),
          isDefault: Boolean(item.isDefault),
          status: item.status || 'active',
          attributes,
        };
      }),
      options: product.options || [],
      status: product.status || 'ACTIVE',
      isFeatured: Boolean(product.isFeatured),
      isFlashSale: Boolean(product.isFlashSale),
    });
  }

  async function reactivateProduct(product: any) {
    if (product.status !== 'INACTIVE') {
      window.alert('Chỉ sản phẩm đang tạm ẩn mới được khôi phục.');
      return;
    }
    try {
      await productApi.adminUpdateProduct(product.id, { ...product, status: 'ACTIVE', discountPrice: product.discountPrice || null });
      await loadData(tab, { force: true });
    } catch (error) {
      window.alert(`Không thể khôi phục sản phẩm:\n${productSubmitErrorMessage(error)}`);
    }
  }

  async function submitProduct(product: any) {
    if (!['DRAFT', 'REVISION_DRAFT'].includes(product.status)) {
      window.alert('Chỉ bản nháp hoặc bản chỉnh sửa đang soạn mới được gửi duyệt.');
      return;
    }
    try {
      await productApi.adminSubmitProduct(product.id);
      await loadData(tab, { force: true });
    } catch (error) {
      window.alert(`Không thể gửi duyệt sản phẩm:\n${productSubmitErrorMessage(error)}`);
    }
  }

  async function approveProduct(product: any) {
    try {
      await productApi.adminApproveProduct(product.id);
      await loadData(tab, { force: true });
    } catch (error) {
      window.alert(`Không thể duyệt sản phẩm:\n${productSubmitErrorMessage(error)}`);
    }
  }

  async function duplicateProduct(product: any) {
    const result = await productApi.adminDuplicateProduct(product.id);
    await loadData(tab, { force: true });
    window.alert(`Đã sao chép sản phẩm sang bản nháp mới: ${result.id}`);
  }

  async function bulkApproveProducts() {
    const ids = selectedProductIds.filter((id) => products.find((product) => product.id === id)?.status === 'PENDING');
    if (ids.length > 500) {
      window.alert('Mỗi lần chỉ duyệt tối đa 500 sản phẩm. Vui lòng chia nhỏ danh sách.');
      return;
    }
    if (!ids.length) {
      window.alert('Chọn ít nhất một sản phẩm đang chờ duyệt.');
      return;
    }
    const result = await productApi.adminBulkApproveProducts(ids);
    setSelectedProductIds([]);
    await loadData(tab, { force: true });
    window.alert(`Đã duyệt ${result.updated} sản phẩm. Bỏ qua: ${result.skipped.length}.`);
  }

  async function exportProducts() {
    const result = await productApi.adminExportProducts({ search: query });
    window.alert(`Đã đưa yêu cầu xuất file vào hàng đợi. Mã job: ${result.jobId}`);
  }

  async function importProducts(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      window.alert('Vui lòng chọn file CSV.');
      return;
    }
    const result = await productApi.adminImportProducts(file);
    window.alert(`Đã đưa file vào hàng đợi import. Mã job: ${result.jobId}`);
    window.setTimeout(() => void loadData(tab, { force: true }), 1500);
  }

  async function archiveProduct(product: any) {
    if (!['DRAFT', 'REVISION_DRAFT', 'INACTIVE'].includes(product.status)) {
      window.alert('Chỉ bản nháp, bản chỉnh sửa đang soạn hoặc sản phẩm đang tạm ẩn mới được lưu trữ.');
      return;
    }
    try {
      await productApi.adminArchiveProduct(product.id);
      await loadData(tab, { force: true });
    } catch (error) {
      window.alert(`Không thể lưu trữ sản phẩm:\n${productSubmitErrorMessage(error)}`);
    }
  }

  function slugifyText(text: string): string {
    return String(text)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)+/g, '');
  }

  async function confirmDelete(label: string, action: () => Promise<unknown>) {
    if (!window.confirm(`Bạn có chắc muốn xóa ${label}? Nếu mục này đã có dữ liệu liên quan, hệ thống sẽ ẩn thay vì xóa để giữ lịch sử.`)) return;
    try {
      const result = await action() as { action?: string };
      await loadData(tab, { force: true });
      if (result?.action === 'deleted') {
        window.alert(`${label} đã được xóa vì chưa có ràng buộc dữ liệu.`);
      } else if (result?.action === 'archived') {
        window.alert(`${label} đã được lưu trữ.`);
      } else if (result?.action === 'deactivated') {
        window.alert(`${label} đã có dữ liệu liên quan nên đã được ẩn.`);
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể xóa mục này.');
    }
  }

  return {
    productForm,
    setProductForm,
    productCategoryFilter,
    setProductCategoryFilter,
    productBrandFilter,
    setProductBrandFilter,
    accessorySearch,
    setAccessorySearch,
    accessoryCategoryFilter,
    setAccessoryCategoryFilter,
    accessoryBrandFilter,
    setAccessoryBrandFilter,
    attachedServiceTypeFilter,
    setAttachedServiceTypeFilter,
    attachedServiceGroupFilter,
    setAttachedServiceGroupFilter,
    attachedServiceSearch,
    setAttachedServiceSearch,
    selectedProductIds,
    setSelectedProductIds,
    previewProduct,
    setPreviewProduct,
    editingProductId,
    setEditingProductId,
    productFormOpen,
    setProductFormOpen,
    productCloseSignal,
    setProductCloseSignal,
    selectedCategory,
    selectedSubCategory,
    variantFields,
    activeVariantFields,
    productSpecFields,
    groupedProductSpecFields,
    groupedActiveVariantFields,
    productBrandOptions,
    filteredProducts,
    accessoryProductChoices,
    productAttachedServiceChoices,
    serviceGroupOptions,
    resetProductForm,
    productPayload,
    handleProductSubmit,
    editProduct,
    reactivateProduct,
    submitProduct,
    approveProduct,
    duplicateProduct,
    bulkApproveProducts,
    exportProducts,
    importProducts,
    archiveProduct,
    addVariant,
    patchVariant,
    addAccessoryOffer,
    patchAccessoryOffer,
    removeAccessoryOffer,
    addAttachedService,
    removeAttachedService,
    toggleVariantSpecField,
    confirmDelete,
  };
}
