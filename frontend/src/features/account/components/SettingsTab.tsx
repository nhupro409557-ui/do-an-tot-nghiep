import type React from 'react';
import { AuthSessionsSection } from './AuthSessionsSection';
import { DeleteAccountSection } from './DeleteAccountSection';
import { PasswordSettingsSection } from './PasswordSettingsSection';
import { ProfileSettingsSection } from './ProfileSettingsSection';
import type { AuthSession, ProfileForm } from '../types/accountDashboardTypes';

type SettingsTabProps = {
  email?: string | null;
  profileForm: ProfileForm;
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
  authSessions: AuthSession[];
  onProfileSubmit: (event: React.FormEvent) => void;
  onProfileFormChange: React.Dispatch<React.SetStateAction<ProfileForm>>;
  onSetProfileEditing: (editing: boolean) => void;
  onPasswordSubmit: (event: React.FormEvent) => void;
  onSetPasswordEditing: (editing: boolean) => void;
  onSetShowPassword: React.Dispatch<React.SetStateAction<boolean>>;
  onSetCurrentPassword: (value: string) => void;
  onSetNewPassword: (value: string) => void;
  onSetConfirmPassword: (value: string) => void;
  onRevokeSession: (sessionId: string, isCurrent: boolean) => void;
  onOpenDeleteAccount: () => void;
};

export function SettingsTab({
  email,
  profileForm,
  profileMessage,
  isProfileEditing,
  passwordMessage,
  passwordError,
  isPasswordEditing,
  isChangingPassword,
  showPassword,
  currentPassword,
  newPassword,
  confirmPassword,
  authSessions,
  onProfileSubmit,
  onProfileFormChange,
  onSetProfileEditing,
  onPasswordSubmit,
  onSetPasswordEditing,
  onSetShowPassword,
  onSetCurrentPassword,
  onSetNewPassword,
  onSetConfirmPassword,
  onRevokeSession,
  onOpenDeleteAccount,
}: SettingsTabProps) {
  return (
    <>
      <ProfileSettingsSection
        email={email}
        profileForm={profileForm}
        profileMessage={profileMessage}
        isProfileEditing={isProfileEditing}
        onProfileSubmit={onProfileSubmit}
        onProfileFormChange={onProfileFormChange}
        onSetProfileEditing={onSetProfileEditing}
      />

      <PasswordSettingsSection
        passwordMessage={passwordMessage}
        passwordError={passwordError}
        isPasswordEditing={isPasswordEditing}
        isChangingPassword={isChangingPassword}
        showPassword={showPassword}
        currentPassword={currentPassword}
        newPassword={newPassword}
        confirmPassword={confirmPassword}
        onPasswordSubmit={onPasswordSubmit}
        onSetPasswordEditing={onSetPasswordEditing}
        onSetShowPassword={onSetShowPassword}
        onSetCurrentPassword={onSetCurrentPassword}
        onSetNewPassword={onSetNewPassword}
        onSetConfirmPassword={onSetConfirmPassword}
      />

      <AuthSessionsSection authSessions={authSessions} onRevokeSession={onRevokeSession} />
      <DeleteAccountSection onOpenDeleteAccount={onOpenDeleteAccount} />
    </>
  );
}
