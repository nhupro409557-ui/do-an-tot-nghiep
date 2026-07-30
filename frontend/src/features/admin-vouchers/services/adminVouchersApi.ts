import { request } from '../../../services/apiClient';

export const adminVouchersApi = {
  adminListVouchers: () => request<any[]>('/admin/vouchers'),
  adminCreateVoucher: (data: any) => request<{ id: string }>('/admin/vouchers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateVoucher: (id: string, data: any) => request(`/admin/vouchers/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteVoucher: (id: string) => request(`/admin/vouchers/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  claimVoucher: (voucherId: string, userId: string) => request<any>(`/vouchers/${encodeURIComponent(voucherId)}/claim`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  }),
  listUserVouchers: (userId: string) => request<any[]>(`/users/${encodeURIComponent(userId)}/vouchers`),
  listPublicVouchers: () => request<any[]>('/vouchers'),
  validateVoucher: (code: string, subtotalAmount: number, context: Record<string, unknown> = {}) => request<any>('/vouchers/validate', {
    method: 'POST',
    body: JSON.stringify({ code, subtotal_amount: subtotalAmount, ...context }),
  }),
};
