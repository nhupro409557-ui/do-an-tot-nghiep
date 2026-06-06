import React from 'react';
import { adminTabTone } from '../pages/AdminDashboardConfig';

type AdminSidebarProps = {
  sidebarOpen: boolean;
  groupedTabs: Record<string, any[]>;
  tab: string;
  setTab: (tab: any) => void;
  setQuery: (query: string) => void;
};

export default function AdminSidebar({ sidebarOpen, groupedTabs, tab, setTab, setQuery }: AdminSidebarProps) {
  return (
    <aside className={`${sidebarOpen ? 'block' : 'hidden'} admin-scroll-panel rounded-[28px] border border-rose-200/80 bg-[linear-gradient(180deg,#fff7f7_0%,#fff1f2_100%)] p-4 shadow-[0_24px_60px_rgba(127,29,29,0.08)]`}>
      <div className="mb-4 rounded-2xl border border-rose-100 bg-[linear-gradient(135deg,#fff1f2_0%,#fffaf9_100%)] px-4 py-4 shadow-sm">
        <div className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">Điều hướng</div>
        <div className="mt-1 text-sm font-semibold text-slate-900">Trung tâm vận hành admin</div>
        <p className="mt-2 text-xs leading-5 text-slate-500">Nhóm chức năng được gom theo ngữ cảnh để quét nhanh hơn và giảm tải thị giác.</p>
      </div>
      <div className="space-y-4">
        {Object.entries(groupedTabs).map(([groupName, items]) => (
          <div key={groupName}>
            <div className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{groupName}</div>
            <div className="space-y-2">
              {items.map((item) => {
                const Icon = item.icon;
                const itemTone = adminTabTone[item.id];
                return (
                  <button key={item.id} onClick={() => { setTab(item.id); setQuery(''); }} className={`flex h-12 w-full items-center gap-3 rounded-2xl border px-3 text-left text-sm font-semibold transition ${tab === item.id ? itemTone.active : 'border-slate-200 bg-slate-50/80 text-slate-700 hover:border-slate-300 hover:bg-white hover:text-slate-950'}`}>
                    <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ring-1 ${tab === item.id ? 'bg-white/70 text-slate-800 ring-white/80' : itemTone.icon}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
