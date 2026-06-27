import { request } from '../../../services/apiClient';

export type PaymentMethodData = {
  id: string;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  is_available?: boolean;
  maintenance_message: string | null;
  maintenance_starts_at: string | null;
  maintenance_ends_at: string | null;
  created_at?: string;
  updated_at?: string;
};

export const adminPaymentMethodsApi = {
  adminListPaymentMethods: () => request<PaymentMethodData[]>('/admin/payment-methods'),
  adminUpdatePaymentMethod: (id: string, data: Partial<PaymentMethodData>) =>
    request<{ ok: boolean }>(`/admin/payment-methods/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  listStorefrontPaymentMethods: () => request<PaymentMethodData[]>('/payment-methods'),
};
