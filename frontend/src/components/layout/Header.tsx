import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  ChevronDown,
  Image as ImageIcon,
  Menu,
  PackageSearch,
  ShoppingCart,
  Trophy,
  User as UserIcon,
  Video,
} from 'lucide-react';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { NotificationDropdown } from './NotificationDropdown';
import { SearchBar } from './SearchBar';
import { CategoryMegaMenu } from './CategoryMegaMenu';
import emvLogo from '../../assets/emv-logo-new.svg';

export const Header = () => {
  const { totalQuantity } = useCart();
  const { user } = useAuth();
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-primary text-white shadow-md">
      <div className="mx-auto max-w-7xl px-3 sm:px-4 lg:px-6">
        <div className="flex min-h-16 items-center gap-3">
          <Link to="/" className="flex shrink-0 items-center" aria-label="ElectroMart Vietnam">
            <img
              src={emvLogo}
              alt="ElectroMart Vietnam"
              className="h-11 w-[112px] object-contain sm:h-12 sm:w-[128px]"
            />
          </Link>

          <div className="relative hidden md:block">
            <button
              type="button"
              onClick={() => setIsCategoryOpen((value) => !value)}
              className={`flex h-10 items-center gap-2 rounded-xl border border-white/20 px-4 text-sm font-semibold transition ${isCategoryOpen ? 'bg-white/20 shadow-inner' : 'hover:bg-white/10'}`}
              aria-expanded={isCategoryOpen}
            >
              <Menu className="h-5 w-5" />
              <span className="whitespace-nowrap">Danh mục</span>
              <ChevronDown className={`h-4 w-4 transition ${isCategoryOpen ? 'rotate-180' : ''}`} />
            </button>

            {isCategoryOpen && (
              <div className="fixed inset-x-0 top-16 z-40">
                <button
                  type="button"
                  className="absolute inset-0 min-h-screen bg-black/45 backdrop-blur-[2px]"
                  aria-label="Đóng danh mục"
                  onClick={() => setIsCategoryOpen(false)}
                />
                <div className="relative mx-auto max-w-7xl px-3 pt-3 text-slate-800 sm:px-4 lg:px-6">
                  <CategoryMegaMenu compact onNavigate={() => setIsCategoryOpen(false)} />
                </div>
              </div>
            )}
          </div>

          <Link
            to="/video"
            title="Video"
            aria-label="Video"
            className="hidden h-10 items-center gap-2 rounded-md px-2 text-sm font-semibold transition hover:bg-white/10 lg:flex xl:px-3"
          >
            <Video className="h-5 w-5" />
            <span className="hidden whitespace-nowrap xl:inline">Video</span>
          </Link>

          <Link
            to="/images"
            title="Hình ảnh"
            aria-label="Hình ảnh"
            className="hidden h-10 items-center gap-2 rounded-md px-2 text-sm font-semibold transition hover:bg-white/10 lg:flex xl:px-3"
          >
            <ImageIcon className="h-5 w-5" />
            <span className="hidden whitespace-nowrap xl:inline">Hình ảnh</span>
          </Link>

          <Link
            to="/rankings"
            title="Xếp hạng"
            aria-label="Xếp hạng"
            className="hidden h-10 items-center gap-2 rounded-md px-2 text-sm font-semibold transition hover:bg-white/10 lg:flex xl:px-3"
          >
            <Trophy className="h-5 w-5" />
            <span className="hidden whitespace-nowrap xl:inline">Xếp hạng</span>
          </Link>

          <SearchBar />

          <Link
            to="/dashboard"
            title="Đơn hàng"
            aria-label="Đơn hàng"
            className="hidden h-10 shrink-0 items-center gap-2 rounded-md px-2 text-sm font-semibold transition hover:bg-white/10 lg:flex xl:px-3"
          >
            <PackageSearch className="h-5 w-5" />
            <span className="hidden whitespace-nowrap xl:inline">Đơn hàng</span>
          </Link>

          <div className="shrink-0">
            <NotificationDropdown />
          </div>

          <Link to="/cart" className="relative flex shrink-0 flex-col items-center p-1 hover:text-white/85">
            <ShoppingCart className="h-6 w-6" />
            <span className="hidden text-xs lg:block">Giỏ hàng</span>
            {totalQuantity > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-yellow-400 text-[10px] font-bold text-black">
                {totalQuantity}
              </span>
            )}
          </Link>

          <Link
            to={user ? '/dashboard' : '/login'}
            className="flex shrink-0 flex-col items-center p-1 hover:text-white/85"
          >
            <UserIcon className="h-6 w-6" />
            <span className="hidden text-xs lg:block">Tài khoản</span>
          </Link>

          <Bell className="hidden" aria-hidden="true" />
        </div>
      </div>
    </header>
  );
};
