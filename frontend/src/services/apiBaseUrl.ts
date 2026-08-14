const LOCAL_API_BASE_URL = 'http://localhost:8000/api';

export function resolveApiBaseUrl(
  configuredUrl: string | undefined,
  hostname: string,
): string {
  if (hostname.endsWith('.vercel.app')) return '/api';
  return configuredUrl || LOCAL_API_BASE_URL;
}

export const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env?.VITE_API_BASE_URL,
  typeof window === 'undefined' ? '' : window.location.hostname,
);
