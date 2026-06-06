import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { signOut } from '../../../services/authDb';
import { AccountDashboardContent } from '../components/AccountDashboardContent';
import { AccountDashboardHeader } from '../components/AccountDashboardHeader';
import { AccountDashboardSidebar } from '../components/AccountDashboardSidebar';
import { DeleteAccountModal } from '../components/DeleteAccountModal';
import { accountNavItems, getNextTierInfo } from '../utils/accountDashboardConfig';
import type { AccountAddress, AccountTab } from '../types/accountDashboardTypes';
import { useAccountAddresses } from '../hooks/useAccountAddresses';
import { useAccountDelete } from '../hooks/useAccountDelete';
import { useAccountFavorites } from '../hooks/useAccountFavorites';
import { useAccountOrders } from '../hooks/useAccountOrders';
import { useAccountPassword } from '../hooks/useAccountPassword';
import { useAccountProfile } from '../hooks/useAccountProfile';
import { useAccountSessions } from '../hooks/useAccountSessions';

export default function DashboardPage() {
  const { user, userData, loading } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<AccountTab>('overview');
  const addresses = useMemo<AccountAddress[]>(() => userData?.addresses || [], [userData]);

  const { orders } = useAccountOrders(user?.uid);
  const { favorites, removeFavorite } = useAccountFavorites(user?.uid);
  const { authSessions, revokeSession } = useAccountSessions(user?.uid, activeTab, navigate);
  const {
    handleProfileSubmit,
    isProfileEditing,
    profileForm,
    profileMessage,
    setIsProfileEditing,
    setProfileForm,
  } = useAccountProfile(user, userData);
  const {
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
  } = useAccountPassword();
  const {
    handleDeleteAccount,
    isDeleting,
    setShowDeleteModal,
    showDeleteModal,
  } = useAccountDelete(user?.uid, navigate);
  const {
    addressDraft,
    editingAddressId,
    emptyAddress,
    handleAddAddress,
    isAddressFormOpen,
    mapPredictionAddress,
    openEditAddressForm,
    openNewAddressForm,
    setAddressDraft,
    setEditingAddressId,
    setIsAddressFormOpen,
    updateAddresses,
    verifyAddressOnMap,
  } = useAccountAddresses({ userId: user?.uid, addresses });

  const points = userData?.points || 0;
  const nextTierInfo = getNextTierInfo(points);

  if (loading || !user) return <div className="text-center py-20">Đang tải...</div>;

  const handleOpenFavoriteProduct = (product: any) => {
    navigate(`/product/${product.slug || product.id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-[1200px]">
      <DeleteAccountModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
        currentLoyaltyPoints={points}
        isDeleting={isDeleting}
      />

      <AccountDashboardHeader
        avatarUrl={profileForm.avatarUrl}
        displayName={profileForm.displayName || user.displayName}
        email={user.email}
        tier={userData?.tier}
        verificationRole={userData?.verificationRole}
        points={points}
        nextTierInfo={nextTierInfo}
        onSignOut={() => signOut()}
      />

      <div className="flex flex-col lg:flex-row gap-6 mt-6">
        <AccountDashboardSidebar
          activeTab={activeTab}
          items={accountNavItems}
          onChangeTab={(tab) => setActiveTab(tab)}
        />

        <AccountDashboardContent
          activeTab={activeTab}
          addresses={addresses}
          orders={orders}
          favorites={favorites}
          points={points}
          nextTierInfo={nextTierInfo}
          userEmail={user.email}
          addressDraft={addressDraft}
          editingAddressId={editingAddressId}
          isAddressFormOpen={isAddressFormOpen}
          mapPredictionAddress={mapPredictionAddress}
          emptyAddress={emptyAddress}
          profileForm={profileForm}
          profileMessage={profileMessage}
          isProfileEditing={isProfileEditing}
          passwordMessage={passwordMessage}
          passwordError={passwordError}
          isPasswordEditing={isPasswordEditing}
          isChangingPassword={isChangingPassword}
          showPassword={showPassword}
          currentPassword={currentPassword}
          newPassword={newPassword}
          confirmPassword={confirmPassword}
          authSessions={authSessions}
          onOpenAddresses={() => setActiveTab('addresses')}
          onOpenLoyalty={() => navigate('/loyalty')}
          onOpenNewAddressForm={openNewAddressForm}
          onOpenEditAddressForm={openEditAddressForm}
          onSubmitAddress={handleAddAddress}
          onUpdateAddressDraft={setAddressDraft}
          onSetAddressFormOpen={setIsAddressFormOpen}
          onSetEditingAddressId={setEditingAddressId}
          onUpdateAddresses={updateAddresses}
          onVerifyAddressOnMap={verifyAddressOnMap}
          onProfileSubmit={handleProfileSubmit}
          onProfileFormChange={setProfileForm}
          onSetProfileEditing={setIsProfileEditing}
          onPasswordSubmit={handleChangePassword}
          onSetPasswordEditing={setIsPasswordEditing}
          onSetShowPassword={setShowPassword}
          onSetCurrentPassword={setCurrentPassword}
          onSetNewPassword={setNewPassword}
          onSetConfirmPassword={setConfirmPassword}
          onRevokeSession={revokeSession}
          onOpenDeleteAccount={() => setShowDeleteModal(true)}
          onOpenProduct={handleOpenFavoriteProduct}
          onRemoveFavorite={removeFavorite}
        />
      </div>
    </div>
  );
}
