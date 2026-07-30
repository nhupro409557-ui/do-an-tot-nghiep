import { request } from '../../../services/apiClient';

function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value));
  });
  return search.toString() ? `?${search.toString()}` : '';
}

export const customerCenterApi = {
  listOrders: () => request<any[]>('/me/orders'),
  cancelOrder: (id: string, reason: string) => request(`/orders/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  listPurchasedAfterSalesItems: () => request<any[]>('/me/after-sales/purchased-items'),
  listReturns: (params: any = {}) => request<any>(`/me/returns${query(params)}`),
  createReturn: (data: any) => request<any>('/me/returns', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  cancelReturn: (id: string) => request(`/me/returns/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  uploadReturnFiles: (id: string, files: File[]) => {
    const body = new FormData();
    files.forEach(file => body.append('files', file));
    return request<any[]>(`/me/returns/${encodeURIComponent(id)}/attachments`, { method: 'POST', body });
  },
  listWarranties: (params: any = {}) => request<any>(`/me/warranties${query(params)}`),
  createWarranty: (data: any) => request<any>('/me/warranties', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  cancelWarranty: (id: string) => request(`/me/warranties/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  uploadWarrantyFiles: (id: string, files: File[]) => {
    const body = new FormData();
    files.forEach(file => body.append('files', file));
    return request<any[]>(`/me/warranties/${encodeURIComponent(id)}/attachments`, { method: 'POST', body });
  },
  listVouchers: () => request<any[]>('/me/vouchers'),
  listTransactions: (page = 1) => request<any>(`/me/transactions?page=${page}&limit=20`),
  listNotifications: (page = 1) => request<any>(`/me/notifications?page=${page}&limit=30`),
  markNotificationRead: (id: string) => request(`/me/notifications/${encodeURIComponent(id)}/read`, { method: 'PATCH' }),
  markAllNotificationsRead: () => request('/me/notifications/read-all', { method: 'PATCH' }),
  shipmentTimeline: (orderId: string) => request<any[]>(`/me/orders/${encodeURIComponent(orderId)}/shipment`),
};
