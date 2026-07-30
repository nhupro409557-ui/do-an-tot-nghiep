import { request } from '../../../services/apiClient';

export const adminAfterSalesApi = {
  listReturns: () => request<any>('/admin/after-sales/returns?limit=100'),
  listWarranties: () => request<any>('/admin/after-sales/warranties?limit=100'),
  updateReturn: (id: string, data: any) => request<any>(`/admin/after-sales/returns/${encodeURIComponent(id)}/status`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  listReturnEvents: (id: string) => request<any[]>(`/admin/after-sales/returns/${encodeURIComponent(id)}/events`),
  addReturnEvent: (id: string, data: any) => request<any>(`/admin/after-sales/returns/${encodeURIComponent(id)}/events`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  updateWarranty: (id: string, data: any) => request<any>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/status`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  listWarrantyEvents: (id: string) => request<any[]>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/events`),
  addWarrantyEvent: (id: string, data: any) => request<any>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/events`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  listDefectiveIdentifiers: () => request<any[]>('/admin/after-sales/defective-identifiers'),
  getDefectiveDispositionReport: () => request<any>('/admin/after-sales/reports/defective-disposition'),
  listDispositionEvents: (id: string) => request<any[]>(`/admin/after-sales/defective-identifiers/${encodeURIComponent(id)}/disposition-events`),
  updateDisposition: (id: string, data: any) => request<any>(`/admin/after-sales/defective-identifiers/${encodeURIComponent(id)}/disposition`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  inspectReturn: (id: string, data: any) => request<any>(`/admin/after-sales/returns/${encodeURIComponent(id)}/inspection`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  inspectWarranty: (id: string, data: any) => request<any>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/inspection`, {
    method: 'POST', body: JSON.stringify(data),
  }),
  listWarrantyReplacementCandidates: (id: string) => request<any>(`/admin/after-sales/warranties/${encodeURIComponent(id)}/replacement-candidates`),
};
