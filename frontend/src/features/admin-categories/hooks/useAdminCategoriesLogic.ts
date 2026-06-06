import { useState, useMemo, type FormEvent } from 'react';
import { flushSync } from 'react-dom';
import { categoryApi } from '../../../services/categoryApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import {
  type CategoryFilterField,
  type SpecField,
  matchesSearch,
} from '../../admin-shell/components/AdminDashboardConfig';

type UseAdminCategoriesLogicParams = {
  query: string;
  categories: any[];
  setCategories: React.Dispatch<React.SetStateAction<any[]>>;
};

export function useAdminCategoriesLogic({
  query,
  categories,
  setCategories,
}: UseAdminCategoriesLogicParams) {
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    slug: '',
    icon: 'phone',
    iconUrl: '',
    bannerUrl: '',
    parentId: '',
    order: 0,
    isActive: true,
    status: 'ACTIVE',
    specFields: [] as SpecField[],
    filterConfig: [] as CategoryFilterField[],
    inventoryPolicy: { inheritImeiPolicy: true, trackImei: false },
    warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
    version: null as number | null,
  });
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [categorySlugStatus, setCategorySlugStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [categoryMetrics, setCategoryMetrics] = useState<any>({});
  const [categoryAuditLogs, setCategoryAuditLogs] = useState<any[]>([]);
  const [categoryMigrationJobs, setCategoryMigrationJobs] = useState<any[]>([]);
  const [categoryPanelBusy, setCategoryPanelBusy] = useState(false);
  const [categoryCloseSignal, setCategoryCloseSignal] = useState(0);
  const [categoryStatusFilter, setCategoryStatusFilter] = useState('all');

  const rootCategories = useMemo(() => categories.filter((item) => !item.parentId), [categories]);
  const subCategories = useMemo(() => categories.filter((item) => item.parentId), [categories]);
  const editingCategory = useMemo(() => categories.find((item) => item.id === editingCategoryId), [categories, editingCategoryId]);
  const categoryParentMigrationHint = Boolean(editingCategoryId && Number(editingCategory?.productCount || 0) > 0);
  const isEditingChildCategory = Boolean(categoryForm.parentId);

  const filteredCategories = useMemo(() => {
    return categories.filter((category) => {
      const matchesQuery = matchesSearch(category, query, ['name', 'slug', 'parentName', 'icon']);
      const matchesStatus =
        categoryStatusFilter === 'all' ||
        (categoryStatusFilter === 'active' && category.isActive !== false) ||
        (categoryStatusFilter === 'inactive' && category.isActive === false);
      return matchesQuery && matchesStatus;
    });
  }, [categories, query, categoryStatusFilter]);

  const filteredRootCategories = useMemo(() => {
    return rootCategories.filter((category) => {
      const matchesQuery = matchesSearch(category, query, ['name', 'slug', 'icon']);
      const matchesStatus =
        categoryStatusFilter === 'all' ||
        (categoryStatusFilter === 'active' && category.isActive !== false) ||
        (categoryStatusFilter === 'inactive' && category.isActive === false);
      return matchesQuery && matchesStatus;
    });
  }, [rootCategories, query, categoryStatusFilter]);

  const filteredCategoryTree = useMemo(() => {
    const visibleIds = new Set(filteredCategories.map((category) => category.id));
    return rootCategories
      .filter((category) => visibleIds.has(category.id) || subCategories.some((child) => child.parentId === category.id && visibleIds.has(child.id)))
      .map((category) => ({
        ...category,
        children: subCategories.filter((child) => child.parentId === category.id && visibleIds.has(child.id)),
      }));
  }, [filteredCategories, rootCategories, subCategories]);

  const categorySlugTaken = useMemo(() => {
    const slug = categoryForm.slug.trim().toLowerCase();
    if (!slug) return false;
    return categories.some((category) => category.id !== editingCategoryId && String(category.slug || '').toLowerCase() === slug);
  }, [categories, categoryForm.slug, editingCategoryId]);

  const derivedCategoryFilters = useMemo(() => {
    const fromAttributes = categoryForm.specFields
      .filter((field) => field.key && field.isFilterable)
      .map((field) => ({
        key: field.key,
        label: field.label || field.key,
        type: field.filterType || (field.type === 'number' ? 'range' : 'checkbox'),
        enabled: field.filterEnabled !== false,
        source: 'attribute',
      }));
    const manual = categoryForm.filterConfig.filter((field) => field.source !== 'attribute' && !fromAttributes.some((item) => item.key === field.key));
    return [...fromAttributes, ...manual];
  }, [categoryForm.filterConfig, categoryForm.specFields]);

  function resetCategoryForm() {
    setEditingCategoryId(null);
    setCategorySlugStatus('idle');
    setCategoryAuditLogs([]);
    setCategoryMigrationJobs([]);
    setCategoryForm({ name: '', slug: '', icon: 'phone', iconUrl: '', bannerUrl: '', parentId: '', order: 0, isActive: true, status: 'ACTIVE', specFields: [] as SpecField[], filterConfig: [] as CategoryFilterField[], inventoryPolicy: { inheritImeiPolicy: true, trackImei: false }, warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 }, version: null });
    setCategoryCloseSignal((value) => value + 1);
  }

  function isConcurrentUpdateError(error: unknown) {
    const message = error instanceof Error ? error.message : '';
    return message.includes('Reload before saving') || message.includes('updated by another admin') || message.includes('409');
  }

  function categorySubmitErrorMessage(error: unknown): string {
    const fallback = 'Không thể lưu danh mục. Vui lòng kiểm tra dữ liệu và thử lại.';
    if (!(error instanceof Error) || !error.message) return fallback;
    try {
      const parsed = JSON.parse(error.message);
      if (parsed && typeof parsed === 'object') {
        return parsed.message || parsed.detail || fallback;
      }
    } catch {
      // API errors are usually plain Vietnamese messages; keep them as-is.
    }
    return error.message;
  }

  async function handleCategorySubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingCategoryId = editingCategoryId;
    if (categorySlugTaken) {
      window.alert('Slug này đã tồn tại. Vui lòng chọn slug khác.');
      return;
    }
    const payload = {
      ...categoryForm,
      parentId: categoryForm.parentId || null,
      isActive: ['ACTIVE', 'APPROVED'].includes(categoryForm.status),
      specFields: categoryForm.specFields,
      filterConfig: categoryForm.filterConfig.filter((item) => item.source !== 'attribute'),
      version: editingCategoryId ? categoryForm.version : null,
    };
    try {
      if (editingCategoryId) await categoryApi.adminUpdateCategory(editingCategoryId, payload);
      else await categoryApi.adminCreateCategory(payload);
    } catch (error: any) {
      const message = error instanceof Error ? error.message : '';
      if (message.includes('SPEC_TYPE_CHANGE_REQUIRES_CONFIRMATION') || message.includes('Thay đổi kiểu thông số')) {
        if (!window.confirm('Thay đổi kiểu dữ liệu thông số có thể ảnh hưởng dữ liệu sản phẩm hiện tại. Tiếp tục và tạo phiên bản thông số mới?')) return;
        try {
          if (editingCategoryId) await categoryApi.adminUpdateCategory(editingCategoryId, { ...payload, allowSpecTypeMigration: true });
          else await categoryApi.adminCreateCategory({ ...payload, allowSpecTypeMigration: true });
        } catch (retryError) {
          if (isConcurrentUpdateError(retryError)) {
            window.alert('Dữ liệu danh mục đã được cập nhật bởi một người khác. Vui lòng tải lại trang rồi thử lại.');
            await refreshCategoryWorkspace(editingCategoryId);
            return;
          }
          window.alert(`Không thể ${currentEditingCategoryId ? 'lưu thay đổi' : 'thêm danh mục'}:\n${categorySubmitErrorMessage(retryError)}`);
          return;
        }
      } else if (isConcurrentUpdateError(error)) {
        window.alert('Dữ liệu danh mục đã được cập nhật bởi một người khác. Vui lòng tải lại trang rồi thử lại.');
        await refreshCategoryWorkspace(editingCategoryId);
        return;
      } else {
        window.alert(`Không thể ${currentEditingCategoryId ? 'lưu thay đổi' : 'thêm danh mục'}:\n${categorySubmitErrorMessage(error)}`);
        return;
      }
    }
    flushSync(() => {
      setCategoryCloseSignal((value) => value + 1);
    });
    window.setTimeout(resetCategoryForm, 250);
    await refreshCategoryWorkspace();
    notifyAdmin(currentEditingCategoryId ? 'Đã lưu thay đổi danh mục thành công.' : 'Đã thêm danh mục thành công.');
  }

  function editCategory(category: any) {
    setEditingCategoryId(category.id);
    setCategorySlugStatus('idle');
    setCategoryForm({
      name: category.name || '',
      slug: category.slug || '',
      icon: category.icon || 'phone',
      iconUrl: category.iconUrl || '',
      bannerUrl: category.bannerUrl || '',
      parentId: category.parentId || '',
      order: Number(category.order || 0),
      isActive: category.isActive !== false,
      status: category.status || (category.isActive === false ? 'INACTIVE' : 'ACTIVE'),
      specFields: category.ownSpecFields || category.specFields || [],
      filterConfig: category.ownFilterConfig || category.filterConfig || [],
      inventoryPolicy: category.inventoryPolicy || { inheritImeiPolicy: true, trackImei: false },
      warrantyPolicy: category.warrantyPolicy || { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
      version: Number(category.version || 1),
    });
  }

  async function reactivateCategory(category: any) {
    await categoryApi.adminRestoreCategory(category.id);
    await refreshCategoryWorkspace(category.id);
    notifyAdmin('Danh mục đã được khôi phục. Các sản phẩm thuộc danh mục này vẫn đang ở trạng thái ẩn. Vui lòng vào Quản lý sản phẩm để kích hoạt lại nếu cần.', 'info');
  }

  async function hideCategory(category: any) {
    if (!window.confirm(`Ẩn danh mục ${category.name}? Danh mục sẽ không hiển thị ở storefront.`)) return;
    await categoryApi.adminUpdateCategory(category.id, {
      name: category.name || '',
      code: category.code || category.slug,
      slug: category.slug || '',
      icon: category.icon || 'phone',
      iconUrl: category.iconUrl || '',
      bannerUrl: category.bannerUrl || '',
      parentId: category.parentId || null,
      order: Number(category.order || 0),
      isActive: false,
      status: 'INACTIVE',
      specFields: category.ownSpecFields || category.specFields || [],
      filterConfig: category.ownFilterConfig || category.filterConfig || [],
      inventoryPolicy: category.inventoryPolicy || { inheritImeiPolicy: true, trackImei: false },
      warrantyPolicy: category.warrantyPolicy || { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
      version: Number(category.version || 1),
    });
    await refreshCategoryWorkspace(category.id);
    notifyAdmin('Danh mục đã được ẩn.', 'info');
  }

  async function reorderCategory(draggedId: string, targetId: string) {
    if (draggedId === targetId) return;
    const dragged = categories.find((item) => item.id === draggedId);
    const target = categories.find((item) => item.id === targetId);
    if (!dragged || !target || (dragged.parentId || '') !== (target.parentId || '')) return;
    const siblings = categories.filter((item) => (item.parentId || '') === (dragged.parentId || '')).sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
    const nextSiblings = siblings.filter((item) => item.id !== draggedId);
    nextSiblings.splice(nextSiblings.findIndex((item) => item.id === targetId), 0, dragged);
    setCategories((items) => items.map((item) => {
      const index = nextSiblings.findIndex((sibling) => sibling.id === item.id);
      return index >= 0 ? { ...item, order: index + 1 } : item;
    }));
    await categoryApi.adminReorderCategories(nextSiblings.map((item, index) => ({
      id: item.id,
      parentId: item.parentId || null,
      order: index + 1,
    })));
    await refreshCategoryWorkspace(editingCategoryId || draggedId);
  }

  async function checkCategorySlug() {
    const slug = categoryForm.slug.trim();
    if (!slug) return;
    if (categorySlugTaken) {
      setCategorySlugStatus('taken');
      return;
    }
    setCategorySlugStatus('checking');
    try {
      await categoryApi.adminCheckCategorySlug({ slug, excludeId: editingCategoryId });
      setCategorySlugStatus('available');
    } catch {
      setCategorySlugStatus('taken');
    }
  }

  async function loadCategoryWorkspace(categoryId?: string | null) {
    setCategoryPanelBusy(true);
    try {
      const [categoryData, metricsData, auditData, migrationData] = await Promise.all([
        categoryApi.adminListCategories().catch(() => categoryApi.listCategories()),
        categoryApi.adminCategoryMetrics().catch(() => ({})),
        categoryId ? categoryApi.adminCategoryAuditLogs(categoryId).catch(() => []) : Promise.resolve([]),
        categoryId ? categoryApi.adminCategoryMigrationJobs(categoryId).catch(() => []) : Promise.resolve([]),
      ]);
      setCategories(categoryData);
      setCategoryMetrics(metricsData);
      setCategoryAuditLogs(auditData);
      setCategoryMigrationJobs(migrationData);
    } finally {
      setCategoryPanelBusy(false);
    }
  }

  async function refreshCategoryWorkspace(categoryId = editingCategoryId) {
    await loadCategoryWorkspace(categoryId);
  }

  function addSpecField() {
    setCategoryForm((prev) => ({
      ...prev,
      specFields: [...prev.specFields, { key: '', label: '', group: 'Thông số chung', type: 'text', required: false, variant: false, isFilterable: false, filterType: 'checkbox', filterEnabled: true }],
    }));
  }

  function patchSpecField(index: number, patch: Partial<SpecField>) {
    setCategoryForm((prev) => ({ ...prev, specFields: prev.specFields.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  function addCategoryFilter() {
    setCategoryForm((prev) => ({
      ...prev,
      filterConfig: [...prev.filterConfig, { key: '', label: '', type: 'checkbox', enabled: true }],
    }));
  }

  function patchCategoryFilter(index: number, patch: Partial<CategoryFilterField>) {
    setCategoryForm((prev) => ({ ...prev, filterConfig: prev.filterConfig.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  return {
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
  };
}
