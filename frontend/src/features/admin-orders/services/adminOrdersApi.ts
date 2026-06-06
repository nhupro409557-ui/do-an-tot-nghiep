import { request } from '../../../services/apiClient';

export const adminOrdersApi = {
  listOrders: (userId?: string) => request<any[]>(`/orders${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`),
  getOrderDetail: (id: string) => request<any>(`/orders/${encodeURIComponent(id)}`),
  quoteShipping: (data: any) => request<any>('/orders/shipping-quote', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  createOrder: (data: any) => request<any>('/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateOrderStatus: (id: string, status: string) => request(`/orders/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  adminUpdateOrder: (id: string, data: any) => request(`/orders/${encodeURIComponent(id)}/admin`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
};
