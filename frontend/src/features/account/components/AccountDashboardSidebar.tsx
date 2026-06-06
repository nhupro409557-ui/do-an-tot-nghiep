import type { LucideIcon } from 'lucide-react';

type AccountDashboardSidebarProps<TabId extends string> = {
  activeTab: TabId;
  items: ReadonlyArray<{
    id: TabId;
    label: string;
    icon: LucideIcon;
  }>;
  onChangeTab: (tab: TabId) => void;
};

export function AccountDashboardSidebar<TabId extends string>({
  activeTab,
  items,
  onChangeTab,
}: AccountDashboardSidebarProps<TabId>) {
  return (
    <aside className="w-full lg:w-64 bg-white rounded-xl shadow-sm py-4 h-fit">
      <ul className="text-sm font-medium text-gray-700">
        {items.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onChangeTab(item.id)}
                className={`w-full flex items-center gap-3 px-6 py-3 border-l-4 transition-colors ${isActive ? 'text-[#d70018] bg-red-50 border-[#d70018]' : 'border-transparent hover:bg-gray-50 hover:text-red-500'}`}
              >
                <Icon className="w-4 h-4" /> {item.label}
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
