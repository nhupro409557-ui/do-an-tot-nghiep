import { useState, type FormEvent } from 'react';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { adminVouchersApi } from '../services/adminVouchersApi';

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
  displayTitle: '',
  displayDescription: '',
  publicTerms: '',
  applicableChannels: ['WEB'] as string[],
  applicablePaymentMethods: [] as string[],
  eligibleTiers: [] as string[],
  eligibleUserRegisteredAfter: '',
  assignedUserId: '',
  assignedUserIds: [] as string[],
  scopeType: 'ALL',
  includeProductIds: [] as string[],
  excludeProductIds: [] as string[],
  includeCategoryIds: [] as string[],
  excludeCategoryIds: [] as string[],
  includeBrandIds: [] as string[],
  excludeBrandIds: [] as string[],
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

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [];
    } catch {
      return value ? [value] : [];
    }
  }
  return [];
}

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
    setVoucherCloseSignal((value) => value + 1);
  }

  async function handleVoucherSubmit(event: FormEvent) {
    event.preventDefault();

    // 1. Client-side Validation
    if (voucherForm.discountAmount <= 0) {
      notifyAdmin('Giá trị giảm giá phải lớn hơn 0.');
      return;
    }
    if (voucherForm.discountType === 'PERCENT' && voucherForm.discountAmount > 100) {
      notifyAdmin('Giá trị giảm giá theo phần trăm không được lớn hơn 100%.');
      return;
    }
    if (voucherForm.minOrderValue < 0) {
      notifyAdmin('Giá trị đơn tối thiểu không được âm.');
      return;
    }
    if (voucherForm.maxDiscount < 0) {
      notifyAdmin('Giảm giá tối đa không được âm.');
      return;
    }
    if (voucherForm.startsAt && voucherForm.endsAt) {
      const start = new Date(voucherForm.startsAt);
      const end = new Date(voucherForm.endsAt);
      if (start >= end) {
        notifyAdmin('Ngày bắt đầu phải trước ngày kết thúc.');
        return;
      }
    }

    const currentEditingVoucherId = editingVoucherId;
    const payload = {
      ...voucherForm,
      maxDiscount: voucherForm.maxDiscount || null,
      totalBudgetCap: voucherForm.totalBudgetCap || null,
      eligibleUserRegisteredAfter: voucherForm.eligibleUserRegisteredAfter || null,
      assignedUserId: voucherForm.assignedUserId || null,
      includeProductIds: voucherForm.scopeType === 'INCLUDE_SELECTED' ? voucherForm.includeProductIds : [],
      includeCategoryIds: voucherForm.scopeType === 'INCLUDE_SELECTED' ? voucherForm.includeCategoryIds : [],
      includeBrandIds: voucherForm.scopeType === 'INCLUDE_SELECTED' ? voucherForm.includeBrandIds : [],
      startsAt: voucherForm.startsAt || null,
      endsAt: voucherForm.endsAt || null,
      hiddenCode: voucherForm.hiddenCode || voucherForm.audienceType === 'HIDDEN',
      firstOrderOnly: voucherForm.firstOrderOnly || voucherForm.audienceType === 'NEW_CUSTOMER',
      abandonedCartOnly: voucherForm.abandonedCartOnly || voucherForm.audienceType === 'ABANDONED_CART',
    };

    try {
      if (editingVoucherId) {
        await adminVouchersApi.adminUpdateVoucher(editingVoucherId, payload);
      } else {
        await adminVouchersApi.adminCreateVoucher(payload);
      }

      setVoucherCloseSignal((value) => value + 1);
      window.setTimeout(resetVoucherForm, 250);
      await reloadCurrentTab();
      window.setTimeout(() => {
        notifyAdmin(currentEditingVoucherId ? 'Đã lưu thay đổi voucher thành công.' : 'Đã thêm voucher thành công.');
      }, 100);
    } catch (err: any) {
      console.error(err);
      const errorMsg = err?.response?.data?.detail || err?.message || 'Có lỗi xảy ra khi lưu voucher. Vui lòng kiểm tra lại.';
      notifyAdmin(typeof errorMsg === 'object' ? JSON.stringify(errorMsg) : errorMsg);
    }
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
      displayTitle: voucher.displayTitle || '',
      displayDescription: voucher.displayDescription || '',
      publicTerms: voucher.publicTerms || '',
      applicableChannels: asStringArray(voucher.applicableChannels).length ? asStringArray(voucher.applicableChannels) : ['WEB'],
      applicablePaymentMethods: asStringArray(voucher.applicablePaymentMethods),
      eligibleTiers: asStringArray(voucher.eligibleTiers),
      eligibleUserRegisteredAfter: voucher.eligibleUserRegisteredAfter ? String(voucher.eligibleUserRegisteredAfter).slice(0, 16) : '',
      assignedUserId: voucher.assignedUserId || '',
      assignedUserIds: asStringArray(voucher.assignedUserIds).length ? asStringArray(voucher.assignedUserIds) : (voucher.assignedUserId ? [voucher.assignedUserId] : []),
      scopeType: asStringArray(voucher.includeProductIds).length
        || asStringArray(voucher.includeCategoryIds).length
        || asStringArray(voucher.includeBrandIds).length
        ? 'INCLUDE_SELECTED'
        : 'ALL',
      includeProductIds: asStringArray(voucher.includeProductIds),
      excludeProductIds: asStringArray(voucher.excludeProductIds),
      includeCategoryIds: asStringArray(voucher.includeCategoryIds),
      excludeCategoryIds: asStringArray(voucher.excludeCategoryIds),
      includeBrandIds: asStringArray(voucher.includeBrandIds),
      excludeBrandIds: asStringArray(voucher.excludeBrandIds),
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
