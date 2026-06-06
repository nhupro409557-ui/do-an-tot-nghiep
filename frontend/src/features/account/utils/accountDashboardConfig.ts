import { ClipboardList, Diamond, Heart, Home, MapPin, Settings } from 'lucide-react';
import type { AccountTab } from '../types/accountDashboardTypes';

export const accountNavItems = [
  { id: 'overview', label: 'Tổng quan', icon: Home },
  { id: 'orders', label: 'Lịch sử mua hàng', icon: ClipboardList },
  { id: 'favorites', label: 'Sản phẩm yêu thích', icon: Heart },
  { id: 'membership', label: 'Hạng thành viên', icon: Diamond },
  { id: 'addresses', label: 'Địa chỉ', icon: MapPin },
  { id: 'settings', label: 'Cài đặt tài khoản', icon: Settings },
] as const satisfies ReadonlyArray<{
  id: AccountTab;
  label: string;
  icon: typeof Home;
}>;

export function getNextTierInfo(points: number) {
  if (points < 3000) {
    return { name: 'S-Mem', needed: 3000 - points, percentage: (points / 3000) * 100 };
  }
  if (points < 15000) {
    return { name: 'S-Vip', needed: 15000 - points, percentage: ((points - 3000) / 12000) * 100 };
  }
  return { name: 'Tối đa', needed: 0, percentage: 100 };
}
