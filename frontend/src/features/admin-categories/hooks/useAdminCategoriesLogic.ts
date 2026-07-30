import { useEffect, useState, useMemo, type FormEvent } from 'react';
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

const defaultInventoryPolicy = {
  inheritImeiPolicy: true,
  trackImei: false,
  inheritSerialPolicy: true,
  trackSerialNumber: false,
  inheritStorageDimensions: true,
  packageLengthCm: 16,
  packageWidthCm: 9,
  packageHeightCm: 6,
  packingRatio: 0.75,
};

const defaultSpecFieldUnits: Record<string, string> = {
  ram: 'GB',
  rom: 'GB/TB',
  storage: 'GB/TB',
  screen_size: 'inch',
  refresh_rate: 'Hz',
  brightness: 'nits',
  rear_camera: 'MP',
  front_camera: 'MP',
  battery: 'mAh',
  charging: 'W',
  power: 'W',
  capacity: 'mAh',
  dimensions: 'mm',
  weight: 'g',
  case_size: 'mm',
  zoom: 'x',
  field_of_view: 'độ',
};

const defaultSpecFieldOptions: Record<string, string> = {
  ram: '4, 6, 8, 12, 16',
  rom: '64 GB, 128 GB, 256 GB, 512 GB, 1 TB',
  storage: '64 GB, 128 GB, 256 GB, 512 GB, 1 TB',
  screen_size: '6.1, 6.3, 6.5, 6.7, 6.8, 6.9',
  refresh_rate: '60, 90, 120, 144',
  brightness: '1000, 1600, 2000, 2600, 3000',
  rear_camera: '12, 32, 48, 50, 64, 108, 200',
  front_camera: '8, 12, 16, 32, 50',
  battery: '4000, 4500, 5000, 5500, 6000',
  charging: '20, 25, 33, 45, 67, 80, 90, 120',
  power: '15, 20, 25, 30, 45, 65, 100, 140, 200, 240',
  capacity: '5000, 10000, 20000, 27650',
  dimensions: '150 x 72 x 8, 160 x 75 x 8, 163 x 78 x 9',
  weight: '150, 180, 200, 220, 240',
  case_size: '40, 41, 43, 44, 45, 49',
  zoom: '2, 3, 5, 10, 20, 30',
  field_of_view: '90, 120, 130, 155, 170',
};

const categorySpecUnitOverrides: Record<string, Record<string, string>> = {
  laptops: {
    storage: 'GB/TB',
    battery: 'Wh',
    weight: 'kg',
  },
  cameras: {
    resolution: 'MP',
    storage: 'GB/TB',
  },
};

const categorySpecOptionOverrides: Record<string, Record<string, string>> = {
  laptops: {
    screen_size: '13.3, 14, 15.6, 16, 17.3',
    refresh_rate: '60, 90, 120, 144, 165, 240',
    ram: '8, 16, 24, 32, 64',
    storage: '256GB SSD, 512GB SSD, 1TB SSD, 2TB SSD',
    battery: '40, 50, 60, 70, 80, 100',
    dimensions: '304 x 215 x 16, 356 x 250 x 20',
    weight: '1.2, 1.4, 1.6, 2.0, 2.5',
  },
  tablets: {
    screen_size: '8.7, 10.9, 11, 12.4, 12.9, 13',
    storage: '64 GB, 128 GB, 256 GB, 512 GB, 1 TB, 2 TB',
    battery: '5000, 7040, 8000, 10000, 11200',
    weight: '450, 500, 600, 700',
  },
  wearables: {
    screen_size: '1.2, 1.3, 1.4, 1.5, 1.9',
    storage: '8, 16, 32, 64',
    weight: '30, 40, 50, 60, 70',
  },
  cameras: {
    resolution: '2, 3, 4, 12, 20, 24, 33, 45',
    storage: 'microSD 32GB, microSD 64GB, microSD 128GB, SD 64GB, SD 128GB',
    battery: '1000, 1720, 1800, 2200, 3000',
    dimensions: '60 x 40 x 30, 100 x 70 x 60, 130 x 100 x 80',
    weight: '150, 250, 500, 700',
  },
  accessories: {
    dimensions: 'Dài 1m, Dài 1.2m, Dài 1.8m, Dài 2m, Nhỏ gọn',
    weight: '50, 100, 200, 300, 500',
  },
};

function defaultSpecFieldUnit(field: Partial<SpecField>, categorySlug?: string) {
  const key = String(field.key || '').trim().toLowerCase();
  if (!key) return '';
  const slug = String(categorySlug || '').trim().toLowerCase();
  return categorySpecUnitOverrides[slug]?.[key] || defaultSpecFieldUnits[key] || '';
}

function defaultSpecFieldOptionsFor(field: Partial<SpecField>, categorySlug?: string) {
  const key = String(field.key || '').trim().toLowerCase();
  if (!key) return '';
  const slug = String(categorySlug || '').trim().toLowerCase();
  return categorySpecOptionOverrides[slug]?.[key] || defaultSpecFieldOptions[key] || '';
}

function withDefaultSpecFieldConfig(fields: SpecField[] = [], categorySlug?: string) {
  let changed = false;
  const specFields = fields.map((field) => {
    const patch: Partial<SpecField> = {};
    if (!String(field.unit || '').trim()) {
      const unit = defaultSpecFieldUnit(field, categorySlug);
      if (unit) patch.unit = unit;
    }
    if (!String(field.options || '').trim()) {
      const options = defaultSpecFieldOptionsFor(field, categorySlug);
      if (options) patch.options = options;
    }
    if (!Object.keys(patch).length) return field;
    changed = true;
    return { ...field, ...patch };
  });
  return changed ? specFields : fields;
}

function duplicateSpecFieldKey(fields: SpecField[] = []) {
  const seen = new Set<string>();
  for (const field of fields) {
    const key = String(field.key || '').trim();
    if (!key) continue;
    const normalizedKey = key.toLowerCase();
    if (seen.has(normalizedKey)) return key;
    seen.add(normalizedKey);
  }
  return '';
}

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
    inventoryPolicy: defaultInventoryPolicy,
    warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
    version: null as number | null,
  });
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [categoryViewOnly, setCategoryViewOnly] = useState(false);
  const [categorySlugStatus, setCategorySlugStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [categoryMetrics, setCategoryMetrics] = useState<any>({});
  const [categoryAuditLogs, setCategoryAuditLogs] = useState<any[]>([]);
  const [categoryMigrationJobs, setCategoryMigrationJobs] = useState<any[]>([]);
  const [identifierPolicyMigrations, setIdentifierPolicyMigrations] = useState<any[]>([]);
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

  useEffect(() => {
    if (!editingCategoryId) return;
    setCategoryForm((prev) => {
      const specFields = withDefaultSpecFieldConfig(prev.specFields, editingCategory?.slug || prev.slug);
      return specFields === prev.specFields ? prev : { ...prev, specFields };
    });
  }, [editingCategoryId, editingCategory?.slug]);

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
    setCategoryViewOnly(false);
    setCategorySlugStatus('idle');
    setCategoryAuditLogs([]);
    setCategoryMigrationJobs([]);
    setIdentifierPolicyMigrations([]);
    setCategoryForm({ name: '', slug: '', icon: 'phone', iconUrl: '', bannerUrl: '', parentId: '', order: 0, isActive: true, status: 'ACTIVE', specFields: [] as SpecField[], filterConfig: [] as CategoryFilterField[], inventoryPolicy: defaultInventoryPolicy, warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 }, version: null });
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
    const duplicatedSpecKey = duplicateSpecFieldKey(categoryForm.specFields);
    if (duplicatedSpecKey) {
      window.alert(`Mã trường thông số '${duplicatedSpecKey}' bị trùng. Vui lòng giữ mỗi key một lần.`);
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
      if (message.includes('IDENTIFIER_POLICY_MIGRATION_REQUIRED') && editingCategoryId) {
        let detail: any = null;
        try {
          detail = JSON.parse(message);
        } catch {
          detail = null;
        }
        const previews = Array.isArray(detail?.previews) ? detail.previews : [];
        const summary = previews
          .map((item: any) => `${item.identifierType}: ${item.requiredIdentifiers} mã cho ${item.affectedProducts} sản phẩm`)
          .join('\n');
        if (!window.confirm(`Tồn kho cũ cần được bổ sung mã trước khi bật chính sách:\n${summary}\n\nTạo tác vụ bổ sung ngay?`)) return;
        try {
          for (const preview of previews) {
            await categoryApi.adminCreateIdentifierPolicyMigration(editingCategoryId, {
              identifierType: preview.identifierType,
              targetInventoryPolicy: detail.targetInventoryPolicy || payload.inventoryPolicy,
            });
          }
          await refreshCategoryWorkspace(editingCategoryId);
          notifyAdmin('Đã tạo tác vụ bổ sung IMEI/Serial. Chính sách sẽ được bật sau khi quét đủ mã.', 'info');
        } catch (migrationError) {
          window.alert(`Không thể tạo tác vụ bổ sung mã:\n${categorySubmitErrorMessage(migrationError)}`);
        }
        return;
      } else if (message.includes('SPEC_TYPE_CHANGE_REQUIRES_CONFIRMATION') || message.includes('Thay đổi kiểu thông số')) {
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
    setCategoryViewOnly(false);
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
      specFields: withDefaultSpecFieldConfig(category.ownSpecFields || category.specFields || [], category.slug),
      filterConfig: category.ownFilterConfig || category.filterConfig || [],
      inventoryPolicy: { ...defaultInventoryPolicy, ...(category.inventoryPolicy || {}) },
      warrantyPolicy: category.warrantyPolicy || { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
      version: Number(category.version || 1),
    });
  }

  function viewCategory(category: any) {
    editCategory(category);
    setCategoryViewOnly(true);
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
      specFields: withDefaultSpecFieldConfig(category.ownSpecFields || category.specFields || [], category.slug),
      filterConfig: category.ownFilterConfig || category.filterConfig || [],
      inventoryPolicy: { ...defaultInventoryPolicy, ...(category.inventoryPolicy || {}) },
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
      const [categoryData, metricsData, auditData, migrationData, identifierMigrationData] = await Promise.all([
        categoryApi.adminListCategories().catch(() => categoryApi.listCategories()),
        categoryApi.adminCategoryMetrics().catch(() => ({})),
        categoryId ? categoryApi.adminCategoryAuditLogs(categoryId).catch(() => []) : Promise.resolve([]),
        categoryId ? categoryApi.adminCategoryMigrationJobs(categoryId).catch(() => []) : Promise.resolve([]),
        categoryId ? categoryApi.adminIdentifierPolicyMigrations(categoryId).catch(() => []) : Promise.resolve([]),
      ]);
      setCategories(categoryData);
      setCategoryMetrics(metricsData);
      setCategoryAuditLogs(auditData);
      setCategoryMigrationJobs(migrationData);
      setIdentifierPolicyMigrations(identifierMigrationData);
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
      specFields: [...prev.specFields, { key: '', label: '', group: 'Thông số chung', type: 'text', required: false, variant: false, isFilterable: false, filterType: 'checkbox', filterEnabled: true, unit: '', options: '' }],
    }));
  }

  function patchSpecField(index: number, patch: Partial<SpecField>) {
    setCategoryForm((prev) => ({
      ...prev,
      specFields: prev.specFields.map((item, i) => {
        if (i !== index) return item;
        const next = { ...item, ...patch };
        if ('key' in patch) {
          const defaultPatch: Partial<SpecField> = {};
          const unit = defaultSpecFieldUnit(next, editingCategory?.slug || prev.slug);
          const options = defaultSpecFieldOptionsFor(next, editingCategory?.slug || prev.slug);
          if (!String(next.unit || '').trim() && unit) defaultPatch.unit = unit;
          if (!String(next.options || '').trim() && options) defaultPatch.options = options;
          return Object.keys(defaultPatch).length ? { ...next, ...defaultPatch } : next;
        }
        return next;
      }),
    }));
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

  async function scanIdentifierPolicyMigration(migrationId: string, lineId: string, identifiers: string[]) {
    await categoryApi.adminScanIdentifierPolicyMigration(migrationId, { lineId, identifiers });
    await refreshCategoryWorkspace(editingCategoryId);
  }

  async function completeIdentifierPolicyMigration(migrationId: string) {
    await categoryApi.adminCompleteIdentifierPolicyMigration(migrationId);
    await refreshCategoryWorkspace(editingCategoryId);
    notifyAdmin('Đã hoàn tất bổ sung mã và kích hoạt chính sách danh mục.');
  }

  async function cancelIdentifierPolicyMigration(migrationId: string) {
    const reason = window.prompt('Nhập lý do hủy tác vụ bổ sung mã:')?.trim();
    if (!reason) return;
    await categoryApi.adminCancelIdentifierPolicyMigration(migrationId, reason);
    await refreshCategoryWorkspace(editingCategoryId);
    notifyAdmin('Đã hủy tác vụ bổ sung mã.', 'info');
  }

  return {
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
    identifierPolicyMigrations,
    setIdentifierPolicyMigrations,
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
    scanIdentifierPolicyMigration,
    completeIdentifierPolicyMigration,
    cancelIdentifierPolicyMigration,
  };
}
