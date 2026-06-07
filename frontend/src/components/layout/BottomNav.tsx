import React, { useEffect, useRef } from 'react';
import { Home, Image as ImageIcon, LayoutGrid, PlaySquare, Trophy, User } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';

export const BottomNav = () => {
  const { totalQuantity } = useCart();
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const lastNonCategoryPathRef = useRef('/');
  const isCategoryPath = location.pathname.startsWith('/category');

  useEffect(() => {
    if (!isCategoryPath) {
      lastNonCategoryPathRef.current = `${location.pathname}${location.search}${location.hash}`;
    }
  }, [isCategoryPath, location.hash, location.pathname, location.search]);

  const isActive = (path: string) => {
    if (path === '/' && location.pathname !== '/') return false;
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { path: '/', icon: <Home className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Trang chủ' },
    { path: '/category', icon: <LayoutGrid className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Danh mục' },
    { path: '/video', icon: <PlaySquare className="w-6 h-6 mb-1 fill-primary/10" strokeWidth={1.5} />, label: 'Video' },
    { path: '/images', icon: <ImageIcon className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Hình ảnh' },
    { path: '/rankings', icon: <Trophy className="w-6 h-6 mb-1" strokeWidth={1.5} />, label: 'Xếp hạng' },
    {
      path: user ? '/dashboard' : '/login',
      icon: (
        <div className="relative">
          <User className="w-6 h-6 mb-1" strokeWidth={1.5} />
          {user && (
            <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </span>
          )}
        </div>
      ),
      label: user ? (user.displayName || 'Tài khoản') : 'Tài khoản',
    },
  ];

  const handleNavClick = (event: React.MouseEvent<HTMLAnchorElement>, path: string) => {
    if (path !== '/category' || !isCategoryPath) return;

    event.preventDefault();
    navigate(lastNonCategoryPathRef.current || '/');
  };

  return (
    <div className="sticky bottom-0 z-50 flex w-full items-center justify-around border-t border-gray-200 bg-white px-1 pb-safe pt-2 shadow-[0_-4px_10px_rgba(0,0,0,0.03)] lg:hidden">
      {navItems.map((item) => {
        const active = isActive(item.path.split('/')[1] ? `/${item.path.split('/')[1]}` : '/');

        return (
          <Link
            key={item.label}
            to={item.path}
            onClick={(event) => handleNavClick(event, item.path)}
            className={`flex flex-1 flex-col items-center p-1 ${active ? 'text-primary' : 'text-gray-500 transition-colors hover:text-primary'}`}
          >
            {item.icon}
            <span className={`whitespace-nowrap text-[10px] ${active ? 'font-bold' : 'font-medium'}`}>
              {item.label}
            </span>
          </Link>
        );
      })}
    </div>
  );
};
