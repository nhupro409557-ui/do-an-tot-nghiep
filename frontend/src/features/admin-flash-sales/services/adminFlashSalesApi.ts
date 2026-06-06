import { request } from '../../../services/apiClient';

export const adminFlashSalesApi = {
  adminListFlashSales: () => request<any[]>('/admin/flash-sales'),
  adminCreateFlashSale: (data: any) => request<{ id: string }>('/admin/flash-sales', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateFlashSale: (id: string, data: any) => request(`/admin/flash-sales/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteFlashSale: (id: string) => request(`/admin/flash-sales/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
