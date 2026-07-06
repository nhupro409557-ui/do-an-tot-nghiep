import { X } from 'lucide-react';
import type { UsedProductHistory, UsedProductHistoryEntry } from '../types';

type DeviceHistoryModalProps = {
  deviceHistory: UsedProductHistory;
  money: Intl.NumberFormat;
  statusLabels: Record<string, string>;
  onClose: () => void;
};

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default function DeviceHistoryModal({
  deviceHistory,
  money,
  statusLabels,
  onClose,
}: DeviceHistoryModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Lịch sử {deviceHistory.device?.deviceCode}</h3>
            <p className="mt-1 text-sm text-slate-500">{deviceHistory.device?.productName} · IMEI {deviceHistory.device?.imei}</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-3 p-5">
          {(deviceHistory.items || []).map((item: UsedProductHistoryEntry, index: number) => (
            <div key={`${item.entryType}-${item.createdAt}-${index}`} className="rounded-md border border-slate-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-bold text-slate-900">{item.title}</div>
                  <div className="mt-1 text-xs font-semibold text-slate-500">{formatDateTime(item.createdAt)} · {item.entryType}</div>
                </div>
                {(item.oldStatus || item.newStatus) && (
                  <div className="text-xs font-bold text-slate-600">
                    {item.oldStatus ? `${statusLabels[item.oldStatus] || item.oldStatus} -> ` : ''}
                    {statusLabels[item.newStatus] || item.newStatus}
                  </div>
                )}
              </div>
              {item.note && <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">{item.note}</div>}
              {item.entryType === 'INSPECTION' && (
                <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                  <div>Kết quả: {statusLabels[item.outcome] || item.outcome || '-'}</div>
                  <div>Hạng: {item.conditionGrade || '-'}</div>
                  <div>Điểm: {item.conditionScore ?? '-'}/100</div>
                  <div>Pin: {item.batteryHealth ?? '-'}%</div>
                </div>
              )}
              {(item.proposedSalePrice != null || item.approvedSalePrice != null || item.repairCostEstimate != null) && (
                <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                  <div>Chi phí sửa: {money.format(Number(item.repairCostEstimate || 0))}</div>
                  <div>Giá đề xuất: {money.format(Number(item.proposedSalePrice || 0))}</div>
                  <div>Giá duyệt: {money.format(Number(item.approvedSalePrice || 0))}</div>
                </div>
              )}
            </div>
          ))}
          {(!deviceHistory.items || deviceHistory.items.length === 0) && (
            <div className="rounded-md border border-dashed border-slate-200 px-4 py-8 text-center text-sm font-semibold text-slate-500">Thiết bị chưa có lịch sử.</div>
          )}
        </div>
      </div>
    </div>
  );
}
