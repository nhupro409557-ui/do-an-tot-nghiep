import { LogOut, Star } from 'lucide-react';

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
  const avatarLetter = displayName?.charAt(0) || email?.charAt(0) || 'U';
  const currentTier = tier || 'S-New';

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4 flex flex-col md:flex-row gap-6 md:items-center">
      <div className="flex gap-4 items-center flex-1 md:border-r border-gray-100 md:pr-6">
        {avatarUrl ? (
          <img src={avatarUrl} alt="Ảnh đại diện" className="w-16 h-16 rounded-full object-cover shrink-0 border border-gray-100" />
        ) : (
          <div className="w-16 h-16 bg-yellow-400 rounded-full flex items-center justify-center text-xl font-bold text-gray-800 shrink-0">
            {avatarLetter.toUpperCase()}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-bold text-gray-800 truncate">{displayName || 'Khách hàng'}</h2>
          <p className="text-sm text-gray-500 mb-1 truncate">{email}</p>
          <div className="flex flex-wrap gap-2">
            <span className="bg-[#d70018] text-white px-2 py-0.5 rounded text-xs font-bold leading-tight">{currentTier}</span>
            {verificationRole && (
              <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs font-bold leading-tight">
                {verificationRole === 'student' ? 'Sinh viên' : 'Giảng viên'}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex-[2] md:px-6">
        <div className="bg-gradient-to-br from-slate-900 to-slate-700 rounded-xl shadow-lg p-5 text-white w-full max-w-md">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] bg-yellow-500 text-slate-900 px-2 py-0.5 rounded-full font-bold">{currentTier}</span>
            <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
          </div>
          <div className="flex items-end gap-2 mb-3">
            <p className="text-2xl font-bold leading-none">{points.toLocaleString('vi-VN')} <span className="text-sm font-normal opacity-70">Điểm</span></p>
          </div>
          <div className="w-full bg-white/20 h-2 rounded-full mb-2 overflow-hidden shadow-inner">
            <div className="bg-yellow-400 h-full rounded-full transition-all duration-1000 ease-out" style={{ width: `${Math.min(100, Math.max(0, nextTierInfo.percentage))}%` }} />
          </div>
          <p className="text-[11px] opacity-80 font-medium">
            {nextTierInfo.needed > 0 ? <>Còn <strong className="text-yellow-400">{nextTierInfo.needed.toLocaleString('vi-VN')} điểm</strong> để lên hạng {nextTierInfo.name}</> : <span className="text-yellow-400">Bạn đã đạt hạng cao nhất!</span>}
          </p>
        </div>
      </div>

      <div className="flex-1 md:pl-6 md:border-l border-gray-100 flex justify-end">
        <button onClick={onSignOut} className="inline-flex items-center justify-center gap-2 text-sm font-medium text-red-600 hover:text-white hover:bg-red-600 border border-red-600 transition-colors px-4 py-2 rounded-lg w-full">
          <LogOut className="w-4 h-4" /> Đăng xuất
        </button>
      </div>
    </div>
  );
}
