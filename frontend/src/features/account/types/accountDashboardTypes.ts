import type { AddressData } from '../../shipping/components/VietnamAddressSelector';

export type AccountTab = 'overview' | 'orders' | 'returns' | 'warranties' | 'vouchers' | 'transactions' | 'notifications' | 'membership' | 'addresses' | 'settings' | 'favorites' | 'buyback';

export type AccountAddress = {
  id: string;
  receiverName: string;
  receiverPhone: string;
  addressLine: string;
  addressData?: AddressData;
  mapQueryAddress?: string;
  lat?: number;
  lng?: number;
  mapUrl?: string;
  note?: string;
  isDefault: boolean;
  isMapVerified: boolean;
};

export type ProfileForm = {
  displayName: string;
  birthDate: string;
  birthDateLocked: boolean;
  gender: string;
  phone: string;
  avatarUrl: string;
  verificationRole: string;
  schoolOrWorkplace: string;
  verificationCode: string;
};

export type AuthSession = {
  id: string;
  current: boolean;
  userAgent?: string | null;
  ipAddress?: string | null;
  createdAt: string;
  rotatedAt?: string | null;
  expiresAt: string;
};
