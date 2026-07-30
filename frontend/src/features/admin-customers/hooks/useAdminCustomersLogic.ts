import { useState } from 'react';
import { adminCustomersApi } from '../services/adminCustomersApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';

type CustomerSection = 'summary' | 'orders' | 'loyalty' | 'notes' | 'audit' | 'vouchers';

type UseAdminCustomersLogicParams = {
  canManageCustomerAccess: boolean;
  canManageCustomerProfile: boolean;
  canAdjustCustomerPoints: boolean;
  canIssueCustomerVoucher: boolean;
  canUpdateCustomerProfile: boolean;
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminCustomersLogic({
  canManageCustomerAccess,
  canManageCustomerProfile,
  canAdjustCustomerPoints,
  canIssueCustomerVoucher,
  canUpdateCustomerProfile,
  reloadCurrentTab,
}: UseAdminCustomersLogicParams) {
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [customerDetailOpen, setCustomerDetailOpen] = useState(false);
  const [customerDetailBusy, setCustomerDetailBusy] = useState(false);
  const [customerDetailError, setCustomerDetailError] = useState('');
  const [customerActiveSection, setCustomerActiveSection] = useState<CustomerSection>('summary');
  const [customerOrders, setCustomerOrders] = useState<any[]>([]);
  const [customerLoyaltyHistory, setCustomerLoyaltyHistory] = useState<any[]>([]);
  const [customerLoyaltyPage, setCustomerLoyaltyPage] = useState(1);
  const [customerLoyaltyTotal, setCustomerLoyaltyTotal] = useState(0);
  const [customerNotes, setCustomerNotes] = useState<any[]>([]);
  const [customerAuditLogs, setCustomerAuditLogs] = useState<any[]>([]);
  const [customerTagDraft, setCustomerTagDraft] = useState('');
  const [customerProfileDraft, setCustomerProfileDraft] = useState({ fullName: '', phone: '', tier: 'MEMBER', walletStatus: 'ACTIVE' });
  const [customerNoteDraft, setCustomerNoteDraft] = useState('');
  const [customerVoucherId, setCustomerVoucherId] = useState('');
  const [customerVoucherNote, setCustomerVoucherNote] = useState('');
  const [customerPointDelta, setCustomerPointDelta] = useState('0');
  const [customerPointReason, setCustomerPointReason] = useState('');

  async function openCustomerDetail(customer: any) {
    setCustomerDetailOpen(true);
    setCustomerDetailBusy(true);
    setCustomerDetailError('');
    setSelectedCustomer(null);
    setCustomerActiveSection('summary');
    try {
      const detail = await adminCustomersApi.adminGetCustomerOverview(customer.id);
      setSelectedCustomer(detail);
      setCustomerOrders([]);
      setCustomerLoyaltyHistory([]);
      setCustomerLoyaltyPage(1);
      setCustomerLoyaltyTotal(0);
      setCustomerNotes([]);
      setCustomerAuditLogs([]);
      setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
      setCustomerProfileDraft({
        fullName: detail.fullName || '',
        phone: detail.phone || '',
        tier: detail.tier || 'MEMBER',
        walletStatus: detail.walletStatus || 'ACTIVE',
      });
      setCustomerVoucherId('');
      setCustomerVoucherNote('');
      setCustomerPointDelta('0');
      setCustomerPointReason('');
      setCustomerNoteDraft('');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể tải thông tin khách hàng.');
    } finally {
      setCustomerDetailBusy(false);
    }
  }

  async function refreshSelectedCustomer() {
    if (!selectedCustomer?.id) return;
    const detail = await adminCustomersApi.adminGetCustomerOverview(selectedCustomer.id);
    setSelectedCustomer(detail);
    setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
    setCustomerProfileDraft({
      fullName: detail.fullName || '',
      phone: detail.phone || '',
      tier: detail.tier || 'MEMBER',
      walletStatus: detail.walletStatus || 'ACTIVE',
    });
    await reloadCurrentTab();
  }

  async function loadCustomerSection(section: CustomerSection) {
    if (!selectedCustomer?.id) return;
    if (section === customerActiveSection) return;
    setCustomerActiveSection(section);
    if (section === 'orders') {
      setCustomerOrders(await adminCustomersApi.adminGetCustomerOrders(selectedCustomer.id).catch(() => []));
    }
    if (section === 'loyalty') {
      await loadCustomerLoyaltyPage(1);
    }
    if (section === 'notes') {
      setCustomerNotes(await adminCustomersApi.adminGetCustomerNotes(selectedCustomer.id).catch(() => []));
    }
    if (section === 'audit') {
      setCustomerAuditLogs(await adminCustomersApi.adminGetCustomerAuditLogs(selectedCustomer.id).catch(() => []));
    }
  }

  async function loadCustomerLoyaltyPage(page: number) {
    if (!selectedCustomer?.id) return;
    const result = await adminCustomersApi.adminGetCustomerLoyaltyHistoryPage(selectedCustomer.id, page, 20).catch(() => ({ items: [], page, limit: 20, total: 0 }));
    setCustomerLoyaltyHistory(result.items);
    setCustomerLoyaltyPage(result.page);
    setCustomerLoyaltyTotal(result.total);
  }

  async function saveCustomerTags() {
    if (!selectedCustomer?.id || !canUpdateCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    try {
      setCustomerDetailError('');
      await adminCustomersApi.adminUpdateCustomerTags(selectedCustomer.id, tags);
      await refreshSelectedCustomer();
      notifyAdmin('Đã lưu tag khách hàng.');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể lưu tag khách hàng.');
    }
  }

  async function saveCustomerProfile() {
    if (!selectedCustomer?.id || !canUpdateCustomerProfile) return;
    if (!customerProfileDraft.fullName.trim() || !customerProfileDraft.tier.trim()) return;
    try {
      setCustomerDetailError('');
      await adminCustomersApi.adminUpdateCustomerProfile(selectedCustomer.id, {
        fullName: customerProfileDraft.fullName.trim(),
        phone: customerProfileDraft.phone.trim() || undefined,
        tier: customerProfileDraft.tier.trim(),
        walletStatus: customerProfileDraft.walletStatus,
      });
      await refreshSelectedCustomer();
      notifyAdmin('Đã cập nhật thông tin khách hàng.');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể cập nhật thông tin khách hàng.');
    }
  }

  async function addCustomerNote() {
    if (!selectedCustomer?.id || !customerNoteDraft.trim() || !canUpdateCustomerProfile) return;
    try {
      setCustomerDetailError('');
      await adminCustomersApi.adminCreateCustomerNote(selectedCustomer.id, customerNoteDraft.trim());
      setCustomerNoteDraft('');
      setCustomerNotes(await adminCustomersApi.adminGetCustomerNotes(selectedCustomer.id).catch(() => []));
      await refreshSelectedCustomer();
      notifyAdmin('Đã thêm ghi chú CSKH.');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể thêm ghi chú CSKH.');
    }
  }

  async function adjustCustomerPoints() {
    if (!selectedCustomer?.id || !canAdjustCustomerPoints) return;
    const delta = Number(customerPointDelta || 0);
    if (!Number.isInteger(delta) || !delta || !customerPointReason.trim()) return;
    try {
      setCustomerDetailError('');
      await adminCustomersApi.adminAdjustCustomerLoyalty(selectedCustomer.id, { delta, reason: customerPointReason.trim() });
      setCustomerPointDelta('0');
      setCustomerPointReason('');
      await loadCustomerLoyaltyPage(customerLoyaltyPage);
      await refreshSelectedCustomer();
      notifyAdmin('Đã cập nhật điểm khách hàng.');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể cập nhật điểm khách hàng.');
    }
  }

  async function issueCustomerVoucher() {
    if (!selectedCustomer?.id || !customerVoucherId || !canIssueCustomerVoucher) return;
    try {
      setCustomerDetailError('');
      await adminCustomersApi.adminIssueCustomerVoucher(selectedCustomer.id, { voucherId: customerVoucherId, note: customerVoucherNote.trim() || undefined });
      setCustomerVoucherId('');
      setCustomerVoucherNote('');
      await refreshSelectedCustomer();
      notifyAdmin('Đã gửi voucher cho khách hàng.');
    } catch (error) {
      setCustomerDetailError(error instanceof Error ? error.message : 'Không thể gửi voucher cho khách hàng.');
    }
  }

  async function bulkSuspendCustomers() {
    if (!selectedCustomerIds.length || !canManageCustomerAccess) return;
    try {
      await adminCustomersApi.adminBulkUpdateUserStatus(selectedCustomerIds, 'SUSPENDED');
      setSelectedCustomerIds([]);
      await reloadCurrentTab();
      notifyAdmin(`Đã khóa ${selectedCustomerIds.length} khách hàng.`);
    } catch (error) {
      notifyAdmin(error instanceof Error ? error.message : 'Không thể khóa khách hàng hàng loạt.', 'error');
    }
  }

  async function bulkApplyCustomerTags() {
    if (!selectedCustomerIds.length || !canManageCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    try {
      await adminCustomersApi.adminBulkUpdateCustomerTags(selectedCustomerIds, tags);
      setSelectedCustomerIds([]);
      await reloadCurrentTab();
      notifyAdmin(`Đã gán tag cho ${selectedCustomerIds.length} khách hàng.`);
    } catch (error) {
      notifyAdmin(error instanceof Error ? error.message : 'Không thể gán tag hàng loạt.', 'error');
    }
  }

  return {
    selectedCustomerIds,
    setSelectedCustomerIds,
    selectedCustomer,
    setSelectedCustomer,
    customerDetailOpen,
    setCustomerDetailOpen,
    customerDetailBusy,
    setCustomerDetailBusy,
    customerDetailError,
    setCustomerDetailError,
    customerActiveSection,
    setCustomerActiveSection,
    customerOrders,
    setCustomerOrders,
    customerLoyaltyHistory,
    setCustomerLoyaltyHistory,
    customerLoyaltyPage,
    customerLoyaltyTotal,
    loadCustomerLoyaltyPage,
    customerNotes,
    setCustomerNotes,
    customerAuditLogs,
    setCustomerAuditLogs,
    customerTagDraft,
    setCustomerTagDraft,
    customerProfileDraft,
    setCustomerProfileDraft,
    customerNoteDraft,
    setCustomerNoteDraft,
    customerVoucherId,
    setCustomerVoucherId,
    customerVoucherNote,
    setCustomerVoucherNote,
    customerPointDelta,
    setCustomerPointDelta,
    customerPointReason,
    setCustomerPointReason,
    canIssueCustomerVoucher,
    openCustomerDetail,
    refreshSelectedCustomer,
    loadCustomerSection,
    saveCustomerTags,
    saveCustomerProfile,
    addCustomerNote,
    adjustCustomerPoints,
    issueCustomerVoucher,
    bulkSuspendCustomers,
    bulkApplyCustomerTags,
  };
}
