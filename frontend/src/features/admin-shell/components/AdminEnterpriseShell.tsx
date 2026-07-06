import React, { useMemo, useState } from 'react';
import { Bell, ChevronDown, Home, KeyRound, LogOut, Menu, PanelLeftClose, PanelLeftOpen, RefreshCw, Search, Settings } from 'lucide-react';
import emvFavicon from '../../../assets/emv-favicon.svg';
import emvLogoNew from '../../../assets/emv-logo-new.svg';
import { useAuth } from '../../../context/AuthContext';

export type AdminShellTab = {
  id: string;
  label: string;
  group?: string;
  icon: React.ReactNode;
};

type AdminEnterpriseShellProps = {
  tabs: AdminShellTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  title: string;
  description: string;
  sectionLabel: string;
  sectionIcon: React.ReactNode;
  query: string;
  onQueryChange: (value: string) => void;
  searchPlaceholder: string;
  onRefresh: () => void;
  onSignOut: () => Promise<void> | void;
  busy?: boolean;
  children: React.ReactNode;
};

export function AdminEnterpriseShell({
  tabs,
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapsed,
  title,
  description,
  sectionLabel,
  sectionIcon,
  query,
  onQueryChange,
  searchPlaceholder,
  onRefresh,
  onSignOut,
  busy = false,
  children,
}: AdminEnterpriseShellProps) {
  const { user, userData } = useAuth();
  const [accountOpen, setAccountOpen] = useState(false);
  const userInitial = user?.displayName?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'A';
  const adminName = userData?.displayName || user?.displayName || 'Admin';
  const adminEmail = user?.email || '';
  const roleLabel = userData?.role === 'super_admin' ? 'Super Admin' : userData?.role === 'staff' ? 'Staff Admin' : 'Admin';

  const groupedTabs = useMemo(
    () => tabs.reduce<Record<string, AdminShellTab[]>>((groups, tab) => {
      const groupName = tab.group || 'Khac';
      groups[groupName] = [...(groups[groupName] || []), tab];
      return groups;
    }, {}),
    [tabs],
  );

  function handleTabChange(tabId: string) {
    onTabChange(tabId);
    onQueryChange('');
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f7fb]">
      <aside className={`${collapsed ? 'w-[84px]' : 'w-[272px]'} hidden h-screen shrink-0 flex-col border-r border-slate-200 bg-white transition-[width] duration-200 lg:flex`}>
        <div className="border-b border-slate-200 px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <a href="/" className="flex min-w-0 items-center gap-3 transition hover:opacity-80">
              {collapsed ? (
                <img src={emvFavicon} alt="ElectroMart Logo" className="h-9 w-9 shrink-0 object-contain" />
              ) : (
                <div className="flex shrink-0 items-center justify-center rounded-lg bg-[#d70018] px-2.5 py-1.5">
                  <img src={emvLogoNew} alt="ElectroMart Logo" className="h-7 w-auto object-contain" />
                </div>
              )}
              {!collapsed && (
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold text-slate-950">ElectroMart Admin</div>
                  <div className="truncate text-[11px] font-medium text-slate-500">Bảng điều hành</div>
                </div>
              )}
            </a>
            {!collapsed && (
              <a href="/" title="Tro ve trang chu" className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-900">
                <Home className="h-4 w-4" />
              </a>
            )}
          </div>
        </div>

        <nav className="admin-sidebar-menu-scroll flex-1 overflow-y-auto px-3 py-3">
          {collapsed ? (
            <div className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  title={tab.label}
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex h-11 w-full items-center justify-center rounded-lg transition ${activeTab === tab.id ? 'bg-red-50 text-[#d70018]' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'}`}
                >
                  {tab.icon}
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-5">
              {Object.entries(groupedTabs).map(([groupLabel, groupTabs]) => (
                <div key={groupLabel}>
                  <div className="mb-2 px-2 text-[11px] font-bold uppercase tracking-wide text-slate-400">{groupLabel}</div>
                  <div className="space-y-1">
                    {groupTabs.map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => handleTabChange(tab.id)}
                        className={`flex h-10 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-semibold transition ${activeTab === tab.id ? 'bg-red-50 text-[#d70018]' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-950'}`}
                      >
                        <span className="shrink-0">{tab.icon}</span>
                        <span className="truncate">{tab.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </nav>

        <div className="border-t border-slate-200 bg-slate-50/50 px-4 py-3">
          <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} min-w-0`}>
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#d70018] text-xs font-bold text-white">{userInitial}</span>
            {!collapsed && (
              <div className="min-w-0">
                <div className="truncate text-xs font-semibold text-slate-800" title={adminName}>{adminName}</div>
                <div className="truncate text-[10px] text-slate-500" title={adminEmail}>{adminEmail}</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      <div className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <header className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <button type="button" onClick={onToggleCollapsed} title={collapsed ? 'Mở rộng menu' : 'Thu gọn menu'} className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-slate-600 transition hover:bg-slate-100 hover:text-slate-950">
                <Menu className="h-5 w-5 lg:hidden" />
                {collapsed ? <PanelLeftOpen className="hidden h-5 w-5 lg:block" /> : <PanelLeftClose className="hidden h-5 w-5 lg:block" />}
              </button>
              <div className="min-w-0 text-xs font-semibold text-slate-500">
                <span>Admin</span>
                <span className="mx-2 text-slate-300">/</span>
                <span>Bảng điều khiển</span>
                <span className="mx-2 text-slate-300">/</span>
                <span className="text-slate-800">{title}</span>
              </div>
            </div>

            <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
              <label className="relative block min-w-0 sm:w-[340px]">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => onQueryChange(event.target.value)}
                  placeholder={searchPlaceholder}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-9 text-sm font-medium text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-[#d70018] focus:ring-2 focus:ring-red-100"
                />
                {query && (
                  <button type="button" onClick={() => onQueryChange('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 hover:text-slate-700">
                    Xóa
                  </button>
                )}
              </label>
              <button type="button" title="Làm mới dữ liệu" onClick={onRefresh} className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-slate-700 transition hover:bg-slate-50">
                <RefreshCw className={`h-5 w-5 ${busy ? 'animate-spin' : ''}`} />
              </button>
              <button type="button" title="Thông báo" className="relative inline-flex h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-slate-700 transition hover:bg-slate-50">
                <Bell className="h-5 w-5" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#d70018]" />
              </button>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setAccountOpen((value) => !value)}
                  className="inline-flex h-11 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-sky-600 text-xs font-bold text-white">{userInitial}</span>
                  <span>{roleLabel}</span>
                  <ChevronDown className="h-4 w-4 text-slate-400" />
                </button>
                {accountOpen && (
                  <div className="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white p-1 shadow-xl">
                    <a href="/change-password" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
                      <Settings className="h-4 w-4" />
                      Đổi mật khẩu
                    </a>
                    <button type="button" onClick={() => void onSignOut()} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50">
                      <LogOut className="h-4 w-4" />
                      Đăng xuất
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {!collapsed && (
          <div className="border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex min-h-10 items-center gap-2 rounded-lg px-3 text-left text-xs font-semibold transition ${activeTab === tab.id ? 'bg-red-50 text-[#d70018]' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
                >
                  <span className="shrink-0">{tab.icon}</span>
                  <span className="truncate">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <section className="mb-5 rounded-lg border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[#d70018]">{sectionIcon}</span>
                  <span className="text-xs font-bold uppercase text-slate-500">{sectionLabel}</span>
                </div>
                <h1 className="mt-2 text-2xl font-bold text-slate-950">{title}</h1>
                <p className="mt-1 block max-w-4xl text-sm leading-6 text-slate-500">{description}</p>
              </div>
            </div>
          </section>
          {busy && (
            <div className="mb-4 rounded-lg border border-sky-100 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-700">
              Đang đồng bộ dữ liệu quản trị...
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
