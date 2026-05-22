import React from 'react';
import { Home, LayoutGrid, PlaySquare, Trophy, User } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';

export const BottomNav = () => {
  const { totalQuantity } = useCart();
  const { user } = useAuth();
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/' && location.pathname !== '/') return false;
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { path: '/', icon: <Home className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Trang chủ' },
    { path: '/category', icon: <LayoutGrid className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Danh mục' },
    { path: '/video', icon: <PlaySquare className="w-6 h-6 mb-1 fill-primary/10" strokeWidth={1.5} />, label: 'Video' },
    { path: '/rankings', icon: <Trophy className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Xếp hạng' },
    { path: user ? '/dashboard' : '/login', icon: <User className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Tài khoản' },
  ];

  return (
    // Hiển thị trên màn hình nhỏ và vừa (mobile, tablet), ẩn trên desktop (lg)
    <div className="sticky bottom-0 w-full bg-white border-t border-gray-200 flex justify-around items-center px-1 pb-safe pt-2 lg:hidden z-50 shadow-[0_-4px_10px_rgba(0,0,0,0.03)]">
      {navItems.map((item) => {
        const active = isActive(item.path.split('/')[1] ? `/${item.path.split('/')[1]}` : '/'); // roughly match
        return (
          <Link 
            key={item.label} 
            to={item.path}
            className={`flex flex-col items-center flex-1 p-1 ${active ? 'text-primary' : 'text-gray-500 hover:text-primary transition-colors'}`}
          >
            {item.icon}
            <span className={`text-[10px] whitespace-nowrap ${active ? 'font-bold' : 'font-medium'}`}>
              {item.label}
            </span>
          </Link>
        );
      })}
    </div>
  );
};
