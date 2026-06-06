import { useState, type FormEvent } from 'react';
import { adminServicesApi } from '../services/adminServicesApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';

export type ServiceForm = {
  code: string;
  name: string;
  serviceType: string;
  attributeGroup: string;
  durationMonths: number;
  priceMode: string;
  fixedPrice: number;
  percentValue: number;
  baseAmount: number;
  isActive: boolean;
};

const initialServiceForm: ServiceForm = {
  code: '',
  name: '',
  serviceType: 'SUPPORT_SERVICE',
  attributeGroup: '',
  durationMonths: 0,
  priceMode: 'FIXED',
  fixedPrice: 0,
  percentValue: 0,
  baseAmount: 0,
  isActive: true,
};

type UseAdminServicesLogicParams = {
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminServicesLogic({ reloadCurrentTab }: UseAdminServicesLogicParams) {
  const [serviceForm, setServiceForm] = useState<ServiceForm>(initialServiceForm);
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [serviceFormOpen, setServiceFormOpen] = useState(false);

  function editService(service: any) {
    setEditingServiceId(service.id);
    setServiceFormOpen(true);
    setServiceForm({
      code: service.code || '',
      name: service.name || '',
      serviceType: service.serviceType || 'SUPPORT_SERVICE',
      attributeGroup: service.attributeGroup || '',
      durationMonths: Number(service.durationMonths || 0),
      priceMode: service.serviceType === 'PRODUCT_SERVICE' ? 'TIERED_AMOUNT' : service.priceMode || 'FIXED',
      fixedPrice: Number(service.fixedPrice || 0),
      percentValue: Number(service.percentValue || 0),
      baseAmount: Number(service.baseAmount || 0),
      isActive: service.isActive !== false,
    });
  }

  function resetServiceForm() {
    setEditingServiceId(null);
    setServiceFormOpen(false);
    setServiceForm(initialServiceForm);
  }

  async function handleServiceSubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingServiceId = editingServiceId;
    const payload = serviceForm.serviceType === 'PRODUCT_SERVICE'
      ? { ...serviceForm, priceMode: 'TIERED_AMOUNT', fixedPrice: 0, percentValue: 0, baseAmount: 0 }
      : serviceForm;
    try {
      if (editingServiceId) await adminServicesApi.adminUpdateAttachedService(editingServiceId, payload);
      else await adminServicesApi.adminCreateAttachedService(payload);
      setServiceFormOpen(false);
      window.setTimeout(() => {
        setEditingServiceId(null);
        setServiceForm(initialServiceForm);
      }, 250);
      await reloadCurrentTab();
      window.setTimeout(() => {
        notifyAdmin(currentEditingServiceId ? 'Đã lưu thay đổi dịch vụ thành công.' : 'Đã thêm dịch vụ thành công.');
      }, 100);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể lưu dịch vụ. Vui lòng thử lại.');
    }
  }

  return {
    serviceForm,
    setServiceForm,
    editingServiceId,
    setEditingServiceId,
    serviceFormOpen,
    setServiceFormOpen,
    editService,
    resetServiceForm,
    handleServiceSubmit,
  };
}
