import type React from 'react';
import { Eye, EyeOff, KeyRound } from 'lucide-react';

type PasswordSettingsSectionProps = {
  passwordMessage: string;
  passwordError: string;
  isPasswordEditing: boolean;
  isChangingPassword: boolean;
  showPassword: boolean;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  onPasswordSubmit: (event: React.FormEvent) => void;
  onSetPasswordEditing: (editing: boolean) => void;
  onSetShowPassword: React.Dispatch<React.SetStateAction<boolean>>;
  onSetCurrentPassword: (value: string) => void;
  onSetNewPassword: (value: string) => void;
  onSetConfirmPassword: (value: string) => void;
};

export function PasswordSettingsSection({
  passwordMessage,
  passwordError,
  isPasswordEditing,
  isChangingPassword,
  showPassword,
  currentPassword,
  newPassword,
  confirmPassword,
  onPasswordSubmit,
  onSetPasswordEditing,
  onSetShowPassword,
  onSetCurrentPassword,
  onSetNewPassword,
  onSetConfirmPassword,
}: PasswordSettingsSectionProps) {
  const inputType = showPassword ? 'text' : 'password';

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <KeyRound className="w-6 h-6 text-[#d70018]" />
          <h3 className="font-bold text-gray-800">Đổi mật khẩu</h3>
        </div>
        {!isPasswordEditing && (
          <button type="button" onClick={() => onSetPasswordEditing(true)} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-[#d70018] text-[#d70018] text-sm font-bold hover:bg-red-50">
            <KeyRound className="w-4 h-4" /> Đổi mật khẩu
          </button>
        )}
      </div>
      {passwordMessage && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{passwordMessage}</div>}
      {passwordError && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-5 text-sm">{passwordError}</div>}
      {isPasswordEditing ? (
        <form onSubmit={onPasswordSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input type={inputType} required value={currentPassword} onChange={event => onSetCurrentPassword(event.target.value)} placeholder="Mật khẩu hiện tại" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
          <input type={inputType} required minLength={6} value={newPassword} onChange={event => onSetNewPassword(event.target.value)} placeholder="Mật khẩu mới" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
          <input type={inputType} required minLength={6} value={confirmPassword} onChange={event => onSetConfirmPassword(event.target.value)} placeholder="Nhập lại mật khẩu mới" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
          <button type="button" onClick={() => onSetShowPassword(value => !value)} className="inline-flex items-center justify-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#d70018]">
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
          </button>
          <button type="submit" disabled={isChangingPassword} className="md:col-span-2 bg-[#d70018] hover:bg-red-700 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-60">
            {isChangingPassword ? 'Đang cập nhật...' : 'Lưu mật khẩu mới'}
          </button>
        </form>
      ) : (
        <p className="text-sm text-gray-500">Bấm Đổi mật khẩu để nhập mật khẩu hiện tại và mật khẩu mới.</p>
      )}
    </section>
  );
}
