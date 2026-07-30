import { BadgePercent, Bell, ClipboardList, CreditCard, Diamond, Heart, Home, MapPin, RotateCcw, Settings, ShieldCheck, Smartphone } from 'lucide-react';
import type { AccountTab } from '../types/accountDashboardTypes';

export const accountNavItems = [
  { id: 'overview', label: 'Tổng quan', icon: Home },
  { id: 'orders', label: 'Lịch sử mua hàng', icon: ClipboardList },
  { id: 'returns', label: 'Đổi trả', icon: RotateCcw },
  { id: 'warranties', label: 'Bảo hành', icon: ShieldCheck },
  { id: 'vouchers', label: 'Ví voucher', icon: BadgePercent },
  { id: 'transactions', label: 'Thanh toán & hoàn tiền', icon: CreditCard },
  { id: 'notifications', label: 'Thông báo', icon: Bell },
  { id: 'favorites', label: 'Sản phẩm yêu thích', icon: Heart },
  { id: 'buyback', label: 'Thu cũ đổi mới', icon: Smartphone },
  { id: 'membership', label: 'Hạng thành viên', icon: Diamond },
  { id: 'addresses', label: 'Địa chỉ', icon: MapPin },
  { id: 'settings', label: 'Cài đặt tài khoản', icon: Settings },
] as const satisfies ReadonlyArray<{
  id: AccountTab;
  label: string;
  icon: typeof Home;
}>;

export function getNextTierInfo(amount: number) {
  if (amount < 30_000_000) {
    return { name: 'Bạc', needed: 30_000_000 - amount, percentage: (amount / 30_000_000) * 100 };
  }
  if (amount < 80_000_000) {
    return { name: 'Vàng', needed: 80_000_000 - amount, percentage: ((amount - 30_000_000) / 50_000_000) * 100 };
  }
  if (amount < 150_000_000) {
    return { name: 'Kim cương', needed: 150_000_000 - amount, percentage: ((amount - 80_000_000) / 70_000_000) * 100 };
  }
  return { name: 'Tối đa', needed: 0, percentage: 100 };
}
