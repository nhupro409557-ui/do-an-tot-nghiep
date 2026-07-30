import { request, requestBlob } from '../../../services/apiClient';

export const adminInventoryApi = {
  adminListPurchaseOrders: (search = '', status = '') => request<any[]>(`/admin/purchase-orders?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`),
  adminGetPurchaseOrder: (id: string) => request<any>(`/admin/purchase-orders/${encodeURIComponent(id)}`),
  adminCreatePurchaseOrder: (data: any) => request<any>('/admin/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),
  adminUpdatePurchaseOrder: (id: string, data: any) => request<any>(`/admin/purchase-orders/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(data) }),
  adminUpdatePurchaseOrderStatus: (id: string, data: any) => request<any>(`/admin/purchase-orders/${encodeURIComponent(id)}/status`, { method: 'PATCH', body: JSON.stringify(data) }),
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
  adminListLevels: (search = '', stockFilter = '', location = '', categoryId = '', brandId = '', page = 1, pageSize = 50) => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (stockFilter) params.set('stockFilter', stockFilter);
    if (location) params.set('location', location);
    if (categoryId) params.set('categoryId', categoryId);
    if (brandId) params.set('brandId', brandId);
    params.set('page', String(page));
    params.set('pageSize', String(pageSize));
    const query = params.toString();
    return request<any>(`/admin/inventory/levels${query ? `?${query}` : ''}`);
  },
  adminListLocations: (search = '', includeInactive = true, filters: any = {}) => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    params.set('includeInactive', includeInactive ? 'true' : 'false');
    if (filters.zone) params.set('zone', filters.zone);
    if (filters.purpose) params.set('purpose', filters.purpose);
    if (filters.status) params.set('status', filters.status);
    if (filters.aisle) params.set('aisle', filters.aisle);
    if (filters.shelf) params.set('shelf', filters.shelf);
    if (filters.bin) params.set('bin', filters.bin);
    return request<any[]>(`/admin/inventory/locations?${params.toString()}`);
  },
  adminCreateLocation: (data: any) => request<any>('/admin/inventory/locations', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateLocation: (locationId: string, data: any) => request<any>(`/admin/inventory/locations/${encodeURIComponent(locationId)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  adminUpdateLocationStatus: (locationId: string, data: any) => request<any>(`/admin/inventory/locations/${encodeURIComponent(locationId)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminGetInventoryDashboard: (search = '') => request<any>(`/admin/inventory/dashboard${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminGetInventoryAgingReport: (search = '', bucket = '') => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (bucket) params.set('bucket', bucket);
    const query = params.toString();
    return request<any>(`/admin/inventory/reports/aging${query ? `?${query}` : ''}`);
  },
  adminGetInventoryReconciliationReport: (search = '', issueType = '') => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (issueType) params.set('issueType', issueType);
    const query = params.toString();
    return request<any>(`/admin/inventory/reports/reconciliation${query ? `?${query}` : ''}`);
  },
  adminListInventoryLedger: (params: any = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set('search', params.search);
    if (params.productId) query.set('productId', params.productId);
    if (params.dateFrom) query.set('dateFrom', params.dateFrom);
    if (params.dateTo) query.set('dateTo', params.dateTo);
    if (params.transactionType) query.set('transactionType', params.transactionType);
    if (params.reason) query.set('reason', params.reason);
    query.set('page', String(params.page || 1));
    query.set('pageSize', String(params.pageSize || 50));
    const queryString = query.toString();
    return request<any>(`/admin/inventory/ledger${queryString ? `?${queryString}` : ''}`);
  },
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
  adminListTransfers: (search = '') => request<any[]>(`/admin/inventory/transfers${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateTransfer: (data: any) => request<any>('/admin/inventory/transfers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateTransferStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/transfers/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListInternalHolds: (search = '') => request<any[]>(`/admin/inventory/internal-holds${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateInternalHold: (data: any) => request<any>('/admin/inventory/internal-holds', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateInternalHoldStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/internal-holds/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListDisposals: (search = '') => request<any[]>(`/admin/inventory/disposals${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateDisposal: (data: any) => request<any>('/admin/inventory/disposals', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateDisposalStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/disposals/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListCostAdjustments: (search = '') => request<any[]>(`/admin/inventory/cost-adjustments${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  adminCreateCostAdjustment: (data: any) => request<any>('/admin/inventory/cost-adjustments', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateCostAdjustmentStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/cost-adjustments/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListIdentifiers: (productId: string, variantId?: string | null) => request<any>(`/admin/inventory/identifiers?productId=${encodeURIComponent(productId)}${variantId ? `&variantId=${encodeURIComponent(variantId)}` : ''}`),
  adminListIssueSuggestions: (productId: string, variantId?: string | null, quantity = 1) => request<any[]>(`/admin/inventory/issue-suggestions?productId=${encodeURIComponent(productId)}${variantId ? `&variantId=${encodeURIComponent(variantId)}` : ''}&quantity=${encodeURIComponent(String(quantity))}`),
  adminListIdentifierEditRequests: (status = 'PENDING') => request<any[]>(`/admin/inventory/identifier-edit-requests?status=${encodeURIComponent(status)}`),
  adminCreateIdentifierEditRequest: (data: any) => request<any>('/admin/inventory/identifier-edit-requests', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminDecideIdentifierEditRequest: (requestId: string, data: any) => request<any>(`/admin/inventory/identifier-edit-requests/${encodeURIComponent(requestId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListIdentifierLocationRequests: (status = 'PENDING') => request<any[]>(`/admin/inventory/identifier-location-requests?status=${encodeURIComponent(status)}`),
  adminCreateIdentifierLocationRequest: (data: any) => request<any>('/admin/inventory/identifier-location-requests', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminDecideIdentifierLocationRequest: (requestId: string, data: any) => request<any>(`/admin/inventory/identifier-location-requests/${encodeURIComponent(requestId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListReceipts: (search = '', dateFrom = '', dateTo = '', status = '', page = 1, pageSize = 50) => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (dateFrom) params.set('dateFrom', dateFrom);
    if (dateTo) params.set('dateTo', dateTo);
    if (status) params.set('status', status);
    params.set('page', String(page));
    params.set('pageSize', String(pageSize));
    const query = params.toString();
    return request<any>(`/admin/inventory/receipts${query ? `?${query}` : ''}`);
  },
  adminGetReceiptReport: () => request<any>('/admin/inventory/receipts/report'),
  adminExportReceiptDocument: (referenceCode: string, format: 'pdf' | 'docx') => requestBlob(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/export?format=${encodeURIComponent(format)}`),
  adminUpdateReceiptStatus: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminUpdateReceiptQuality: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/quality`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminUpdateReceiptAttachments: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/attachments`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDecideReceiptAttachments: (referenceCode: string, data: any) => request<any>(`/admin/inventory/receipts/${encodeURIComponent(referenceCode)}/attachments/decision`, {
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
  adminGetOutbounds: (search = '', status = '', dateFrom = '', dateTo = '') => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (status) params.set('status', status);
    if (dateFrom) params.set('dateFrom', dateFrom);
    if (dateTo) params.set('dateTo', dateTo);
    const query = params.toString();
    return request<any[]>(`/admin/inventory/outbounds${query ? `?${query}` : ''}`);
  },
  adminGetOutboundDetail: (documentNo: string) => request<any>(`/admin/inventory/outbounds/${encodeURIComponent(documentNo)}`),
  adminResolveOutboundIdentifierPair: (params: {
    productId: string;
    variantId?: string | null;
    locationId: string;
    identifierType: 'IMEI' | 'SERIAL';
    identifierValue: string;
  }) => {
    const query = new URLSearchParams();
    query.set('productId', params.productId);
    if (params.variantId) query.set('variantId', params.variantId);
    query.set('locationId', params.locationId);
    query.set('identifierType', params.identifierType);
    query.set('identifierValue', params.identifierValue);
    return request<any>(`/admin/inventory/outbound-identifier-pair?${query.toString()}`);
  },
  adminUpdateOutbound: (documentNo: string, lines: any[]) => request<any>(`/admin/inventory/outbounds/${encodeURIComponent(documentNo)}`, {
    method: 'PUT',
    body: JSON.stringify(lines),
  }),
  adminAllocateLegacyInventory: (data: any) => request<any>('/admin/inventory/reconciliation/legacy-putaway', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateOutboundStatus: (documentNo: string, status: string, cancelReason?: string) => request<any>(`/admin/inventory/outbounds/${encodeURIComponent(documentNo)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, cancelReason }),
  }),
  adminAutoSuggestOutbound: (documentNo: string) => request<any>(`/admin/inventory/outbounds/${encodeURIComponent(documentNo)}/auto-suggest`, {
    method: 'POST',
  }),
};
