import { request } from '../../../services/apiClient';

export const adminCustomersApi = {
  adminListCustomers: (params: { search?: string; page?: number; limit?: number; role?: 'CUSTOMER' | 'STAFF_ADMIN' } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.set('search', params.search);
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(params.limit));
    if (params.role) searchParams.set('role', params.role);
    const query = searchParams.toString();
    return request<{ items: any[]; page: number; limit: number; total: number }>(`/admin/customers${query ? `?${query}` : ''}`);
  },
  adminGetCustomerDetail: (id: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}`),
  adminGetCustomerOverview: (id: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}/overview`),
  adminGetCustomerOrders: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/orders`),
  adminGetCustomerLoyaltyHistory: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/loyalty-history`),
  adminGetCustomerNotes: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/notes`),
  adminGetCustomerAuditLogs: (id: string) => request<any[]>(`/admin/customers/${encodeURIComponent(id)}/audit-logs`),
  adminUpdateCustomerTags: (id: string, tags: string[]) => request<any>(`/admin/customers/${encodeURIComponent(id)}/tags`, {
    method: 'PUT',
    body: JSON.stringify({ tags }),
  }),
  adminBulkUpdateCustomerTags: (userIds: string[], tags: string[]) => request<any>('/admin/customers/tags/bulk', {
    method: 'PUT',
    body: JSON.stringify({ userIds, tags }),
  }),
  adminCreateCustomerNote: (id: string, content: string) => request<any>(`/admin/customers/${encodeURIComponent(id)}/notes`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  }),
  adminAdjustCustomerLoyalty: (id: string, data: { delta: number; reason: string }) => request<any>(`/admin/customers/${encodeURIComponent(id)}/loyalty-adjustments`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminIssueCustomerVoucher: (id: string, data: { voucherId: string; note?: string }) => request<any>(`/admin/customers/${encodeURIComponent(id)}/vouchers`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminBulkUpdateUserStatus: (userIds: string[], status: string) => request<any>('/admin/users/status/bulk', {
    method: 'PATCH',
    body: JSON.stringify({ userIds, status }),
  }),
  adminCreateStaff: (data: any) => request<any>('/admin/staff', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateUserRole: (id: string, data: any) => request(`/admin/users/${encodeURIComponent(id)}/role`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminGetUserPermissions: (id: string) => request<any>(`/admin/users/${encodeURIComponent(id)}/permissions`),
  adminUpdateUserPermissions: (id: string, permissionCodes: string[]) => request<any>(`/admin/users/${encodeURIComponent(id)}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissionCodes }),
  }),
};
