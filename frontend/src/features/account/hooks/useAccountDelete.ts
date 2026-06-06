import { useState } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { deleteCurrentUser, signOut, updateUserProfile } from '../../../services/authDb';

export function useAccountDelete(userId: string | undefined, navigate: NavigateFunction) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAccount = async () => {
    if (!userId) return;
    setIsDeleting(true);
    try {
      updateUserProfile(userId, { points: 0, tier: 'S-New' });
      await deleteCurrentUser();
      navigate('/');
    } catch (error: any) {
      if (error.code === 'auth/requires-recent-login') {
        alert('Vui lòng đăng nhập lại trước khi xóa tài khoản.');
        await signOut();
      } else {
        alert('Có lỗi xảy ra khi xóa tài khoản.');
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  return {
    handleDeleteAccount,
    isDeleting,
    setShowDeleteModal,
    showDeleteModal,
  };
}
