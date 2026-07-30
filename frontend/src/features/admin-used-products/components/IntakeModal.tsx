import { Smartphone, X } from 'lucide-react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';
import type { SourceProduct, UsedProductIntakeDraft } from '../types';

type IntakeModalProps = {
  busy: boolean;
  intakeDraft: UsedProductIntakeDraft;
  products: SourceProduct[];
  selectedProduct?: SourceProduct;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  setIntakeDraft: Dispatch<SetStateAction<UsedProductIntakeDraft>>;
};

export default function IntakeModal({
  busy,
  intakeDraft,
  products,
  selectedProduct,
  onClose,
  onSubmit,
  setIntakeDraft,
}: IntakeModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <form onSubmit={onSubmit} className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Tạo hồ sơ tiếp nhận</h3>
            <p className="mt-1 text-sm text-slate-500">Thiết bị chỉ vào kho hàng cũ sau khi thẩm định và xác nhận thu mua.</p>
          </div>
          <button type="button" title="Đóng" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-700">Nguồn thiết bị
            <select value={intakeDraft.sourceType} onChange={(event) => setIntakeDraft({ ...intakeDraft, sourceType: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3">
              <option value="USER_BUYBACK">Thu mua từ người dùng</option>
              <option value="RETURNED_USED">Máy hoàn về đã sử dụng</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-700">Sản phẩm gốc
            <select required value={intakeDraft.productId} onChange={(event) => setIntakeDraft({ ...intakeDraft, productId: event.target.value, externalProductName: event.target.value === '__EXTERNAL__' ? intakeDraft.externalProductName : '', variantId: '' })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3">
              <option value="">Chọn sản phẩm</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
              <option value="__EXTERNAL__">Model ngoài danh mục</option>
            </select>
          </label>
          {intakeDraft.productId === '__EXTERNAL__' && (
            <label className="text-sm font-semibold text-slate-700">Tên model ngoài danh mục
              <input required minLength={2} value={intakeDraft.externalProductName} onChange={(event) => setIntakeDraft({ ...intakeDraft, externalProductName: event.target.value })} placeholder="Ví dụ: Sony Xperia 5 IV" className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
            </label>
          )}
          <label className="text-sm font-semibold text-slate-700">Biến thể
            <select disabled={intakeDraft.productId === '__EXTERNAL__'} value={intakeDraft.variantId} onChange={(event) => setIntakeDraft({ ...intakeDraft, variantId: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 disabled:bg-slate-100">
              <option value="">Không xác định biến thể</option>
              {(selectedProduct?.variants || []).map((variant) => <option key={variant.id} value={variant.id}>{[variant.colorName, variant.storage, variant.ram, variant.configuration].filter(Boolean).join(' / ') || variant.sku}</option>)}
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-700">IMEI
            <input required inputMode="numeric" pattern="[0-9]{15}" value={intakeDraft.imei} onChange={(event) => setIntakeDraft({ ...intakeDraft, imei: event.target.value.replace(/\D/g, '').slice(0, 15) })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 font-mono" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Serial
            <input value={intakeDraft.serialNumber} onChange={(event) => setIntakeDraft({ ...intakeDraft, serialNumber: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Tên người bán
            <input value={intakeDraft.sellerName} onChange={(event) => setIntakeDraft({ ...intakeDraft, sellerName: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Số điện thoại
            <input value={intakeDraft.sellerPhone} onChange={(event) => setIntakeDraft({ ...intakeDraft, sellerPhone: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Số giấy tờ định danh
            <input value={intakeDraft.sellerIdentityNumber} onChange={(event) => setIntakeDraft({ ...intakeDraft, sellerIdentityNumber: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Địa chỉ người bán
            <input value={intakeDraft.sellerAddress} onChange={(event) => setIntakeDraft({ ...intakeDraft, sellerAddress: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700">Giá mong muốn
            <input type="number" min="0" value={intakeDraft.expectedPrice} onChange={(event) => setIntakeDraft({ ...intakeDraft, expectedPrice: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3" />
          </label>
          <label className="text-sm font-semibold text-slate-700 md:col-span-2">Ghi chú
            <textarea value={intakeDraft.note} onChange={(event) => setIntakeDraft({ ...intakeDraft, note: event.target.value })} rows={3} className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2" />
          </label>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
          <button type="button" onClick={onClose} className="h-9 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-600">Hủy</button>
          <button type="submit" disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-md bg-emerald-700 px-3 text-sm font-bold text-white disabled:opacity-50"><Smartphone className="h-4 w-4" /> Lưu hồ sơ</button>
        </div>
      </form>
    </div>
  );
}
