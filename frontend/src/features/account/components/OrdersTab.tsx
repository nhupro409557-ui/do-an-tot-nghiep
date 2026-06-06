import { AccountOrdersList } from './AccountOrdersList';

type OrdersTabProps = {
  orders: any[];
};

export function OrdersTab({ orders }: OrdersTabProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="font-bold text-gray-800 mb-4">Lịch sử mua hàng</h3>
      <AccountOrdersList orders={orders} />
    </section>
  );
}
