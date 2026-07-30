import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { customerCenterApi } from '../services/customerCenterApi';

const voucherStatusLabels: Record<string, string> = {
  AVAILABLE: 'Có thể sử dụng',
  RESERVED: 'Đang giữ chỗ',
  USED: 'Đã sử dụng',
  EXPIRED: 'Đã hết hạn',
  REVOKED: 'Đã thu hồi',
};

const transactionStatusLabels: Record<string, string> = {
  PENDING: 'Chờ xử lý',
  PROCESSING: 'Đang xử lý',
  PAID: 'Đã thanh toán',
  PAID_LATE: 'Thanh toán trễ cần đối soát',
  COMPLETED: 'Hoàn thành',
  FAILED: 'Thất bại',
  EXPIRED: 'Đã hết hạn',
  REFUNDED: 'Đã hoàn tiền',
};

const transactionStatusStyles: Record<string, string> = {
  PENDING: 'text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  PROCESSING: 'text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  PAID: 'text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  PAID_LATE: 'text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  COMPLETED: 'text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  FAILED: 'text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  EXPIRED: 'text-rose-600 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
  REFUNDED: 'text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-xs font-semibold inline-block',
};

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
            <p className="mt-1 text-sm text-slate-600">{voucherStatusLabels[item.status] || item.status} · Hết hạn: {item.expires_at || item.expiresAt ? new Date(item.expires_at || item.expiresAt).toLocaleDateString('vi-VN') : 'Theo chương trình'}</p>
            {item.status === 'AVAILABLE' && <button type="button" onClick={() => { localStorage.setItem('selectedVoucherCode', item.code); navigate('/checkout'); }} className="mt-3 rounded-lg bg-[#d70018] px-4 py-2 text-sm font-bold text-white">Áp dụng vào giỏ</button>}
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
          <thead><tr className="border-b text-slate-500"><th className="p-3">Loại</th><th>Đơn hàng</th><th>Cổng</th><th>Số tiền</th><th>Trạng thái</th><th>Mã tham chiếu</th><th>Thao tác</th></tr></thead>
          <tbody>{items.map(item => <tr key={`${item.type}-${item.id}`} className="border-b">
            <td className="p-3 font-semibold">{item.type === 'REFUND' ? 'Hoàn tiền' : 'Thanh toán'}</td>
            <td>#{item.orderCode}</td><td>{item.provider}</td><td>{Number(item.amount).toLocaleString('vi-VN')}đ</td><td><span className={transactionStatusStyles[item.status] || 'text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-xs font-semibold inline-block'}>{transactionStatusLabels[item.status] || item.status}</span></td><td>{item.transactionRef || '-'}</td>
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
      <div className="flex items-center justify-between"><h3 className="font-bold text-slate-900">Trung tâm thông báo</h3><button type="button" onClick={() => customerCenterApi.markAllNotificationsRead().then(load)} className="text-sm font-semibold text-red-600">Đánh dấu đã đọc</button></div>
      <div className="mt-4 space-y-2">{items.map(item => <button type="button" key={item.id} onClick={() => customerCenterApi.markNotificationRead(item.id).then(load)} className={`w-full rounded-lg border p-4 text-left ${item.read ? 'bg-white' : 'border-blue-200 bg-blue-50'}`}>
        <div className="font-bold">{item.title}</div><div className="mt-1 text-sm text-slate-600">{item.message}</div><div className="mt-1 text-xs text-slate-400">{new Date(item.createdAt).toLocaleString('vi-VN')}</div>
      </button>)}</div>
    </section>
  );
}
