import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { confirmRegistrationByToken, getAuthErrorMessage } from '../services/authDb';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('Đang xác nhận tài khoản...');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token') || '';
    if (!token) {
      setError('Link xác nhận không hợp lệ.');
      setStatus('');
      return;
    }

    confirmRegistrationByToken(token)
      .then(() => {
        setStatus('Xác nhận thành công. Bạn sẽ được chuyển về trang chủ.');
        setTimeout(() => navigate('/'), 1200);
      })
      .catch((err: any) => {
        setError(getAuthErrorMessage(err.code, err.message || 'Không thể xác nhận tài khoản.'));
        setStatus('');
      });
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
