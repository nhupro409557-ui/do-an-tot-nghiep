import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, Edit2, KeyRound, LogOut, Menu, MoreHorizontal, Plus, RefreshCw, ShieldCheck, Trash2, RotateCcw, UserCircle, X } from 'lucide-react';
import { signOut } from '../../../services/authDb';
import { resolveImageUrl } from '../../../services/apiDb';

export function AdminTopBar({
  onRefresh,
  query,
  setQuery,
  sidebarOpen,
  searchPlaceholder,
  onToggleSidebar,
}: {
  onRefresh: () => void;
  query: string;
  setQuery: (value: string) => void;
  sidebarOpen: boolean;
  searchPlaceholder: string;
  onToggleSidebar: () => void;
}) {
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
    navigate('/admin/login');
  }

  return (
    <header className="sticky top-0 z-40 mb-5 rounded-[24px] border border-rose-200/80 bg-rose-50/95 shadow-[0_18px_45px_rgba(127,29,29,0.08)] backdrop-blur">
      <div className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onToggleSidebar}
            title={sidebarOpen ? 'Ẩn menu quản trị' : 'Hiện menu quản trị'}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50 hover:text-slate-950"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">
              <ShieldCheck className="h-4 w-4" /> Admin Console
            </div>
            <h1 className="truncate text-xl font-bold text-slate-955 sm:text-2xl">
              Quản lý cửa hàng
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Bảng điều khiển sáng hơn, ưu tiên dữ liệu và thao tác quan trọng.
            </p>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center lg:justify-end">
          <div className="min-w-0 flex-1">
            <label className="relative block w-full sm:flex-1">
              <span className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400">
                <ShieldCheck className="h-4 w-4 hidden" />
              </span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-800 outline-none transition hover:border-slate-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400"
              />
            </label>
          </div>
          <Link
            to="/"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-red-100 px-4 text-sm font-semibold text-red-700 shadow-sm transition hover:bg-red-200"
          >
            <span>Trang chủ</span>
          </Link>
          <button
            type="button"
            onClick={onRefresh}
            title="Làm mới dữ liệu"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            <span className="hidden xl:inline">Làm mới</span>
          </button>
          <button
            type="button"
            title="Thông báo"
            className="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-600"></span>
          </button>
          <div className="relative">
            <button
              type="button"
              title="Hồ sơ admin"
              onClick={() => setProfileOpen((value) => !value)}
              className="inline-flex h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm font-semibold text-slate-700 transition hover:bg-white"
            >
              <UserCircle className="h-5 w-5" />
              <span>Admin</span>
            </button>
            {profileOpen && (
              <div className="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white p-1 shadow-xl">
                <Link
                  to="/change-password"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 hover:text-slate-950"
                >
                  <KeyRound className="h-4 w-4" />
                  Đổi mật khẩu
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50"
                >
                  <LogOut className="h-4 w-4" />
                  Đăng xuất
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export function AdminBadge({
  children,
  tone = 'slate',
}: {
  children: React.ReactNode;
  tone?: 'slate' | 'green' | 'red' | 'yellow' | 'blue' | 'amber';
}) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700 ring-slate-200',
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    red: 'bg-red-50 text-red-700 ring-red-100',
    yellow: 'bg-amber-50 text-amber-700 ring-amber-100',
    blue: 'bg-sky-50 text-sky-700 ring-sky-100',
    amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  };
  return (
    <span className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold ring-1 ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function BrandLogo({ brand }: { brand: any }) {
  const initial = String(brand.name || brand.code || '?').trim().charAt(0).toUpperCase() || '?';
  const logoUrl = resolveImageUrl(brand.logoUrl);

  if (logoUrl) {
    return (
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white p-1 shadow-sm">
        <img
          src={logoUrl}
          alt={brand.logoAltText || (brand.name ? `${brand.name} logo` : 'Brand logo')}
          className="h-full w-full rounded-full object-contain"
        />
      </span>
    );
  }

  return (
    <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-700 ring-1 ring-slate-200">
      {initial}
    </span>
  );
}

export function SubmitButtons({
  editing,
  onCancel,
}: {
  editing: boolean;
  onCancel: () => void;
}) {
  return (
    <div className="flex items-end gap-2">
      <button className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700">
        <Plus className="h-4 w-4" /> {editing ? 'Lưu' : 'Thêm'}
      </button>
      {editing && (
        <button
          type="button"
          onClick={onCancel}
          title="Hủy chỉnh sửa"
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function RowActions({
  onEdit,
  onDelete,
  onRestore,
}: {
  onEdit: () => void;
  onDelete: () => void;
  onRestore?: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex items-center gap-2">
      <button
        type="button"
        onClick={onEdit}
        title="Sửa"
        className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
      >
        <Edit2 className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        title="Thao tác khác"
        className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white/90 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-20 min-w-[150px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" /> Xóa / ẩn
          </button>
          {onRestore && (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onRestore();
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50"
            >
              <RotateCcw className="h-4 w-4" /> Bật lại
            </button>
          )}
        </div>
      )}
    </div>
  );
}
