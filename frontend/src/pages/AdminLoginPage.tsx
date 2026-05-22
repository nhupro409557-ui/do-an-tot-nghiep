import React, { useEffect, useState } from 'react';
import { ArrowLeft, KeyRound, LockKeyhole, ShieldCheck, Store, UserRoundCog } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { adminSignInWithEmailAndPassword, getAuthErrorMessage, verifyAdminMfa } from '../services/authDb';
import { useAuth } from '../context/AuthContext';

type MfaChallenge = {
  requiresMfa?: boolean;
  requiresMfaSetup?: boolean;
  tempToken: string;
  mfaSecret?: string;
  otpauthUrl?: string;
};

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const { user, canAccessAdmin, loading: authLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && user && canAccessAdmin) {
      navigate('/admin', { replace: true });
    }
  }, [authLoading, canAccessAdmin, navigate, user]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await adminSignInWithEmailAndPassword(email.trim(), password);
      if (result?.requiresMfa || result?.requiresMfaSetup) {
        setChallenge(result);
        setOtpCode('');
        return;
      }
      navigate('/admin', { replace: true });
    } catch (err: any) {
      setError(getAuthErrorMessage(err.code, err.message || 'Đăng nhập admin thất bại. Vui lòng kiểm tra email và mật khẩu.'));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyMfa(event: React.FormEvent) {
    event.preventDefault();
    if (!challenge) return;
    setError('');
    setLoading(true);
    try {
      await verifyAdminMfa(challenge.tempToken, otpCode);
      navigate('/admin', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Mã xác thực không hợp lệ.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-140px)] w-full max-w-6xl items-center justify-center py-8">
      <div className="grid w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg lg:grid-cols-[0.95fr_1.05fr]">
        <section className="hidden bg-gradient-to-br from-red-700 via-red-600 to-rose-500 p-10 text-white lg:block">
          <div className="inline-flex items-center gap-2 rounded-md bg-white/20 px-3 py-2 text-sm font-bold shadow-sm backdrop-blur-sm">
            <ShieldCheck className="h-4 w-4 text-white" />
            Khu vực quản trị
          </div>
          <h1 className="mt-8 text-3xl font-bold text-white">Đăng nhập Admin Console</h1>
          <p className="mt-3 max-w-md text-sm leading-6 text-red-50">
            Truy cập bảng điều khiển để quản lý sản phẩm, đơn hàng, voucher, tồn kho và dữ liệu vận hành.
          </p>
          <div className="mt-10 space-y-4">
            {[
              ['MFA bắt buộc', 'Tài khoản quản trị phải xác thực mã OTP sau bước mật khẩu.'],
              ['Phân quyền chi tiết', 'Mỗi tab và thao tác được kiểm soát bằng permission.'],
              ['Nhật ký bảo mật', 'Các thao tác thay đổi dữ liệu được ghi log để truy vết.'],
            ].map(([title, description]) => (
              <div key={title} className="flex gap-3 rounded-lg border border-white/20 bg-white/10 p-4 shadow-sm backdrop-blur-sm transition-colors hover:bg-white/20">
                <Store className="mt-0.5 h-5 w-5 shrink-0 text-white" />
                <div>
                  <div className="font-semibold text-white">{title}</div>
                  <div className="mt-1 text-sm text-red-50">{description}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="p-6 sm:p-10">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-red-50 text-red-600 ring-1 ring-red-100">
              {challenge ? <KeyRound className="h-6 w-6" /> : <UserRoundCog className="h-6 w-6" />}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900">{challenge ? 'Xác thực MFA' : 'Đăng nhập quản trị'}</h2>
              <p className="text-sm text-slate-500">
                {challenge?.requiresMfaSetup ? 'Quét hoặc nhập secret vào Google Authenticator/Authy rồi nhập mã OTP.' : challenge ? 'Nhập mã OTP từ ứng dụng xác thực.' : 'Chỉ tài khoản có quyền admin mới truy cập được trang này.'}
              </p>
            </div>
          </div>

          {error && <div className="mb-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div>}

          {!challenge ? (
            <form onSubmit={handleSubmit} className="space-y-5">
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">Email admin</span>
                <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="admin@company.vn" className="h-12 w-full rounded-md border border-slate-200 px-4 text-sm outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">Mật khẩu</span>
                <div className="relative">
                  <LockKeyhole className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-red-500" />
                  <input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Nhập mật khẩu admin" className="h-12 w-full rounded-md border border-red-200 bg-red-50 pl-11 pr-4 text-sm text-red-900 outline-none transition placeholder:text-red-300 focus:border-red-500 focus:bg-white focus:ring-2 focus:ring-red-100" />
                </div>
              </label>
              <button type="submit" disabled={loading} className="flex h-12 w-full items-center justify-center rounded-md bg-red-600 px-4 text-sm font-bold text-white shadow-md shadow-red-200/50 transition hover:bg-red-700 disabled:opacity-70">
                {loading ? 'Đang kiểm tra quyền...' : 'Tiếp tục'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyMfa} className="space-y-5">
              {challenge.requiresMfaSetup && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                  <div className="text-sm font-bold text-slate-800">Secret MFA</div>
                  <div className="mt-2 break-all rounded-md bg-white px-3 py-2 font-mono text-sm text-slate-700">{challenge.mfaSecret}</div>
                  {challenge.otpauthUrl && <div className="mt-2 break-all text-xs text-slate-500">{challenge.otpauthUrl}</div>}
                </div>
              )}
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">Mã OTP</span>
                <input inputMode="numeric" pattern="[0-9]*" required value={otpCode} onChange={(event) => setOtpCode(event.target.value)} placeholder="123456" className="h-12 w-full rounded-md border border-slate-200 px-4 text-center font-mono text-lg tracking-[0.35em] outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" />
              </label>
              <button type="submit" disabled={loading} className="flex h-12 w-full items-center justify-center rounded-md bg-red-600 px-4 text-sm font-bold text-white shadow-md shadow-red-200/50 transition hover:bg-red-700 disabled:opacity-70">
                {loading ? 'Đang xác thực...' : 'Xác thực và vào Admin'}
              </button>
              <button type="button" onClick={() => setChallenge(null)} className="h-11 w-full rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700">
                Quay lại đăng nhập
              </button>
            </form>
          )}

          <div className="mt-6 flex flex-col gap-2 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <Link to="/login" className="font-semibold text-red-600 transition-colors hover:text-red-700">Đăng nhập tài khoản khách hàng</Link>
            <Link to="/" className="inline-flex items-center gap-1.5 font-semibold text-slate-600 transition-colors hover:text-red-600">
              <ArrowLeft className="h-4 w-4" />
              Quay về trang chủ
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
