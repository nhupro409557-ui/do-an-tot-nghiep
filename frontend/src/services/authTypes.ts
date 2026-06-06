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
