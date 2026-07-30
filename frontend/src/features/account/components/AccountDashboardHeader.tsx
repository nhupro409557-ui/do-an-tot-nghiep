import { useEffect, useState } from 'react';
import { Award, LogOut, Star } from 'lucide-react';

type AccountDashboardHeaderProps = {
  avatarUrl?: string;
  displayName?: string | null;
  email?: string | null;
  tier?: string | null;
  verificationRole?: string | null;
  points: number;
  nextTierInfo: {
    name: string;
    needed: number;
    percentage: number;
  };
  onSignOut: () => void;
};

export function AccountDashboardHeader({
  avatarUrl,
  displayName,
  email,
  tier,
  verificationRole,
  points,
  nextTierInfo,
  onSignOut,
}: AccountDashboardHeaderProps) {
  const [avatarFailed, setAvatarFailed] = useState(false);
  const avatarLetter = displayName?.charAt(0) || email?.charAt(0) || 'U';
  const currentTier = tier || 'S-New';

  useEffect(() => {
    setAvatarFailed(false);
  }, [avatarUrl]);

  return (
    <section className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm">
      <div className="absolute inset-x-0 top-0 h-1 bg-[#d70018]" />
      <div className="flex flex-col gap-6 p-5 sm:p-6 lg:flex-row lg:items-center lg:p-7">
        <div className="flex min-w-0 flex-1 items-center gap-4">
          {avatarUrl && !avatarFailed ? (
            <img
              src={avatarUrl}
              alt="Ảnh đại diện"
              onError={() => setAvatarFailed(true)}
              className="h-16 w-16 shrink-0 rounded-2xl border-2 border-white object-cover shadow-sm ring-1 ring-slate-200 sm:h-20 sm:w-20"
            />
          ) : (
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-red-50 text-2xl font-bold text-[#d70018] ring-1 ring-red-100 sm:h-20 sm:w-20">
              {avatarLetter.toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Tài khoản của tôi</p>
            <h1 className="truncate text-xl font-bold text-slate-900 sm:text-2xl">{displayName || 'Khách hàng'}</h1>
            <p className="mb-3 truncate text-sm text-slate-500" title={email || undefined}>{email}</p>
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-xs font-bold text-[#d70018] ring-1 ring-red-100"><Award className="h-3.5 w-3.5" />{currentTier}</span>
              {verificationRole && (
                <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 ring-1 ring-blue-100">
                  {verificationRole === 'student' ? 'Sinh viên' : 'Giảng viên'}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex-[1.4] lg:px-4">
          <div className="w-full rounded-2xl bg-slate-900 p-5 text-white shadow-sm ring-1 ring-slate-800">
            <div className="mb-2 flex items-start justify-between">
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-200">Hạng {currentTier}</span>
              <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />
            </div>
            <div className="mb-3 flex items-end gap-2">
              <p className="text-2xl font-bold leading-none">{points.toLocaleString('vi-VN')} <span className="text-sm font-normal opacity-70">Điểm</span></p>
            </div>
            <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-white/15">
              <div className="h-full rounded-full bg-yellow-400 transition-all duration-1000 ease-out" style={{ width: `${Math.min(100, Math.max(0, nextTierInfo.percentage))}%` }} />
            </div>
            <p className="text-[11px] font-medium opacity-80">
              {nextTierInfo.needed > 0 ? <>Còn <strong className="text-yellow-400">{nextTierInfo.needed.toLocaleString('vi-VN')}đ doanh số</strong> để lên hạng {nextTierInfo.name}</> : <span className="text-yellow-400">Bạn đã đạt hạng cao nhất!</span>}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 lg:justify-end">
          <button type="button" onClick={onSignOut} className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-[#d70018] focus:outline-none focus:ring-2 focus:ring-red-200 lg:w-auto">
            <LogOut className="h-4 w-4" /> Đăng xuất
          </button>
        </div>
      </div>
    </section>
  );
}
