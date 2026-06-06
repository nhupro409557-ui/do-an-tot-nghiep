import { request, requestBlob } from '../../../services/apiClient';

export const adminInventoryApi = {
  adminGetProductInventory: (id: string) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory`),
  adminAdjustInventory: (id: string, data: any) => request<any>(`/admin/products/${encodeURIComponent(id)}/inventory/adjust`, {
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
