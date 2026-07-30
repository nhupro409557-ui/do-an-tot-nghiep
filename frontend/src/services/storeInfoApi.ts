import { request } from './apiClient';

export interface StoreInfo {
  id: string;
  name: string;
  hotline: string;
  email: string;
  address: string;
  description: string;
  lat?: number;
  lng?: number;
  updated_at?: string;
}

export interface StorePolicy {
  id: string;
  code: string;
  title: string;
  content: string;
  is_active: boolean;
  version: number;
  updated_at?: string;
}

export type PublicStorePolicy = Pick<StorePolicy, 'code' | 'title' | 'content' | 'version' | 'updated_at'>;


export const storeInfoApi = {
  getStoreInfo: () => request<StoreInfo>('/store/info'),
  listPublicStorePolicies: () => request<PublicStorePolicy[]>('/store/policies'),
  adminUpdateStoreInfo: (data: Omit<StoreInfo, 'id' | 'updated_at'>) => request<{ ok: boolean }>('/admin/store-info', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListStorePolicies: () => request<StorePolicy[]>('/admin/store-info/policies'),
  adminUpdateStorePolicy: (code: string, data: Pick<StorePolicy, 'title' | 'content' | 'is_active'>) =>
    request<StorePolicy>(`/admin/store-info/policies/${encodeURIComponent(code)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};
