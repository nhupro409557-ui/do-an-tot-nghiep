import React from 'react';

export function AdminPanel({
  title,
  action,
  filters,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  filters?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[20px] border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold tracking-tight text-slate-955">{title}</h2>
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
