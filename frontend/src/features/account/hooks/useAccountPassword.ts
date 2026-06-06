import React, { useState } from 'react';
import { changePassword, getAuthErrorMessage } from '../../../services/authDb';

export function useAccountPassword() {
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isPasswordEditing, setIsPasswordEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setPasswordMessage('');
    setPasswordError('');

    if (newPassword !== confirmPassword) {
      setPasswordError('Mật khẩu mới nhập lại không khớp.');
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError('Mật khẩu mới cần khác mật khẩu hiện tại.');
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setIsPasswordEditing(false);
      setPasswordMessage('Đổi mật khẩu thành công.');
    } catch (err: any) {
      setPasswordError(getAuthErrorMessage(err.code, err.message || 'Không thể đổi mật khẩu.'));
    } finally {
      setIsChangingPassword(false);
    }
  };

  return {
    confirmPassword,
    currentPassword,
    handleChangePassword,
    isChangingPassword,
    isPasswordEditing,
    newPassword,
    passwordError,
    passwordMessage,
    setConfirmPassword,
    setCurrentPassword,
    setIsPasswordEditing,
    setNewPassword,
    setShowPassword,
    showPassword,
  };
}
