import { useEffect, useState } from 'react';
import { adminOrdersApi } from '../../admin-orders/services/adminOrdersApi';

export function useAccountOrders(userId?: string) {
  const [orders, setOrders] = useState<any[]>([]);

  useEffect(() => {
    if (!userId) return;
    adminOrdersApi.listOrders(userId)
      .then(data => setOrders(data.sort((a: any, b: any) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))))
      .catch(e => console.log('Error loading orders', e));
  }, [userId]);

  return { orders };
}
