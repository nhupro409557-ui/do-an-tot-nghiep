import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { confirmPasswordResetByVerificationToken, getAuthErrorMessage, resetPasswordWithToken } from '../services/authDb';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const directToken = searchParams.get('token');
    if (directToken) {
      setResetToken(directToken);
      return;
    }

    const verificationToken = searchParams.get('verify');
    if (!verificationToken) return;

    confirmPasswordResetByVerificationToken(verificationToken)
      .then(setResetToken)
      .catch((err: any) => {
        setError(getAuthErrorMessage(err.code, err.message || 'Lien ket xac nhan khong hop le.'));
      });
  }, [searchParams]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');

    if (!resetToken) {
      setError('Ban can xac nhan bang ma hoac lien ket trong email truoc khi dat lai mat khau.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Mat khau nhap lai khong khop.');
      return;
    }

    setLoading(true);
    try {
      await resetPasswordWithToken(resetToken, password);
      setMessage('Da doi mat khau thanh cong. Ban co the dang nhap bang mat khau moi.');
      setTimeout(() => navigate('/login'), 1200);
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Khong the dat lai mat khau.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="mb-6 text-center text-2xl font-bold text-primary">Dat mat khau moi</h1>

        {message && <div className="mb-5 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div className="mb-5 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-2 block text-sm font-bold text-gray-700">Mat khau moi</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-bold text-gray-700">Nhap lai mat khau</label>
            <input
              type="password"
              required
              minLength={6}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !resetToken}
            className="w-full rounded-lg bg-primary py-3 font-bold text-white transition-colors hover:bg-red-700 disabled:opacity-70"
          >
            {loading ? 'Dang luu...' : 'Luu mat khau moi'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm">
          <Link to="/forgot-password" className="font-bold text-primary hover:underline">Gui lai ma xac nhan</Link>
        </div>
      </div>
    </div>
  );
}
