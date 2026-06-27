import { request } from '../../../services/apiClient';

export const adminAfterSalesApi = {
  listReturns: () => request<any>('/admin/after-sales/returns?limit=100'),
  listWarranties: () => request<any>('/admin/after-sales/warranties?limit=100'),
  updateReturn: (id: string, data: any) => request<any>(`/admin/after-sales/returns/${encodeURIComponent(id)}/status`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  updateWarranty: (id: string, data: any) => request<any>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/status`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  listDefectiveIdentifiers: () => request<any[]>('/admin/after-sales/defective-identifiers'),
  updateDisposition: (id: string, data: any) => request<any>(`/admin/after-sales/defective-identifiers/${encodeURIComponent(id)}/disposition`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
};
