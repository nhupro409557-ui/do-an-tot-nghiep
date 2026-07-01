import { useEffect, useReducer } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { confirmRegistrationByToken, getAuthErrorMessage } from '../../../services/authDb';

type VerifyEmailState = {
  status: string;
  error: string;
};

const initialVerifyEmailState: VerifyEmailState = {
  status: 'Đang xác nhận tài khoản...',
  error: '',
};

function mergeVerifyEmailState(state: VerifyEmailState, patch: Partial<VerifyEmailState>): VerifyEmailState {
  return { ...state, ...patch };
}

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [{ status, error }, setPageState] = useReducer(mergeVerifyEmailState, initialVerifyEmailState);
  const navigate = useNavigate();

  useEffect(() => {
    let redirectTimer: ReturnType<typeof setTimeout> | null = null;
    let isActive = true;
    const token = searchParams.get('token') || '';

    if (!token) {
      setPageState({ error: 'Liên kết xác nhận không hợp lệ.', status: '' });
      return () => {};
    }

    confirmRegistrationByToken(token)
      .then(() => {
        if (!isActive) return;
        setPageState({ status: 'Xác nhận thành công. Bạn sẽ được chuyển về trang chủ.', error: '' });
        redirectTimer = setTimeout(() => navigate('/'), 1200);
      })
      .catch((err: any) => {
        if (!isActive) return;
        setPageState({ error: getAuthErrorMessage(err.code, err.message || 'Không thể xác nhận tài khoản.'), status: '' });
      });

    return () => {
      isActive = false;
      if (redirectTimer) clearTimeout(redirectTimer);
    };
  }, [navigate, searchParams]);

  return (
    <div className="flex justify-center items-center py-10 px-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-primary mb-4">Xác nhận email</h1>
        {status && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{status}</div>}
        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-5 text-sm">{error}</div>}
        <Link to="/login" className="text-primary font-bold hover:underline">Quay lại đăng nhập</Link>
      </div>
    </div>
  );
}
