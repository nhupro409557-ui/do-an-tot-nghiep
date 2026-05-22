import { normalizeVietnameseEncoding } from '../utils/textEncoding';

export interface MockUser {
  uid: string;
  email: string;
  displayName: string | null;
  emailVerified: boolean;
  isAnonymous: boolean;
  tenantId: string | null;
  providerData: { providerId: string; email: string | null }[];
}

export type PendingRegistration = {
  token: string;
  email: string;
  displayName: string;
  expiresAt: number;
};

export type PendingPasswordReset = {
  token: string;
  email: string;
  expiresAt: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

let currentUser: MockUser | null = readJson('auth_user', null);
let currentProfile: any | null = readJson('auth_user_profile', null);
let authToken: string | null = null;
const listeners: ((user: MockUser | null) => void)[] = [];
let authBootstrapPromise: Promise<void> | null = null;

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? normalizeVietnameseEncoding(JSON.parse(raw)) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });
  const body = normalizeVietnameseEncoding(await response.json().catch(() => ({})));
  if (!response.ok) {
    const err: any = new Error(body.detail || 'Co loi xay ra. Vui long thu lai.');
    err.code = response.status === 401 ? 'auth/invalid-credential' : `http/${response.status}`;
    throw err;
  }
  return body as T;
}

function notify() {
  listeners.forEach(listener => listener(currentUser));
}

function persistAuth(payload: { token: string; user: MockUser; profile: any }) {
  authToken = payload.token;
  currentUser = payload.user;
  currentProfile = payload.profile;
  writeJson('auth_user', payload.user);
  writeJson('auth_user_profile', payload.profile);
  notify();
}

export function getAccessToken() {
  return authToken;
}

export async function refreshSession() {
  persistAuth(await apiRequest('/auth/refresh', { method: 'POST' }));
  return currentUser;
}

function clearLocalAuthState(notifyListeners = true) {
  authToken = null;
  currentUser = null;
  currentProfile = null;
  localStorage.removeItem('auth_user');
  localStorage.removeItem('auth_user_profile');
  localStorage.removeItem('last_pending_registration');
  localStorage.removeItem('last_pending_password_reset');
  if (notifyListeners) notify();
}

// Bootstrap auth once so route guards can wait for silent refresh to finish.
export async function initializeAuth() {
  if (!authBootstrapPromise) {
    authBootstrapPromise = (async () => {
      if (!currentUser && !currentProfile) return;
      try {
        await refreshSession();
      } catch {
        clearLocalAuthState();
      }
    })().finally(() => {
      authBootstrapPromise = null;
    });
  }
  await authBootstrapPromise;
}

export function onAuthStateChanged(callback: (user: MockUser | null) => void) {
  listeners.push(callback);
  callback(currentUser);
  return () => {
    const index = listeners.indexOf(callback);
    if (index >= 0) listeners.splice(index, 1);
  };
}

export function getCurrentUser() {
  return currentUser;
}

export async function signInWithEmailAndPassword(email: string, password: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password }),
  }));
  return currentUser!;
}

export async function adminSignInWithEmailAndPassword(email: string, password: string): Promise<any> {
  const payload = await apiRequest<any>('/auth/admin/login', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password }),
  });
  if (payload.requiresMfa || payload.requiresMfaSetup) return payload;
  persistAuth(payload);
  return currentUser!;
}

export async function verifyAdminMfa(tempToken: string, code: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/admin/verify-mfa', {
    method: 'POST',
    headers: { Authorization: `Bearer ${tempToken}` },
    body: JSON.stringify({ code }),
  }));
  return currentUser!;
}

export async function createUserWithEmailAndPassword(email: string, password: string, displayName: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password, displayName }),
  }));
  return currentUser!;
}

export async function startRegistration(email: string, password: string, displayName: string): Promise<PendingRegistration> {
  const payload = await apiRequest<{ email: string; verificationToken: string }>('/auth/register/start', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password, displayName: displayName.trim() || email.trim() }),
  });
  return {
    token: payload.verificationToken,
    email: payload.email,
    displayName: displayName.trim() || email.trim().toLowerCase(),
    expiresAt: Date.now() + 15 * 60 * 1000,
  };
}

export async function resendRegistrationCode(email: string): Promise<PendingRegistration> {
  const payload = await apiRequest<{ email: string; verificationToken: string }>('/auth/register/resend', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
  return {
    token: payload.verificationToken,
    email: payload.email,
    displayName: payload.email,
    expiresAt: Date.now() + 15 * 60 * 1000,
  };
}

export async function confirmRegistrationByCode(email: string, code: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/register/verify', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), code: code.trim() }),
  }));
  return currentUser!;
}

export async function confirmRegistrationByToken(token: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/register/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  }));
  return currentUser!;
}

export async function signInWithGoogleProfile(profile: { email: string; name: string; picture?: string }): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/google', {
    method: 'POST',
    body: JSON.stringify(profile),
  }));
  return currentUser!;
}

export async function signOut() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' });
  } catch {
    // Local cleanup still matters if the backend session has already expired.
  }
  clearLocalAuthState();
}

export async function deleteCurrentUser() {
  await apiRequest('/users/me', {
    method: 'DELETE',
    body: JSON.stringify({ confirmation: 'DELETE_ACCOUNT' }),
  });
  await signOut();
}

export async function sendPasswordResetEmail(email: string) {
  return apiRequest<{ email: string; verificationToken: string }>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
}

export async function resendPasswordResetEmail(email: string) {
  return apiRequest<{ email: string; verificationToken: string }>('/auth/forgot-password/resend', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
}

export function createPendingPasswordReset(email: string, verificationToken: string): PendingPasswordReset {
  return {
    token: verificationToken,
    email: email.trim().toLowerCase(),
    expiresAt: Date.now() + 15 * 60 * 1000,
  };
}

export function rememberPendingPasswordReset(reset: PendingPasswordReset) {
  void reset;
}

export async function confirmPasswordResetByCode(email: string, code: string) {
  const payload = await apiRequest<{ resetToken: string }>('/auth/forgot-password/verify', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), code: code.trim() }),
  });
  return payload.resetToken;
}

export async function confirmPasswordResetByVerificationToken(token: string) {
  const payload = await apiRequest<{ resetToken: string }>('/auth/forgot-password/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
  return payload.resetToken;
}

export async function resetPasswordWithToken(token: string, newPassword: string) {
  await apiRequest('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, newPassword }),
  });
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await apiRequest('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ currentPassword, newPassword }),
  });
}

export function getUserProfile(uid: string): any | null {
  return currentUser?.uid === uid ? currentProfile : null;
}

export function updateUserProfile(uid: string, updates: any) {
  if (currentUser?.uid !== uid) return;
  currentProfile = { ...(currentProfile || {}), ...updates, updatedAt: new Date().toISOString() };
  writeJson('auth_user_profile', currentProfile);
  notify();
  apiRequest<any>('/auth/me/profile', {
    method: 'PATCH',
    body: JSON.stringify({ data: updates }),
  })
    .then(profile => {
      currentProfile = profile;
      writeJson('auth_user_profile', profile);
      notify();
    })
    .catch(console.error);
}

export function ensureUserProfile(user: MockUser) {
  return getUserProfile(user.uid);
}

export function rememberPendingRegistration(registration: PendingRegistration) {
  void registration;
}

export function getAuthErrorMessage(code?: string, fallback = 'Co loi xay ra. Vui long thu lai.') {
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'Email hoac mat khau khong dung.';
    case 'http/409':
    case 'auth/email-already-in-use':
      return 'Email nay da duoc dang ky.';
    case 'auth/weak-password':
      return 'Mat khau can co it nhat 6 ky tu.';
    case 'http/400':
      return fallback;
    case 'auth/requires-recent-login':
      return 'Vui long dang nhap lai truoc khi thuc hien thao tac nay.';
    case 'auth/too-many-requests':
      return 'Ban thao tac qua nhieu lan. Vui long thu lai sau.';
    case 'auth/invalid-reset-token':
      return 'Lien ket dat lai mat khau da het han.';
    case 'auth/invalid-reset-code':
      return 'Ma xac nhan khong hop le hoac da het han.';
    default:
      return fallback;
  }
}
