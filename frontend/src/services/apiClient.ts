import { getAccessToken, isAccessTokenExpiringSoon, refreshSession } from './authDb';
import { normalizeVietnameseEncoding } from '../utils/textEncoding';
import { API_BASE_URL } from './apiBaseUrl';

export { API_BASE_URL } from './apiBaseUrl';

const NETWORK_RETRY_DELAY_MS = 250;

function isRetryableRequest(options: RequestInit) {
  const method = String(options.method || 'GET').toUpperCase();
  return method === 'GET' || method === 'HEAD';
}

async function fetchWithNetworkRetry(url: string, options: RequestInit): Promise<Response> {
  try {
    return await fetch(url, options);
  } catch (error) {
    if (!isRetryableRequest(options) || (error instanceof DOMException && error.name === 'AbortError')) {
      throw error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, NETWORK_RETRY_DELAY_MS));
    return fetch(url, options);
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (getAccessToken() && isAccessTokenExpiringSoon()) {
    await refreshSession().catch(() => undefined);
  }
  let token = getAccessToken();
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetchWithNetworkRetry(`${API_BASE_URL}${path}`, {
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
      response = await fetchWithNetworkRetry(`${API_BASE_URL}${path}`, {
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
  if (getAccessToken() && isAccessTokenExpiringSoon()) {
    await refreshSession().catch(() => undefined);
  }
  let token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let response = await fetchWithNetworkRetry(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  if (response.status === 401) {
    await refreshSession().catch(() => undefined);
    token = getAccessToken();
    const retryHeaders: Record<string, string> = {};
    if (token) retryHeaders.Authorization = `Bearer ${token}`;
    response = await fetchWithNetworkRetry(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
    });
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === 'string'
        ? body.detail
        : 'Không thể xuất dữ liệu.',
    );
  }
  return response.blob();
}
