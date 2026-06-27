import type React from 'react';
import { AddressesTab } from './AddressesTab';
import { FavoriteProductsTab } from './FavoriteProductsTab';
import { MembershipTab } from './MembershipTab';
import { OrdersTab } from './OrdersTab';
import { OverviewTab } from './OverviewTab';
import { SettingsTab } from './SettingsTab';
import { AfterSalesTab } from './AfterSalesTab';
import { NotificationsTab, TransactionsTab, VoucherWalletTab } from './CustomerCenterTabs';

type AccountDashboardContentProps = {
  activeTab: string;
  addresses: any[];
  orders: any[];
  favorites: any[];
  points: number;
  nextTierInfo: {
    name: string;
    needed: number;
    percentage: number;
  };
  userEmail?: string | null;
  addressDraft: any;
  editingAddressId: string | null;
  isAddressFormOpen: boolean;
  mapPredictionAddress: string;
  emptyAddress: any;
  profileForm: any;
  profileMessage: string;
  isProfileEditing: boolean;
  passwordMessage: string;
  passwordError: string;
  isPasswordEditing: boolean;
  isChangingPassword: boolean;
  showPassword: boolean;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  authSessions: any[];
  onOpenAddresses: () => void;
  onOpenLoyalty: () => void;
  onOpenNewAddressForm: () => void;
  onOpenEditAddressForm: (address: any) => void;
  onSubmitAddress: (event: React.FormEvent) => void;
  onUpdateAddressDraft: React.Dispatch<React.SetStateAction<any>>;
  onSetAddressFormOpen: (isOpen: boolean) => void;
  onSetEditingAddressId: (id: string | null) => void;
  onUpdateAddresses: (addresses: any[]) => void;
  onVerifyAddressOnMap: (address: any) => void;
  onProfileSubmit: (event: React.FormEvent) => void;
  onProfileFormChange: React.Dispatch<React.SetStateAction<any>>;
  onSetProfileEditing: (editing: boolean) => void;
  onPasswordSubmit: (event: React.FormEvent) => void;
  onSetPasswordEditing: (editing: boolean) => void;
  onSetShowPassword: React.Dispatch<React.SetStateAction<boolean>>;
  onSetCurrentPassword: (value: string) => void;
  onSetNewPassword: (value: string) => void;
  onSetConfirmPassword: (value: string) => void;
  onRevokeSession: (sessionId: string, isCurrent: boolean) => void;
  onOpenDeleteAccount: () => void;
  onOpenProduct: (product: any) => void;
  onRemoveFavorite: (productId: string) => void;
};

export function AccountDashboardContent(props: AccountDashboardContentProps) {
  return (
    <div className="flex-1 flex flex-col gap-6 min-w-0">
      {props.activeTab === 'overview' && (
        <OverviewTab
          addresses={props.addresses}
          orders={props.orders}
          onOpenAddresses={props.onOpenAddresses}
          onOpenLoyalty={props.onOpenLoyalty}
        />
      )}

      {props.activeTab === 'orders' && (
        <OrdersTab orders={props.orders} />
      )}
      {props.activeTab === 'returns' && <AfterSalesTab kind="return" orders={props.orders} />}
      {props.activeTab === 'warranties' && <AfterSalesTab kind="warranty" orders={props.orders} />}
      {props.activeTab === 'vouchers' && <VoucherWalletTab />}
      {props.activeTab === 'transactions' && <TransactionsTab />}
      {props.activeTab === 'notifications' && <NotificationsTab />}

      {props.activeTab === 'membership' && (
        <MembershipTab points={props.points} nextTierInfo={props.nextTierInfo} />
      )}

      {props.activeTab === 'addresses' && (
        <AddressesTab
          addresses={props.addresses}
          addressDraft={props.addressDraft}
          editingAddressId={props.editingAddressId}
          isAddressFormOpen={props.isAddressFormOpen}
          mapPredictionAddress={props.mapPredictionAddress}
          emptyAddress={props.emptyAddress}
          onOpenNewAddressForm={props.onOpenNewAddressForm}
          onOpenEditAddressForm={props.onOpenEditAddressForm}
          onSubmitAddress={props.onSubmitAddress}
          onUpdateAddressDraft={props.onUpdateAddressDraft}
          onSetAddressFormOpen={props.onSetAddressFormOpen}
          onSetEditingAddressId={props.onSetEditingAddressId}
          onUpdateAddresses={props.onUpdateAddresses}
          onVerifyAddressOnMap={props.onVerifyAddressOnMap}
        />
      )}

      {props.activeTab === 'settings' && (
        <SettingsTab
          email={props.userEmail}
          profileForm={props.profileForm}
          profileMessage={props.profileMessage}
          isProfileEditing={props.isProfileEditing}
          passwordMessage={props.passwordMessage}
          passwordError={props.passwordError}
          isPasswordEditing={props.isPasswordEditing}
          isChangingPassword={props.isChangingPassword}
          showPassword={props.showPassword}
          currentPassword={props.currentPassword}
          newPassword={props.newPassword}
          confirmPassword={props.confirmPassword}
          authSessions={props.authSessions}
          onProfileSubmit={props.onProfileSubmit}
          onProfileFormChange={props.onProfileFormChange}
          onSetProfileEditing={props.onSetProfileEditing}
          onPasswordSubmit={props.onPasswordSubmit}
          onSetPasswordEditing={props.onSetPasswordEditing}
          onSetShowPassword={props.onSetShowPassword}
          onSetCurrentPassword={props.onSetCurrentPassword}
          onSetNewPassword={props.onSetNewPassword}
          onSetConfirmPassword={props.onSetConfirmPassword}
          onRevokeSession={props.onRevokeSession}
          onOpenDeleteAccount={props.onOpenDeleteAccount}
        />
      )}

      {props.activeTab === 'favorites' && (
        <FavoriteProductsTab
          favorites={props.favorites}
          onOpenProduct={props.onOpenProduct}
          onRemoveFavorite={props.onRemoveFavorite}
        />
      )}
    </div>
  );
}
