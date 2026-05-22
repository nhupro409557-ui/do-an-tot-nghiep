const MOJIBAKE_PATTERN = /(?:Ã|Ä|Æ|á[º»]|Â[^\p{L}]|[\u0080-\u009f])/u;

function decodeUtf8BytesReadAsLatin1(value: string): string {
  const bytes = new Uint8Array(value.length);
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code > 255) return value;
    bytes[index] = code;
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

export function fixVietnameseEncoding(value: string): string {
  if (!MOJIBAKE_PATTERN.test(value)) return value;
  try {
    const decoded = decodeUtf8BytesReadAsLatin1(value);
    return MOJIBAKE_PATTERN.test(decoded) ? value : decoded;
  } catch {
    return value;
  }
}

export function normalizeVietnameseEncoding<T>(value: T): T {
  if (typeof value === 'string') return fixVietnameseEncoding(value) as T;
  if (!value || typeof value !== 'object') return value;
  if (value instanceof File || value instanceof Blob || value instanceof Date) return value;
  if (Array.isArray(value)) return value.map(item => normalizeVietnameseEncoding(item)) as T;

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, normalizeVietnameseEncoding(item)]),
  ) as T;
}
