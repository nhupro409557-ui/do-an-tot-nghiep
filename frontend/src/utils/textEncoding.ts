const MOJIBAKE_PATTERN = /(?:Ã|Ä|Æ|á[º»]|Â[^\p{L}]|[\u0080-\u009f])/u;

const WINDOWS1252_TO_LATIN1: Record<string, number> = {
  '\u20ac': 128, // €
  '\u201a': 130, // ‚
  '\u0192': 131, // ƒ
  '\u201e': 132, // „
  '\u2026': 133, // …
  '\u2020': 134, // †
  '\u2021': 135, // ‡
  '\u02c6': 136, // ˆ
  '\u2030': 137, // ‰
  '\u0160': 138, // Š
  '\u2039': 139, // ‹
  '\u0152': 140, // Œ
  '\u017d': 142, // Ž
  '\u2018': 145, // ‘
  '\u2019': 146, // ’
  '\u201c': 147, // “
  '\u201d': 148, // ”
  '\u2022': 149, // •
  '\u2013': 150, // –
  '\u2014': 151, // —
  '\u02dc': 152, // ˜
  '\u2122': 153, // ™
  '\u0161': 154, // š
  '\u203a': 155, // ›
  '\u0153': 156, // œ
  '\u017e': 158, // ž
  '\u0178': 159, // Ÿ
};

function decodeUtf8BytesReadAsLatin1(value: string): string {
  const bytes = new Uint8Array(value.length);
  for (let index = 0; index < value.length; index += 1) {
    const char = value.charAt(index);
    let code = value.charCodeAt(index);
    if (code > 255) {
      if (char in WINDOWS1252_TO_LATIN1) {
        code = WINDOWS1252_TO_LATIN1[char];
      } else {
        return value;
      }
    }
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
