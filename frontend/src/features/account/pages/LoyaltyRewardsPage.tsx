import React, { Suspense, lazy, useEffect, useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { publicApi } from '../../../services/publicApi';
import { deleteCurrentUser, getLoyaltyHistory, signOut, updateUserProfile } from '../../../services/authDb';
import { DeleteAccountModal } from '../components/DeleteAccountModal';

const LoyaltyBadge3D = lazy(() =>
  import('../../loyalty/components/LoyaltyBadge3D').then(module => ({ default: module.LoyaltyBadge3D })),
);

function getNextTierInfo(amount: number) {
  if (amount < 30_000_000) {
    return { nextTier: 'SILVER', needed: 30_000_000 - amount, percentage: (amount / 30_000_000) * 100 };
  }
  if (amount < 80_000_000) {
    return { nextTier: 'GOLD', needed: 80_000_000 - amount, percentage: ((amount - 30_000_000) / 50_000_000) * 100 };
  }
  if (amount < 150_000_000) {
    return { nextTier: 'DIAMOND', needed: 150_000_000 - amount, percentage: ((amount - 80_000_000) / 70_000_000) * 100 };
  }
  return { nextTier: 'Tối đa', needed: 0, percentage: 100 };
}

function getTierGradient(tier: string) {
  switch (tier) {
    case 'SILVER': case 'S-Mem': return 'from-gray-300 to-gray-500 text-gray-900';
    case 'GOLD': return 'from-amber-300 to-yellow-600 text-gray-900';
    case 'DIAMOND': case 'S-Vip': return 'from-gray-800 to-black text-white border border-gray-700';
    case 'S-New':
    default: return 'from-yellow-400 to-yellow-600 text-white';
  }
}

function getTierDisplayName(tier: string) {
  switch (tier) {
    case 'DIAMOND': case 'S-Vip': return 'KIM CƯƠNG';
    case 'GOLD': return 'VÀNG';
    case 'SILVER': case 'S-Mem': return 'BẠC';
    case 'MEMBER': return 'THÀNH VIÊN';
    case 'S-New':
    default: return 'NEW';
  }
}

export default function LoyaltyRewardsPage() {
  const { user, userData } = useAuth();
  const navigate = useNavigate();

  // Dùng data thật từ AuthContext.
  const currentPoints = userData?.points ?? 0;
  const currentTier = userData?.tier ?? 'S-New';
  const displayName = user?.displayName || user?.email?.split('@')[0] || 'Khách hàng';

  const periodSpendAmount = userData?.tierPeriodSpendAmount ?? 0;
  const nextTierInfo = getNextTierInfo(periodSpendAmount);
  const nearestExpirationDate = userData?.nearestPointsExpirationAt
    ? new Intl.DateTimeFormat('vi-VN').format(new Date(new Date(userData.nearestPointsExpirationAt).getTime() - 24 * 60 * 60 * 1000))
    : null;

  const [rewardsStore, setRewardsStore] = useState<any[]>([]);
  const [loyaltyHistory, setLoyaltyHistory] = useState<any[]>([]);
  const [historyFilter, setHistoryFilter] = useState('ALL');

  useEffect(() => {
    publicApi.listRewards()
      .then(rewards => setRewardsStore(rewards.sort((a:any, b:any) => (a.cost || 0) - (b.cost || 0))))
      .catch(() => setRewardsStore([]));
    getLoyaltyHistory().then(setLoyaltyHistory).catch(() => setLoyaltyHistory([]));
  }, []);

  // State quản lý Modal xóa tài khoản
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAccount = async () => {
    if (!user) return;
    setIsDeleting(true);
    try {
      updateUserProfile(user.uid, { points: 0, tier: 'S-New' });
      await deleteCurrentUser();
      navigate('/');
    } catch (error: any) {
      console.error(error);
      if (error.code === 'auth/requires-recent-login') {
        alert("Vui lòng đăng nhập lại trước khi xóa tài khoản.");
        await signOut();
      } else {
        alert("Có lỗi xảy ra khi xóa tài khoản.");
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6 font-display">Smember - Khách hàng thân thiết</h1>

      {/* 1. Thẻ thành viên điện tử (Digital Member Card) */}
      <div className={`rounded-2xl p-6 shadow-2xl bg-gradient-to-br ${getTierGradient(currentTier)} mb-8 relative overflow-hidden perspective-1000`}>
        {/* Họa tiết trang trí thẻ */}
        <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-white opacity-10"></div>
        <div className="absolute bottom-0 right-10 -mb-8 w-24 h-24 rounded-full bg-white opacity-10"></div>

        <div className="flex justify-between items-start relative z-10">
          <div>
            <p className="text-sm opacity-80 mb-1">Thành viên</p>
            <p className="text-xl font-bold uppercase tracking-wider font-display">{displayName}</p>
          </div>
          <div className="text-right flex flex-col items-end">
            <p className="text-sm opacity-80 mb-1">Hạng hiện tại</p>
            <div className="absolute inset-0 bg-blue-400 opacity-20 blur-3xl rounded-full"></div>
            <Suspense fallback={<div className="h-[120px] w-[120px]" />}>
              <LoyaltyBadge3D tier={currentTier as any} size={120} />
            </Suspense>
            <p className="text-xl font-black uppercase italic tracking-widest relative z-10">{getTierDisplayName(currentTier)}</p>
          </div>
        </div>

        <div className="mt-8 relative z-10">
          <p className="text-3xl font-bold font-mono">{currentPoints.toLocaleString()} <span className="text-sm font-normal opacity-80 font-sans">Điểm</span></p>
        </div>
      </div>

      {nearestExpirationDate && (userData?.nearestPointsExpirationAmount || 0) > 0 && (
        <div className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>{(userData?.nearestPointsExpirationAmount || 0).toLocaleString('vi-VN')} / {currentPoints.toLocaleString('vi-VN')} điểm</strong>{' '}
          sẽ hết hạn vào cuối ngày <strong>{nearestExpirationDate}</strong>.
        </div>
      )}

      {/* 2. Thanh tiến trình lên hạng (Progress Bar) */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-8">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Hạng {getTierDisplayName(currentTier)}</span>
          <span>Hạng {nextTierInfo.nextTier === 'Tối đa' ? 'Tối đa' : getTierDisplayName(nextTierInfo.nextTier)}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2 overflow-hidden">
          <div className="bg-primary h-2.5 rounded-full transition-all duration-1000" style={{ width: `${Math.min(100, Math.max(0, nextTierInfo.percentage))}%` }}></div>
        </div>
        <p className="text-sm text-gray-500 text-center mt-3">
          {nextTierInfo.needed > 0 ? (
            <>Mua thêm <strong className="text-primary">{nextTierInfo.needed.toLocaleString('vi-VN')}đ</strong> trong kỳ để thăng hạng {getTierDisplayName(nextTierInfo.nextTier)}.</>
          ) : (
            <span className="text-primary font-bold">Bạn đã đạt hạng cao nhất!</span>
          )}
        </p>
      </div>

      <div className="mb-8 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-xl font-bold text-gray-800">Lịch sử điểm</h2>
          <select value={historyFilter} onChange={event => setHistoryFilter(event.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm">
            <option value="ALL">Tất cả</option><option value="EARN">Tích điểm</option><option value="REDEEM">Dùng điểm</option><option value="REFUND">Hoàn điểm</option><option value="REVOKE">Thu hồi</option><option value="EXPIRE">Hết hạn</option>
          </select>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead><tr className="border-b text-gray-500"><th className="p-3">Thời gian</th><th>Loại</th><th>Điểm</th><th>Số dư sau</th><th>Lý do</th></tr></thead>
            <tbody>{loyaltyHistory.filter(item => historyFilter === 'ALL' || item.type === historyFilter).map(item => {
              const positive = ['EARN', 'REFUND'].includes(item.type) || (item.type === 'ADJUST' && Number(item.metadata?.delta || 0) > 0);
              const labels: Record<string, string> = { EARN: 'Tích điểm', REDEEM: 'Dùng điểm', REFUND: 'Hoàn điểm', REVOKE: 'Thu hồi', EXPIRE: 'Hết hạn', ADJUST: 'Điều chỉnh' };
              return <tr key={item.id} className="border-b last:border-0"><td className="p-3">{new Date(item.createdAt).toLocaleString('vi-VN')}</td><td>{labels[item.type] || item.type}</td><td className={positive ? 'font-bold text-emerald-600' : 'font-bold text-red-600'}>{positive ? '+' : '-'}{Number(item.points).toLocaleString('vi-VN')}</td><td>{Number(item.balanceAfter).toLocaleString('vi-VN')}</td><td>{item.reason}</td></tr>;
            })}</tbody>
          </table>
        </div>
      </div>

      {/* 3. Cửa hàng đổi thưởng (Redemption Store) */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">🎁 Cửa hàng ưu đãi</h2>
          <span className="text-sm text-blue-600 cursor-pointer hover:underline">Lịch sử đổi điểm</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rewardsStore.length === 0 && (
            <div className="md:col-span-2 text-center py-10 text-gray-400 bg-white rounded-xl border border-gray-100">
              Chưa có ưu đãi thật để hiển thị.
            </div>
          )}
          {rewardsStore.map((reward) => {
            const isLocked = currentPoints < reward.cost;
            return (
              <div key={reward.id} className={`flex border rounded-xl overflow-hidden transition-all ${isLocked ? 'bg-gray-50 border-gray-200 grayscale opacity-75' : 'bg-white border-red-100 hover:shadow-md'}`}>
                {/* Phần icon/hình ảnh bên trái */}
                <div className={`w-24 flex flex-col items-center justify-center text-white p-2 ${isLocked ? 'bg-gray-400' : 'bg-primary'}`}>
                  <span className="text-2xl mb-1">{reward.type === 'shipping' ? '🚚' : reward.type === 'event' ? '🎟️' : '🎫'}</span>
                  <span className="text-xs text-center font-semibold">VOUCHER</span>
                </div>

                {/* Phần thông tin bên phải */}
                <div className="p-3 flex-1 flex flex-col justify-between relative">
                  <div>
                    <h3 className={`font-bold text-sm ${isLocked ? 'text-gray-600' : 'text-gray-800'}`}>{reward.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{reward.description}</p>
                  </div>

                  <div className="flex items-center justify-between mt-3">
                    <span className={`font-bold text-sm ${isLocked ? 'text-gray-500' : 'text-primary'}`}>
                      {reward.cost} điểm
                    </span>
                    {isLocked ? (
                      <button type="button" className="flex items-center gap-1 text-xs bg-gray-200 text-gray-600 px-3 py-1 rounded-full cursor-not-allowed">
                        🔒 Thiếu {reward.cost - currentPoints} điểm
                      </button>
                    ) : (
                      <button type="button" className="text-xs bg-red-100 text-primary font-bold px-4 py-1 rounded-full hover:bg-primary hover:text-white transition-colors">
                        Đổi ngay
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 4. Quản lý tài khoản & Cảnh báo bảo mật */}
      <div className="mt-12 pt-6 border-t border-gray-200">
        <h3 className="text-lg font-bold text-gray-800 mb-4">Cài đặt tài khoản</h3>
        <button type="button"
          onClick={() => setShowDeleteModal(true)}
          className="text-red-600 border border-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
        >
          Yêu cầu xóa tài khoản
        </button>
      </div>

      {/* Modal xác nhận xóa tài khoản - dùng component có logic xử lý */}
      <DeleteAccountModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
        currentLoyaltyPoints={currentPoints}
        isDeleting={isDeleting}
      />
    </div>
  );
}
