import React, { useReducer } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  confirmPasswordResetByCode,
  createPendingPasswordReset,
  getAuthErrorMessage,
  PendingPasswordReset,
  resendPasswordResetEmail,
  sendPasswordResetEmail,
} from '../../../services/authDb';

type ForgotPasswordState = {
  email: string;
  verificationCode: string;
  pendingReset: PendingPasswordReset | null;
  error: string;
  message: string;
  loading: boolean;
};

const initialForgotPasswordState: ForgotPasswordState = {
  email: '',
  verificationCode: '',
  pendingReset: null,
  error: '',
  message: '',
  loading: false,
};

function mergeForgotPasswordState(state: ForgotPasswordState, patch: Partial<ForgotPasswordState>): ForgotPasswordState {
  return { ...state, ...patch };
}

export default function ForgotPasswordPage() {
  const [{ email, verificationCode, pendingReset, error, message, loading }, setFormState] = useReducer(
    mergeForgotPasswordState,
    initialForgotPasswordState,
  );
  const navigate = useNavigate();

  const handleSendCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormState({ error: '', message: '', verificationCode: '', loading: true });

    try {
      const reset = await sendPasswordResetEmail(email.trim());
      const pending = createPendingPasswordReset(reset.email);
      setFormState({ pendingReset: pending, message: 'Đã gửi mã xác nhận 6 số và liên kết đặt lại mật khẩu vào email của bạn.' });
    } catch (err: any) {
      setFormState({ error: getAuthErrorMessage(err.code, err.message || 'Không thể gửi mã xác nhận đặt lại mật khẩu.') });
    } finally {
      setFormState({ loading: false });
    }
  };

  const handleConfirmCode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!pendingReset) return;

    setFormState({ error: '' });
    try {
      const resetToken = await confirmPasswordResetByCode(pendingReset.email, verificationCode);
      navigate(`/reset-password?token=${encodeURIComponent(resetToken)}`);
    } catch (err: any) {
      setFormState({ error: getAuthErrorMessage(err.code, err.message || 'Không thể xác nhận mã đặt lại mật khẩu.') });
    }
  };

  const handleResendCode = async () => {
    if (!pendingReset) return;
    setFormState({ error: '', message: '', verificationCode: '', loading: true });
    try {
      const reset = await resendPasswordResetEmail(pendingReset.email);
      const pending = createPendingPasswordReset(reset.email);
      setFormState({ pendingReset: pending, message: 'Đã gửi lại mã xác nhận mới. Mã cũ đã hết hiệu lực.' });
    } catch (err: any) {
      setFormState({ error: getAuthErrorMessage(err.code, err.message || 'Không thể gửi lại mã xác nhận.') });
    } finally {
      setFormState({ loading: false });
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
              <label htmlFor="forgot-password-email" className="mb-2 block text-sm font-bold text-gray-700">Email</label>
              <input
                id="forgot-password-email"
                aria-label="Email khôi phục mật khẩu"
                type="email"
                required
                placeholder="Nhập email của bạn"
                value={email}
                onChange={(event) => setFormState({ email: event.target.value })}
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
              <label htmlFor="forgot-password-code" className="mb-2 block text-sm font-bold text-gray-700">Mã xác nhận</label>
              <input
                id="forgot-password-code"
                aria-label="Mã xác nhận khôi phục mật khẩu"
                required
                inputMode="numeric"
                maxLength={6}
                placeholder="Nhập mã 6 số"
                value={verificationCode}
                onChange={(event) => setFormState({ verificationCode: event.target.value.replace(/\D/g, '').slice(0, 6) })}
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

            <button type="button" onClick={handleResendCode} disabled={loading} className="w-full text-sm font-semibold text-gray-500 hover:text-primary disabled:opacity-60">
              Gửi lại mã xác nhận
            </button>

            <button type="button" onClick={() => setFormState({ pendingReset: null })} className="w-full text-sm font-semibold text-gray-500 hover:text-primary">
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
