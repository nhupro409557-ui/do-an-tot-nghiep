import type React from 'react';
import { Mail, Pencil, UserRound } from 'lucide-react';
import type { ProfileForm } from '../types/accountDashboardTypes';

type ProfileSettingsSectionProps = {
  email?: string | null;
  profileForm: ProfileForm;
  profileMessage: string;
  isProfileEditing: boolean;
  onProfileSubmit: (event: React.FormEvent) => void;
  onProfileFormChange: React.Dispatch<React.SetStateAction<ProfileForm>>;
  onSetProfileEditing: (editing: boolean) => void;
};

export function ProfileSettingsSection({
  email,
  profileForm,
  profileMessage,
  isProfileEditing,
  onProfileSubmit,
  onProfileFormChange,
  onSetProfileEditing,
}: ProfileSettingsSectionProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <UserRound className="w-6 h-6 text-[#d70018]" />
          <h3 className="font-bold text-gray-800">Cài đặt tài khoản</h3>
        </div>
        {!isProfileEditing && (
          <button type="button" onClick={() => onSetProfileEditing(true)} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-[#d70018] text-[#d70018] text-sm font-bold hover:bg-red-50">
            <Pencil className="w-4 h-4" /> Chỉnh sửa
          </button>
        )}
      </div>
      {profileMessage && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{profileMessage}</div>}
      <form onSubmit={onProfileSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="text-sm font-semibold text-gray-700 md:col-span-2">Gmail
          <div className="mt-2 flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-500">
            <Mail className="w-4 h-4" />
            <span className="truncate">{email}</span>
          </div>
        </label>
        <label className="text-sm font-semibold text-gray-700">Họ tên
          <input disabled={!isProfileEditing} value={profileForm.displayName} onChange={event => onProfileFormChange({ ...profileForm, displayName: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
        </label>
        <label className="text-sm font-semibold text-gray-700">Số điện thoại chính
          <input disabled={!isProfileEditing} value={profileForm.phone} onChange={event => onProfileFormChange({ ...profileForm, phone: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
        </label>
        <label className="text-sm font-semibold text-gray-700">Ngày tháng năm sinh
          <input disabled={!isProfileEditing} type="date" value={profileForm.birthDate} onChange={event => onProfileFormChange({ ...profileForm, birthDate: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
        </label>
        <label className="text-sm font-semibold text-gray-700">Giới tính
          <select disabled={!isProfileEditing} value={profileForm.gender} onChange={event => onProfileFormChange({ ...profileForm, gender: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500">
            <option value="">Chưa chọn</option>
            <option value="female">Nữ</option>
            <option value="male">Nam</option>
            <option value="other">Khác</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-gray-700 md:col-span-2">Ảnh đại diện (có thể để trống)
          <input disabled={!isProfileEditing} value={profileForm.avatarUrl} onChange={event => onProfileFormChange({ ...profileForm, avatarUrl: event.target.value })} placeholder="Dán liên kết ảnh nếu muốn dùng ảnh đại diện" className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
        </label>
        <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 rounded-lg p-4">
          <label className="text-sm font-semibold text-gray-700">Xác minh
            <select disabled={!isProfileEditing} value={profileForm.verificationRole} onChange={event => onProfileFormChange({ ...profileForm, verificationRole: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500">
              <option value="">Không xác minh</option>
              <option value="student">Sinh viên</option>
              <option value="lecturer">Giảng viên</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-gray-700">Trường / đơn vị
            <input disabled={!isProfileEditing} value={profileForm.schoolOrWorkplace} onChange={event => onProfileFormChange({ ...profileForm, schoolOrWorkplace: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
          </label>
          <label className="text-sm font-semibold text-gray-700">Mã sinh viên / giảng viên
            <input disabled={!isProfileEditing} value={profileForm.verificationCode} onChange={event => onProfileFormChange({ ...profileForm, verificationCode: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
          </label>
        </div>
        {isProfileEditing && (
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button type="button" onClick={() => onSetProfileEditing(false)} className="border border-gray-300 text-gray-700 py-3 rounded-lg font-bold hover:bg-gray-50">Hủy</button>
            <button type="submit" className="bg-[#d70018] hover:bg-red-700 text-white py-3 rounded-lg font-bold transition-colors">Lưu thông tin tài khoản</button>
          </div>
        )}
      </form>
    </section>
  );
}
