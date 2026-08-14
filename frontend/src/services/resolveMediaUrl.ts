export function resolveMediaUrl(
  url: string | null | undefined,
  apiBaseUrl: string,
): string {
  if (!url) return '';
  if (url.startsWith('data:') || url.startsWith('/images/')) return url;

  const backendBaseUrl = apiBaseUrl.replace(/\/api\/?$/, '');
  if (url.startsWith('http://localhost:') || url.startsWith('http://127.0.0.1:')) {
    const localUrl = new URL(url);
    return `${backendBaseUrl}${localUrl.pathname}${localUrl.search}${localUrl.hash}`;
  }
  if (url.startsWith('http://') || url.startsWith('https://')) return url;

  return `${backendBaseUrl}/${url.startsWith('/') ? url.slice(1) : url}`;
}
