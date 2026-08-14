import { authRequest } from './authRequest';
import { clearStoredAuth, readAuthJson, writeAuthJson } from './authStorage';
import type { MockUser, PendingPasswordReset, PendingRegistration } from './authTypes';
export type { MockUser, PendingPasswordReset, PendingRegistration } from './authTypes';
export { getAuthErrorMessage } from './authErrors';

export type AdminMfaChallenge = {
  requiresMfa?: boolean;
  requiresMfaSetup?: boolean;
  tempToken: string;
  mfaSecret?: string;
  otpauthUrl?: string;
};

let currentUser: MockUser | null = readAuthJson('auth_user', null);
let currentProfile: any | null = readAuthJson('auth_user_profile', null);
let authToken: string | null = null;
const listeners: ((user: MockUser | null) => void)[] = [];
let authBootstrapPromise: Promise<void> | null = null;
let refreshPromise: Promise<MockUser | null> | null = null;

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  return authRequest<T>(path, options, authToken);
}

function notify() {
  listeners.forEach(listener => listener(currentUser));
}

function persistAuth(payload: { token: string; user: MockUser; profile: any }) {
  authToken = payload.token;
  currentUser = payload.user;
  currentProfile = payload.profile;
  writeAuthJson('auth_user', payload.user);
  writeAuthJson('auth_user_profile', payload.profile);
  notify();
}

export function getAccessToken() {
  return authToken;
}

export async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      persistAuth(await apiRequest('/auth/refresh', { method: 'POST' }));
      return currentUser;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export function isAccessTokenExpiringSoon(thresholdSeconds = 30) {
  if (!authToken) return false;
  try {
    const payloadPart = authToken.split('.')[1];
    if (!payloadPart) return true;
    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
    const payload = JSON.parse(atob(padded));
    return typeof payload.exp !== 'number' || payload.exp * 1000 <= Date.now() + thresholdSeconds * 1000;
  } catch {
    return true;
  }
}

function clearLocalAuthState(notifyListeners = true) {
  authToken = null;
  currentUser = null;
  currentProfile = null;
  clearStoredAuth();
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

export async function adminSignInWithEmailAndPassword(email: string, password: string): Promise<MockUser | AdminMfaChallenge> {
  const payload = await apiRequest<AdminMfaChallenge | { token: string; user: MockUser; profile: any }>('/auth/admin/login', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password }),
  });
  if ('tempToken' in payload) return payload;
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

export async function startAdminMfaRecovery(tempToken: string) {
  return apiRequest<{ ok: boolean; email: string; recoveryToken: string }>('/auth/admin/mfa-recovery/start', {
    method: 'POST',
    headers: { Authorization: `Bearer ${tempToken}` },
  });
}

export async function verifyAdminMfaRecovery(tempToken: string, code: string) {
  return apiRequest<AdminMfaChallenge>('/auth/admin/mfa-recovery/verify', {
    method: 'POST',
    headers: { Authorization: `Bearer ${tempToken}` },
    body: JSON.stringify({ code: code.trim() }),
  });
}

export async function createUserWithEmailAndPassword(email: string, password: string, displayName: string): Promise<MockUser> {
  persistAuth(await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password, displayName }),
  }));
  return currentUser!;
}

export async function startRegistration(email: string, password: string, displayName: string): Promise<PendingRegistration> {
  const payload = await apiRequest<{ email: string }>('/auth/register/start', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), password, displayName: displayName.trim() || email.trim() }),
  });
  return {
    email: payload.email,
    displayName: displayName.trim() || email.trim().toLowerCase(),
    expiresAt: Date.now() + 15 * 60 * 1000,
  };
}

export async function getLoyaltyHistory(): Promise<any[]> {
  return apiRequest<any[]>('/loyalty/history');
}

export async function resendRegistrationCode(email: string): Promise<PendingRegistration> {
  const payload = await apiRequest<{ email: string }>('/auth/register/resend', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
  return {
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

export async function signInWithGoogleProfile(profile: { credential?: string; id_token?: string; access_token?: string }): Promise<MockUser> {
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
  return apiRequest<{ email: string; adminContext: boolean }>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
}

export async function resendPasswordResetEmail(email: string) {
  return apiRequest<{ email: string; adminContext: boolean }>('/auth/forgot-password/resend', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  });
}

export function createPendingPasswordReset(email: string): PendingPasswordReset {
  return {
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
  writeAuthJson('auth_user_profile', currentProfile);
  notify();
  apiRequest<any>('/auth/me/profile', {
    method: 'PATCH',
    body: JSON.stringify({ data: updates }),
  })
    .then(profile => {
      currentProfile = profile;
      writeAuthJson('auth_user_profile', profile);
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
