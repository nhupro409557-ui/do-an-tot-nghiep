import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { signInWithEmailAndPassword, signInWithGoogleProfile, getAuthErrorMessage, ensureUserProfile } from '../services/authDb';
import { requestGoogleProfile } from '../services/googleAuth';

const brandName = 'ElectroMart VietNam';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await signInWithEmailAndPassword(email.trim(), password);
      ensureUserProfile(user);
      navigate('/');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, 'Đăng nhập thất bại.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      const profile = await requestGoogleProfile();
      await signInWithGoogleProfile(profile);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Đăng nhập bằng Google thất bại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-10">
      <div className="flex w-full max-w-[1000px] overflow-hidden rounded-3xl bg-white shadow-xl">
        <div className="relative hidden flex-1 flex-col border-r border-gray-100 bg-[#fffafb] p-10 md:flex">
          <div className="mb-6 flex gap-2">
            <span className="rounded bg-[#d70018] px-2 py-1 text-sm font-bold text-white">{brandName}</span>
            <span className="rounded bg-[#d70018] px-2 py-1 text-sm font-bold text-white">Thành viên</span>
          </div>
          <h2 className="mb-2 text-2xl font-bold text-gray-800">
            Đăng nhập tài khoản <span className="text-[#d70018]">{brandName}</span>
          </h2>
          <p className="mb-8 text-gray-600">Theo dõi đơn hàng, điểm thành viên và ưu đãi của bạn.</p>

          <ul className="space-y-4">
            <li className="flex items-center gap-3 text-gray-700">
              <span className="text-xl">✓</span>
              <span>Quản lý thông tin tài khoản với dữ liệu lưu trữ local.</span>
            </li>
            <li className="flex items-center gap-3 text-gray-700">
              <span className="text-xl">✓</span>
              <span>Đăng nhập bằng email và mật khẩu.</span>
            </li>
            <li className="flex items-center gap-3 text-gray-700">
              <span className="text-xl">✓</span>
              <span>Tự động tạo hồ sơ thành viên khi đăng nhập lần đầu.</span>
            </li>
          </ul>
        </div>

        <div className="flex-1 bg-white p-8 md:p-10">
          <h2 className="mb-8 text-center text-2xl font-bold text-[#d70018]">Đăng nhập</h2>

          {error && (
            <div className="mb-6 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-bold text-gray-700">Email</label>
              <input
                type="email"
                required
                placeholder="Nhập email của bạn"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] xl:bg-[#f9f9f9]"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-bold text-gray-700">Mật khẩu</label>
              <input
                type="password"
                required
                placeholder="Nhập mật khẩu của bạn"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] xl:bg-[#f9f9f9]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full rounded-lg bg-[#d70018] py-3.5 font-bold text-white shadow-md transition-colors hover:bg-[#c00015] disabled:opacity-70"
            >
              {loading ? 'Đang xử lý...' : 'Đăng nhập'}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-gray-400">
            <div className="h-px flex-1 bg-gray-200" />
            <span>hoặc</span>
            <div className="h-px flex-1 bg-gray-200" />
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={handleGoogleLogin}
            className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white py-3 font-bold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-70"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-sm font-black text-[#4285f4]">G</span>
            Đăng nhập bằng Google
          </button>

          <div className="mt-5 text-center">
            <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:text-blue-700">Quên mật khẩu?</Link>
          </div>

          <div className="mt-8 text-center text-sm text-gray-600">
            Bạn chưa có tài khoản?{' '}
            <Link to="/register" className="font-bold text-[#d70018] hover:underline">Đăng ký ngay</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
