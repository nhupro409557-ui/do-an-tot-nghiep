import { ChevronDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type AccountDashboardSidebarProps<TabId extends string> = {
  activeTab: TabId;
  items: ReadonlyArray<{
    id: TabId;
    label: string;
    icon: LucideIcon;
  }>;
  isOpen: boolean;
  onChangeTab: (tab: TabId) => void;
  onToggle: () => void;
};

export function AccountDashboardSidebar<TabId extends string>({
  activeTab,
  items,
  isOpen,
  onChangeTab,
  onToggle,
}: AccountDashboardSidebarProps<TabId>) {
  const activeItem = items.find(item => item.id === activeTab) || items[0];
  const ActiveIcon = activeItem.icon;

  return (
    <aside className="h-fit w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm lg:sticky lg:top-24 lg:w-72 lg:shrink-0">
      <div className="hidden border-b border-slate-100 px-5 py-4 lg:block">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Trung tâm tài khoản</p>
        <p className="mt-1 text-sm text-slate-500">Quản lý thông tin và dịch vụ</p>
      </div>
      <button
        type="button"
        onClick={onToggle}
        className="flex min-h-14 w-full items-center justify-between gap-3 px-4 py-3 text-left focus:outline-none focus:ring-2 focus:ring-inset focus:ring-red-200 lg:hidden"
        aria-expanded={isOpen}
        aria-controls="account-dashboard-menu"
      >
        <span className="flex items-center gap-3 min-w-0 flex-1">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50 text-[#d70018]">
            <ActiveIcon className="w-4 h-4" />
          </span>
          <span className="min-w-0">
            <span className="block text-[11px] font-semibold uppercase text-gray-400 leading-none mb-1">
              Khu vực quản lý
            </span>
            <span className="block text-sm font-bold text-gray-800 truncate">{activeItem.label}</span>
          </span>
        </span>
        <span className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center shrink-0">
          <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </span>
      </button>

      <ul
        id="account-dashboard-menu"
        className={`${isOpen ? 'grid max-h-[640px] opacity-100' : 'grid max-h-0 opacity-0'} grid-cols-1 gap-1 overflow-hidden border-t border-slate-100 px-2 py-0 text-sm font-medium text-slate-600 transition-all duration-200 ease-out md:grid-cols-2 lg:grid lg:max-h-none lg:grid-cols-1 lg:border-t-0 lg:py-3 lg:opacity-100`}
      >
        {items.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onChangeTab(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`flex min-h-11 w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-left transition focus:outline-none focus:ring-2 focus:ring-red-200 ${isActive ? 'bg-[#d70018] font-bold text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              >
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${isActive ? 'bg-white/15' : 'bg-slate-100 text-slate-500'}`}><Icon className="h-4 w-4" /></span>
                <span className="truncate">{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
