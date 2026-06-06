import React from 'react';
import { AdminPagination } from './AdminPagination';

export function AdminTable({
  headers,
  children,
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
  itemName = 'dòng',
  hideFooter = false,
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
