import { BadgeCheck, X } from 'lucide-react';
import type { FormEvent } from 'react';
import type { UsedProductIntake, UsedProductStatusPayload } from '../types';

type AcquisitionConfirmationModalProps = {
  busy: boolean;
  intake: UsedProductIntake;
  draft: UsedProductStatusPayload;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  setDraft: (draft: UsedProductStatusPayload) => void;
};

export default function AcquisitionConfirmationModal({
  busy,
  intake,
  draft,
  onClose,
  onSubmit,
  setDraft,
}: AcquisitionConfirmationModalProps) {
  const needsReference = ['BANK_TRANSFER', 'TRADE_IN_CREDIT'].includes(draft.acquisitionPaymentMethod || '');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <form onSubmit={onSubmit} className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="acquisition-title">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 id="acquisition-title" className="text-lg font-bold text-slate-900">Xác nhận thu mua {intake.requestCode}</h3>
            <p className="mt-1 text-sm text-slate-500">{intake.productName} · Giá thu {new Intl.NumberFormat('vi-VN').format(Number(intake.proposedAcquisitionPrice || 0))} đ</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-700">Số giấy tờ định danh
            <input required value={draft.sellerIdentityNumber || ''} onChange={(event) => setDraft({ ...draft, sellerIdentityNumber: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-emerald-600" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Phương thức chi trả
            <select required value={draft.acquisitionPaymentMethod || ''} onChange={(event) => setDraft({ ...draft, acquisitionPaymentMethod: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-emerald-600">
              <option value="">Chọn phương thức</option>
              <option value="CASH">Tiền mặt</option>
              <option value="BANK_TRANSFER">Chuyển khoản</option>
              <option value="TRADE_IN_CREDIT">Bù trừ đơn đổi máy</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Địa chỉ người bán
            <input required minLength={5} value={draft.sellerAddress || ''} onChange={(event) => setDraft({ ...draft, sellerAddress: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-emerald-600" />
          </label>
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Mã tham chiếu {needsReference ? '(bắt buộc)' : '(nếu có)'}
            <input required={needsReference} value={draft.acquisitionPaymentReference || ''} onChange={(event) => setDraft({ ...draft, acquisitionPaymentReference: event.target.value })} placeholder="Mã giao dịch hoặc mã đơn đổi máy" className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 outline-none focus:border-emerald-600" />
          </label>
          <label className="flex items-start gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-900 md:col-span-2">
            <input required type="checkbox" checked={Boolean(draft.ownershipConfirmed)} onChange={(event) => setDraft({ ...draft, ownershipConfirmed: event.target.checked })} className="mt-0.5 h-4 w-4 rounded border-emerald-300 text-emerald-700" />
            Người bán xác nhận là chủ sở hữu hợp pháp, thiết bị không có tranh chấp và đồng ý mức giá thu mua.
          </label>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <button type="button" onClick={onClose} className="h-9 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-600">Hủy</button>
          <button type="submit" disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-md bg-emerald-700 px-3 text-sm font-bold text-white disabled:opacity-50"><BadgeCheck className="h-4 w-4" /> Xác nhận và tạo thiết bị</button>
        </div>
      </form>
    </div>
  );
}
