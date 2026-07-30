import { Link } from 'react-router-dom';

const statusLabels: Record<string, string> = {
  PENDING: 'Chờ xử lý',
  PROCESSING: 'Đang xử lý',
  SHIPPED: 'Đang giao hàng',
  COMPLETED: 'Hoàn tất',
  CANCELLED: 'Đã hủy',
  PAYMENT_FAILED: 'Thanh toán thất bại',
  RETURNING: 'Đang hoàn hàng',
  RETURNED: 'Đã hoàn hàng',
  REFUNDED: 'Đã hoàn tiền',
};

const statusStyles: Record<string, { bg: string; text: string }> = {
  PENDING: { bg: 'bg-amber-50', text: 'text-amber-700' },
  PROCESSING: { bg: 'bg-blue-50', text: 'text-blue-700' },
  SHIPPED: { bg: 'bg-indigo-50', text: 'text-indigo-700' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
  CANCELLED: { bg: 'bg-rose-50', text: 'text-rose-700' },
  PAYMENT_FAILED: { bg: 'bg-rose-50', text: 'text-rose-700' },
  RETURNING: { bg: 'bg-purple-50', text: 'text-purple-700' },
  RETURNED: { bg: 'bg-slate-50', text: 'text-slate-700' },
  REFUNDED: { bg: 'bg-slate-50', text: 'text-slate-700' },
};

type AccountOrder = {
  id: string;
  orderCode?: string | null;
  status?: string | null;
  createdAt?: string | null;
  totalAmount?: number | string | null;
  orderType?: 'SALE' | 'WARRANTY_REPLACEMENT' | 'RETURN_EXCHANGE' | null;
};

type AccountOrdersListProps = {
  orders: AccountOrder[];
  limit?: number;
};

function formatOrderDate(value?: string | null) {
  if (!value) return '';
  return new Date(value).toLocaleDateString('vi-VN');
}

function formatOrderAmount(value?: number | string | null) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? `${amount.toLocaleString('vi-VN')}đ` : '0đ';
}

export function AccountOrdersList({ orders, limit }: AccountOrdersListProps) {
  const visibleOrders = typeof limit === 'number' ? orders.slice(0, limit) : orders;

  if (visibleOrders.length === 0) {
    return <p className="text-sm text-gray-500 py-4">Bạn chưa có đơn hàng nào.</p>;
  }

  return (
    <div className="space-y-4">
      {visibleOrders.map((order) => (
        <div key={order.id} className="border border-gray-100 rounded-lg p-4 text-sm">
          {order.orderType && order.orderType !== 'SALE' && (
            <div className="mb-2 inline-flex rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">
              {order.orderType === 'WARRANTY_REPLACEMENT' ? 'Đơn giao máy bảo hành' : 'Đơn giao máy đổi trả'}
            </div>
          )}
          <div className="flex justify-between mb-2">
            <span className="font-mono font-medium text-gray-700">#{order.orderCode || order.id.slice(0, 8).toUpperCase()}</span>
            <span className={`${order.status && statusStyles[order.status] ? `${statusStyles[order.status].text} ${statusStyles[order.status].bg}` : 'text-green-600 bg-green-50'} px-2 py-0.5 rounded text-xs font-semibold`}>
              {order.status ? (statusLabels[order.status] || order.status) : ''}
            </span>
          </div>
          <div className="text-gray-500 text-xs mb-3">Ngày đặt: {formatOrderDate(order.createdAt)}</div>
          <div className="flex justify-between font-bold text-gray-800 border-t border-dashed pt-3">
            <span className="font-normal text-gray-500">{order.orderType && order.orderType !== 'SALE' ? 'Khách cần thanh toán:' : 'Tổng thanh toán:'}</span>
            <span className="text-red-600">{order.orderType && order.orderType !== 'SALE' && Number(order.totalAmount || 0) === 0 ? 'Không phát sinh' : formatOrderAmount(order.totalAmount)}</span>
          </div>
          <Link to={`/orders/${order.id}`} className="mt-3 inline-flex w-full items-center justify-center rounded-lg border border-red-200 px-4 py-2 font-bold text-[#d70018] transition-colors hover:bg-red-50">
            {order.orderType && order.orderType !== 'SALE' ? 'Theo dõi giao máy' : 'Xem chi tiết đơn hàng'}
          </Link>
        </div>
      ))}
    </div>
  );
}
