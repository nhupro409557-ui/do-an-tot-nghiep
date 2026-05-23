import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  confirmRegistrationByCode,
  getAuthErrorMessage,
  PendingRegistration,
  resendRegistrationCode,
  signInWithGoogleProfile,
  startRegistration,
} from '../services/authDb';
import { requestGoogleProfile } from '../services/googleAuth';

const brandName = 'ElectroMart VietNam';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [pendingRegistration, setPendingRegistration] = useState<PendingRegistration | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const verificationLink = useMemo(() => {
    if (!pendingRegistration) return '';
    return `${window.location.origin}/verify-email?token=${pendingRegistration.token}`;
  }, [pendingRegistration]);

  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setError('Mật khẩu nhập lại không khớp.');
      return;
    }

    setError('');
    setMessage('');
    setLoading(true);
    try {
      const pending = await startRegistration(email, password, name);
      setPendingRegistration(pending);
      setMessage('Đã gửi mã xác nhận 6 số và link xác nhận vào email của bạn.');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Đăng ký thất bại.'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmCode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!pendingRegistration) return;

    setError('');
    setLoading(true);
    try {
      await confirmRegistrationByCode(pendingRegistration.email, verificationCode);
      setMessage('Xác nhận thành công. Tài khoản đã được tạo.');
      navigate('/');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Không thể xác nhận tài khoản.'));
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (!pendingRegistration) return;
    setError('');
    setMessage('');
    setVerificationCode('');
    setLoading(true);
    try {
      const pending = await resendRegistrationCode(pendingRegistration.email);
      setPendingRegistration(pending);
      setMessage('Da gui lai ma xac nhan moi. Ma cu da het hieu luc.');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Khong the gui lai ma xac nhan.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleRegister = async () => {
    setError('');
    setLoading(true);
    try {
      const profile = await requestGoogleProfile();
      await signInWithGoogleProfile(profile);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Đăng ký bằng Google thất bại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-[760px] rounded-3xl bg-white p-8 shadow-xl">
        <h1 className="mb-6 text-center text-2xl font-bold text-[#d70018]">Đăng ký tài khoản {brandName}</h1>
        {message && <div className="mb-5 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

        {!pendingRegistration ? (
          <form onSubmit={handleRegister} className="space-y-6">
            <div>
              <h3 className="mb-4 rounded bg-gray-50 p-2 text-sm font-bold text-gray-800">Thông tin cá nhân</h3>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-gray-700">Họ và tên</label>
                  <input required type="text" placeholder="Nhập họ và tên" value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-red-500" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-gray-700">Email</label>
                  <input required type="email" placeholder="Nhập email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-red-500" />
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-4 rounded bg-gray-50 p-2 text-sm font-bold text-gray-800">Tạo mật khẩu</h3>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-gray-700">Mật khẩu</label>
                  <input required type="password" minLength={6} placeholder="Tối thiểu 6 ký tự" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-red-500" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-gray-700">Nhập lại mật khẩu</label>
                  <input required type="password" minLength={6} placeholder="Nhập lại mật khẩu" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-red-500" />
                </div>
              </div>
            </div>

            <div className="mb-4 flex items-start gap-2 text-xs text-gray-600">
              <input type="checkbox" required className="mt-0.5" />
              <p>Bằng việc đăng ký, bạn xác nhận thông tin cung cấp là chính xác.</p>
            </div>

            <div className="flex flex-col-reverse gap-4 pt-4 md:flex-row">
              <Link to="/login" className="flex-1 rounded-lg border border-gray-300 py-3 text-center font-bold text-gray-700 hover:bg-gray-50">
                Quay lại đăng nhập
              </Link>
              <button type="submit" disabled={loading} className="flex-[2] rounded-lg bg-[#d70018] py-3 font-bold text-white hover:bg-[#c00015] disabled:bg-red-400">
                {loading ? 'Đang gửi mã...' : 'Gửi mã xác nhận'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleConfirmCode} className="space-y-5">
            <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-gray-700">
              Mã xác nhận đã gửi tới <strong>{pendingRegistration.email}</strong>. Bạn có thể nhập mã 6 số hoặc bấm link trong email để xác nhận tự động.
              <br /><br />
              <span className="text-xs italic text-gray-500">*Mã xác nhận và link được tạo, lưu và gửi từ backend.</span>
            </div>
            <div>
              <label className="mb-2 block text-sm font-bold text-gray-700">Mã xác nhận</label>
              <input
                required
                inputMode="numeric"
                maxLength={6}
                placeholder="Nhập mã 6 số"
                value={verificationCode}
                onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-center text-xl font-bold tracking-[0.35em] outline-none focus:border-red-500"
              />
            </div>
            <button type="submit" disabled={loading || verificationCode.length !== 6} className="w-full rounded-lg bg-[#d70018] py-3 font-bold text-white hover:bg-[#c00015] disabled:bg-red-400">
              {loading ? 'Đang xác nhận...' : 'Xác nhận tài khoản'}
            </button>
            <Link to={verificationLink} className="block text-center text-sm font-bold text-blue-600 hover:underline">
              Mở link xác nhận trên trình duyệt này
            </Link>
            <button type="button" onClick={handleResendCode} disabled={loading} className="w-full text-sm font-semibold text-gray-500 hover:text-[#d70018] disabled:opacity-60">
              Gui lai ma xac nhan
            </button>
          </form>
        )}

        <div className="my-6 flex items-center gap-3 text-xs text-gray-400">
          <div className="h-px flex-1 bg-gray-200" />
          <span>hoặc</span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={handleGoogleRegister}
          className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white py-3 font-bold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-70"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-sm font-black text-[#4285f4]">G</span>
          Đăng ký bằng Google
        </button>
      </div>
    </div>
  );
}
