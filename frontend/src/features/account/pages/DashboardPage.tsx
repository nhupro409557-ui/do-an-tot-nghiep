import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<AccountTab>('overview');
  const [isDashboardMenuOpen, setIsDashboardMenuOpen] = useState(false);
  const addresses = useMemo<AccountAddress[]>(() => userData?.addresses || [], [userData]);

  const { orders, loading: ordersLoading } = useAccountOrders(user?.uid, activeTab);
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
  const nextTierInfo = getNextTierInfo(userData?.tierPeriodSpendAmount || 0);

  // Auto switch tab and action based on URL query params
  useEffect(() => {
    if (loading || !user) return;
    const tabParam = searchParams.get('tab') as AccountTab | null;
    const actionParam = searchParams.get('action');
    
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
    if (tabParam === 'addresses' && actionParam === 'new') {
      openNewAddressForm();
    }
  }, [searchParams, loading, user]);

  if (loading || !user) return <div className="min-h-[50vh] py-20 text-center text-sm font-medium text-slate-500">Đang tải tài khoản...</div>;

  const handleOpenFavoriteProduct = (product: any) => {
    navigate(`/product/${product.slug || product.id}`);
  };

  const handleChangeTab = (tab: AccountTab) => {
    setActiveTab(tab);
    setIsDashboardMenuOpen(false);
  };

  const handleSubmitAddress = (event: React.FormEvent) => {
    handleAddAddress(event);
    const redirectParam = searchParams.get('redirect');
    if (redirectParam) {
      navigate(redirectParam);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50/80">
      <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
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

      <div className="mt-6 flex flex-col gap-6 lg:flex-row lg:items-start">
        <AccountDashboardSidebar
          activeTab={activeTab}
          items={accountNavItems}
          isOpen={isDashboardMenuOpen}
          onChangeTab={handleChangeTab}
          onToggle={() => setIsDashboardMenuOpen(isOpen => !isOpen)}
        />

        <AccountDashboardContent
          activeTab={activeTab}
          addresses={addresses}
          orders={orders}
          ordersLoading={ordersLoading}
          favorites={favorites}
          points={points}
          loyaltyPeriod={{
            startedAt: userData?.tierPeriodStartedAt,
            endsAt: userData?.tierPeriodEndsAt,
            spendAmount: userData?.tierPeriodSpendAmount,
            expiringSoon: userData?.pointsExpiringSoon,
            nearestExpirationAt: userData?.nearestPointsExpirationAt,
            nearestExpirationAmount: userData?.nearestPointsExpirationAmount,
            tier: userData?.tier,
          }}
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
          onSubmitAddress={handleSubmitAddress}
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
    </main>
  );
}
