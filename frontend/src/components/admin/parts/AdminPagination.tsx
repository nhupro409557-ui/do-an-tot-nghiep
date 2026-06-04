import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

export function AdminPagination({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  onPageChange?: (page: number) => void;
}) {
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
              <span
                key={`dots-${index}`}
                className="flex h-8 w-8 items-center justify-center text-xs font-semibold text-slate-400 select-none"
              >
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
                ${
                  isCurrent
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
