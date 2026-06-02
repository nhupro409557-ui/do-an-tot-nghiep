import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Edit2, GripVertical, Home, KeyRound, LogOut, Menu, MoreHorizontal, Plus, RefreshCw, RotateCcw, Search, ShieldCheck, Trash2, TrendingUp, Upload, UserCircle, X } from 'lucide-react';
import { signOut } from '../../services/authDb';

const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });

export function AdminTopBar({ onRefresh, query, setQuery, sidebarOpen, searchPlaceholder, onToggleSidebar }: { onRefresh: () => void; query: string; setQuery: (value: string) => void; sidebarOpen: boolean; searchPlaceholder: string; onToggleSidebar: () => void }) {
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
          <button type="button" onClick={onToggleSidebar} title={sidebarOpen ? 'Ẩn menu quản trị' : 'Hiện menu quản trị'} className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50 hover:text-slate-950">
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-600"><ShieldCheck className="h-4 w-4" /> Admin Console</div>
            <h1 className="truncate text-xl font-bold text-slate-950 sm:text-2xl">Quản lý cửa hàng</h1>
            <p className="mt-1 text-sm text-slate-500">Bảng điều khiển sáng hơn, ưu tiên dữ liệu và thao tác quan trọng.</p>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center lg:justify-end">
          <div className="min-w-0 flex-1">
            <SearchBox value={query} onChange={setQuery} placeholder={searchPlaceholder} />
          </div>
          <Link to="/" className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-red-100 px-4 text-sm font-semibold text-red-700 shadow-sm transition hover:bg-red-200">
            <Home className="h-4 w-4" />
            <span>Trang chủ</span>
          </Link>
          <button type="button" onClick={onRefresh} title="Làm mới dữ liệu" className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
            <RefreshCw className="h-4 w-4" />
            <span className="hidden xl:inline">Làm mới</span>
          </button>
          <button type="button" title="Thông báo" className="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50">
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-600"></span>
          </button>
          <div className="relative">
            <button type="button" title="Hồ sơ admin" onClick={() => setProfileOpen((value) => !value)} className="inline-flex h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm font-semibold text-slate-700 transition hover:bg-white">
              <UserCircle className="h-5 w-5" />
              <span>Admin</span>
            </button>
            {profileOpen && (
              <div className="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white p-1 shadow-xl">
                <Link to="/change-password" onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 hover:text-slate-950">
                  <KeyRound className="h-4 w-4" />
                  Đổi mật khẩu
                </Link>
                <button type="button" onClick={handleSignOut} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50">
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

export function HeaderPanel({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="mb-5 overflow-hidden rounded-lg border border-slate-200/80 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
      <div className="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-red-600"><ShieldCheck className="h-4 w-4" /> Admin Console</div>
          <h1 className="mt-2 font-display text-3xl font-bold text-slate-950">Quản lý cửa hàng</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">Điều phối danh mục, thương hiệu, đơn hàng, voucher, nội dung và tồn kho trong một bảng quản trị gọn, rõ, dễ thao tác.</p>
        </div>
        <button onClick={onRefresh} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"><RefreshCw className="h-4 w-4" />Làm mới dữ liệu</button>
      </div>
      <div className="grid gap-3 bg-slate-50/70 px-5 py-3 text-xs font-semibold text-slate-500 sm:grid-cols-3">
        <span>Chuẩn dữ liệu: sản phẩm, biến thể, media</span>
        <span>Vận hành: đơn hàng, tồn kho, voucher</span>
        <span>Bảo mật: chỉ tài khoản admin truy cập</span>
      </div>
    </div>
  );
}

export type StatTone = 'emerald' | 'red' | 'sky' | 'amber';

export function StatCard({ label, value, caption, icon: Icon, tone }: { label: string; value: string | number; caption: string; icon: React.ElementType; tone: StatTone }) {
  const tones: Record<StatTone, { shell: string; badge: string; trend: string }> = {
    emerald: { shell: 'from-emerald-50 to-white', badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200', trend: 'bg-emerald-100 text-emerald-700' },
    red: { shell: 'from-red-50 to-white', badge: 'bg-red-100 text-red-700 ring-red-200', trend: 'bg-red-100 text-red-700' },
    sky: { shell: 'from-sky-50 to-white', badge: 'bg-sky-100 text-sky-700 ring-sky-200', trend: 'bg-sky-100 text-sky-700' },
    amber: { shell: 'from-amber-50 to-white', badge: 'bg-amber-100 text-amber-700 ring-amber-200', trend: 'bg-amber-100 text-amber-700' },
  };
  const currentTone = tones[tone];
  return (
    <div className={`rounded-[24px] border border-slate-200/80 bg-gradient-to-br ${currentTone.shell} p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-sm font-semibold text-slate-500">{label}</span>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</div>
          <span className={`mt-3 inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${currentTone.trend}`}>
            <TrendingUp className="mr-1 h-3.5 w-3.5" />
            Theo dõi sát
          </span>
        </div>
        <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl ring-1 ${currentTone.badge}`}><Icon className="h-6 w-6" /></span>
      </div>
      <p className="mt-3 text-xs font-medium leading-5 text-slate-500">{caption}</p>
    </div>
  );
}

export function MiniMetric({ label, value, helper }: { label: string; value: string | number; helper: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50/90 p-5">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold text-slate-950">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-500">{helper}</div>
    </div>
  );
}

export function MetricCard({ label, value, tone = 'slate' }: { label: string; value: string; tone?: 'emerald' | 'sky' | 'amber' | 'slate' }) {
  const tones = {
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-900',
    sky: 'border-sky-100 bg-sky-50 text-sky-900',
    amber: 'border-amber-100 bg-amber-50 text-amber-900',
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
  };
  return (
    <div className={`rounded-md border p-4 ${tones[tone]}`}>
      <div className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </div>
  );
}

export function AlertRow({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className={`rounded-md border px-3 py-2 ${value > 0 ? 'border-amber-200 bg-amber-50' : 'border-emerald-100 bg-emerald-50'}`}>
      <div className="flex items-center justify-between gap-3">
        <span className={`text-sm font-bold ${value > 0 ? 'text-amber-900' : 'text-emerald-800'}`}>{label}</span>
        <span className={`font-mono text-sm font-black ${value > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{value}</span>
      </div>
      <div className={`mt-1 text-xs font-semibold ${value > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{detail}</div>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm font-semibold text-slate-500">{text}</div>;
}

export function CollapsibleSection({ title, description, children, defaultOpen = false, forceOpen = false, forceOpenKey, closeSignal = 0, onClose }: { title: string; description?: string; children: React.ReactNode; defaultOpen?: boolean; forceOpen?: boolean; forceOpenKey?: string | null; closeSignal?: number; onClose?: () => void }) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    if (forceOpen) setOpen(true);
  }, [forceOpen, forceOpenKey]);

  useEffect(() => {
    if (closeSignal > 0) setOpen(false);
  }, [closeSignal]);

  const closePopup = () => {
    setOpen(false);
    onClose?.();
  };

  return (
    <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex w-full flex-col gap-3 rounded-md bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="text-sm font-bold text-slate-950">{title}</div>
          {description && <div className="mt-1 text-xs font-medium leading-5 text-slate-500">{description}</div>}
        </div>
        <button type="button" onClick={() => setOpen(true)} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-red-700">
          <Plus className="h-4 w-4" /> Thêm
        </button>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">{title}</h3>
                {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
              </div>
              <button type="button" onClick={closePopup} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">{children}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export function AdminBadge({ children, tone = 'slate' }: { children: React.ReactNode; tone?: 'slate' | 'green' | 'red' | 'yellow' | 'blue' | 'amber' }) {
  const tones = { slate: 'bg-slate-100 text-slate-700 ring-slate-200', green: 'bg-emerald-50 text-emerald-700 ring-emerald-100', red: 'bg-red-50 text-red-700 ring-red-100', yellow: 'bg-amber-50 text-amber-700 ring-amber-100', blue: 'bg-sky-50 text-sky-700 ring-sky-100', amber: 'bg-amber-50 text-amber-700 ring-amber-100' };
  return <span className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold ring-1 ${tones[tone]}`}>{children}</span>;
}

export function AdminPanel({ title, action, filters, children }: { title: string; action?: React.ReactNode; filters?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-[20px] border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold tracking-tight text-slate-950">{title}</h2>
        {action && <div className="flex flex-wrap items-center gap-2">{action}</div>}
      </div>
      {filters && (
        <div className="mb-5 flex flex-wrap items-stretch sm:items-center gap-3 rounded-2xl border border-slate-200/60 bg-slate-50/70 p-3.5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
          {filters}
        </div>
      )}
      {children}
    </div>
  );
}

export function AdminPagination({ currentPage, totalPages, onPageChange }: { currentPage: number; totalPages: number; onPageChange?: (page: number) => void }) {
  const safeTotal = Math.max(1, totalPages || 1);
  const safeCurrent = Math.min(Math.max(1, currentPage || 1), safeTotal);
  
  const getPages = () => {
    const pages: (number | string)[] = [];
    if (safeTotal <= 7) {
      for (let i = 1; i <= safeTotal; i++) pages.push(i);
    } else {
      pages.push(1);
      if (safeCurrent > 4) pages.push('...');
      
      const start = Math.max(2, safeCurrent - 2);
      const end = Math.min(safeTotal - 1, safeCurrent + 2);
      
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      
      if (safeCurrent < safeTotal - 3) pages.push('...');
      pages.push(safeTotal);
    }
    return pages;
  };

  const pages = getPages();
  const canChangePage = Boolean(onPageChange);

  return (
    <div className="flex items-center gap-1 bg-slate-100/50 p-1.5 rounded-full border border-slate-200/30 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
      {/* Đi tới trang đầu */}
      <button 
        type="button" 
        title="Trang đầu" 
        disabled={!canChangePage || safeCurrent <= 1} 
        onClick={() => onPageChange?.(1)} 
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/50 bg-white text-slate-500 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-30"
      >
        <ChevronsLeft className="h-4 w-4" />
      </button>

      {/* Đi tới trang trước */}
      <button 
        type="button" 
        title="Trang trước" 
        disabled={!canChangePage || safeCurrent <= 1} 
        onClick={() => onPageChange?.(safeCurrent - 1)} 
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/50 bg-white text-slate-500 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-30"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {/* Danh sách trang */}
      <div className="flex items-center gap-1">
        {pages.map((page, index) => {
          if (page === '...') {
            return (
              <span key={`dots-${index}`} className="flex h-8 w-8 items-center justify-center text-xs font-semibold text-slate-400 select-none">
                ...
              </span>
            );
          }
          const isCurrent = page === safeCurrent;
          return (
            <button
              key={page}
              type="button"
              disabled={!canChangePage || isCurrent}
              onClick={() => onPageChange?.(Number(page))}
              className={`inline-flex h-8 min-w-8 items-center justify-center rounded-full text-xs font-bold transition-all duration-200 disabled:pointer-events-none
                ${isCurrent 
                  ? 'bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-md shadow-red-500/25 scale-[1.05] border-0' 
                  : 'text-slate-600 hover:bg-slate-200/60 hover:text-slate-950 border-0'
                }
              `}
            >
              {page}
            </button>
          );
        })}
      </div>

      {/* Đi tới trang sau */}
      <button 
        type="button" 
        title="Trang sau" 
        disabled={!canChangePage || safeCurrent >= safeTotal} 
        onClick={() => onPageChange?.(safeCurrent + 1)} 
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/50 bg-white text-slate-500 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-30"
      >
        <ChevronRight className="h-4 w-4" />
      </button>

      {/* Đi tới trang cuối */}
      <button 
        type="button" 
        title="Trang cuối" 
        disabled={!canChangePage || safeCurrent >= safeTotal} 
        onClick={() => onPageChange?.(safeTotal)} 
        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/50 bg-white text-slate-500 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-30"
      >
        <ChevronsRight className="h-4 w-4" />
      </button>
    </div>
  );
}

export function AdminTable({
  headers,
  children,
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
  itemName = 'dòng',
  hideFooter = false
}: {
  headers: string[];
  children: React.ReactNode;
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  totalCount?: number;
  itemName?: string;
  hideFooter?: boolean;
}) {
  const rowCount = React.Children.count(children);
  
  return (
    <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500">
            <tr className="border-b border-slate-200">
              {headers.map((header) => (
                <th key={header} className="whitespace-nowrap px-4 py-3.5">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-slate-700 [&_tr:hover]:bg-slate-50/50">
            {children}
          </tbody>
        </table>
      </div>
      
      {!hideFooter && (
        <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span className="font-medium">
            {totalPages && currentPage ? (
              <>
                Đang hiển thị <span className="font-semibold text-slate-800">{rowCount}</span>
                {totalCount !== undefined && (
                  <>
                    {' '}/ <span className="font-semibold text-slate-800">{totalCount}</span>
                  </>
                )}
                {' '}{itemName}
              </>
            ) : (
              <>
                Đang xem <span className="font-semibold text-slate-800">{rowCount}</span> dòng trong bảng hiện tại.
              </>
            )}
          </span>
          {totalPages && currentPage && onPageChange ? (
            <AdminPagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={onPageChange}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}

export function BrandLogo({ brand }: { brand: any }) {
  const initial = String(brand.name || brand.code || '?').trim().charAt(0).toUpperCase() || '?';

  if (brand.logoUrl) {
    return (
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white p-1 shadow-sm">
        <img src={brand.logoUrl} alt={brand.logoAltText || (brand.name ? `${brand.name} logo` : 'Brand logo')} className="h-full w-full rounded-full object-contain" />
      </span>
    );
  }

  return (
    <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-700 ring-1 ring-slate-200">
      {initial}
    </span>
  );
}

export function VoucherConditions({ voucher }: { voucher: any }) {
  const conditions = [
    Number(voucher.minOrderValue || 0) > 0 ? `Tối thiểu ${currency.format(Number(voucher.minOrderValue || 0))}` : '',
    Number(voucher.maxDiscount || 0) > 0 ? `Giảm tối đa ${currency.format(Number(voucher.maxDiscount || 0))}` : '',
    voucher.stackable ? 'Cho cộng dồn' : 'Không cộng dồn',
    Number(voucher.validityDaysAfterClaim || 0) > 0 ? `Hạn sau lưu: ${voucher.validityDaysAfterClaim} ngày` : '',
    voucher.firstOrderOnly ? 'Chỉ đơn đầu tiên' : '',
    voucher.abandonedCartOnly ? 'Chỉ giỏ bỏ quên' : '',
    Number(voucher.perDeviceLimit || 0) > 0 ? `Thiết bị: ${voucher.perDeviceLimit}` : '',
    Number(voucher.perIpLimit || 0) > 0 ? `IP: ${voucher.perIpLimit}` : '',
    Array.isArray(voucher.eligibleTiers) && voucher.eligibleTiers.length ? `Hạng: ${voucher.eligibleTiers.join(', ')}` : '',
    Array.isArray(voucher.includeProductIds) && voucher.includeProductIds.length ? `SP áp dụng: ${voucher.includeProductIds.length}` : '',
    Array.isArray(voucher.excludeProductIds) && voucher.excludeProductIds.length ? `SP loại trừ: ${voucher.excludeProductIds.length}` : '',
    Array.isArray(voucher.includeCategoryIds) && voucher.includeCategoryIds.length ? `DM áp dụng: ${voucher.includeCategoryIds.length}` : '',
    Array.isArray(voucher.excludeCategoryIds) && voucher.excludeCategoryIds.length ? `DM loại trừ: ${voucher.excludeCategoryIds.length}` : '',
    voucher.assignedUserId ? `User: ${String(voucher.assignedUserId).slice(0, 8)}` : '',
    voucher.startsAt || voucher.endsAt ? `${voucher.startsAt ? new Date(voucher.startsAt).toLocaleDateString('vi-VN') : '...'} - ${voucher.endsAt ? new Date(voucher.endsAt).toLocaleDateString('vi-VN') : '...'}` : '',
  ].filter(Boolean);

  if (conditions.length === 0) return <span className="text-slate-400">Không ràng buộc</span>;
  return <div className="max-w-xs space-y-1 text-xs font-semibold text-slate-600">{conditions.map((item) => <div key={item}>{item}</div>)}</div>;
}

export function Input({ label, value, onChange, onBlur, type = 'text', required = false, disabled = false, placeholder, noLabel = false }: { label: string; value: string | number; onChange: (value: string) => void; onBlur?: () => void; type?: string; required?: boolean; disabled?: boolean; placeholder?: string; noLabel?: boolean }) {
  return (
    <label className="block w-full sm:w-auto">
      {!noLabel && <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>}
      <input 
        disabled={disabled} 
        required={required} 
        type={type} 
        value={value} 
        placeholder={placeholder || (noLabel ? label : undefined)} 
        onBlur={onBlur} 
        onChange={(event) => onChange(event.target.value)} 
        className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400" 
      />
    </label>
  );
}

export function Select({ label, value, onChange, options, disabled = false, noLabel = false }: { label: string; value: string; onChange?: (value: string) => void; options: [string, string][]; disabled?: boolean; noLabel?: boolean }) {
  return (
    <label className="block w-full sm:w-auto">
      {!noLabel && <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>}
      <select 
        disabled={disabled} 
        value={value} 
        aria-label={noLabel ? label : undefined}
        onChange={(event) => onChange?.(event.target.value)} 
        className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
      >
        {options.map(([optionValue, labelText]) => (
          <option key={optionValue || labelText} value={optionValue}>
            {labelText}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Checkbox({ label, checked, onChange, disabled = false }: { label: string; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }) {
  return <label className="mt-5 flex h-10 items-center gap-2 text-sm font-semibold text-slate-700"><input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-indigo-600 disabled:opacity-40" /> {label}</label>;
}

export function FileInput({ label, accept, multiple = false, onFiles }: { label: string; accept: string; multiple?: boolean; onFiles: (files: FileList | null) => void }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span><span className="flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"><Upload className="h-4 w-4" /> Chọn file</span><input className="hidden" type="file" accept={accept} multiple={multiple} onChange={(event) => onFiles(event.target.files)} /></label>;
}

export function RichTextEditor({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const editorRef = React.useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || '<p></p>';
    }
  }, [value]);

  function apply(command: string, commandValue?: string) {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    onChange(editorRef.current?.innerHTML || '<p></p>');
  }

  return (
    <div className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 p-2">
          <button type="button" onClick={() => apply('bold')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Bold</button>
          <button type="button" onClick={() => apply('italic')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Italic</button>
          <button type="button" onClick={() => apply('formatBlock', 'h2')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">H2</button>
          <button type="button" onClick={() => apply('insertUnorderedList')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">List</button>
          <button type="button" onClick={() => { const link = window.prompt('Nhập URL liên kết'); if (link) apply('createLink', link); }} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Link</button>
        </div>
        <div ref={editorRef} contentEditable suppressContentEditableWarning onInput={() => onChange(editorRef.current?.innerHTML || '<p></p>')} className="prose min-h-48 max-w-none px-4 py-3 text-sm outline-none" />
      </div>
    </div>
  );
}

export function MultiSelectBox({ label, options, values, onChange }: { label: string; options: { value: string; label: string }[]; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <select multiple value={values} onChange={(event) => onChange(Array.from(event.target.selectedOptions).map((option) => option.value))} className="min-h-36 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

export function SubmitButtons({ editing, onCancel }: { editing: boolean; onCancel: () => void }) {
  return <div className="flex items-end gap-2"><button className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"><Plus className="h-4 w-4" /> {editing ? 'Lưu' : 'Thêm'}</button>{editing && <button type="button" onClick={onCancel} title="Hủy chỉnh sửa" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"><X className="h-4 w-4" /></button>}</div>;
}

export function SearchBox({ value, onChange, placeholder = 'Tìm kiếm nhanh' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="relative block w-full sm:flex-1">
      <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input 
        value={value} 
        onChange={(event) => onChange(event.target.value)} 
        placeholder={placeholder} 
        className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-800 outline-none transition hover:border-slate-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400" 
      />
    </label>
  );
}

export function RowActions({ onEdit, onDelete, onRestore }: { onEdit: () => void; onDelete: () => void; onRestore?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex items-center gap-2">
      <button type="button" onClick={onEdit} title="Sửa" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
        <Edit2 className="h-4 w-4" />
      </button>
      <button type="button" onClick={() => setOpen((value) => !value)} title="Thao tác khác" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white/90 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-20 min-w-[150px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <button type="button" onClick={() => { setOpen(false); onDelete(); }} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50">
            <Trash2 className="h-4 w-4" /> Xóa / ẩn
          </button>
          {onRestore && (
            <button type="button" onClick={() => { setOpen(false); onRestore(); }} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
              <RotateCcw className="h-4 w-4" /> Bật lại
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function CategoryTableRow({ category, level, onEdit, onDelete, onRestore, onReorder }: { category: any; level: number; onEdit: () => void; onDelete: () => void; onRestore?: () => void; onReorder: (draggedId: string, targetId: string) => void }) {
  return (
    <tr draggable onDragStart={(event) => event.dataTransfer.setData('categoryId', category.id)} onDragOver={(event) => event.preventDefault()} onDrop={(event) => onReorder(event.dataTransfer.getData('categoryId'), category.id)}>
      <td className="px-4 py-3 text-slate-400"><GripVertical className="h-4 w-4" /></td>
      <td className="px-4 py-3">
        {category.iconUrl ? <img src={category.iconUrl} alt="" className="h-10 w-10 rounded-md border border-slate-200 object-cover" /> : <span className="text-xs font-semibold text-slate-400">{category.icon || '-'}</span>}
      </td>
      <td className="px-4 py-3 font-semibold text-slate-900">
        <div className="flex items-center gap-2" style={{ paddingLeft: level * 24 }}>
          {level > 0 && <span className="h-px w-4 bg-slate-300" />}
          <span>{category.name}</span>
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs">{category.slug}</td>
      <td className="px-4 py-3">{category.parentId ? 'Danh mục con' : 'Danh mục cha'}</td>
      <td className="px-4 py-3">{category.parentName || '-'}</td>
      <td className="px-4 py-3">{category.specFields?.length || 0} trường / {category.filterConfig?.length || 0} lọc</td>
      <td className="px-4 py-3">
        <div className="flex flex-col items-start gap-1">
          <AdminBadge tone={category.status === 'DRAFT' || category.status === 'PENDING_REVIEW' ? 'yellow' : category.isActive ? 'green' : category.status === 'REJECTED' ? 'red' : 'slate'}>{category.status || (category.isActive ? 'ACTIVE' : 'INACTIVE')}</AdminBadge>
          {category.workflowStatus && <span className="text-xs font-semibold text-slate-500">Duyệt: {category.workflowStatus}</span>}
          {category.hiddenByParent && <span className="text-xs font-semibold text-amber-600">Ẩn theo danh mục cha</span>}
        </div>
      </td>
      <td className="px-4 py-3"><RowActions onEdit={onEdit} onDelete={onDelete} onRestore={onRestore} /></td>
    </tr>
  );
}

export function MediaPreview({ title, items, onRemove }: { title: string; items: string[]; onRemove: (url: string) => void }) {
  if (items.length === 0) return null;
  return <div className="md:col-span-4"><div className="mb-2 text-xs font-bold text-slate-500">{title}</div><div className="flex flex-wrap gap-2">{items.map((item) => <div key={item} className="relative h-16 w-16 rounded-md border border-slate-200 bg-white p-1 shadow-sm"><img src={item} alt="" className="h-full w-full object-contain" /><button type="button" onClick={() => onRemove(item)} title="Xóa ảnh" className="absolute -right-2 -top-2 rounded-full bg-red-600 p-1 text-white shadow-sm"><X className="h-3 w-3" /></button></div>)}</div></div>;
}

export function VideoPreview({ title, url, onRemove }: { title: string; url: string; onRemove: () => void }) {
  const embedUrl = (() => {
    if (url.includes('youtube.com/embed/')) return url;
    if (url.includes('youtu.be/')) return `https://www.youtube.com/embed/${url.split('youtu.be/')[1].split(/[/?&]/)[0]}`;
    if (url.includes('youtube.com/shorts/')) return `https://www.youtube.com/embed/${url.split('youtube.com/shorts/')[1].split(/[/?&]/)[0]}`;
    if (url.includes('youtube.com/watch') && url.includes('v=')) return `https://www.youtube.com/embed/${url.split('v=')[1].split('&')[0]}`;
    return '';
  })();
  return (
    <div className="md:col-span-4">
      <div className="mb-2 text-xs font-bold text-slate-500">{title}</div>
      <div className="rounded-xl border border-slate-200 bg-slate-950 p-3 shadow-sm">
        {embedUrl ? (
          <iframe src={embedUrl} title={title} className="aspect-video w-full rounded-lg bg-black" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen />
        ) : (
          <video src={url} controls className="max-h-72 w-full rounded-lg bg-black" />
        )}
        <div className="mt-3 flex justify-end">
          <button type="button" onClick={onRemove} className="rounded-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">Xóa video đã chọn</button>
        </div>
      </div>
    </div>
  );
}

export function SimpleList({ title, icon: Icon, headers, rows, emptyText, action }: { title: string; icon: React.ElementType; headers: string[]; rows: (string | number)[][]; emptyText: string; action?: React.ReactNode }) {
  return <AdminPanel title={title} action={<div className="flex flex-col gap-2 sm:flex-row sm:items-center"><Icon className="hidden h-5 w-5 text-red-600 sm:block" />{action}</div>}><AdminTable headers={headers}>{rows.length === 0 ? <tr><td colSpan={headers.length} className="px-4 py-8 text-center text-sm font-medium text-slate-500">{emptyText}</td></tr> : rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={`${index}-${cellIndex}`} className={`px-4 py-3 ${cellIndex === 0 ? 'font-semibold text-slate-900' : ''}`}>{cell}</td>)}</tr>)}</AdminTable></AdminPanel>;
}



