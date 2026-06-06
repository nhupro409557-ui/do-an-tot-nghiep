import React, { useEffect, useState } from 'react';
import { updateUserProfile } from '../../../services/authDb';
import type { ProfileForm } from '../types/accountDashboardTypes';

const emptyProfileForm: ProfileForm = {
  displayName: '',
  birthDate: '',
  gender: '',
  phone: '',
  avatarUrl: '',
  verificationRole: '',
  schoolOrWorkplace: '',
  verificationCode: '',
};

export function useAccountProfile(user: any, userData: any) {
  const [profileForm, setProfileForm] = useState<ProfileForm>(emptyProfileForm);
  const [profileMessage, setProfileMessage] = useState('');
  const [isProfileEditing, setIsProfileEditing] = useState(false);

  useEffect(() => {
    if (!userData || !user) return;
    setProfileForm({
      displayName: userData.displayName || user.displayName || '',
      birthDate: userData.birthDate || '',
      gender: userData.gender || '',
      phone: userData.phone || '',
      avatarUrl: userData.avatarUrl || '',
      verificationRole: userData.verificationRole || '',
      schoolOrWorkplace: userData.schoolOrWorkplace || '',
      verificationCode: userData.verificationCode || '',
    });
  }, [user, userData]);

  const handleProfileSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!user) return;
    updateUserProfile(user.uid, {
      ...profileForm,
      displayName: profileForm.displayName.trim(),
      phone: profileForm.phone.trim(),
      verificationStatus: profileForm.verificationRole ? 'PENDING' : 'NONE',
    });
    setProfileMessage('Đã lưu cài đặt tài khoản.');
    setIsProfileEditing(false);
    setTimeout(() => setProfileMessage(''), 2500);
  };

  return {
    handleProfileSubmit,
    isProfileEditing,
    profileForm,
    profileMessage,
    setIsProfileEditing,
    setProfileForm,
  };
}
