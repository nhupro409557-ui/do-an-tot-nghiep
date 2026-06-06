import { normalizeVietnameseEncoding } from '../utils/textEncoding';

const AUTH_STORAGE_KEYS = [
  'auth_user',
  'auth_user_profile',
  'last_pending_registration',
  'last_pending_password_reset',
];

export function readAuthJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? normalizeVietnameseEncoding(JSON.parse(raw)) : fallback;
  } catch {
    return fallback;
  }
}

export function writeAuthJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function clearStoredAuth() {
  AUTH_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
}
