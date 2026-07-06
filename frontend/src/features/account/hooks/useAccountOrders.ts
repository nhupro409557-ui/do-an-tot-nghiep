import { useEffect, useState } from 'react';
import { customerCenterApi } from '../services/customerCenterApi';

export function useAccountOrders(userId?: string) {
  const [orders, setOrders] = useState<any[]>([]);

  useEffect(() => {
    if (!userId) return;
    customerCenterApi.listOrders()
      .then(data => setOrders(data.sort((a: any, b: any) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))))
      .catch(e => console.log('Error loading orders', e));
  }, [userId]);

  return { orders };
}
