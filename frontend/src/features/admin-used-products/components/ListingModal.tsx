import { FilePenLine, ImagePlus, X } from 'lucide-react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';
import { resolveImageUrl } from '../../../services/productMedia';
import type { UsedProductDevice, UsedProductListingDraft } from '../types';

type ListingModalProps = {
  busy: boolean;
  listingDraft: UsedProductListingDraft;
  money: Intl.NumberFormat;
  selectedDevice: UsedProductDevice;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  setListingDraft: Dispatch<SetStateAction<UsedProductListingDraft>>;
  uploadListingImages: (files: FileList | null) => void;
};

export default function ListingModal({
  busy,
  listingDraft,
  money,
  selectedDevice,
  onClose,
  onSubmit,
  setListingDraft,
  uploadListingImages,
}: ListingModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <form onSubmit={onSubmit} className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Bài đăng {selectedDevice.deviceCode}</h3>
            <p className="mt-1 text-sm text-slate-500">{selectedDevice.productName} · Hạng {selectedDevice.conditionGrade} · {money.format(Number(selectedDevice.approvedSalePrice || 0))}</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-11 w-11 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid gap-5 p-5 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Tiêu đề bài đăng
            <input required minLength={5} value={listingDraft.title} onChange={(event) => setListingDraft({ ...listingDraft, title: event.target.value })} className="mt-1 h-11 w-full rounded-md border border-slate-200 px-3 text-base outline-none focus:border-emerald-600" />
          </label>
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Mô tả tình trạng
            <textarea required minLength={20} value={listingDraft.description} onChange={(event) => setListingDraft({ ...listingDraft, description: event.target.value })} rows={4} className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-base outline-none focus:border-emerald-600" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Điểm nổi bật
            <textarea value={listingDraft.highlightsText} onChange={(event) => setListingDraft({ ...listingDraft, highlightsText: event.target.value })} rows={5} placeholder="Mỗi dòng là một điểm nổi bật" className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-base outline-none focus:border-emerald-600" />
          </label>
          <div>
            <label className="text-sm font-semibold text-slate-700">Bảo hành hàng cũ
              <select value={listingDraft.warrantyMonths} onChange={(event) => setListingDraft({ ...listingDraft, warrantyMonths: event.target.value })} className="mt-1 h-11 w-full rounded-md border border-slate-200 bg-white px-3 text-base">
                {[0, 1, 3, 6, 9, 12].map((months) => <option key={months} value={months}>{months === 0 ? 'Không bảo hành' : `${months} tháng`}</option>)}
              </select>
            </label>
            <label className="mt-4 block text-sm font-semibold text-slate-700">Ghi chú so sánh giá
              <textarea value={listingDraft.priceComparisonNote} onChange={(event) => setListingDraft({ ...listingDraft, priceComparisonNote: event.target.value })} rows={2} className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-base outline-none focus:border-emerald-600" />
            </label>
          </div>
          <div className="md:col-span-2">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-700">Ảnh công khai của đúng thiết bị</div>
                <div className="mt-1 text-xs text-slate-500">Bài đăng phải có ít nhất một ảnh thực tế.</div>
              </div>
              <label className="inline-flex h-11 cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50">
                <ImagePlus className="h-4 w-4" /> Tải thêm ảnh
                <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(event) => void uploadListingImages(event.target.files)} />
              </label>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
              {listingDraft.images.map((image: string) => (
                <div key={image} className="relative aspect-square overflow-hidden rounded-md border border-slate-200 bg-slate-50">
                  <img src={resolveImageUrl(image)} alt="Ảnh thực tế bài đăng" className="h-full w-full object-cover" />
                  <button type="button" title="Xóa ảnh" onClick={() => setListingDraft((current) => ({ ...current, images: current.images.filter((item) => item !== image) }))} className="absolute right-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-md bg-slate-950/75 text-white"><X className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <button type="button" onClick={onClose} className="h-11 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-600">Hủy</button>
          <button type="submit" disabled={busy || listingDraft.images.length === 0} className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"><FilePenLine className="h-4 w-4" /> Lưu bài nháp</button>
        </div>
      </form>
    </div>
  );
}
