import React, { useEffect, useState } from 'react';
import { Check, ClipboardList, Download, Eye, X } from 'lucide-react';
import { AdminPanel, AdminTable, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { compactId, currency, getInventorySettings } from '../../admin-shell/components/AdminDashboardConfig';
import { adminInventoryApi } from '../services/adminInventoryApi';

type AdminInventoryTabProps = Record<string, any>;
type StockCountDraft = {
  referenceCode: string;
  reason: string;
  note: string;
  lines: Array<{
    key: string;
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    expectedQuantity: number;
    countedQuantity: number;
    note: string;
  }>;
};
type AdjustmentDraft = {
  referenceCode: string;
  reason: string;
  note: string;
  line: {
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    currentQuantity: number;
    newQuantity: number;
    reason: string;
    note: string;
  };
};
type LocationDraft = {
  id?: string;
  code: string;
  name: string;
  zone: string;
  purpose: string;
  sortOrder: number;
  allowMixedSku: boolean;
  lengthCm: number | '';
  widthCm: number | '';
  heightCm: number | '';
  usableRatio: number | '';
  description: string;
};

const locationPurposeOptions: [string, string][] = [
  ['STORAGE', 'Lưu hàng bán'],
  ['QC', 'Kiểm tra / cách ly'],
  ['WARRANTY', 'Bảo hành'],
  ['DAMAGED', 'Hàng lỗi'],
  ['RETURN', 'Hàng trả'],
  ['VIRTUAL', 'Vị trí hệ thống'],
];

function locationPurposeLabel(value: string) {
  return locationPurposeOptions.find(([key]) => key === value)?.[1] || value || '-';
}

function identifierStatusLabel(status: string) {
  const labels: Record<string, string> = {
    PENDING_INBOUND: 'Chờ nhập kho',
    IN_STOCK: 'Còn trong kho',
    RESERVED: 'Đang giữ',
    SOLD: 'Đã bán',
    IN_WARRANTY: 'Đang bảo hành',
    WARRANTY: 'Đang bảo hành',
    SCRAP: 'Loại bỏ',
    RETIRED: 'Ngừng sử dụng',
    REVERSED: 'Đã đảo phiếu',
  };
  return labels[status] || status || '-';
}

function stockStateLabel(state: string, blockSaleWhenOutOfStock = true) {
  if (state === 'AVAILABLE') return 'Có thể bán';
  if (state === 'RESERVED') return 'Đang giữ hàng';
  if (state === 'UNAVAILABLE') return 'Không khả dụng';
  return blockSaleWhenOutOfStock ? 'Khóa bán khi hết' : 'Hết hàng';
}

function transactionTypeLabel(type: string) {
  const labels: Record<string, string> = {
    RECEIPT: 'Nhập kho',
    SALE: 'Xuất bán',
    ADJUSTMENT: 'Điều chỉnh/Kiểm kê',
    RETURN: 'Hoàn hàng',
    REVERSAL: 'Đảo phiếu',
  };
  return labels[type] || type || '-';
}

function renderIdentifierSummary(row: any) {
  if (!row.tracksImei && !row.tracksSerialNumber) return 'Không quản lý mã định danh';
  const summary = row.imeiSummary || {};
  const serialSummary = row.serialNumberSummary || {};
  const parts = [];
  if (row.tracksImei) {
    const primary = row.primaryImei ? `chính ${row.primaryImei}` : 'chưa có IMEI chính';
    parts.push(`IMEI: ${primary}; phụ ${row.supplementalImei || 0}; trong kho ${summary.inStock || 0} / giữ ${summary.reserved || 0} / đã bán ${summary.sold || 0}`);
  }
  if (row.tracksSerialNumber) {
    parts.push(`Serial: trong kho ${serialSummary.inStock || 0} / giữ ${serialSummary.reserved || 0} / đã bán ${serialSummary.sold || 0}`);
  }
  return parts.join(' | ');
}

export default function AdminInventoryTab(props: AdminInventoryTabProps) {
  const [identifierModal, setIdentifierModal] = useState<{ row: any; data: any } | null>(null);
  const [issueSuggestionModal, setIssueSuggestionModal] = useState<{ row: any; quantity: number; suggestions: any[] } | null>(null);
  const [identifierLoading, setIdentifierLoading] = useState(false);
  const [pendingEditRequests, setPendingEditRequests] = useState<any[]>([]);
  const [stockCounts, setStockCounts] = useState<any[]>([]);
  const [stockCountDraft, setStockCountDraft] = useState<StockCountDraft | null>(null);
  const [stockCountDetail, setStockCountDetail] = useState<any | null>(null);
  const [selectedStockCountKeys, setSelectedStockCountKeys] = useState<string[]>([]);
  const [stockCountLoading, setStockCountLoading] = useState(false);
  const [adjustments, setAdjustments] = useState<any[]>([]);
  const [adjustmentDraft, setAdjustmentDraft] = useState<AdjustmentDraft | null>(null);
  const [adjustmentDetail, setAdjustmentDetail] = useState<any | null>(null);
  const [locationDraft, setLocationDraft] = useState<LocationDraft | null>(null);
  const [inventoryView, setInventoryView] = useState<'stock' | 'ledger' | 'locations'>('stock');
  const [locationSearchFilter, setLocationSearchFilter] = useState('');
  const [locationZoneFilter, setLocationZoneFilter] = useState('');
  const [locationPurposeFilter, setLocationPurposeFilter] = useState('');
  const [locationStatusFilter, setLocationStatusFilter] = useState('');
  const [locationAisleFilter, setLocationAisleFilter] = useState('');
  const [locationShelfFilter, setLocationShelfFilter] = useState('');
  const [locationBinFilter, setLocationBinFilter] = useState('');
  const {
    categories,
    exportInventorySnapshot,
    filteredInventory,
    inventoryDashboard,
    inventoryPage,
    inventoryTotal,
    inventoryTotalPages,
    inventoryLocations,
    inventoryLedger,
    ledgerPage,
    ledgerTotal,
    ledgerTotalPages,
    inventoryStockFilter,
    setInventoryStockFilter,
    inventoryLocationFilter,
    setInventoryLocationFilter,
    ledgerDateFrom,
    setLedgerDateFrom,
    ledgerDateTo,
    setLedgerDateTo,
    ledgerTransactionType,
    setLedgerTransactionType,
    loadInventoryLedger,
    loadInventoryLocations,
    applyInventoryAdvancedFilters,
    clearInventoryAdvancedFilters,
    applyInventoryLedgerFilters,
    clearInventoryLedgerFilters,
    inventoryBrandFilter,
    inventoryBrandOptions,
    inventoryCategoryFilter,
    loadInventoryLevels,
    query,
    setInventoryBrandFilter,
    setInventoryCategoryFilter,
    setQuery,
    usePermission,
    isSuperAdmin,
  } = props;
  const canAdjustInventory = usePermission('inventory:adjust');
  const canCountInventory = usePermission('inventory:count');
  const canApproveInventory = isSuperAdmin || usePermission('inventory:approve');
  const locationZoneOptions = Array.from(
    new Set((inventoryLocations || []).map((location: any) => String(location.zone || '').trim()).filter(Boolean)),
  ).sort((first, second) => String(first).localeCompare(String(second), 'vi')) as string[];
  const locationAisleOptions = Array.from(
    new Set((inventoryLocations || [])
      .map((location: any) => String(location.code || '').match(/^([A-Z])-\d{2}-\d{2}$/)?.[1] || '')
      .filter(Boolean)),
  ).sort();
  const locationShelfOptions = Array.from(
    new Set((inventoryLocations || [])
      .filter((location: any) => !locationAisleFilter || String(location.code || '').startsWith(`${locationAisleFilter}-`))
      .map((location: any) => String(location.code || '').match(/^[A-Z]-(\d{2})-\d{2}$/)?.[1] || '')
      .filter(Boolean)),
  ).sort();
  const locationBinOptions = Array.from(
    new Set((inventoryLocations || [])
      .filter((location: any) => !locationAisleFilter || String(location.code || '').startsWith(`${locationAisleFilter}-`))
      .filter((location: any) => !locationShelfFilter || String(location.code || '').slice(2, 4) === locationShelfFilter)
      .map((location: any) => String(location.code || '').match(/^[A-Z]-\d{2}-(\d{2})$/)?.[1] || '')
      .filter(Boolean)),
  ).sort();

  async function loadPendingEditRequests() {
    const rows = await adminInventoryApi.adminListIdentifierEditRequests('PENDING').catch(() => []);
    setPendingEditRequests(Array.isArray(rows) ? rows : []);
  }

  async function loadStockCounts() {
    const rows = await adminInventoryApi.adminListStockCounts(query || '').catch(() => []);
    setStockCounts(Array.isArray(rows) ? rows : []);
  }

  async function loadAdjustments() {
    const rows = await adminInventoryApi.adminListAdjustments(query || '').catch(() => []);
    setAdjustments(Array.isArray(rows) ? rows : []);
  }

  async function submitLocationDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!locationDraft) return;
    if (!locationDraft.code.trim() || !locationDraft.name.trim()) {
      window.alert('Vui lòng nhập mã kệ và tên kệ.');
      return;
    }
    const payload = {
      code: locationDraft.code.trim(),
      name: locationDraft.name.trim(),
      zone: locationDraft.zone.trim() || null,
      purpose: locationDraft.purpose || 'STORAGE',
      sortOrder: Math.max(0, Number(locationDraft.sortOrder || 0)),
      allowMixedSku: Boolean(locationDraft.allowMixedSku),
      lengthCm: locationDraft.lengthCm === '' ? null : Number(locationDraft.lengthCm || 0),
      widthCm: locationDraft.widthCm === '' ? null : Number(locationDraft.widthCm || 0),
      heightCm: locationDraft.heightCm === '' ? null : Number(locationDraft.heightCm || 0),
      usableRatio: locationDraft.usableRatio === '' ? 0.75 : Math.min(1, Math.max(0.01, Number(locationDraft.usableRatio || 0.75))),
      description: locationDraft.description.trim() || null,
    };
    if (locationDraft.id) {
      await adminInventoryApi.adminUpdateLocation(locationDraft.id, payload);
    } else {
      await adminInventoryApi.adminCreateLocation(payload);
    }
    setLocationDraft(null);
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  async function toggleLocationStatus(location: any) {
    const isActive = String(location.status || 'ACTIVE') === 'ACTIVE';
    if (isActive && !window.confirm(`Khóa kệ ${location.code}? Kệ còn tồn kho sẽ bị hệ thống từ chối.`)) return;
    await adminInventoryApi.adminUpdateLocationStatus(String(location.id), { isActive: !isActive });
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  async function applyLocationFilters() {
    if (typeof loadInventoryLocations !== 'function') return;
    await loadInventoryLocations(locationSearchFilter.trim(), {
      zone: locationZoneFilter,
      purpose: locationPurposeFilter,
      status: locationStatusFilter,
      aisle: locationAisleFilter,
      shelf: locationShelfFilter,
      bin: locationBinFilter,
    });
  }

  async function clearLocationFilters() {
    setLocationSearchFilter('');
    setLocationZoneFilter('');
    setLocationPurposeFilter('');
    setLocationStatusFilter('');
    setLocationAisleFilter('');
    setLocationShelfFilter('');
    setLocationBinFilter('');
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations('', {});
  }

  useEffect(() => {
    void loadPendingEditRequests();
    void loadStockCounts();
    void loadAdjustments();
    if (typeof loadInventoryLocations === 'function') void loadInventoryLocations();
    if (typeof loadInventoryLedger === 'function') void loadInventoryLedger(query);
  }, []);

  async function openIdentifierModal(row: any) {
    setIdentifierLoading(true);
    try {
      const data = await adminInventoryApi.adminListIdentifiers(row.productId, row.variantId || null);
      setIdentifierModal({ row, data });
    } finally {
      setIdentifierLoading(false);
    }
  }

  async function openIssueSuggestionModal(row: any) {
    const rawQuantity = window.prompt('Nhập số lượng cần gợi ý xuất kho:', '1');
    if (!rawQuantity) return;
    const quantity = Math.max(1, Number(rawQuantity || 1));
    const suggestions = await adminInventoryApi.adminListIssueSuggestions(row.productId, row.variantId || null, quantity).catch(() => []);
    setIssueSuggestionModal({ row, quantity, suggestions: Array.isArray(suggestions) ? suggestions : [] });
  }

  async function requestIdentifierEdit(identifierType: 'IMEI' | 'SERIAL', item: any) {
    const label = identifierType === 'IMEI' ? 'IMEI' : 'serial number';
    const newValue = window.prompt(`Nhập ${label} đúng:`)?.trim();
    if (!newValue) return;
    const reason = window.prompt('Nhập lý do chỉnh sửa mã định danh:')?.trim();
    if (!reason) return;
    await adminInventoryApi.adminCreateIdentifierEditRequest({
      identifierType,
      identifierId: item.id,
      newValue,
      reason,
    });
    await loadPendingEditRequests();
    if (identifierModal?.row) await openIdentifierModal(identifierModal.row);
  }

  async function decideIdentifierEdit(requestId: string, decision: 'APPROVED' | 'CANCELLED') {
    const note = window.prompt(decision === 'APPROVED' ? 'Ghi chú duyệt (không bắt buộc):' : 'Lý do hủy yêu cầu (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminDecideIdentifierEditRequest(requestId, { decision, note });
    await loadPendingEditRequests();
    if (identifierModal?.row) await openIdentifierModal(identifierModal.row);
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  function renderRequestProductName(request: any) {
    const variantText = [request.variantSku, request.variantColor, request.variantConfiguration].filter(Boolean).join(' - ');
    return `${request.productName || 'Sản phẩm'}${variantText ? ` / ${variantText}` : ''}`;
  }

  function generateStockCountCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `KK${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  }

  function generateAdjustmentCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `DC${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  }

  function openAdjustmentDraft(item: any) {
    const currentQuantity = Number(item.physicalStock ?? item.stock ?? item.stockQuantity ?? 0);
    setAdjustmentDraft({
      referenceCode: generateAdjustmentCode(),
      reason: 'DIEU_CHINH_THU_CONG',
      note: '',
      line: {
        productId: String(item.productId || item.id),
        variantId: item.variantId ? String(item.variantId) : null,
        productName: String(item.productName || item.name || ''),
        sku: String(item.variantSku || item.productSku || item.sku || compactId(item.productId || item.id)),
        currentQuantity,
        newQuantity: currentQuantity,
        reason: '',
        note: '',
      },
    });
  }

  function inventoryItemKey(item: any) {
    return `${item.productId || item.id}-${item.variantId || 'base'}`;
  }

  function inventoryItemToStockCountLine(item: any): StockCountDraft['lines'][number] | null {
    const productId = item.productId || item.id;
    if (!productId) return null;
    const expectedQuantity = Number(item.physicalStock ?? item.stock ?? item.stockQuantity ?? 0);
    return {
      key: inventoryItemKey(item),
      productId: String(productId),
      variantId: item.variantId ? String(item.variantId) : null,
      productName: String(item.productName || item.name || ''),
      sku: String(item.variantSku || item.productSku || item.sku || compactId(productId)),
      expectedQuantity,
      countedQuantity: expectedQuantity,
      note: '',
    };
  }

  function stockCountEligibleRows(rows = filteredInventory) {
    return rows
      .filter((item: any) => 'physicalStock' in item || 'availableStock' in item)
      .map(inventoryItemToStockCountLine)
      .filter(Boolean) as StockCountDraft['lines'];
  }

  function openStockCountDraftFromRows(rows: StockCountDraft['lines'], scopeLabel: string) {
    if (!rows.length) {
      window.alert('Không có dòng tồn kho để tạo phiếu kiểm kê.');
      return;
    }
    setStockCountDraft({
      referenceCode: generateStockCountCode(),
      reason: 'KIEM_KE_DINH_KY',
      note: scopeLabel,
      lines: rows,
    });
  }

  function openSelectedStockCountDraft() {
    const selectedKeys = new Set(selectedStockCountKeys);
    const rows = stockCountEligibleRows().filter((line) => selectedKeys.has(line.key));
    if (!rows.length) {
      window.alert('Vui lòng chọn ít nhất một dòng tồn kho để kiểm kê.');
      return;
    }
    openStockCountDraftFromRows(rows, `Kiểm kê theo danh sách đã chọn (${rows.length} dòng).`);
  }

  async function openAllStockCountDraft() {
    setStockCountLoading(true);
    try {
      const pageSize = 100;
      const first = await adminInventoryApi.adminListLevels(
        String(query || '').trim(),
        inventoryStockFilter,
        inventoryLocationFilter,
        inventoryCategoryFilter,
        inventoryBrandFilter,
        1,
        pageSize,
      ).catch(() => ({ items: [], totalPages: 1 }));
      const allItems = Array.isArray(first?.items) ? [...first.items] : [];
      const totalPages = Math.max(1, Number(first?.totalPages || 1));
      for (let page = 2; page <= totalPages; page += 1) {
        const result = await adminInventoryApi.adminListLevels(
          String(query || '').trim(),
          inventoryStockFilter,
          inventoryLocationFilter,
          inventoryCategoryFilter,
          inventoryBrandFilter,
          page,
          pageSize,
        ).catch(() => ({ items: [] }));
        if (Array.isArray(result?.items)) allItems.push(...result.items);
      }
      const rows = stockCountEligibleRows(allItems);
      openStockCountDraftFromRows(rows, `Kiểm kê toàn bộ theo bộ lọc hiện tại (${rows.length} dòng).`);
    } finally {
      setStockCountLoading(false);
    }
  }

  function toggleStockCountSelection(key: string) {
    setSelectedStockCountKeys((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  function toggleCurrentPageStockCountSelection() {
    const pageKeys = stockCountEligibleRows().map((line) => line.key);
    const selected = new Set(selectedStockCountKeys);
    const allSelected = pageKeys.length > 0 && pageKeys.every((key) => selected.has(key));
    setSelectedStockCountKeys(allSelected ? selectedStockCountKeys.filter((key) => !pageKeys.includes(key)) : Array.from(new Set([...selectedStockCountKeys, ...pageKeys])));
  }

  function updateStockCountLine(key: string, patch: Partial<StockCountDraft['lines'][number]>) {
    setStockCountDraft((current) => current ? {
      ...current,
      lines: current.lines.map((line) => line.key === key ? { ...line, ...patch } : line),
    } : current);
  }

  async function submitStockCountDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!stockCountDraft) return;
    await adminInventoryApi.adminCreateStockCount({
      referenceCode: stockCountDraft.referenceCode.trim(),
      reason: stockCountDraft.reason.trim() || 'KIEM_KE_DINH_KY',
      note: stockCountDraft.note.trim() || null,
      locationCode: 'MAIN',
      locationName: 'Kho chính',
      lines: stockCountDraft.lines.map((line) => ({
        productId: line.productId,
        variantId: line.variantId,
        expectedQuantity: line.expectedQuantity,
        countedQuantity: Math.max(0, Number(line.countedQuantity || 0)),
        note: line.note.trim() || null,
      })),
    });
    setStockCountDraft(null);
    await loadStockCounts();
  }

  async function decideStockCount(referenceCode: string, status: 'APPROVED' | 'CANCELLED') {
    const note = window.prompt(status === 'APPROVED' ? 'Ghi chú duyệt kiểm kê (không bắt buộc):' : 'Lý do hủy phiếu kiểm kê (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminUpdateStockCountStatus(referenceCode, { status, note });
    await loadStockCounts();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  async function submitAdjustmentDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!adjustmentDraft) return;
    if (!adjustmentDraft.line.reason.trim()) {
      window.alert('Vui lòng nhập lý do điều chỉnh tồn.');
      return;
    }
    await adminInventoryApi.adminCreateAdjustment({
      referenceCode: adjustmentDraft.referenceCode.trim(),
      reason: adjustmentDraft.reason.trim() || 'DIEU_CHINH_THU_CONG',
      note: adjustmentDraft.note.trim() || null,
      locationCode: 'MAIN',
      locationName: 'Kho chính',
      lines: [{
        productId: adjustmentDraft.line.productId,
        variantId: adjustmentDraft.line.variantId,
        currentQuantity: adjustmentDraft.line.currentQuantity,
        newQuantity: Math.max(0, Number(adjustmentDraft.line.newQuantity || 0)),
        reason: adjustmentDraft.line.reason.trim(),
        note: adjustmentDraft.line.note.trim() || null,
      }],
    });
    setAdjustmentDraft(null);
    await loadAdjustments();
  }

  async function decideAdjustment(referenceCode: string, status: 'APPROVED' | 'CANCELLED') {
    const note = window.prompt(status === 'APPROVED' ? 'Ghi chú duyệt điều chỉnh (không bắt buộc):' : 'Lý do hủy phiếu điều chỉnh (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminUpdateAdjustmentStatus(referenceCode, { status, note });
    await loadAdjustments();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  function renderIdentifierRows(identifierType: 'IMEI' | 'SERIAL', rows: any[]) {
    if (!rows.length) {
      return (
        <tr>
          <td colSpan={6} className="px-4 py-3 text-sm text-slate-500">Chưa có mã.</td>
        </tr>
      );
    }
    return rows.map((item) => (
      <tr key={`${identifierType}-${item.id}`}>
        <td className="px-4 py-3 font-mono text-xs text-slate-800">{item.value}</td>
        <td className="px-4 py-3 text-xs text-slate-600">{identifierStatusLabel(String(item.status || ''))}</td>
        <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.locationName || item.locationCode || '-'}</td>
        <td className="px-4 py-3 text-xs text-slate-600">{item.sourceReference || '-'}</td>
        <td className="px-4 py-3 text-xs text-slate-600">
          {item.pendingRequestId ? (
            <div className="space-y-1">
              <div className="font-semibold text-amber-700">Chờ duyệt: {item.pendingNewValue}</div>
              <div>{item.pendingReason}</div>
            </div>
          ) : 'Không có'}
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-2">
            {!item.pendingRequestId ? (
              <button type="button" onClick={() => void requestIdentifierEdit(identifierType, item)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                Sửa
              </button>
            ) : (
              <>
                <button type="button" onClick={() => void decideIdentifierEdit(item.pendingRequestId, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                  <Check className="h-3.5 w-3.5" /> Duyệt
                </button>
                <button type="button" onClick={() => void decideIdentifierEdit(item.pendingRequestId, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                  <X className="h-3.5 w-3.5" /> Hủy
                </button>
              </>
            )}
          </div>
        </td>
      </tr>
    ));
  }

  function renderEditRequestRows(rows: any[], compact = false) {
    if (!rows.length) {
      return (
        <tr>
          <td colSpan={compact ? 5 : 6} className="px-4 py-3 text-sm text-slate-500">Chưa có yêu cầu.</td>
        </tr>
      );
    }
    return rows.map((item) => (
      <tr key={item.id}>
        {!compact && <td className="px-4 py-3 text-sm font-semibold text-slate-800">{renderRequestProductName(item)}</td>}
        <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.identifierType}</td>
        <td className="px-4 py-3 font-mono text-xs text-slate-700">{item.currentValue}</td>
        <td className="px-4 py-3 font-mono text-xs text-slate-900">{item.newValue}</td>
        <td className="px-4 py-3 text-xs text-slate-600">
          <div className="space-y-1">
            <div>{item.reason}</div>
            {item.status !== 'PENDING' && (
              <div className="text-slate-500">
                {item.status === 'APPROVED' ? 'Đã duyệt' : 'Đã hủy'}
                {item.decisionNote ? ` - ${item.decisionNote}` : ''}
              </div>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          {item.status === 'PENDING' ? (
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => void decideIdentifierEdit(item.id, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                <Check className="h-3.5 w-3.5" /> Duyệt
              </button>
              <button type="button" onClick={() => void decideIdentifierEdit(item.id, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                <X className="h-3.5 w-3.5" /> Hủy
              </button>
            </div>
          ) : (
            <span className="text-xs font-semibold text-slate-500">{item.status === 'APPROVED' ? 'Đã duyệt' : 'Đã hủy'}</span>
          )}
        </td>
      </tr>
    ));
  }

  const currentPageStockCountLines = stockCountEligibleRows();
  const currentPageStockCountKeys = currentPageStockCountLines.map((line) => line.key);
  const selectedStockCountKeySet = new Set(selectedStockCountKeys);
  const currentPageStockCountAllSelected = currentPageStockCountKeys.length > 0 && currentPageStockCountKeys.every((key) => selectedStockCountKeySet.has(key));

  return (
    <AdminPanel
      title="Quản lý tồn kho"
      action={
        <div className="flex flex-wrap gap-2">
          {canCountInventory && (
            <>
              <button type="button" onClick={openSelectedStockCountDraft} disabled={selectedStockCountKeys.length === 0 || stockCountLoading} className="inline-flex h-10 items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 text-sm font-bold text-emerald-700 shadow-sm transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50">
                <ClipboardList className="h-4 w-4" /> Kiểm kê đã chọn ({selectedStockCountKeys.length})
              </button>
              <button type="button" onClick={() => void openAllStockCountDraft()} disabled={stockCountLoading} className="inline-flex h-10 items-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 text-sm font-bold text-emerald-700 shadow-sm transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50">
                <ClipboardList className="h-4 w-4" /> {stockCountLoading ? 'Đang tải...' : 'Kiểm kê toàn bộ'}
              </button>
            </>
          )}
          <button type="button" onClick={() => void exportInventorySnapshot()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50">
            <Download className="h-4 w-4" /> Xuất
          </button>
        </div>
      }
    >
      <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        <button
          type="button"
          onClick={() => setInventoryView('ledger')}
          className={`h-9 rounded-lg px-4 text-sm font-bold transition ${inventoryView === 'ledger' ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
        >
          Sổ kho
        </button>
        <button
          type="button"
          onClick={() => setInventoryView('stock')}
          className={`h-9 rounded-lg px-4 text-sm font-bold transition ${inventoryView === 'stock' ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
        >
          Tồn kho
        </button>
        <button
          type="button"
          onClick={() => setInventoryView('locations')}
          className={`h-9 rounded-lg px-4 text-sm font-bold transition ${inventoryView === 'locations' ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
        >
          Kệ hàng
        </button>
      </div>
      <div className={inventoryView === 'stock' ? 'contents' : 'hidden'}>
      <section className="mb-4 grid gap-3 xl:grid-cols-[420px_1fr]">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-bold uppercase text-slate-500">Tổng SKU theo dõi</div>
            <div className="mt-2 text-2xl font-black text-slate-900">{inventoryDashboard?.totalSku || 0}</div>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-bold uppercase text-amber-700">Sản phẩm sắp hết</div>
            <div className="mt-2 text-2xl font-black text-amber-900">{inventoryDashboard?.lowStockCount || 0}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-bold uppercase text-slate-500">Giá trị tồn kho</div>
            <div className="mt-2 text-xl font-black text-slate-900">{currency.format(Number(inventoryDashboard?.inventoryValue || 0))}</div>
          </div>
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            <div className="text-xs font-bold uppercase text-indigo-700">SKU đang giữ hàng</div>
            <div className="mt-2 text-2xl font-black text-indigo-900">{inventoryDashboard?.reservedSkuCount || 0}</div>
          </div>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="mb-3 text-sm font-bold text-slate-900">Top tồn nhiều</div>
            <div className="space-y-2">
              {(inventoryDashboard?.topStock || []).slice(0, 5).map((item: any) => (
                <div key={`${item.productId}-${item.variantId || 'base'}`} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-800">{item.productName}</div>
                    {(item.variantColor || item.variantConfiguration) && (
                      <div className="truncate text-xs font-semibold text-slate-500">
                        {[item.variantColor, item.variantConfiguration].filter(Boolean).join(' · ')}
                      </div>
                    )}
                  </div>
                  <span className="font-bold text-slate-900">{item.physicalStock || 0}</span>
                </div>
              ))}
              {(inventoryDashboard?.topStock || []).length === 0 && <div className="text-sm font-semibold text-slate-500">Chưa có dữ liệu.</div>}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="mb-3 text-sm font-bold text-slate-900">Top cần nhập thêm</div>
            <div className="space-y-2">
              {(inventoryDashboard?.topNeedRestock || []).slice(0, 5).map((item: any) => (
                <div key={`${item.productId}-${item.variantId || 'base'}`} className="flex items-center justify-between gap-3 rounded-lg bg-amber-50 px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-800">{item.productName}</div>
                    {(item.variantColor || item.variantConfiguration) && (
                      <div className="truncate text-xs font-semibold text-slate-500">
                        {[item.variantColor, item.variantConfiguration].filter(Boolean).join(' · ')}
                      </div>
                    )}
                  </div>
                  <span className="font-bold text-amber-800">Còn {item.availableStock || 0} / min {item.minimumStock || 0}</span>
                </div>
              ))}
              {(inventoryDashboard?.topNeedRestock || []).length === 0 && <div className="text-sm font-semibold text-slate-500">Không có hàng sắp hết.</div>}
            </div>
          </div>
        </div>
      </section>
      <div className="mb-5 flex flex-wrap items-stretch gap-3 rounded-2xl border border-slate-200/60 bg-slate-50/70 p-3.5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)] sm:items-center">
        <Select noLabel={true} label="Danh mục" value={inventoryCategoryFilter} onChange={setInventoryCategoryFilter} options={[['', 'Tất cả danh mục'], ...categories.map((c: any) => [String(c.id), c.parentName ? `${c.parentName} / ${c.name}` : c.name] as [string, string])]} />
        <Select noLabel={true} label="Thương hiệu" value={inventoryBrandFilter} onChange={setInventoryBrandFilter} options={inventoryBrandOptions} />
        <Select noLabel={true} label="Tồn kho" value={inventoryStockFilter || ''} onChange={setInventoryStockFilter} options={[['', 'Tất cả tồn kho'], ['LOW', 'Hàng sắp hết'], ['IN_STOCK', 'Còn tồn'], ['RESERVED', 'Đang giữ']]} />
        <Select
          noLabel={true}
          label="Kệ hàng"
          value={inventoryLocationFilter || ''}
          onChange={setInventoryLocationFilter}
          options={[
            ['', 'Tất cả kệ hàng'],
            ...(inventoryLocations || []).map((location: any) => [String(location.code), `${location.code} - ${location.name}`] as [string, string]),
          ]}
        />
        <button type="button" onClick={() => void applyInventoryAdvancedFilters()} className="h-10 rounded-xl border border-indigo-200 bg-indigo-50 px-3 text-sm font-bold text-indigo-700 transition hover:bg-indigo-100">
          Lọc tồn
        </button>
        {(inventoryStockFilter || inventoryLocationFilter) && (
          <button type="button" onClick={() => void clearInventoryAdvancedFilters()} className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-600 transition hover:bg-slate-50">
            Xóa lọc tồn
          </button>
        )}
        <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, trạng thái kho" />
      </div>
      </div>

      <section className={`${inventoryView === 'locations' ? '' : 'hidden'} mb-4 rounded-xl border border-slate-200 bg-white p-4`}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-bold text-slate-900">Danh mục kệ hàng</div>
            <div className="text-xs font-semibold text-slate-500">Chuẩn hóa vị trí lưu kho để nhập, lọc tồn và truy vết IMEI/serial.</div>
          </div>
          <button
            type="button"
            onClick={() => setLocationDraft({ code: '', name: '', zone: 'Kho chính', purpose: 'STORAGE', sortOrder: 0, allowMixedSku: true, lengthCm: 100, widthCm: 60, heightCm: 40, usableRatio: 0.75, description: '' })}
            className="h-9 rounded-lg border border-emerald-200 bg-emerald-50 px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-100"
          >
            Thêm kệ
          </button>
        </div>
        <div className="mb-4 grid gap-2 md:grid-cols-4 xl:grid-cols-8">
          <input
            value={locationSearchFilter}
            onChange={(event) => setLocationSearchFilter(event.target.value)}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm text-slate-800"
            placeholder="Tìm mã, tên, khu"
          />
          <Select
            noLabel={true}
            label="Dãy"
            value={locationAisleFilter}
            onChange={(value) => {
              setLocationAisleFilter(value);
              setLocationShelfFilter('');
              setLocationBinFilter('');
            }}
            options={[['', 'Tất cả dãy'], ...locationAisleOptions.map((value) => [value, `Dãy ${value}`] as [string, string])]}
          />
          <Select
            noLabel={true}
            label="Kệ"
            value={locationShelfFilter}
            onChange={(value) => {
              setLocationShelfFilter(value);
              setLocationBinFilter('');
            }}
            options={[['', 'Tất cả kệ'], ...locationShelfOptions.map((value) => [value, `Kệ ${value}`] as [string, string])]}
          />
          <Select
            noLabel={true}
            label="Ô"
            value={locationBinFilter}
            onChange={setLocationBinFilter}
            options={[['', 'Tất cả ô'], ...locationBinOptions.map((value) => [value, `Ô ${value}`] as [string, string])]}
          />
          <Select
            noLabel={true}
            label="Khu vực"
            value={locationZoneFilter}
            onChange={setLocationZoneFilter}
            options={[['', 'Tất cả khu'], ...locationZoneOptions.map((value) => [value, value] as [string, string])]}
          />
          <Select
            noLabel={true}
            label="Loại"
            value={locationPurposeFilter}
            onChange={setLocationPurposeFilter}
            options={[['', 'Tất cả loại'], ...locationPurposeOptions]}
          />
          <Select
            noLabel={true}
            label="Trạng thái"
            value={locationStatusFilter}
            onChange={setLocationStatusFilter}
            options={[['', 'Tất cả trạng thái'], ['ACTIVE', 'Đang dùng'], ['INACTIVE', 'Đã khóa']]}
          />
          <div className="flex gap-2">
            <button type="button" onClick={() => void applyLocationFilters()} className="h-10 flex-1 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 hover:bg-indigo-100">
              Lọc
            </button>
            {(locationSearchFilter || locationZoneFilter || locationPurposeFilter || locationStatusFilter || locationAisleFilter || locationShelfFilter || locationBinFilter) && (
              <button type="button" onClick={() => void clearLocationFilters()} className="h-10 flex-1 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 hover:bg-slate-50">
                Xóa
              </button>
            )}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2">Mã kệ</th>
                <th className="px-3 py-2">Tên kệ</th>
                <th className="px-3 py-2">Khu vực</th>
                <th className="px-3 py-2">Loại</th>
                <th className="px-3 py-2">Thứ tự</th>
                <th className="px-3 py-2">Kích thước</th>
                <th className="px-3 py-2">Trộn SKU</th>
                <th className="px-3 py-2">SKU</th>
                <th className="px-3 py-2">Tồn</th>
                <th className="px-3 py-2">Trạng thái</th>
                <th className="px-3 py-2">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(inventoryLocations || []).map((location: any) => {
                const isActive = String(location.status || 'ACTIVE') === 'ACTIVE';
                return (
                  <tr key={location.id}>
                    <td className="px-3 py-2 font-mono font-bold text-slate-800">{location.code}</td>
                    <td className="px-3 py-2 font-semibold text-slate-800">{location.name}</td>
                    <td className="px-3 py-2 text-slate-600">{location.zone || '-'}</td>
                    <td className="px-3 py-2 text-slate-600">{locationPurposeLabel(String(location.purpose || 'STORAGE'))}</td>
                    <td className="px-3 py-2 text-slate-600">{location.sortOrder || 0}</td>
                    <td className="px-3 py-2 text-slate-600">
                      {location.lengthCm && location.widthCm && location.heightCm
                        ? `${location.lengthCm} x ${location.widthCm} x ${location.heightCm} cm`
                        : '-'}
                      {location.capacityVolumeCm3 ? (
                        <div className="text-[11px] font-semibold text-slate-400">
                          {Number(location.capacityVolumeCm3).toLocaleString('vi-VN')} cm³
                        </div>
                      ) : null}
                      {location.fillRatio != null ? (
                        <div className={`mt-1 text-[11px] font-bold ${Number(location.fillRatio) >= 0.9 ? 'text-rose-600' : Number(location.fillRatio) >= 0.7 ? 'text-amber-600' : 'text-emerald-600'}`}>
                          Đầy {Math.round(Number(location.fillRatio) * 100)}% · còn {Number(location.availableVolumeCm3 || 0).toLocaleString('vi-VN')} cm³
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{location.allowMixedSku ? 'Cho phép' : 'Không'}</td>
                    <td className="px-3 py-2 text-slate-700">{location.skuCount || 0}</td>
                    <td className="px-3 py-2 text-slate-700">{location.onHandQuantity || 0}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-1 text-xs font-bold ${isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                        {isActive ? 'Đang dùng' : 'Đã khóa'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setLocationDraft({
                            id: String(location.id),
                            code: String(location.code || ''),
                            name: String(location.name || ''),
                            zone: String(location.zone || ''),
                            purpose: String(location.purpose || 'STORAGE'),
                            sortOrder: Number(location.sortOrder || 0),
                            allowMixedSku: Boolean(location.allowMixedSku),
                            lengthCm: location.lengthCm == null ? '' : Number(location.lengthCm),
                            widthCm: location.widthCm == null ? '' : Number(location.widthCm),
                            heightCm: location.heightCm == null ? '' : Number(location.heightCm),
                            usableRatio: location.usableRatio == null ? 0.75 : Number(location.usableRatio),
                            description: String(location.description || ''),
                          })}
                          className="rounded-md border border-slate-200 px-2.5 py-1.5 font-bold text-slate-700 hover:bg-slate-50"
                        >
                          Sửa
                        </button>
                        <button
                          type="button"
                          onClick={() => void toggleLocationStatus(location)}
                          disabled={Boolean(location.isDefault)}
                          className="rounded-md border border-amber-200 px-2.5 py-1.5 font-bold text-amber-700 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isActive ? 'Khóa' : 'Mở'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {(!inventoryLocations || inventoryLocations.length === 0) && (
                <tr><td colSpan={11} className="px-3 py-3 text-sm font-semibold text-slate-500">Chưa có kệ hàng.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="contents">
      <section className={`${inventoryView === 'ledger' ? '' : 'hidden'} mb-4 rounded-xl border border-slate-200 bg-white p-4`}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-slate-900">Sổ kho / lịch sử biến động tồn</h3>
          <div className="flex flex-wrap items-center gap-2">
            <input type="date" value={ledgerDateFrom || ''} onChange={(event) => setLedgerDateFrom(event.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-sm font-semibold text-slate-700" />
            <input type="date" value={ledgerDateTo || ''} onChange={(event) => setLedgerDateTo(event.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-sm font-semibold text-slate-700" />
            <Select noLabel={true} label="Loại giao dịch" value={ledgerTransactionType || ''} onChange={setLedgerTransactionType} options={[['', 'Tất cả giao dịch'], ['RECEIPT', 'Nhập kho'], ['SALE', 'Xuất bán'], ['ADJUSTMENT', 'Điều chỉnh/Kiểm kê'], ['RETURN', 'Hoàn hàng'], ['REVERSAL', 'Đảo phiếu']]} />
            <button type="button" onClick={() => void applyInventoryLedgerFilters()} className="h-9 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 hover:bg-indigo-100">Lọc sổ</button>
            {(ledgerDateFrom || ledgerDateTo || ledgerTransactionType) && (
              <button type="button" onClick={() => void clearInventoryLedgerFilters()} className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 hover:bg-slate-50">Xóa lọc</button>
            )}
          </div>
        </div>
        <AdminTable headers={['Thời gian', 'Sản phẩm', 'Loại', 'Chứng từ', 'Cũ', 'Chênh lệch', 'Mới', 'Vị trí', 'Ghi chú']}>
          {(inventoryLedger || []).length === 0 ? (
            <tr><td colSpan={9} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Chưa có biến động tồn phù hợp.</td></tr>
          ) : (inventoryLedger || []).map((item: any) => (
            <tr key={item.id}>
              <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '-'}</td>
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900">{item.productName || '-'}</div>
                <div className="font-mono text-xs text-slate-500">{item.variantSku || item.productSku || '-'}</div>
              </td>
              <td className="px-4 py-3 text-xs font-bold text-slate-700">{transactionTypeLabel(item.transactionType)}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-700">{item.referenceCode || '-'}</td>
              <td className="px-4 py-3 text-right">{item.oldQuantity ?? '-'}</td>
              <td className={`px-4 py-3 text-right font-bold ${Number(item.delta || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{Number(item.delta || 0) >= 0 ? '+' : ''}{item.delta || 0}</td>
              <td className="px-4 py-3 text-right">{item.newQuantity ?? '-'}</td>
              <td className="px-4 py-3 text-xs text-slate-600">{item.locationName || item.locationCode || '-'}</td>
              <td className="px-4 py-3 text-xs text-slate-600">{item.note || item.reason || '-'}</td>
            </tr>
          ))}
        </AdminTable>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
          <div className="text-sm font-semibold text-slate-600">
            {ledgerTotal > 0 ? `Hiển thị ${(ledgerPage - 1) * 50 + 1}-${Math.min(ledgerPage * 50, ledgerTotal)} trong ${ledgerTotal} biến động` : 'Không có biến động tồn'}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" disabled={ledgerPage <= 1} onClick={() => void loadInventoryLedger(query, ledgerPage - 1)} className="h-9 rounded-lg border border-slate-200 px-3 text-sm font-bold text-slate-700 disabled:opacity-50">Trang trước</button>
            <span className="min-w-24 text-center text-sm font-bold text-slate-700">Trang {ledgerPage} / {ledgerTotalPages}</span>
            <button type="button" disabled={ledgerPage >= ledgerTotalPages} onClick={() => void loadInventoryLedger(query, ledgerPage + 1)} className="h-9 rounded-lg border border-slate-200 px-3 text-sm font-bold text-slate-700 disabled:opacity-50">Trang sau</button>
          </div>
        </div>
      </section>

      {inventoryView === 'stock' && pendingEditRequests.length > 0 && (
        <section className="mb-4 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-amber-900">Yêu cầu chỉnh sửa IMEI/Serial chờ duyệt</h3>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">{pendingEditRequests.length} yêu cầu</span>
          </div>
          <AdminTable headers={['Sản phẩm', 'Loại', 'Mã hiện tại', 'Mã đề xuất', 'Lý do', 'Thao tác']}>
            {renderEditRequestRows(pendingEditRequests)}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && stockCounts.length > 0 && (
        <section className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-emerald-900">Phiếu kiểm kê kho</h3>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">{stockCounts.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Trạng thái', 'Số dòng', 'Lệch tuyệt đối', 'Lệch ròng', 'Thao tác']}>
            {stockCounts.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3">{item.absoluteVarianceQuantity || 0}</td>
                <td className="px-4 py-3">{item.netVarianceQuantity || 0}</td>
                <td className="px-4 py-3">
                  {item.status === 'DRAFT' ? (
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => setStockCountDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                        <Eye className="h-3.5 w-3.5" /> Xem
                      </button>
                      <button type="button" onClick={() => void decideStockCount(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                        <Check className="h-3.5 w-3.5" /> Duyệt
                      </button>
                      <button type="button" onClick={() => void decideStockCount(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                        <X className="h-3.5 w-3.5" /> Hủy
                      </button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setStockCountDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && adjustments.length > 0 && (
        <section className="mb-4 rounded-xl border border-sky-200 bg-sky-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-sky-900">Phiếu điều chỉnh tồn</h3>
            <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-800">{adjustments.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Trạng thái', 'Số dòng', 'Lệch tuyệt đối', 'Lệch ròng', 'Thao tác']}>
            {adjustments.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3">{item.absoluteVarianceQuantity || 0}</td>
                <td className="px-4 py-3">{item.netVarianceQuantity || 0}</td>
                <td className="px-4 py-3">
                  {item.status === 'DRAFT' ? (
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => setAdjustmentDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                        <Eye className="h-3.5 w-3.5" /> Xem
                      </button>
                      <button type="button" onClick={() => void decideAdjustment(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                        <Check className="h-3.5 w-3.5" /> Duyệt
                      </button>
                      <button type="button" onClick={() => void decideAdjustment(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                        <X className="h-3.5 w-3.5" /> Hủy
                      </button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setAdjustmentDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      <div className={inventoryView === 'stock' ? 'contents' : 'hidden'}>
      <AdminTable headers={[
        <label key="select" className="inline-flex items-center justify-center" title="Chọn tất cả dòng trên trang">
          <input
            type="checkbox"
            checked={currentPageStockCountAllSelected}
            onChange={toggleCurrentPageStockCountSelection}
            className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
          />
        </label>,
        'Sản phẩm',
        'SKU / Biến thể',
        'Tồn thực tế',
        'Đang giữ',
        'Khả dụng',
        'Giá vốn BQ',
        'IMEI / Serial',
        'Cảnh báo',
        'Trạng thái',
      ]}>
        {filteredInventory.flatMap((item: any) => {
          if ('physicalStock' in item || 'availableStock' in item) {
            const itemKey = inventoryItemKey(item);
            return [
              <tr key={itemKey}>
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedStockCountKeySet.has(itemKey)}
                    onChange={() => toggleStockCountSelection(itemKey)}
                    className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                    aria-label={`Chọn kiểm kê ${item.productName || item.productSku || itemKey}`}
                  />
                </td>
                <td className="px-4 py-3 font-semibold text-slate-900">{item.productName}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  {item.variantSku || item.productSku || compactId(item.productId)}
                  {item.variantColor ? ` - ${item.variantColor}` : ''}
                  {item.variantConfiguration ? ` - ${item.variantConfiguration}` : ''}
                </td>
                <td className="px-4 py-3">{item.physicalStock ?? 0}</td>
                <td className="px-4 py-3">{item.reservedStock ?? 0}</td>
                <td className="px-4 py-3 font-semibold text-slate-900">{item.availableStock ?? 0}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-700">{currency.format(Number(item.averageUnitCost || 0))}</td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  <div className="space-y-2">
                    <div>{renderIdentifierSummary(item)}</div>
                    {(item.tracksImei || item.tracksSerialNumber) && (
                      <button type="button" onClick={() => void openIdentifierModal(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                        <Eye className="h-3.5 w-3.5" /> Xem mã
                      </button>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{item.stockAlert === 'LOW' ? `Cần nhập thêm (min ${item.minimumStock || 0})` : 'Ổn định'}</td>
                <td className="px-4 py-3">
                  <div className="space-y-2">
                    <div>{stockStateLabel(item.stockState, item.blockSaleWhenOutOfStock)}</div>
                    {Number(item.availableStock || 0) > 0 && (
                      <button type="button" onClick={() => void openIssueSuggestionModal(item)} className="rounded-lg border border-indigo-200 px-2.5 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50">
                        Gợi ý xuất
                      </button>
                    )}
                    <button type="button" onClick={() => openAdjustmentDraft(item)} className="rounded-lg border border-sky-200 px-2.5 py-1.5 text-xs font-semibold text-sky-700 hover:bg-sky-50">
                      Điều chỉnh
                    </button>
                  </div>
                </td>
              </tr>,
            ];
          }

          const inventorySettings = getInventorySettings(item);
          const rows = [
            <tr key={`${item.id}-base`}>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3 font-semibold text-slate-900">{item.name}</td>
              <td className="px-4 py-3 font-mono text-xs">{item.sku || compactId(item.id)}</td>
              <td className="px-4 py-3">{item.stock ?? 0}</td>
              <td className="px-4 py-3">0</td>
              <td className="px-4 py-3">{item.stock ?? 0}</td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">{Number(item.stock || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
              <td className="px-4 py-3">
                <div className="space-y-2">
                  <div>{Number(item.stock || 0) > 0 ? 'Có thể bán' : inventorySettings.blockSaleWhenOutOfStock ? 'Khóa bán khi hết' : 'Hết hàng'}</div>
                  <button type="button" onClick={() => openAdjustmentDraft({ ...item, productId: item.id, productName: item.name, physicalStock: item.stock })} className="rounded-lg border border-sky-200 px-2.5 py-1.5 text-xs font-semibold text-sky-700 hover:bg-sky-50">
                    Điều chỉnh
                  </button>
                </div>
              </td>
            </tr>,
          ];
          (item.variants || []).forEach((variant: any) => {
            rows.push(
              <tr key={`${item.id}-${variant.id}`} className="bg-slate-50/60">
                <td className="px-4 py-3">-</td>
                <td className="px-4 py-3 pl-8 text-sm text-slate-600">{item.name}</td>
                <td className="px-4 py-3 font-mono text-xs">{variant.sku || compactId(variant.id)} {variant.colorName ? `- ${variant.colorName}` : ''}</td>
                <td className="px-4 py-3">{variant.stockQuantity ?? 0}</td>
                <td className="px-4 py-3">0</td>
                <td className="px-4 py-3">{variant.stockQuantity ?? 0}</td>
                <td className="px-4 py-3">-</td>
                <td className="px-4 py-3">-</td>
                <td className="px-4 py-3">{Number(variant.stockQuantity || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
                <td className="px-4 py-3">
                  <div className="space-y-2">
                    <div>{variant.isActive === false ? 'Đã ẩn' : Number(variant.stockQuantity || 0) > 0 ? 'Có thể bán' : 'Hết hàng'}</div>
                    <button type="button" onClick={() => openAdjustmentDraft({ productId: item.id, variantId: variant.id, productName: item.name, variantSku: variant.sku, productSku: item.sku, physicalStock: variant.stockQuantity })} className="rounded-lg border border-sky-200 px-2.5 py-1.5 text-xs font-semibold text-sky-700 hover:bg-sky-50">
                      Điều chỉnh
                    </button>
                  </div>
                </td>
              </tr>,
            );
          });
          return rows;
        })}
      </AdminTable>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
        <div className="text-sm font-semibold text-slate-600">
          {inventoryTotal > 0
            ? `Hiển thị ${(inventoryPage - 1) * 50 + 1}-${Math.min(inventoryPage * 50, inventoryTotal)} trong ${inventoryTotal} dòng`
            : 'Không có dữ liệu tồn kho'}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={inventoryPage <= 1}
            onClick={() => void loadInventoryLevels(query, inventoryPage - 1)}
            className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Trang trước
          </button>
          <span className="min-w-24 text-center text-sm font-bold text-slate-700">
            Trang {inventoryPage} / {inventoryTotalPages}
          </span>
          <button
            type="button"
            disabled={inventoryPage >= inventoryTotalPages}
            onClick={() => void loadInventoryLevels(query, inventoryPage + 1)}
            className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Trang sau
          </button>
        </div>
      </div>
      </div>
      </div>
      {locationDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <form onSubmit={(event) => void submitLocationDraft(event)} className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">{locationDraft.id ? 'Sửa kệ hàng' : 'Thêm kệ hàng'}</h3>
                <p className="text-sm text-slate-600">Kệ đang dùng sẽ được chọn trong phiếu nhập kho.</p>
              </div>
              <button type="button" onClick={() => setLocationDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid gap-3 p-5 md:grid-cols-2">
              <label className="text-xs font-semibold text-slate-600">
                Mã kệ
                <input value={locationDraft.code} onChange={(event) => setLocationDraft((current) => current ? { ...current, code: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="A-01-01" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Tên kệ
                <input value={locationDraft.name} onChange={(event) => setLocationDraft((current) => current ? { ...current, name: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="Dãy A - Kệ 01 - Ô 01" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Khu vực
                <input value={locationDraft.zone} onChange={(event) => setLocationDraft((current) => current ? { ...current, zone: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="Kho chính" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Loại vị trí
                <select value={locationDraft.purpose} onChange={(event) => setLocationDraft((current) => current ? { ...current, purpose: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800">
                  {locationPurposeOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Thứ tự lấy hàng
                <input type="number" min={0} value={locationDraft.sortOrder} onChange={(event) => setLocationDraft((current) => current ? { ...current, sortOrder: Number(event.target.value || 0) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="10101" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Dài (cm)
                <input type="number" min={0} step="0.1" value={locationDraft.lengthCm} onChange={(event) => setLocationDraft((current) => current ? { ...current, lengthCm: event.target.value === '' ? '' : Number(event.target.value) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="100" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Rộng (cm)
                <input type="number" min={0} step="0.1" value={locationDraft.widthCm} onChange={(event) => setLocationDraft((current) => current ? { ...current, widthCm: event.target.value === '' ? '' : Number(event.target.value) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="60" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Cao (cm)
                <input type="number" min={0} step="0.1" value={locationDraft.heightCm} onChange={(event) => setLocationDraft((current) => current ? { ...current, heightCm: event.target.value === '' ? '' : Number(event.target.value) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="40" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Hệ số sử dụng
                <input type="number" min={0.01} max={1} step="0.01" value={locationDraft.usableRatio} onChange={(event) => setLocationDraft((current) => current ? { ...current, usableRatio: event.target.value === '' ? '' : Number(event.target.value) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="0.75" />
              </label>
              <label className="flex min-h-10 items-center gap-2 self-end rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-bold text-slate-700">
                <input
                  type="checkbox"
                  checked={Boolean(locationDraft.allowMixedSku)}
                  onChange={(event) => setLocationDraft((current) => current ? { ...current, allowMixedSku: event.target.checked } : current)}
                  className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                Cho phép nhiều SKU cùng kệ
              </label>
              <label className="text-xs font-semibold text-slate-600 md:col-span-2">
                Mô tả
                <textarea value={locationDraft.description} onChange={(event) => setLocationDraft((current) => current ? { ...current, description: event.target.value } : current)} className="mt-1 min-h-24 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" placeholder="Ghi chú vị trí, nhóm hàng hoặc quy tắc lưu kho" />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setLocationDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700">Lưu kệ hàng</button>
            </div>
          </form>
        </div>
      )}
      {adjustmentDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <form onSubmit={(event) => void submitAdjustmentDraft(event)} className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu điều chỉnh tồn</h3>
                <p className="text-sm text-slate-600">Phiếu chỉ cập nhật tồn kho sau khi được duyệt.</p>
              </div>
              <button type="button" onClick={() => setAdjustmentDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-[180px_220px_1fr]">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={adjustmentDraft.referenceCode} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Loại điều chỉnh
                  <input value={adjustmentDraft.reason} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Ghi chú chung
                  <input value={adjustmentDraft.note} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, note: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="mb-4">
                  <div className="text-sm font-bold text-slate-900">{adjustmentDraft.line.productName}</div>
                  <div className="font-mono text-xs text-slate-500">{adjustmentDraft.line.sku}</div>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <label className="text-xs font-semibold text-slate-600">
                    Tồn hiện tại
                    <input value={adjustmentDraft.line.currentQuantity} disabled className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-700" />
                  </label>
                  <label className="text-xs font-semibold text-slate-600">
                    Tồn đề xuất
                    <input type="number" min={0} value={adjustmentDraft.line.newQuantity} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, line: { ...current.line, newQuantity: Number(event.target.value || 0) } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                  </label>
                  <div className="text-xs font-semibold text-slate-600">
                    Chênh lệch
                    <div className={`mt-1 flex h-10 items-center rounded-lg border border-slate-200 px-3 text-sm font-bold ${adjustmentDraft.line.newQuantity - adjustmentDraft.line.currentQuantity === 0 ? 'text-slate-600' : adjustmentDraft.line.newQuantity > adjustmentDraft.line.currentQuantity ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {adjustmentDraft.line.newQuantity - adjustmentDraft.line.currentQuantity}
                    </div>
                  </div>
                </div>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  Lý do điều chỉnh
                  <textarea value={adjustmentDraft.line.reason} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, line: { ...current.line, reason: event.target.value } } : current)} className="mt-1 min-h-24 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" />
                </label>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  Ghi chú dòng
                  <input value={adjustmentDraft.line.note} onChange={(event) => setAdjustmentDraft((current) => current ? { ...current, line: { ...current.line, note: event.target.value } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setAdjustmentDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-bold text-white hover:bg-sky-700">Tạo phiếu điều chỉnh</button>
            </div>
          </form>
        </div>
      )}
      {adjustmentDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu điều chỉnh {adjustmentDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {adjustmentDetail.status} - Lệch tuyệt đối: {adjustmentDetail.absoluteVarianceQuantity || 0}</p>
              </div>
              <button type="button" onClick={() => setAdjustmentDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Tồn hiện tại', 'Tồn đề xuất', 'Chênh lệch', 'Lý do', 'Ghi chú']}>
                {(adjustmentDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3">{line.currentQuantity || 0}</td>
                    <td className="px-4 py-3">{line.newQuantity || 0}</td>
                    <td className={`px-4 py-3 text-sm font-semibold ${Number(line.varianceQuantity || 0) === 0 ? 'text-slate-500' : Number(line.varianceQuantity || 0) > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{line.varianceQuantity || 0}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.reason || adjustmentDetail.reason || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {stockCountDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <form onSubmit={(event) => void submitStockCountDraft(event)} className="max-h-[90vh] w-full max-w-6xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu kiểm kê kho</h3>
                <p className="text-sm text-slate-600">Nhập số lượng thực đếm. Phiếu chỉ ghi tồn sau khi được duyệt.</p>
              </div>
              <button type="button" onClick={() => setStockCountDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[70vh] space-y-4 overflow-y-auto p-5">
              <div className="grid gap-3 md:grid-cols-[180px_220px_1fr]">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={stockCountDraft.referenceCode} onChange={(event) => setStockCountDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Lý do
                  <input value={stockCountDraft.reason} onChange={(event) => setStockCountDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Ghi chú
                  <input value={stockCountDraft.note} onChange={(event) => setStockCountDraft((current) => current ? { ...current, note: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <AdminTable headers={['Sản phẩm', 'SKU', 'Tồn hệ thống', 'Thực đếm', 'Chênh lệch', 'Ghi chú']}>
                {stockCountDraft.lines.map((line) => {
                  const variance = Number(line.countedQuantity || 0) - Number(line.expectedQuantity || 0);
                  return (
                    <tr key={line.key}>
                      <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.sku}</td>
                      <td className="px-4 py-3">{line.expectedQuantity}</td>
                      <td className="px-4 py-3">
                        <input type="number" min={0} value={line.countedQuantity} onChange={(event) => updateStockCountLine(line.key, { countedQuantity: Number(event.target.value || 0) })} className="h-9 w-24 rounded-lg border border-slate-200 px-3 text-sm" />
                      </td>
                      <td className={`px-4 py-3 text-sm font-semibold ${variance === 0 ? 'text-slate-500' : variance > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{variance}</td>
                      <td className="px-4 py-3">
                        <input value={line.note} onChange={(event) => updateStockCountLine(line.key, { note: event.target.value })} className="h-9 w-full min-w-40 rounded-lg border border-slate-200 px-3 text-sm" />
                      </td>
                    </tr>
                  );
                })}
              </AdminTable>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setStockCountDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700">Tạo phiếu kiểm kê</button>
            </div>
          </form>
        </div>
      )}
      {stockCountDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu kiểm kê {stockCountDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {stockCountDetail.status} - Lệch tuyệt đối: {stockCountDetail.absoluteVarianceQuantity || 0}</p>
              </div>
              <button type="button" onClick={() => setStockCountDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Tồn hệ thống', 'Thực đếm', 'Chênh lệch', 'Ghi chú']}>
                {(stockCountDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3">{line.expectedQuantity || 0}</td>
                    <td className="px-4 py-3">{line.countedQuantity || 0}</td>
                    <td className={`px-4 py-3 text-sm font-semibold ${Number(line.varianceQuantity || 0) === 0 ? 'text-slate-500' : Number(line.varianceQuantity || 0) > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{line.varianceQuantity || 0}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {identifierLoading && (
        <div className="fixed inset-x-0 bottom-6 z-50 mx-auto w-fit rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-xl">
          Đang tải danh sách mã...
        </div>
      )}
      {issueSuggestionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Gợi ý xuất kho theo kệ</h3>
                <p className="text-sm text-slate-600">
                  {issueSuggestionModal.row.productName} - {issueSuggestionModal.row.variantSku || issueSuggestionModal.row.productSku || compactId(issueSuggestionModal.row.productId)}
                </p>
                <p className="mt-1 text-xs font-semibold text-slate-500">Số lượng cần xuất: {issueSuggestionModal.quantity}</p>
              </div>
              <button type="button" onClick={() => setIssueSuggestionModal(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Kệ hàng', 'Tồn khả dụng', 'SL gợi ý', 'Cơ chế', 'Mã gợi ý']}>
                {issueSuggestionModal.suggestions.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Không có tồn khả dụng theo kệ để gợi ý.</td></tr>
                ) : issueSuggestionModal.suggestions.map((item: any) => (
                  <tr key={item.warehouseLocationId || item.locationCode}>
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{item.locationName || '-'}</div>
                      <div className="font-mono text-xs text-slate-500">{item.locationCode || '-'}</div>
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-700">{item.availableQuantity || 0}</td>
                    <td className="px-4 py-3 text-sm font-bold text-indigo-700">{item.suggestedQuantity || 0}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.mode === 'IDENTIFIER' ? 'FIFO theo IMEI/serial' : 'FIFO theo tồn kệ'}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {(item.identifiers || []).length === 0 ? '-' : (
                        <div className="flex max-w-md flex-wrap gap-1">
                          {(item.identifiers || []).slice(0, 12).map((identifier: any) => (
                            <span key={`${identifier.type}-${identifier.value}`} className="rounded bg-slate-100 px-2 py-1 font-mono text-[11px] text-slate-700">
                              {identifier.value}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {identifierModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Danh sách IMEI / Serial</h3>
                <p className="text-sm text-slate-600">{identifierModal.row.productName} - {identifierModal.row.variantSku || identifierModal.row.productSku || compactId(identifierModal.row.productId)}</p>
              </div>
              <button type="button" onClick={() => setIdentifierModal(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] space-y-6 overflow-y-auto p-5">
              <section>
                <h4 className="mb-2 text-sm font-bold text-slate-800">IMEI</h4>
                <AdminTable headers={['Mã hiện tại', 'Trạng thái', 'Kệ hiện tại', 'Nguồn', 'Yêu cầu chờ duyệt', 'Thao tác']}>
                  {renderIdentifierRows('IMEI', identifierModal.data?.imeis || [])}
                </AdminTable>
              </section>
              <section>
                <h4 className="mb-2 text-sm font-bold text-slate-800">Serial number</h4>
                <AdminTable headers={['Mã hiện tại', 'Trạng thái', 'Kệ hiện tại', 'Nguồn', 'Yêu cầu chờ duyệt', 'Thao tác']}>
                  {renderIdentifierRows('SERIAL', identifierModal.data?.serialNumbers || [])}
                </AdminTable>
              </section>
              <section>
                <h4 className="mb-2 text-sm font-bold text-slate-800">Lịch sử yêu cầu chỉnh sửa</h4>
                <AdminTable headers={['Loại', 'Mã hiện tại', 'Mã đề xuất', 'Lý do / quyết định', 'Thao tác']}>
                  {renderEditRequestRows(identifierModal.data?.editRequests || [], true)}
                </AdminTable>
              </section>
            </div>
          </div>
        </div>
      )}
    </AdminPanel>
  );
}
