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
    <aside className="w-full lg:w-64 bg-white rounded-xl shadow-sm h-fit overflow-hidden lg:sticky lg:top-24">
      <button
        type="button"
        onClick={onToggle}
        className="lg:hidden w-full flex items-center justify-between gap-3 px-4 py-3 text-left"
        aria-expanded={isOpen}
        aria-controls="account-dashboard-menu"
      >
        <span className="flex items-center gap-3 min-w-0 flex-1">
          <span className="w-9 h-9 rounded-lg bg-red-50 text-[#d70018] flex items-center justify-center shrink-0">
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
        className={`${isOpen ? 'grid max-h-96 opacity-100' : 'grid max-h-0 opacity-0'} lg:grid lg:max-h-none lg:opacity-100 grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-1 text-sm font-medium text-gray-700 border-t border-gray-100 lg:border-t-0 px-2 py-0 lg:py-3 overflow-hidden transition-all duration-200 ease-out`}
      >
        {items.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onChangeTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg lg:rounded-none lg:border-l-4 transition-colors text-left ${isActive ? 'text-[#d70018] bg-red-50 lg:border-[#d70018]' : 'lg:border-transparent hover:bg-gray-50 hover:text-red-500'}`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
