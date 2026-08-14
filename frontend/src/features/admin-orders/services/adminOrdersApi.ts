import { request } from '../../../services/apiClient';

export const adminOrdersApi = {
  listOrders: (userId?: string) => request<any[]>(`/orders${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`),
  getOrderDetail: (id: string) => request<any>(`/orders/${encodeURIComponent(id)}`),
  quoteShipping: (data: any) => request<any>('/orders/shipping-quote', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  quoteCarrierShipment: (id: string, data: any) => request<any>(`/orders/${encodeURIComponent(id)}/carrier/quote`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  createCarrierShipment: (id: string, data: any) => request<any>(`/orders/${encodeURIComponent(id)}/carrier/shipment`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  cancelCarrierShipment: (id: string, data: any) => request<any>(`/orders/${encodeURIComponent(id)}/carrier/cancel`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateCarrierEvent: (id: string, data: any) => request<any>(`/orders/${encodeURIComponent(id)}/carrier/events`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  createOrder: (data: any) => request<any>('/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getPaymentStatus: (id: string) => request<any>(`/payments/${encodeURIComponent(id)}`),
  retryPayment: (id: string) => request<any>(`/payments/${encodeURIComponent(id)}/retry`, {
    method: 'POST',
  }),
  cancelPayment: (id: string) => request<any>(`/payments/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
  }),
  updateOrderStatus: (id: string, status: string, customerReceiptConfirmed = false) => request(`/orders/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, customer_receipt_confirmed: customerReceiptConfirmed }),
  }),
  adminUpdateOrder: (id: string, data: any) => request(`/orders/${encodeURIComponent(id)}/admin`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
};
