import { useState, type FormEvent } from 'react';
import { apiDb } from '../../../services/apiDb';
import { splitIds } from '../AdminDashboardConfig';

const initialVoucherForm = {
  code: '',
  discountType: 'FIXED',
  discountAmount: 100000,
  minOrderValue: 0,
  maxDiscount: 0,
  usageLimit: 100,
  totalBudgetCap: 0,
  perUserLimit: 1,
  perDeviceLimit: 0,
  perIpLimit: 0,
  campaignType: 'CONVERSION',
  audienceType: 'PUBLIC',
  eligibleTiers: [] as string[],
  eligibleUserRegisteredAfter: '',
  assignedUserId: '',
  includeProductIds: '',
  excludeProductIds: '',
  includeCategoryIds: '',
  excludeCategoryIds: '',
  firstOrderOnly: false,
  hiddenCode: false,
  abandonedCartOnly: false,
  validityDaysAfterClaim: 0,
  stackable: false,
  refundPolicy: 'SHOP_FAULT_ONLY',
  startsAt: '',
  endsAt: '',
  internalNote: '',
  status: 'ACTIVE',
};

type UseAdminVouchersLogicParams = {
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminVouchersLogic({ reloadCurrentTab }: UseAdminVouchersLogicParams) {
  const [voucherForm, setVoucherForm] = useState(initialVoucherForm);
  const [editingVoucherId, setEditingVoucherId] = useState<string | null>(null);
  const [voucherCloseSignal, setVoucherCloseSignal] = useState(0);

  function resetVoucherForm() {
    setEditingVoucherId(null);
    setVoucherForm(initialVoucherForm);
  }

  async function handleVoucherSubmit(event: FormEvent) {
    event.preventDefault();
    const currentEditingVoucherId = editingVoucherId;
    const payload = {
      ...voucherForm,
      maxDiscount: voucherForm.maxDiscount || null,
      totalBudgetCap: voucherForm.totalBudgetCap || null,
      eligibleUserRegisteredAfter: voucherForm.eligibleUserRegisteredAfter || null,
      assignedUserId: voucherForm.assignedUserId || null,
      includeProductIds: splitIds(voucherForm.includeProductIds),
      excludeProductIds: splitIds(voucherForm.excludeProductIds),
      includeCategoryIds: splitIds(voucherForm.includeCategoryIds),
      excludeCategoryIds: splitIds(voucherForm.excludeCategoryIds),
      startsAt: voucherForm.startsAt || null,
      endsAt: voucherForm.endsAt || null,
      hiddenCode: voucherForm.hiddenCode || voucherForm.audienceType === 'HIDDEN',
      firstOrderOnly: voucherForm.firstOrderOnly || voucherForm.audienceType === 'NEW_CUSTOMER',
      abandonedCartOnly: voucherForm.abandonedCartOnly || voucherForm.audienceType === 'ABANDONED_CART',
    };
    if (editingVoucherId) await apiDb.adminUpdateVoucher(editingVoucherId, payload);
    else await apiDb.adminCreateVoucher(payload);
    resetVoucherForm();
    setVoucherCloseSignal((value) => value + 1);
    await reloadCurrentTab();
    window.alert(currentEditingVoucherId ? 'Đã lưu thay đổi voucher thành công.' : 'Đã thêm voucher thành công.');
  }

  function editVoucher(voucher: any) {
    setEditingVoucherId(voucher.id);
    setVoucherForm({
      code: voucher.code || '',
      discountType: voucher.discountType || 'FIXED',
      discountAmount: Number(voucher.discountAmount || 0),
      minOrderValue: Number(voucher.minOrderValue || 0),
      maxDiscount: Number(voucher.maxDiscount || 0),
      usageLimit: Number(voucher.usageLimit || 0),
      totalBudgetCap: Number(voucher.totalBudgetCap || 0),
      perUserLimit: Number(voucher.perUserLimit || 0),
      perDeviceLimit: Number(voucher.perDeviceLimit || 0),
      perIpLimit: Number(voucher.perIpLimit || 0),
      campaignType: voucher.campaignType || 'CONVERSION',
      audienceType: voucher.audienceType || 'PUBLIC',
      eligibleTiers: Array.isArray(voucher.eligibleTiers) ? voucher.eligibleTiers : [],
      eligibleUserRegisteredAfter: voucher.eligibleUserRegisteredAfter ? String(voucher.eligibleUserRegisteredAfter).slice(0, 16) : '',
      assignedUserId: voucher.assignedUserId || '',
      includeProductIds: Array.isArray(voucher.includeProductIds) ? voucher.includeProductIds.join(', ') : '',
      excludeProductIds: Array.isArray(voucher.excludeProductIds) ? voucher.excludeProductIds.join(', ') : '',
      includeCategoryIds: Array.isArray(voucher.includeCategoryIds) ? voucher.includeCategoryIds.join(', ') : '',
      excludeCategoryIds: Array.isArray(voucher.excludeCategoryIds) ? voucher.excludeCategoryIds.join(', ') : '',
      firstOrderOnly: Boolean(voucher.firstOrderOnly),
      hiddenCode: Boolean(voucher.hiddenCode),
      abandonedCartOnly: Boolean(voucher.abandonedCartOnly),
      validityDaysAfterClaim: Number(voucher.validityDaysAfterClaim || 0),
      stackable: Boolean(voucher.stackable),
      refundPolicy: voucher.refundPolicy || 'SHOP_FAULT_ONLY',
      startsAt: voucher.startsAt ? String(voucher.startsAt).slice(0, 16) : '',
      endsAt: voucher.endsAt ? String(voucher.endsAt).slice(0, 16) : '',
      internalNote: voucher.internalNote || '',
      status: voucher.status || 'ACTIVE',
    });
  }

  return {
    voucherForm,
    setVoucherForm,
    editingVoucherId,
    setEditingVoucherId,
    voucherCloseSignal,
    setVoucherCloseSignal,
    resetVoucherForm,
    handleVoucherSubmit,
    editVoucher,
  };
}
