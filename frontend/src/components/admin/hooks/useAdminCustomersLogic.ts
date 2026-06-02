import { useState } from 'react';
import { apiDb } from '../../../services/apiDb';

type CustomerSection = 'summary' | 'orders' | 'loyalty' | 'notes' | 'audit';

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
  const [customerActiveSection, setCustomerActiveSection] = useState<CustomerSection>('summary');
  const [customerOrders, setCustomerOrders] = useState<any[]>([]);
  const [customerLoyaltyHistory, setCustomerLoyaltyHistory] = useState<any[]>([]);
  const [customerNotes, setCustomerNotes] = useState<any[]>([]);
  const [customerAuditLogs, setCustomerAuditLogs] = useState<any[]>([]);
  const [customerTagDraft, setCustomerTagDraft] = useState('');
  const [customerNoteDraft, setCustomerNoteDraft] = useState('');
  const [customerVoucherId, setCustomerVoucherId] = useState('');
  const [customerVoucherNote, setCustomerVoucherNote] = useState('');
  const [customerPointDelta, setCustomerPointDelta] = useState('0');
  const [customerPointReason, setCustomerPointReason] = useState('');

  async function openCustomerDetail(customer: any) {
    setCustomerDetailOpen(true);
    setCustomerDetailBusy(true);
    setCustomerActiveSection('summary');
    try {
      const detail = await apiDb.adminGetCustomerOverview(customer.id);
      setSelectedCustomer(detail);
      setCustomerOrders([]);
      setCustomerLoyaltyHistory([]);
      setCustomerNotes([]);
      setCustomerAuditLogs([]);
      setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
      setCustomerVoucherId('');
      setCustomerVoucherNote('');
      setCustomerPointDelta('0');
      setCustomerPointReason('');
      setCustomerNoteDraft('');
    } finally {
      setCustomerDetailBusy(false);
    }
  }

  async function refreshSelectedCustomer() {
    if (!selectedCustomer?.id) return;
    const detail = await apiDb.adminGetCustomerOverview(selectedCustomer.id);
    setSelectedCustomer(detail);
    setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
    await reloadCurrentTab();
  }

  async function loadCustomerSection(section: CustomerSection) {
    if (!selectedCustomer?.id) return;
    setCustomerActiveSection(section);
    if (section === 'orders' && customerOrders.length === 0) {
      setCustomerOrders(await apiDb.adminGetCustomerOrders(selectedCustomer.id).catch(() => []));
    }
    if (section === 'loyalty' && customerLoyaltyHistory.length === 0) {
      setCustomerLoyaltyHistory(await apiDb.adminGetCustomerLoyaltyHistory(selectedCustomer.id).catch(() => []));
    }
    if (section === 'notes' && customerNotes.length === 0) {
      setCustomerNotes(await apiDb.adminGetCustomerNotes(selectedCustomer.id).catch(() => []));
    }
    if (section === 'audit' && customerAuditLogs.length === 0) {
      setCustomerAuditLogs(await apiDb.adminGetCustomerAuditLogs(selectedCustomer.id).catch(() => []));
    }
  }

  async function saveCustomerTags() {
    if (!selectedCustomer?.id || !canUpdateCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    await apiDb.adminUpdateCustomerTags(selectedCustomer.id, tags);
    await refreshSelectedCustomer();
  }

  async function addCustomerNote() {
    if (!selectedCustomer?.id || !customerNoteDraft.trim() || !canUpdateCustomerProfile) return;
    await apiDb.adminCreateCustomerNote(selectedCustomer.id, customerNoteDraft.trim());
    setCustomerNoteDraft('');
    await refreshSelectedCustomer();
  }

  async function adjustCustomerPoints() {
    if (!selectedCustomer?.id || !canAdjustCustomerPoints) return;
    const delta = Number(customerPointDelta || 0);
    if (!delta || !customerPointReason.trim()) return;
    await apiDb.adminAdjustCustomerLoyalty(selectedCustomer.id, { delta, reason: customerPointReason.trim() });
    setCustomerPointDelta('0');
    setCustomerPointReason('');
    await refreshSelectedCustomer();
  }

  async function issueCustomerVoucher() {
    if (!selectedCustomer?.id || !customerVoucherId || !canIssueCustomerVoucher) return;
    await apiDb.adminIssueCustomerVoucher(selectedCustomer.id, { voucherId: customerVoucherId, note: customerVoucherNote.trim() || undefined });
    setCustomerVoucherId('');
    setCustomerVoucherNote('');
    await refreshSelectedCustomer();
  }

  async function bulkSuspendCustomers() {
    if (!selectedCustomerIds.length || !canManageCustomerAccess) return;
    await apiDb.adminBulkUpdateUserStatus(selectedCustomerIds, 'SUSPENDED');
    setSelectedCustomerIds([]);
    await reloadCurrentTab();
  }

  async function bulkApplyCustomerTags() {
    if (!selectedCustomerIds.length || !canManageCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    await apiDb.adminBulkUpdateCustomerTags(selectedCustomerIds, tags);
    setSelectedCustomerIds([]);
    await reloadCurrentTab();
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
    customerActiveSection,
    setCustomerActiveSection,
    customerOrders,
    setCustomerOrders,
    customerLoyaltyHistory,
    setCustomerLoyaltyHistory,
    customerNotes,
    setCustomerNotes,
    customerAuditLogs,
    setCustomerAuditLogs,
    customerTagDraft,
    setCustomerTagDraft,
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
    openCustomerDetail,
    refreshSelectedCustomer,
    loadCustomerSection,
    saveCustomerTags,
    addCustomerNote,
    adjustCustomerPoints,
    issueCustomerVoucher,
    bulkSuspendCustomers,
    bulkApplyCustomerTags,
  };
}
