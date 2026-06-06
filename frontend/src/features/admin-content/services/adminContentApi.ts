import { request } from '../../../services/apiClient';

export const adminContentApi = {
  listBanners: () => request<any[]>('/banners'),
  adminListImageComments: () => request<any[]>('/admin/image-comments'),
  adminReplyImageComment: (commentId: string, body: string) => request<any>(`/admin/image-comments/${encodeURIComponent(commentId)}/reply`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  }),
  adminUpdateImageComment: (commentId: string, data: any) => request<any>(`/admin/image-comments/${encodeURIComponent(commentId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListContent: () => request<any[]>('/admin/content'),
  adminCreateContent: (data: any) => request<{ id: string }>('/admin/content', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateContent: (id: string, data: any) => request(`/admin/content/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteContent: (id: string) => request(`/admin/content/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminListVideos: () => request<any[]>('/admin/videos'),
  adminCreateVideo: (data: any) => request<{ id: string }>('/admin/videos', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateVideo: (id: string, data: any) => request(`/admin/videos/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteVideo: (id: string) => request(`/admin/videos/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  adminReplyVideoComment: (videoId: string, commentId: string, body: string) => request<any>(`/admin/videos/${encodeURIComponent(videoId)}/comments/${encodeURIComponent(commentId)}/reply`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  }),
  adminUpdateVideoComment: (videoId: string, commentId: string, data: any) => request<any>(`/admin/videos/${encodeURIComponent(videoId)}/comments/${encodeURIComponent(commentId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminListBanners: () => request<any[]>('/admin/banners'),
  adminCreateBanner: (data: any) => request<{ id: string }>('/admin/banners', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  adminUpdateBanner: (id: string, data: any) => request(`/admin/banners/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  adminDeleteBanner: (id: string) => request(`/admin/banners/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
