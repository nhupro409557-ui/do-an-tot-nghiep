import React, { useEffect, useRef } from 'react';
import { Home, LayoutGrid, PlaySquare, ShoppingCart, User } from 'lucide-react';
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
  const currentPath = `${location.pathname}${location.search}${location.hash}`;

  useEffect(() => {
    if (!isCategoryPath) {
      lastNonCategoryPathRef.current = currentPath;
    }
  }, [currentPath, isCategoryPath]);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    if (path === '/category') return isCategoryPath;
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { path: '/', icon: <Home className="mb-1 h-5 w-5" strokeWidth={1.8} />, label: 'Trang chủ' },
    { path: '/category', icon: <LayoutGrid className="mb-1 h-5 w-5" strokeWidth={1.8} />, label: 'Danh mục' },
    { path: '/video', icon: <PlaySquare className="mb-1 h-5 w-5" strokeWidth={1.8} />, label: 'Video' },
    {
      path: '/cart',
      icon: (
        <div className="relative mb-1">
          <ShoppingCart className="h-5 w-5" strokeWidth={1.8} />
          {totalQuantity > 0 && (
            <span className="absolute -right-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold leading-none text-white">
              {totalQuantity > 99 ? '99+' : totalQuantity}
            </span>
          )}
        </div>
      ),
      label: 'Giỏ hàng',
    },
    {
      path: user ? '/dashboard' : '/login',
      icon: (
        <div className="relative mb-1">
          <User className="h-5 w-5" strokeWidth={1.8} />
          {user && (
            <span className="absolute -right-1 -top-1 flex h-2.5 w-2.5">
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
    <nav className="sticky bottom-0 z-50 flex w-full items-center justify-around border-t border-slate-200 bg-white px-1 pb-safe pt-1.5 shadow-[0_-4px_14px_rgba(15,23,42,0.08)] lg:hidden" aria-label="Điều hướng chính">
      {navItems.map((item) => {
        const active = isActive(item.path);

        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={(event) => handleNavClick(event, item.path)}
            aria-current={active ? 'page' : undefined}
            className={`flex min-h-12 flex-1 flex-col items-center justify-center rounded-xl px-1 py-1 transition-colors ${active ? 'text-primary' : 'text-slate-500 hover:text-primary'}`}
          >
            {item.icon}
            <span className={`max-w-full truncate text-[10px] leading-none ${active ? 'font-bold' : 'font-medium'}`}>
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
};
