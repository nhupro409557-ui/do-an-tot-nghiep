import { request } from './apiClient';

export const categoryApi = {
  listCategories: () => request<any[]>('/catalog/categories'),
  adminListCategories: () => request<any[]>('/admin/categories'),
  adminCheckCategorySlug: (data: any) => request<{ available: boolean }>('/admin/categories/check-slug', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCreateCategory: (data: any) => request<{ id: string }>('/admin/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateCategory: (id: string, data: any) => request(`/admin/categories/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminReorderCategories: (items: any[]) => request('/admin/categories/reorder', {
    method: 'PATCH',
    body: JSON.stringify({ items }),
  }),
  adminRestoreCategory: (id: string) => request(`/admin/categories/${encodeURIComponent(id)}/restore`, {
    method: 'PATCH',
  }),
  adminDeleteCategory: (id: string) => request(`/admin/categories/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  }),
  adminCategoryMetrics: () => request<any>('/admin/categories/ops/metrics'),
  adminCategoryAuditLogs: (id: string) => request<any[]>(`/admin/categories/${encodeURIComponent(id)}/audit-logs`),
  adminCategoryMigrationJobs: (id: string) => request<any[]>(`/admin/categories/${encodeURIComponent(id)}/migration-jobs`),
  adminIdentifierPolicyMigrations: (id: string) => request<any[]>(`/admin/categories/${encodeURIComponent(id)}/identifier-policy/migrations`),
  adminCreateIdentifierPolicyMigration: (id: string, data: any) => request<any>(`/admin/categories/${encodeURIComponent(id)}/identifier-policy/migrations`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminScanIdentifierPolicyMigration: (migrationId: string, data: any) => request<any>(`/admin/identifier-policy/migrations/${encodeURIComponent(migrationId)}/scan`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminCompleteIdentifierPolicyMigration: (migrationId: string) => request<any>(`/admin/identifier-policy/migrations/${encodeURIComponent(migrationId)}/complete`, {
    method: 'POST',
  }),
  adminCancelIdentifierPolicyMigration: (migrationId: string, reason: string) => request<any>(`/admin/identifier-policy/migrations/${encodeURIComponent(migrationId)}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
};
