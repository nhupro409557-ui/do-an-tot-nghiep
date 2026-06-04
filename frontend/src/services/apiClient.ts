import { getAccessToken, refreshSession } from './authDb';
import { normalizeVietnameseEncoding } from '../utils/textEncoding';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let token = getAccessToken();
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  if (response.status === 401) {
    try {
      await refreshSession();
      token = getAccessToken();
      const retryHeaders: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' };
      if (token) retryHeaders.Authorization = `Bearer ${token}`;
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: 'include',
        headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
      });
    } catch {
      // Keep the original 401 response for normal error handling below.
    }
  }
  const body = normalizeVietnameseEncoding(await response.json().catch(() => ({})));
  if (!response.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : body.detail ? JSON.stringify(body.detail) : 'Không thể tải dữ liệu từ hệ thống.');
  }
  return body as T;
}

export async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  let token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  if (response.status === 401) {
    await refreshSession().catch(() => undefined);
    token = getAccessToken();
    const retryHeaders: Record<string, string> = {};
    if (token) retryHeaders.Authorization = `Bearer ${token}`;
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
    });
  }
  if (!response.ok) {
    throw new Error('Không thể xuất dữ liệu tồn kho.');
  }
  return response.blob();
}
