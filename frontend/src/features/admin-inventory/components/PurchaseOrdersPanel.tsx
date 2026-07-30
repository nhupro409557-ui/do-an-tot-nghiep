import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Pencil, Plus, Send, XCircle } from 'lucide-react';
import { AdminBadge } from '../../admin-shell/components/AdminDashboardParts';
import { currency } from '../../admin-shell/components/AdminDashboardConfig';
import { adminInventoryApi } from '../services/adminInventoryApi';

const statusLabel: Record<string, string> = {
  DRAFT: 'Nháp', PENDING_APPROVAL: 'Chờ duyệt', APPROVED: 'Đã duyệt',
  PARTIALLY_RECEIVED: 'Đã nhận một phần', COMPLETED: 'Đã nhận đủ', CANCELLED: 'Đã hủy',
};

function emptyLine() {
  return { id: crypto.randomUUID(), productId: '', variantId: '', quantity: 1, unitCost: 0, note: '' };
}

export default function PurchaseOrdersPanel({ products = [], suppliers = [], isSuperAdmin = false }: Record<string, any>) {
  const [orders, setOrders] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState('');
  const [form, setForm] = useState<any>({ code: '', supplierId: '', expectedDate: '', note: '', discountAmount: 0, shippingFee: 0, lines: [emptyLine()] });
  const activeSuppliers = useMemo(() => suppliers.filter((item: any) => item.isActive !== false), [suppliers]);

  async function load() {
    setOrders(await adminInventoryApi.adminListPurchaseOrders().catch(() => []));
  }
  useEffect(() => { void load(); }, []);

  function updateLine(id: string, patch: any) {
    setForm((current: any) => ({ ...current, lines: current.lines.map((line: any) => line.id === id ? { ...line, ...patch } : line) }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.code.trim() || !form.supplierId) return window.alert('Vui lòng nhập mã đơn và chọn nhà cung cấp.');
    const lines = form.lines.filter((line: any) => line.productId && Number(line.quantity) > 0 && Number(line.unitCost) > 0);
    if (!lines.length) return window.alert('Đơn mua phải có ít nhất một dòng hợp lệ.');
    const payload = {
      ...form, code: form.code.trim(), expectedDate: form.expectedDate || null,
      lines: lines.map(({ id, ...line }: any) => ({ ...line, variantId: line.variantId || null, quantity: Number(line.quantity), unitCost: Number(line.unitCost) })),
    };
    if (editingId) await adminInventoryApi.adminUpdatePurchaseOrder(editingId, payload);
    else await adminInventoryApi.adminCreatePurchaseOrder(payload);
    setOpen(false);
    setEditingId('');
    setForm({ code: '', supplierId: '', expectedDate: '', note: '', discountAmount: 0, shippingFee: 0, lines: [emptyLine()] });
    await load();
  }

  async function editOrder(order: any) {
    const detail = await adminInventoryApi.adminGetPurchaseOrder(order.id);
    setEditingId(String(order.id));
    setForm({
      code: detail.code, supplierId: String(detail.supplierId), expectedDate: detail.expectedDate ? String(detail.expectedDate).slice(0, 10) : '',
      note: detail.note || '', discountAmount: Number(detail.discountAmount || 0), shippingFee: Number(detail.shippingFee || 0),
      lines: (detail.lines || []).map((line: any) => ({ id: String(line.id), productId: String(line.productId), variantId: String(line.variantId || ''), quantity: Number(line.quantity), unitCost: Number(line.unitCost), note: line.note || '' })),
    });
    setOpen(true);
  }

  async function changeStatus(order: any, status: string) {
    await adminInventoryApi.adminUpdatePurchaseOrderStatus(order.id, { status });
    await load();
  }

  return (
    <div className="mb-5 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><div className="font-bold text-indigo-950">Đơn mua hàng</div><div className="text-xs font-semibold text-indigo-700">Lập kế hoạch mua, duyệt và theo dõi số lượng đã nhận qua nhiều phiếu nhập.</div></div>
        <button type="button" onClick={() => setOpen(!open)} className="inline-flex h-9 items-center gap-1 rounded-lg bg-indigo-600 px-3 text-xs font-bold text-white"><Plus className="h-4 w-4" /> Tạo đơn mua</button>
      </div>
      {open && <form onSubmit={submit} className="mt-4 space-y-3 rounded-lg border border-indigo-100 bg-white p-3">
        <div className="grid gap-2 md:grid-cols-3">
          <input className="h-10 rounded-lg border px-3 text-sm" placeholder="Mã đơn mua" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          <select className="h-10 rounded-lg border px-3 text-sm" value={form.supplierId} onChange={(e) => setForm({ ...form, supplierId: e.target.value })}><option value="">Chọn nhà cung cấp</option>{activeSuppliers.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
          <input type="date" className="h-10 rounded-lg border px-3 text-sm" value={form.expectedDate} onChange={(e) => setForm({ ...form, expectedDate: e.target.value })} />
          <input type="number" min="0" className="h-10 rounded-lg border px-3 text-sm" placeholder="Chiết khấu" value={form.discountAmount} onChange={(e) => setForm({ ...form, discountAmount: Number(e.target.value) })} />
          <input type="number" min="0" className="h-10 rounded-lg border px-3 text-sm" placeholder="Phí nhập/vận chuyển" value={form.shippingFee} onChange={(e) => setForm({ ...form, shippingFee: Number(e.target.value) })} />
          <input className="h-10 rounded-lg border px-3 text-sm" placeholder="Ghi chú" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        </div>
        {form.lines.map((line: any) => {
          const product = products.find((item: any) => String(item.id) === line.productId);
          return <div key={line.id} className="grid gap-2 md:grid-cols-[2fr_2fr_100px_150px_40px]">
            <select className="h-10 rounded-lg border px-2 text-sm" value={line.productId} onChange={(e) => updateLine(line.id, { productId: e.target.value, variantId: '' })}><option value="">Chọn sản phẩm</option>{products.filter((p: any) => String(p.status || '').toUpperCase() === 'ACTIVE').map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
            <select className="h-10 rounded-lg border px-2 text-sm" value={line.variantId} onChange={(e) => updateLine(line.id, { variantId: e.target.value })}><option value="">Chọn biến thể</option>{(product?.variants || []).map((v: any) => <option key={v.id} value={v.id}>{v.sku || v.name || v.id}</option>)}</select>
            <input type="number" min="1" className="h-10 rounded-lg border px-2 text-sm" value={line.quantity} onChange={(e) => updateLine(line.id, { quantity: Number(e.target.value) })} />
            <input type="number" min="1" className="h-10 rounded-lg border px-2 text-sm" placeholder="Đơn giá" value={line.unitCost} onChange={(e) => updateLine(line.id, { unitCost: Number(e.target.value) })} />
            <button type="button" disabled={form.lines.length === 1} onClick={() => setForm({ ...form, lines: form.lines.filter((item: any) => item.id !== line.id) })} className="text-red-600 disabled:opacity-30">×</button>
          </div>;
        })}
        <div className="flex gap-2"><button type="button" onClick={() => setForm({ ...form, lines: [...form.lines, emptyLine()] })} className="h-9 rounded-lg border px-3 text-xs font-bold">Thêm dòng</button><button type="submit" className="h-9 rounded-lg bg-indigo-600 px-4 text-xs font-bold text-white">{editingId ? 'Cập nhật đơn mua' : 'Lưu đơn mua'}</button></div>
      </form>}
      <div className="mt-4 overflow-x-auto"><table className="min-w-full text-left text-xs"><thead className="text-slate-500"><tr><th className="py-2">Mã đơn</th><th>Nhà cung cấp</th><th>Trạng thái</th><th>Đã nhận</th><th>Tổng giá trị</th><th>Thao tác</th></tr></thead><tbody className="divide-y divide-indigo-100">{orders.slice(0, 10).map((order: any) => <tr key={order.id}><td className="py-2 font-mono font-bold">{order.code}</td><td>{order.supplierName}</td><td><AdminBadge tone={order.status === 'COMPLETED' ? 'green' : order.status === 'CANCELLED' ? 'red' : 'blue'}>{statusLabel[order.status] || order.status}</AdminBadge></td><td>{order.receivedQuantity}/{order.orderedQuantity}</td><td>{currency.format(Number(order.totalAmount || 0))}</td><td><div className="flex gap-1">{order.status === 'DRAFT' && <button title="Sửa đơn" onClick={() => void editOrder(order)}><Pencil className="h-4 w-4" /></button>}{order.status === 'DRAFT' && <button title="Gửi duyệt" onClick={() => void changeStatus(order, 'PENDING_APPROVAL')}><Send className="h-4 w-4" /></button>}{isSuperAdmin && order.status === 'PENDING_APPROVAL' && <button title="Duyệt" className="text-emerald-700" onClick={() => void changeStatus(order, 'APPROVED')}><CheckCircle2 className="h-4 w-4" /></button>}{isSuperAdmin && ['DRAFT', 'PENDING_APPROVAL', 'APPROVED'].includes(order.status) && <button title="Hủy" className="text-red-600" onClick={() => void changeStatus(order, 'CANCELLED')}><XCircle className="h-4 w-4" /></button>}</div></td></tr>)}</tbody></table></div>
    </div>
  );
}
