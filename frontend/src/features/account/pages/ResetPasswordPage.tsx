import React, { useEffect, useReducer } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { confirmPasswordResetByVerificationToken, getAuthErrorMessage, resetPasswordWithToken } from '../../../services/authDb';

type ResetPasswordState = {
  password: string;
  confirmPassword: string;
  resetToken: string;
  error: string;
  message: string;
  loading: boolean;
};

const initialResetPasswordState: ResetPasswordState = {
  password: '',
  confirmPassword: '',
  resetToken: '',
  error: '',
  message: '',
  loading: false,
};

function mergeResetPasswordState(state: ResetPasswordState, patch: Partial<ResetPasswordState>): ResetPasswordState {
  return { ...state, ...patch };
}

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [{ password, confirmPassword, resetToken, error, message, loading }, setFormState] = useReducer(
    mergeResetPasswordState,
    initialResetPasswordState,
  );
  const navigate = useNavigate();
  const isAdminRecovery = searchParams.get('context') === 'admin';
  const loginPath = isAdminRecovery ? '/admin/login' : '/login';
  const forgotPasswordPath = isAdminRecovery ? '/forgot-password?context=admin' : '/forgot-password';

  useEffect(() => {
    const directToken = searchParams.get('token');
    if (directToken) {
      setFormState({ resetToken: directToken });
      return;
    }

    const verificationToken = searchParams.get('verify');
    if (!verificationToken) return;

    confirmPasswordResetByVerificationToken(verificationToken)
      .then((confirmedToken) => setFormState({ resetToken: confirmedToken }))
      .catch((err: any) => {
        setFormState({ error: getAuthErrorMessage(err.code, err.message || 'Liên kết xác nhận không hợp lệ.') });
      });
  }, [searchParams]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormState({ error: '', message: '' });

    if (!resetToken) {
      setFormState({ error: 'Bạn cần xác nhận bằng mã hoặc liên kết trong email trước khi đặt lại mật khẩu.' });
      return;
    }
    if (password !== confirmPassword) {
      setFormState({ error: 'Mật khẩu nhập lại không khớp.' });
      return;
    }

    setFormState({ loading: true });
    try {
      await resetPasswordWithToken(resetToken, password);
      setFormState({ message: 'Đã đổi mật khẩu thành công. Bạn có thể đăng nhập bằng mật khẩu mới.' });
      setTimeout(() => navigate(loginPath), 1200);
    } catch (err: any) {
      setFormState({ error: getAuthErrorMessage(err.code, err.message || 'Không thể đặt lại mật khẩu.') });
    } finally {
      setFormState({ loading: false });
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="mb-6 text-center text-2xl font-bold text-primary">Đặt mật khẩu mới</h1>

        {message && <div className="mb-5 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="reset-password-new" className="mb-2 block text-sm font-bold text-gray-700">Mật khẩu mới</label>
            <input
              id="reset-password-new"
              aria-label="Mật khẩu mới"
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(event) => setFormState({ password: event.target.value })}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label htmlFor="reset-password-confirm" className="mb-2 block text-sm font-bold text-gray-700">Nhập lại mật khẩu</label>
            <input
              id="reset-password-confirm"
              aria-label="Nhập lại mật khẩu mới"
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(event) => setFormState({ confirmPassword: event.target.value })}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !resetToken}
            className="w-full rounded-lg bg-primary py-3 font-bold text-white transition-colors hover:bg-red-700 disabled:opacity-70"
          >
            {loading ? 'Đang lưu...' : 'Lưu mật khẩu mới'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm">
          <Link to={forgotPasswordPath} className="font-bold text-primary hover:underline">Gửi lại mã xác nhận</Link>
        </div>
      </div>
    </div>
  );
}
