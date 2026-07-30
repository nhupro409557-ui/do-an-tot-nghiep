import { Wrench, X } from 'lucide-react';
import type { FormEvent } from 'react';
import type { UsedProductDevice, UsedProductRepairPayload } from '../types';

type RepairModalProps = {
  busy: boolean;
  device: UsedProductDevice;
  draft: UsedProductRepairPayload;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  setDraft: (draft: UsedProductRepairPayload) => void;
};

export default function RepairModal({ busy, device, draft, onClose, onSubmit, setDraft }: RepairModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-lg rounded-lg bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="repair-title">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 id="repair-title" className="text-lg font-bold text-slate-900">Ghi nhận sửa chữa</h3>
            <p className="mt-1 text-sm text-slate-500">{device.deviceCode} · {device.productName}</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-4 p-5">
          <label className="block text-sm font-semibold text-slate-700">Nội dung sửa chữa
            <textarea required minLength={3} rows={4} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 outline-none focus:border-purple-600" />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700">Chi phí thực tế
              <input required type="number" min="0" value={draft.cost} onChange={(event) => setDraft({ ...draft, cost: Number(event.target.value) })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-purple-600" />
            </label>
            <label className="text-sm font-semibold text-slate-700">Ngày sửa
              <input type="date" value={draft.repairedAt || ''} onChange={(event) => setDraft({ ...draft, repairedAt: event.target.value || null })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-purple-600" />
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <button type="button" onClick={onClose} className="h-9 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-600">Hủy</button>
          <button type="submit" disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-md bg-purple-700 px-3 text-sm font-bold text-white disabled:opacity-50"><Wrench className="h-4 w-4" /> Lưu sửa chữa</button>
        </div>
      </form>
    </div>
  );
}
