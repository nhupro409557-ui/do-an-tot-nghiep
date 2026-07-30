import React, { useEffect, useState } from 'react';
import { ArrowRightLeft, Check, ClipboardList, Download, Eye, X, Edit, Lock, Unlock, Plus, Filter, RotateCcw } from 'lucide-react';
import { AdminPanel, AdminTable, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { compactId, currency, getInventorySettings } from '../../admin-shell/components/AdminDashboardConfig';
import { adminInventoryApi } from '../services/adminInventoryApi';

type AdminInventoryTabProps = Record<string, any>;
type StockCountDraft = {
  referenceCode: string;
  reason: string;
  note: string;
  locationCode: string;
  locationName: string;
  lines: Array<{
    key: string;
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    expectedQuantity: number;
    countedQuantity: number;
    tracksImei: boolean;
    tracksSerialNumber: boolean;
    imeis: string;
    serialNumbers: string;
    availableImeis: InventoryLocationIdentifier[];
    availableSerialNumbers: InventoryLocationIdentifier[];
    identifierPairIds: string[];
    availableIdentifierUnits: InventoryIdentifierUnit[];
    note: string;
  }>;
};
type StockCountIdentifierMode = 'select' | 'manual';
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
type TransferDraft = {
  referenceCode: string;
  reason: string;
  note: string;
  line: {
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    fromLocationId: string;
    toLocationId: string;
    quantity: number;
    maxQuantity: number;
    imeis: string;
    serialNumbers: string;
    availableImeis: InventoryLocationIdentifier[];
    availableSerialNumbers: InventoryLocationIdentifier[];
    identifierPairIds: string[];
    availableIdentifierUnits: InventoryIdentifierUnit[];
    note: string;
  };
};
type InternalHoldDraft = {
  referenceCode: string;
  holdType: 'QC_HOLD' | 'CLAIM_HOLD' | 'INTERNAL_HOLD';
  reason: string;
  note: string;
  line: {
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    locationId: string;
    locationCode: string;
    locationName: string;
    quantity: number;
    maxQuantity: number;
    note: string;
  };
};
type DisposalDraft = {
  referenceCode: string;
  dispositionType: 'SCRAP' | 'LIQUIDATED' | 'OUT_OF_SYSTEM';
  reason: string;
  note: string;
  partnerName: string;
  recoveryValue: number | '';
  line: {
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    locationId: string;
    locationCode: string;
    locationName: string;
    quantity: number;
    maxQuantity: number;
    imeis: string;
    serialNumbers: string;
    availableImeis: InventoryLocationIdentifier[];
    availableSerialNumbers: InventoryLocationIdentifier[];
    identifierPairIds: string[];
    availableIdentifierUnits: InventoryIdentifierUnit[];
    note: string;
  };
};
type CostAdjustmentDraft = {
  referenceCode: string;
  reason: string;
  note: string;
  line: {
    productId: string;
    variantId: string | null;
    productName: string;
    sku: string;
    locationId: string;
    locationCode: string;
    locationName: string;
    currentAverageUnitCost: number;
    newAverageUnitCost: number;
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
type InventoryLocationEntry = {
  id: string;
  code: string;
  name: string;
  zone: string;
  purpose?: string;
  onHandQuantity: number;
  imeis: InventoryLocationIdentifier[];
  serialNumbers: InventoryLocationIdentifier[];
  identifierUnits: InventoryIdentifierUnit[];
};
type InventoryIdentifierUnit = {
  pairId: string;
  imei1: string;
  imei2?: string | null;
  serialNumber: string;
  status: string;
  isPrimary?: boolean;
  isConsistent?: boolean;
};
type InventoryLocationIdentifier = {
  id: string;
  code: string;
  status: string;
  isPrimary?: boolean;
};
type IdentifierLocationDraft = {
  identifierType: 'IMEI' | 'SERIAL';
  identifierId: string | null;
  identifierValue: string;
  productId: string;
  variantId: string | null;
  productName: string;
  currentLocationCode: string;
  newLocationId: string;
  reason: string;
};
type InventoryLocationDetailModal = {
  row: any;
  locations: InventoryLocationEntry[];
};
type InventoryLocationIdentifierModal = {
  row: any;
  location: InventoryLocationEntry;
};
type InventoryView = 'stock' | 'ledger' | 'locations' | 'aging' | 'reconciliation';

const inventoryLocationAreaNames: Record<string, string> = {
  MAIN: 'Kho',
  BH: 'Dãy bảo hành',
  CL: 'Dãy cách ly',
  ERR: 'Dãy hàng lỗi',
  RT: 'Dãy hàng trả',
  CU: 'Dãy hàng cũ',
};

function parseInventoryLocationCode(code: string) {
  const match = code.trim().toUpperCase().match(/^([A-Z]{1,4})-(\d{2})-(\d{2})$/);
  return match ? { area: match[1], shelf: match[2], bin: match[3] } : null;
}

function resolveInventoryLocationArea(code: string) {
  const normalizedCode = code.trim().toUpperCase();
  if (normalizedCode === 'MAIN') return 'MAIN';
  return parseInventoryLocationCode(normalizedCode)?.area || '';
}

function inventoryLocationAreaLabel(area: string, zone = '') {
  const normalizedArea = area.trim().toUpperCase();
  const zoneName = zone.trim();
  if (zoneName) return zoneName;
  if (!normalizedArea) return '-';
  if (inventoryLocationAreaNames[normalizedArea]) return inventoryLocationAreaNames[normalizedArea];
  if (normalizedArea.length === 1) return `Dãy ${normalizedArea}`;
  return `Dãy ${normalizedArea}`;
}

function resolveInventoryLocationZone(code: string, name: string, zone: string) {
  const codeParts = parseInventoryLocationCode(code);
  if (codeParts) return inventoryLocationAreaLabel(codeParts.area, zone);
  if (code.trim().toUpperCase() === 'MAIN') return inventoryLocationAreaLabel('MAIN', zone);
  const nameZone = name.match(/Dãy\s+([A-ZÀ-Ỵ0-9]+)/i)?.[1];
  if (nameZone) return `Dãy ${nameZone.toUpperCase()}`;
  const explicitZone = zone.trim();
  if (explicitZone) return explicitZone;
  return '-';
}

const locationPurposeOptions: [string, string][] = [
  ['STORAGE', 'Sản phẩm bán'],
  ['VIRTUAL', 'Kho'],
  ['WARRANTY', 'Dãy bảo hành'],
  ['QC', 'Dãy cách ly / kiểm tra'],
  ['DAMAGED', 'Hàng lỗi'],
  ['RETURN', 'Hàng trả'],
  ['USED', 'Hàng cũ đã thẩm định'],
];

const defaultLocationAreaOptions: [string, string][] = [
  ['A', 'Dãy A'],
  ['B', 'Dãy B'],
  ['C', 'Dãy C'],
  ['MAIN', 'Kho'],
  ['BH', 'Dãy bảo hành'],
  ['CL', 'Dãy cách ly'],
  ['ERR', 'Dãy hàng lỗi'],
  ['RT', 'Dãy hàng trả'],
  ['CU', 'Dãy hàng cũ'],
];

const defaultLocationAreaPurpose: Record<string, string> = {
  MAIN: 'VIRTUAL',
  BH: 'WARRANTY',
  CL: 'QC',
  QC: 'QC',
  ERR: 'DAMAGED',
  RT: 'RETURN',
  CU: 'USED',
};

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

const documentStatusLabels: Record<string, string> = {
  DRAFT: 'Nháp',
  APPROVED: 'Đã duyệt',
  COMPLETED: 'Đã hoàn tất',
  CANCELLED: 'Đã hủy',
};

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

function internalHoldTypeLabel(type: string) {
  const labels: Record<string, string> = {
    QC_HOLD: 'Giữ kiểm tra',
    CLAIM_HOLD: 'Giữ khiếu nại',
    INTERNAL_HOLD: 'Giữ nội bộ',
  };
  return labels[type] || type || '-';
}

function disposalTypeLabel(type: string) {
  const labels: Record<string, string> = {
    SCRAP: 'Hủy/phế phẩm',
    LIQUIDATED: 'Thanh lý',
    OUT_OF_SYSTEM: 'Xuất khỏi hệ thống',
  };
  return labels[type] || type || '-';
}

function reconciliationIssueLabel(type: string) {
  const labels: Record<string, string> = {
    LEVEL_GT_IDENTIFIERS: 'Tồn kệ lớn hơn số mã',
    IDENTIFIER_IN_STOCK_WITHOUT_LOCATION: 'Mã còn tồn nhưng chưa có kệ',
    IDENTIFIER_LOCATION_WITHOUT_LEVEL: 'Mã có kệ nhưng kệ không có tồn',
    TERMINAL_IDENTIFIER_WITH_LOCATION: 'Mã đã rời kho nhưng còn gắn kệ',
    SELLABLE_STOCK_MISMATCH: 'Tồn bán được lệch tổng tồn kệ',
    LOT_QUANTITY_MISMATCH: 'Tồn kệ lệch số lượng lô',
    RESERVED_QUANTITY_MISMATCH: 'Tồn giữ lệch số mã đang giữ',
    IDENTIFIER_PAIR_MISMATCH: 'Cặp IMEI/serial không đồng bộ',
    DOCUMENT_LEDGER_MISMATCH: 'Chứng từ hoàn tất thiếu sổ kho',
  };
  return labels[type] || type || '-';
}

function dispositionReasonLabel(reason: string) {
  const labels: Record<string, string> = {
    RTV_COMPLETED: 'RTV hoàn tất',
    LIQUIDATED: 'Đã thanh lý',
    SCRAP: 'Hủy/phế phẩm',
    OUT_OF_SYSTEM: 'Xuất khỏi hệ thống',
  };
  return labels[reason] || '';
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

function inventoryLocationEntries(row: any): InventoryLocationEntry[] {
  const locations = Array.isArray(row?.locations) ? row.locations : [];
  return locations.map((item: any, index: number) => {
    const code = String(item?.code || '').trim();
    const name = String(item?.name || '').trim();
    const zone = String(item?.zone || '').trim();
    const imeis = Array.isArray(item?.imeis) ? item.imeis : [];
    const serialNumbers = Array.isArray(item?.serialNumbers) ? item.serialNumbers : [];
    const identifierUnits = Array.isArray(item?.identifierUnits) ? item.identifierUnits : [];
    return {
      id: String(item?.id || item?.locationId || item?.code || index),
      code,
      name,
      zone: resolveInventoryLocationZone(code, name, zone),
      purpose: String(item?.purpose || '').trim(),
      onHandQuantity: Number(item?.onHandQuantity || 0),
      imeis: imeis.map((identifier: any) => ({
        id: String(identifier?.id || ''),
        code: String(identifier?.code || '').trim(),
        status: String(identifier?.status || '').trim(),
        isPrimary: Boolean(identifier?.isPrimary),
      })).filter((identifier: InventoryLocationIdentifier) => identifier.code),
      serialNumbers: serialNumbers.map((identifier: any) => ({
        id: String(identifier?.id || ''),
        code: String(identifier?.code || '').trim(),
        status: String(identifier?.status || '').trim(),
      })).filter((identifier: InventoryLocationIdentifier) => identifier.code),
      identifierUnits: identifierUnits.map((unit: any) => ({
        pairId: String(unit?.pairId || ''), imei1: String(unit?.imei1 || ''), imei2: unit?.imei2 ? String(unit.imei2) : null,
        serialNumber: String(unit?.serialNumber || ''), status: String(unit?.status || ''), isPrimary: Boolean(unit?.isPrimary), isConsistent: unit?.isConsistent !== false,
      })).filter((unit: InventoryIdentifierUnit) => unit.pairId && unit.imei1 && unit.serialNumber),
    };
  });
}

function inventoryLocationSummary(row: any) {
  const locations = inventoryLocationEntries(row);
  if (locations.length === 0) {
    return {
      locations,
      primary: Number(row?.physicalStock || 0) > 0 ? 'Chưa phân bổ kệ' : '-',
      secondary: '',
    };
  }
  const totalQuantity = locations.reduce((sum, item) => sum + item.onHandQuantity, 0);
  const firstLocation = locations[0];
  return {
    locations,
    primary: `${locations.length} kệ`,
    secondary: `${firstLocation.code || 'Kệ không rõ'}${locations.length > 1 ? ` +${locations.length - 1}` : ''} • ${totalQuantity} SP`,
  };
}

function locationIdentifierStats(location: InventoryLocationEntry, row: any) {
  const tracksIdentifiers = Boolean(row?.tracksImei || row?.tracksSerialNumber);
  const managedQuantity = Math.max(location.imeis.length, location.serialNumbers.length);
  const missingQuantity = Math.max(0, Number(location.onHandQuantity || 0) - managedQuantity);
  return {
    tracksIdentifiers,
    managedQuantity,
    missingQuantity,
    totalIdentifiers: location.imeis.length + location.serialNumbers.length,
  };
}

function renderLocationIdentifierTable(
  label: string,
  identifiers: InventoryLocationIdentifier[],
  onEdit: (identifierType: 'IMEI' | 'SERIAL', identifier: InventoryLocationIdentifier) => void,
  onMove: (identifierType: 'IMEI' | 'SERIAL', identifier: InventoryLocationIdentifier) => void,
) {
  const identifierType = label === 'IMEI' ? 'IMEI' : 'SERIAL';
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3 text-xs font-black uppercase text-slate-500">
        {label} ({identifiers.length})
      </div>
      {identifiers.length > 0 ? (
        <table className="w-full text-left text-sm">
          <thead className="bg-white text-xs uppercase text-slate-400">
            <tr>
              <th className="px-4 py-2">Mã</th>
              <th className="px-4 py-2">Trạng thái</th>
              <th className="px-4 py-2">Ghi chú</th>
              <th className="px-4 py-2 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {identifiers.map((identifier) => (
              <tr key={`${label}-${identifier.code}`}>
                <td className="px-4 py-2 font-mono text-xs font-bold text-slate-800">{identifier.code}</td>
                <td className="px-4 py-2 text-xs font-semibold text-slate-600">{identifierStatusLabel(identifier.status)}</td>
                <td className="px-4 py-2 text-xs text-slate-500">{identifier.isPrimary ? 'IMEI chính' : '-'}</td>
                <td className="px-4 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => onMove(identifierType, identifier)}
                      className="rounded-lg border border-indigo-200 px-2.5 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"
                    >
                      Đổi kệ
                    </button>
                    <button
                      type="button"
                      onClick={() => onEdit(identifierType, identifier)}
                      className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Sửa mã
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="px-4 py-5 text-sm font-semibold text-slate-400">Không có {label.toLowerCase()} trên kệ này.</div>
      )}
    </div>
  );
}

function IdentifierUnitTable({ units, onToggle, selectedIds }: { units: InventoryIdentifierUnit[]; onToggle?: (unit: InventoryIdentifierUnit, selected: boolean) => void; selectedIds?: string[] }) {
  const selected = new Set(selectedIds || []);
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3 text-xs font-black uppercase text-slate-500">Thiết bị định danh ({units.length})</div>
      <table className="w-full text-left text-sm">
        <thead className="bg-white text-xs uppercase text-slate-400"><tr>{onToggle && <th className="px-3 py-2">Chọn</th>}<th className="px-3 py-2">IMEI 1</th><th className="px-3 py-2">IMEI 2</th><th className="px-3 py-2">Số sê-ri</th><th className="px-3 py-2">Trạng thái</th></tr></thead>
        <tbody className="divide-y divide-slate-100">
          {units.map((unit) => <tr key={unit.pairId} className={!unit.isConsistent ? 'bg-red-50' : ''}>
            {onToggle && <td className="px-3 py-2"><input type="checkbox" disabled={!unit.isConsistent} checked={selected.has(unit.pairId)} onChange={(event) => onToggle(unit, event.target.checked)} /></td>}
            <td className="px-3 py-2 font-mono text-xs font-bold">{unit.imei1}</td><td className="px-3 py-2 font-mono text-xs">{unit.imei2 || '-'}</td><td className="px-3 py-2 font-mono text-xs font-bold">{unit.serialNumber}</td><td className="px-3 py-2 text-xs">{unit.isConsistent ? identifierStatusLabel(unit.status) : 'Lệch kệ/trạng thái'}</td>
          </tr>)}
          {!units.length && <tr><td colSpan={onToggle ? 5 : 4} className="px-3 py-6 text-center text-sm text-slate-500">Chưa có thiết bị ghép cặp.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function splitIdentifierText(value: string) {
  return value
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinIdentifierText(values: string[]) {
  return values.join('\n');
}

function TransferIdentifierPicker({
  label,
  availableTitle,
  selectedTitle,
  emptyAvailableText,
  emptySelectedText,
  identifiers,
  selectedValues,
  onToggle,
  manualValue,
  onManualChange,
  manualPlaceholder,
}: {
  label: string;
  availableTitle?: string;
  selectedTitle?: string;
  emptyAvailableText?: string;
  emptySelectedText?: string;
  identifiers: InventoryLocationIdentifier[];
  selectedValues: string[];
  onToggle: (value: string, selected: boolean) => void;
  manualValue?: string;
  onManualChange?: (value: string) => void;
  manualPlaceholder?: string;
}) {
  const [mode, setMode] = useState<'select' | 'manual'>('select');
  const canManualInput = typeof onManualChange === 'function';
  const selectedSet = new Set(selectedValues);
  const availableIdentifiers = identifiers.filter((identifier) => !selectedSet.has(identifier.code));
  const selectedIdentifiers = selectedValues.map((value) => identifiers.find((identifier) => identifier.code === value) || {
    id: value,
    code: value,
    status: '',
  });

  function renderTable(title: string, rows: InventoryLocationIdentifier[], selected: boolean) {
    return (
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-3 py-2">
          <span className="text-xs font-black uppercase text-slate-500">{title}</span>
          <div className="flex items-center gap-2">
            {rows.length > 0 && (
              <button
                type="button"
                onClick={() => rows.forEach((identifier) => onToggle(identifier.code, !selected))}
                className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50"
              >
                {selected ? 'Bỏ hết' : 'Chọn hết'}
              </button>
            )}
            <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-slate-500">{rows.length}</span>
          </div>
        </div>
        <div className="max-h-40 overflow-y-auto">
          {rows.length === 0 ? (
            <div className="px-3 py-4 text-xs font-semibold text-slate-400">
              {selected ? (emptySelectedText || `Chưa chọn ${label.toLowerCase()}.`) : (emptyAvailableText || `Không còn ${label.toLowerCase()} khả dụng.`)}
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <tbody className="divide-y divide-slate-100">
                {rows.map((identifier) => (
                  <tr key={`${label}-${selected ? 'selected' : 'available'}-${identifier.code}`} className="hover:bg-slate-50">
                    <td className="w-10 px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => onToggle(identifier.code, !selected)}
                        className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                        aria-label={`${selected ? 'Bỏ chọn' : 'Chọn'} ${identifier.code}`}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-mono text-xs font-bold text-slate-800">{identifier.code}</div>
                      <div className="mt-0.5 text-[11px] font-semibold text-slate-500">
                        {identifier.status ? identifierStatusLabel(identifier.status) : 'Đã chọn'}
                        {identifier.isPrimary ? ' · IMEI chính' : ''}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-slate-600">{label}</div>
        {canManualInput && (
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
            <button
              type="button"
              onClick={() => setMode('select')}
              className={`rounded-md px-2.5 py-1 text-xs font-bold ${mode === 'select' ? 'bg-amber-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              Chọn mã
            </button>
            <button
              type="button"
              onClick={() => setMode('manual')}
              className={`rounded-md px-2.5 py-1 text-xs font-bold ${mode === 'manual' ? 'bg-amber-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              Nhập tay
            </button>
          </div>
        )}
      </div>
      {canManualInput && mode === 'manual' ? (
        <textarea
          value={manualValue || ''}
          onChange={(event) => onManualChange?.(event.target.value)}
          className="min-h-24 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-100"
          placeholder={manualPlaceholder || `Quét hoặc nhập ${label}, mỗi dòng một mã`}
          aria-label={`${label} nhập tay`}
        />
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {renderTable(availableTitle || `${label} hiện tại`, availableIdentifiers, false)}
          {renderTable(selectedTitle || `${label} cần chuyển`, selectedIdentifiers, true)}
        </div>
      )}
    </div>
  );
}

export default function AdminInventoryTab(props: AdminInventoryTabProps) {
  const [issueSuggestionModal, setIssueSuggestionModal] = useState<{ row: any; quantity: number; suggestions: any[] } | null>(null);
  const [locationDetailModal, setLocationDetailModal] = useState<InventoryLocationDetailModal | null>(null);
  const [locationIdentifierModal, setLocationIdentifierModal] = useState<InventoryLocationIdentifierModal | null>(null);
  const [pendingEditRequests, setPendingEditRequests] = useState<any[]>([]);
  const [pendingLocationRequests, setPendingLocationRequests] = useState<any[]>([]);
  const [identifierLocationDraft, setIdentifierLocationDraft] = useState<IdentifierLocationDraft | null>(null);
  const [stockCounts, setStockCounts] = useState<any[]>([]);
  const [stockCountDraft, setStockCountDraft] = useState<StockCountDraft | null>(null);
  const [stockCountIdentifierModes, setStockCountIdentifierModes] = useState<Record<string, StockCountIdentifierMode>>({});
  const [stockCountDetail, setStockCountDetail] = useState<any | null>(null);
  const [selectedStockCountKeys, setSelectedStockCountKeys] = useState<string[]>([]);
  const [stockCountLoading, setStockCountLoading] = useState(false);
  const [adjustments, setAdjustments] = useState<any[]>([]);
  const [adjustmentDraft, setAdjustmentDraft] = useState<AdjustmentDraft | null>(null);
  const [adjustmentDetail, setAdjustmentDetail] = useState<any | null>(null);
  const [transfers, setTransfers] = useState<any[]>([]);
  const [transferDraft, setTransferDraft] = useState<TransferDraft | null>(null);
  const [transferIdentifiersOpen, setTransferIdentifiersOpen] = useState(false);
  const [transferDetail, setTransferDetail] = useState<any | null>(null);
  const [internalHolds, setInternalHolds] = useState<any[]>([]);
  const [internalHoldDraft, setInternalHoldDraft] = useState<InternalHoldDraft | null>(null);
  const [internalHoldDetail, setInternalHoldDetail] = useState<any | null>(null);
  const [disposals, setDisposals] = useState<any[]>([]);
  const [disposalDraft, setDisposalDraft] = useState<DisposalDraft | null>(null);
  const [disposalDetail, setDisposalDetail] = useState<any | null>(null);
  const [costAdjustments, setCostAdjustments] = useState<any[]>([]);
  const [costAdjustmentDraft, setCostAdjustmentDraft] = useState<CostAdjustmentDraft | null>(null);
  const [costAdjustmentDetail, setCostAdjustmentDetail] = useState<any | null>(null);
  const [locationDraft, setLocationDraft] = useState<LocationDraft | null>(null);
  const [inventoryView, setInventoryView] = useState<InventoryView>('stock');
  const [locationSearchFilter, setLocationSearchFilter] = useState('');
  const [locationStatusFilter, setLocationStatusFilter] = useState('');
  const [locationAisleFilter, setLocationAisleFilter] = useState('');
  const [locationShelfFilter, setLocationShelfFilter] = useState('');
  const [locationBinFilter, setLocationBinFilter] = useState('');
  const [agingReport, setAgingReport] = useState<any | null>(null);
  const [agingBucketFilter, setAgingBucketFilter] = useState('');
  const [agingLoading, setAgingLoading] = useState(false);
  const [reconciliationReport, setReconciliationReport] = useState<any | null>(null);
  const [reconciliationIssueFilter, setReconciliationIssueFilter] = useState('');
  const [reconciliationLoading, setReconciliationLoading] = useState(false);
  const {
    categories,
    exportInventorySnapshot,
    filteredInventory,
    inventoryDashboard,
    inventoryPage,
    inventoryTotal,
    inventoryTotalPages,
    inventoryLocations,
    inventoryAllLocations,
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
    ledgerReason,
    setLedgerReason,
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
  const canReserveInventory = usePermission('inventory:reserve');
  const canCountInventory = usePermission('inventory:count');
  const canApproveInventory = isSuperAdmin || usePermission('inventory:approve');
  const inventoryLocationOptionSource = inventoryAllLocations?.length ? inventoryAllLocations : inventoryLocations;
  const loadedLocationAreas = Array.from(
    new Set((inventoryLocationOptionSource || [])
      .map((location: any) => parseInventoryLocationCode(String(location.code || ''))?.area || '')
      .filter(Boolean)),
  ).sort() as string[];
  const defaultLocationAreaValues = defaultLocationAreaOptions.map(([value]) => value);
  const locationAisleOptions = [
    ...defaultLocationAreaValues,
    ...loadedLocationAreas.filter((value) => !defaultLocationAreaValues.includes(value)),
  ];
  const locationShelfOptions = Array.from(
    new Set((inventoryLocationOptionSource || [])
      .filter((location: any) => !locationAisleFilter || String(location.code || '').startsWith(`${locationAisleFilter}-`))
      .map((location: any) => parseInventoryLocationCode(String(location.code || ''))?.shelf || '')
      .filter(Boolean)),
  ).sort();
  const locationBinOptions = Array.from(
    new Set((inventoryLocationOptionSource || [])
      .filter((location: any) => !locationAisleFilter || String(location.code || '').startsWith(`${locationAisleFilter}-`))
      .filter((location: any) => !locationShelfFilter || parseInventoryLocationCode(String(location.code || ''))?.shelf === locationShelfFilter)
      .map((location: any) => parseInventoryLocationCode(String(location.code || ''))?.bin || '')
      .filter(Boolean)),
  ).sort();
  const locationAreaLabels = new Map<string, string>([
    ...defaultLocationAreaOptions,
    ...(inventoryLocationOptionSource || []).map((location: any) => {
      const area = parseInventoryLocationCode(String(location.code || ''))?.area || '';
      return [area, inventoryLocationAreaLabel(area, String(location.zone || ''))] as [string, string];
    }).filter(([area]) => Boolean(area)),
  ]);

  function renderInventoryLocationCell(row: any) {
    const summary = inventoryLocationSummary(row);
    if (summary.locations.length === 0) {
      return <span className="text-xs font-semibold text-slate-500">{summary.primary}</span>;
    }
    return (
      <button
        type="button"
        onClick={() => setLocationDetailModal({ row, locations: summary.locations })}
        className="inline-flex items-center gap-1.5 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-800 hover:border-emerald-300 hover:bg-emerald-100 whitespace-nowrap"
        title="Xem danh sách kệ của sản phẩm"
      >
        <ClipboardList className="h-3.5 w-3.5 shrink-0" />
        <span>Xem kệ</span>
        <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] font-black text-emerald-700 shrink-0">{summary.locations.length}</span>
      </button>
    );
  }

  function createLocationDraftForArea(area = locationAisleFilter): LocationDraft {
    const normalizedArea = String(area || '').trim().toUpperCase();
    const safeArea = normalizedArea || 'A';
    const areaLabel = locationAreaLabels.get(safeArea) || inventoryLocationAreaLabel(safeArea);
    const isWarehouse = safeArea === 'MAIN';
    return {
      code: isWarehouse ? 'MAIN' : `${safeArea}-01-01`,
      name: isWarehouse ? areaLabel : `${areaLabel} - Kệ 01 - Ô 01`,
      zone: areaLabel,
      purpose: defaultLocationAreaPurpose[safeArea] || 'STORAGE',
      sortOrder: 0,
      allowMixedSku: true,
      lengthCm: isWarehouse ? '' : 100,
      widthCm: isWarehouse ? '' : 60,
      heightCm: isWarehouse ? '' : 40,
      usableRatio: 0.75,
      description: '',
    };
  }

  async function loadPendingEditRequests() {
    const rows = await adminInventoryApi.adminListIdentifierEditRequests('PENDING').catch(() => []);
    setPendingEditRequests(Array.isArray(rows) ? rows : []);
  }

  async function loadPendingLocationRequests() {
    const rows = await adminInventoryApi.adminListIdentifierLocationRequests('PENDING').catch(() => []);
    setPendingLocationRequests(Array.isArray(rows) ? rows : []);
  }

  async function loadStockCounts() {
    const rows = await adminInventoryApi.adminListStockCounts(query || '').catch(() => []);
    setStockCounts(Array.isArray(rows) ? rows : []);
  }

  async function loadAdjustments() {
    const rows = await adminInventoryApi.adminListAdjustments(query || '').catch(() => []);
    setAdjustments(Array.isArray(rows) ? rows : []);
  }

  async function loadTransfers() {
    const rows = await adminInventoryApi.adminListTransfers(query || '').catch(() => []);
    setTransfers(Array.isArray(rows) ? rows : []);
  }

  async function loadInternalHolds() {
    const rows = await adminInventoryApi.adminListInternalHolds(query || '').catch(() => []);
    setInternalHolds(Array.isArray(rows) ? rows : []);
  }

  async function loadDisposals() {
    const rows = await adminInventoryApi.adminListDisposals(query || '').catch(() => []);
    setDisposals(Array.isArray(rows) ? rows : []);
  }

  async function loadCostAdjustments() {
    const rows = await adminInventoryApi.adminListCostAdjustments(query || '').catch(() => []);
    setCostAdjustments(Array.isArray(rows) ? rows : []);
  }

  async function loadInventoryAgingReport(bucket = agingBucketFilter) {
    setAgingLoading(true);
    try {
      const report = await adminInventoryApi.adminGetInventoryAgingReport(query || '', bucket || '');
      setAgingReport(report && typeof report === 'object' ? report : null);
    } catch (err) {
      console.error('Không thể tải báo cáo tuổi tồn kho:', err);
      setAgingReport(null);
    } finally {
      setAgingLoading(false);
    }
  }

  async function loadInventoryReconciliationReport(issueType = reconciliationIssueFilter) {
    setReconciliationLoading(true);
    try {
      const report = await adminInventoryApi.adminGetInventoryReconciliationReport(query || '', issueType || '');
      setReconciliationReport(report && typeof report === 'object' ? report : null);
    } catch (err) {
      console.error('Không thể tải báo cáo đối soát tồn kho:', err);
      setReconciliationReport(null);
    } finally {
      setReconciliationLoading(false);
    }
  }

  async function allocateLegacyInventory(item: any) {
    const locations = (inventoryLocationOptionSource || []).filter((location: any) =>
      String(location.status || 'ACTIVE') === 'ACTIVE'
      && ['STORAGE', 'VIRTUAL'].includes(String(location.purpose || 'STORAGE').toUpperCase()),
    );
    const locationCode = window.prompt(
      `Nhập mã kệ nhận tồn chưa phân bổ. Kệ khả dụng: ${locations.slice(0, 12).map((location: any) => location.code).join(', ')}`,
    )?.trim().toUpperCase();
    if (!locationCode) return;
    const location = locations.find((entry: any) => String(entry.code || '').toUpperCase() === locationCode);
    if (!location) {
      window.alert('Không tìm thấy kệ đang hoạt động với mã đã nhập.');
      return;
    }
    const maximum = Math.max(0, Number(item.differenceQuantity || 0));
    const quantity = Number(window.prompt(`Số lượng phân bổ vào kệ ${location.code} (tối đa ${maximum}):`, String(maximum)));
    if (!Number.isInteger(quantity) || quantity <= 0 || quantity > maximum) {
      window.alert('Số lượng phân bổ không hợp lệ.');
      return;
    }
    const unitCost = Number(window.prompt('Giá vốn đơn vị cho tồn cũ (có thể nhập 0 nếu chưa xác định):', '0'));
    if (!Number.isFinite(unitCost) || unitCost < 0) {
      window.alert('Giá vốn không hợp lệ.');
      return;
    }
    try {
      await adminInventoryApi.adminAllocateLegacyInventory({
        productId: item.productId,
        variantId: item.variantId || null,
        locationId: location.id,
        quantity,
        unitCost,
        note: `Phân bổ tồn chưa có kệ cho ${item.variantSku || item.productSku || item.productName}`,
      });
      await loadInventoryReconciliationReport(reconciliationIssueFilter);
      if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
      if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể phân bổ tồn vào kệ.');
    }
  }

  async function submitLocationDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!locationDraft) return;
    if (!locationDraft.code.trim() || !locationDraft.name.trim()) {
      window.alert('Vui lòng nhập mã kệ và tên kệ.');
      return;
    }
    const areaCode = resolveInventoryLocationArea(locationDraft.code);
    const isWarehouseLocation = areaCode === 'MAIN';
    const payload = {
      code: locationDraft.code.trim(),
      name: locationDraft.name.trim(),
      zone: locationDraft.zone.trim() || (areaCode ? inventoryLocationAreaLabel(areaCode) : null),
      purpose: areaCode ? (defaultLocationAreaPurpose[areaCode] || 'STORAGE') : (locationDraft.purpose || 'STORAGE'),
      sortOrder: Math.max(0, Number(locationDraft.sortOrder || 0)),
      allowMixedSku: Boolean(locationDraft.allowMixedSku),
      lengthCm: isWarehouseLocation || locationDraft.lengthCm === '' ? null : Number(locationDraft.lengthCm || 0),
      widthCm: isWarehouseLocation || locationDraft.widthCm === '' ? null : Number(locationDraft.widthCm || 0),
      heightCm: isWarehouseLocation || locationDraft.heightCm === '' ? null : Number(locationDraft.heightCm || 0),
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
      status: locationStatusFilter,
      aisle: locationAisleFilter,
      shelf: locationShelfFilter,
      bin: locationBinFilter,
    });
  }

  async function clearLocationFilters() {
    setLocationSearchFilter('');
    setLocationStatusFilter('');
    setLocationAisleFilter('');
    setLocationShelfFilter('');
    setLocationBinFilter('');
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations('', {});
  }

  useEffect(() => {
    void loadPendingEditRequests();
    void loadPendingLocationRequests();
    void loadStockCounts();
    void loadAdjustments();
    void loadTransfers();
    void loadInternalHolds();
    void loadDisposals();
    void loadCostAdjustments();
    void loadInventoryAgingReport('');
    void loadInventoryReconciliationReport('');
    if (typeof loadInventoryLocations === 'function') void loadInventoryLocations();
    if (typeof loadInventoryLedger === 'function') void loadInventoryLedger(query);
  }, []);

  useEffect(() => {
    if (!locationIdentifierModal) return;
    const nextRow = (filteredInventory || []).find((row: any) => (
      String(row.productId || row.id || '') === String(locationIdentifierModal.row.productId || locationIdentifierModal.row.id || '')
      && String(row.variantId || '') === String(locationIdentifierModal.row.variantId || '')
    ));
    if (!nextRow) return;
    const nextLocation = inventoryLocationEntries(nextRow).find((location) => (
      String(location.id) === String(locationIdentifierModal.location.id)
      || (location.code && location.code === locationIdentifierModal.location.code)
    ));
    if (!nextLocation) return;
    if (nextRow === locationIdentifierModal.row && nextLocation === locationIdentifierModal.location) return;
    setLocationIdentifierModal({ row: nextRow, location: nextLocation });
  }, [filteredInventory]);

  async function openIssueSuggestionModal(row: any) {
    const rawQuantity = window.prompt('Nhập số lượng cần gợi ý xuất kho:', '1');
    if (!rawQuantity) return;
    const quantity = Math.max(1, Number(rawQuantity || 1));
    const suggestions = await adminInventoryApi.adminListIssueSuggestions(row.productId, row.variantId || null, quantity).catch(() => []);
    setIssueSuggestionModal({ row, quantity, suggestions: Array.isArray(suggestions) ? suggestions : [] });
  }

  async function decideIdentifierEdit(requestId: string, decision: 'APPROVED' | 'CANCELLED') {
    const note = window.prompt(decision === 'APPROVED' ? 'Ghi chú duyệt (không bắt buộc):' : 'Lý do hủy yêu cầu (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminDecideIdentifierEditRequest(requestId, { decision, note });
    await loadPendingEditRequests();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  async function requestLocationIdentifierEdit(identifierType: 'IMEI' | 'SERIAL', identifier: InventoryLocationIdentifier) {
    const label = identifierType === 'IMEI' ? 'IMEI' : 'serial number';
    const newValue = window.prompt(`Nhập ${label} đúng:`, identifier.code)?.trim();
    if (!newValue || newValue === identifier.code) return;
    if (!identifier.id) {
      window.alert('Không tìm thấy ID mã định danh để tạo yêu cầu chỉnh sửa. Vui lòng tải lại dữ liệu tồn kho.');
      return;
    }
    const reason = window.prompt('Nhập lý do chỉnh sửa mã định danh:')?.trim();
    if (!reason) return;
    await adminInventoryApi.adminCreateIdentifierEditRequest({
      identifierType,
      identifierId: identifier.id,
      newValue,
      reason,
    });
    await loadPendingEditRequests();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
    window.alert('Đã gửi yêu cầu chỉnh sửa mã định danh. Danh sách trong kệ sẽ cập nhật sau khi yêu cầu được duyệt.');
  }

  function openIdentifierLocationDraft(
    identifierType: 'IMEI' | 'SERIAL',
    identifier?: InventoryLocationIdentifier,
  ) {
    if (!locationIdentifierModal) return;
    setIdentifierLocationDraft({
      identifierType,
      identifierId: identifier?.id || null,
      identifierValue: identifier?.code || '',
      productId: String(locationIdentifierModal.row.productId || locationIdentifierModal.row.id || ''),
      variantId: locationIdentifierModal.row.variantId ? String(locationIdentifierModal.row.variantId) : null,
      productName: String(locationIdentifierModal.row.productName || locationIdentifierModal.row.name || 'Sản phẩm'),
      currentLocationCode: identifier ? locationIdentifierModal.location.code : 'Chưa gắn kệ',
      newLocationId: identifier ? '' : String(locationIdentifierModal.location.id),
      reason: '',
    });
  }

  async function submitIdentifierLocationRequest(event?: React.FormEvent) {
    event?.preventDefault();
    if (!identifierLocationDraft) return;
    if (!identifierLocationDraft.identifierValue.trim() || !identifierLocationDraft.newLocationId || identifierLocationDraft.reason.trim().length < 5) {
      window.alert('Vui lòng nhập mã định danh, kệ đích và lý do ít nhất 5 ký tự.');
      return;
    }
    await adminInventoryApi.adminCreateIdentifierLocationRequest({
      identifierType: identifierLocationDraft.identifierType,
      identifierId: identifierLocationDraft.identifierId,
      identifierValue: identifierLocationDraft.identifierValue.trim(),
      productId: identifierLocationDraft.productId,
      variantId: identifierLocationDraft.variantId,
      newLocationId: identifierLocationDraft.newLocationId,
      reason: identifierLocationDraft.reason.trim(),
    });
    setIdentifierLocationDraft(null);
    await loadPendingLocationRequests();
    window.alert('Đã gửi yêu cầu gán vị trí mã định danh để chờ duyệt.');
  }

  async function decideIdentifierLocation(requestId: string, decision: 'APPROVED' | 'CANCELLED') {
    const note = window.prompt(decision === 'APPROVED' ? 'Ghi chú duyệt vị trí (không bắt buộc):' : 'Lý do hủy yêu cầu (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminDecideIdentifierLocationRequest(requestId, { decision, note });
    await loadPendingLocationRequests();
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

  function generateTransferCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `CK${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  }

  function generateInternalHoldCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `GH${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  }

  function generateDisposalCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `XL${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  }

  function generateCostAdjustmentCode() {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return `GV${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
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

  function openTransferDraft(
    row: any,
    fromLocation?: InventoryLocationEntry,
    reason = 'CHUYEN_KE',
  ) {
    setTransferIdentifiersOpen(false);
    const locations = inventoryLocationEntries(row);
    const sourceLocation = fromLocation || locations.find((location) => Number(location.onHandQuantity || 0) > 0);
    if (!sourceLocation) {
      window.alert('Sản phẩm chưa có kệ nguồn để chuyển.');
      return;
    }
    const sourceLocationMaster = (inventoryLocationOptionSource || []).find(
      (location: any) => String(location.id || '') === String(sourceLocation.id),
    );
    const sourcePurpose = String(sourceLocationMaster?.purpose || sourceLocation.purpose || 'STORAGE').toUpperCase();
    const sourceIsSellable = ['STORAGE', 'VIRTUAL'].includes(sourcePurpose);
    const isStateTransfer = reason === 'CHUYEN_TRANG_THAI';
    const targetLocation = (inventoryLocationOptionSource || []).find((location: any) => (
      String(location.id || '') !== String(sourceLocation.id)
      && String(location.status || 'ACTIVE') === 'ACTIVE'
      && (
        !isStateTransfer
        || (['STORAGE', 'VIRTUAL'].includes(String(location.purpose || 'STORAGE').toUpperCase()) !== sourceIsSellable)
      )
    ));
    const movableStatuses = new Set([
      'IN_STOCK',
      'RETURNED',
      'WARRANTY',
      'IN_WARRANTY',
      'DEFECTIVE_RETURNED',
      'INSPECTION_PENDING',
    ]);
    const availableImeis = sourceLocation.imeis
      .filter((identifier) => movableStatuses.has(identifier.status))
      .sort((left, right) => Number(Boolean(right.isPrimary)) - Number(Boolean(left.isPrimary)))
    const availableSerialNumbers = sourceLocation.serialNumbers
      .filter((identifier) => movableStatuses.has(identifier.status));
    const availableIdentifierUnits = sourceLocation.identifierUnits.filter((unit) => movableStatuses.has(unit.status));
    setTransferDraft({
      referenceCode: generateTransferCode(),
      reason,
      note: '',
      line: {
        productId: String(row.productId || row.id),
        variantId: row.variantId ? String(row.variantId) : null,
        productName: String(row.productName || row.name || ''),
        sku: String(row.variantSku || row.productSku || row.sku || compactId(row.productId || row.id)),
        fromLocationId: String(sourceLocation.id),
        toLocationId: targetLocation ? String(targetLocation.id) : '',
        quantity: Math.max(1, Math.min(1, Number(sourceLocation.onHandQuantity || 0))),
        maxQuantity: Number(sourceLocation.onHandQuantity || 0),
        imeis: '',
        serialNumbers: '',
        availableImeis,
        availableSerialNumbers,
        identifierPairIds: [],
        availableIdentifierUnits,
        note: '',
      },
    });
  }

  function openInternalHoldDraft(row: any, location: InventoryLocationEntry) {
    if (Number(location.onHandQuantity || 0) <= 0) {
      window.alert('Kệ này không còn tồn để giữ nội bộ.');
      return;
    }
    setInternalHoldDraft({
      referenceCode: generateInternalHoldCode(),
      holdType: 'INTERNAL_HOLD',
      reason: 'Giữ hàng nội bộ chờ xử lý',
      note: '',
      line: {
        productId: String(row.productId || row.id),
        variantId: row.variantId ? String(row.variantId) : null,
        productName: String(row.productName || row.name || ''),
        sku: String(row.variantSku || row.productSku || row.sku || compactId(row.productId || row.id)),
        locationId: String(location.id),
        locationCode: String(location.code || ''),
        locationName: String(location.name || ''),
        quantity: 1,
        maxQuantity: Number(location.onHandQuantity || 0),
        note: '',
      },
    });
  }

  function openDisposalDraft(row: any, location: InventoryLocationEntry) {
    if (Number(location.onHandQuantity || 0) <= 0) {
      window.alert('Kệ này không còn tồn để xử lý.');
      return;
    }
    const movableStatuses = new Set([
      'IN_STOCK',
      'RETURNED',
      'WARRANTY',
      'IN_WARRANTY',
      'DEFECTIVE_RETURNED',
      'INSPECTION_PENDING',
    ]);
    const availableImeis = location.imeis
      .filter((identifier) => movableStatuses.has(identifier.status))
      .sort((left, right) => Number(Boolean(right.isPrimary)) - Number(Boolean(left.isPrimary)));
    const availableSerialNumbers = location.serialNumbers
      .filter((identifier) => movableStatuses.has(identifier.status));
    const availableIdentifierUnits = location.identifierUnits.filter((unit) => movableStatuses.has(unit.status));
    setDisposalDraft({
      referenceCode: generateDisposalCode(),
      dispositionType: 'SCRAP',
      reason: 'Hàng hỏng không thể bán',
      note: '',
      partnerName: '',
      recoveryValue: '',
      line: {
        productId: String(row.productId || row.id),
        variantId: row.variantId ? String(row.variantId) : null,
        productName: String(row.productName || row.name || ''),
        sku: String(row.variantSku || row.productSku || row.sku || compactId(row.productId || row.id)),
        locationId: String(location.id),
        locationCode: String(location.code || ''),
        locationName: String(location.name || ''),
        quantity: 1,
        maxQuantity: Number(location.onHandQuantity || 0),
        imeis: '',
        serialNumbers: '',
        availableImeis,
        availableSerialNumbers,
        identifierPairIds: [],
        availableIdentifierUnits,
        note: '',
      },
    });
  }

  function openCostAdjustmentDraft(row: any, location: InventoryLocationEntry) {
    if (Number(location.onHandQuantity || 0) <= 0) {
      window.alert('Kệ này không còn tồn để điều chỉnh giá vốn.');
      return;
    }
    setCostAdjustmentDraft({
      referenceCode: generateCostAdjustmentCode(),
      reason: 'Điều chỉnh giá vốn theo đối soát kế toán/kho',
      note: '',
      line: {
        productId: row.productId,
        variantId: row.variantId || null,
        productName: row.productName,
        sku: row.variantSku || row.productSku || '',
        locationId: location.id,
        locationCode: location.code,
        locationName: location.name,
        currentAverageUnitCost: Number(row.averageUnitCost || 0),
        newAverageUnitCost: Number(row.averageUnitCost || 0),
        note: '',
      },
    });
  }

  function inventoryItemKey(item: any) {
    return `${item.productId || item.id}-${item.variantId || 'base'}`;
  }

  function inventoryItemToStockCountLine(item: any, locationCode: string): StockCountDraft['lines'][number] | null {
    const productId = item.productId || item.id;
    if (!productId) return null;
    const location = (item.locations || []).find((entry: any) => String(entry.code || '') === locationCode);
    if (!location) return null;
    const expectedQuantity = Number(location.onHandQuantity || 0);
    const tracksImei = Boolean(item.tracksImei);
    const tracksSerialNumber = Boolean(item.tracksSerialNumber);
    return {
      key: inventoryItemKey(item),
      productId: String(productId),
      variantId: item.variantId ? String(item.variantId) : null,
      productName: String(item.productName || item.name || ''),
      sku: String(item.variantSku || item.productSku || item.sku || compactId(productId)),
      expectedQuantity,
      countedQuantity: tracksImei || tracksSerialNumber ? 0 : expectedQuantity,
      tracksImei,
      tracksSerialNumber,
      imeis: '',
      serialNumbers: '',
      availableImeis: Array.isArray(location.imeis) ? location.imeis : [],
      availableSerialNumbers: Array.isArray(location.serialNumbers) ? location.serialNumbers : [],
      identifierPairIds: [],
      availableIdentifierUnits: Array.isArray(location.identifierUnits) ? location.identifierUnits : [],
      note: '',
    };
  }

  function stockCountEligibleRows(rows = filteredInventory, locationCode = inventoryLocationFilter) {
    if (!locationCode) return [];
    return rows
      .filter((item: any) => 'physicalStock' in item || 'availableStock' in item)
      .map((item: any) => inventoryItemToStockCountLine(item, locationCode))
      .filter(Boolean) as StockCountDraft['lines'];
  }

  function openStockCountDraftFromRows(rows: StockCountDraft['lines'], scopeLabel: string, locationCode: string) {
    if (!rows.length) {
      window.alert('Không có dòng tồn kho để tạo phiếu kiểm kê.');
      return;
    }
    const location = (inventoryLocationOptionSource || []).find((entry: any) => String(entry.code || '') === locationCode);
    setStockCountIdentifierModes({});
    setStockCountDraft({
      referenceCode: generateStockCountCode(),
      reason: 'KIEM_KE_DINH_KY',
      note: scopeLabel,
      locationCode,
      locationName: String(location?.name || locationCode),
      lines: rows,
    });
  }

  function openSelectedStockCountDraft() {
    if (!inventoryLocationFilter) {
      window.alert('Vui lòng chọn một kệ hàng trước khi kiểm kê.');
      return;
    }
    const selectedKeys = new Set(selectedStockCountKeys);
    const rows = stockCountEligibleRows(filteredInventory, inventoryLocationFilter).filter((line) => selectedKeys.has(line.key));
    if (!rows.length) {
      window.alert('Vui lòng chọn ít nhất một dòng tồn kho để kiểm kê.');
      return;
    }
    openStockCountDraftFromRows(rows, `Kiểm kê kệ ${inventoryLocationFilter} theo danh sách đã chọn (${rows.length} dòng).`, inventoryLocationFilter);
  }

  async function openAllStockCountDraft() {
    if (!inventoryLocationFilter) {
      window.alert('Vui lòng chọn một kệ hàng trước khi kiểm kê.');
      return;
    }
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
      const rows = stockCountEligibleRows(allItems, inventoryLocationFilter);
      openStockCountDraftFromRows(rows, `Kiểm kê toàn bộ kệ ${inventoryLocationFilter} (${rows.length} dòng).`, inventoryLocationFilter);
    } finally {
      setStockCountLoading(false);
    }
  }

  async function openShelfStockCountDraft(location: InventoryLocationEntry) {
    const locationCode = String(location.code || '').trim();
    if (!locationCode) return;
    setStockCountLoading(true);
    try {
      const pageSize = 100;
      const first = await adminInventoryApi.adminListLevels('', '', locationCode, '', '', 1, pageSize);
      const allItems = Array.isArray(first?.items) ? [...first.items] : [];
      const totalPages = Math.max(1, Number(first?.totalPages || 1));
      for (let page = 2; page <= totalPages; page += 1) {
        const result = await adminInventoryApi.adminListLevels('', '', locationCode, '', '', page, pageSize);
        if (Array.isArray(result?.items)) allItems.push(...result.items);
      }
      const rows = stockCountEligibleRows(allItems, locationCode);
      openStockCountDraftFromRows(rows, `Kiểm kê toàn bộ kệ ${locationCode} (${rows.length} dòng).`, locationCode);
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

  function setStockCountIdentifierMode(lineKey: string, identifierType: 'IMEI' | 'SERIAL', mode: StockCountIdentifierMode) {
    setStockCountIdentifierModes((current) => ({ ...current, [`${lineKey}:${identifierType}`]: mode }));
  }

  function getStockCountIdentifierMode(line: StockCountDraft['lines'][number], identifierType: 'IMEI' | 'SERIAL') {
    const key = `${line.key}:${identifierType}`;
    const fallback = identifierType === 'IMEI'
      ? line.availableImeis.length > 0
      : line.availableSerialNumbers.length > 0;
    return stockCountIdentifierModes[key] || (fallback ? 'select' : 'manual');
  }

  function updateStockCountIdentifiers(lineKey: string, identifierType: 'IMEI' | 'SERIAL', value: string, selected: boolean) {
    setStockCountDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        lines: current.lines.map((line) => {
          if (line.key !== lineKey) return line;
          const field = identifierType === 'IMEI' ? 'imeis' : 'serialNumbers';
          const currentValues = splitIdentifierText(line[field]);
          const nextValues = selected
            ? Array.from(new Set([...currentValues, value]))
            : currentValues.filter((item) => item !== value);
          return { ...line, [field]: joinIdentifierText(nextValues) };
        }),
      };
    });
  }

  function updateStockCountIdentifierUnit(lineKey: string, unit: InventoryIdentifierUnit, selected: boolean) {
    setStockCountDraft((current) => current ? {
      ...current,
      lines: current.lines.map((line) => {
        if (line.key !== lineKey) return line;
        const identifierPairIds = selected ? Array.from(new Set([...line.identifierPairIds, unit.pairId])) : line.identifierPairIds.filter((id) => id !== unit.pairId);
        const units = line.availableIdentifierUnits.filter((item) => identifierPairIds.includes(item.pairId));
        return { ...line, identifierPairIds, countedQuantity: units.length, imeis: joinIdentifierText(units.flatMap((item) => [item.imei1, item.imei2].filter(Boolean) as string[])), serialNumbers: joinIdentifierText(units.map((item) => item.serialNumber)) };
      }),
    } : current);
  }

  async function submitStockCountDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!stockCountDraft) return;
    await adminInventoryApi.adminCreateStockCount({
      referenceCode: stockCountDraft.referenceCode.trim(),
      reason: stockCountDraft.reason.trim() || 'KIEM_KE_DINH_KY',
      note: stockCountDraft.note.trim() || null,
      locationCode: stockCountDraft.locationCode,
      locationName: stockCountDraft.locationName,
      lines: stockCountDraft.lines.map((line) => ({
        productId: line.productId,
        variantId: line.variantId,
        expectedQuantity: line.expectedQuantity,
        countedQuantity: line.availableIdentifierUnits.length > 0
          ? line.identifierPairIds.length
          : line.tracksImei
          ? splitIdentifierText(line.imeis).length
          : line.tracksSerialNumber
            ? splitIdentifierText(line.serialNumbers).length
            : Math.max(0, Number(line.countedQuantity || 0)),
        imeis: splitIdentifierText(line.imeis),
        serialNumbers: splitIdentifierText(line.serialNumbers),
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

  async function submitTransferDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!transferDraft) return;
    if (!transferDraft.line.fromLocationId || !transferDraft.line.toLocationId) {
      window.alert('Vui lòng chọn đủ kệ nguồn và kệ đích.');
      return;
    }
    if (transferDraft.line.fromLocationId === transferDraft.line.toLocationId) {
      window.alert('Kệ nguồn và kệ đích phải khác nhau.');
      return;
    }
    if (transferDraft.line.availableIdentifierUnits.length > 0 && transferDraft.line.identifierPairIds.length === 0) {
      window.alert('Vui lòng chọn ít nhất một thiết bị IMEI/serial cần chuyển.');
      return;
    }
    await adminInventoryApi.adminCreateTransfer({
      referenceCode: transferDraft.referenceCode.trim(),
      reason: transferDraft.reason.trim() || 'CHUYEN_KE',
      note: transferDraft.note.trim() || null,
      lines: [{
        productId: transferDraft.line.productId,
        variantId: transferDraft.line.variantId,
        fromLocationId: transferDraft.line.fromLocationId,
        toLocationId: transferDraft.line.toLocationId,
        quantity: Math.max(1, Number(transferDraft.line.quantity || 1)),
        imeis: splitIdentifierText(transferDraft.line.imeis),
        serialNumbers: splitIdentifierText(transferDraft.line.serialNumbers),
        identifierPairIds: transferDraft.line.identifierPairIds,
        note: transferDraft.line.note.trim() || null,
      }],
    });
    setTransferDraft(null);
    await loadTransfers();
  }

  function updateTransferIdentifiers(identifierType: 'IMEI' | 'SERIAL', value: string, selected: boolean) {
    setTransferDraft((current) => {
      if (!current) return current;
      const field = identifierType === 'IMEI' ? 'imeis' : 'serialNumbers';
      const currentValues = splitIdentifierText(current.line[field]);
      const nextValues = selected
        ? Array.from(new Set([...currentValues, value]))
        : currentValues.filter((item) => item !== value);
      const nextImeiCount = identifierType === 'IMEI' ? nextValues.length : splitIdentifierText(current.line.imeis).length;
      const nextSerialCount = identifierType === 'SERIAL' ? nextValues.length : splitIdentifierText(current.line.serialNumbers).length;
      const identifierQuantity = Math.max(nextImeiCount, nextSerialCount);
      return {
        ...current,
        line: {
          ...current.line,
          [field]: joinIdentifierText(nextValues),
          quantity: identifierQuantity > 0
            ? Math.min(Math.max(1, identifierQuantity), Math.max(1, Number(current.line.maxQuantity || 1)))
            : current.line.quantity,
        },
      };
    });
  }

  function updateTransferIdentifierUnit(unit: InventoryIdentifierUnit, selected: boolean) {
    setTransferDraft((current) => {
      if (!current) return current;
      const identifierPairIds = selected
        ? Array.from(new Set([...current.line.identifierPairIds, unit.pairId]))
        : current.line.identifierPairIds.filter((id) => id !== unit.pairId);
      return { ...current, line: { ...current.line, identifierPairIds, quantity: Math.max(1, identifierPairIds.length || current.line.quantity) } };
    });
  }

  function updateTransferIdentifierText(identifierType: 'IMEI' | 'SERIAL', value: string) {
    setTransferDraft((current) => {
      if (!current) return current;
      const field = identifierType === 'IMEI' ? 'imeis' : 'serialNumbers';
      const nextValues = splitIdentifierText(value);
      const nextImeiCount = identifierType === 'IMEI' ? nextValues.length : splitIdentifierText(current.line.imeis).length;
      const nextSerialCount = identifierType === 'SERIAL' ? nextValues.length : splitIdentifierText(current.line.serialNumbers).length;
      const identifierQuantity = Math.max(nextImeiCount, nextSerialCount);
      return {
        ...current,
        line: {
          ...current.line,
          [field]: value,
          quantity: identifierQuantity > 0
            ? Math.min(Math.max(1, identifierQuantity), Math.max(1, Number(current.line.maxQuantity || 1)))
            : current.line.quantity,
        },
      };
    });
  }

  async function decideTransfer(referenceCode: string, status: 'APPROVED' | 'COMPLETED' | 'CANCELLED') {
    const promptLabel = status === 'APPROVED'
      ? 'Ghi chú duyệt chuyển kệ (không bắt buộc):'
      : status === 'COMPLETED'
        ? 'Ghi chú hoàn tất chuyển kệ (không bắt buộc):'
        : 'Lý do hủy phiếu chuyển kệ (không bắt buộc):';
    const note = window.prompt(promptLabel)?.trim() || null;
    await adminInventoryApi.adminUpdateTransferStatus(referenceCode, { status, note });
    await loadTransfers();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
  }

  async function submitInternalHoldDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!internalHoldDraft) return;
    if (!internalHoldDraft.reason.trim()) {
      window.alert('Vui lòng nhập lý do giữ nội bộ.');
      return;
    }
    await adminInventoryApi.adminCreateInternalHold({
      referenceCode: internalHoldDraft.referenceCode.trim(),
      holdType: internalHoldDraft.holdType,
      reason: internalHoldDraft.reason.trim(),
      note: internalHoldDraft.note.trim() || null,
      lines: [{
        productId: internalHoldDraft.line.productId,
        variantId: internalHoldDraft.line.variantId,
        locationId: internalHoldDraft.line.locationId,
        quantity: Math.max(1, Number(internalHoldDraft.line.quantity || 1)),
        note: internalHoldDraft.line.note.trim() || null,
      }],
    });
    setInternalHoldDraft(null);
    await loadInternalHolds();
  }

  async function decideInternalHold(referenceCode: string, status: 'APPROVED' | 'COMPLETED' | 'CANCELLED') {
    const promptLabel = status === 'APPROVED'
      ? 'Ghi chú duyệt giữ nội bộ (không bắt buộc):'
      : status === 'COMPLETED'
        ? 'Ghi chú mở khóa tồn (không bắt buộc):'
        : 'Lý do hủy phiếu giữ nội bộ (không bắt buộc):';
    const note = window.prompt(promptLabel)?.trim() || null;
    await adminInventoryApi.adminUpdateInternalHoldStatus(referenceCode, { status, note });
    await loadInternalHolds();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
  }

  async function submitDisposalDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!disposalDraft) return;
    if (!disposalDraft.reason.trim()) {
      window.alert('Vui lòng nhập lý do xử lý tồn.');
      return;
    }
    if (disposalDraft.line.availableIdentifierUnits.length > 0 && disposalDraft.line.identifierPairIds.length === 0) {
      window.alert('Vui lòng chọn ít nhất một thiết bị IMEI/serial cần xử lý.');
      return;
    }
    await adminInventoryApi.adminCreateDisposal({
      referenceCode: disposalDraft.referenceCode.trim(),
      dispositionType: disposalDraft.dispositionType,
      reason: disposalDraft.reason.trim(),
      note: disposalDraft.note.trim() || null,
      partnerName: disposalDraft.partnerName.trim() || null,
      recoveryValue: disposalDraft.recoveryValue === '' ? null : Number(disposalDraft.recoveryValue || 0),
      lines: [{
        productId: disposalDraft.line.productId,
        variantId: disposalDraft.line.variantId,
        locationId: disposalDraft.line.locationId,
        quantity: Math.max(1, Number(disposalDraft.line.quantity || 1)),
        imeis: splitIdentifierText(disposalDraft.line.imeis),
        serialNumbers: splitIdentifierText(disposalDraft.line.serialNumbers),
        note: disposalDraft.line.note.trim() || null,
      }],
    });
    setDisposalDraft(null);
    await loadDisposals();
  }

  function updateDisposalIdentifiers(identifierType: 'IMEI' | 'SERIAL', value: string, selected: boolean) {
    setDisposalDraft((current) => {
      if (!current) return current;
      const field = identifierType === 'IMEI' ? 'imeis' : 'serialNumbers';
      const currentValues = splitIdentifierText(current.line[field]);
      const nextValues = selected
        ? Array.from(new Set([...currentValues, value]))
        : currentValues.filter((item) => item !== value);
      const nextImeiCount = identifierType === 'IMEI' ? nextValues.length : splitIdentifierText(current.line.imeis).length;
      const nextSerialCount = identifierType === 'SERIAL' ? nextValues.length : splitIdentifierText(current.line.serialNumbers).length;
      const identifierQuantity = Math.max(nextImeiCount, nextSerialCount);
      return {
        ...current,
        line: {
          ...current.line,
          [field]: joinIdentifierText(nextValues),
          quantity: identifierQuantity > 0
            ? Math.min(Math.max(1, identifierQuantity), Math.max(1, Number(current.line.maxQuantity || 1)))
            : current.line.quantity,
        },
      };
    });
  }

  function updateDisposalIdentifierUnit(unit: InventoryIdentifierUnit, selected: boolean) {
    setDisposalDraft((current) => {
      if (!current) return current;
      const identifierPairIds = selected ? Array.from(new Set([...current.line.identifierPairIds, unit.pairId])) : current.line.identifierPairIds.filter((id) => id !== unit.pairId);
      const units = current.line.availableIdentifierUnits.filter((item) => identifierPairIds.includes(item.pairId));
      return { ...current, line: { ...current.line, identifierPairIds, quantity: Math.max(1, units.length || current.line.quantity), imeis: joinIdentifierText(units.flatMap((item) => [item.imei1, item.imei2].filter(Boolean) as string[])), serialNumbers: joinIdentifierText(units.map((item) => item.serialNumber)) } };
    });
  }

  function updateDisposalIdentifierText(identifierType: 'IMEI' | 'SERIAL', value: string) {
    setDisposalDraft((current) => {
      if (!current) return current;
      const field = identifierType === 'IMEI' ? 'imeis' : 'serialNumbers';
      const nextValues = splitIdentifierText(value);
      const nextImeiCount = identifierType === 'IMEI' ? nextValues.length : splitIdentifierText(current.line.imeis).length;
      const nextSerialCount = identifierType === 'SERIAL' ? nextValues.length : splitIdentifierText(current.line.serialNumbers).length;
      const identifierQuantity = Math.max(nextImeiCount, nextSerialCount);
      return {
        ...current,
        line: {
          ...current.line,
          [field]: value,
          quantity: identifierQuantity > 0
            ? Math.min(Math.max(1, identifierQuantity), Math.max(1, Number(current.line.maxQuantity || 1)))
            : current.line.quantity,
        },
      };
    });
  }

  async function decideDisposal(referenceCode: string, status: 'APPROVED' | 'COMPLETED' | 'CANCELLED') {
    const promptLabel = status === 'APPROVED'
      ? 'Ghi chú duyệt phiếu xử lý tồn (không bắt buộc):'
      : status === 'COMPLETED'
        ? 'Ghi chú hoàn tất xử lý tồn (không bắt buộc):'
        : 'Lý do hủy phiếu xử lý tồn (không bắt buộc):';
    const note = window.prompt(promptLabel)?.trim() || null;
    await adminInventoryApi.adminUpdateDisposalStatus(referenceCode, { status, note });
    await loadDisposals();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
    if (typeof loadInventoryLocations === 'function') await loadInventoryLocations();
  }

  async function submitCostAdjustmentDraft(event?: React.FormEvent) {
    event?.preventDefault();
    if (!costAdjustmentDraft) return;
    if (!costAdjustmentDraft.reason.trim()) {
      window.alert('Vui lòng nhập lý do điều chỉnh giá vốn.');
      return;
    }
    await adminInventoryApi.adminCreateCostAdjustment({
      referenceCode: costAdjustmentDraft.referenceCode.trim(),
      reason: costAdjustmentDraft.reason.trim(),
      note: costAdjustmentDraft.note.trim() || null,
      lines: [{
        productId: costAdjustmentDraft.line.productId,
        variantId: costAdjustmentDraft.line.variantId,
        locationId: costAdjustmentDraft.line.locationId,
        newAverageUnitCost: Number(costAdjustmentDraft.line.newAverageUnitCost || 0),
        lotCosts: [],
        note: costAdjustmentDraft.line.note.trim() || null,
      }],
    });
    setCostAdjustmentDraft(null);
    await loadCostAdjustments();
  }

  async function decideCostAdjustment(referenceCode: string, status: 'APPROVED' | 'COMPLETED' | 'CANCELLED') {
    const promptLabel = status === 'APPROVED'
      ? 'Ghi chú duyệt phiếu giá vốn (không bắt buộc):'
      : status === 'COMPLETED'
        ? 'Ghi chú hoàn tất điều chỉnh giá vốn (không bắt buộc):'
        : 'Lý do hủy phiếu giá vốn (không bắt buộc):';
    const note = window.prompt(promptLabel)?.trim() || null;
    await adminInventoryApi.adminUpdateCostAdjustmentStatus(referenceCode, { status, note });
    await loadCostAdjustments();
    if (typeof loadInventoryLevels === 'function') await loadInventoryLevels(query);
  }

  async function createConsolidationTransfer(row: any, targetLocation: InventoryLocationEntry) {
    const sourceLocations = inventoryLocationEntries(row).filter((location) => (
      String(location.id) !== String(targetLocation.id) && Number(location.onHandQuantity || 0) > 0
    ));
    if (!sourceLocations.length) {
      window.alert('Không có kệ nguồn khác để gom về kệ này.');
      return;
    }
    if (!window.confirm(`Gom ${sourceLocations.length} kệ của sản phẩm này về ${targetLocation.code}?`)) return;
    await adminInventoryApi.adminCreateTransfer({
      referenceCode: generateTransferCode(),
      reason: 'GOM_KE',
      note: `Gom cùng SKU từ ${sourceLocations.length} kệ về ${targetLocation.code}.`,
      lines: sourceLocations.map((sourceLocation) => ({
        productId: String(row.productId || row.id),
        variantId: row.variantId ? String(row.variantId) : null,
        fromLocationId: sourceLocation.id,
        toLocationId: targetLocation.id,
        quantity: Number(sourceLocation.onHandQuantity || 0),
        imeis: sourceLocation.imeis.filter((identifier) => identifier.status === 'IN_STOCK').map((identifier) => identifier.code),
        serialNumbers: sourceLocation.serialNumbers.filter((identifier) => identifier.status === 'IN_STOCK').map((identifier) => identifier.code),
        note: `Gom từ ${sourceLocation.code} về ${targetLocation.code}.`,
      })),
    });
    await loadTransfers();
    window.alert('Đã tạo phiếu gom kệ ở trạng thái nháp để chờ duyệt.');
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
        <button
          type="button"
          onClick={() => setInventoryView('aging')}
          className={`h-9 rounded-lg px-4 text-sm font-bold transition ${inventoryView === 'aging' ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
        >
          Tuổi tồn kho
        </button>
        <button
          type="button"
          onClick={() => setInventoryView('reconciliation')}
          className={`h-9 rounded-lg px-4 text-sm font-bold transition ${inventoryView === 'reconciliation' ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
        >
          Đối soát
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
        <Select
          noLabel={true}
          label="Danh mục"
          value={inventoryCategoryFilter}
          onChange={(value) => {
            setInventoryCategoryFilter(value);
            setInventoryBrandFilter('');
          }}
          options={[['', 'Tất cả danh mục'], ...categories.map((c: any) => [String(c.id), c.parentName ? `${c.parentName} / ${c.name}` : c.name] as [string, string])]}
        />
        <Select noLabel={true} label="Thương hiệu" value={inventoryBrandFilter} onChange={setInventoryBrandFilter} options={inventoryBrandOptions} />
        <Select noLabel={true} label="Tồn kho" value={inventoryStockFilter || ''} onChange={setInventoryStockFilter} options={[['', 'Tất cả tồn kho'], ['LOW', 'Hàng sắp hết'], ['IN_STOCK', 'Còn tồn'], ['RESERVED', 'Đang giữ']]} />
        <Select
          noLabel={true}
          label="Kệ hàng"
          value={inventoryLocationFilter || ''}
          onChange={setInventoryLocationFilter}
          options={[
            ['', 'Tất cả kệ hàng'],
            ...(inventoryLocationOptionSource || []).map((location: any) => [String(location.code), `${location.code} - ${location.name}`] as [string, string]),
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
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="text-sm font-bold text-slate-900">Danh mục kệ hàng</div>
            <div className="text-xs font-semibold text-slate-500">Chuẩn hóa vị trí lưu kho để nhập, lọc tồn và truy vết IMEI/serial.</div>
          </div>
          <button
            type="button"
            onClick={() => setLocationDraft(createLocationDraftForArea())}
            className="inline-flex items-center gap-1.5 h-9 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 px-4 text-xs font-bold text-white shadow-sm transition-all hover:from-emerald-600 hover:to-teal-700 hover:shadow-md"
          >
            <Plus className="h-4 w-4" />
            <span>Thêm kệ</span>
          </button>
        </div>
        <div className="mb-5 grid gap-3 rounded-xl border border-slate-100 bg-slate-50/50 p-4 md:grid-cols-4 xl:grid-cols-8">
          <input
            value={locationSearchFilter}
            onChange={(event) => setLocationSearchFilter(event.target.value)}
            className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            placeholder="Tìm mã, tên, dãy..."
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
            options={[['', 'Tất cả dãy'], ...locationAisleOptions.map((value) => [value, locationAreaLabels.get(value) || inventoryLocationAreaLabel(value)] as [string, string])]}
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
            label="Trạng thái"
            value={locationStatusFilter}
            onChange={setLocationStatusFilter}
            options={[['', 'Tất cả trạng thái'], ['ACTIVE', 'Đang dùng'], ['INACTIVE', 'Đã khóa']]}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void applyLocationFilters()}
              className="inline-flex h-10 flex-1 items-center justify-center gap-1 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 px-3 text-xs font-bold text-white shadow-sm hover:from-indigo-600 hover:to-violet-700 transition-all hover:shadow"
            >
              <Filter className="h-3.5 w-3.5" />
              <span>Lọc</span>
            </button>
            {(locationSearchFilter || locationStatusFilter || locationAisleFilter || locationShelfFilter || locationBinFilter) && (
              <button
                type="button"
                onClick={() => void clearLocationFilters()}
                className="inline-flex h-10 flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 hover:bg-slate-50 transition-colors shadow-sm"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Xóa</span>
              </button>
            )}
          </div>
        </div>

        <AdminTable
          hideFooter={true}
          headers={[
            'Mã kệ',
            'Tên kệ',
            'Dãy',
            'Thứ tự',
            'Kích thước',
            'Trộn SKU',
            'SKU',
            'Tồn',
            'Trạng thái',
            'Thao tác'
          ]}
        >
          {(inventoryLocations || []).map((location: any) => {
            const isActive = String(location.status || 'ACTIVE') === 'ACTIVE';
            return (
              <tr key={location.id}>
                <td className="px-4 py-3 font-mono font-bold text-slate-900">
                  <span className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">{location.code}</span>
                </td>
                <td className="px-4 py-3 font-semibold text-slate-800">{location.name}</td>
                <td className="px-4 py-3 text-slate-600">{resolveInventoryLocationZone(String(location.code || ''), String(location.name || ''), String(location.zone || ''))}</td>
                <td className="px-4 py-3 text-slate-600 text-center">{location.sortOrder || 0}</td>
                <td className="px-4 py-3 text-slate-600">
                  {location.lengthCm && location.widthCm && location.heightCm
                    ? `${location.lengthCm} x ${location.widthCm} x ${location.heightCm} cm`
                    : '-'}
                  {location.capacityVolumeCm3 ? (
                    <div className="text-[11px] font-semibold text-slate-400 mt-0.5">
                      {Number(location.capacityVolumeCm3).toLocaleString('vi-VN')} cm³
                    </div>
                  ) : null}
                  {location.fillRatio != null ? (
                    <div className="mt-2 space-y-1 max-w-[150px]">
                      <div className="flex items-center justify-between text-[10px] font-bold">
                        <span className={Number(location.fillRatio) >= 0.9 ? 'text-rose-600' : Number(location.fillRatio) >= 0.7 ? 'text-amber-600' : 'text-emerald-600'}>
                          Đầy {Math.round(Number(location.fillRatio) * 100)}%
                        </span>
                        <span className="text-slate-400">còn {Number(location.availableVolumeCm3 || 0).toLocaleString('vi-VN')} cm³</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            Number(location.fillRatio) >= 0.9
                              ? 'bg-rose-500'
                              : Number(location.fillRatio) >= 0.7
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.round(Number(location.fillRatio) * 100))}%` }}
                        />
                      </div>
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${location.allowMixedSku ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                    {location.allowMixedSku ? 'Cho phép' : 'Không'}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-700 font-semibold text-center">{location.skuCount || 0}</td>
                <td className="px-4 py-3 text-slate-700 font-bold text-center">{location.onHandQuantity || 0}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                    {isActive ? 'Đang dùng' : 'Đã khóa'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5">
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
                      className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-indigo-600 hover:bg-slate-50 hover:border-indigo-200 transition-colors"
                    >
                      <Edit className="h-3 w-3" />
                      <span>Sửa</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void toggleLocationStatus(location)}
                      disabled={Boolean(location.isDefault)}
                      className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                        isActive
                          ? 'border-amber-200 bg-white text-amber-700 hover:bg-amber-50 hover:border-amber-300'
                          : 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300'
                      }`}
                    >
                      {isActive ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                      <span>{isActive ? 'Khóa' : 'Mở'}</span>
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
          {(!inventoryLocations || inventoryLocations.length === 0) && (
            <tr>
              <td colSpan={10} className="px-4 py-6 text-center">
                <div className="space-y-3">
                  <div>
                    <div className="text-sm font-bold text-slate-700">
                      {locationAisleFilter ? `Chưa có kệ trong ${locationAreaLabels.get(locationAisleFilter) || inventoryLocationAreaLabel(locationAisleFilter)}.` : 'Chưa có kệ hàng.'}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      {locationAisleFilter ? `Tạo kệ mã ${locationAisleFilter}-01-01 để dãy này có danh sách.` : 'Tạo kệ đầu tiên để bắt đầu quản lý tồn theo dãy.'}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLocationDraft(createLocationDraftForArea())}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-700"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {locationAisleFilter ? 'Thêm kệ dãy này' : 'Thêm kệ'}
                  </button>
                </div>
              </td>
            </tr>
          )}
        </AdminTable>
      </section>

      <section className={`${inventoryView === 'aging' ? '' : 'hidden'} mb-4 rounded-xl border border-slate-200 bg-white p-4`}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Báo cáo tuổi tồn kho</h3>
            <div className="text-xs font-semibold text-slate-500">Tính theo các lô còn tồn, ngày nhập kho và giá vốn của từng lô.</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              noLabel={true}
              label="Nhóm tuổi"
              value={agingBucketFilter}
              onChange={setAgingBucketFilter}
              options={[
                ['', 'Tất cả nhóm tuổi'],
                ['0_30', '0-30 ngày'],
                ['31_90', '31-90 ngày'],
                ['91_180', '91-180 ngày'],
                ['180_PLUS', 'Trên 180 ngày'],
              ]}
            />
            <button type="button" onClick={() => void loadInventoryAgingReport()} disabled={agingLoading} className="h-9 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50">
              {agingLoading ? 'Đang tải...' : 'Tải báo cáo'}
            </button>
          </div>
        </div>
        <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {(agingReport?.buckets || []).map((bucket: any) => (
            <div key={bucket.bucket} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase text-slate-500">{bucket.label}</div>
              <div className="mt-2 text-2xl font-black text-slate-900">{Number(bucket.quantity || 0).toLocaleString('vi-VN')}</div>
              <div className="mt-1 text-xs font-semibold text-slate-600">
                {bucket.skuCount || 0} dòng · {currency.format(Number(bucket.totalCost || 0))}
              </div>
            </div>
          ))}
        </div>
        <AdminTable headers={['Nhóm tuổi', 'Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Nhập lâu nhất', 'Tuổi cao nhất', 'Số lượng', 'Giá trị vốn']}>
          {agingLoading ? (
            <tr><td colSpan={8} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Đang tải báo cáo tuổi tồn kho...</td></tr>
          ) : (agingReport?.items || []).length === 0 ? (
            <tr><td colSpan={8} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Không có lô tồn kho phù hợp.</td></tr>
          ) : (agingReport?.items || []).map((item: any) => (
            <tr key={`${item.bucket}-${item.productId}-${item.variantId || 'base'}-${item.locationId}`}>
              <td className="px-4 py-3 text-xs font-bold text-slate-700">{item.bucketLabel || item.bucket}</td>
              <td className="px-4 py-3 font-semibold text-slate-900">{item.productName || '-'}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-700">
                {item.variantSku || item.productSku || '-'}
                {item.variantColor ? ` - ${item.variantColor}` : ''}
                {item.variantConfiguration ? ` - ${item.variantConfiguration}` : ''}
              </td>
              <td className="px-4 py-3 text-xs text-slate-600">{item.locationCode || '-'}{item.locationName ? ` - ${item.locationName}` : ''}</td>
              <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.oldestReceivedAt ? new Date(item.oldestReceivedAt).toLocaleDateString('vi-VN') : '-'}</td>
              <td className="px-4 py-3 text-right font-bold text-amber-700">{Number(item.maxAgeDays || 0).toLocaleString('vi-VN')} ngày</td>
              <td className="px-4 py-3 text-right font-bold text-slate-900">{Number(item.quantity || 0).toLocaleString('vi-VN')}</td>
              <td className="px-4 py-3 text-right font-semibold text-slate-700">{currency.format(Number(item.totalCost || 0))}</td>
            </tr>
          ))}
        </AdminTable>
      </section>

      <section className={`${inventoryView === 'reconciliation' ? '' : 'hidden'} mb-4 rounded-xl border border-slate-200 bg-white p-4`}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Đối soát lệch tồn và mã</h3>
            <div className="text-xs font-semibold text-slate-500">Kiểm tra tồn kệ, IMEI/serial chưa gắn kệ, mã nằm sai kệ và mã đã rời kho nhưng vẫn còn vị trí.</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              noLabel={true}
              label="Loại sai lệch"
              value={reconciliationIssueFilter}
              onChange={setReconciliationIssueFilter}
              options={[
                ['', 'Tất cả sai lệch'],
                ['LEVEL_GT_IDENTIFIERS', 'Tồn kệ lớn hơn số mã'],
                ['IDENTIFIER_IN_STOCK_WITHOUT_LOCATION', 'Mã còn tồn nhưng chưa có kệ'],
                ['IDENTIFIER_LOCATION_WITHOUT_LEVEL', 'Mã có kệ nhưng kệ không có tồn'],
                ['TERMINAL_IDENTIFIER_WITH_LOCATION', 'Mã đã rời kho nhưng còn gắn kệ'],
                ['SELLABLE_STOCK_MISMATCH', 'Tồn bán được lệch tổng tồn kệ'],
                ['LOT_QUANTITY_MISMATCH', 'Tồn kệ lệch số lượng lô'],
                ['RESERVED_QUANTITY_MISMATCH', 'Tồn giữ lệch số mã đang giữ'],
                ['IDENTIFIER_PAIR_MISMATCH', 'Cặp IMEI/serial không đồng bộ'],
                ['DOCUMENT_LEDGER_MISMATCH', 'Chứng từ hoàn tất thiếu sổ kho'],
              ]}
            />
            <button type="button" onClick={() => void loadInventoryReconciliationReport()} disabled={reconciliationLoading} className="h-9 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50">
              {reconciliationLoading ? 'Đang tải...' : 'Tải đối soát'}
            </button>
          </div>
        </div>
        <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {(reconciliationReport?.summary || []).map((item: any) => (
            <div key={item.issueType} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase text-slate-500">{item.label || reconciliationIssueLabel(item.issueType)}</div>
              <div className={`mt-2 text-2xl font-black ${Number(item.count || 0) > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
                {Number(item.count || 0).toLocaleString('vi-VN')}
              </div>
            </div>
          ))}
        </div>
        <AdminTable headers={['Loại lệch', 'Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Tồn kệ', 'Số mã', 'Mã định danh', 'Trạng thái', 'Ghi chú', 'Xử lý']}>
          {reconciliationLoading ? (
            <tr><td colSpan={10} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Đang tải báo cáo đối soát...</td></tr>
          ) : (reconciliationReport?.items || []).length === 0 ? (
            <tr><td colSpan={10} className="px-4 py-6 text-center text-sm font-semibold text-emerald-700">Chưa phát hiện lệch tồn và mã theo bộ lọc hiện tại.</td></tr>
          ) : (reconciliationReport?.items || []).map((item: any, index: number) => (
            <tr key={`${item.issueType}-${item.productId}-${item.variantId || 'base'}-${item.locationId || 'none'}-${item.identifierValue || index}`}>
              <td className="px-4 py-3 text-xs font-bold text-rose-700">{reconciliationIssueLabel(item.issueType)}</td>
              <td className="px-4 py-3 font-semibold text-slate-900">{item.productName || '-'}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-700">
                {item.variantSku || item.productSku || '-'}
                {item.variantColor ? ` - ${item.variantColor}` : ''}
                {item.variantConfiguration ? ` - ${item.variantConfiguration}` : ''}
              </td>
              <td className="px-4 py-3 text-xs text-slate-600">{item.locationCode || '-'}{item.locationName ? ` - ${item.locationName}` : ''}</td>
              <td className="px-4 py-3 text-right font-bold text-slate-900">{item.onHandQuantity ?? '-'}</td>
              <td className="px-4 py-3 text-right font-bold text-slate-900">{item.identifierQuantity ?? '-'}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-700">{item.identifierValue || '-'}</td>
              <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.identifierStatus || item.identifierType || '-'}</td>
              <td className="px-4 py-3 text-xs text-slate-600">{item.message || '-'}</td>
              <td className="px-4 py-3">
                {isSuperAdmin && item.issueType === 'SELLABLE_STOCK_MISMATCH' && Number(item.differenceQuantity || 0) > 0 ? (
                  <button type="button" onClick={() => void allocateLegacyInventory(item)} className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100">
                    Phân bổ kệ
                  </button>
                ) : '-'}
              </td>
            </tr>
          ))}
        </AdminTable>
      </section>

      <div className="contents">
      <section className={`${inventoryView === 'ledger' ? '' : 'hidden'} mb-4 rounded-xl border border-slate-200 bg-white p-4`}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-slate-900">Sổ kho / lịch sử biến động tồn</h3>
          <div className="flex flex-wrap items-center gap-2">
            <input type="date" value={ledgerDateFrom || ''} onChange={(event) => setLedgerDateFrom(event.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-sm font-semibold text-slate-700" />
            <input type="date" value={ledgerDateTo || ''} onChange={(event) => setLedgerDateTo(event.target.value)} className="h-9 rounded-lg border border-slate-200 px-2 text-sm font-semibold text-slate-700" />
            <Select noLabel={true} label="Loại giao dịch" value={ledgerTransactionType || ''} onChange={setLedgerTransactionType} options={[['', 'Tất cả giao dịch'], ['RECEIPT', 'Nhập kho'], ['SALE', 'Xuất bán'], ['ADJUSTMENT', 'Điều chỉnh/Kiểm kê'], ['RETURN', 'Hoàn hàng'], ['REVERSAL', 'Đảo phiếu']]} />
            <Select noLabel={true} label="Lý do định đoạt" value={ledgerReason || ''} onChange={setLedgerReason} options={[['', 'Tất cả lý do'], ['RTV_COMPLETED', 'RTV hoàn tất'], ['LIQUIDATED', 'Đã thanh lý'], ['SCRAP', 'Hủy/phế phẩm'], ['OUT_OF_SYSTEM', 'Xuất khỏi hệ thống'], ['COST_ADJUSTMENT', 'Điều chỉnh giá vốn']]} />
            <button type="button" onClick={() => void applyInventoryLedgerFilters()} className="h-9 rounded-lg border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 hover:bg-indigo-100">Lọc sổ</button>
            {(ledgerDateFrom || ledgerDateTo || ledgerTransactionType || ledgerReason) && (
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
              <td className="px-4 py-3 text-xs font-bold text-slate-700">
                <div>{transactionTypeLabel(item.transactionType)}</div>
                {dispositionReasonLabel(item.reason) && (
                  <div className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                    {dispositionReasonLabel(item.reason)}
                  </div>
                )}
              </td>
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
      {inventoryView === 'stock' && pendingLocationRequests.length > 0 && (
        <section className="mb-4 rounded-xl border border-indigo-200 bg-indigo-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-indigo-900">Yêu cầu gán vị trí IMEI/serial chờ duyệt</h3>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-800">{pendingLocationRequests.length} yêu cầu</span>
          </div>
          <AdminTable headers={['Sản phẩm', 'Loại', 'Mã định danh', 'Kệ hiện tại', 'Kệ đề xuất', 'Lý do', 'Thao tác']}>
            {pendingLocationRequests.map((item: any) => (
              <tr key={item.id}>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{renderRequestProductName(item)}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{item.identifierType}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-800">
                  <div className="font-bold">{item.identifierValue}</div>
                  {item.identifierPairId && (
                    <div className="mt-1 space-y-0.5 text-[11px] text-slate-500">
                      <div>IMEI1: {item.imei1}</div>
                      {item.imei2 && <div>IMEI2: {item.imei2}</div>}
                      <div>Serial: {item.pairedSerialNumber}</div>
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{item.currentLocationCode || 'Chưa gắn kệ'}</td>
                <td className="px-4 py-3 font-mono text-xs font-bold text-indigo-700">{item.newLocationCode}</td>
                <td className="px-4 py-3 text-xs text-slate-600">{item.reason}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => void decideIdentifierLocation(item.id, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                      <Check className="h-3.5 w-3.5" /> Duyệt
                    </button>
                    <button type="button" onClick={() => void decideIdentifierLocation(item.id, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                      <X className="h-3.5 w-3.5" /> Hủy
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && stockCounts.length > 0 && (
        <section className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-emerald-900">Phiếu kiểm kê kho</h3>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">{stockCounts.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Kệ', 'Trạng thái', 'Số dòng', 'Lệch tuyệt đối', 'Lệch ròng', 'Thao tác']}>
            {stockCounts.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">{item.locationCode || '-'}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
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
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
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
      {inventoryView === 'stock' && transfers.length > 0 && (
        <section className="mb-4 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-amber-900">Phiếu chuyển kệ</h3>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">{transfers.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Trạng thái', 'Số dòng', 'Số lượng', 'Thao tác']}>
            {transfers.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3">{item.totalQuantity || 0}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setTransferDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                    {item.status === 'DRAFT' && canApproveInventory ? (
                      <>
                        <button type="button" onClick={() => void decideTransfer(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                          <Check className="h-3.5 w-3.5" /> Duyệt
                        </button>
                        <button type="button" onClick={() => void decideTransfer(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          <X className="h-3.5 w-3.5" /> Hủy
                        </button>
                      </>
                    ) : null}
                    {item.status === 'APPROVED' && canApproveInventory ? (
                      <>
                        <button type="button" onClick={() => void decideTransfer(item.referenceCode, 'COMPLETED')} className="inline-flex items-center gap-1 rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50">
                          <Check className="h-3.5 w-3.5" /> Hoàn tất
                        </button>
                        <button type="button" onClick={() => void decideTransfer(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          <X className="h-3.5 w-3.5" /> Hủy
                        </button>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && internalHolds.length > 0 && (
        <section className="mb-4 rounded-xl border border-sky-200 bg-sky-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-sky-900">Phiếu giữ nội bộ</h3>
            <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-800">{internalHolds.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Loại giữ', 'Trạng thái', 'Số dòng', 'Số lượng', 'Thao tác']}>
            {internalHolds.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-700">{internalHoldTypeLabel(item.holdType)}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3">{item.totalQuantity || 0}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setInternalHoldDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                    {item.status === 'DRAFT' && canApproveInventory ? (
                      <>
                        <button type="button" onClick={() => void decideInternalHold(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                          <Check className="h-3.5 w-3.5" /> Duyệt giữ
                        </button>
                        <button type="button" onClick={() => void decideInternalHold(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          <X className="h-3.5 w-3.5" /> Hủy
                        </button>
                      </>
                    ) : null}
                    {item.status === 'APPROVED' && canApproveInventory ? (
                      <button type="button" onClick={() => void decideInternalHold(item.referenceCode, 'COMPLETED')} className="inline-flex items-center gap-1 rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50">
                        <Unlock className="h-3.5 w-3.5" /> Mở khóa
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && disposals.length > 0 && (
        <section className="mb-4 rounded-xl border border-rose-200 bg-rose-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-rose-900">Phiếu xử lý tồn</h3>
            <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-800">{disposals.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Loại xử lý', 'Trạng thái', 'Số dòng', 'Số lượng', 'Thao tác']}>
            {disposals.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-700">{disposalTypeLabel(item.dispositionType)}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3">{item.totalQuantity || 0}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setDisposalDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                    {item.status === 'DRAFT' && canApproveInventory ? (
                      <>
                        <button type="button" onClick={() => void decideDisposal(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                          <Check className="h-3.5 w-3.5" /> Duyệt
                        </button>
                        <button type="button" onClick={() => void decideDisposal(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          <X className="h-3.5 w-3.5" /> Hủy
                        </button>
                      </>
                    ) : null}
                    {item.status === 'APPROVED' && canApproveInventory ? (
                      <button type="button" onClick={() => void decideDisposal(item.referenceCode, 'COMPLETED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-300 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100">
                        <Check className="h-3.5 w-3.5" /> Hoàn tất
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </AdminTable>
        </section>
      )}
      {inventoryView === 'stock' && costAdjustments.length > 0 && (
        <section className="mb-4 rounded-xl border border-violet-200 bg-violet-50/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-violet-900">Phiếu điều chỉnh giá vốn</h3>
            <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-bold text-violet-800">{costAdjustments.length} phiếu</span>
          </div>
          <AdminTable headers={['Mã phiếu', 'Trạng thái', 'Số dòng', 'Lý do', 'Thao tác']}>
            {costAdjustments.map((item: any) => (
              <tr key={item.id || item.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{item.referenceCode}</td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-600">{documentStatusLabels[item.status] || item.status}</td>
                <td className="px-4 py-3">{item.lineCount || 0}</td>
                <td className="px-4 py-3 text-xs text-slate-600">{item.reason || '-'}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setCostAdjustmentDetail(item)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                      <Eye className="h-3.5 w-3.5" /> Xem
                    </button>
                    {item.status === 'DRAFT' && canApproveInventory ? (
                      <>
                        <button type="button" onClick={() => void decideCostAdjustment(item.referenceCode, 'APPROVED')} className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                          <Check className="h-3.5 w-3.5" /> Duyệt
                        </button>
                        <button type="button" onClick={() => void decideCostAdjustment(item.referenceCode, 'CANCELLED')} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          <X className="h-3.5 w-3.5" /> Hủy
                        </button>
                      </>
                    ) : null}
                    {item.status === 'APPROVED' && canApproveInventory ? (
                      <button type="button" onClick={() => void decideCostAdjustment(item.referenceCode, 'COMPLETED')} className="inline-flex items-center gap-1 rounded-lg border border-violet-300 px-3 py-1.5 text-xs font-semibold text-violet-700 hover:bg-violet-100">
                        <Check className="h-3.5 w-3.5" /> Hoàn tất
                      </button>
                    ) : null}
                  </div>
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
        'Kệ',
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
                <td className="w-40 px-4 py-3">{renderInventoryLocationCell(item)}</td>
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
      {locationDetailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Danh sách kệ</h3>
                <p className="text-sm font-semibold text-slate-600">
                  {locationDetailModal.row.productName || locationDetailModal.row.name || 'Sản phẩm'}
                </p>
                <p className="text-xs text-slate-500">
                  {locationDetailModal.row.variantSku || locationDetailModal.row.productSku || compactId(locationDetailModal.row.variantId || locationDetailModal.row.productId || locationDetailModal.row.id)}
                </p>
              </div>
              <button type="button" onClick={() => setLocationDetailModal(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng danh sách kệ">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-auto p-5">
              <div className="overflow-hidden rounded-xl border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-4 py-3">Mã kệ</th>
                      <th className="px-4 py-3">Tên kệ</th>
                      <th className="px-4 py-3">Dãy</th>
                      <th className="px-4 py-3 text-right">Số lượng</th>
                      <th className="px-4 py-3">Mã định danh trên kệ</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {locationDetailModal.locations.map((location) => {
                      const stats = locationIdentifierStats(location, locationDetailModal.row);
                      return (
                        <tr key={location.id}>
                          <td className="px-4 py-3 font-mono text-xs font-bold text-slate-800">{location.code || '-'}</td>
                          <td className="px-4 py-3 text-slate-700">{location.name || 'Kệ không rõ'}</td>
                          <td className="px-4 py-3 text-slate-600">{location.zone || '-'}</td>
                          <td className="px-4 py-3 text-right font-bold text-emerald-700">{location.onHandQuantity}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col items-start gap-1.5">
                              <button
                                type="button"
                                onClick={() => setLocationIdentifierModal({ row: locationDetailModal.row, location })}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                <span>Xem danh sách</span>
                                <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] font-black text-indigo-700">{stats.totalIdentifiers}</span>
                              </button>
                              {stats.tracksIdentifiers && stats.missingQuantity > 0 ? (
                                <span className="text-[11px] font-semibold text-amber-700">Thiếu {stats.missingQuantity} mã</span>
                              ) : null}
                              {canAdjustInventory && Number(location.onHandQuantity || 0) > 0 ? (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => openTransferDraft(locationDetailModal.row, location)}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-bold text-amber-700 hover:bg-amber-100"
                                  >
                                    <ClipboardList className="h-3.5 w-3.5" />
                                    <span>Tách/chuyển</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => openTransferDraft(locationDetailModal.row, location, 'CHUYEN_TRANG_THAI')}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-100"
                                  >
                                    <ArrowRightLeft className="h-3.5 w-3.5" />
                                    <span>Chuyển trạng thái</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => openDisposalDraft(locationDetailModal.row, location)}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-bold text-red-700 hover:bg-red-100"
                                  >
                                    <X className="h-3.5 w-3.5" />
                                    <span>Xử lý tồn</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => openCostAdjustmentDraft(locationDetailModal.row, location)}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-2.5 py-1.5 text-xs font-bold text-violet-700 hover:bg-violet-100"
                                  >
                                    <Edit className="h-3.5 w-3.5" />
                                    <span>Giá vốn</span>
                                  </button>
                                </>
                              ) : null}
                              {canReserveInventory && Number(location.onHandQuantity || 0) > 0 ? (
                                <button
                                  type="button"
                                  onClick={() => openInternalHoldDraft(locationDetailModal.row, location)}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-2.5 py-1.5 text-xs font-bold text-sky-700 hover:bg-sky-100"
                                >
                                  <Lock className="h-3.5 w-3.5" />
                                  <span>Giữ nội bộ</span>
                                </button>
                              ) : null}
                              {canAdjustInventory && inventoryLocationEntries(locationDetailModal.row).some((source) => String(source.id) !== String(location.id) && Number(source.onHandQuantity || 0) > 0) ? (
                                <button
                                  type="button"
                                  onClick={() => void createConsolidationTransfer(locationDetailModal.row, location)}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100"
                                >
                                  <ClipboardList className="h-3.5 w-3.5" />
                                  <span>Gom về đây</span>
                                </button>
                              ) : null}
                              {canCountInventory && Number(location.onHandQuantity || 0) > 0 ? (
                                <button
                                  type="button"
                                  onClick={() => void openShelfStockCountDraft(location)}
                                  disabled={stockCountLoading}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                                >
                                  <ClipboardList className="h-3.5 w-3.5" />
                                  <span>Kiểm kê kệ</span>
                                </button>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
      {locationIdentifierModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Danh sách mã trên kệ</h3>
                <p className="text-sm font-semibold text-slate-600">
                  {locationIdentifierModal.row.productName || locationIdentifierModal.row.name || 'Sản phẩm'}
                </p>
                <p className="text-xs text-slate-500">
                  {locationIdentifierModal.location.code || '-'} - {locationIdentifierModal.location.name || 'Kệ không rõ'} · Tồn {locationIdentifierModal.location.onHandQuantity}
                </p>
              </div>
              <button type="button" onClick={() => setLocationIdentifierModal(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng danh sách mã">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[70vh] space-y-4 overflow-auto p-5">
              <div className="flex flex-wrap gap-2">
                {locationIdentifierModal.row.tracksImei && (
                  <button type="button" onClick={() => openIdentifierLocationDraft('IMEI')} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-100">
                    Gán IMEI chưa có kệ vào đây
                  </button>
                )}
                {locationIdentifierModal.row.tracksSerialNumber && (
                  <button type="button" onClick={() => openIdentifierLocationDraft('SERIAL')} className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-100">
                    Gán serial chưa có kệ vào đây
                  </button>
                )}
              </div>
              {(() => {
                const stats = locationIdentifierStats(locationIdentifierModal.location, locationIdentifierModal.row);
                if (stats.tracksIdentifiers && stats.missingQuantity > 0) {
                  return (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                      Còn {stats.missingQuantity} sản phẩm trên kệ chưa khớp IMEI/serial.
                    </div>
                  );
                }
                if (!stats.tracksIdentifiers) {
                  return (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-500">
                      Sản phẩm này không bật quản lý mã định danh.
                    </div>
                  );
                }
                return null;
              })()}
              {locationIdentifierModal.row.tracksImei && locationIdentifierModal.row.tracksSerialNumber && locationIdentifierModal.location.identifierUnits.length > 0 ? (
                <IdentifierUnitTable units={locationIdentifierModal.location.identifierUnits} />
              ) : (
                <>
                  {renderLocationIdentifierTable('IMEI', locationIdentifierModal.location.imeis, requestLocationIdentifierEdit, openIdentifierLocationDraft)}
                  {renderLocationIdentifierTable('Serial', locationIdentifierModal.location.serialNumbers, requestLocationIdentifierEdit, openIdentifierLocationDraft)}
                </>
              )}
            </div>
          </div>
        </div>
      )}
      {identifierLocationDraft && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={(event) => void submitIdentifierLocationRequest(event)} className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Yêu cầu gán vị trí mã định danh</h3>
                <p className="text-sm text-slate-600">{identifierLocationDraft.productName}</p>
              </div>
              <button type="button" onClick={() => setIdentifierLocationDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng yêu cầu gán vị trí">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-xs font-semibold text-slate-600">
                  Loại mã
                  <select value={identifierLocationDraft.identifierType} disabled={Boolean(identifierLocationDraft.identifierId)} onChange={(event) => setIdentifierLocationDraft((current) => current ? { ...current, identifierType: event.target.value as 'IMEI' | 'SERIAL' } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 disabled:bg-slate-50">
                    <option value="IMEI">IMEI</option>
                    <option value="SERIAL">Serial</option>
                  </select>
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Mã định danh
                  <input value={identifierLocationDraft.identifierValue} readOnly={Boolean(identifierLocationDraft.identifierId)} onChange={(event) => setIdentifierLocationDraft((current) => current ? { ...current, identifierValue: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 font-mono text-sm text-slate-800 read-only:bg-slate-50" />
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-xs font-semibold text-slate-600">
                  Kệ hiện tại
                  <input value={identifierLocationDraft.currentLocationCode} readOnly className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-700" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Kệ đích
                  <select value={identifierLocationDraft.newLocationId} onChange={(event) => setIdentifierLocationDraft((current) => current ? { ...current, newLocationId: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800">
                    <option value="">Chọn kệ đích</option>
                    {(inventoryLocationOptionSource || [])
                      .filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE' && String(location.code || '') !== identifierLocationDraft.currentLocationCode)
                      .map((location: any) => (
                        <option key={location.id} value={String(location.id)}>{location.code} - {location.name}</option>
                      ))}
                  </select>
                </label>
              </div>
              <label className="block text-xs font-semibold text-slate-600">
                Lý do
                <textarea value={identifierLocationDraft.reason} onChange={(event) => setIdentifierLocationDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 min-h-24 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" placeholder="Ví dụ: mã chưa được gắn kệ sau khi nhập kho" />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setIdentifierLocationDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700">Gửi duyệt</button>
            </div>
          </form>
        </div>
      )}
      {costAdjustmentDraft && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={(event) => void submitCostAdjustmentDraft(event)} className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu điều chỉnh giá vốn</h3>
                <p className="text-sm text-slate-600">Phiếu không đổi số lượng; khi hoàn tất mới cập nhật giá vốn kệ và lô còn tồn.</p>
              </div>
              <button type="button" onClick={() => setCostAdjustmentDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={costAdjustmentDraft.referenceCode} onChange={(event) => setCostAdjustmentDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Giá vốn mới
                  <input type="number" min={0} value={costAdjustmentDraft.line.newAverageUnitCost} onChange={(event) => setCostAdjustmentDraft((current) => current ? { ...current, line: { ...current.line, newAverageUnitCost: Number(event.target.value || 0) } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-bold text-slate-900">{costAdjustmentDraft.line.productName}</div>
                <div className="font-mono text-xs text-slate-500">{costAdjustmentDraft.line.sku}</div>
                <div className="mt-2 text-sm text-slate-600">Kệ: <span className="font-semibold text-slate-800">{costAdjustmentDraft.line.locationCode}</span> - {costAdjustmentDraft.line.locationName}</div>
                <div className="mt-1 text-sm text-slate-600">Giá vốn hiện tại: <span className="font-semibold text-slate-800">{currency.format(Number(costAdjustmentDraft.line.currentAverageUnitCost || 0))}</span></div>
              </div>
              <label className="block text-xs font-semibold text-slate-600">
                Lý do
                <textarea value={costAdjustmentDraft.reason} onChange={(event) => setCostAdjustmentDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 min-h-20 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" />
              </label>
              <label className="block text-xs font-semibold text-slate-600">
                Ghi chú dòng
                <textarea value={costAdjustmentDraft.line.note} onChange={(event) => setCostAdjustmentDraft((current) => current ? { ...current, line: { ...current.line, note: event.target.value } } : current)} className="mt-1 min-h-16 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setCostAdjustmentDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-bold text-white hover:bg-violet-700">Tạo phiếu giá vốn</button>
            </div>
          </form>
        </div>
      )}
      {disposalDraft && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={(event) => void submitDisposalDraft(event)} className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu xử lý tồn</h3>
                <p className="text-sm text-slate-600">Phiếu được duyệt trước; khi hoàn tất mới giảm tồn, lô và chuyển trạng thái mã định danh.</p>
              </div>
              <button type="button" onClick={() => setDisposalDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-3">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={disposalDraft.referenceCode} onChange={(event) => setDisposalDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Loại xử lý
                  <select value={disposalDraft.dispositionType} onChange={(event) => setDisposalDraft((current) => current ? { ...current, dispositionType: event.target.value as DisposalDraft['dispositionType'] } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800">
                    <option value="SCRAP">Hủy/phế phẩm</option>
                    <option value="LIQUIDATED">Thanh lý</option>
                    <option value="OUT_OF_SYSTEM">Xuất khỏi hệ thống</option>
                  </select>
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Số lượng
                  <input type="number" min={1} max={Math.max(1, disposalDraft.line.maxQuantity)} readOnly={disposalDraft.line.availableIdentifierUnits.length > 0} value={disposalDraft.line.quantity} onChange={(event) => setDisposalDraft((current) => current ? { ...current, line: { ...current.line, quantity: Math.max(1, Number(event.target.value || 1)) } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 read-only:bg-slate-50" />
                </label>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-bold text-slate-900">{disposalDraft.line.productName}</div>
                <div className="font-mono text-xs text-slate-500">{disposalDraft.line.sku}</div>
                <div className="mt-2 text-sm text-slate-600">Kệ: <span className="font-semibold text-slate-800">{disposalDraft.line.locationCode}</span> - {disposalDraft.line.locationName}</div>
              </div>
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold text-slate-900">Chọn mã xử lý</div>
                    <div className="text-xs font-semibold text-slate-500">Tick mã ở bảng hiện tại để đưa sang bảng xử lý; bỏ tick ở bảng xử lý để trả lại.</div>
                  </div>
                  <div className="text-xs font-bold text-red-700">
                    {disposalDraft.line.availableIdentifierUnits.length > 0 ? `Đã chọn ${disposalDraft.line.identifierPairIds.length} thiết bị` : `Đã chọn ${splitIdentifierText(disposalDraft.line.imeis).length} IMEI · ${splitIdentifierText(disposalDraft.line.serialNumbers).length} serial`}
                  </div>
                </div>
                {disposalDraft.line.availableIdentifierUnits.length > 0 ? (
                  <IdentifierUnitTable units={disposalDraft.line.availableIdentifierUnits} selectedIds={disposalDraft.line.identifierPairIds} onToggle={updateDisposalIdentifierUnit} />
                ) : <><TransferIdentifierPicker
                  label="IMEI"
                  availableTitle="IMEI hiện tại"
                  selectedTitle="IMEI xử lý"
                  emptySelectedText="Chưa chọn IMEI xử lý."
                  identifiers={disposalDraft.line.availableImeis}
                  selectedValues={splitIdentifierText(disposalDraft.line.imeis)}
                  onToggle={(value, selected) => updateDisposalIdentifiers('IMEI', value, selected)}
                  manualValue={disposalDraft.line.imeis}
                  onManualChange={(value) => updateDisposalIdentifierText('IMEI', value)}
                  manualPlaceholder="Quét hoặc nhập IMEI cần xử lý, mỗi dòng một mã"
                />
                <TransferIdentifierPicker
                  label="Serial"
                  availableTitle="Serial hiện tại"
                  selectedTitle="Serial xử lý"
                  emptySelectedText="Chưa chọn serial xử lý."
                  identifiers={disposalDraft.line.availableSerialNumbers}
                  selectedValues={splitIdentifierText(disposalDraft.line.serialNumbers)}
                  onToggle={(value, selected) => updateDisposalIdentifiers('SERIAL', value, selected)}
                  manualValue={disposalDraft.line.serialNumbers}
                  onManualChange={(value) => updateDisposalIdentifierText('SERIAL', value)}
                  manualPlaceholder="Quét hoặc nhập serial cần xử lý, mỗi dòng một mã"
                /></>}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-xs font-semibold text-slate-600">
                  Đối tác
                  <input value={disposalDraft.partnerName} onChange={(event) => setDisposalDraft((current) => current ? { ...current, partnerName: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Giá trị thu hồi
                  <input type="number" min={0} value={disposalDraft.recoveryValue} onChange={(event) => setDisposalDraft((current) => current ? { ...current, recoveryValue: event.target.value === '' ? '' : Number(event.target.value || 0) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <label className="block text-xs font-semibold text-slate-600">
                Lý do
                <textarea value={disposalDraft.reason} onChange={(event) => setDisposalDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 min-h-20 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setDisposalDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-bold text-white hover:bg-rose-700">Tạo phiếu xử lý</button>
            </div>
          </form>
        </div>
      )}
      {internalHoldDraft && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={(event) => void submitInternalHoldDraft(event)} className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu giữ nội bộ</h3>
                <p className="text-sm text-slate-600">Phiếu nháp chưa khóa tồn; khi duyệt mới giảm tồn khả dụng trên kệ.</p>
              </div>
              <button type="button" onClick={() => setInternalHoldDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-3">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={internalHoldDraft.referenceCode} onChange={(event) => setInternalHoldDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Loại giữ
                  <select value={internalHoldDraft.holdType} onChange={(event) => setInternalHoldDraft((current) => current ? { ...current, holdType: event.target.value as InternalHoldDraft['holdType'] } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800">
                    <option value="INTERNAL_HOLD">Giữ nội bộ</option>
                    <option value="QC_HOLD">Giữ kiểm tra</option>
                    <option value="CLAIM_HOLD">Giữ khiếu nại</option>
                  </select>
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Số lượng
                  <input type="number" min={1} max={Math.max(1, internalHoldDraft.line.maxQuantity)} value={internalHoldDraft.line.quantity} onChange={(event) => setInternalHoldDraft((current) => current ? { ...current, line: { ...current.line, quantity: Math.max(1, Number(event.target.value || 1)) } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-bold text-slate-900">{internalHoldDraft.line.productName}</div>
                <div className="font-mono text-xs text-slate-500">{internalHoldDraft.line.sku}</div>
                <div className="mt-2 text-sm text-slate-600">Kệ: <span className="font-semibold text-slate-800">{internalHoldDraft.line.locationCode}</span> - {internalHoldDraft.line.locationName}</div>
              </div>
              <label className="block text-xs font-semibold text-slate-600">
                Lý do
                <textarea value={internalHoldDraft.reason} onChange={(event) => setInternalHoldDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 min-h-24 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800" />
              </label>
              <label className="block text-xs font-semibold text-slate-600">
                Ghi chú
                <input value={internalHoldDraft.note} onChange={(event) => setInternalHoldDraft((current) => current ? { ...current, note: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
              </label>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setInternalHoldDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-bold text-white hover:bg-sky-700">Tạo phiếu giữ</button>
            </div>
          </form>
        </div>
      )}
      {transferDraft && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/50 p-4">
          <form onSubmit={(event) => void submitTransferDraft(event)} className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu chuyển kệ</h3>
                <p className="text-sm text-slate-600">Phiếu được duyệt trước, chỉ cập nhật tồn, lô và IMEI/serial khi hoàn tất.</p>
              </div>
              <button type="button" onClick={() => setTransferDraft(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="grid gap-3 md:grid-cols-[180px_180px_1fr]">
                <label className="text-xs font-semibold text-slate-600">
                  Mã phiếu
                  <input value={transferDraft.referenceCode} onChange={(event) => setTransferDraft((current) => current ? { ...current, referenceCode: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Loại nghiệp vụ
                  <input value={transferDraft.reason} onChange={(event) => setTransferDraft((current) => current ? { ...current, reason: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
                <label className="text-xs font-semibold text-slate-600">
                  Ghi chú chung
                  <input value={transferDraft.note} onChange={(event) => setTransferDraft((current) => current ? { ...current, note: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="mb-4">
                  <div className="text-sm font-bold text-slate-900">{transferDraft.line.productName}</div>
                  <div className="font-mono text-xs text-slate-500">{transferDraft.line.sku}</div>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <label className="text-xs font-semibold text-slate-600">
                    Kệ nguồn
                    <select value={transferDraft.line.fromLocationId} disabled className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-700">
                      {inventoryLocationOptionSource.map((location: any) => (
                        <option key={location.id} value={String(location.id)}>{location.code} - {location.name} [{locationPurposeLabel(String(location.purpose || 'STORAGE'))}]</option>
                      ))}
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-slate-600">
                    Kệ đích
                    <select value={transferDraft.line.toLocationId} onChange={(event) => setTransferDraft((current) => current ? { ...current, line: { ...current.line, toLocationId: event.target.value } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800">
                      <option value="">Chọn kệ đích</option>
                      {inventoryLocationOptionSource
                        .filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE')
                        .filter((location: any) => String(location.id) !== transferDraft.line.fromLocationId)
                        .map((location: any) => (
                          <option key={location.id} value={String(location.id)}>{location.code} - {location.name} [{locationPurposeLabel(String(location.purpose || 'STORAGE'))}]</option>
                        ))}
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-slate-600">
                    Số lượng
                    <input type="number" min={1} max={Math.max(1, transferDraft.line.maxQuantity)} readOnly={transferDraft.line.availableIdentifierUnits.length > 0} value={transferDraft.line.quantity} onChange={(event) => setTransferDraft((current) => current ? { ...current, line: { ...current.line, quantity: Math.max(1, Number(event.target.value || 1)) } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 read-only:bg-slate-50" />
                  </label>
                </div>
                <div className="mt-3 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-slate-900">Chọn mã cần chuyển</div>
                      <div className="text-xs font-semibold text-slate-500">Danh sách chỉ mở khi cần chọn thiết bị, tránh làm nặng giao diện.</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-xs font-bold text-amber-700">{transferDraft.line.availableIdentifierUnits.length > 0 ? `Đã chọn ${transferDraft.line.identifierPairIds.length} thiết bị` : `Đã chọn ${splitIdentifierText(transferDraft.line.imeis).length} IMEI · ${splitIdentifierText(transferDraft.line.serialNumbers).length} serial`}</div>
                      <button type="button" onClick={() => setTransferIdentifiersOpen((current) => !current)} className="rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-50">{transferIdentifiersOpen ? 'Thu gọn' : 'Mở danh sách thiết bị'}</button>
                    </div>
                  </div>
                  {transferIdentifiersOpen && (transferDraft.line.availableIdentifierUnits.length > 0 ? (
                    <IdentifierUnitTable units={transferDraft.line.availableIdentifierUnits} selectedIds={transferDraft.line.identifierPairIds} onToggle={updateTransferIdentifierUnit} />
                  ) : <><TransferIdentifierPicker
                    label="IMEI"
                    identifiers={transferDraft.line.availableImeis}
                    selectedValues={splitIdentifierText(transferDraft.line.imeis)}
                    onToggle={(value, selected) => updateTransferIdentifiers('IMEI', value, selected)}
                    manualValue={transferDraft.line.imeis}
                    onManualChange={(value) => updateTransferIdentifierText('IMEI', value)}
                    manualPlaceholder="Quét hoặc nhập IMEI cần chuyển, mỗi dòng một mã"
                  />
                  <TransferIdentifierPicker
                    label="Serial"
                    identifiers={transferDraft.line.availableSerialNumbers}
                    selectedValues={splitIdentifierText(transferDraft.line.serialNumbers)}
                    onToggle={(value, selected) => updateTransferIdentifiers('SERIAL', value, selected)}
                    manualValue={transferDraft.line.serialNumbers}
                    onManualChange={(value) => updateTransferIdentifierText('SERIAL', value)}
                    manualPlaceholder="Quét hoặc nhập serial cần chuyển, mỗi dòng một mã"
                  /></>)}
                </div>
                <label className="mt-3 block text-xs font-semibold text-slate-600">
                  Ghi chú dòng
                  <input value={transferDraft.line.note} onChange={(event) => setTransferDraft((current) => current ? { ...current, line: { ...current.line, note: event.target.value } } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" />
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <button type="button" onClick={() => setTransferDraft(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">Đóng</button>
              <button type="submit" className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-bold text-white hover:bg-amber-700">Tạo phiếu chuyển</button>
            </div>
          </form>
        </div>
      )}
      {costAdjustmentDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu giá vốn {costAdjustmentDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {documentStatusLabels[costAdjustmentDetail.status] || costAdjustmentDetail.status}</p>
              </div>
              <button type="button" onClick={() => setCostAdjustmentDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Tồn kệ', 'Giá cũ', 'Giá mới', 'Lô áp dụng', 'Ghi chú']}>
                {(costAdjustmentDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{line.locationCode || '-'} - {line.locationName || ''}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{line.onHandQuantity || 0}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-700">{currency.format(Number(line.oldAverageUnitCost || 0))}</td>
                    <td className="px-4 py-3 text-right font-bold text-violet-700">{currency.format(Number(line.newAverageUnitCost || 0))}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">{(line.appliedLots || line.lotCosts || []).length}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {disposalDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu xử lý tồn {disposalDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {documentStatusLabels[disposalDetail.status] || disposalDetail.status} - Loại: {disposalTypeLabel(disposalDetail.dispositionType)}</p>
              </div>
              <button type="button" onClick={() => setDisposalDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Loại xử lý', 'Số lượng', 'IMEI / Serial', 'Ghi chú']}>
                {(disposalDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{line.locationCode || '-'} - {line.locationName || ''}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-slate-700">{disposalTypeLabel(line.dispositionType || disposalDetail.dispositionType)}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{line.quantity || 0}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <div>IMEI: {(line.imeis || []).length}</div>
                      <div>Serial: {(line.serialNumbers || []).length}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {internalHoldDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu giữ nội bộ {internalHoldDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {documentStatusLabels[internalHoldDetail.status] || internalHoldDetail.status} - Loại: {internalHoldTypeLabel(internalHoldDetail.holdType)}</p>
              </div>
              <button type="button" onClick={() => setInternalHoldDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Loại giữ', 'Số lượng', 'Ghi chú']}>
                {(internalHoldDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{line.locationCode || '-'} - {line.locationName || ''}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-slate-700">{internalHoldTypeLabel(line.holdType || internalHoldDetail.holdType)}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{line.quantity || 0}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
      {transferDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Chi tiết phiếu chuyển kệ {transferDetail.referenceCode}</h3>
                <p className="text-sm text-slate-600">Trạng thái: {documentStatusLabels[transferDetail.status] || transferDetail.status} - Số lượng: {transferDetail.totalQuantity || 0}</p>
              </div>
              <button type="button" onClick={() => setTransferDetail(null)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[75vh] overflow-y-auto p-5">
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Kệ nguồn', 'Kệ đích', 'Số lượng', 'IMEI / Serial', 'Ghi chú']}>
                {(transferDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{line.fromLocationCode || '-'} - {line.fromLocationName || ''}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{line.toLocationCode || '-'} - {line.toLocationName || ''}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{line.quantity || 0}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <div>IMEI: {(line.imeis || []).length}</div>
                      <div>Serial: {(line.serialNumbers || []).length}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
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
                <input value={locationDraft.code} onChange={(event) => setLocationDraft((current) => current ? { ...current, code: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="A-01-01 hoặc BH-01-01" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Tên kệ
                <input value={locationDraft.name} onChange={(event) => setLocationDraft((current) => current ? { ...current, name: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="Dãy A - Kệ 01 - Ô 01" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Tên dãy
                <input value={locationDraft.zone} onChange={(event) => setLocationDraft((current) => current ? { ...current, zone: event.target.value } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="Dãy A, Dãy bảo hành, Dãy cách ly" />
              </label>
              <label className="text-xs font-semibold text-slate-600">
                Thứ tự lấy hàng
                <input type="number" min={0} value={locationDraft.sortOrder} onChange={(event) => setLocationDraft((current) => current ? { ...current, sortOrder: Number(event.target.value || 0) } : current)} className="mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800" placeholder="10101" />
              </label>
              {resolveInventoryLocationArea(locationDraft.code) !== 'MAIN' && (
                <>
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
                </>
              )}
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
                <h3 className="text-lg font-bold text-slate-900">Tạo phiếu kiểm kê kệ {stockCountDraft.locationCode}</h3>
                <p className="text-sm text-slate-600">Hàng quản lý mã được tính theo danh sách IMEI/serial quét. Phiếu chỉ ghi tồn sau khi được duyệt.</p>
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
              <AdminTable headers={['Sản phẩm', 'SKU', 'Tồn trên kệ', 'Thực đếm', 'Mã đã quét', 'Chênh lệch', 'Ghi chú']}>
                {stockCountDraft.lines.map((line) => {
                  const scannedImeis = splitIdentifierText(line.imeis);
                  const scannedSerialNumbers = splitIdentifierText(line.serialNumbers);
                  const countedQuantity = line.availableIdentifierUnits.length > 0
                    ? line.identifierPairIds.length
                    : line.tracksImei
                    ? scannedImeis.length
                    : line.tracksSerialNumber
                      ? scannedSerialNumbers.length
                      : Number(line.countedQuantity || 0);
                  const variance = countedQuantity - Number(line.expectedQuantity || 0);
                  const imeiMode = getStockCountIdentifierMode(line, 'IMEI');
                  const serialMode = getStockCountIdentifierMode(line, 'SERIAL');
                  return (
                    <tr key={line.key}>
                      <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.sku}</td>
                      <td className="px-4 py-3">{line.expectedQuantity}</td>
                      <td className="px-4 py-3">
                        {line.tracksImei || line.tracksSerialNumber ? (
                          <span className="font-bold text-slate-800">{countedQuantity}</span>
                        ) : (
                          <input type="number" min={0} value={line.countedQuantity} onChange={(event) => updateStockCountLine(line.key, { countedQuantity: Number(event.target.value || 0) })} className="h-9 w-24 rounded-lg border border-slate-200 px-3 text-sm" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="min-w-56 space-y-2">
                          {line.availableIdentifierUnits.length > 0 && <IdentifierUnitTable units={line.availableIdentifierUnits} selectedIds={line.identifierPairIds} onToggle={(unit, selected) => updateStockCountIdentifierUnit(line.key, unit, selected)} />}
                          {line.availableIdentifierUnits.length === 0 && line.tracksImei && (
                            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
                              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                <div className="text-xs font-bold text-slate-700">IMEI ({scannedImeis.length}/{line.expectedQuantity})</div>
                                <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
                                  <button
                                    type="button"
                                    onClick={() => setStockCountIdentifierMode(line.key, 'IMEI', 'select')}
                                    className={`rounded-md px-2.5 py-1 text-xs font-bold ${imeiMode === 'select' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
                                  >
                                    Chọn mã
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setStockCountIdentifierMode(line.key, 'IMEI', 'manual')}
                                    className={`rounded-md px-2.5 py-1 text-xs font-bold ${imeiMode === 'manual' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
                                  >
                                    Nhập tay
                                  </button>
                                </div>
                              </div>
                              {imeiMode === 'select' ? (
                                <TransferIdentifierPicker
                                  label="IMEI"
                                  availableTitle="IMEI trên kệ"
                                  selectedTitle="IMEI đã kiểm kê"
                                  emptyAvailableText="Không có IMEI hệ thống trên kệ này."
                                  emptySelectedText="Chưa chọn IMEI kiểm kê."
                                  identifiers={line.availableImeis}
                                  selectedValues={scannedImeis}
                                  onToggle={(value, selected) => updateStockCountIdentifiers(line.key, 'IMEI', value, selected)}
                                />
                              ) : (
                                <textarea
                                  value={line.imeis}
                                  onChange={(event) => updateStockCountLine(line.key, { imeis: event.target.value })}
                                  className="min-h-20 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                                  placeholder="Quét hoặc nhập IMEI, mỗi dòng một mã"
                                  aria-label={`IMEI kiểm kê ${line.sku}`}
                                />
                              )}
                            </div>
                          )}
                          {line.availableIdentifierUnits.length === 0 && line.tracksSerialNumber && (
                            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
                              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                <div className="text-xs font-bold text-slate-700">Serial ({scannedSerialNumbers.length}/{line.expectedQuantity})</div>
                                <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
                                  <button
                                    type="button"
                                    onClick={() => setStockCountIdentifierMode(line.key, 'SERIAL', 'select')}
                                    className={`rounded-md px-2.5 py-1 text-xs font-bold ${serialMode === 'select' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
                                  >
                                    Chọn mã
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setStockCountIdentifierMode(line.key, 'SERIAL', 'manual')}
                                    className={`rounded-md px-2.5 py-1 text-xs font-bold ${serialMode === 'manual' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
                                  >
                                    Nhập tay
                                  </button>
                                </div>
                              </div>
                              {serialMode === 'select' ? (
                                <TransferIdentifierPicker
                                  label="Serial"
                                  availableTitle="Serial trên kệ"
                                  selectedTitle="Serial đã kiểm kê"
                                  emptyAvailableText="Không có serial hệ thống trên kệ này."
                                  emptySelectedText="Chưa chọn serial kiểm kê."
                                  identifiers={line.availableSerialNumbers}
                                  selectedValues={scannedSerialNumbers}
                                  onToggle={(value, selected) => updateStockCountIdentifiers(line.key, 'SERIAL', value, selected)}
                                />
                              ) : (
                                <textarea
                                  value={line.serialNumbers}
                                  onChange={(event) => updateStockCountLine(line.key, { serialNumbers: event.target.value })}
                                  className="min-h-20 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-xs outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                                  placeholder="Quét hoặc nhập serial, mỗi dòng một mã"
                                  aria-label={`Serial kiểm kê ${line.sku}`}
                                />
                              )}
                            </div>
                          )}
                          {!line.tracksImei && !line.tracksSerialNumber && <span className="text-xs font-semibold text-slate-400">Không quản lý mã</span>}
                        </div>
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
              <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Kệ', 'Tồn hệ thống', 'Thực đếm', 'Mã kiểm kê', 'Chênh lệch', 'Ghi chú']}>
                {(stockCountDetail.lines || []).map((line: any) => (
                  <tr key={line.id}>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-800">{line.productName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{line.variantSku || line.productSku || compactId(line.productId)}</td>
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">{stockCountDetail.locationCode || '-'}</td>
                    <td className="px-4 py-3">{line.expectedQuantity || 0}</td>
                    <td className="px-4 py-3">{line.countedQuantity || 0}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <div>IMEI: {(line.imeis || []).length}</div>
                      <div>Serial: {(line.serialNumbers || []).length}</div>
                      {((line.missingImeis || []).length + (line.unexpectedImeis || []).length + (line.missingSerialNumbers || []).length + (line.unexpectedSerialNumbers || []).length) > 0 && (
                        <div className="mt-1 font-bold text-amber-700">Có mã thiếu/thừa, chưa thể duyệt</div>
                      )}
                    </td>
                    <td className={`px-4 py-3 text-sm font-semibold ${Number(line.varianceQuantity || 0) === 0 ? 'text-slate-500' : Number(line.varianceQuantity || 0) > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{line.varianceQuantity || 0}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{line.note || '-'}</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
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
              <AdminTable headers={['Kệ hàng', 'Tồn khả dụng', 'SL gợi ý', 'Cơ chế']}>
                {issueSuggestionModal.suggestions.length === 0 ? (
                  <tr><td colSpan={4} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Không có tồn khả dụng theo kệ để gợi ý.</td></tr>
                ) : issueSuggestionModal.suggestions.map((item: any) => (
                  <tr key={item.warehouseLocationId || item.locationCode}>
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{item.locationName || '-'}</div>
                      <div className="font-mono text-xs text-slate-500">{item.locationCode || '-'}</div>
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-slate-700">{item.availableQuantity || 0}</td>
                    <td className="px-4 py-3 text-sm font-bold text-indigo-700">{item.suggestedQuantity || 0}</td>
                    <td className="px-4 py-3 text-xs font-semibold text-slate-600">FIFO theo kệ</td>
                  </tr>
                ))}
              </AdminTable>
            </div>
          </div>
        </div>
      )}
    </AdminPanel>
  );
}
