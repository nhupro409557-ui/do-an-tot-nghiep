import { normalizeVietnameseEncoding } from '../utils/textEncoding';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export async function authRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  const body = normalizeVietnameseEncoding(await response.json().catch(() => ({})));
  if (!response.ok) {
    const err: any = new Error(body.detail || 'Có lỗi xảy ra. Vui lòng thử lại.');
    err.code = response.status === 401 ? 'auth/invalid-credential' : `http/${response.status}`;
    throw err;
  }
  return body as T;
}
