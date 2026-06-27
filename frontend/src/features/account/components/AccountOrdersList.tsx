import { Link } from 'react-router-dom';

type AccountOrder = {
  id: string;
  orderCode?: string | null;
  status?: string | null;
  createdAt?: string | null;
  totalAmount?: number | null;
};

type AccountOrdersListProps = {
  orders: AccountOrder[];
  limit?: number;
};

function formatOrderDate(value?: string | null) {
  if (!value) return '';
  return new Date(value).toLocaleDateString('vi-VN');
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
          <div className="flex justify-between mb-2">
            <span className="font-mono font-medium text-gray-700">#{order.orderCode || order.id.slice(0, 8).toUpperCase()}</span>
            <span className="text-green-600 bg-green-50 px-2 py-0.5 rounded text-xs font-semibold">{order.status}</span>
          </div>
          <div className="text-gray-500 text-xs mb-3">Ngày đặt: {formatOrderDate(order.createdAt)}</div>
          <div className="flex justify-between font-bold text-gray-800 border-t border-dashed pt-3">
            <span className="font-normal text-gray-500">Tổng thanh toán:</span>
            <span className="text-red-600">{order.totalAmount?.toLocaleString('vi-VN')}đ</span>
          </div>
          <Link to={`/orders/${order.id}`} className="mt-3 inline-flex w-full items-center justify-center rounded-lg border border-red-200 px-4 py-2 font-bold text-[#d70018] transition-colors hover:bg-red-50">
            Xem chi tiết đơn hàng
          </Link>
        </div>
      ))}
    </div>
  );
}
