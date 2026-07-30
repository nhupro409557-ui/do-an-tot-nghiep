import { ImagePlus, PackageCheck, X } from 'lucide-react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { resolveImageUrl } from '../../../services/productMedia';
import type { UsedProductEvidence, UsedProductInspectionDraft, UsedProductIntake } from '../types';

type InspectionModalProps = {
  busy: boolean;
  inspectionDraft: UsedProductInspectionDraft;
  selectedIntake: UsedProductIntake;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  setInspectionDraft: Dispatch<SetStateAction<UsedProductInspectionDraft>>;
  uploadInspectionEvidence: (files: FileList | null) => void;
};

const checklistOptions = [
  ['imeiVerified', 'IMEI trên máy khớp hồ sơ'],
  ['screen', 'Màn hình và cảm ứng'],
  ['camera', 'Camera'],
  ['connectivity', 'Kết nối và SIM'],
  ['biometric', 'Sinh trắc học'],
  ['accountUnlocked', 'Đã thoát tài khoản/khóa máy'],
  ['dataErased', 'Đã xóa dữ liệu cá nhân'],
  ['charging', 'Sạc và cổng kết nối'],
  ['audioAndButtons', 'Loa, mic và phím vật lý'],
];

export default function InspectionModal({
  busy,
  inspectionDraft,
  selectedIntake,
  onClose,
  onSubmit,
  setInspectionDraft,
  uploadInspectionEvidence,
}: InspectionModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <form onSubmit={onSubmit} className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Thẩm định {selectedIntake.requestCode}</h3>
            <p className="mt-1 text-sm text-slate-500">{selectedIntake.productName} · IMEI {selectedIntake.imei}</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-3">
          <label className="text-sm font-semibold text-slate-700">Kết quả
            <select value={inspectionDraft.outcome} onChange={(event) => setInspectionDraft({ ...inspectionDraft, outcome: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3">
              <option value="APPRAISED">Đạt, đề xuất thu mua</option>
              <option value="REPAIR_REQUIRED">Cần sửa chữa</option>
              <option value="REJECTED">Từ chối</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-700">Hạng
            <select value={inspectionDraft.conditionGrade} onChange={(event) => setInspectionDraft({ ...inspectionDraft, conditionGrade: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3">
              <option value="A">A - Rất tốt</option><option value="B">B - Tốt</option><option value="C">C - Có dấu hiệu sử dụng</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-700">Điểm tình trạng
            <input type="number" min="0" max="100" value={inspectionDraft.conditionScore} onChange={(event) => setInspectionDraft({ ...inspectionDraft, conditionScore: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Sức khỏe pin (%)
            <input type="number" min="0" max="100" value={inspectionDraft.batteryHealth} onChange={(event) => setInspectionDraft({ ...inspectionDraft, batteryHealth: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Giá thu mua
            <input type="number" min="0" value={inspectionDraft.proposedAcquisitionPrice} onChange={(event) => setInspectionDraft({ ...inspectionDraft, proposedAcquisitionPrice: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Chi phí sửa dự kiến
            <input type="number" min="0" value={inspectionDraft.repairCostEstimate} onChange={(event) => setInspectionDraft({ ...inspectionDraft, repairCostEstimate: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Giá bán hàng cũ
            <input type="number" min="0" value={inspectionDraft.proposedSalePrice} onChange={(event) => setInspectionDraft({ ...inspectionDraft, proposedSalePrice: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <fieldset className="md:col-span-2">
            <legend className="text-sm font-semibold text-slate-700">Checklist chức năng</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {checklistOptions.map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm font-semibold text-slate-600">
                  <input type="checkbox" checked={Boolean((inspectionDraft.checklist as any)[key])} onChange={(event) => setInspectionDraft({ ...inspectionDraft, checklist: { ...inspectionDraft.checklist, [key]: event.target.checked } })} className="h-4 w-4 rounded border-slate-300 text-emerald-600" />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="md:col-span-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-700">Ảnh thực tế và bằng chứng QC</div>
                <div className="mt-1 text-xs text-slate-500">Kết quả đạt cần ít nhất 3 ảnh: mặt trước, mặt sau và cạnh máy/điểm trầy xước.</div>
              </div>
              <label className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50">
                <ImagePlus className="h-4 w-4" /> Thêm ảnh
                <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(event) => void uploadInspectionEvidence(event.target.files)} />
              </label>
            </div>
            {inspectionDraft.evidence.length > 0 && (
              <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
                {inspectionDraft.evidence.map((item) => (
                  <div key={item.url} className="relative aspect-square overflow-hidden rounded-md border border-slate-200 bg-slate-50">
                    <img src={resolveImageUrl(item.url)} alt={item.name || 'Ảnh thẩm định'} className="h-full w-full object-cover" />
                    <button type="button" title="Xóa ảnh" onClick={() => setInspectionDraft((current) => ({ ...current, evidence: current.evidence.filter((evidence: UsedProductEvidence) => evidence.url !== item.url) }))} className="absolute right-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-md bg-slate-950/75 text-white"><X className="h-4 w-4" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <label className="text-sm font-semibold text-slate-700 md:col-span-3">Ghi chú thẩm định
            <textarea value={inspectionDraft.note} onChange={(event) => setInspectionDraft({ ...inspectionDraft, note: event.target.value })} rows={3} className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2" />
          </label>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <button type="button" onClick={onClose} className="h-9 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-600">Hủy</button>
          <button type="submit" disabled={busy || (inspectionDraft.outcome === 'APPRAISED' && inspectionDraft.evidence.length < 3)} className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-600 px-3 text-sm font-bold text-white disabled:opacity-50"><PackageCheck className="h-4 w-4" /> Lưu thẩm định</button>
        </div>
      </form>
    </div>
  );
}
