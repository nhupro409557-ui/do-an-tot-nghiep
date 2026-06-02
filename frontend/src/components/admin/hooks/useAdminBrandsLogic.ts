import { useState, type FormEvent } from 'react';
import { apiDb } from '../../../services/apiDb';

const initialBrandForm = {
  name: '',
  code: '',
  slug: '',
  logoUrl: '',
  logoAltText: '',
  order: 0,
  isActive: true,
  landingTitle: '',
  seoTitle: '',
  seoDescription: '',
};

type UseAdminBrandsLogicParams = {
  brands: any[];
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminBrandsLogic({ brands, reloadCurrentTab }: UseAdminBrandsLogicParams) {
  const [brandForm, setBrandForm] = useState(initialBrandForm);
  const [brandCodeStatus, setBrandCodeStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [brandImportMode, setBrandImportMode] = useState('skip');
  const [brandImportJobs, setBrandImportJobs] = useState<any[]>([]);
  const [activeBrandImportJob, setActiveBrandImportJob] = useState<any | null>(null);
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>([]);
  const [editingBrandId, setEditingBrandId] = useState<string | null>(null);
  const [brandCloseSignal, setBrandCloseSignal] = useState(0);

  function resetBrandForm() {
    setEditingBrandId(null);
    setBrandCodeStatus('idle');
    setBrandForm(initialBrandForm);
  }

  async function handleBrandSubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingBrandId = editingBrandId;
    const existing = brands.find((item) => item.id === editingBrandId);
    const payload = { ...brandForm, categoryIds: existing?.categoryIds || [] };
    if (payload.code.trim()) {
      const check = await apiDb.adminCheckBrandCode({ code: payload.code.trim(), excludeId: editingBrandId });
      if (!check.available) {
        window.alert('Mã thương hiệu đã tồn tại. Vui lòng chọn mã khác.');
        return;
      }
    }
    if (editingBrandId) await apiDb.adminUpdateBrand(editingBrandId, payload);
    else await apiDb.adminCreateBrand(payload);
    resetBrandForm();
    setBrandCloseSignal((value) => value + 1);
    await reloadCurrentTab();
    window.alert(currentEditingBrandId ? 'Đã lưu thay đổi thương hiệu thành công.' : 'Đã thêm thương hiệu thành công.');
  }

  async function checkBrandCodeOnBlur() {
    const code = brandForm.code.trim();
    if (!code) {
      setBrandCodeStatus('idle');
      return;
    }
    setBrandCodeStatus('checking');
    const result = await apiDb.adminCheckBrandCode({ code, excludeId: editingBrandId });
    setBrandCodeStatus(result.available ? 'available' : 'taken');
  }

  async function handleBrandImportFile(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      window.alert('Vui lòng chọn file CSV.');
      return;
    }
    const result = await apiDb.adminImportBrands(file, brandImportMode);
    setActiveBrandImportJob({ id: result.jobId, status: result.status, progress: 0, totalRows: 0, processedRows: 0, importedRows: 0, updatedRows: 0, skippedRows: 0 });
    await reloadCurrentTab();
    window.alert(`Đã đưa file vào hàng đợi xử lý. Mã lịch sử: ${result.jobId}`);
  }

  function editBrand(brand: any) {
    setEditingBrandId(brand.id);
    setBrandForm({
      name: brand.name || '',
      code: brand.code || '',
      slug: brand.slug || '',
      logoUrl: brand.logoUrl || '',
      logoAltText: brand.logoAltText || '',
      order: Number(brand.order || 0),
      isActive: brand.isActive !== false,
      landingTitle: brand.landingTitle || '',
      seoTitle: brand.seoTitle || '',
      seoDescription: brand.seoDescription || '',
    });
  }

  async function reactivateBrand(brand: any) {
    await apiDb.adminUpdateBrandStatus(brand.id, true);
    await reloadCurrentTab();
  }

  async function hideBrand(brand: any) {
    if (!window.confirm(`Ẩn thương hiệu ${brand.name}? Thương hiệu sẽ không hiển thị ở storefront.`)) return;
    await apiDb.adminUpdateBrandStatus(brand.id, false);
    await reloadCurrentTab();
  }

  async function bulkUpdateBrandStatus(isActive: boolean) {
    if (!selectedBrandIds.length) return;
    if (!window.confirm(`${isActive ? 'Khôi phục' : 'Ẩn'} ${selectedBrandIds.length} thương hiệu đã chọn?`)) return;
    const result = await apiDb.adminUpdateBrandsStatus(selectedBrandIds, isActive);
    setSelectedBrandIds([]);
    await reloadCurrentTab();
    window.alert(`Đã cập nhật ${result.updated} thương hiệu. Lỗi: ${result.failed.length}.`);
  }

  return {
    brandForm,
    setBrandForm,
    brandCodeStatus,
    setBrandCodeStatus,
    brandImportMode,
    setBrandImportMode,
    brandImportJobs,
    setBrandImportJobs,
    activeBrandImportJob,
    setActiveBrandImportJob,
    selectedBrandIds,
    setSelectedBrandIds,
    editingBrandId,
    setEditingBrandId,
    brandCloseSignal,
    setBrandCloseSignal,
    resetBrandForm,
    handleBrandSubmit,
    checkBrandCodeOnBlur,
    handleBrandImportFile,
    editBrand,
    reactivateBrand,
    hideBrand,
    bulkUpdateBrandStatus,
  };
}
