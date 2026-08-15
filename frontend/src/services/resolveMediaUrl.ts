export function resolveMediaUrl(
  url: string | null | undefined,
  apiBaseUrl: string,
): string {
  if (!url) return '';
  if (url.startsWith('data:') || url.startsWith('/images/')) return url;

  const backendBaseUrl = apiBaseUrl.replace(/\/api\/?$/, '');
  const managedRootFolders = [
    'after-sales',
    'brands',
    'categories',
    'content',
    'inventory',
    'products',
    'reviews',
    'used-products',
  ];
  const normalizedReference = url.replace(/^\/+/, '');
  if (managedRootFolders.some((folder) => normalizedReference.startsWith(`${folder}/`))) {
    let decodedReference = normalizedReference;
    try {
      decodedReference = decodeURIComponent(normalizedReference);
    } catch {
      return '';
    }
    const segments = decodedReference.replace(/\\/g, '/').split('/');
    if (segments.some((segment) => !segment || segment === '.' || segment === '..')) return '';
    return `${backendBaseUrl}/media/${normalizedReference}`;
  }
  if (url.startsWith('http://localhost:') || url.startsWith('http://127.0.0.1:')) {
    const localUrl = new URL(url);
    return `${backendBaseUrl}${localUrl.pathname}${localUrl.search}${localUrl.hash}`;
  }
  if (url.startsWith('http://') || url.startsWith('https://')) return url;

  return `${backendBaseUrl}/${url.startsWith('/') ? url.slice(1) : url}`;
}
