import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { customerCenterApi } from '../services/customerCenterApi';

export function VoucherWalletTab() {
  const navigate = useNavigate();
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { customerCenterApi.listVouchers().then(setItems).catch(() => setItems([])); }, []);
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="font-bold text-slate-900">Ví voucher của tôi</h3>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {items.map(item => (
          <article key={item.id} className="rounded-xl border border-dashed border-red-200 bg-red-50/40 p-4">
            <div className="text-lg font-black text-[#d70018]">{item.code}</div>
            <p className="mt-1 text-sm text-slate-600">{item.status} · Hết hạn: {item.expires_at || item.expiresAt ? new Date(item.expires_at || item.expiresAt).toLocaleDateString('vi-VN') : 'Theo chương trình'}</p>
            {item.status === 'AVAILABLE' && <button onClick={() => { localStorage.setItem('selectedVoucherCode', item.code); navigate('/cart'); }} className="mt-3 rounded-lg bg-[#d70018] px-4 py-2 text-sm font-bold text-white">Áp dụng vào giỏ</button>}
          </article>
        ))}
        {!items.length && <p className="text-sm text-slate-500">Bạn chưa nhận voucher nào.</p>}
      </div>
    </section>
  );
}

export function TransactionsTab() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { customerCenterApi.listTransactions().then(data => setItems(data.items || [])).catch(() => setItems([])); }, []);
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm">
      <h3 className="font-bold text-slate-900">Thanh toán và hoàn tiền</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead><tr className="border-b text-slate-500"><th className="p-3">Loại</th><th>Đơn hàng</th><th>Cổng</th><th>Số tiền</th><th>Trạng thái</th><th>Mã tham chiếu</th><th /></tr></thead>
          <tbody>{items.map(item => <tr key={`${item.type}-${item.id}`} className="border-b">
            <td className="p-3 font-semibold">{item.type === 'REFUND' ? 'Hoàn tiền' : 'Thanh toán'}</td>
            <td>#{item.orderCode}</td><td>{item.provider}</td><td>{Number(item.amount).toLocaleString('vi-VN')}đ</td><td>{item.status}</td><td>{item.transactionRef || '-'}</td>
            <td>{item.type === 'PAYMENT' && ['FAILED', 'EXPIRED'].includes(item.status) && <a href={`/payment/${item.id}`} className="font-semibold text-red-600">Thanh toán lại</a>}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}

export function NotificationsTab() {
  const [items, setItems] = useState<any[]>([]);
  async function load() { const data = await customerCenterApi.listNotifications(); setItems(data.items || []); }
  useEffect(() => { void load(); }, []);
  return (
    <section className="rounded-xl bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between"><h3 className="font-bold text-slate-900">Trung tâm thông báo</h3><button onClick={() => customerCenterApi.markAllNotificationsRead().then(load)} className="text-sm font-semibold text-red-600">Đánh dấu đã đọc</button></div>
      <div className="mt-4 space-y-2">{items.map(item => <button key={item.id} onClick={() => customerCenterApi.markNotificationRead(item.id).then(load)} className={`w-full rounded-lg border p-4 text-left ${item.read ? 'bg-white' : 'border-blue-200 bg-blue-50'}`}>
        <div className="font-bold">{item.title}</div><div className="mt-1 text-sm text-slate-600">{item.message}</div><div className="mt-1 text-xs text-slate-400">{new Date(item.createdAt).toLocaleString('vi-VN')}</div>
      </button>)}</div>
    </section>
  );
}
