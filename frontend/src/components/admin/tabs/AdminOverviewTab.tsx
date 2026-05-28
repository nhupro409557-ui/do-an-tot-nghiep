import React from 'react';
import { Activity, AlertTriangle, BarChart3, Boxes, Building2, FolderTree, RotateCcw, ShieldCheck, ShoppingBag, TrendingUp, Users } from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AdminPanel, AlertRow, EmptyState, MiniMetric, StatCard, type StatTone } from '../AdminDashboardParts';

type AdminOverviewTabProps = {
  stats: any[];
  overview: any;
  roleDashboards: any[];
  currency: Intl.NumberFormat;
  compactCurrency: Intl.NumberFormat;
  percent: Intl.NumberFormat;
};

export default function AdminOverviewTab({
  stats,
  overview,
  roleDashboards,
  currency,
  compactCurrency,
  percent,
}: AdminOverviewTabProps) {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;
          return <StatCard key={item.label} label={item.label} value={item.value} caption={item.caption} icon={Icon} tone={item.tone as StatTone} />;
        })}
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <AdminPanel title="Nhịp vận hành hôm nay" action={<Activity className="h-5 w-5 text-red-600" />}>
          <div className="grid gap-3 md:grid-cols-3">
            <MiniMetric label="Đơn chờ xử lý" value={overview?.orders?.pending || 0} helper="Cần xác nhận sớm" />
            <MiniMetric label="Sản phẩm sắp hết" value={overview?.lowStockCount || 0} helper="Ưu tiên nhập kho" />
            <MiniMetric label="Đánh giá mới" value={overview?.reviews?.pending || 0} helper="Theo dõi trải nghiệm" />
          </div>
        </AdminPanel>
        <AdminPanel title="Danh mục dữ liệu" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
          <div className="space-y-3">
            {[
              ['Danh mục', overview?.categories?.total || 0, FolderTree],
              ['Thương hiệu', overview?.brands?.total || 0, Building2],
              ['Khách hàng', overview?.customers?.total || 0, Users],
            ].map(([label, value, Icon]: [string, number, any]) => (
              <div key={label} className="flex items-center justify-between rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-600">
                  <Icon className="h-4 w-4 text-slate-400" />
                  {label}
                </span>
                <span className="font-mono text-sm font-bold text-slate-900">{value}</span>
              </div>
            ))}
          </div>
        </AdminPanel>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <AdminPanel title="Doanh thu theo ngày" action={<TrendingUp className="h-5 w-5 text-emerald-600" />}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview?.revenueByDay || []} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="adminRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#64748b" />
                <YAxis tickFormatter={(value) => compactCurrency.format(Number(value))} tick={{ fontSize: 12 }} stroke="#64748b" width={48} />
                <Tooltip formatter={(value) => currency.format(Number(value))} labelFormatter={(label) => `Ngày ${label}`} />
                <Area type="monotone" dataKey="total" stroke="#059669" strokeWidth={3} fill="url(#adminRevenue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </AdminPanel>
        <AdminPanel title="Doanh thu theo tháng" action={<BarChart3 className="h-5 w-5 text-sky-600" />}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overview?.revenueByMonth || []} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#64748b" />
                <YAxis tickFormatter={(value) => compactCurrency.format(Number(value))} tick={{ fontSize: 12 }} stroke="#64748b" width={48} />
                <Tooltip formatter={(value) => currency.format(Number(value))} />
                <Bar dataKey="total" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </AdminPanel>
      </div>
      <div className="grid gap-5 xl:grid-cols-3">
        <AdminPanel title="Top sản phẩm bán chạy" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
          <div className="space-y-3">
            {(overview?.topProducts || []).map((product: any, index: number) => (
              <div key={product.id || product.name} className="flex items-center gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-100 text-sm font-black text-red-700">{index + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-bold text-slate-800">{product.name}</div>
                  <div className="text-xs font-semibold text-slate-500">{product.soldCount} đã bán</div>
                </div>
                <span className="text-xs font-bold text-slate-700">{compactCurrency.format(product.periodRevenue || 0)}</span>
              </div>
            ))}
            {(!overview?.topProducts || overview.topProducts.length === 0) && <EmptyState text="Chưa có dữ liệu bán chạy." />}
          </div>
        </AdminPanel>
        <AdminPanel title="Tỉ lệ hủy và hoàn đơn" action={<RotateCcw className="h-5 w-5 text-amber-600" />}>
          <div className="grid gap-3">
            <MiniMetric label="Tỉ lệ hủy đơn" value={overview?.orders?.total ? percent.format((overview.orders.cancelled || 0) / overview.orders.total) : '0%'} helper={`${overview?.orders?.cancelled || 0} đơn đã hủy`} />
            <MiniMetric label="Tỉ lệ hoàn đơn" value={overview?.orders?.total ? percent.format((overview.orders.refunded || 0) / overview.orders.total) : '0%'} helper={`${overview?.orders?.refunded || 0} đơn hoàn / trả`} />
          </div>
        </AdminPanel>
        <AdminPanel title="Cảnh báo điều hành" action={<AlertTriangle className="h-5 w-5 text-amber-600" />}>
          <div className="space-y-3">
            <AlertRow label="Voucher gần hết ngân sách" value={overview?.riskyVoucherCount || 0} detail="Đã dùng từ 80% ngân sách" />
            <AlertRow label="Tồn kho âm" value={overview?.negativeStockCount || 0} detail="Cần đối soát lệch kho" />
            <AlertRow label="Sắp hết hàng" value={overview?.lowStockCount || 0} detail="Dựa trên ngưỡng tối thiểu từng sản phẩm" />
          </div>
        </AdminPanel>
      </div>
      <AdminPanel title="Dashboard theo vai trò" action={<ShieldCheck className="h-5 w-5 text-slate-600" />}>
        <div className="grid gap-3 md:grid-cols-3">
          {roleDashboards.map((item) => {
            const Icon = item.icon || Boxes;
            return (
              <div key={item.role} className="rounded-md border border-slate-100 bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-400"><Icon className="h-4 w-4" />{item.role}</div>
                <div className="mt-2 text-xl font-bold text-slate-950">{item.metric}</div>
                <p className="mt-1 text-xs font-medium leading-5 text-slate-500">{item.helper}</p>
              </div>
            );
          })}
        </div>
      </AdminPanel>
    </div>
  );
}
