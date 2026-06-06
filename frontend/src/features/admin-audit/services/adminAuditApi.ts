import { request } from '../../../services/apiClient';

export const adminAuditApi = {
  adminListAuditLogs: (params: Record<string, string | number> = {}) => {
    const query = new URLSearchParams(
      Object.entries(params)
        .filter(([, value]) => value !== '')
        .map(([key, value]) => [key, String(value)])
    );
    return request<any[]>(`/admin/audit-logs${query.toString() ? `?${query.toString()}` : ''}`);
  },
};
