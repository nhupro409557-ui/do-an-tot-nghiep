import { request, requestBlob } from '../../../services/apiClient';

export const adminInventoryApi = {
  adminGetProductInventory: (id: string) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory`),
  adminAdjustInventory: (id: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory/adjust`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateReceipt: (data: any) => request<any>('/admin/inventory/receipts', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateReceipt: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  adminDeleteReceipt: (referenceCode: string) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}`, {
    method: 'DELETE',
  }),
  adminListLevels: (search = '') => request<any[]>(`/admin/inventory/levels${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminListStockCounts: (search = '') => request<any[]>(`/admin/inventory/stock-counts${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateStockCount: (data: any) => request<any>('/admin/inventory/stock-counts', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateStockCountStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/stock-counts/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListAdjustments: (search = '') => request<any[]>(`/admin/inventory/adjustments${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateAdjustment: (data: any) => request<any>('/admin/inventory/adjustments', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateAdjustmentStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/adjustments/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListIdentifiers: (productId: string, variantId?: string | null) => request<any>(`/admin/inventory/identifiers?productId=${encodeURIComponent(productId)}${variantId ? `&variantId=${encodeURIComponent(variantId)}` : ''}`),
  adminListIdentifierEditRequests: (status = 'PENDING') => request<any[]>(`/admin/inventory/identifier-edit-requests?status=${encodeURIComponent(status)}`),
  adminCreateIdentifierEditRequest: (data: any) => request<any>('/admin/inventory/identifier-edit-requests', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminDecideIdentifierEditRequest: (requestId: string, data: any) => request<any>(`/admin/inventory/identifier-edit-requests/${encodeURIComponent(requestId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListReceipts: (search = '') => request<any[]>(`/admin/inventory/receipts${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminExportReceiptDocument: (referenceCode: string, format: 'pdf' | 'docx') => requestBlob(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/export?format=${encodeURIComponent(format)}`),
  adminUpdateReceiptStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminSubmitReceiptImeis: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/imeis`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminReverseReceipt: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/reverse`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateInventorySettings: (id: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory/settings`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminExportInventory: (search = '') => requestBlob(`/admin/inventory/export${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminSetVariantInventory: (productId: string, variantId: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}/inventory`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
};
