import { useState, useMemo, type FormEvent } from 'react';
import { apiDb } from '../../../services/apiDb';
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

  const accessoryProductChoices = useMemo(() => {
    const selectedCategory = categories.find((category) => sameId(category.id, accessoryCategoryFilter));
    const childCategoryIds = new Set(categories.filter((category) => sameId(category.parentId, accessoryCategoryFilter)).map((category) => String(category.id)));
    return products
      .filter((product) => !sameId(product.id, editingProductId))
      .filter((product) => !productForm.accessoryOffers.some((offer) => sameId(offer.productId, product.id)))
      .filter((product) => {
        if (!accessoryCategoryFilter) return true;
        return sameId(product.categoryId, accessoryCategoryFilter)
          || sameId(product.subcategoryId, accessoryCategoryFilter)
          || childCategoryIds.has(String(product.categoryId || ''))
          || childCategoryIds.has(String(product.subcategoryId || ''))
          || (!!selectedCategory && [product.category, product.categoryName, product.subcategoryName].some((value) => String(value || '').toLowerCase() === String(selectedCategory.name || selectedCategory.code || selectedCategory.slug || '').toLowerCase()));
      })
      .filter((product) => !accessoryBrandFilter || sameId(product.brandId, accessoryBrandFilter) || sameId(product.brand, brands.find((brand) => sameId(brand.id, accessoryBrandFilter))?.name))
      .filter((product) => matchesSearch(product, accessorySearch, ['name', 'sku', 'brand', 'brandName', 'categoryName', 'category']))
      .slice(0, 50);
  }, [accessoryBrandFilter, accessoryCategoryFilter, accessorySearch, brands, categories, editingProductId, productForm.accessoryOffers, products]);

  const productAttachedServiceChoices = useMemo(() => {
    const keyword = attachedServiceSearch.trim().toLowerCase();
    return attachedServices
      .filter((service) => service.isActive !== false)
      .filter((service) => !productForm.attachedServices.some((item) => item.serviceId === service.id))
      .filter((service) => !attachedServiceTypeFilter || service.serviceType === attachedServiceTypeFilter)
      .filter((service) => !attachedServiceGroupFilter || service.attributeGroup === attachedServiceGroupFilter)
      .filter((service) => {
        if (!keyword) return true;
        return [service.name, service.code, service.attributeGroup, service.serviceType]
          .some((value) => String(value || '').toLowerCase().includes(keyword));
      });
  }, [attachedServiceGroupFilter, attachedServiceSearch, attachedServiceTypeFilter, attachedServices, productForm.attachedServices]);

  const serviceGroupOptions = useMemo(() => {
    const groups = new Set<string>();
    attachedServices.forEach((service) => {
      const group = String(service.attributeGroup || '').trim();
      if (group) groups.add(group);
    });
    return Array.from(groups).sort((left, right) => left.localeCompare(right));
  }, [attachedServices]);

  const colorOptionName = 'Màu sắc';

  function activeVariantOptionName(key: string) {
    return activeVariantFields.find((field) => field.key === key)?.label || key;
  }

  function buildVariantAttributes(variant: VariantForm): Record<string, string> {
    const attributes: Record<string, string> = {};
    const colorValue = String(variant.colorName || variant.attributes?.[colorOptionName] || variant.attributes?.Color || '').trim();
    if (colorValue) {
      attributes[colorOptionName] = colorValue;
    }
    productForm.variantSpecKeys.forEach((key) => {
      const optionName = activeVariantOptionName(key);
      const value = String(variant.specs?.[key] || variant.attributes?.[optionName] || '').trim();
      if (value) {
        attributes[optionName] = value;
      }
    });
    return attributes;
  }

  function deriveOptionsFromVariants(variants: VariantForm[]) {
    const optionValues = new Map<string, string[]>();
    variants.forEach((variant) => {
      Object.entries(buildVariantAttributes(variant)).forEach(([name, value]) => {
        if (!optionValues.has(name)) optionValues.set(name, []);
        const values = optionValues.get(name)!;
        if (!values.includes(value)) values.push(value);
      });
    });
    return Array.from(optionValues.entries()).map(([name, values]) => ({ name, values }));
  }

  function resetProductForm() {
    setEditingProductId(null);
    setProductForm({ ...emptyProduct, images: [], specifications: {}, variants: [] });
    setAccessorySearch('');
    setAccessoryCategoryFilter('');
    setAccessoryBrandFilter('');
  }

  function productPayload() {
    const specifications = {
      ...productForm.specifications,
      _variantSpecKeys: productForm.variantSpecKeys,
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
    const derivedOptions = deriveOptionsFromVariants(sortedVariants);
    return {
      name: productForm.name,
      price: productForm.price,
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
        storage: '',
        ram: '',
        configuration: '',
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
    if ((productForm.variantSpecKeys.length > 0 || variants.some((variant) => String(variant.colorName || '').trim())) && variants.length === 0) {
      return 'Sản phẩm có thuộc tính phải có ít nhất một biến thể.';
    }

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
    try {
      if (currentEditingProductId) {
        await apiDb.adminUpdateProduct(currentEditingProductId, productPayload());
      } else {
        await apiDb.adminCreateProduct(productPayload());
      }
    } catch (error) {
      const action = currentEditingProductId ? 'lưu thay đổi' : 'thêm sản phẩm';
      window.alert(`Không thể ${action}:\n${productSubmitErrorMessage(error)}`);
      return;
    }
    resetProductForm();
    setProductCloseSignal((value) => value + 1);
    await loadData(tab, { force: true });
    window.alert(currentEditingProductId ? 'Đã lưu thay đổi sản phẩm thành công.' : 'Đã thêm sản phẩm thành công.');
  }

  function editProduct(product: any) {
    setEditingProductId(product.id);
    const savedVariantSpecKeys = Array.isArray(product.specifications?._variantSpecKeys)
      ? product.specifications._variantSpecKeys
      : Array.from(new Set((product.variants || []).flatMap((item: any) => Object.keys(item.specs || {}))));
    const cleanSpecifications = { ...(product.specifications || {}) };
    productExtraKeys.forEach((key) => delete cleanSpecifications[key]);
    setProductForm({
      ...emptyProduct,
      name: product.name || '',
      price: Number(product.price || 0),
      discountPrice: Number(product.discountPrice || 0),
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
      accessoryOffers: (product.salesConfig?.accessoryOffers || []).map((item: any) => ({
        productId: item.productId || '',
        productName: item.productName || '',
        productSku: item.productSku || '',
        imageUrl: item.imageUrl || '',
        images: item.images || [],
        discountType: item.discountType === 'FIXED' ? 'FIXED' : 'PERCENT',
        discountValue: Number(item.discountValue || 0),
        maxQuantity: Number(item.maxQuantity || 1),
      })),
      attachedServices: (product.salesConfig?.attachedServices || []).map((item: any) => ({
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
      warrantyPolicy: normalizeWarrantyPolicy(product.salesConfig?.warrantyPolicy || product.specifications?._warrantyPolicy || defaultWarrantyPolicy),
      updatedAt: product.updatedAt || '',
      version: Number(product.version || 1),
      variantSpecKeys: savedVariantSpecKeys,
      variants: (product.variants || []).map((item: any) => ({
        ...emptyVariant,
        id: item.id,
        sku: item.sku || '',
        colorName: item.colorName || '',
        colorCode: item.colorCode || '#111827',
        storage: item.storage || '',
        ram: item.ram || '',
        configuration: item.configuration || '',
        specs: item.specs || {},
        imageUrl: item.imageUrl || '',
        price: Number(item.price || 0),
        salePrice: Number(item.salePrice || 0),
        isActive: item.isActive !== false,
        compareAtPrice: Number(item.compareAtPrice || 0),
        isDefault: Boolean(item.isDefault),
        status: item.status || 'active',
        attributes: item.attributes || {},
      })),
      options: product.options || [],
      status: product.status || 'ACTIVE',
      isFeatured: Boolean(product.isFeatured),
      isFlashSale: Boolean(product.isFlashSale),
    });
  }

  async function reactivateProduct(product: any) {
    await apiDb.adminUpdateProduct(product.id, { ...product, status: 'ACTIVE', discountPrice: product.discountPrice || null });
    await loadData(tab, { force: true });
  }

  async function submitProduct(product: any) {
    await apiDb.adminSubmitProduct(product.id);
    await loadData(tab, { force: true });
  }

  async function approveProduct(product: any) {
    await apiDb.adminApproveProduct(product.id);
    await loadData(tab, { force: true });
  }

  async function duplicateProduct(product: any) {
    const result = await apiDb.adminDuplicateProduct(product.id);
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
    const result = await apiDb.adminBulkApproveProducts(ids);
    setSelectedProductIds([]);
    await loadData(tab, { force: true });
    window.alert(`Đã duyệt ${result.updated} sản phẩm. Bỏ qua: ${result.skipped.length}.`);
  }

  async function exportProducts() {
    const result = await apiDb.adminExportProducts({ search: query });
    window.alert(`Đã đưa yêu cầu xuất file vào hàng đợi. Mã job: ${result.jobId}`);
  }

  async function importProducts(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      window.alert('Vui lòng chọn file CSV.');
      return;
    }
    const result = await apiDb.adminImportProducts(file);
    window.alert(`Đã đưa file vào hàng đợi import. Mã job: ${result.jobId}`);
    window.setTimeout(() => void loadData(tab, { force: true }), 1500);
  }

  async function archiveProduct(product: any) {
    await apiDb.adminArchiveProduct(product.id);
    await loadData(tab, { force: true });
  }

  function addVariant() {
    setProductForm((prev) => ({ ...prev, variants: [...prev.variants, { ...emptyVariant, price: prev.price, salePrice: prev.discountPrice }] }));
  }

  function patchVariant(index: number, patch: Partial<VariantForm>) {
    setProductForm((prev) => ({ ...prev, variants: prev.variants.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  function addAccessoryOffer(item: any) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: [
        ...prev.accessoryOffers,
        {
          productId: item.id,
          productName: item.name || '',
          productSku: item.sku || '',
          imageUrl: item.imageUrl || '',
          discountType: 'PERCENT',
          discountValue: 25,
          maxQuantity: 1,
        },
      ],
    }));
    setAccessorySearch('');
  }

  function patchAccessoryOffer(productId: string, patch: Partial<AccessoryOfferForm>) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.map((item) => (item.productId === productId ? { ...item, ...patch } : item)),
    }));
  }

  function removeAccessoryOffer(productId: string) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.filter((item) => item.productId !== productId),
    }));
  }

  function addAttachedService(service: any) {
    const group = String(service.attributeGroup || '').trim();
    if (group && productForm.attachedServices.some((item) => item.serviceType === service.serviceType && item.attributeGroup === group)) {
      window.alert('Mỗi nhóm thuộc tính của dịch vụ chỉ được chọn một lựa chọn. Hãy bỏ lựa chọn cũ trước khi chọn lựa chọn mới.');
      return;
    }
    setProductForm((prev) => prev.attachedServices.some((item) => item.serviceId === service.id)
      ? prev
      : {
        ...prev,
        attachedServices: [
          ...prev.attachedServices,
          {
            serviceId: service.id,
            name: service.name || '',
            code: service.code || '',
            serviceType: service.serviceType || 'SUPPORT_SERVICE',
            attributeGroup: service.attributeGroup || '',
            durationMonths: Number(service.durationMonths || 0),
            priceMode: service.priceMode || 'FIXED',
            fixedPrice: Number(service.fixedPrice || 0),
            percentValue: Number(service.percentValue || 0),
          },
        ],
      });
  }

  function removeAttachedService(serviceId: string) {
    setProductForm((prev) => ({ ...prev, attachedServices: prev.attachedServices.filter((item) => item.serviceId !== serviceId) }));
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

  function toggleVariantSpecField(key: string, checked: boolean) {
    setProductForm((prev) => ({
      ...prev,
      variantSpecKeys: checked ? [...new Set([...prev.variantSpecKeys, key])] : prev.variantSpecKeys.filter((item) => item !== key),
      variants: checked
        ? prev.variants
        : prev.variants.map((variant) => {
          const specs = { ...variant.specs };
          delete specs[key];
          return { ...variant, specs };
        }),
    }));
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
