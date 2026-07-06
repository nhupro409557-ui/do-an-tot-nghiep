import { request } from '../../../services/apiClient';
import type {
  SourceProduct,
  UsedProductDevice,
  UsedProductHistory,
  UsedProductInspectionPayload,
  UsedProductIntake,
  UsedProductIntakeListResponse,
  UsedProductIntakePayload,
  UsedProductListing,
  UsedProductListingPayload,
  UsedProductStatusPayload,
} from '../types';

export const adminUsedProductsApi = {
  listIntakes: (status = '', search = '') => request<UsedProductIntakeListResponse>(
    `/admin/used-products/intakes?limit=200&status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`,
  ),
  createIntake: (data: UsedProductIntakePayload) => request<UsedProductIntake>('/admin/used-products/intakes', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateIntakeStatus: (id: string, data: UsedProductStatusPayload) => request<UsedProductIntake>(
    `/admin/used-products/intakes/${encodeURIComponent(id)}/status`,
    { method: 'PATCH', body: JSON.stringify(data) },
  ),
  inspectIntake: (id: string, data: UsedProductInspectionPayload) => request<UsedProductDevice>(
    `/admin/used-products/intakes/${encodeURIComponent(id)}/inspections`,
    { method: 'POST', body: JSON.stringify(data) },
  ),
  listDevices: (status = '', search = '') => request<UsedProductDevice[]>(
    `/admin/used-products/devices?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`,
  ),
  saveListing: (deviceId: string, data: UsedProductListingPayload) => request<UsedProductListing>(
    `/admin/used-products/devices/${encodeURIComponent(deviceId)}/listing`,
    { method: 'PUT', body: JSON.stringify(data) },
  ),
  updateDeviceStatus: (deviceId: string, data: UsedProductStatusPayload) => request<UsedProductDevice>(
    `/admin/used-products/devices/${encodeURIComponent(deviceId)}/status`,
    { method: 'PATCH', body: JSON.stringify(data) },
  ),
  getDeviceHistory: (deviceId: string) => request<UsedProductHistory>(
    `/admin/used-products/devices/${encodeURIComponent(deviceId)}/history`,
  ),
  reinspectDevice: (deviceId: string, data: UsedProductInspectionPayload) => request<UsedProductDevice>(
    `/admin/used-products/devices/${encodeURIComponent(deviceId)}/reinspection`,
    { method: 'POST', body: JSON.stringify(data) },
  ),
  listListings: (status = '', search = '') => request<UsedProductListing[]>(
    `/admin/used-products/listings?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`,
  ),
  updateListingStatus: (listingId: string, data: UsedProductStatusPayload) => request<UsedProductListing>(
    `/admin/used-products/listings/${encodeURIComponent(listingId)}/status`,
    { method: 'PATCH', body: JSON.stringify(data) },
  ),
  listSourceProducts: () => request<SourceProduct[]>('/admin/used-products/source-products'),
};
