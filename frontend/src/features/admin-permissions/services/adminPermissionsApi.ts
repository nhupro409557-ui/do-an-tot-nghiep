import { request } from '../../../services/apiClient';

export const adminPermissionsApi = {
  adminListPermissions: () => request<any[]>('/admin/permissions'),
  adminListRoles: () => request<any[]>('/admin/roles'),
  adminGetRolePermissions: (id: string) => request<any>(`/admin/roles/${encodeURIComponent(id)}/permissions`),
  adminUpdateRolePermissions: (id: string, permissionCodes: string[]) => request<any>(`/admin/roles/${encodeURIComponent(id)}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissionCodes }),
  }),
};
