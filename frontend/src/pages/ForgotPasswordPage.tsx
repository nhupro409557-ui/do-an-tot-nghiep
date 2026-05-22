import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  confirmPasswordResetByCode,
  createPendingPasswordReset,
  getAuthErrorMessage,
  PendingPasswordReset,
  resendPasswordResetEmail,
  sendPasswordResetEmail,
} from '../services/authDb';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [pendingReset, setPendingReset] = useState<PendingPasswordReset | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const verificationLink = useMemo(() => {
    if (!pendingReset) return '';
    return `/reset-password?verify=${pendingReset.token}`;
  }, [pendingReset]);

  const handleSendCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setVerificationCode('');
    setLoading(true);

    try {
      const reset = await sendPasswordResetEmail(email.trim());
      const pending = createPendingPasswordReset(reset.email, reset.verificationToken);
      setPendingReset(pending);
      setMessage('Đã gửi mã xác nhận 6 số và liên kết đặt lại mật khẩu vào email của bạn.');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Không thể gửi mã xác nhận đặt lại mật khẩu.'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmCode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!pendingReset) return;

    setError('');
    try {
      const resetToken = await confirmPasswordResetByCode(pendingReset.email, verificationCode);
      navigate(`/reset-password?token=${encodeURIComponent(resetToken)}`);
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Không thể xác nhận mã đặt lại mật khẩu.'));
    }
  };

  const handleResendCode = async () => {
    if (!pendingReset) return;
    setError('');
    setMessage('');
    setVerificationCode('');
    setLoading(true);
    try {
      const reset = await resendPasswordResetEmail(pendingReset.email);
      const pending = createPendingPasswordReset(reset.email, reset.verificationToken);
      setPendingReset(pending);
      setMessage('Da gui lai ma xac nhan moi. Ma cu da het hieu luc.');
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Khong the gui lai ma xac nhan.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="mb-3 text-center text-2xl font-bold text-primary">Quên mật khẩu</h1>
        <p className="mb-6 text-center text-sm text-gray-500">
          Nhập email tài khoản. Hệ thống sẽ gửi mã xác nhận và liên kết đặt lại mật khẩu có hiệu lực trong 15 phút.
        </p>

        {message && <div className="mb-5 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

        {!pendingReset ? (
          <form onSubmit={handleSendCode} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-bold text-gray-700">Email</label>
              <input
                type="email"
                required
                placeholder="Nhập email của bạn"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-primary py-3 font-bold text-white transition-colors hover:bg-red-700 disabled:opacity-70"
            >
              {loading ? 'Đang gửi mã...' : 'Gửi mã xác nhận'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirmCode} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-bold text-gray-700">Mã xác nhận</label>
              <input
                required
                inputMode="numeric"
                maxLength={6}
                placeholder="Nhập mã 6 số"
                value={verificationCode}
                onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-center text-xl font-bold tracking-[0.35em] outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <button
              type="submit"
              disabled={loading || verificationCode.length !== 6}
              className="w-full rounded-lg bg-primary py-3 font-bold text-white transition-colors hover:bg-red-700 disabled:opacity-70"
            >
              Xác nhận mã
            </button>

            <Link to={verificationLink} className="block text-center text-sm font-bold text-blue-600 hover:underline">
              Mở link xác nhận trên trình duyệt này
            </Link>

            <button type="button" onClick={handleResendCode} disabled={loading} className="w-full text-sm font-semibold text-gray-500 hover:text-primary disabled:opacity-60">
              Gui lai ma xac nhan
            </button>

            <button type="button" onClick={() => setPendingReset(null)} className="w-full text-sm font-semibold text-gray-500 hover:text-primary">
              Gửi lại bằng email khác
            </button>
          </form>
        )}

        <div className="mt-6 text-center text-sm">
          <Link to="/login" className="font-bold text-primary hover:underline">Quay lại đăng nhập</Link>
        </div>
      </div>
    </div>
  );
}
