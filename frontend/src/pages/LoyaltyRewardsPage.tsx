import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { LoyaltyBadge3D } from '../components/loyalty/LoyaltyBadge3D';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { apiDb } from '../services/apiDb';
import { deleteCurrentUser, signOut, updateUserProfile } from '../services/authDb';
import { DeleteAccountModal } from '../components/account/DeleteAccountModal';

export default function LoyaltyRewardsPage() {
  const { user, userData } = useAuth();
  const navigate = useNavigate();

  // Dùng data thật từ AuthContext.
  const currentPoints = userData?.points ?? 0;
  const currentTier = userData?.tier ?? 'S-New';
  const displayName = user?.displayName || user?.email?.split('@')[0] || 'Khách hàng';

  // Tính toán tier tiếp theo dựa trên điểm thực tế
  const getNextTierInfo = (points: number) => {
    if (points < 3000) {
      return { nextTier: 'S-Mem', needed: 3000 - points, percentage: (points / 3000) * 100 };
    } else if (points < 15000) {
      return { nextTier: 'S-Vip', needed: 15000 - points, percentage: ((points - 3000) / 12000) * 100 };
    } else {
      return { nextTier: 'Tối đa', needed: 0, percentage: 100 };
    }
  };

  const nextTierInfo = getNextTierInfo(currentPoints);

  const [rewardsStore, setRewardsStore] = useState<any[]>([]);

  useEffect(() => {
    apiDb.listRewards()
      .then(rewards => setRewardsStore(rewards.sort((a:any, b:any) => (a.cost || 0) - (b.cost || 0))))
      .catch(() => setRewardsStore([]));
  }, []);

  // State quản lý Modal xóa tài khoản
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Chọn màu gradient cho thẻ tùy theo hạng
  const getTierGradient = (tier: string) => {
    switch(tier) {
      case 'S-Mem': return 'from-gray-300 to-gray-500 text-gray-900';
      case 'S-Vip': return 'from-gray-800 to-black text-white border border-gray-700';
      case 'S-New':
      default: return 'from-yellow-400 to-yellow-600 text-white';
    }
  };

  // Map tier display name
  const getTierDisplayName = (tier: string) => {
    switch(tier) {
      case 'S-Vip': return 'VIP';
      case 'S-Mem': return 'MEMBER';
      case 'S-New':
      default: return 'NEW';
    }
  };

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
            <LoyaltyBadge3D tier={currentTier as any} size={120} />
            <p className="text-xl font-black uppercase italic tracking-widest relative z-10">{getTierDisplayName(currentTier)}</p>
          </div>
        </div>

        <div className="mt-8 relative z-10">
          <p className="text-3xl font-bold font-mono">{currentPoints.toLocaleString()} <span className="text-sm font-normal opacity-80 font-sans">Điểm</span></p>
        </div>
      </div>

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
            <>Mua thêm <strong className="text-primary">{(nextTierInfo.needed * 100).toLocaleString()}đ</strong> để nhận {nextTierInfo.needed} điểm và thăng hạng {nextTierInfo.nextTier}.</>
          ) : (
            <span className="text-primary font-bold">Bạn đã đạt hạng cao nhất!</span>
          )}
        </p>
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
                      <button className="flex items-center gap-1 text-xs bg-gray-200 text-gray-600 px-3 py-1 rounded-full cursor-not-allowed">
                        🔒 Thiếu {reward.cost - currentPoints} điểm
                      </button>
                    ) : (
                      <button className="text-xs bg-red-100 text-primary font-bold px-4 py-1 rounded-full hover:bg-primary hover:text-white transition-colors">
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
        <button 
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
