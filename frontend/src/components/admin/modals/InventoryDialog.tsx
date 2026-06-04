import React from 'react';
import { Input, Select } from '../AdminDashboardParts';
import { X } from 'lucide-react';
import { inventoryTransactionOptions } from '../../../pages/AdminDashboardConfig';

type InventoryDialogProps = Record<string, any>;

export default function InventoryDialog(props: InventoryDialogProps) {
  const {
    inventoryDraft,
    setInventoryDraft,
    submitInventoryDraft,
  } = props;

  if (!inventoryDraft) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={submitInventoryDraft} className="w-full max-w-3xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Nhập/điều chỉnh kho</h3>
            <p className="mt-1 text-sm text-slate-500">{inventoryDraft.product.name}{inventoryDraft.variant?.sku ? ` / ${inventoryDraft.variant.sku}` : ''}</p>
          </div>
          <button type="button" onClick={() => setInventoryDraft(null)} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid gap-3 p-5 md:grid-cols-2">
          <Select label="Kiểu giao dịch" value={inventoryDraft.transactionType} onChange={(value) => setInventoryDraft({ ...inventoryDraft, transactionType: value })} options={inventoryTransactionOptions} />
          <Input label="Số lượng thay đổi" type="number" value={inventoryDraft.delta} onChange={(value) => setInventoryDraft({ ...inventoryDraft, delta: Number(value) })} />
          <Input label="Mã phiếu tham chiếu" value={inventoryDraft.referenceCode} required onChange={(value) => setInventoryDraft({ ...inventoryDraft, referenceCode: value })} />
          <Input label="Lý do" value={inventoryDraft.reason} required onChange={(value) => setInventoryDraft({ ...inventoryDraft, reason: value })} />
          <Input label="Nhà cung cấp" value={inventoryDraft.supplierName} onChange={(value) => setInventoryDraft({ ...inventoryDraft, supplierName: value })} />
          <Input label="Giá nhập" type="number" value={inventoryDraft.unitCost} onChange={(value) => setInventoryDraft({ ...inventoryDraft, unitCost: Number(value) })} />
          <Input label="Tồn kho tối thiểu" type="number" value={inventoryDraft.minimumStock} onChange={(value) => setInventoryDraft({ ...inventoryDraft, minimumStock: Math.max(0, Number(value)) })} />
          <Input label="Chu kỳ kiểm kê (ngày)" type="number" value={inventoryDraft.cycleCountDays} onChange={(value) => setInventoryDraft({ ...inventoryDraft, cycleCountDays: Math.max(1, Number(value)) })} />
          <label className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 md:col-span-2">
            <input type="checkbox" checked={inventoryDraft.blockSaleWhenOutOfStock} onChange={(event) => setInventoryDraft({ ...inventoryDraft, blockSaleWhenOutOfStock: event.target.checked })} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" />
            Khóa bán khi hết hàng
          </label>
          <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-2" placeholder="IMEI khi nhập kho, mỗi dòng một IMEI. Để trống hệ thống tự tạo từ SKU biến thể + 10 số ngẫu nhiên." value={inventoryDraft.imeis} onChange={(event) => setInventoryDraft({ ...inventoryDraft, imeis: event.target.value })} />
          <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-2" placeholder="Ghi chú kho" value={inventoryDraft.note} onChange={(event) => setInventoryDraft({ ...inventoryDraft, note: event.target.value })} />
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 md:col-span-2">
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Lịch sử gần nhất</div>
            {inventoryDraft.logs.length === 0 ? (
              <div className="text-sm font-medium text-slate-500">Chưa có giao dịch kho.</div>
            ) : (
              <div className="max-h-52 overflow-y-auto divide-y divide-slate-200 rounded-md bg-white">
                {inventoryDraft.logs.map((log: any) => (
                  <div key={log.id} className="grid gap-2 px-3 py-2 text-xs text-slate-600 md:grid-cols-[1fr_90px_100px]">
                    <span className="font-semibold text-slate-800">{log.referenceCode || '-'} · {log.transactionType}{log.locationCode ? ` · ${log.locationCode}` : ''}</span>
                    <span className={Number(log.delta || 0) >= 0 ? 'font-bold text-emerald-700' : 'font-bold text-red-700'}>{Number(log.delta || 0) >= 0 ? '+' : ''}{log.delta}</span>
                    <span>{log.createdAt ? new Date(log.createdAt).toLocaleDateString('vi-VN') : '-'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2 md:col-span-2">
            <button type="button" onClick={() => setInventoryDraft(null)} className="h-10 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700">Hủy</button>
            <button type="submit" className="h-10 rounded-md bg-amber-600 px-4 text-sm font-bold text-white">Lưu giao dịch</button>
          </div>
        </div>
      </form>
    </div>
  );
}
