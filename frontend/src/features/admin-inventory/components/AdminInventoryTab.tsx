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

function identifierStatusLabel(status: string) {
  const labels: Record<string, string> = {
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
  const [identifierLoading, setIdentifierLoading] = useState(false);
  const [pendingEditRequests, setPendingEditRequests] = useState<any[]>([]);
  const [stockCounts, setStockCounts] = useState<any[]>([]);
  const [stockCountDraft, setStockCountDraft] = useState<StockCountDraft | null>(null);
  const [stockCountDetail, setStockCountDetail] = useState<any | null>(null);
  const [adjustments, setAdjustments] = useState<any[]>([]);
  const [adjustmentDraft, setAdjustmentDraft] = useState<AdjustmentDraft | null>(null);
  const [adjustmentDetail, setAdjustmentDetail] = useState<any | null>(null);
  const {
    categories,
    exportInventorySnapshot,
    filteredInventory,
    inventoryBrandFilter,
    inventoryBrandOptions,
    inventoryCategoryFilter,
    loadInventoryLevels,
    query,
    setInventoryBrandFilter,
    setInventoryCategoryFilter,
    setQuery,
  } = props;

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

  useEffect(() => {
    void loadPendingEditRequests();
    void loadStockCounts();
    void loadAdjustments();
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

  function openStockCountDraft() {
    const rows = filteredInventory
      .filter((item: any) => 'physicalStock' in item || 'availableStock' in item)
      .slice(0, 200)
      .map((item: any) => ({
        key: `${item.productId}-${item.variantId || 'base'}`,
        productId: String(item.productId),
        variantId: item.variantId ? String(item.variantId) : null,
        productName: String(item.productName || ''),
        sku: String(item.variantSku || item.productSku || compactId(item.productId)),
        expectedQuantity: Number(item.physicalStock || 0),
        countedQuantity: Number(item.physicalStock || 0),
        note: '',
      }));
    if (!rows.length) {
      window.alert('Không có dòng tồn kho để tạo phiếu kiểm kê.');
      return;
    }
    setStockCountDraft({
      referenceCode: generateStockCountCode(),
      reason: 'KIEM_KE_DINH_KY',
      note: '',
      lines: rows,
    });
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
          <td colSpan={5} className="px-4 py-3 text-sm text-slate-500">Chưa có mã.</td>
        </tr>
      );
    }
    return rows.map((item) => (
      <tr key={`${identifierType}-${item.id}`}>
        <td className="px-4 py-3 font-mono text-xs text-slate-800">{item.value}</td>
        <td className="px-4 py-3 text-xs text-slate-600">{identifierStatusLabel(String(item.status || ''))}</td>
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

  return (
    <AdminPanel
      title="Quản lý tồn kho"
      action={
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={openStockCountDraft} className="inline-flex h-10 items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 text-sm font-bold text-emerald-700 shadow-sm transition hover:bg-emerald-100">
            <ClipboardList className="h-4 w-4" /> Kiểm kê
          </button>
          <button type="button" onClick={() => void exportInventorySnapshot()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50">
            <Download className="h-4 w-4" /> Xuất
          </button>
        </div>
      }
      filters={
        <>
          <Select noLabel={true} label="Danh mục" value={inventoryCategoryFilter} onChange={setInventoryCategoryFilter} options={[['', 'Tất cả danh mục'], ...categories.map((c: any) => [String(c.id), c.parentName ? `${c.parentName} / ${c.name}` : c.name] as [string, string])]} />
          <Select noLabel={true} label="Thương hiệu" value={inventoryBrandFilter} onChange={setInventoryBrandFilter} options={inventoryBrandOptions} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, trạng thái kho" />
        </>
      }
    >
      {pendingEditRequests.length > 0 && (
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
      {stockCounts.length > 0 && (
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
      {adjustments.length > 0 && (
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
      <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Tồn thực tế', 'Đang giữ', 'Khả dụng', 'Giá vốn BQ', 'IMEI / Serial', 'Cảnh báo', 'Trạng thái']}>
        {filteredInventory.flatMap((item: any) => {
          if ('physicalStock' in item || 'availableStock' in item) {
            return [
              <tr key={`${item.productId}-${item.variantId || 'base'}`}>
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
                <AdminTable headers={['Mã hiện tại', 'Trạng thái', 'Nguồn', 'Yêu cầu chờ duyệt', 'Thao tác']}>
                  {renderIdentifierRows('IMEI', identifierModal.data?.imeis || [])}
                </AdminTable>
              </section>
              <section>
                <h4 className="mb-2 text-sm font-bold text-slate-800">Serial number</h4>
                <AdminTable headers={['Mã hiện tại', 'Trạng thái', 'Nguồn', 'Yêu cầu chờ duyệt', 'Thao tác']}>
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
