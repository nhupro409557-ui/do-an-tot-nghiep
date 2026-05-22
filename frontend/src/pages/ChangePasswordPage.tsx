import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, KeyRound, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { changePassword, getAuthErrorMessage } from '../services/authDb';

export default function ChangePasswordPage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage('');
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Mật khẩu mới nhập lại không khớp.');
      return;
    }
    if (newPassword === currentPassword) {
      setError('Mật khẩu mới cần khác mật khẩu hiện tại.');
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setMessage('Đổi mật khẩu thành công. Lần đăng nhập sau hãy dùng mật khẩu mới.');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Không thể đổi mật khẩu.'));
    } finally {
      setLoading(false);
    }
  };

  const inputType = showPassword ? 'text' : 'password';

  return (
    <div className="container mx-auto px-4 py-8 max-w-[1200px]">
      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
        <aside className="bg-white rounded-xl shadow-sm py-4 h-fit">
          <ul className="text-sm font-medium text-gray-700">
            <li>
              <Link to="/dashboard" className="block px-6 py-3 border-l-4 border-transparent hover:bg-gray-50 hover:text-red-500">
                🏠 Tổng quan
              </Link>
            </li>
            <li className="px-6 py-3 border-l-4 border-transparent text-gray-400">📋 Lịch sử mua hàng</li>
            <li className="px-6 py-3 border-l-4 border-transparent text-gray-400">💎 Hạng thành viên</li>
            <li className="px-6 py-3 border-l-4 border-transparent text-gray-400">⚙️ Cài đặt tài khoản</li>
            <li className="px-6 py-3 text-[#d70018] bg-red-50 border-l-4 border-[#d70018]">Đổi mật khẩu</li>
          </ul>
        </aside>

        <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 md:p-8">
          <div className="flex items-start gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-red-50 text-[#d70018] flex items-center justify-center">
              <KeyRound className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Đổi mật khẩu</h1>
              <p className="text-sm text-slate-500 mt-1">Tài khoản: {user?.email}</p>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-100 text-blue-900 rounded-xl p-4 text-sm mb-6 flex gap-3">
            <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5" />
            <span>Mật khẩu mới nên có ít nhất 6 ký tự và không trùng với mật khẩu hiện tại.</span>
          </div>

          {message && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{message}</div>}
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-5 text-sm">{error}</div>}

          <form onSubmit={handleChangePassword} className="max-w-xl space-y-5">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Mật khẩu hiện tại</label>
              <input
                type={inputType}
                required
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Mật khẩu mới</label>
              <input
                type={inputType}
                required
                minLength={6}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Nhập lại mật khẩu mới</label>
              <input
                type={inputType}
                required
                minLength={6}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />
            </div>

            <button
              type="button"
              onClick={() => setShowPassword(value => !value)}
              className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#d70018]"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
            </button>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button type="submit" disabled={loading} className="flex-1 bg-primary hover:bg-red-700 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-60">
                {loading ? 'Đang cập nhật...' : 'Lưu mật khẩu mới'}
              </button>
              <Link to="/dashboard" className="flex-1 text-center border border-gray-300 text-gray-700 py-3 rounded-lg font-bold hover:bg-gray-50">
                Về tài khoản
              </Link>
            </div>
          </form>

          <div className="mt-6 text-sm">
            <Link to="/forgot-password" className="text-blue-600 font-semibold hover:underline">Quên mật khẩu?</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
