import React from 'react';
import { RefreshCw, ShieldCheck, TrendingUp } from 'lucide-react';
import { AdminPanel } from './AdminPanel';
import { AdminTable } from './AdminTable';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export function HeaderPanel({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="mb-5 overflow-hidden rounded-lg border border-slate-200/80 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
      <div className="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-red-600">
            <ShieldCheck className="h-4 w-4" /> Admin Console
          </div>
          <h1 className="mt-2 font-display text-3xl font-bold text-slate-955">
            Quản lý cửa hàng
          </h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
            Điều phối danh mục, thương hiệu, đơn hàng, voucher, nội dung và tồn kho trong
            một bảng quản trị gọn, rõ, dễ thao tác.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          <RefreshCw className="h-4 w-4" /> Làm mới dữ liệu
        </button>
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

export function StatCard({
  label,
  value,
  caption,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  caption: string;
  icon: React.ElementType;
  tone: StatTone;
}) {
  const tones: Record<StatTone, { shell: string; badge: string; trend: string }> = {
    emerald: {
      shell: 'from-emerald-50 to-white',
      badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
      trend: 'bg-emerald-100 text-emerald-700',
    },
    red: {
      shell: 'from-red-50 to-white',
      badge: 'bg-red-100 text-red-700 ring-red-200',
      trend: 'bg-red-100 text-red-700',
    },
    sky: {
      shell: 'from-sky-50 to-white',
      badge: 'bg-sky-100 text-sky-700 ring-sky-200',
      trend: 'bg-sky-100 text-sky-700',
    },
    amber: {
      shell: 'from-amber-50 to-white',
      badge: 'bg-amber-100 text-amber-700 ring-amber-200',
      trend: 'bg-amber-100 text-amber-700',
    },
  };
  const currentTone = tones[tone];
  return (
    <div
      className={`rounded-[24px] border border-slate-200/80 bg-gradient-to-br ${currentTone.shell} p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-sm font-semibold text-slate-500">{label}</span>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-955">
            {value}
          </div>
          <span
            className={`mt-3 inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${currentTone.trend}`}
          >
            <TrendingUp className="mr-1 h-3.5 w-3.5" />
            Theo dõi sát
          </span>
        </div>
        <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl ring-1 ${currentTone.badge}`}>
          <Icon className="h-6 w-6" />
        </span>
      </div>
      <p className="mt-3 text-xs font-medium leading-5 text-slate-500">{caption}</p>
    </div>
  );
}

export function MiniMetric({
  label,
  value,
  helper,
}: {
  label: string;
  value: string | number;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50/90 p-5">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold text-slate-955">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-500">{helper}</div>
    </div>
  );
}

export function MetricCard({
  label,
  value,
  tone = 'slate',
}: {
  label: string;
  value: string;
  tone?: 'emerald' | 'sky' | 'amber' | 'slate';
}) {
  const tones = {
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-900',
    sky: 'border-sky-100 bg-sky-50 text-sky-900',
    amber: 'border-amber-100 bg-amber-50 text-amber-900',
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
  };
  return (
    <div className={`rounded-md border p-4 ${tones[tone]}`}>
      <div className="text-xs font-bold uppercase tracking-wide opacity-70">
        {label}
      </div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </div>
  );
}

export function AlertRow({
  label,
  value,
  detail,
}: {
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <div
      className={`rounded-md border px-3 py-2 ${
        value > 0 ? 'border-amber-200 bg-amber-50' : 'border-emerald-100 bg-emerald-50'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={`text-sm font-bold ${value > 0 ? 'text-amber-900' : 'text-emerald-800'}`}
        >
          {label}
        </span>
        <span
          className={`font-mono text-sm font-black ${
            value > 0 ? 'text-amber-700' : 'text-emerald-700'
          }`}
        >
          {value}
        </span>
      </div>
      <div
        className={`mt-1 text-xs font-semibold ${
          value > 0 ? 'text-amber-700' : 'text-emerald-700'
        }`}
      >
        {detail}
      </div>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm font-semibold text-slate-500">
      {text}
    </div>
  );
}

export function VoucherConditions({ voucher }: { voucher: any }) {
  const conditions = [
    Number(voucher.minOrderValue || 0) > 0
      ? `Tối thiểu ${currency.format(Number(voucher.minOrderValue || 0))}`
      : '',
    Number(voucher.maxDiscount || 0) > 0
      ? `Giảm tối đa ${currency.format(Number(voucher.maxDiscount || 0))}`
      : '',
    voucher.stackable ? 'Cho cộng dồn' : 'Không cộng dồn',
    Number(voucher.validityDaysAfterClaim || 0) > 0
      ? `Hạn sau lưu: ${voucher.validityDaysAfterClaim} ngày`
      : '',
    voucher.firstOrderOnly ? 'Chỉ đơn đầu tiên' : '',
    voucher.abandonedCartOnly ? 'Chỉ giỏ bỏ quên' : '',
    Number(voucher.perDeviceLimit || 0) > 0 ? `Thiết bị: ${voucher.perDeviceLimit}` : '',
    Number(voucher.perIpLimit || 0) > 0 ? `IP: ${voucher.perIpLimit}` : '',
    Array.isArray(voucher.eligibleTiers) && voucher.eligibleTiers.length
      ? `Hạng: ${voucher.eligibleTiers.join(', ')}`
      : '',
    Array.isArray(voucher.includeProductIds) && voucher.includeProductIds.length
      ? `SP áp dụng: ${voucher.includeProductIds.length}`
      : '',
    Array.isArray(voucher.excludeProductIds) && voucher.excludeProductIds.length
      ? `SP loại trừ: ${voucher.excludeProductIds.length}`
      : '',
    Array.isArray(voucher.includeCategoryIds) && voucher.includeCategoryIds.length
      ? `DM áp dụng: ${voucher.includeCategoryIds.length}`
      : '',
    Array.isArray(voucher.excludeCategoryIds) && voucher.excludeCategoryIds.length
      ? `DM loại trừ: ${voucher.excludeCategoryIds.length}`
      : '',
    voucher.assignedUserId ? `User: ${String(voucher.assignedUserId).slice(0, 8)}` : '',
    voucher.startsAt || voucher.endsAt
      ? `${
          voucher.startsAt ? new Date(voucher.startsAt).toLocaleDateString('vi-VN') : '...'
        } - ${
          voucher.endsAt ? new Date(voucher.endsAt).toLocaleDateString('vi-VN') : '...'
        }`
      : '',
  ].filter(Boolean);

  if (conditions.length === 0)
    return <span className="text-slate-400">Không ràng buộc</span>;
  return (
    <div className="max-w-xs space-y-1 text-xs font-semibold text-slate-600">
      {conditions.map((item) => (
        <div key={item}>{item}</div>
      ))}
    </div>
  );
}

export function SimpleList({
  title,
  icon: Icon,
  headers,
  rows,
  emptyText,
  action,
}: {
  title: string;
  icon: React.ElementType;
  headers: string[];
  rows: (string | number)[][];
  emptyText: string;
  action?: React.ReactNode;
}) {
  return (
    <AdminPanel
      title={title}
      action={
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Icon className="hidden h-5 w-5 text-red-600 sm:block" />
          {action}
        </div>
      }
    >
      <AdminTable headers={headers}>
        {rows.length === 0 ? (
          <tr>
            <td
              colSpan={headers.length}
              className="px-4 py-8 text-center text-sm font-medium text-slate-500"
            >
              {emptyText}
            </td>
          </tr>
        ) : (
          rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td
                  key={`${index}-${cellIndex}`}
                  className={`px-4 py-3 ${cellIndex === 0 ? 'font-semibold text-slate-900' : ''}`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))
        )}
      </AdminTable>
    </AdminPanel>
  );
}
