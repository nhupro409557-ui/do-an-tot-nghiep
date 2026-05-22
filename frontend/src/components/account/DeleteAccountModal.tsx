import React, { useState } from 'react';
import { AlertTriangle, Trash2, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { signOut } from '../../services/authDb';

interface DeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  currentLoyaltyPoints: number; // Điểm hiện tại của user
  isDeleting: boolean;
}

export function DeleteAccountModal({ isOpen, onClose, onConfirm, currentLoyaltyPoints, isDeleting }: DeleteAccountModalProps) {
  const [confirmText, setConfirmText] = useState('');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl animate-in zoom-in-95">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4 mx-auto">
          <AlertTriangle className="w-8 h-8 text-red-600" />
        </div>
        
        <h3 className="text-xl font-bold text-center text-gray-900 mb-2 font-display">Yêu cầu xóa tài khoản</h3>
        
        <div className="bg-red-50 text-red-800 p-4 rounded-lg mb-6 text-sm border border-red-100">
          <p className="font-bold mb-1">CẢNH BÁO QUAN TRỌNG:</p>
          <p className="mb-2 text-[#b91c1c]">Hành động này không thể hoàn tác. Toàn bộ lịch sử mua hàng và thông tin cá nhân sẽ bị xóa vĩnh viễn.</p>
          <p className="font-bold border-t border-red-200/60 pt-3 mt-3 text-red-700">
            Hệ thống sẽ tiến hành tạo giao dịch REVOKE để thu hồi toàn bộ <span className="text-xl">{currentLoyaltyPoints.toLocaleString()}</span> điểm Loyalty hiện còn trong ví của bạn.
          </p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Nhập chữ <strong className="text-red-600 font-mono text-base bg-red-50 px-1 rounded">XOA</strong> để xác nhận:
          </label>
          <input 
            type="text" 
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none text-center font-mono text-lg font-bold tracking-widest uppercase"
            placeholder="XOA"
            disabled={isDeleting}
          />
        </div>

        <div className="flex gap-3">
          <button 
            onClick={onClose}
            className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-700 font-bold rounded-lg hover:bg-gray-200 transition"
            disabled={isDeleting}
          >
            Hủy bỏ
          </button>
          <button 
            onClick={onConfirm}
            disabled={confirmText !== 'XOA' || isDeleting}
            className="flex-1 px-4 py-2.5 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isDeleting ? 'Đang xóa...' : 'Xác nhận xóa'}
          </button>
        </div>
      </div>
    </div>
  );
}
