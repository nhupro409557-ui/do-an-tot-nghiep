import { useEffect, useState } from 'react';
import { customerCenterApi } from '../services/customerCenterApi';

export function useAccountOrders(userId?: string, refreshKey?: string) {
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    customerCenterApi.listOrders()
      .then(data => setOrders(data.sort((a: any, b: any) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))))
      .catch(e => console.log('Không thể tải đơn hàng', e))
      .finally(() => setLoading(false));
  }, [userId, refreshKey]);

  return { orders, loading };
}
