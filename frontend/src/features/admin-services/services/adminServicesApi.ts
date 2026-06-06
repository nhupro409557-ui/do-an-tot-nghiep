import { request } from '../../../services/apiClient';

export const adminServicesApi = {
  adminListAttachedServices: () => request<any[]>('/admin/attached-services'),
  adminCreateAttachedService: (data: any) => request<{ id: string }>('/admin/attached-services', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateAttachedService: (id: string, data: any) => request(`/admin/attached-services/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteAttachedService: (id: string) => request(`/admin/attached-services/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
