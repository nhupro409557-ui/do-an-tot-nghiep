import React, { createContext, use, useCallback, useEffect, useMemo, useState } from 'react';
import { MockUser, onAuthStateChanged, getUserProfile, initializeAuth, updateUserProfile } from '../services/authDb';

interface UserData {
  role: string;
  tier: string;
  points: number;
  displayName?: string;
  birthDate?: string;
  gender?: string;
  phone?: string;
  avatarUrl?: string;
  verificationRole?: string;
  verificationStatus?: string;
  schoolOrWorkplace?: string;
  verificationCode?: string;
  permissions?: string[];
  addresses?: {
    id: string;
    receiverName: string;
    receiverPhone: string;
    addressLine: string;
    addressData?: {
      provinceId: string;
      provinceName: string;
      districtId: string;
      districtName: string;
      wardId: string;
      wardName: string;
      street: string;
    };
    oldAddressData?: {
      provinceId: string;
      provinceName: string;
      districtId: string;
      districtName: string;
      wardId: string;
      wardName: string;
      street: string;
    };
    mapQueryAddress?: string;
    mapUrl?: string;
    lat?: number;
    lng?: number;
    note?: string;
    isDefault: boolean;
    isMapVerified: boolean;
  }[];
}

interface AuthContextType {
  user: MockUser | null;
  userData: UserData | null;
  loading: boolean;
  isSuperAdmin: boolean;
  isStaff: boolean;
  canAccessAdmin: boolean;
  permissions: string[];
  usePermission: (code: string) => boolean;
  useAnyPermission: (codes: string[]) => boolean;
}

const EMPTY_PERMISSIONS: string[] = [];

const AuthContext = createContext<AuthContextType>({
  user: null,
  userData: null,
  loading: true,
  isSuperAdmin: false,
  isStaff: false,
  canAccessAdmin: false,
  permissions: [],
  usePermission: () => false,
  useAnyPermission: () => false,
});

const calculateTier = (points: number): string => {
  if (points >= 15000) return 'S-Vip';
  if (points >= 3000) return 'S-Mem';
  return 'S-New';
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<MockUser | null>(null);
  const [userData, setUserData] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const unsubscribe = onAuthStateChanged((currentUser) => {
      if (!mounted) return;
      setUser(currentUser);

      if (currentUser) {
        const profile = getUserProfile(currentUser.uid);
        if (profile) {
          const data = profile as UserData;
          const computedTier = calculateTier(data.points || 0);

          if (data.tier !== computedTier && data.role === 'user') {
            updateUserProfile(currentUser.uid, { tier: computedTier });
          }
          setUserData({ ...data, tier: computedTier });
        } else {
          setUserData(null);
        }
      } else {
        setUserData(null);
      }
    });

    (async () => {
      try {
        await initializeAuth();
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, []);

  const permissions = userData?.permissions || EMPTY_PERMISSIONS;
  const isSuperAdmin = userData?.role === 'super_admin';
  const isStaff = userData?.role === 'staff';
  const canAccessAdmin = isSuperAdmin || isStaff || permissions.length > 0;
  const usePermission = useCallback((code: string) => permissions.includes(code), [permissions]);
  const useAnyPermission = useCallback((codes: string[]) => codes.some((code) => permissions.includes(code)), [permissions]);
  const contextValue = useMemo(
    () => ({ user, userData, loading, isSuperAdmin, isStaff, canAccessAdmin, permissions, usePermission, useAnyPermission }),
    [user, userData, loading, isSuperAdmin, isStaff, canAccessAdmin, permissions, usePermission, useAnyPermission],
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => use(AuthContext);
