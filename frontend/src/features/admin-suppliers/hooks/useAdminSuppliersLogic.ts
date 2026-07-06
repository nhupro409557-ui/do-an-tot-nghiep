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
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  function resetSupplierForm() {
    setEditingSupplierId(null);
    setSupplierViewOnly(false);
    setSupplierCodeStatus('idle');
    setSupplierForm(initialSupplierForm);
    setFormErrors({});
  }

  async function handleSupplierSubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingSupplierId = editingSupplierId;
    const payload = {
      ...supplierForm,
      code: supplierForm.code.trim(),
      name: supplierForm.name.trim(),
      phone: supplierForm.phone ? supplierForm.phone.replace(/[\s.-]/g, '').trim() : '',
      email: supplierForm.email ? supplierForm.email.trim() : '',
    };

    // Front-end Validation
    const errors: Record<string, string> = {};
    if (!payload.name) {
      errors.name = 'Tên nhà cung cấp là bắt buộc.';
    } else if (payload.name.length < 2 || payload.name.length > 200) {
      errors.name = 'Tên nhà cung cấp phải từ 2 đến 200 ký tự.';
    }

    if (!payload.code) {
      errors.code = 'Mã nhà cung cấp là bắt buộc.';
    }

    if (payload.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(payload.email)) {
        errors.email = 'Email không hợp lệ.';
      }
    }

    if (payload.phone) {
      const phoneRegex = /^(0|\+84)(3|5|7|8|9)\d{8}$/;
      if (!phoneRegex.test(payload.phone)) {
        errors.phone = 'Số điện thoại không hợp lệ.';
      }
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setFormErrors({});

    try {
      const check = await adminSuppliersApi.adminCheckSupplierCode({ code: payload.code, excludeId: editingSupplierId });
      if (!check.available) {
        setSupplierCodeStatus('taken');
        setFormErrors({ code: 'Mã nhà cung cấp đã tồn tại. Vui lòng chọn mã khác.' });
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
    formErrors,
  };
}
