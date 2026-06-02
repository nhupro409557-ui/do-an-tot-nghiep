import { useState, useMemo, useEffect, useRef } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { apiDb } from '../../../services/apiDb';
import { getAccessToken } from '../../../services/authDb';
import { useAdminBrandsLogic } from './useAdminBrandsLogic';
import { useAdminContentLogic } from './useAdminContentLogic';
import { useAdminCustomersLogic } from './useAdminCustomersLogic';
import { useAdminInventoryLogic } from './useAdminInventoryLogic';
import { useAdminOrdersLogic } from './useAdminOrdersLogic';
import { useAdminPermissionsLogic } from './useAdminPermissionsLogic';
import { useAdminReviewsLogic } from './useAdminReviewsLogic';
import { useAdminServicesLogic } from './useAdminServicesLogic';
import { useAdminVouchersLogic } from './useAdminVouchersLogic';
import { useAdminProductsLogic } from './useAdminProductsLogic';
import { useAdminCategoriesLogic } from './useAdminCategoriesLogic';
import { adminTabs, AdminTab } from '../AdminDashboardConfig';
import {
  matchesSearch,
} from '../AdminDashboardConfig';

export function useAdminLogic() {
  const { canAccessAdmin, loading, usePermission, useAnyPermission, isSuperAdmin } = useAuth();
  const [tab, setTab] = useState<AdminTab>('overview');
  const [query, setQuery] = useState('');
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
  const [brandStatusFilter, setBrandStatusFilter] = useState('all');
  const [brandPage, setBrandPage] = useState(1);
  const [brandTotal, setBrandTotal] = useState(0);
  const [vouchers, setVouchers] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerPage, setCustomerPage] = useState(1);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [reviews, setReviews] = useState<any[]>([]);
  const [imageComments, setImageComments] = useState<any[]>([]);
  const [reviewSummary, setReviewSummary] = useState<any[]>([]);
  const [reviewStatusFilter, setReviewStatusFilter] = useState('all');
  const [reviewStarFilter, setReviewStarFilter] = useState('all');
  const [contentItems, setContentItems] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  const orderLogic = useAdminOrdersLogic({ setOrders });
  const serviceLogic = useAdminServicesLogic({
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const brandLogic = useAdminBrandsLogic({
    brands,
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const voucherLogic = useAdminVouchersLogic({
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const inventoryLogic = useAdminInventoryLogic({
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
  } = productLogic;

  const {
    activeBrandImportJob,
    setActiveBrandImportJob,
    setBrandImportJobs,
  } = brandLogic;

  const inventoryBrandOptions = useMemo(() => {
    return [['', 'Tất cả thương hiệu'] as [string, string], ...brands.filter((b: any) => {
      if (!inventoryCategoryFilter) return true;
      if (b.categoryIds && (b.categoryIds.includes(inventoryCategoryFilter) || categories.some((c: any) => c.parentId === inventoryCategoryFilter && b.categoryIds.includes(c.id)))) return true;
      return products.some((p: any) => (p.brandId === b.id || p.brand === b.name) && (p.categoryId === inventoryCategoryFilter || p.subcategoryId === inventoryCategoryFilter || categories.some((c: any) => c.parentId === inventoryCategoryFilter && (p.categoryId === c.id || p.subcategoryId === c.id))));
    }).map((b: any) => [String(b.id), b.name] as [string, string])];
  }, [brands, inventoryCategoryFilter, categories, products]);

  const filteredBrands = useMemo(() => {
    return brands.filter((brand) => {
      const ms = matchesSearch(brand, query, ['name', 'code']);
      const mc = !brandCategoryFilter || (brand.categoryIds && (brand.categoryIds.includes(brandCategoryFilter) || categories.some((c: any) => c.parentId === brandCategoryFilter && brand.categoryIds.includes(c.id))));
      return ms && mc;
    });
  }, [brands, query, brandCategoryFilter, categories]);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => matchesSearch(order, query, ['id', 'orderCode', 'userId', 'user_id', 'recipientName', 'recipientPhone', 'paymentMethod', 'payment_method', 'trackingCode', 'status']));
  }, [orders, query]);
  const cancelledOrders = useMemo(() => orders.filter((order) => order.status === 'CANCELLED').length, [orders]);
  const refundedOrders = useMemo(() => orders.filter((order) => order.status === 'REFUNDED' || order.status === 'RETURNED').length, [orders]);
  const filteredVouchers = useMemo(() => {
    return vouchers.filter((voucher) => matchesSearch(voucher, query, ['code', 'discountType', 'status']));
  }, [vouchers, query]);
  const filteredCustomers = useMemo(() => customers, [customers]);
  const filteredInventory = useMemo(() => {
    return products.filter((product) => {
      const ms = matchesSearch(product, query, ['name', 'sku', 'brand', 'categoryName', 'status']);
      const mc = !inventoryCategoryFilter || String(product.categoryId) === inventoryCategoryFilter || String(product.subcategoryId) === inventoryCategoryFilter;
      const mb = !inventoryBrandFilter || String(product.brandId) === inventoryBrandFilter || (product.brand && brands.find(b => String(b.id) === inventoryBrandFilter)?.name === product.brand);
      return ms && mc && mb;
    });
  }, [products, query, inventoryCategoryFilter, inventoryBrandFilter, brands]);
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
  const tabPermissions: Record<AdminTab, string[]> = {
    overview: ['overview:read'],
    products: ['product:read'],
    categories: ['category:read'],
    brands: ['brand:read'],
    services: ['product:read'],
    orders: ['order:read'],
    vouchers: ['voucher:read'],
    customers: ['customer:read'],
    inventory: ['inventory:read'],
    reviews: ['review:read'],
    content: ['content:read'],
    audit: ['audit:read'],
    permissions: ['sys:manage_roles'],
  };
  const availableTabs = useMemo(() => adminTabs.filter((item) => useAnyPermission(tabPermissions[item.id])), [useAnyPermission]);
  const canManageCustomerAccess = usePermission('sys:manage_users');
  const canManageCustomerProfile = useAnyPermission(['customer:update', 'customer:loyalty_adjust', 'customer:issue_voucher', 'sys:manage_users']);
  const permissionLogic = useAdminPermissionsLogic({
    customers,
    canManageCustomerAccess,
    canManageUsers: usePermission('sys:manage_users'),
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const customerLogic = useAdminCustomersLogic({
    canManageCustomerAccess,
    canManageCustomerProfile,
    canAdjustCustomerPoints: usePermission('customer:loyalty_adjust'),
    canIssueCustomerVoucher: usePermission('customer:issue_voucher'),
    canUpdateCustomerProfile: useAnyPermission(['customer:update', 'sys:manage_users']),
    reloadCurrentTab: () => loadData(tab, { force: true }),
  });
  const canCreateContent = usePermission('content:create');
  const canUpdateContent = usePermission('content:update');
  const canDeleteContent = usePermission('content:delete');
  const loadedAdminSectionsRef = useRef<Set<AdminTab>>(new Set());
  const loadedAdminResourcesRef = useRef<Set<string>>(new Set());
  const loadingAdminResourcesRef = useRef<Map<string, Promise<void>>>(new Map());
  const preloadingAdminSectionsRef = useRef(false);

  useEffect(() => {
    if (canAccessAdmin) void loadData(tab);
  }, [canAccessAdmin, tab]);

  useEffect(() => {
    if (!canAccessAdmin || preloadingAdminSectionsRef.current) return;
    preloadingAdminSectionsRef.current = true;
    const preload = () => {
      if (!canAccessAdmin) return;
      void loadData('products', { silent: true, prefetch: true });
    };
    if ('requestIdleCallback' in window) {
      const idleId = window.requestIdleCallback(preload, { timeout: 2500 });
      return () => window.cancelIdleCallback(idleId);
    }
    const timer = globalThis.setTimeout(preload, 1200);
    return () => globalThis.clearTimeout(timer);
  }, [canAccessAdmin]);

  useEffect(() => {
    if (canAccessAdmin && tab === 'categories') {
      void loadCategoryWorkspace(editingCategoryId);
    }
  }, [canAccessAdmin, tab, editingCategoryId]);

  useEffect(() => {
    if (tab !== 'categories' || !editingCategoryId) return;
    if (!categoryMigrationJobs.some((job) => ['PENDING', 'RUNNING', 'IN_PROGRESS'].includes(String(job.status)))) return;
    const timer = window.setInterval(() => {
      void loadCategoryWorkspace(editingCategoryId);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [categoryMigrationJobs, editingCategoryId, tab]);

  useEffect(() => {
    if (canAccessAdmin && tab === 'brands') void loadData('brands', { force: true });
  }, [brandPage, brandStatusFilter, query, tab]);

  useEffect(() => {
    if (tab === 'products') {
      setProductPage(1);
    }
  }, [query, productCategoryFilter, productBrandFilter, productStatusFilter, tab]);

  useEffect(() => {
    console.log("DEBUG: useEffect productCategoryFilter changed:", { productCategoryFilter, productBrandFilter, productStatusFilter });
    if (canAccessAdmin && tab === 'products') {
      void loadData('products', { force: true });
    }
  }, [canAccessAdmin, tab, productPage, query, productCategoryFilter, productBrandFilter, productStatusFilter]);

  useEffect(() => {
    if (tab === 'customers') {
      setCustomerPage(1);
    }
  }, [query]);

  useEffect(() => {
    setBrandPage(1);
  }, [brandStatusFilter, query]);

  useEffect(() => {
    if (!activeBrandImportJob || ['COMPLETED', 'FAILED'].includes(activeBrandImportJob.status)) return;
    const timer = window.setInterval(async () => {
      const nextJob = await apiDb.adminGetBrandImportJob(activeBrandImportJob.id).catch(() => null);
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
      setTab(availableTabs[0]?.id || 'products');
    }
  }, [availableTabs, tab]);

  useEffect(() => {
    if (canAccessAdmin && tab === 'customers') {
      void loadData('customers', { force: true });
    }
  }, [canAccessAdmin, tab, customerPage]);

  async function loadData(targetTab: AdminTab = tab, options: { force?: boolean; silent?: boolean; prefetch?: boolean } = {}) {
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
        const overviewData = await apiDb.adminOverview().catch(() => ({}));
        setOverview(overviewData);
      };
      const loadProducts = async () => {
        const isProductListTab = targetTab === 'products';
        console.log("DEBUG: loadProducts params:", {
          productPage,
          query: query.trim(),
          productStatusFilter,
          productCategoryFilter,
          productBrandFilter
        });
        const productResourceKey = isProductListTab
          ? `products:${productPage}:${query.trim()}:${productStatusFilter}:${productCategoryFilter}:${productBrandFilter}`
          : 'products:all';
        await runResource(productResourceKey, async () => {
          const productData = isProductListTab
            ? await apiDb.adminListProducts({
              page: productPage,
              limit: 20,
              search: query.trim(),
              status: productStatusFilter || undefined,
              categoryId: productCategoryFilter || undefined,
              brandId: productBrandFilter || undefined,
            })
            : await apiDb.adminListProducts().catch(() => apiDb.listProducts());
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
          const categoryData = await apiDb.adminListCategories().catch(() => apiDb.listCategories());
          setCategories(categoryData);
        });
      };
      const loadBrands = async () => {
        const brandResourceKey = targetTab === 'brands'
          ? `brands:${brandPage}:${brandStatusFilter}:${query.trim()}`
          : 'brands:all';
        await runResource(brandResourceKey, async () => {
          const brandData = targetTab === 'brands'
            ? await apiDb.adminListBrands({ page: brandPage, limit: 10, search: query, status: brandStatusFilter }).catch(() => apiDb.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 10 })))
            : await apiDb.adminListBrands({ page: 1, limit: 1000, status: 'all' }).catch(() => apiDb.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 1000 })));
          setBrands(Array.isArray(brandData) ? brandData : brandData.items || []);
          setBrandTotal(Array.isArray(brandData) ? brandData.length : brandData.total || 0);
        });
        if (targetTab === 'brands') {
          await runResource('brand-import-jobs', async () => {
            setBrandImportJobs(await apiDb.adminListBrandImportJobs().catch(() => []));
          });
        }
      };
      const loadServices = async () => {
        await runResource('attached-services', async () => {
          const serviceData = await apiDb.adminListAttachedServices().catch(() => []);
          setAttachedServices(serviceData);
        });
      };
      const loadOrders = async () => {
        const orderData = await apiDb.listOrders().catch(() => []);
        setOrders(orderData);
      };
      const loadVouchers = async () => {
        const voucherData = await apiDb.adminListVouchers().catch(() => []);
        setVouchers(voucherData);
      };
      const loadCustomers = async () => {
        const customerData = await apiDb.adminListCustomers({ search: query, page: customerPage, limit: 20 }).catch(() => ({ items: [], total: 0, page: 1, limit: 20 }));
        setCustomers(Array.isArray(customerData) ? customerData : customerData.items || []);
        setCustomerTotal(Array.isArray(customerData) ? customerData.length : customerData.total || 0);
      };
      const loadReviews = async () => {
        const [reviewData, reviewSummaryData, imageCommentData] = await Promise.all([
          apiDb.adminListReviews().catch(() => []),
          apiDb.adminListReviewSummary().catch(() => []),
          apiDb.adminListImageComments().catch(() => []),
        ]);
        setReviews(reviewData);
        setReviewSummary(reviewSummaryData);
        setImageComments(imageCommentData);
      };
      const loadContent = async () => {
        const contentData = await apiDb.adminListVideos().catch(() => []);
        setContentItems(contentData);
      };
      const loadAudit = async () => {
        const auditData = await apiDb.adminListAuditLogs({ limit: 100 }).catch(() => []);
        setAuditLogs(auditData);
      };
      const loadPermissions = async () => {
        const [permissionData, roleData] = await Promise.all([
          apiDb.adminListPermissions().catch(() => []),
          apiDb.adminListRoles().catch(() => []),
        ]);
        permissionLogic.setPermissions(permissionData);
        permissionLogic.setRoles(roleData);
        const roleEntries = await Promise.all((roleData || []).map(async (role: any) => {
          const detail = await apiDb.adminGetRolePermissions(role.id).catch(() => ({ permissionCodes: [] }));
          return [role.id, detail.permissionCodes || []] as const;
        }));
        permissionLogic.setRolePermissionMap(Object.fromEntries(roleEntries));
      };

      if (options.force) loadedAdminSectionsRef.current.delete(targetTab);
      if (options.force) {
        if (targetTab === 'products' || targetTab === 'inventory') {
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('products:') || key === 'products')
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
        if (targetTab === 'categories') loadedAdminResourcesRef.current.delete('categories');
        if (targetTab === 'services') loadedAdminResourcesRef.current.delete('attached-services');
        if (targetTab === 'brands') {
          [...loadedAdminResourcesRef.current]
            .filter((key) => key.startsWith('brands:') || key === 'brand-import-jobs')
            .forEach((key) => loadedAdminResourcesRef.current.delete(key));
        }
      }
      if (loadedAdminSectionsRef.current.has(targetTab) && !options.force) return;

      if (targetTab === 'overview') {
        await ensureOverview();
      } else if (targetTab === 'products') {
        await Promise.all([loadProducts(), loadCategories(), loadBrands(), loadServices()]);
      } else if (targetTab === 'categories') {
        await loadCategories();
      } else if (targetTab === 'brands') {
        await loadBrands();
      } else if (targetTab === 'services') {
        await loadServices();
      } else if (targetTab === 'orders') {
        await loadOrders();
      } else if (targetTab === 'vouchers') {
        await Promise.all([loadVouchers(), loadProducts(), loadCategories()]);
      } else if (targetTab === 'customers') {
        await Promise.all([loadCustomers(), loadVouchers()]);
      } else if (targetTab === 'inventory') {
        await loadProducts();
      } else if (targetTab === 'reviews') {
        await loadReviews();
      } else if (targetTab === 'content') {
        await Promise.all([loadContent(), loadProducts(), loadCategories(), loadBrands()]);
      } else if (targetTab === 'audit') {
        await loadAudit();
      } else if (targetTab === 'permissions') {
        await Promise.all([loadPermissions(), loadCustomers()]);
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
        const res = await apiDb.adminCreatePresignedUpload({
          folder,
          contentType: file.type,
          size: file.size,
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
    brandStatusFilter,
    setBrandStatusFilter,
    brandPage,
    setBrandPage,
    brandTotal,
    setBrandTotal,
    vouchers,
    setVouchers,
    customers,
    setCustomers,
    customerPage,
    setCustomerPage,
    customerTotal,
    setCustomerTotal,
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
    ...contentLogic,
    auditLogs,
    setAuditLogs,
    ...permissionLogic,
    ...inventoryLogic,
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
    editingCategoryId,
    setEditingCategoryId,
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
    submitProduct,
    approveProduct,
    duplicateProduct,
    bulkApproveProducts,
    exportProducts,
    importProducts,
    archiveProduct,
    reactivateCategory,
    reorderCategory,
    checkCategorySlug,
    ...reviewLogic,
    resetProductForm,
    resetCategoryForm,
    productPayload,
    editProduct,
    editCategory,
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
    canCreateContent,
    canUpdateContent,
    canDeleteContent,
    canAccessAdmin,
    loading,
    usePermission,
    useAnyPermission,
    isSuperAdmin
  };
}
