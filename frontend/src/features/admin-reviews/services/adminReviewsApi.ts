import { request } from '../../../services/apiClient';

export const adminReviewsApi = {
  adminListReviews: () => request<any[]>('/admin/reviews'),
  adminListReviewSummary: () => request<any[]>('/admin/reviews/summary'),
  adminUpdateReview: (id: string, data: any) => request(`/admin/reviews/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteReview: (id: string) => request(`/admin/reviews/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
