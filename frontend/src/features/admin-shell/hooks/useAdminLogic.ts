import { useState, useMemo, useEffect, useRef } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { brandApi } from '../../../services/brandApi';
import { categoryApi } from '../../../services/categoryApi';
import { productApi } from '../../../services/productApi';
import { publicApi } from '../../../services/publicApi';
import { getAccessToken } from '../../../services/authDb';
import { adminAiCatalogApi } from '../../admin-ai-catalog/services/adminAiCatalogApi';
import { adminAuditApi } from '../../admin-audit/services/adminAuditApi';
import { useAdminBrandsLogic } from '../../admin-brands/hooks/useAdminBrandsLogic';
import { useAdminBannersLogic } from '../../admin-content/hooks/useAdminBannersLogic';
import { useAdminAccountPayablesLogic } from '../../admin-account-payables/hooks/useAdminAccountPayablesLogic';
import { useAdminContentLogic } from '../../admin-content/hooks/useAdminContentLogic';
import { adminContentApi } from '../../admin-content/services/adminContentApi';
import { useAdminCustomersLogic } from '../../admin-customers/hooks/useAdminCustomersLogic';
import { adminCustomersApi } from '../../admin-customers/services/adminCustomersApi';
import { useAdminFlashSalesLogic } from '../../admin-flash-sales/hooks/useAdminFlashSalesLogic';
import { adminFlashSalesApi } from '../../admin-flash-sales/services/adminFlashSalesApi';
import { useAdminInventoryLogic } from '../../admin-inventory/hooks/useAdminInventoryLogic';
import { useAdminOrdersLogic } from '../../admin-orders/hooks/useAdminOrdersLogic';
import { adminOrdersApi } from '../../admin-orders/services/adminOrdersApi';
import { useAdminPermissionsLogic } from '../../admin-permissions/hooks/useAdminPermissionsLogic';
import { adminPermissionsApi } from '../../admin-permissions/services/adminPermissionsApi';
import { useAdminReviewsLogic } from '../../admin-reviews/hooks/useAdminReviewsLogic';
import { adminReviewsApi } from '../../admin-reviews/services/adminReviewsApi';
import { useAdminServicesLogic } from '../../admin-services/hooks/useAdminServicesLogic';
import { adminServicesApi } from '../../admin-services/services/adminServicesApi';
import { useAdminSuppliersLogic } from '../../admin-suppliers/hooks/useAdminSuppliersLogic';
import { adminSuppliersApi } from '../../admin-suppliers/services/adminSuppliersApi';
import { useAdminVouchersLogic } from '../../admin-vouchers/hooks/useAdminVouchersLogic';
import { adminVouchersApi } from '../../admin-vouchers/services/adminVouchersApi';
import { useAdminProductsLogic } from '../../admin-products/hooks/useAdminProductsLogic';
import { adminProductsApi } from '../../admin-products/services/adminProductsApi';
import { useAdminCategoriesLogic } from '../../admin-categories/hooks/useAdminCategoriesLogic';
import { adminTabs, AdminTab, matchesSearch } from '../components/AdminDashboardConfig';
import { useAdminAccessControls } from './useAdminAccessControls';

const MAX_UPLOAD_VIDEO_DURATION_SECONDS = 300;

function readVideoDurationSeconds(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const objectUrl = URL.createObjectURL(file);
    const cleanup = () => {
      URL.revokeObjectURL(objectUrl);
      video.removeAttribute('src');
      video.load();
    };
    video.preload = 'metadata';
    video.onloadedmetadata = () => {
      const duration = video.duration;
      cleanup();
      if (!Number.isFinite(duration) || duration <= 0) {
        reject(new Error('Không đọc được thời lượng video.'));
        return;
      }
      resolve(duration);
    };
    video.onerror = () => {
      cleanup();
      reject(new Error('Không đọc được thời lượng video.'));
    };
    video.src = objectUrl;
  });
}

function categoryContainsCategory(categories: any[], selectedCategoryId: string, categoryId: unknown) {
  if (!selectedCategoryId) return true;
  if (String(categoryId || '') === selectedCategoryId) return true;
  return categories.some((category: any) => String(category.id) === String(categoryId || '') && String(category.parentId || '') === selectedCategoryId);
}

function categoryContainsProduct(categories: any[], selectedCategoryId: string, product: any) {
  if (!selectedCategoryId) return true;
  return categoryContainsCategory(categories, selectedCategoryId, product?.categoryId)
    || categoryContainsCategory(categories, selectedCategoryId, product?.subcategoryId);
}

export function useAdminLogic() {
  const { canAccessAdmin, loading, usePermission, useAnyPermission, isSuperAdmin } = useAuth();
  const [tab, setTab] = useState<AdminTab>('overview');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 350);
    return () => clearTimeout(timer);
  }, [query]);
  const [inventoryCategoryFilter, setInventoryCategoryFilter] = useState('');
  const [inventoryBrandFilter, setInventoryBrandFilter] = useState('');
  const [brandCategoryFilter, setBrandCategoryFilter] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [overview, setOverview] = useState<any>({});
  const [orders, setOrders] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [productPage, setProductPage] = useState(1);
  const [productTotal, setProductTotal] = useState(0);
  const [productTotalPages, setProductTotalPages] = useState(1);
  const [productStatusFilter, setProductStatusFilter] = useState('');
  const [productCategoryFilter, setProductCategoryFilter] = useState('');
  const [productBrandFilter, setProductBrandFilter] = useState('');
  const [attachedServices, setAttachedServices] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [brandStatusFilter, setBrandStatusFilter] = useState('all');
  const [brandPage, setBrandPage] = useState(1);
  const [brandTotal, setBrandTotal] = useState(0);
  const [supplierStatusFilter, setSupplierStatusFilter] = useState('all');
  const [supplierPage, setSupplierPage] = useState(1);
  const [supplierTotal, setSupplierTotal] = useState(0);
  const [vouchers, setVouchers] = useState<any[]>([]);
  const [flashSales, setFlashSales] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerPage, setCustomerPage] = useState(1);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [reviews, setReviews] = useState<any[]>([]);
  const [imageComments, setImageComments] = useState<any[]>([]);
  const [reviewSummary, setReviewSummary] = useState<any[]>([]);
  const [reviewStatusFilter, setReviewStatusFilter] = useState('all');
  const [reviewStarFilter, setReviewStarFilter] = useState('all');
  const [contentItems, setContentItems] = useState<any[]>([]);
  const [banners, setBanners] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [aiCatalogIndexStatus, setAiCatalogIndexStatus] = useState<any | null>(null);
  const [aiCatalogIndexJobs, setAiCatalogIndexJobs] = useState<any[]>([]);
  const [infoView, setInfoView] = useState<any | null>(null);

  const {
    canCreateContent,
    canDeleteContent,
    canManageCustomerAccess,
    canManageCustomerProfile,
    canUpdateContent,
    reportAccess,
    tabAccess,
  } = useAdminAccessControls(usePermission, useAnyPermission, Boolean(isSuperAdmin));

  const orderLogic = useAdminOrdersLogic({ setOrders });
  const serviceLogic = useAdminServicesLogic({
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const brandLogic = useAdminBrandsLogic({
    brands,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const supplierLogic = useAdminSuppliersLogic({
    suppliers,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const voucherLogic = useAdminVouchersLogic({
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const flashSaleLogic = useAdminFlashSalesLogic({
    flashSales,
    products,
    categories,
    brands,
    query,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const inventoryLogic = useAdminInventoryLogic({
    products,
    categories,
    suppliers,
    query,
    inventoryCategoryFilter,
    inventoryBrandFilter,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const accountPayableLogic = useAdminAccountPayablesLogic({
    query,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const reviewLogic = useAdminReviewsLogic({
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const contentLogic = useAdminContentLogic({
    contentItems,
    products,
    query,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const bannerLogic = useAdminBannersLogic({
    banners,
    query,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });

  const productLogic = useAdminProductsLogic({
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
  });

  const categoryLogic = useAdminCategoriesLogic({
    query,
    categories,
    setCategories,
  });

  const {
    categoryForm,
    setCategoryForm,
    editingCategoryId,
    setEditingCategoryId,
    categoryViewOnly,
    setCategoryViewOnly,
    categorySlugStatus,
    setCategorySlugStatus,
    categoryMetrics,
    setCategoryMetrics,
    categoryAuditLogs,
    setCategoryAuditLogs,
    categoryMigrationJobs,
    setCategoryMigrationJobs,
    categoryPanelBusy,
    setCategoryPanelBusy,
    categoryCloseSignal,
    setCategoryCloseSignal,
    categoryStatusFilter,
    setCategoryStatusFilter,
    rootCategories,
    subCategories,
    editingCategory,
    categoryParentMigrationHint,
    isEditingChildCategory,
    filteredCategories,
    filteredRootCategories,
    filteredCategoryTree,
    categorySlugTaken,
    derivedCategoryFilters,
    resetCategoryForm,
    handleCategorySubmit,
    editCategory,
    viewCategory,
    hideCategory,
    reactivateCategory,
    reorderCategory,
    checkCategorySlug,
    loadCategoryWorkspace,
    refreshCategoryWorkspace,
    addSpecField,
    patchSpecField,
    addCategoryFilter,
    patchCategoryFilter,
  } = categoryLogic;

  const {
    productForm,
    setProductForm,
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
    productViewOnly,
    setProductViewOnly,
    openNewProductForm,
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
    viewProduct,
    reactivateProduct,
    hideProduct,
    deleteProduct,
    submitProduct,
    approveProduct,
    duplicateProduct,
    bulkApproveProducts,
    bulkProductAction,
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
  } = productLogic;

  const {
    activeBrandImportJob,
    setActiveBrandImportJob,
    setBrandImportJobs,
  } = brandLogic;

  const inventoryBrandOptions = useMemo(() => {
    return [['', 'Tất cả thương hiệu'] as [string, string], ...brands.filter((b: any) => {
      if (!inventoryCategoryFilter) return true;
      if (b.categoryIds && b.categoryIds.some((categoryId: string) => categoryContainsCategory(categories, inventoryCategoryFilter, categoryId))) return true;
      return products.some((p: any) => (p.brandId === b.id || p.brand === b.name) && categoryContainsProduct(categories, inventoryCategoryFilter, p));
    }).map((b: any) => [String(b.id), b.name] as [string, string])];
  }, [brands, inventoryCategoryFilter, categories, products]);

  useEffect(() => {
    if (inventoryBrandFilter && !inventoryBrandOptions.some(([value]) => value === inventoryBrandFilter)) {
      setInventoryBrandFilter('');
    }
  }, [inventoryBrandFilter, inventoryBrandOptions]);

  const filteredBrands = useMemo(() => {
    return brands.filter((brand) => {
      const ms = matchesSearch(brand, query, ['name', 'code']);
      const mc = !brandCategoryFilter || (brand.categoryIds && (brand.categoryIds.includes(brandCategoryFilter) || categories.some((c: any) => c.parentId === brandCategoryFilter && brand.categoryIds.includes(c.id))));
      return ms && mc;
    });
  }, [brands, query, brandCategoryFilter, categories]);
  const filteredSuppliers = useMemo(() => suppliers, [suppliers]);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => matchesSearch(order, query, ['id', 'orderCode', 'userId', 'user_id', 'recipientName', 'recipientPhone', 'paymentMethod', 'payment_method', 'trackingCode', 'status']));
  }, [orders, query]);
  const cancelledOrders = useMemo(() => orders.filter((order) => order.status === 'CANCELLED').length, [orders]);
  const refundedOrders = useMemo(() => orders.filter((order) => order.status === 'REFUNDED' || order.status === 'RETURNED').length, [orders]);
  const filteredVouchers = useMemo(() => {
    return vouchers.filter((voucher) => matchesSearch(voucher, query, ['code', 'discountType', 'status']));
  }, [vouchers, query]);
  const filteredCustomers = customers;
  const filteredInventory = useMemo(() => {
    return inventoryLogic.inventoryLevels;
  }, [inventoryLogic.inventoryLevels]);
  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesQuery = matchesSearch(review, query, ['productName', 'userName', 'status', 'comment', 'moderationNote', 'shopReply', 'flaggedReason', 'spamReason', 'orderOutcome']);
      const matchesStatus = reviewStatusFilter === 'all' || review.status === reviewStatusFilter;
      const matchesStars = reviewStarFilter === 'all' || String(review.rating) === reviewStarFilter;
      return matchesQuery && matchesStatus && matchesStars;
    });
  }, [reviews, query, reviewStatusFilter, reviewStarFilter]);
  const filteredImageComments = useMemo(() => {
    return imageComments.filter((comment) => matchesSearch(comment, query, ['productName', 'userName', 'content', 'moderationReason', 'replyToUserName']));
  }, [imageComments, query]);
  const reviewMetrics = useMemo(() => ({
    total: reviews.length,
    pending: reviews.filter((item) => item.status === 'PENDING').length,
    published: reviews.filter((item) => item.status === 'PUBLISHED').length,
    flagged: reviews.filter((item) => item.flaggedReason || item.isSpam).length,
  }), [reviews]);
  const imageCommentMetrics = useMemo(() => ({
    total: imageComments.length,
    hidden: imageComments.filter((item) => item.isHidden).length,
    retracted: imageComments.filter((item) => item.isRetracted).length,
  }), [imageComments]);
  const revenue = useMemo(() => orders.reduce((sum, order) => sum + Number(order.totalAmount || order.total_amount || 0), 0), [orders]);
  const availableTabs = useMemo(() => adminTabs.filter((item) => tabAccess[item.id]), [tabAccess]);
  const canLoadTab = (targetTab: AdminTab) => Boolean(tabAccess[targetTab]);
  const canAdjustCustomerPoints = usePermission('customer:loyalty_adjust');
  const canRecordSupplierPayment = usePermission('payable:pay');
  const canUpdateCustomerProfile = useAnyPermission(['customer:update', 'sys:manage_users']);
  const permissionLogic = useAdminPermissionsLogic({
    customers,
    canManageCustomerAccess,
    canManageUsers: usePermission('sys:manage_users'),
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const customerLogic = useAdminCustomersLogic({
    canManageCustomerAccess,
    canManageCustomerProfile,
    canAdjustCustomerPoints,
    canIssueCustomerVoucher: usePermission('customer:issue_voucher'),
    canUpdateCustomerProfile,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const loadedAdminSectionsRef = useRef<Set<AdminTab>>(new Set());
  const loadedAdminResourcesRef = useRef<Set<string>>(new Set());
  const loadingAdminResourcesRef = useRef<Map<string, Promise<void>>>(new Map());
  const preloadingAdminSectionsRef = useRef(false);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab(tab)) void loadData(tab);
  }, [canAccessAdmin, tab, tabAccess]);

  useEffect(() => {
    if (!canAccessAdmin || preloadingAdminSectionsRef.current) return;
    preloadingAdminSectionsRef.current = true;
    const preload = () => {
      if (!canAccessAdmin || !canLoadTab('products')) return;
      void loadData('products', { silent: true, prefetch: true });
    };
    if ('requestIdleCallback' in window) {
      const idleId = window.requestIdleCallback(preload, { timeout: 2500 });
      return () => window.cancelIdleCallback(idleId);
    }
    const timer = globalThis.setTimeout(preload, 1200);
    return () => globalThis.clearTimeout(timer);
  }, [canAccessAdmin, tabAccess]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('categories') && tab === 'categories') {
      void loadCategoryWorkspace(editingCategoryId);
    }
  }, [canAccessAdmin, tab, editingCategoryId, tabAccess]);

  useEffect(() => {
    if (tab !== 'categories' || !editingCategoryId) return;
    if (!categoryMigrationJobs.some((job) => ['PENDING', 'RUNNING', 'IN_PROGRESS'].includes(String(job.status)))) return;
    const timer = window.setInterval(() => {
      void loadCategoryWorkspace(editingCategoryId);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [categoryMigrationJobs, editingCategoryId, tab]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('brands') && tab === 'brands') void loadData('brands', { force: true });
  }, [canAccessAdmin, brandPage, brandStatusFilter, query, tab, tabAccess]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('suppliers') && tab === 'suppliers') void loadData('suppliers', { force: true });
  }, [canAccessAdmin, supplierPage, supplierStatusFilter, query, tab, tabAccess]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('inventoryReceipts') && tab === 'inventoryReceipts') void loadData('inventoryReceipts', { force: true });
  }, [canAccessAdmin, query, tab, tabAccess]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('accountPayables') && tab === 'accountPayables') void loadData('accountPayables', { force: true });
  }, [canAccessAdmin, query, tab, tabAccess]);

  useEffect(() => {
    if (tab === 'products') {
      setProductPage(1);
    }
  }, [query, productCategoryFilter, productBrandFilter, productStatusFilter, tab]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('products') && tab === 'products') {
      void loadData('products', { force: true });
    }
  }, [canAccessAdmin, tab, productPage, query, productCategoryFilter, productBrandFilter, productStatusFilter, tabAccess]);

  useEffect(() => {
    if (tab === 'customers') {
      setCustomerPage(1);
    }
  }, [query]);

  useEffect(() => {
    setBrandPage(1);
  }, [brandStatusFilter, query]);

  useEffect(() => {
    setSupplierPage(1);
  }, [supplierStatusFilter, query]);

  useEffect(() => {
    if (!activeBrandImportJob || ['COMPLETED', 'FAILED'].includes(activeBrandImportJob.status)) return;
    const timer = window.setInterval(async () => {
      const nextJob = await brandApi.adminGetBrandImportJob(activeBrandImportJob.id).catch(() => null);
      if (!nextJob) return;
      setActiveBrandImportJob(nextJob);
      if (['COMPLETED', 'FAILED'].includes(nextJob.status)) {
        window.clearInterval(timer);
        await loadData(tab, { force: true });
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [activeBrandImportJob?.id, activeBrandImportJob?.status]);

  useEffect(() => {
    if (!availableTabs.some((item) => item.id === tab)) {
      setTab(availableTabs[0]?.id || 'overview');
    }
  }, [availableTabs, tab]);

  useEffect(() => {
    if (canAccessAdmin && canLoadTab('customers') && tab === 'customers') {
      void loadData('customers', { force: true });
    }
  }, [canAccessAdmin, tab, customerPage, debouncedQuery, tabAccess]);

  async function loadData(targetTab: AdminTab = tab, options: { force?: boolean; silent?: boolean; prefetch?: boolean } = {}) {
    if (!canLoadTab(targetTab)) return;
    if (options.prefetch && loadedAdminSectionsRef.current.has(targetTab)) return;
    if (!options.silent) setBusy(true);
    try {
      const runResource = async (key: string, loader: () => Promise<void>, force = options.force) => {
        if (!force && loadedAdminResourcesRef.current.has(key)) return;
        const loadingKey = force ? `${key}:force` : key;
        const existing = loadingAdminResourcesRef.current.get(loadingKey);
        if (existing) return existing;
        const task = loader()
          .then(() => {
            loadedAdminResourcesRef.current.add(key);
          })
          .finally(() => {
            loadingAdminResourcesRef.current.delete(loadingKey);
          });
        loadingAdminResourcesRef.current.set(loadingKey, task);
        return task;
      };
      const ensureOverview = async () => {
        const overviewData = await publicApi.adminOverview().catch(() => ({}));
        setOverview(overviewData);
      };
      const loadProducts = async () => {
        const isProductListTab = targetTab === 'products';
        const productResourceKey = isProductListTab
          ? `products:${productPage}:${query.trim()}:${productStatusFilter}:${productCategoryFilter}:${productBrandFilter}`
          : 'products:all';
        await runResource(productResourceKey, async () => {
          const productData = isProductListTab
            ? await productApi.adminListProducts({
              page: productPage,
              limit: 20,
              search: query.trim(),
              status: productStatusFilter || undefined,
              categoryId: productCategoryFilter || undefined,
              brandId: productBrandFilter || undefined,
            })
            : await productApi.adminListProducts({ limit: 200 }).catch(() => publicApi.listProducts({ limit: 100 }));
          if (Array.isArray(productData)) {
            setProducts(productData);
            setProductTotal(productData.length);
            setProductTotalPages(1);
          } else {
            setProducts(productData.items || []);
            setProductTotal(productData.totalRecords || 0);
            setProductTotalPages(productData.totalPages || 1);
          }
        });
      };
      const loadCategories = async () => {
        await runResource('categories', async () => {
          const categoryData = await categoryApi.adminListCategories().catch(() => categoryApi.listCategories());
          setCategories(categoryData);
        });
      };
      const loadBrands = async () => {
        const brandResourceKey = targetTab === 'brands'
          ? `brands:${brandPage}:${brandStatusFilter}:${query.trim()}`
          : 'brands:all';
        await runResource(brandResourceKey, async () => {
          const brandData = targetTab === 'brands'
            ? await brandApi.adminListBrands({ page: brandPage, limit: 10, search: query, status: brandStatusFilter }).catch(() => brandApi.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 10 })))
            : await brandApi.adminListBrands({ page: 1, limit: 1000, status: 'all' }).catch(() => brandApi.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 1000 })));
          setBrands(Array.isArray(brandData) ? brandData : brandData.items || []);
          setBrandTotal(Array.isArray(brandData) ? brandData.length : brandData.total || 0);
        });
        if (targetTab === 'brands') {
          await runResource('brand-import-jobs', async () => {
            setBrandImportJobs(await brandApi.adminListBrandImportJobs().catch(() => []));
          });
        }
      };
      const loadServices = async () => {
        await runResource('attached-services', async () => {
          const serviceData = await adminServicesApi.adminListAttachedServices().catch(() => []);
          setAttachedServices(serviceData);
        });
      };
      const loadSuppliers = async () => {
        const supplierResourceKey = targetTab === 'suppliers'
          ? `suppliers:${supplierPage}:${supplierStatusFilter}:${query.trim()}`
          : 'suppliers:all';
        await runResource(supplierResourceKey, async () => {
          const supplierData = await adminSuppliersApi.adminListSuppliers(targetTab === 'suppliers'
            ? { page: supplierPage, limit: 10, search: query, status: supplierStatusFilter }
            : { page: 1, limit: 1000, status: 'active' }
          ).catch(() => ({ items: [], total: 0, page: 1, limit: 10 }));
          setSuppliers(supplierData.items || []);
          setSupplierTotal(supplierData.total || 0);
        });
      };
      const loadOrders = async () => {
        const orderData = await adminOrdersApi.listOrders().catch(() => []);
        setOrders(orderData);
      };
      const loadVouchers = async () => {
        const voucherData = await adminVouchersApi.adminListVouchers().catch(() => []);
        setVouchers(voucherData);
      };
      const loadFlashSales = async () => {
        const saleData = await adminFlashSalesApi.adminListFlashSales().catch(() => []);
        setFlashSales(saleData);
      };
      const customerPickerLimit = 100;
      const loadCustomers = async (role: 'CUSTOMER' | 'STAFF_ADMIN' = 'CUSTOMER', options: { picker?: boolean } = {}) => {
        const customerData = await adminCustomersApi.adminListCustomers({
          search: role === 'CUSTOMER' && !options.picker ? debouncedQuery : undefined,
          page: role === 'CUSTOMER' && !options.picker ? customerPage : 1,
          limit: role === 'CUSTOMER' && !options.picker ? 20 : customerPickerLimit,
          role,
        }).catch(() => ({ items: [], total: 0, page: 1, limit: role === 'CUSTOMER' && !options.picker ? 20 : customerPickerLimit }));
        setCustomers(Array.isArray(customerData) ? customerData : customerData.items || []);
        setCustomerTotal(Array.isArray(customerData) ? customerData.length : customerData.total || 0);
      };
      const loadReviews = async () => {
        const [reviewData, reviewSummaryData] = await Promise.all([
          adminReviewsApi.adminListReviews().catch(() => []),
          adminReviewsApi.adminListReviewSummary().catch(() => []),
        ]);
        setReviews(reviewData);
        setReviewSummary(reviewSummaryData);
      };
      const loadProductInteractions = async () => {
        const imageCommentData = await adminContentApi.adminListImageComments().catch(() => []);
        setImageComments(imageCommentData);
      };
      const loadContent = async () => {
        const contentData = await adminContentApi.adminListVideos().catch(() => []);
        setContentItems(contentData);
      };
      const loadBanners = async () => {
        const bannerData = await adminContentApi.adminListBanners().catch(() => []);
        setBanners(bannerData);
      };
      const loadAudit = async () => {
        const auditData = await adminAuditApi.adminListAuditLogs({ limit: 100 }).catch(() => []);
        setAuditLogs(auditData);
      };
      const loadAiCatalogIndex = async () => {
        await runResource('ai-catalog-index', async () => {
          const [statusData, jobsData] = await Promise.all([
            adminAiCatalogApi.getStatus(),
            adminAiCatalogApi.listJobs(10),
          ]);
          setAiCatalogIndexStatus(statusData);
          setAiCatalogIndexJobs(jobsData.items || statusData.recent_refresh_jobs || []);
        });
      };
      const loadPermissions = async () => {
        const [permissionData, roleData] = await Promise.all([
          adminPermissionsApi.adminListPermissions().catch(() => []),
          adminPermissionsApi.adminListRoles().catch(() => []),
        ]);
        permissionLogic.setPermissions(permissionData);
        permissionLogic.setRoles(roleData);
        const roleEntries = await Promise.all((roleData || []).map(async (role: any) => {
          const detail = await adminPermissionsApi.adminGetRolePermissions(role.id).catch(() => ({ permissionCodes: [] }));
          return [role.id, detail.permissionCodes || []] as const;
        }));
        permissionLogic.setRolePermissionMap(Object.fromEntries(roleEntries));
      };

      if (options.force) loadedAdminSectionsRef.current.delete(targetTab);
      if (options.force) {
        if (targetTab === 'products' || targetTab === 'inventory' || targetTab === 'inventoryReceipts') {
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('products:') || key === 'products')
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
        if (targetTab === 'inventory' || targetTab === 'inventoryReceipts' || targetTab === 'accountPayables') {
          loadedAdminResourcesRef.current.delete('categories');
          loadedAdminResourcesRef.current.delete('brands:all');
          loadedAdminResourcesRef.current.delete('suppliers:all');
          loadedAdminResourcesRef.current.delete('inventory-receipts');
        }
        if (targetTab === 'categories') loadedAdminResourcesRef.current.delete('categories');
        if (targetTab === 'services') loadedAdminResourcesRef.current.delete('attached-services');
        if (targetTab === 'interactions') loadedAdminResourcesRef.current.delete('product-interactions');
        if (targetTab === 'banners') loadedAdminResourcesRef.current.delete('banners');
        if (targetTab === 'aiCatalogIndex') loadedAdminResourcesRef.current.delete('ai-catalog-index');
        if (targetTab === 'flashSales') {
          loadedAdminResourcesRef.current.delete('flash-sales');
          loadedAdminResourcesRef.current.delete('categories');
          loadedAdminResourcesRef.current.delete('brands:all');
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('products:') || key === 'products')
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
        if (targetTab === 'brands') {
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('brands:') || key === 'brand-import-jobs')
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
        if (targetTab === 'suppliers') {
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('suppliers:'))
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
      }
      // Tổng quan là read-model tổng hợp từ nhiều phân hệ nên phải đọc lại mỗi
      // lần người dùng quay về tab để không giữ số liệu đơn hàng đã lỗi thời.
      if (loadedAdminSectionsRef.current.has(targetTab) && !options.force && targetTab !== 'overview') return;

      if (targetTab === 'overview') {
        await ensureOverview();
      } else if (targetTab === 'products') {
        await Promise.all([
          loadProducts(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('brands') ? loadBrands() : Promise.resolve(),
          canLoadTab('services') ? loadServices() : Promise.resolve(),
        ]);
      } else if (targetTab === 'categories') {
        await loadCategories();
      } else if (targetTab === 'brands') {
        await loadBrands();
      } else if (targetTab === 'suppliers') {
        await loadSuppliers();
      } else if (targetTab === 'services') {
        await loadServices();
      } else if (targetTab === 'orders') {
        await loadOrders();
      } else if (targetTab === 'vouchers') {
        await Promise.all([
          loadVouchers(),
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('customers') ? loadCustomers('CUSTOMER', { picker: true }) : Promise.resolve(),
        ]);
      } else if (targetTab === 'flashSales') {
        await Promise.all([
          loadFlashSales(),
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('brands') ? loadBrands() : Promise.resolve(),
        ]);
      } else if (targetTab === 'customers') {
        await Promise.all([
          loadCustomers(),
          canLoadTab('vouchers') ? loadVouchers() : Promise.resolve(),
        ]);
      } else if (targetTab === 'inventory') {
        await Promise.all([
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('brands') ? loadBrands() : Promise.resolve(),
          canLoadTab('suppliers') ? loadSuppliers() : Promise.resolve(),
          inventoryLogic.loadInventoryLevels(query),
        ]);
      } else if (targetTab === 'inventoryReceipts') {
        await Promise.all([
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('brands') ? loadBrands() : Promise.resolve(),
          canLoadTab('suppliers') ? loadSuppliers() : Promise.resolve(),
          inventoryLogic.loadInventoryReceipts(query),
        ]);
      } else if (targetTab === 'accountPayables') {
        await Promise.all([
          canLoadTab('suppliers') ? loadSuppliers() : Promise.resolve(),
          accountPayableLogic.loadAccountPayables(query),
        ]);
      } else if (targetTab === 'reviews') {
        await loadReviews();
      } else if (targetTab === 'interactions') {
        await loadProductInteractions();
      } else if (targetTab === 'content') {
        await Promise.all([
          loadContent(),
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
          canLoadTab('brands') ? loadBrands() : Promise.resolve(),
        ]);
      } else if (targetTab === 'banners') {
        await Promise.all([
          loadBanners(),
          canLoadTab('products') ? loadProducts() : Promise.resolve(),
          canLoadTab('categories') ? loadCategories() : Promise.resolve(),
        ]);
      } else if (targetTab === 'audit') {
        await loadAudit();
      } else if (targetTab === 'aiCatalogIndex') {
        await loadAiCatalogIndex();
      } else if (targetTab === 'permissions') {
        await Promise.all([loadPermissions(), loadCustomers('STAFF_ADMIN')]);
      }
      loadedAdminSectionsRef.current.add(targetTab);
    } finally {
      if (!options.silent) setBusy(false);
    }
  }

  async function uploadFiles(files: FileList | null | File[], folder: string = 'products'): Promise<string[]> {
    if (!files || files.length === 0) return [];
    const fileArray = Array.from(files);
    const urls: string[] = [];

    for (const file of fileArray) {
      try {
        let durationSeconds: number | undefined;
        if (file.type.startsWith('video/')) {
          durationSeconds = await readVideoDurationSeconds(file);
          if (durationSeconds > MAX_UPLOAD_VIDEO_DURATION_SECONDS) {
            throw new Error('Video không được dài quá 5 phút.');
          }
        }
        const res = await adminProductsApi.adminCreatePresignedUpload({
          folder,
          contentType: file.type,
          size: file.size,
          durationSeconds,
        });

        const { uploadUrl, publicUrl, storage } = res;

        const headers: Record<string, string> = {
          'Content-Type': file.type,
        };

        if (storage === 'local') {
          const token = getAccessToken();
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
          }
          if (durationSeconds !== undefined) {
            headers['X-Media-Duration-Seconds'] = String(durationSeconds);
          }
        }

        const uploadRes = await fetch(uploadUrl, {
          method: 'PUT',
          body: file,
          headers,
        });

        if (!uploadRes.ok) {
          throw new Error(`Tải file lên thất bại với mã lỗi: ${uploadRes.status}`);
        }

        urls.push(publicUrl);
      } catch (error) {
        console.error('Lỗi khi tải file:', error);
        alert(error instanceof Error ? error.message : 'Tải file lên thất bại.');
      }
    }

    return urls;
  }

  return {
    uploadFiles,
    productCategoryFilter,
    setProductCategoryFilter,
    productBrandFilter,
    setProductBrandFilter,
    tab,
    setTab,
    query,
    setQuery,
    inventoryCategoryFilter,
    setInventoryCategoryFilter,
    inventoryBrandFilter,
    setInventoryBrandFilter,
    brandCategoryFilter,
    setBrandCategoryFilter,
    sidebarOpen,
    setSidebarOpen,
    busy,
    infoView,
    setInfoView,
    setBusy,
    overview,
    setOverview,
    orders,
    setOrders,
    products,
    setProducts,
    productPage,
    setProductPage,
    productTotal,
    setProductTotal,
    productTotalPages,
    setProductTotalPages,
    productStatusFilter,
    setProductStatusFilter,
    attachedServices,
    setAttachedServices,
    categories,
    setCategories,
    brands,
    setBrands,
    suppliers,
    setSuppliers,
    brandStatusFilter,
    setBrandStatusFilter,
    brandPage,
    setBrandPage,
    brandTotal,
    setBrandTotal,
    supplierStatusFilter,
    setSupplierStatusFilter,
    supplierPage,
    setSupplierPage,
    supplierTotal,
    setSupplierTotal,
    vouchers,
    setVouchers,
    flashSales,
    setFlashSales,
    ...flashSaleLogic,
    customers,
    setCustomers,
    customerPage,
    setCustomerPage,
    customerTotal,
    setCustomerTotal,
    canAdjustCustomerPoints,
    canRecordSupplierPayment,
    ...customerLogic,
    reviews,
    setReviews,
    imageComments,
    setImageComments,
    reviewSummary,
    setReviewSummary,
    reviewStatusFilter,
    setReviewStatusFilter,
    reviewStarFilter,
    setReviewStarFilter,
    contentItems,
    setContentItems,
    banners,
    setBanners,
    ...bannerLogic,
    ...contentLogic,
    auditLogs,
    setAuditLogs,
    aiCatalogIndexStatus,
    setAiCatalogIndexStatus,
    aiCatalogIndexJobs,
    setAiCatalogIndexJobs,
    ...permissionLogic,
    ...inventoryLogic,
    ...accountPayableLogic,
    ...orderLogic,
    productForm,
    setProductForm,
    ...serviceLogic,
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
    categoryForm,
    setCategoryForm,
    ...brandLogic,
    ...voucherLogic,
    editingProductId,
    setEditingProductId,
    productFormOpen,
    setProductFormOpen,
    productViewOnly,
    setProductViewOnly,
    openNewProductForm,
    productCloseSignal,
    setProductCloseSignal,
    editingCategoryId,
    setEditingCategoryId,
    categoryViewOnly,
    setCategoryViewOnly,
    categorySlugStatus,
    setCategorySlugStatus,
    categoryMetrics,
    setCategoryMetrics,
    categoryAuditLogs,
    setCategoryAuditLogs,
    categoryMigrationJobs,
    setCategoryMigrationJobs,
    categoryPanelBusy,
    setCategoryPanelBusy,
    categoryCloseSignal,
    setCategoryCloseSignal,
    categoryStatusFilter,
    setCategoryStatusFilter,
    rootCategories,
    subCategories,
    editingCategory,
    selectedCategory,
    selectedSubCategory,
    groupedProductSpecFields,
    groupedActiveVariantFields,
    productBrandOptions,
    inventoryBrandOptions,
    filteredProducts,
    accessoryProductChoices,
    filteredCategories,
    filteredRootCategories,
    filteredCategoryTree,
    categorySlugTaken,
    filteredBrands,
    filteredSuppliers,
    filteredOrders,
    cancelledOrders,
    refundedOrders,
    filteredVouchers,
    filteredCustomers,
    filteredInventory,
    filteredReviews,
    filteredImageComments,
    reviewMetrics,
    imageCommentMetrics,
    revenue,
    availableTabs,
    loadedAdminSectionsRef,
    preloadingAdminSectionsRef,
    serviceGroupOptions,
    productAttachedServiceChoices,
    derivedCategoryFilters,
    loadData,
    loadCategoryWorkspace,
    refreshCategoryWorkspace,
    handleProductSubmit,
    handleCategorySubmit,
    confirmDelete,
    reactivateProduct,
    hideProduct,
    deleteProduct,
    submitProduct,
    approveProduct,
    duplicateProduct,
    bulkApproveProducts,
    bulkProductAction,
    exportProducts,
    importProducts,
    archiveProduct,
    hideCategory,
    reactivateCategory,
    reorderCategory,
    checkCategorySlug,
    ...reviewLogic,
    ...supplierLogic,
    resetProductForm,
    resetCategoryForm,
    productPayload,
    editProduct,
    viewProduct,
    editCategory,
    viewCategory,
    addSpecField,
    patchSpecField,
    addCategoryFilter,
    patchCategoryFilter,
    addVariant,
    patchVariant,
    addAccessoryOffer,
    patchAccessoryOffer,
    removeAccessoryOffer,
    addAttachedService,
    removeAttachedService,
    toggleVariantSpecField,
    categoryParentMigrationHint,
    isEditingChildCategory,
    variantFields,
    activeVariantFields,
    productSpecFields,
    canManageCustomerAccess,
    canManageCustomerProfile,
    canUpdateCustomerProfile,
    canCreateContent,
    canUpdateContent,
    canDeleteContent,
    reportAccess,
    canAccessAdmin,
    loading,
    usePermission,
    useAnyPermission,
    isSuperAdmin
  };
}
