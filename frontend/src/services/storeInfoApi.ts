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


export const storeInfoApi = {
  getStoreInfo: () => request<StoreInfo>('/store/info'),
  adminUpdateStoreInfo: (data: Omit<StoreInfo, 'id' | 'updated_at'>) => request<{ ok: boolean }>('/admin/store-info', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
};
