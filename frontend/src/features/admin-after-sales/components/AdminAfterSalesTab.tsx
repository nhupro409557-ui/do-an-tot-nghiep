import { useEffect, useMemo, useState } from 'react';
import { adminAfterSalesApi } from '../services/adminAfterSalesApi';
import { API_BASE_URL } from '../../../services/apiClient';
import { adminActorLabel } from '../../admin-audit/utils/adminActorLabel';
import { useAuth } from '../../../context/AuthContext';

const statusLabel: Record<string, string> = {
  SUBMITTED: 'Chờ cửa hàng duyệt',
  RECEIVED: 'Cửa hàng đã tiếp nhận',
  QC_IN_PROGRESS: 'Đang kiểm tra QC',
  QC_APPROVED: 'Đã duyệt đổi trả',
  WARRANTY_ACCEPTED: 'Đã nhận bảo hành',
  REPAIRING: 'Đang sửa máy bảo hành cho khách',
  REPAIR_COMPLETED: 'Đã sửa xong máy bảo hành',
  REPLACEMENT_APPROVED: 'Đã duyệt thay máy',
  WAITING_FOR_STOCK: 'Đang chờ hàng',
  EXCHANGE_PROCESSING: 'Đang xử lý đổi máy',
  REPLACEMENT_PROCESSING: 'Đang xử lý máy thay thế',
  REFUND_PROCESSING: 'Ghi nhận hoàn tiền',
  READY_TO_RETURN: 'Sẵn sàng trả máy',
  RETURNING_TO_CUSTOMER: 'Đang gửi trả khách',
  COMPLETED: 'Hoàn tất xử lý',
  REJECTED: 'Bị từ chối',
  CANCELLED: 'Đã hủy',
  CLOSED_EXPIRED: 'Đã hết hạn',
};

const actionLabel: Record<string, string> = {
  RECEIVED: 'Tiếp nhận máy',
  QC_IN_PROGRESS: 'Bắt đầu kiểm QC',
  QC_APPROVED: 'Duyệt đổi trả',
  WARRANTY_ACCEPTED: 'Chấp nhận bảo hành',
  REPAIRING: 'Bắt đầu sửa máy bảo hành',
  REPAIR_COMPLETED: 'Xác nhận sửa xong máy bảo hành',
  READY_TO_RETURN: 'Sẵn sàng trả khách',
  RETURNING_TO_CUSTOMER: 'Gửi máy đến khách',
  REPLACEMENT_APPROVED: 'Duyệt đổi máy mới',
  REPLACEMENT_PROCESSING: 'Đang đổi máy',
  EXCHANGE_PROCESSING: 'Đang đổi máy',
  REFUND_PROCESSING: 'Ghi nhận hoàn tiền',
  COMPLETED: 'Hoàn tất hồ sơ',
  REJECTED: 'Từ chối yêu cầu',
};

const actionStyles: Record<string, string> = {
  RECEIVED: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200',
  QC_IN_PROGRESS: 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200',
  QC_APPROVED: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  WARRANTY_ACCEPTED: 'bg-teal-50 text-teal-700 hover:bg-teal-100 border border-teal-200',
  REPAIRING: 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200',
  REPAIR_COMPLETED: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  READY_TO_RETURN: 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200',
  RETURNING_TO_CUSTOMER: 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200',
  REPLACEMENT_APPROVED: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  REPLACEMENT_PROCESSING: 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200',
  EXCHANGE_PROCESSING: 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200',
  REFUND_PROCESSING: 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200',
  COMPLETED: 'bg-slate-900 text-white hover:bg-slate-800 shadow-sm',
  REJECTED: 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200',
};

const dispositionStatusLabels: Record<string, string> = {
  DEFECTIVE_RETURNED: 'Lỗi trả về',
  INSPECTION_PENDING: 'Chờ thẩm định QC',
  REPAIR_PENDING: 'Máy cũ thu hồi chờ sửa',
  REPAIRED: 'Máy cũ đã sửa xong',
  RTV_PENDING: 'Chờ trả NCC (RTV)',
  LIQUIDATION_PENDING: 'Chờ thanh lý',
  RTV_COMPLETED: 'Đã trả NCC (RTV xong)',
  LIQUIDATED: 'Đã thanh lý',
  SCRAP: 'Hủy phế phẩm (Scrap)',
  OUT_OF_SYSTEM: 'Đã xuất khỏi HT',
};

const INITIAL_DEFECTIVE_ACTIONS = ['REPAIR_PENDING', 'RTV_COMPLETED', 'LIQUIDATED', 'SCRAP'];
const REPAIR_RESULT_ACTIONS = ['REPAIRED', 'RTV_COMPLETED', 'LIQUIDATED', 'SCRAP'];

const hasValidDeliveryDetails = (name: string, phone: string, address: string) => (
  name.trim().length >= 2 && phone.trim().length >= 8 && address.trim().length >= 10
);

const completedDispositionStatuses = ['REPAIRED', 'RTV_COMPLETED', 'LIQUIDATED', 'SCRAP', 'OUT_OF_SYSTEM'];

const distinctPhysicalDevices = (items: any[]) => {
  const devices = new Map<string, any>();
  items.forEach(item => {
    const key = String(item.deviceKey || `${item.type || 'IDENTIFIER'}:${item.id}`);
    if (!devices.has(key)) devices.set(key, item);
  });
  return Array.from(devices.values());
};

const statusStyles: Record<string, { bg: string; text: string; border: string }> = {
  SUBMITTED: { bg: 'bg-slate-50', text: 'text-slate-650', border: 'border-slate-200' },
  RECEIVED: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  QC_IN_PROGRESS: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  QC_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WARRANTY_ACCEPTED: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
  REPAIRING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  REPAIR_COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  REPLACEMENT_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WAITING_FOR_STOCK: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  EXCHANGE_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REPLACEMENT_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REFUND_PROCESSING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  READY_TO_RETURN: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  RETURNING_TO_CUSTOMER: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  REJECTED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  CANCELLED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200' },
  CLOSED_EXPIRED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200' },
};

const uploadBaseUrl = API_BASE_URL.replace(/\/api\/?$/, '');

const inventoryDispositionLabels: Record<string, string> = {
  NEW_STOCK: 'Nhập lại kho hàng mới',
  USED_INTAKE: 'Chuyển sang hàng cũ',
  REPAIR: 'Cách ly chờ sửa chữa',
  SCRAP: 'Chờ thanh lý / tiêu hủy',
};

statusLabel.WAITING_FOR_EXCHANGE_PAYMENT = 'Chờ thanh toán chênh lệch';
actionLabel.WAITING_FOR_EXCHANGE_PAYMENT = 'Chờ khách thanh toán';
statusStyles.WAITING_FOR_EXCHANGE_PAYMENT = { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' };
actionStyles.WAITING_FOR_EXCHANGE_PAYMENT = 'bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200';

const resolveAttachmentUrl = (url: string | undefined) => {
  if (!url) return '#';
  if (/^https?:\/\//i.test(url)) return url;
  const normalized = url.startsWith('/') ? url : `/${url}`;
  return `${uploadBaseUrl}${normalized}`;
};

const isImageAttachment = (contentType: string | undefined) => String(contentType || '').startsWith('image/');
const isVideoAttachment = (contentType: string | undefined) => String(contentType || '').startsWith('video/');

const formatAttachmentSize = (value: unknown) => {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('vi-VN')} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} MB`;
};

const returnActions: Record<string, string[]> = {
  SUBMITTED: ['RECEIVED', 'REJECTED'],
  RECEIVED: ['QC_IN_PROGRESS', 'REJECTED'],
  QC_IN_PROGRESS: ['QC_APPROVED', 'REJECTED'],
  QC_APPROVED: ['EXCHANGE_PROCESSING', 'REFUND_PROCESSING'],
  WAITING_FOR_STOCK: ['QC_APPROVED', 'EXCHANGE_PROCESSING'],
  WAITING_FOR_EXCHANGE_PAYMENT: ['EXCHANGE_PROCESSING'],
  EXCHANGE_PROCESSING: ['COMPLETED'],
  REFUND_PROCESSING: ['COMPLETED'],
};

const warrantyActions: Record<string, string[]> = {
  SUBMITTED: ['RECEIVED', 'REJECTED'],
  RECEIVED: ['QC_IN_PROGRESS', 'REJECTED'],
  QC_IN_PROGRESS: ['WARRANTY_ACCEPTED', 'REPLACEMENT_APPROVED', 'REJECTED'],
  WARRANTY_ACCEPTED: ['QC_IN_PROGRESS', 'REPAIRING'],
  REPAIRING: ['REPAIR_COMPLETED'],
  REPAIR_COMPLETED: ['READY_TO_RETURN', 'RETURNING_TO_CUSTOMER'],
  REPLACEMENT_APPROVED: ['QC_IN_PROGRESS', 'REPLACEMENT_PROCESSING'],
  WAITING_FOR_STOCK: ['QC_IN_PROGRESS', 'REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'],
  REPLACEMENT_PROCESSING: ['READY_TO_RETURN', 'COMPLETED'],
  READY_TO_RETURN: ['COMPLETED'],
  RETURNING_TO_CUSTOMER: [],
};

type ReplacementIdentifierDraft = {
  imeis: string;
  serialNumbers: string;
};

const canShowAfterSalesAction = (section: string, item: any, targetStatus: string) => {
  if (
    section !== 'warranties'
    || item.resolutionType !== 'REPLACEMENT'
    || !['READY_TO_RETURN', 'COMPLETED'].includes(targetStatus)
  ) {
    return true;
  }
  if (item.fulfillmentOutbound?.status !== 'COMPLETED') return false;
  if (targetStatus === 'READY_TO_RETURN') {
    return item.fulfillmentOrder?.fulfillmentMethod === 'STORE_PICKUP';
  }
  return item.fulfillmentOrder?.fulfillmentMethod !== 'DELIVERY'
    || item.fulfillmentOrder?.status === 'COMPLETED';
};

type ReplacementCandidate = {
  key: string;
  imeis: string[];
  secondaryImei?: string | null;
  serialNumbers: string[];
  locationId: string;
  locationCode?: string | null;
  locationName?: string | null;
};

const splitIdentifierValues = (value: string) => (
  value
    .split(/[\s,;]+/)
    .map(item => item.trim())
    .filter(Boolean)
);

const needsReplacementIdentifiers = (
  _section: 'returns' | 'warranties' | 'defective',
  _request: any,
  _targetStatus: string,
) => {
  return false;
};

export default function AdminAfterSalesTab({ query = '', setTab, setQuery }: { query?: string; setTab?: (tab: string) => void; setQuery?: (value: string) => void }) {
  const { usePermission } = useAuth();
  const canUpdateAfterSales = usePermission('after_sales:update');
  const canInspectAfterSales = usePermission('after_sales:inspect');
  const canRefundAfterSales = usePermission('after_sales:refund');
  const canExchangeAfterSales = usePermission('after_sales:exchange');
  const canManageUsedProducts = usePermission('used_product:manage');
  const [section, setSection] = useState<'returns' | 'warranties' | 'defective'>('returns');
  const [returns, setReturns] = useState<any[]>([]);
  const [warranties, setWarranties] = useState<any[]>([]);
  const [defective, setDefective] = useState<any[]>([]);
  const [defectiveReport, setDefectiveReport] = useState<any>({ summary: {}, byStatus: [], byBrand: [], topProducts: [] });
  const [message, setMessage] = useState('');

  // States dành cho Modal xử lý đổi trạng thái
  const [showAdvanceModal, setShowAdvanceModal] = useState(false);
  const [modalRequest, setModalRequest] = useState<any>(null);
  const [modalTargetStatus, setModalTargetStatus] = useState('');
  const [note, setNote] = useState('');
  const [replacementIdentifiers, setReplacementIdentifiers] = useState<Record<string, ReplacementIdentifierDraft>>({});
  const [replacementCandidates, setReplacementCandidates] = useState<Record<string, ReplacementCandidate[]>>({});
  const [replacementSearch, setReplacementSearch] = useState<Record<string, string>>({});
  const [replacementCandidatesLoading, setReplacementCandidatesLoading] = useState(false);
  const [replacementCandidatesError, setReplacementCandidatesError] = useState('');
  const [depreciationFee, setDepreciationFee] = useState('');
  const [shippingDeduction, setShippingDeduction] = useState('');
  const [exchangeFee, setExchangeFee] = useState('');
  const [refundTransactionRef, setRefundTransactionRef] = useState('');
  const [refundProofUrl, setRefundProofUrl] = useState('');
  const [refundNote, setRefundNote] = useState('');
  const [repairDiagnosis, setRepairDiagnosis] = useState('');
  const [repairAction, setRepairAction] = useState('');
  const [repairParts, setRepairParts] = useState('');
  const [repairCost, setRepairCost] = useState('');
  const [repairChannel, setRepairChannel] = useState<'INTERNAL' | 'MANUFACTURER'>('INTERNAL');
  const [repairProviderName, setRepairProviderName] = useState('');
  const [returnFulfillmentMethod, setReturnFulfillmentMethod] = useState<'STORE_PICKUP' | 'DELIVERY'>('STORE_PICKUP');
  const [recipientName, setRecipientName] = useState('');
  const [recipientPhone, setRecipientPhone] = useState('');
  const [shippingAddress, setShippingAddress] = useState('');
  const [shippingProvider, setShippingProvider] = useState('');
  const [busy, setBusy] = useState(false);
  const [qcResult, setQcResult] = useState('');
  const [inventoryDisposition, setInventoryDisposition] = useState('USED_INTAKE');
  const [customerFault, setCustomerFault] = useState(false);
  const [customerReceiptConfirmed, setCustomerReceiptConfirmed] = useState(false);

  // States dành cho Modal xem chi tiết
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailRequest, setDetailRequest] = useState<any>(null);
  const [detailEvents, setDetailEvents] = useState<any[]>([]);
  const [detailEventsLoading, setDetailEventsLoading] = useState(false);
  const [timelineNote, setTimelineNote] = useState('');
  const [timelineNoteBusy, setTimelineNoteBusy] = useState(false);

  // States dành cho Modal xử lý IMEI lỗi (Disposition)
  const [showDispositionModal, setShowDispositionModal] = useState(false);
  const [selectedDefective, setSelectedDefective] = useState<any>(null);
  const [dispositionEvents, setDispositionEvents] = useState<any[]>([]);
  const [dispositionEventsLoading, setDispositionEventsLoading] = useState(false);
  const [dispStatus, setDispStatus] = useState('INSPECTION_PENDING');
  const [dispReason, setDispReason] = useState('');
  const [docRef, setDocRef] = useState('');
  const [partner, setPartner] = useState('');
  const [recoveryVal, setRecoveryVal] = useState('0');
  const [defectiveQuery, setDefectiveQuery] = useState('');
  const [defectiveStatusFilter, setDefectiveStatusFilter] = useState('all');
  const [defectiveQuickFilter, setDefectiveQuickFilter] = useState<'all' | 'processing' | 'completed' | 'documented' | 'recovered'>('all');

  async function load() {
    const results = await Promise.allSettled([
      adminAfterSalesApi.listReturns(),
      adminAfterSalesApi.listWarranties(),
      adminAfterSalesApi.listDefectiveIdentifiers(),
      adminAfterSalesApi.getDefectiveDispositionReport(),
    ]);
    const [returnResult, warrantyResult, defectiveResult, defectiveReportResult] = results;
    const refreshedReturns = returnResult.status === 'fulfilled' ? returnResult.value.items || [] : returns;
    const refreshedWarranties = warrantyResult.status === 'fulfilled' ? warrantyResult.value.items || [] : warranties;
    if (returnResult.status === 'fulfilled') setReturns(refreshedReturns);
    if (warrantyResult.status === 'fulfilled') setWarranties(refreshedWarranties);
    if (defectiveResult.status === 'fulfilled') setDefective(defectiveResult.value || []);
    if (defectiveReportResult.status === 'fulfilled') {
      setDefectiveReport(defectiveReportResult.value || { summary: {}, byStatus: [], byBrand: [], topProducts: [] });
    }
    const failedSections = [
      returnResult.status === 'rejected' ? 'đổi trả' : '',
      warrantyResult.status === 'rejected' ? 'bảo hành' : '',
      defectiveResult.status === 'rejected' || defectiveReportResult.status === 'rejected' ? 'máy lỗi thu hồi' : '',
    ].filter(Boolean);
    setMessage(failedSections.length > 0
      ? `Không thể tải phần ${failedSections.join(', ')}. Các phần còn lại vẫn hoạt động.`
      : '');
    return { returns: refreshedReturns, warranties: refreshedWarranties };
  }

  useEffect(() => {
    void load();
  }, []);

  // Mở modal để đổi trạng thái
  const handleOpenAdvanceModal = (item: any, status: string) => {
    setModalRequest(item);
    setModalTargetStatus(status);
    setNote('');
    setReplacementIdentifiers(Object.fromEntries(
      (item.items || []).map((requestItem: any) => [
        requestItem.id,
        {
          imeis: (requestItem.replacementImeis || [requestItem.replacementImei].filter(Boolean)).join('\n'),
          serialNumbers: (requestItem.replacementSerialNumbers || []).join('\n'),
        },
      ]),
    ));
    setReplacementCandidates({});
    setReplacementSearch({});
    setReplacementCandidatesError('');
    setDepreciationFee(String(item.depreciationFee || ''));
    setShippingDeduction('');
    setExchangeFee(item.exchangeFee ? String(item.exchangeFee) : '');
    setRefundTransactionRef('');
    setRefundProofUrl('');
    setRefundNote('');
    setRepairDiagnosis(String(item.repairSummary?.diagnosis || ''));
    setRepairAction(String(item.repairSummary?.action || ''));
    setRepairParts(String(item.repairSummary?.parts || ''));
    setRepairCost(item.repairSummary?.cost ? String(item.repairSummary.cost) : '');
    setRepairChannel(item.repairChannel === 'MANUFACTURER' ? 'MANUFACTURER' : 'INTERNAL');
    setRepairProviderName(String(item.repairProviderName || ''));
    setReturnFulfillmentMethod(item.returnFulfillmentMethod === 'DELIVERY' || item.fulfillmentOrder?.fulfillmentMethod === 'DELIVERY' ? 'DELIVERY' : 'STORE_PICKUP');
    setRecipientName(String(item.fulfillmentOrder?.recipientName || ''));
    setRecipientPhone(String(item.fulfillmentOrder?.recipientPhone || ''));
    setShippingAddress(String(item.fulfillmentOrder?.shippingAddress || ''));
    setShippingProvider(String(item.fulfillmentOrder?.shippingProvider || ''));
    setQcResult(item.status === 'QC_IN_PROGRESS' ? (section === 'returns' ? 'APPROVE_EXCHANGE' : 'ACCEPT_REPAIR') : '');
    setInventoryDisposition(String(item.inventoryDisposition || 'USED_INTAKE'));
    setCustomerFault(false);
    setCustomerReceiptConfirmed(false);
    setShowAdvanceModal(true);
  };

  const requiresCustomerReceiptConfirmation = Boolean(
    modalRequest
    && modalTargetStatus === 'COMPLETED'
    && (
      (section === 'returns' && modalRequest.resolutionType === 'EXCHANGE')
      || (section === 'warranties' && ['REPAIR', 'REPLACEMENT'].includes(modalRequest.resolutionType))
    )
  );

  const loadReplacementCandidates = async () => {
    if (!modalRequest || section !== 'warranties') return;
    setReplacementCandidatesLoading(true);
    setReplacementCandidatesError('');
    try {
      const data = await adminAfterSalesApi.listWarrantyReplacementCandidates(modalRequest.id);
      setReplacementCandidates(Object.fromEntries(
        (data.items || []).map((item: any) => [item.requestItemId, item.candidates || []]),
      ));
    } catch (error) {
      setReplacementCandidatesError(error instanceof Error ? error.message : 'Không thể tải danh sách máy thay thế.');
    } finally {
      setReplacementCandidatesLoading(false);
    }
  };

  const selectReplacementCandidate = (requestItem: any, candidate: ReplacementCandidate) => {
    const current = replacementIdentifiers[requestItem.id] || { imeis: '', serialNumbers: '' };
    const imeis = splitIdentifierValues(current.imeis);
    const serialNumbers = splitIdentifierValues(current.serialNumbers);
    const primaryImei = candidate.imeis[0];
    const serialNumber = candidate.serialNumbers[0];
    const quantity = Number(requestItem.quantity || 1);
    if ((primaryImei && imeis.includes(primaryImei)) || (serialNumber && serialNumbers.includes(serialNumber))) return;
    if (Math.max(imeis.length, serialNumbers.length) >= quantity) {
      setReplacementCandidatesError(`Đã chọn đủ ${quantity} thiết bị cho ${requestItem.productName}.`);
      return;
    }
    setReplacementIdentifiers(currentState => ({
      ...currentState,
      [requestItem.id]: {
        imeis: [...imeis, ...(primaryImei ? [primaryImei] : [])].join('\n'),
        serialNumbers: [...serialNumbers, ...(serialNumber ? [serialNumber] : [])].join('\n'),
      },
    }));
    setReplacementCandidatesError('');
  };

  const removeReplacementCandidate = (requestItem: any, index: number) => {
    const current = replacementIdentifiers[requestItem.id] || { imeis: '', serialNumbers: '' };
    const imeis = splitIdentifierValues(current.imeis);
    const serialNumbers = splitIdentifierValues(current.serialNumbers);
    imeis.splice(index, 1);
    serialNumbers.splice(index, 1);
    setReplacementIdentifiers(currentState => ({
      ...currentState,
      [requestItem.id]: { imeis: imeis.join('\n'), serialNumbers: serialNumbers.join('\n') },
    }));
  };

  // Xác nhận đổi trạng thái từ Modal
  const handleConfirmAdvance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalRequest) return;

    if (modalRequest.status === 'QC_IN_PROGRESS') {
      if (note.trim().length < 10) {
        alert('Vui lòng nhập đánh giá QC chi tiết (tối thiểu 10 ký tự).');
        return;
      }
      if (section === 'warranties' && qcResult === 'ACCEPT_REPAIR' && repairChannel === 'MANUFACTURER' && !repairProviderName.trim()) {
        alert('Vui lòng nhập tên hãng hoặc trung tâm bảo hành.');
        return;
      }
      if (
        section === 'warranties'
        && qcResult === 'APPROVE_REPLACEMENT'
        && returnFulfillmentMethod === 'DELIVERY'
        && !hasValidDeliveryDetails(recipientName, recipientPhone, shippingAddress)
      ) {
        alert('Tên người nhận cần ít nhất 2 ký tự, số điện thoại 8 ký tự và địa chỉ 10 ký tự.');
        return;
      }
      setBusy(true);
      try {
        const api = section === 'returns' ? adminAfterSalesApi.inspectReturn : adminAfterSalesApi.inspectWarranty;
        await api(modalRequest.id, {
          result: qcResult,
          qc_note: note.trim(),
          customer_fault: customerFault,
          depreciation_fee: section === 'returns' ? Number(depreciationFee || 0) : 0,
          shipping_deduction: section === 'returns' ? Number(shippingDeduction || 0) : 0,
          exchange_fee: section === 'returns' && exchangeFee !== '' ? Number(exchangeFee || 0) : null,
          inventory_disposition: section === 'returns' && qcResult !== 'REJECT' ? inventoryDisposition : null,
          repair_channel: section === 'warranties' && qcResult === 'ACCEPT_REPAIR' ? repairChannel : undefined,
          repair_provider_name: section === 'warranties' && qcResult === 'ACCEPT_REPAIR' && repairChannel === 'MANUFACTURER' ? repairProviderName.trim() : undefined,
          return_fulfillment_method: section === 'warranties' && qcResult === 'APPROVE_REPLACEMENT' ? returnFulfillmentMethod : undefined,
          recipient_name: returnFulfillmentMethod === 'DELIVERY' ? recipientName.trim() || undefined : undefined,
          recipient_phone: returnFulfillmentMethod === 'DELIVERY' ? recipientPhone.trim() || undefined : undefined,
          shipping_address: returnFulfillmentMethod === 'DELIVERY' ? shippingAddress.trim() || undefined : undefined,
          shipping_provider: returnFulfillmentMethod === 'DELIVERY' ? shippingProvider.trim() || undefined : undefined,
        });
        setShowAdvanceModal(false);
        const refreshed = await load();
        if (detailRequest && detailRequest.id === modalRequest.id) {
          const list = section === 'returns' ? refreshed.returns : refreshed.warranties;
          const updated = list.find(r => r.id === modalRequest.id);
          if (updated) {
            setDetailRequest(updated);
            await loadDetailEvents(updated);
          }
        }
      } catch (error) {
        alert(error instanceof Error ? error.message : 'Không thể ghi nhận kết quả QC.');
      } finally {
        setBusy(false);
      }
      return;
    }

    if (section === 'warranties' && modalTargetStatus === 'QC_IN_PROGRESS' && note.trim().length < 10) {
      alert('Vui lòng nhập lý do đánh giá lại QC tối thiểu 10 ký tự.');
      return;
    }

    const needsIdentifiers = needsReplacementIdentifiers(section, modalRequest, modalTargetStatus);
    const replacementItems = (modalRequest.items || []).map((requestItem: any) => {
      const draft = replacementIdentifiers[requestItem.id] || { imeis: '', serialNumbers: '' };
      return {
        request_item_id: requestItem.id,
        imeis: splitIdentifierValues(draft.imeis),
        serial_numbers: splitIdentifierValues(draft.serialNumbers),
      };
    });
    if (needsIdentifiers) {
      for (let index = 0; index < replacementItems.length; index += 1) {
        const replacementItem = replacementItems[index];
        const requestItem = modalRequest.items[index];
        const quantity = Number(requestItem.quantity || 1);
        if (!replacementItem.imeis.length && !replacementItem.serial_numbers.length) {
          alert(`Vui lòng nhập IMEI hoặc serial thay thế cho ${requestItem.productName}.`);
          return;
        }
        if (replacementItem.imeis.length && replacementItem.imeis.length !== quantity) {
          alert(`Số IMEI thay thế của ${requestItem.productName} phải bằng số lượng ${quantity}.`);
          return;
        }
        if (replacementItem.serial_numbers.length && replacementItem.serial_numbers.length !== quantity) {
          alert(`Số serial thay thế của ${requestItem.productName} phải bằng số lượng ${quantity}.`);
          return;
        }
      }
    }

    const needsRefundProof = section === 'returns' && modalTargetStatus === 'COMPLETED' && modalRequest.status === 'REFUND_PROCESSING';
    if (needsRefundProof) {
      if (!refundTransactionRef.trim()) {
        alert('Vui lòng nhập mã giao dịch hoặc chứng từ hoàn tiền.');
        return;
      }
      if (!refundProofUrl.trim()) {
        alert('Vui lòng cung cấp link hình ảnh/chứng từ hoàn tiền (proof URL).');
        return;
      }
    }

    const needsRepairDetails = section === 'warranties' && modalTargetStatus === 'REPAIR_COMPLETED' && modalRequest.resolutionType === 'REPAIR';
    if (needsRepairDetails) {
      if (!repairDiagnosis.trim()) {
        alert('Vui lòng nhập chẩn đoán lỗi.');
        return;
      }
      if (!repairAction.trim()) {
        alert('Vui lòng nhập hướng xử lý.');
        return;
      }
    }
    if (section === 'warranties' && modalTargetStatus === 'REPAIRING') {
      if (repairChannel === 'MANUFACTURER' && !repairProviderName.trim()) {
        alert('Vui lòng nhập tên hãng hoặc trung tâm bảo hành.');
        return;
      }
    }
    if (section === 'warranties' && modalTargetStatus === 'RETURNING_TO_CUSTOMER') {
      if (!hasValidDeliveryDetails(recipientName, recipientPhone, shippingAddress)) {
        alert('Tên người nhận cần ít nhất 2 ký tự, số điện thoại 8 ký tự và địa chỉ 10 ký tự.');
        return;
      }
    }
    if (section === 'warranties' && modalRequest.resolutionType === 'REPLACEMENT' && ['REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'].includes(modalTargetStatus) && returnFulfillmentMethod === 'DELIVERY') {
      if (!hasValidDeliveryDetails(recipientName, recipientPhone, shippingAddress)) {
        alert('Tên người nhận cần ít nhất 2 ký tự, số điện thoại 8 ký tự và địa chỉ 10 ký tự.');
        return;
      }
    }
    if (requiresCustomerReceiptConfirmation && !customerReceiptConfirmed) {
      alert('Vui lòng xác nhận khách đã nhận máy trước khi hoàn tất hồ sơ.');
      return;
    }
    setBusy(true);
    try {
      const resolutionType = modalTargetStatus === 'QC_APPROVED' ? 'EXCHANGE' :
                             modalTargetStatus === 'REFUND_PROCESSING' ? 'REFUND' :
                             modalTargetStatus === 'REPLACEMENT_APPROVED' ? 'REPLACEMENT' : undefined;

      const api = section === 'returns' ? adminAfterSalesApi.updateReturn : adminAfterSalesApi.updateWarranty;
      await api(modalRequest.id, {
        status: modalTargetStatus,
        resolution_type: resolutionType,
        note: note.trim() || undefined,
        replacement_items: needsIdentifiers ? replacementItems : undefined,
        refund_transaction_ref: needsRefundProof ? refundTransactionRef.trim() : undefined,
        refund_proof_url: needsRefundProof ? refundProofUrl.trim() || undefined : undefined,
        refund_note: needsRefundProof ? refundNote.trim() || undefined : undefined,
        depreciation_fee: section === 'returns' ? Number(depreciationFee || 0) : 0,
        repair_diagnosis: section === 'warranties' ? repairDiagnosis.trim() || undefined : undefined,
        repair_action: section === 'warranties' ? repairAction.trim() || undefined : undefined,
        repair_parts: section === 'warranties' ? repairParts.trim() || undefined : undefined,
        repair_cost: section === 'warranties' ? Number(repairCost || 0) : 0,
        repair_channel: section === 'warranties' && modalRequest.resolutionType === 'REPAIR' ? repairChannel : undefined,
        repair_provider_name: section === 'warranties' && repairChannel === 'MANUFACTURER' ? repairProviderName.trim() || undefined : undefined,
        return_fulfillment_method: section === 'warranties' ? (modalTargetStatus === 'RETURNING_TO_CUSTOMER' ? 'DELIVERY' : modalTargetStatus === 'READY_TO_RETURN' ? 'STORE_PICKUP' : returnFulfillmentMethod) : undefined,
        recipient_name: returnFulfillmentMethod === 'DELIVERY' || modalTargetStatus === 'RETURNING_TO_CUSTOMER' ? recipientName.trim() || undefined : undefined,
        recipient_phone: returnFulfillmentMethod === 'DELIVERY' || modalTargetStatus === 'RETURNING_TO_CUSTOMER' ? recipientPhone.trim() || undefined : undefined,
        shipping_address: returnFulfillmentMethod === 'DELIVERY' || modalTargetStatus === 'RETURNING_TO_CUSTOMER' ? shippingAddress.trim() || undefined : undefined,
        shipping_provider: returnFulfillmentMethod === 'DELIVERY' || modalTargetStatus === 'RETURNING_TO_CUSTOMER' ? shippingProvider.trim() || undefined : undefined,
        customer_receipt_confirmed: requiresCustomerReceiptConfirmation ? customerReceiptConfirmed : false,
      });

      setShowAdvanceModal(false);
      const refreshed = await load();

      // Cập nhật lại chi tiết nếu đang mở xem chi tiết
      if (detailRequest && detailRequest.id === modalRequest.id) {
        const list = section === 'returns' ? refreshed.returns : refreshed.warranties;
        const updated = list.find(r => r.id === modalRequest.id);
        if (updated) {
          setDetailRequest(updated);
          await loadDetailEvents(updated);
        }
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể cập nhật trạng thái.');
    } finally {
      setBusy(false);
    }
  };

  const handleCreateRepairedUsedIntake = async (item: any) => {
    const confirmed = window.confirm(
      `Chuyển máy cũ ${item.identifier} sang quy trình hàng cũ? Máy vẫn phải được thẩm định và duyệt giá trước khi bán.`,
    );
    if (!confirmed) return;
    setBusy(true);
    try {
      const result = await adminAfterSalesApi.createRepairedUsedIntake(item.id, {
        confirmed: true,
        note: 'Admin chuyển máy cũ đã sửa sang quy trình thẩm định hàng cũ.',
      });
      await load();
      setMessage(`Đã tạo hồ sơ hàng cũ ${result.requestCode}.`);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể chuyển máy đã sửa sang hàng cũ.');
    } finally {
      setBusy(false);
    }
  };

  // Xem chi tiết hồ sơ
  async function loadDetailEvents(item: any) {
    setDetailEventsLoading(true);
    try {
      const loader = section === 'returns' ? adminAfterSalesApi.listReturnEvents : adminAfterSalesApi.listWarrantyEvents;
      const events = await loader(item.id);
      setDetailEvents(Array.isArray(events) ? events : []);
    } catch (error) {
      console.error('Không thể tải timeline hậu mãi:', error);
      setDetailEvents([]);
    } finally {
      setDetailEventsLoading(false);
    }
  }

  const handleOpenDetailModal = async (item: any) => {
    setDetailRequest(item);
    setDetailEvents([]);
    setTimelineNote('');
    setShowDetailModal(true);
    await loadDetailEvents(item);
  };

  async function handleAddTimelineNote() {
    if (!detailRequest || timelineNote.trim().length < 3) return;
    setTimelineNoteBusy(true);
    try {
      const api = section === 'returns' ? adminAfterSalesApi.addReturnEvent : adminAfterSalesApi.addWarrantyEvent;
      await api(detailRequest.id, { note: timelineNote.trim() });
      setTimelineNote('');
      await loadDetailEvents(detailRequest);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể thêm ghi chú timeline.');
    } finally {
      setTimelineNoteBusy(false);
    }
  };

  // Mở modal Disposition IMEI lỗi
  async function loadDispositionEvents(item: any) {
    setDispositionEventsLoading(true);
    try {
      const rows = await adminAfterSalesApi.listDispositionEvents(String(item.id));
      setDispositionEvents(Array.isArray(rows) ? rows : []);
    } catch (error) {
      console.error('Không thể tải lịch sử định đoạt IMEI:', error);
      setDispositionEvents([]);
    } finally {
      setDispositionEventsLoading(false);
    }
  }

  const handleOpenDispositionModal = (item: any, initialStatus = 'REPAIR_PENDING') => {
    setSelectedDefective(item);
    setDispositionEvents([]);
    setDispStatus(initialStatus);
    setDispReason('');
    setDocRef('');
    setPartner('');
    setRecoveryVal('0');
    setShowDispositionModal(true);
    void loadDispositionEvents(item);
  };

  // Xác nhận Disposition IMEI lỗi
  const handleConfirmDisposition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDefective) return;

    setBusy(true);
    try {
      await adminAfterSalesApi.updateDisposition(selectedDefective.id, {
        status: dispStatus,
        reason: dispReason.trim() || (dispositionStatusLabels[dispStatus] || 'Xử lý mã định danh lỗi.'),
        document_reference: docRef.trim() || undefined,
        partner_name: partner.trim() || undefined,
        recovery_value: parseFloat(recoveryVal) || 0
      });
      await loadDispositionEvents(selectedDefective);
      setShowDispositionModal(false);
      await load();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể cập nhật định đoạt.');
    } finally {
      setBusy(false);
    }
  };

  const requests = section === 'returns' ? returns : warranties;
  const filteredRequests = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return requests;

    return requests.filter(item => {
      const itemSearchText = (item.items || []).flatMap((line: any) => [
        line.productName,
        line.imei,
        line.secondaryImei,
        line.serialNumber,
        ...(line.replacementImeis || []),
        ...(line.replacementSecondaryImeis || []),
        ...(line.replacementSerialNumbers || []),
      ]);
      const searchable = [
        item.requestCode,
        item.orderCode,
        item.status,
        statusLabel[item.status],
        item.fulfillmentOrder?.orderCode,
        item.fulfillmentOrder?.trackingCode,
        item.fulfillmentOutbound?.documentNo,
        ...itemSearchText,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return searchable.includes(needle);
    });
  }, [query, requests]);
  const actions = section === 'returns' ? returnActions : warrantyActions;
  const filteredDefective = useMemo(() => {
    const query = defectiveQuery.trim().toLowerCase();

    return defective.filter(item => {
      const latest = item.latestDisposition || {};
      const recoveryValue = Number(latest.recoveryValue || 0);
      const matchesStatus = defectiveStatusFilter === 'all' || item.status === defectiveStatusFilter;
      const matchesQuickFilter =
        defectiveQuickFilter === 'all'
        || (defectiveQuickFilter === 'processing' && !completedDispositionStatuses.includes(item.status))
        || (defectiveQuickFilter === 'completed' && completedDispositionStatuses.includes(item.status))
        || (defectiveQuickFilter === 'documented' && Boolean(latest.documentReference))
        || (defectiveQuickFilter === 'recovered' && recoveryValue > 0);
      const searchable = [
        item.identifier,
        item.productName,
        item.status,
        latest.documentReference,
        latest.partnerName,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return matchesStatus && matchesQuickFilter && (!query || searchable.includes(query));
    });
  }, [defective, defectiveQuery, defectiveQuickFilter, defectiveStatusFilter]);

  const defectiveQuickCounts = useMemo(() => {
    return distinctPhysicalDevices(defective).reduce(
      (summary, item) => {
        const latest = item.latestDisposition || {};
        const recoveryValue = Number(latest.recoveryValue || 0);
        const completed = completedDispositionStatuses.includes(item.status);

        summary.all += 1;
        if (!completed) summary.processing += 1;
        if (completed) summary.completed += 1;
        if (latest.documentReference) summary.documented += 1;
        if (recoveryValue > 0) summary.recovered += 1;
        return summary;
      },
      { all: 0, processing: 0, completed: 0, documented: 0, recovered: 0 },
    );
  }, [defective]);

  const defectiveSummary = useMemo(() => {
    return distinctPhysicalDevices(filteredDefective).reduce(
      (summary, item) => {
        const latest = item.latestDisposition || {};
        const averageUnitCost = Number(item.averageUnitCost || 0);
        const recoveryValue = Number(latest.recoveryValue || 0);

        summary.total += 1;
        summary.inventoryValue += averageUnitCost;
        summary.recoveryValue += recoveryValue;
        if (latest.documentReference) summary.documented += 1;
        if (completedDispositionStatuses.includes(item.status)) {
          summary.completed += 1;
        }
        return summary;
      },
      { total: 0, inventoryValue: 0, recoveryValue: 0, documented: 0, completed: 0 },
    );
  }, [filteredDefective]);

  const reportSummary = defectiveReport?.summary || {};
  const reportByStatus = Array.isArray(defectiveReport?.byStatus) ? defectiveReport.byStatus : [];
  const reportByBrand = Array.isArray(defectiveReport?.byBrand) ? defectiveReport.byBrand : [];
  const reportTopProducts = Array.isArray(defectiveReport?.topProducts) ? defectiveReport.topProducts : [];
  const recoveryRate = Number(reportSummary.inventoryValue || 0) > 0
    ? Math.round((Number(reportSummary.recoveryValue || 0) / Number(reportSummary.inventoryValue || 0)) * 100)
    : 0;

  function handleExportDefectiveCsv() {
    if (!filteredDefective.length) return;

    const escapeCsv = (value: unknown) => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };
    const headers = [
      'IMEI',
      'Sản phẩm',
      'Trạng thái',
      'Giá trị trung bình',
      'Chứng từ',
      'Đối tác',
      'Giá trị thu hồi',
      'Cập nhật gần nhất',
    ];
    const rows = filteredDefective.map(item => {
      const latest = item.latestDisposition || {};
      return [
        item.identifier,
        item.productName,
        dispositionStatusLabels[item.status] || item.status,
        Number(item.averageUnitCost || 0),
        latest.documentReference || '',
        latest.partnerName || '',
        Number(latest.recoveryValue || 0),
        latest.createdAt ? new Date(latest.createdAt).toLocaleString('vi-VN') : '',
      ];
    });
    const csv = [headers, ...rows].map(row => row.map(escapeCsv).join(',')).join('\r\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `imei-loi-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {/* Tab Selector */}
      <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
        {([
          ['returns', 'Yêu cầu đổi trả'],
          ['warranties', 'Yêu cầu bảo hành'],
          ['defective', 'Quản lý IMEI lỗi']
        ] as const).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setSection(id)}
            className={`rounded-xl px-5 py-2.5 text-xs font-bold transition-all ${
              section === id
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {message && (
        <div className="rounded-xl bg-rose-50 border border-rose-100 p-4 text-sm text-rose-850 font-medium">
          {message}
        </div>
      )}

      {/* Tables list */}
      {section !== 'defective' ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white shadow-sm">
          <table className="w-full text-left text-sm divide-y divide-slate-100">
            <thead>
              <tr className="bg-slate-50/50 text-slate-500 font-bold">
                <th className="p-4 text-xs uppercase tracking-wider">Mã hồ sơ</th>
                <th className="p-4 text-xs uppercase tracking-wider">Đơn hàng</th>
                <th className="p-4 text-xs uppercase tracking-wider">Sản phẩm cần xử lý</th>
                <th className="p-4 text-xs uppercase tracking-wider text-center">Trạng thái</th>
                <th className="p-4 text-xs uppercase tracking-wider">Hạn xử lý (SLA)</th>
                <th className="p-4 text-xs uppercase tracking-wider text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRequests.map(item => {
                const style = statusStyles[item.status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };
                const isOverSLA = item.slaBreachedAt || (item.slaDueAt && new Date(item.slaDueAt) < new Date());

                return (
                  <tr key={item.id} className="hover:bg-slate-50/50 transition-colors align-middle">
                    <td className="p-4 font-bold text-slate-900">{item.requestCode}</td>
                    <td className="p-4 text-slate-500 font-medium">#{item.orderCode}</td>
                    <td className="p-4">
                      {(item.items || []).map((line: any) => (
                        <div key={line.id} className="text-xs font-semibold text-slate-700">
                          {line.productName}
                          {line.imei && <span className="text-[10px] text-slate-400 font-normal ml-1">(IMEI: {line.imei})</span>}
                        </div>
                      ))}
                      {section === 'warranties' && item.repairSummary?.diagnosis && (
                        <div className="mt-1 rounded-lg bg-amber-50 px-2 py-1 text-[10px] font-semibold text-amber-800">
                          Chẩn đoán: {item.repairSummary.diagnosis}
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`inline-flex items-center rounded-lg px-2.5 py-0.5 text-xs font-bold border ${style.bg} ${style.text} ${style.border}`}>
                        {statusLabel[item.status] || item.status}
                      </span>
                      {section === 'returns' && item.inventoryDisposition && (
                        <div className="mt-1.5"><span className="inline-flex rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-violet-700">{inventoryDispositionLabels[item.inventoryDisposition] || item.inventoryDisposition}</span></div>
                      )}
                    </td>
                    <td className="p-4">
                      {isOverSLA ? (
                        <span className="text-xs font-bold text-rose-600 bg-rose-50 border border-rose-100 px-2 py-0.5 rounded-lg">Trễ SLA</span>
                      ) : item.slaDueAt ? (
                        <span className="text-xs text-slate-500 font-medium">{new Date(item.slaDueAt).toLocaleString('vi-VN')}</span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => void handleOpenDetailModal(item)}
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-650 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      >
                        Chi tiết
                      </button>
                      <div className="inline-flex gap-1.5">
                        {item.status === 'QC_IN_PROGRESS' && canInspectAfterSales ? (
                          <button
                            onClick={() => handleOpenAdvanceModal(item, 'QC_IN_PROGRESS')}
                            className="rounded-lg px-3 py-1.5 text-xs font-bold bg-blue-600 text-white hover:bg-blue-700 transition-all"
                          >
                            Đánh giá QC
                          </button>
                        ) : (
                          canUpdateAfterSales && (actions[item.status] || []).filter(status => status !== 'REFUND_PROCESSING' || canRefundAfterSales).filter(status => !['EXCHANGE_PROCESSING', 'REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'].includes(status) || canExchangeAfterSales).filter(status => status !== 'QC_IN_PROGRESS' || canInspectAfterSales).filter(status => canShowAfterSalesAction(section, item, status)).map(status => (
                            <button
                              key={status}
                              onClick={() => handleOpenAdvanceModal(item, status)}
                              className={`rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                                actionStyles[status] || 'bg-slate-800 text-white hover:bg-slate-750'
                              }`}
                            >
                              {status === 'QC_IN_PROGRESS'
                                ? (item.status === 'RECEIVED' ? 'Bắt đầu kiểm QC' : 'Đánh giá lại QC')
                                : (actionLabel[status] || status)}
                            </button>
                          ))
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!filteredRequests.length && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm font-medium text-slate-500">
                    {query.trim() ? `Không tìm thấy hồ sơ phù hợp với “${query.trim()}”.` : 'Chưa có hồ sơ trong nhóm này.'}
                  </td>
                </tr>
              )}
              {!requests.length && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-sm text-slate-400 font-medium">
                    Không tìm thấy yêu cầu hậu mãi nào.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* Defective IMEI identifiers tab */
        <div className="space-y-3">
          <section className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">Báo cáo hàng lỗi và giá trị thu hồi</h3>
                <p className="mt-1 text-xs font-semibold text-slate-500">Tổng hợp theo thiết bị vật lý, không cộng trùng IMEI và serial liên kết.</p>
              </div>
              <span className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
                Tỷ lệ thu hồi {recoveryRate}%
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Tổng thiết bị lỗi</div>
                <div className="mt-2 text-2xl font-extrabold text-slate-900">{Number(reportSummary.total || 0)}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">Đang xử lý: {Number(reportSummary.processing || 0)}</div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Đã định đoạt</div>
                <div className="mt-2 text-2xl font-extrabold text-slate-900">{Number(reportSummary.completed || 0)}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">Có chứng từ: {Number(reportSummary.documented || 0)}</div>
              </div>
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-emerald-700">Giá trị thu hồi</div>
                <div className="mt-2 text-lg font-extrabold text-emerald-800">{Number(reportSummary.recoveryValue || 0).toLocaleString('vi-VN')}đ</div>
                <div className="mt-1 text-xs font-semibold text-emerald-700">Có thu hồi: {Number(reportSummary.recovered || 0)}</div>
              </div>
              <div className="rounded-lg border border-rose-100 bg-rose-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-rose-700">Tổn thất ròng</div>
                <div className="mt-2 text-lg font-extrabold text-rose-800">{Number(reportSummary.netLossValue || 0).toLocaleString('vi-VN')}đ</div>
                <div className="mt-1 text-xs font-semibold text-rose-700">Vốn: {Number(reportSummary.inventoryValue || 0).toLocaleString('vi-VN')}đ</div>
              </div>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Theo trạng thái</div>
                <div className="space-y-2">
                  {reportByStatus.slice(0, 6).map((row: any) => (
                    <div key={row.status} className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-bold text-slate-700">{dispositionStatusLabels[row.status] || row.status}</span>
                      <span className="font-mono font-bold text-slate-900">{row.count}</span>
                    </div>
                  ))}
                  {!reportByStatus.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Brand lỗi nhiều</div>
                <div className="space-y-2">
                  {reportByBrand.slice(0, 6).map((row: any) => (
                    <div key={row.brandName} className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-bold text-slate-700">{row.brandName}</span>
                      <span className="font-mono font-bold text-slate-900">{row.count}</span>
                    </div>
                  ))}
                  {!reportByBrand.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Sản phẩm cần chú ý</div>
                <div className="space-y-2">
                  {reportTopProducts.slice(0, 5).map((row: any) => (
                    <div key={row.productId} className="text-xs">
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate font-bold text-slate-700">{row.productName}</span>
                        <span className="font-mono font-bold text-slate-900">{row.count}</span>
                      </div>
                      <div className="mt-0.5 text-[11px] font-semibold text-slate-400">
                        Tổn thất {Number(row.netLossValue || 0).toLocaleString('vi-VN')}đ
                      </div>
                    </div>
                  ))}
                  {!reportTopProducts.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
            </div>
          </section>

          <div className="flex flex-col gap-3 rounded-xl border border-slate-100 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-400">Tìm IMEI lỗi</label>
              <input
                value={defectiveQuery}
                onChange={event => setDefectiveQuery(event.target.value)}
                placeholder="IMEI, sản phẩm, chứng từ hoặc đối tác"
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm font-medium text-slate-700 outline-none transition-colors focus:border-slate-900 focus:bg-white"
              />
            </div>
            <div className="w-full md:w-64">
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-400">Trạng thái</label>
              <select
                value={defectiveStatusFilter}
                onChange={event => setDefectiveStatusFilter(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm font-bold text-slate-700 outline-none transition-colors focus:border-slate-900 focus:bg-white"
              >
                <option value="all">Tất cả trạng thái</option>
                {Object.entries(dispositionStatusLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              {([
                ['all', 'Tất cả', defectiveQuickCounts.all],
                ['processing', 'Đang xử lý', defectiveQuickCounts.processing],
                ['completed', 'Đã hoàn tất', defectiveQuickCounts.completed],
                ['documented', 'Có chứng từ', defectiveQuickCounts.documented],
                ['recovered', 'Có thu hồi', defectiveQuickCounts.recovered],
              ] as const).map(([value, label, count]) => (
                <button
                  key={value}
                  onClick={() => setDefectiveQuickFilter(value)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors ${
                    defectiveQuickFilter === value
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {label} <span className={defectiveQuickFilter === value ? 'text-white/70' : 'text-slate-400'}>{count}</span>
                </button>
              ))}
              {(defectiveQuery || defectiveStatusFilter !== 'all' || defectiveQuickFilter !== 'all') && (
                <button
                  onClick={() => {
                    setDefectiveQuery('');
                    setDefectiveStatusFilter('all');
                    setDefectiveQuickFilter('all');
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
                >
                  Xóa bộ lọc
                </button>
              )}
            </div>
            <button
              onClick={handleExportDefectiveCsv}
              disabled={!filteredDefective.length}
              className="w-full rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-350 lg:w-auto"
            >
              Xuất CSV
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Thiết bị lỗi</div>
              <div className="mt-2 text-2xl font-extrabold text-slate-900">{defectiveSummary.total}</div>
            </div>
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Giá trị vốn</div>
              <div className="mt-2 text-lg font-extrabold text-slate-900">{defectiveSummary.inventoryValue.toLocaleString('vi-VN')}đ</div>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-700">Thu hồi dự kiến</div>
              <div className="mt-2 text-lg font-extrabold text-emerald-800">{defectiveSummary.recoveryValue.toLocaleString('vi-VN')}đ</div>
            </div>
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Đã có chứng từ</div>
              <div className="mt-2 text-2xl font-extrabold text-slate-900">
                {defectiveSummary.documented}/{defectiveSummary.total}
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-400">Hoàn tất: {defectiveSummary.completed}</div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white shadow-sm">
            <table className="w-full text-left text-sm divide-y divide-slate-100">
              <thead>
                <tr className="bg-slate-50/50 text-slate-500 font-bold">
                  <th className="p-4 text-xs uppercase tracking-wider">IMEI / Serial lỗi</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Sản phẩm</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Trạng thái định đoạt</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Giá trị trung bình</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Chứng từ / thu hồi</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-right">Xử lý</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDefective.map(item => {
                  const latest = item.latestDisposition || {};
                  const recoveryValue = Number(latest.recoveryValue || 0);

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="p-4 font-mono font-bold text-slate-850">{item.identifier}</td>
                      <td className="p-4 font-medium text-slate-700">{item.productName}</td>
                      <td className="p-4">
                        <span className="inline-flex items-center rounded-lg bg-rose-50 border border-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-700">
                          {dispositionStatusLabels[item.status] || item.status}
                        </span>
                      </td>
                      <td className="p-4 text-slate-600 font-medium">
                        {Number(item.averageUnitCost || 0).toLocaleString('vi-VN')}đ
                      </td>
                      <td className="p-4 text-xs text-slate-600">
                        {latest.documentReference || latest.partnerName || recoveryValue > 0 ? (
                          <div className="space-y-0.5">
                            {latest.documentReference && <div className="font-mono font-bold text-slate-800">{latest.documentReference}</div>}
                            {latest.partnerName && <div>{latest.partnerName}</div>}
                            {recoveryValue > 0 && <div className="font-bold text-emerald-700">{recoveryValue.toLocaleString('vi-VN')}đ</div>}
                          </div>
) : '-'}
                      </td>
                      <td className="p-4 text-right">
                        {item.status === 'REPAIR_PENDING' ? (
                          canUpdateAfterSales ? (
                            <div className="flex flex-wrap justify-end gap-1.5">
                              <button
                                onClick={() => handleOpenDispositionModal(item, 'REPAIRED')}
                                className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition-colors hover:bg-emerald-100"
                              >
                                Xác nhận sửa xong
                              </button>
                              <button
                                onClick={() => handleOpenDispositionModal(item, 'RTV_COMPLETED')}
                                className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-bold text-rose-700 transition-colors hover:bg-rose-100"
                              >
                                Sửa không thành công
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs font-semibold text-amber-700">Máy cũ thu hồi đang sửa</span>
                          )
                        ) : item.status === 'REPAIRED' && item.usedIntake ? (
                          <button
                            type="button"
                            onClick={() => { setQuery?.(item.usedIntake.requestCode || item.identifier); setTab?.('usedProducts'); }}
                            className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-bold text-violet-700 transition-colors hover:bg-violet-100"
                          >
                            Mở hồ sơ {item.usedIntake.requestCode}
                          </button>
                        ) : item.status === 'REPAIRED' && item.type === 'IMEI' && canUpdateAfterSales && canManageUsedProducts ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void handleCreateRepairedUsedIntake(item)}
                            className="rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-bold text-violet-700 transition-colors hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Chuyển sang hàng cũ
                          </button>
                        ) : completedDispositionStatuses.includes(item.status) ? (
                          <span className="text-xs font-semibold text-emerald-700">Đã xử lý</span>
                        ) : canUpdateAfterSales ? (
                          <button
                            onClick={() => handleOpenDispositionModal(item)}
                            className="rounded-lg bg-slate-900 text-white px-3 py-1.5 text-xs font-bold hover:bg-slate-800 transition-colors"
                          >
                            Định đoạt
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
                {!filteredDefective.length && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-sm text-slate-400 font-medium">
                      {defective.length ? 'Không có IMEI lỗi khớp bộ lọc hiện tại.' : 'Không có danh sách IMEI lỗi cần xử lý.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= MODAL CẬP NHẬT TRẠNG THÁI (ADVANCE STATUS) ================= */}
      {showAdvanceModal && modalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-base font-extrabold text-slate-900">
              Cập nhật hồ sơ {modalRequest.requestCode}
            </h3>
            <p className="mt-1.5 text-xs text-slate-400 font-medium">
              Trạng thái hiện tại: <span className="underline font-bold text-slate-700">{statusLabel[modalRequest.status]}</span>
              {modalRequest.status !== 'QC_IN_PROGRESS' && (
                <>
                  {' '}| Chuyển sang: <span className="font-bold text-slate-900">{modalTargetStatus === 'QC_IN_PROGRESS'
                    ? (modalRequest.status === 'RECEIVED' ? 'Bắt đầu kiểm QC' : 'Đánh giá lại QC')
                    : actionLabel[modalTargetStatus]}</span>
                </>
              )}
            </p>

            <form onSubmit={handleConfirmAdvance} className="mt-5 space-y-4">
              {modalRequest.status === 'QC_IN_PROGRESS' ? (
                <div className="space-y-4 rounded-xl border border-blue-100 bg-blue-50/20 p-4">
                  <div className="text-xs font-bold uppercase tracking-wider text-blue-800 mb-2">Đánh giá QC Chuyên dụng</div>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Kết quả QC *</span>
                    <select
                      value={qcResult}
                      onChange={e => setQcResult(e.target.value)}
                      className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none bg-white"
                    >
                      {section === 'returns' ? (
                        <>
                          <option value="APPROVE_EXCHANGE">Đồng ý Đổi máy mới (EXCHANGE)</option>
                          <option value="APPROVE_REFUND">Đồng ý Hoàn tiền (REFUND)</option>
                          <option value="REJECT">Từ chối / Trả lại thiết bị cũ</option>
                        </>
                      ) : (
                        <>
                          <option value="ACCEPT_REPAIR">Đồng ý Nhận sửa chữa (REPAIR)</option>
                          <option value="APPROVE_REPLACEMENT">Đồng ý Đổi máy mới (REPLACEMENT)</option>
                          <option value="REJECT">Từ chối / Không bảo hành</option>
                        </>
                      )}
                    </select>
                  </label>

                  {section === 'warranties' && qcResult === 'ACCEPT_REPAIR' && (
                    <div className="grid gap-3 rounded-xl border border-amber-100 bg-amber-50/40 p-3 sm:grid-cols-2">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Kênh sửa chữa *</span>
                        <select value={repairChannel} onChange={event => setRepairChannel(event.target.value as 'INTERNAL' | 'MANUFACTURER')} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                          <option value="INTERNAL">Sửa máy bảo hành tại cửa hàng</option>
                          <option value="MANUFACTURER">Gửi máy bảo hành đến hãng</option>
                        </select>
                      </label>
                      {repairChannel === 'MANUFACTURER' && <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Hãng / trung tâm bảo hành *</span>
                        <input value={repairProviderName} onChange={event => setRepairProviderName(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Tên hãng hoặc trung tâm bảo hành" />
                      </label>}
                    </div>
                  )}

                  {section === 'warranties' && qcResult === 'APPROVE_REPLACEMENT' && (
                    <div className="space-y-3 rounded-xl border border-cyan-100 bg-cyan-50/40 p-3">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Cách giao máy thay thế *</span>
                        <select value={returnFulfillmentMethod} onChange={event => setReturnFulfillmentMethod(event.target.value as 'STORE_PICKUP' | 'DELIVERY')} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                          <option value="STORE_PICKUP">Khách nhận tại cửa hàng</option>
                          <option value="DELIVERY">Gửi máy đến khách</option>
                        </select>
                      </label>
                      {returnFulfillmentMethod === 'DELIVERY' && (
                        <div className="grid gap-3 sm:grid-cols-2">
                          <input aria-label="Tên người nhận máy thay thế" value={recipientName} onChange={event => setRecipientName(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Tên người nhận" />
                          <input aria-label="Số điện thoại người nhận máy thay thế" value={recipientPhone} onChange={event => setRecipientPhone(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Số điện thoại" />
                          <input aria-label="Địa chỉ giao máy thay thế" value={shippingAddress} onChange={event => setShippingAddress(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Địa chỉ giao máy" />
                          <input aria-label="Đơn vị vận chuyển máy thay thế" value={shippingProvider} onChange={event => setShippingProvider(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Đơn vị vận chuyển (tùy chọn)" />
                        </div>
                      )}
                    </div>
                  )}

                  <label className="flex items-center gap-2 py-1 select-none">
                    <input
                      type="checkbox"
                      checked={customerFault}
                      onChange={e => setCustomerFault(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                    />
                    <span className="text-sm font-semibold text-slate-700">Lỗi do khách hàng (Customer Fault)</span>
                  </label>

                  {section === 'returns' && (
                    <div className="grid gap-3 md:grid-cols-3">
                      <label className="flex flex-col gap-1.5 md:col-span-3">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Hướng xử lý thiết bị hoàn về *</span>
                        <select value={inventoryDisposition} onChange={e => setInventoryDisposition(e.target.value)} className="rounded-xl border border-slate-200 bg-white p-3 text-sm focus:border-slate-900 focus:outline-none">
                          <option value="USED_INTAKE">Chuyển sang kiểm định và bán hàng cũ</option>
                          <option value="NEW_STOCK">Đủ điều kiện nhập lại kho hàng mới</option>
                          <option value="REPAIR">Chuyển khu vực chờ sửa chữa / tân trang</option>
                          <option value="SCRAP">Không thể bán — chờ thanh lý / tiêu hủy</option>
                        </select>
                        <span className="text-xs text-slate-500">Chỉ chọn kho hàng mới khi thiết bị còn nguyên trạng và đủ điều kiện bán như mới.</span>
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Phí khấu hao</span>
                        <input
                          type="number"
                          min={0}
                          value={depreciationFee}
                          onChange={e => setDepreciationFee(e.target.value)}
                          placeholder="0"
                          className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                        />
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Khấu trừ ship</span>
                        <input
                          type="number"
                          min={0}
                          value={shippingDeduction}
                          onChange={e => setShippingDeduction(e.target.value)}
                          placeholder="0"
                          className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                        />
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Phí đổi máy</span>
                        <input
                          type="number"
                          min={0}
                          value={exchangeFee}
                          onChange={e => setExchangeFee(e.target.value)}
                          placeholder="Mặc định 5%"
                          className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                        />
                      </label>
                      <span className="md:col-span-3 text-[10px] text-slate-400">
                        Các khoản này được dùng để tính số tiền chênh lệch/hoàn lại sau QC. Để trống phí đổi máy nếu muốn dùng mức mặc định của hệ thống.
                      </span>
                    </div>
                  )}

                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đánh giá chất lượng / Chi tiết QC *</span>
                    <textarea
                      value={note}
                      onChange={e => setNote(e.target.value)}
                      placeholder="Nhập chẩn đoán tình trạng ngoại quan, linh kiện, khóa tài khoản... (Tối thiểu 10 ký tự)"
                      className="min-h-24 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                      required
                    />
                  </label>
                </div>
              ) : (
                <>
                  {(
                    (section === 'returns' && modalRequest?.resolutionType === 'EXCHANGE')
                    || (section === 'warranties' && modalRequest?.resolutionType === 'REPLACEMENT')
                  ) && (
                    <div className="rounded-xl border border-cyan-100 bg-cyan-50/40 p-4 text-sm text-cyan-950">
                      <div className="font-bold">Máy thay thế được xử lý tại phiếu xuất kho</div>
                      <p className="mt-1 text-xs leading-5 text-cyan-800">
                        Nhân viên kho sẽ tìm kiếm, chọn kệ và quét IMEI/serial khi đóng hàng. Hồ sơ hậu mãi tự nhận mã máy sau khi phiếu xuất hoàn tất.
                      </p>
                    </div>
                  )}
                  {needsReplacementIdentifiers(section, modalRequest, modalTargetStatus) && (
                    <div className="space-y-3 rounded-xl border border-cyan-100 bg-cyan-50/30 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="text-xs font-bold uppercase tracking-wider text-cyan-800">Chọn thiết bị thay thế trong kho</div>
                          <p className="mt-1 text-xs text-slate-500">Tìm theo IMEI hoặc serial; hệ thống tự lấy đúng cặp mã và vị trí kệ.</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void loadReplacementCandidates()}
                          disabled={replacementCandidatesLoading}
                          className="min-h-10 cursor-pointer rounded-lg border border-cyan-200 bg-white px-3 text-xs font-bold text-cyan-800 transition hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {replacementCandidatesLoading ? 'Đang tải thiết bị...' : 'Tải lại danh sách máy'}
                        </button>
                      </div>
                      {replacementCandidatesError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{replacementCandidatesError}</div>}
                      {(modalRequest.items || []).map((requestItem: any) => {
                        const draft = replacementIdentifiers[requestItem.id] || { imeis: '', serialNumbers: '' };
                        const selectedImeis = splitIdentifierValues(draft.imeis);
                        const selectedSerials = splitIdentifierValues(draft.serialNumbers);
                        const query = String(replacementSearch[requestItem.id] || '').trim().toLowerCase();
                        const candidates = replacementCandidates[requestItem.id] || [];
                        const visibleCandidates = candidates.filter(candidate => {
                          const selected = candidate.imeis.some(value => selectedImeis.includes(value))
                            || candidate.serialNumbers.some(value => selectedSerials.includes(value));
                          if (selected) return false;
                          const searchable = [
                            ...candidate.imeis,
                            candidate.secondaryImei || '',
                            ...candidate.serialNumbers,
                            candidate.locationCode || '',
                            candidate.locationName || '',
                          ].join(' ').toLowerCase();
                          return !query || searchable.includes(query);
                        }).slice(0, 12);
                        const selectedCount = Math.max(selectedImeis.length, selectedSerials.length);
                        return (
                          <div key={requestItem.id} className="space-y-3 rounded-xl border border-slate-200 bg-white p-3">
                            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                              <div className="text-sm font-bold text-slate-900">{requestItem.productName}</div>
                              <span className={`text-xs font-bold ${selectedCount === Number(requestItem.quantity || 1) ? 'text-emerald-700' : 'text-amber-700'}`}>
                                Đã chọn {selectedCount}/{requestItem.quantity}
                              </span>
                            </div>
                            {selectedCount > 0 && (
                              <div className="space-y-2">
                                {Array.from({ length: selectedCount }).map((_, index) => (
                                  <div key={`${selectedImeis[index] || ''}:${selectedSerials[index] || ''}`} className="flex min-h-11 items-center justify-between gap-3 rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2">
                                    <div className="min-w-0 text-xs">
                                      {selectedSerials[index] && <div className="font-mono font-bold text-slate-900">Serial: {selectedSerials[index]}</div>}
                                      {selectedImeis[index] && <div className="font-mono text-slate-600">IMEI: {selectedImeis[index]}</div>}
                                    </div>
                                    <button type="button" onClick={() => removeReplacementCandidate(requestItem, index)} className="min-h-9 cursor-pointer rounded-lg border border-red-200 bg-white px-3 text-xs font-bold text-red-700 hover:bg-red-50">Bỏ chọn</button>
                                  </div>
                                ))}
                              </div>
                            )}
                            <div className="relative">
                              <label htmlFor={`replacement-search-${requestItem.id}`} className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-500">Tìm máy khả dụng</label>
                              <input
                                id={`replacement-search-${requestItem.id}`}
                                type="search"
                                value={replacementSearch[requestItem.id] || ''}
                                onFocus={() => { if (!Object.keys(replacementCandidates).length) void loadReplacementCandidates(); }}
                                onChange={event => setReplacementSearch(current => ({ ...current, [requestItem.id]: event.target.value }))}
                                placeholder="Nhập IMEI hoặc serial để tìm..."
                                className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
                              />
                            </div>
                            <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-1">
                              {replacementCandidatesLoading ? (
                                <div className="px-3 py-6 text-center text-xs font-semibold text-slate-500">Đang tải danh sách thiết bị...</div>
                              ) : visibleCandidates.length ? visibleCandidates.map(candidate => (
                                <button
                                  key={candidate.key}
                                  type="button"
                                  onClick={() => selectReplacementCandidate(requestItem, candidate)}
                                  disabled={selectedCount >= Number(requestItem.quantity || 1)}
                                  className="flex min-h-12 w-full cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-xs transition hover:bg-cyan-50 focus:bg-cyan-50 focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
                                >
                                  <span className="min-w-0">
                                    {candidate.serialNumbers[0] && <span className="block font-mono font-bold text-slate-900">Serial: {candidate.serialNumbers[0]}</span>}
                                    {candidate.imeis[0] && <span className="block font-mono text-slate-600">IMEI: {candidate.imeis[0]}{candidate.secondaryImei ? ` · IMEI 2: ${candidate.secondaryImei}` : ''}</span>}
                                  </span>
                                  <span className="shrink-0 text-[11px] font-semibold text-slate-500">{candidate.locationCode || 'Chưa rõ kệ'}</span>
                                </button>
                              )) : (
                                <div className="px-3 py-6 text-center text-xs text-slate-500">
                                  {Object.keys(replacementCandidates).length ? 'Không tìm thấy máy khả dụng phù hợp.' : 'Nhấn vào ô tìm kiếm để tải danh sách máy.'}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                      <span className="block text-xs text-slate-500">Chỉ hiển thị thiết bị `IN_STOCK` tại kệ thật; kho tổng `MAIN` và mã không đồng bộ bị loại khỏi danh sách.</span>
                    </div>
                  )}

                  {/* Ghi chú xử lý */}
                  {section === 'returns' && (modalTargetStatus === 'REFUND_PROCESSING' || (modalTargetStatus === 'COMPLETED' && modalRequest.status === 'REFUND_PROCESSING')) && (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Phí khấu hao / nhập lại</label>
                      <input
                        type="number"
                        min={0}
                        value={depreciationFee}
                        onChange={(event) => setDepreciationFee(event.target.value)}
                        placeholder="0"
                        className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                      />
                      <span className="text-[10px] text-slate-400">Khoản phí này được dùng để tính số tiền hoàn trong hồ sơ.</span>
                    </div>
                  )}

                  {section === 'returns' && modalTargetStatus === 'COMPLETED' && modalRequest.status === 'REFUND_PROCESSING' && (
                    <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-3">
                      <div className="mb-3 text-xs font-bold uppercase tracking-wider text-emerald-800">Chứng từ hoàn tiền</div>
                      <p className="mb-3 text-xs leading-5 text-emerald-900/70">
                        Luồng này chỉ ghi nhận mã giao dịch/chứng từ để phục vụ đối soát, không gọi API hoàn tiền.
                      </p>
                      <div className="space-y-3">
                        <label className="flex flex-col gap-1.5">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã giao dịch / chứng từ *</span>
                          <input
                            value={refundTransactionRef}
                            onChange={e => setRefundTransactionRef(e.target.value)}
                            placeholder="Ví dụ: REF-DEMO-20260705-001, biên nhận nội bộ..."
                            className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            required
                          />
                        </label>
                        <label className="flex flex-col gap-1.5">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Link chứng từ demo *</span>
                          <input
                            value={refundProofUrl}
                            onChange={e => setRefundProofUrl(e.target.value)}
                            placeholder="URL ảnh/PDF chứng từ demo"
                            className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            required
                          />
                        </label>
                        <label className="flex flex-col gap-1.5">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ghi chú hoàn tiền</span>
                          <textarea
                            value={refundNote}
                            onChange={e => setRefundNote(e.target.value)}
                            placeholder="Ghi chú đối soát hoặc kênh hoàn tiền"
                            className="min-h-16 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                          />
                        </label>
                      </div>
                    </div>
                  )}

                  {section === 'warranties' && modalRequest.resolutionType === 'REPLACEMENT' && ['REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'].includes(modalTargetStatus) && (
                    <div className="space-y-3 rounded-xl border border-cyan-100 bg-cyan-50/40 p-3">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Cách giao máy thay thế *</span>
                        <select value={returnFulfillmentMethod} onChange={event => setReturnFulfillmentMethod(event.target.value as 'STORE_PICKUP' | 'DELIVERY')} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                          <option value="STORE_PICKUP">Khách nhận tại cửa hàng</option>
                          <option value="DELIVERY">Gửi máy đến khách</option>
                        </select>
                      </label>
                      {returnFulfillmentMethod === 'DELIVERY' && (
                        <div className="grid gap-3 sm:grid-cols-2">
                          <input aria-label="Tên người nhận máy thay thế" value={recipientName} onChange={event => setRecipientName(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Tên người nhận" />
                          <input aria-label="Số điện thoại nhận máy thay thế" value={recipientPhone} onChange={event => setRecipientPhone(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Số điện thoại" />
                          <input aria-label="Địa chỉ giao máy thay thế" value={shippingAddress} onChange={event => setShippingAddress(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Địa chỉ giao máy" />
                          <input aria-label="Đơn vị vận chuyển máy thay thế" value={shippingProvider} onChange={event => setShippingProvider(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Đơn vị vận chuyển (tùy chọn)" />
                        </div>
                      )}
                    </div>
                  )}

                  {section === 'warranties' && modalRequest.resolutionType === 'REPAIR' && modalTargetStatus === 'REPAIRING' && (
                    <div className="grid gap-3 rounded-xl border border-amber-100 bg-amber-50/40 p-3 sm:grid-cols-2">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Kênh sửa chữa *</span>
                        <select value={repairChannel} onChange={event => setRepairChannel(event.target.value as 'INTERNAL' | 'MANUFACTURER')} className="rounded-xl border border-slate-200 bg-white p-3 text-sm">
                          <option value="INTERNAL">Sửa máy bảo hành tại cửa hàng</option>
                          <option value="MANUFACTURER">Gửi máy bảo hành đến hãng</option>
                        </select>
                      </label>
                      {repairChannel === 'MANUFACTURER' && <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Hãng / trung tâm bảo hành *</span>
                        <input value={repairProviderName} onChange={event => setRepairProviderName(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Tên hãng hoặc trung tâm bảo hành" />
                      </label>}
                    </div>
                  )}

                  {section === 'warranties' && modalRequest.resolutionType === 'REPAIR' && modalTargetStatus === 'RETURNING_TO_CUSTOMER' && (
                    <div className="grid gap-3 rounded-xl border border-blue-100 bg-blue-50/40 p-3 sm:grid-cols-2">
                      <input aria-label="Tên người nhận máy đã sửa" value={recipientName} onChange={event => setRecipientName(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Tên người nhận" />
                      <input aria-label="Số điện thoại nhận máy đã sửa" value={recipientPhone} onChange={event => setRecipientPhone(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm" placeholder="Số điện thoại" />
                      <input aria-label="Địa chỉ giao máy đã sửa" value={shippingAddress} onChange={event => setShippingAddress(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Địa chỉ giao máy" />
                      <input aria-label="Đơn vị vận chuyển máy đã sửa" value={shippingProvider} onChange={event => setShippingProvider(event.target.value)} className="rounded-xl border border-slate-200 p-3 text-sm sm:col-span-2" placeholder="Đơn vị vận chuyển (tùy chọn)" />
                    </div>
                  )}

                  {section === 'warranties'
                    && modalRequest.resolutionType === 'REPAIR'
                    && ['READY_TO_RETURN', 'RETURNING_TO_CUSTOMER', 'COMPLETED'].includes(modalTargetStatus)
                    && modalRequest.repairSummary
                    && Object.keys(modalRequest.repairSummary).length > 0 && (
                    <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-3 text-xs text-slate-700">
                      <div className="font-bold uppercase tracking-wider text-emerald-800">Kết quả sửa chữa đã lưu</div>
                      <div className="mt-2 space-y-1">
                        <div><strong>Chẩn đoán:</strong> {modalRequest.repairSummary.diagnosis || '-'}</div>
                        <div><strong>Hướng xử lý:</strong> {modalRequest.repairSummary.action || '-'}</div>
                      </div>
                    </div>
                  )}

                  {requiresCustomerReceiptConfirmation && (
                    <label className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-sm text-emerald-950">
                      <input
                        type="checkbox"
                        checked={customerReceiptConfirmed}
                        onChange={event => setCustomerReceiptConfirmed(event.target.checked)}
                        className="mt-0.5 h-4 w-4 rounded border-emerald-300"
                      />
                      <span>
                        <strong className="block">Xác nhận khách đã nhận máy</strong>
                        Hệ thống sẽ ghi người thao tác và thời gian xác nhận vào timeline hậu mãi.
                      </span>
                    </label>
                  )}

                  {section === 'warranties'
                    && modalRequest.resolutionType === 'REPAIR'
                    && modalTargetStatus === 'REPAIR_COMPLETED' && (
                    <div className="rounded-xl border border-amber-100 bg-amber-50/40 p-3">
                      <div className="mb-3 text-xs font-bold uppercase tracking-wider text-amber-800">Chi tiết sửa chữa / bảo hành</div>
                      <div className="space-y-3">
                        <label className="flex flex-col gap-1.5">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chẩn đoán lỗi *</span>
                          <textarea
                            value={repairDiagnosis}
                            onChange={e => setRepairDiagnosis(e.target.value)}
                            placeholder="Ví dụ: lỗi main, mất nguồn, pin chai, lỗi màn hình..."
                            className="min-h-16 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            required={modalRequest.resolutionType === 'REPAIR'}
                          />
                        </label>
                        <label className="flex flex-col gap-1.5">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Hướng xử lý *</span>
                          <textarea
                            value={repairAction}
                            onChange={e => setRepairAction(e.target.value)}
                            placeholder="Sửa chữa, thay linh kiện, vệ sinh, cập nhật phần mềm, trả máy..."
                            className="min-h-16 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            required={modalRequest.resolutionType === 'REPAIR'}
                          />
                        </label>
                        <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
                          <label className="flex flex-col gap-1.5">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Linh kiện / vật tư</span>
                            <input
                              value={repairParts}
                              onChange={e => setRepairParts(e.target.value)}
                              placeholder="Pin, màn hình, cáp sạc..."
                              className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            />
                          </label>
                          <label className="flex flex-col gap-1.5">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chi phí</span>
                            <input
                              type="number"
                              min={0}
                              value={repairCost}
                              onChange={e => setRepairCost(e.target.value)}
                              placeholder="0"
                              className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                            />
                          </label>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ghi chú Xử lý (Nội bộ)</label>
                    <textarea
                      value={note}
                      onChange={e => setNote(e.target.value)}
                      placeholder="Điền thông tin ghi chú cho hành động này (tùy chọn)"
                      className="min-h-24 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                    />
                  </div>
                </>
              )}

              {/* Action buttons */}
              <div className="mt-6 flex justify-end gap-3.5 border-t border-slate-50 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAdvanceModal(false)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-500 hover:bg-slate-50 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {busy ? 'Đang cập nhật...' : (modalRequest.status === 'QC_IN_PROGRESS' ? 'Xác nhận Kết quả QC' : 'Xác nhận Chuyển')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL XEM CHI TIẾT HỒ SƠ & MINH CHỨNG ================= */}
      {showDetailModal && detailRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl border border-slate-100 flex flex-col max-h-[85vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-50 pb-3 shrink-0">
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">Chi tiết Hồ sơ Hậu mãi</h3>
                <p className="text-xs text-slate-400 mt-0.5">Mã yêu cầu: <span className="font-mono font-bold">{detailRequest.requestCode}</span></p>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="h-8 w-8 rounded-full hover:bg-slate-50 flex items-center justify-center text-slate-400 hover:text-slate-800 transition-colors text-lg"
              >
                ×
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="mt-4 flex-1 overflow-y-auto space-y-6 pr-1">

              {/* Thông tin đơn hàng & Khách hàng */}
              <div className="grid gap-4 sm:grid-cols-2 bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-xs">
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Mã Đơn hàng</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">#{detailRequest.orderCode}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Trạng thái hiện tại</span>
                  <p className="mt-0.5">
                    <span className={`inline-flex items-center rounded-lg px-2 py-0.5 text-[10px] font-bold border ${
                      statusStyles[detailRequest.status]?.bg || 'bg-slate-50'
                    } ${statusStyles[detailRequest.status]?.text || 'text-slate-700'} ${
                      statusStyles[detailRequest.status]?.border || 'border-slate-200'
                    }`}>
                      {statusLabel[detailRequest.status] || detailRequest.status}
                    </span>
                  </p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Ngày gửi yêu cầu</span>
                  <p className="font-semibold text-slate-700 mt-0.5">{new Date(detailRequest.createdAt).toLocaleString('vi-VN')}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Thời hạn xử lý (SLA)</span>
                  <p className="font-semibold text-slate-700 mt-0.5">
                    {detailRequest.slaDueAt ? new Date(detailRequest.slaDueAt).toLocaleString('vi-VN') : '-'}
                  </p>
                </div>
              </div>

              {(detailRequest.fulfillmentOrder || detailRequest.fulfillmentOutbound) && (
                <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-xs">
                  <div className="font-bold uppercase tracking-wider text-cyan-700">Giao máy hậu mãi</div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {detailRequest.fulfillmentOrder && (
                      <div className="rounded-lg border border-cyan-100 bg-white p-3">
                        <div className="text-slate-500">Đơn giao máy</div>
                        <div className="mt-0.5 font-mono font-bold text-slate-900">{detailRequest.fulfillmentOrder.orderCode}</div>
                        <div className="mt-1 font-semibold text-cyan-700">{detailRequest.fulfillmentOrder.status}</div>
                      </div>
                    )}
                    {detailRequest.fulfillmentOutbound && (
                      <div className="rounded-lg border border-cyan-100 bg-white p-3">
                        <div className="text-slate-500">Phiếu xuất kho</div>
                        <div className="mt-0.5 font-mono font-bold text-slate-900">{detailRequest.fulfillmentOutbound.documentNo}</div>
                        <div className="mt-1 font-semibold text-cyan-700">{detailRequest.fulfillmentOutbound.status}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {section === 'returns' && detailRequest.inventoryDisposition && (
                <div className="rounded-xl border border-violet-200 bg-violet-50 p-4 text-xs">
                  <div className="font-bold uppercase tracking-wider text-violet-700">Hướng xử lý tồn kho</div>
                  <div className="mt-1 text-sm font-bold text-slate-900">{inventoryDispositionLabels[detailRequest.inventoryDisposition] || detailRequest.inventoryDisposition}</div>
                  {detailRequest.inventoryDestination ? (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-violet-100 bg-white p-3">
                      <div>
                        <div className="text-slate-500">Chứng từ / hồ sơ liên quan</div>
                        <div className="mt-0.5 font-mono font-bold text-slate-900">{detailRequest.inventoryDestination.referenceCode}</div>
                        <div className="mt-0.5 text-[10px] font-semibold text-slate-500">Trạng thái: {detailRequest.inventoryDestination.status}</div>
                      </div>
                      <button type="button" onClick={() => { setShowDetailModal(false); setQuery?.(detailRequest.inventoryDestination.referenceCode || ''); setTab?.(detailRequest.inventoryDestination.type === 'USED_INTAKE' ? 'usedProducts' : 'inventory'); }} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-bold text-white hover:bg-violet-800">
                        {detailRequest.inventoryDestination.type === 'USED_INTAKE' ? 'Mở quản lý hàng cũ' : 'Mở chứng từ kho'}
                      </button>
                    </div>
                  ) : <div className="mt-2 text-violet-700">Hệ thống đang chờ tạo hồ sơ hoặc chứng từ liên quan.</div>}
                </div>
              )}

              {/* Sản phẩm lỗi */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Sản phẩm cần kiểm QC</h4>
                <div className="divide-y divide-slate-100 rounded-xl border border-slate-100 px-4 py-1">
                  {(detailRequest.items || []).map((line: any) => (
                    <div key={line.id} className="py-3 flex justify-between items-center text-xs">
                      <div>
                        <p className="font-bold text-slate-800">{line.productName}</p>
                         <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-slate-400">
                           {line.imei && <span>IMEI: <strong>{line.imei}</strong></span>}
                           {line.serialNumber && <span>Serial: <strong>{line.serialNumber}</strong></span>}
                         </div>
                         {((line.replacementImeis || []).length > 0 || (line.replacementSerialNumbers || []).length > 0) && (
                           <div className="mt-2 rounded-lg bg-emerald-50 px-2 py-1.5 text-[10px] text-emerald-800">
                             {(line.replacementImeis || []).length > 0 && (
                               <div>IMEI thay thế: <strong>{line.replacementImeis.join(', ')}</strong></div>
                             )}
                             {(line.replacementSecondaryImeis || []).length > 0 && (
                               <div>IMEI2 thay thế: <strong>{line.replacementSecondaryImeis.join(', ')}</strong></div>
                             )}
                             {(line.replacementSerialNumbers || []).length > 0 && (
                               <div>Serial thay thế: <strong>{line.replacementSerialNumbers.join(', ')}</strong></div>
                             )}
                           </div>
                         )}
                       </div>
                      <div className="text-right font-semibold text-slate-500">
                        Số lượng: {line.quantity}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mô tả của khách */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Mô tả tình trạng lỗi từ khách hàng</h4>
                <div className="text-xs leading-relaxed text-slate-700 bg-amber-50/20 border border-amber-100 rounded-xl p-4">
                  {detailRequest.reason}
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Timeline xử lý</h4>
                <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                  <div className="mb-4 rounded-xl border border-slate-200 bg-white p-3">
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-slate-500">Thêm ghi chú timeline</label>
                    <textarea
                      value={timelineNote}
                      onChange={event => setTimelineNote(event.target.value)}
                      placeholder="Ghi nhận cuộc gọi, hẹn lịch, yêu cầu bổ sung ảnh, cập nhật kỹ thuật..."
                      className="min-h-16 w-full rounded-lg border border-slate-200 p-2 text-xs text-slate-700 focus:border-slate-900 focus:outline-none"
                    />
                    <div className="mt-2 flex justify-end">
                      <button
                        type="button"
                        onClick={() => void handleAddTimelineNote()}
                        disabled={timelineNote.trim().length < 3 || timelineNoteBusy}
                        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {timelineNoteBusy ? 'Đang thêm...' : 'Thêm ghi chú'}
                      </button>
                    </div>
                  </div>
                  {detailEventsLoading ? (
                    <div className="text-xs font-semibold text-slate-500">Đang tải timeline...</div>
                  ) : detailEvents.length === 0 ? (
                    <div className="text-xs font-semibold text-slate-500">Chưa có sự kiện xử lý.</div>
                  ) : (
                    <div className="space-y-3">
                      {detailEvents.map((event) => {
                        const repair = event.metadata?.repair;
                        return (
                          <div key={event.id} className="border-l-2 border-slate-300 pl-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="text-xs font-bold text-slate-800">
                                {event.oldStatus ? `${statusLabel[event.oldStatus] || event.oldStatus} → ` : ''}
                                {statusLabel[event.newStatus] || event.newStatus}
                              </div>
                              <div className="text-[10px] font-semibold text-slate-400">
                                {event.createdAt ? new Date(event.createdAt).toLocaleString('vi-VN') : '-'}
                              </div>
                            </div>
                            <div className="mt-1 text-[11px] font-semibold text-slate-500">
                              {event.actorName || 'Hệ thống'}{event.note ? ` · ${event.note}` : ''}
                            </div>
                            {event.metadata?.customerReceiptConfirmed && (
                              <div className="mt-2 inline-flex rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-800">
                                Admin đã xác nhận khách nhận máy
                              </div>
                            )}
                            {repair && (
                              <div className="mt-2 rounded-lg border border-amber-100 bg-white px-3 py-2 text-[11px] text-slate-700">
                                {repair.diagnosis && <div><strong>Chẩn đoán:</strong> {repair.diagnosis}</div>}
                                {repair.action && <div><strong>Hướng xử lý:</strong> {repair.action}</div>}
                                {repair.parts && <div><strong>Linh kiện:</strong> {repair.parts}</div>}
                                {Number(repair.cost || 0) > 0 && <div><strong>Chi phí:</strong> {Number(repair.cost || 0).toLocaleString('vi-VN')}đ</div>}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {section === 'warranties' && detailRequest.resolutionType === 'REPAIR' && (
                <div className="grid gap-3 rounded-xl border border-amber-100 bg-amber-50/40 p-4 sm:grid-cols-2">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Kênh sửa chữa</div>
                    <div className="mt-1 text-sm font-bold text-slate-900">{detailRequest.repairChannel === 'MANUFACTURER' ? 'Gửi máy bảo hành đến hãng' : 'Sửa máy bảo hành tại cửa hàng'}</div>
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Đơn vị xử lý</div>
                    <div className="mt-1 text-sm font-bold text-slate-900">{detailRequest.repairProviderName || 'Cửa hàng'}</div>
                  </div>
                </div>
              )}

              {section === 'warranties' && detailRequest.repairSummary && Object.keys(detailRequest.repairSummary).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Chi tiết sửa chữa / bảo hành</h4>
                  <div className="grid gap-3 rounded-xl border border-amber-100 bg-amber-50/30 p-4 text-xs sm:grid-cols-2">
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Chẩn đoán</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.diagnosis || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Hướng xử lý</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.action || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Linh kiện</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.parts || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Chi phí</span>
                      <p className="mt-1 font-semibold text-slate-800">{Number(detailRequest.repairSummary.cost || 0).toLocaleString('vi-VN')}đ</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Trình duyệt Minh chứng (Hình ảnh/Video đính kèm) */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Tệp đính kèm / Minh chứng</h4>

                {(detailRequest.attachments || []).length > 0 ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(detailRequest.attachments || []).map((attachment: any) => {
                      const url = resolveAttachmentUrl(attachment.url);
                      const name = attachment.originalName || attachment.name || 'Tệp minh chứng';
                      const size = formatAttachmentSize(attachment.sizeBytes);

                      return (
                        <a
                          key={attachment.id || attachment.url}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="group overflow-hidden rounded-xl border border-slate-200 bg-white text-left shadow-sm transition hover:border-slate-300 hover:shadow-md"
                        >
                          <div className="flex aspect-video items-center justify-center bg-slate-50">
                            {isImageAttachment(attachment.contentType) ? (
                              <img src={url} alt={name} className="h-full w-full object-cover" />
                            ) : isVideoAttachment(attachment.contentType) ? (
                              <div className="flex flex-col items-center gap-2 text-slate-500">
                                <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                <span className="text-[11px] font-bold">Video minh chứng</span>
                              </div>
                            ) : (
                              <div className="flex flex-col items-center gap-2 text-slate-500">
                                <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                </svg>
                                <span className="text-[11px] font-bold">Tệp đính kèm</span>
                              </div>
                            )}
                          </div>
                          <div className="p-3">
                            <div className="truncate text-xs font-bold text-slate-800" title={name}>{name}</div>
                            <div className="mt-1 flex items-center justify-between gap-2 text-[10px] font-semibold text-slate-400">
                              <span>{attachment.contentType || 'Không rõ định dạng'}</span>
                              {size && <span>{size}</span>}
                            </div>
                            <div className="mt-2 text-[10px] font-bold text-slate-500 group-hover:text-slate-900">Mở tệp minh chứng</div>
                          </div>
                        </a>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/70 p-4 text-center text-xs font-medium text-slate-400">
                    Khách hàng chưa gửi tệp minh chứng cho hồ sơ này.
                  </div>
                )}
              </div>

              {/* Lịch sử nhật ký xử lý của admin */}
              {detailRequest.adminNote && (
                <div>
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Ghi chú xử lý nội bộ của Admin</h4>
                  <div className="text-xs leading-relaxed text-slate-700 bg-slate-50 border border-slate-200 rounded-xl p-4">
                    {detailRequest.adminNote}
                  </div>
                </div>
              )}
            </div>

            {/* Footer buttons */}
            <div className="mt-5 border-t border-slate-100 pt-4 flex justify-between items-center shrink-0">
              <div className="flex gap-1">
                {detailRequest.status === 'QC_IN_PROGRESS' ? (
                  <button
                    onClick={() => {
                      handleOpenAdvanceModal(detailRequest, 'QC_IN_PROGRESS');
                    }}
                    className="rounded-xl px-3 py-2 text-xs font-bold bg-blue-600 text-white hover:bg-blue-700 transition-all"
                  >
                    Đánh giá QC
                  </button>
                ) : (
                  canUpdateAfterSales && (actions[detailRequest.status] || [])
                    .filter(status => status !== 'REFUND_PROCESSING' || canRefundAfterSales)
                    .filter(status => !['EXCHANGE_PROCESSING', 'REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'].includes(status) || canExchangeAfterSales)
                    .filter(status => status !== 'QC_IN_PROGRESS' || canInspectAfterSales)
                    .filter(status => canShowAfterSalesAction(section, detailRequest, status))
                    .map(status => (
                    <button
                      key={status}
                      onClick={() => {
                        handleOpenAdvanceModal(detailRequest, status);
                      }}
                      className={`rounded-xl px-3 py-2 text-xs font-bold transition-all ${
                        actionStyles[status] || 'bg-slate-800 text-white'
                      }`}
                    >
                      {status === 'QC_IN_PROGRESS'
                        ? (detailRequest.status === 'RECEIVED' ? 'Bắt đầu kiểm QC' : 'Đánh giá lại QC')
                        : actionLabel[status]}
                    </button>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={() => setShowDetailModal(false)}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-550 hover:bg-slate-50 transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL ĐỊNH ĐOẠT IMEI LỖI (DISPOSITION) ================= */}
      {showDispositionModal && selectedDefective && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-base font-extrabold text-slate-900">
              Xử lý định đoạt IMEI: {selectedDefective.identifier}
            </h3>
            <p className="mt-1 text-xs text-slate-400 font-medium">Sản phẩm: {selectedDefective.productName}</p>

            <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
              <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Lịch sử định đoạt</div>
              {dispositionEventsLoading ? (
                <div className="text-xs font-semibold text-slate-500">Đang tải lịch sử...</div>
              ) : dispositionEvents.length === 0 ? (
                <div className="text-xs font-semibold text-slate-500">Chưa có lịch sử định đoạt.</div>
              ) : (
                <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
                  {dispositionEvents.map((event) => (
                    <div key={event.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-bold text-slate-800">
                          {event.oldStatus ? `${dispositionStatusLabels[event.oldStatus] || event.oldStatus} → ` : ''}
                          {dispositionStatusLabels[event.newStatus] || event.newStatus}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400">
                          {event.createdAt ? new Date(event.createdAt).toLocaleString('vi-VN') : '-'}
                        </span>
                      </div>
                      <div className="mt-1 text-slate-600">{event.reason}</div>
                      <div className="mt-1 font-semibold text-indigo-700">Người thao tác: {adminActorLabel(event).name}{adminActorLabel(event).role ? ` · ${adminActorLabel(event).role}` : ''}</div>
                      {(event.documentReference || event.partnerName || Number(event.recoveryValue || 0) > 0) && (
                        <div className="mt-1 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-500">
                          {event.documentReference && <span>Chứng từ: {event.documentReference}</span>}
                          {event.partnerName && <span>Đối tác: {event.partnerName}</span>}
                          {Number(event.recoveryValue || 0) > 0 && <span className="text-emerald-700">Thu hồi: {Number(event.recoveryValue || 0).toLocaleString('vi-VN')}đ</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <form onSubmit={handleConfirmDisposition} className="mt-5 space-y-4">
              {/* Trạng thái định đoạt */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chọn Trạng thái định đoạt *</label>
                <select
                  value={dispStatus}
                  onChange={e => setDispStatus(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
                  required
                >
                  {(selectedDefective.status === 'REPAIR_PENDING' ? REPAIR_RESULT_ACTIONS : INITIAL_DEFECTIVE_ACTIONS).map(status => (
                    <option key={status} value={status}>
                      {dispositionStatusLabels[status] || status}
                    </option>
                  ))}
                </select>
              </div>

              {/* Tài liệu tham chiếu */}
              {!['REPAIR_PENDING', 'REPAIRED'].includes(dispStatus) && <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chứng từ / Tài liệu tham chiếu</label>
                <input
                  type="text"
                  value={docRef}
                  onChange={e => setDocRef(e.target.value)}
                  placeholder="Mã phiếu xuất/hóa đơn thanh lý"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>}

              {/* Tên đối tác */}
              {!['REPAIR_PENDING', 'REPAIRED'].includes(dispStatus) && <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đối tác thu hồi / Thanh lý</label>
                <input
                  type="text"
                  value={partner}
                  onChange={e => setPartner(e.target.value)}
                  placeholder="Tên đối tác hoặc nhà phân phối"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>}

              {/* Giá trị thu hồi */}
              {['RTV_COMPLETED', 'LIQUIDATED'].includes(dispStatus) && <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Giá trị thu hồi (VNĐ)</label>
                <input
                  type="number"
                  value={recoveryVal}
                  onChange={e => setRecoveryVal(e.target.value)}
                  placeholder="Số tiền thu về (nếu có)"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>}

              {/* Lý do định đoạt */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ghi chú</label>
                <textarea
                  value={dispReason}
                  onChange={e => setDispReason(e.target.value)}
                  placeholder={dispStatus === 'REPAIRED' ? 'Ghi nhận kết quả sửa chữa' : 'Mô tả lý do định đoạt và kết quả kiểm định'}
                  className="min-h-20 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>

              {/* Action buttons */}
              <div className="mt-6 flex justify-end gap-3 border-t border-slate-55 pt-4">
                <button
                  type="button"
                  onClick={() => setShowDispositionModal(false)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-500 hover:bg-slate-50 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {busy ? 'Đang cập nhật...' : 'Xác nhận xử lý'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
