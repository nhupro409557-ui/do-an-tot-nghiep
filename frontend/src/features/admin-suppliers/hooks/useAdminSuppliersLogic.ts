import { useState, type FormEvent } from 'react';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { adminSuppliersApi } from '../services/adminSuppliersApi';

const initialSupplierForm = {
  name: '',
  code: '',
  contactName: '',
  phone: '',
  email: '',
  address: '',
  taxCode: '',
  website: '',
  note: '',
  isActive: true,
};

type UseAdminSuppliersLogicParams = {
  suppliers: any[];
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminSuppliersLogic({ suppliers, reloadCurrentTab }: UseAdminSuppliersLogicParams) {
  const [supplierForm, setSupplierForm] = useState(initialSupplierForm);
  const [supplierCodeStatus, setSupplierCodeStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<string[]>([]);
  const [editingSupplierId, setEditingSupplierId] = useState<string | null>(null);
  const [supplierViewOnly, setSupplierViewOnly] = useState(false);
  const [supplierFormOpen, setSupplierFormOpen] = useState(false);

  function resetSupplierForm() {
    setEditingSupplierId(null);
    setSupplierViewOnly(false);
    setSupplierCodeStatus('idle');
    setSupplierForm(initialSupplierForm);
  }

  async function handleSupplierSubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingSupplierId = editingSupplierId;
    const payload = { ...supplierForm, code: supplierForm.code.trim(), name: supplierForm.name.trim() };
    try {
      const check = await adminSuppliersApi.adminCheckSupplierCode({ code: payload.code, excludeId: editingSupplierId });
      if (!check.available) {
        window.alert('Mã nhà cung cấp đã tồn tại. Vui lòng chọn mã khác.');
        return;
      }
      if (editingSupplierId) await adminSuppliersApi.adminUpdateSupplier(editingSupplierId, payload);
      else await adminSuppliersApi.adminCreateSupplier(payload);
      setSupplierFormOpen(false);
      resetSupplierForm();
      await reloadCurrentTab();
      notifyAdmin(currentEditingSupplierId ? 'Đã lưu thay đổi nhà cung cấp.' : 'Đã thêm nhà cung cấp mới.');
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể lưu nhà cung cấp. Vui lòng thử lại.');
    }
  }

  async function checkSupplierCodeOnBlur() {
    const code = supplierForm.code.trim();
    if (!code) {
      setSupplierCodeStatus('idle');
      return;
    }
    setSupplierCodeStatus('checking');
    try {
      const result = await adminSuppliersApi.adminCheckSupplierCode({ code, excludeId: editingSupplierId });
      setSupplierCodeStatus(result.available ? 'available' : 'taken');
    } catch {
      setSupplierCodeStatus('idle');
    }
  }

  function editSupplier(supplier: any) {
    setSupplierViewOnly(false);
    setEditingSupplierId(supplier.id);
    setSupplierForm({
      name: supplier.name || '',
      code: supplier.code || '',
      contactName: supplier.contactName || '',
      phone: supplier.phone || '',
      email: supplier.email || '',
      address: supplier.address || '',
      taxCode: supplier.taxCode || '',
      website: supplier.website || '',
      note: supplier.note || '',
      isActive: supplier.isActive !== false,
    });
    setSupplierFormOpen(true);
  }

  function viewSupplier(supplier: any) {
    editSupplier(supplier);
    setSupplierViewOnly(true);
  }

  async function reactivateSupplier(supplier: any) {
    await adminSuppliersApi.adminUpdateSupplierStatus(supplier.id, true);
    await reloadCurrentTab();
  }

  async function hideSupplier(supplier: any) {
    if (!window.confirm(`Ẩn nhà cung cấp ${supplier.name}?`)) return;
    await adminSuppliersApi.adminUpdateSupplierStatus(supplier.id, false);
    await reloadCurrentTab();
  }

  async function deleteSupplier(supplier: any) {
    if (!window.confirm(`Xóa nhà cung cấp ${supplier.name}? Thao tác này không thể hoàn tác.`)) return;
    await adminSuppliersApi.adminDeleteSupplier(supplier.id);
    await reloadCurrentTab();
  }

  async function bulkUpdateSupplierStatus(isActive: boolean) {
    if (!selectedSupplierIds.length) return;
    if (!window.confirm(`${isActive ? 'Khôi phục' : 'Ẩn'} ${selectedSupplierIds.length} nhà cung cấp đã chọn?`)) return;
    const result = await adminSuppliersApi.adminUpdateSuppliersStatus(selectedSupplierIds, isActive);
    setSelectedSupplierIds([]);
    await reloadCurrentTab();
    notifyAdmin(`Đã cập nhật ${result.updated} nhà cung cấp. Lỗi: ${result.failed.length}.`, result.failed.length ? 'info' : 'success');
  }

  return {
    supplierForm,
    setSupplierForm,
    supplierCodeStatus,
    setSupplierCodeStatus,
    selectedSupplierIds,
    setSelectedSupplierIds,
    editingSupplierId,
    supplierViewOnly,
    setSupplierViewOnly,
    setEditingSupplierId,
    supplierFormOpen,
    setSupplierFormOpen,
    resetSupplierForm,
    handleSupplierSubmit,
    checkSupplierCodeOnBlur,
    editSupplier,
    viewSupplier,
    reactivateSupplier,
    hideSupplier,
    deleteSupplier,
    bulkUpdateSupplierStatus,
  };
}
