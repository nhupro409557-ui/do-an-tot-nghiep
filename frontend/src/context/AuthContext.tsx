import React, { createContext, use, useCallback, useEffect, useMemo, useState } from 'react';
import { MockUser, onAuthStateChanged, getUserProfile, initializeAuth } from '../services/authDb';

interface UserData {
  role: string;
  tier: string;
  points: number;
  tierPeriodStartedAt?: string;
  tierPeriodEndsAt?: string;
  tierPeriodSpendAmount?: number;
  pointsExpiringSoon?: number;
  nearestPointsExpirationAt?: string;
  nearestPointsExpirationAmount?: number;
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
          setUserData(data);
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
  const normalizedRole = String(userData?.role || '').trim().toLowerCase().replaceAll('-', '_');
  const isSuperAdmin = ['super_admin', 'superadmin'].includes(normalizedRole);
  const isStaff = ['staff', 'staff_admin'].includes(normalizedRole);
  const canAccessAdmin = isSuperAdmin || isStaff || permissions.length > 0;
  const usePermission = useCallback((code: string) => isSuperAdmin || permissions.includes(code), [isSuperAdmin, permissions]);
  const useAnyPermission = useCallback((codes: string[]) => isSuperAdmin || codes.some((code) => permissions.includes(code)), [isSuperAdmin, permissions]);
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
