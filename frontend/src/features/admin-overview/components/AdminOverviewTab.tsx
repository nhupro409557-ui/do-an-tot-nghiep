import React from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  FolderTree,
  RotateCcw,
  ShieldCheck,
  ShoppingBag,
  TrendingUp,
  Users,
  PlusCircle,
  ArrowRight,
  Database,
  Percent,
  ClipboardList,
  Zap
} from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { StatCard, MetricCard, SimpleList, EmptyState, AlertRow } from '../../admin-shell/components/AdminDashboardParts';

type AdminOverviewTabProps = {
  stats: any[];
  overview: any;
  roleDashboards: any[];
  currency: Intl.NumberFormat;
  compactCurrency: Intl.NumberFormat;
  percent: Intl.NumberFormat;
  setTab?: (tab: string) => void;
};

export default function AdminOverviewTab({
  stats,
  overview,
  roleDashboards,
  currency,
  compactCurrency,
  percent,
  setTab,
}: AdminOverviewTabProps) {

  // Minimalist clean tooltips for charts
  const renderTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm text-xs">
          <p className="font-semibold text-slate-500">Ngày {label}</p>
          <p className="mt-1 font-bold text-slate-900">
            {currency.format(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  const renderBarTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm text-xs">
          <p className="font-semibold text-slate-500">Tháng {label}</p>
          <p className="mt-1 font-bold text-indigo-600">
            {currency.format(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  // Corporate styling configs for stat cards (clean white cards with border accent)
  const cardStyles: Record<string, {
    iconColor: string;
    iconBg: string;
    borderColor: string;
  }> = {
    'Doanh thu': {
      iconColor: 'text-indigo-600',
      iconBg: 'bg-indigo-50',
      borderColor: 'hover:border-indigo-200',
    },
    'Sản phẩm': {
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-50',
      borderColor: 'hover:border-blue-200',
    },
    'Đơn hàng': {
      iconColor: 'text-sky-600',
      iconBg: 'bg-sky-50',
      borderColor: 'hover:border-sky-200',
    },
    'Khách hàng': {
      iconColor: 'text-amber-600',
      iconBg: 'bg-amber-50',
      borderColor: 'hover:border-amber-200',
    }
  };

  // Helper values for order flow pipeline
  const ordersTotal = overview?.orders?.total || 0;
  const ordersPending = overview?.orders?.pending || 0;
  const ordersProcessing = overview?.orders?.processing || 0;
  const ordersCancelled = overview?.orders?.cancelled || 0;
  const ordersRefunded = overview?.orders?.refunded || 0;
  const ordersCompleted = Math.max(0, ordersTotal - (ordersPending + ordersProcessing + ordersCancelled + ordersRefunded));

  // Quick Action Config
  const quickActions = [
    { label: 'Thêm sản phẩm', desc: 'Đăng bán sản phẩm mới', icon: PlusCircle, tab: 'products', color: 'text-blue-600 bg-blue-50/50 hover:bg-blue-50 border-blue-100' },
    { label: 'Tác vụ kho', desc: 'Đối soát và điều chỉnh kho', icon: Database, tab: 'inventory', color: 'text-sky-600 bg-sky-50/50 hover:bg-sky-50 border-sky-100' },
    { label: 'Tạo khuyến mãi', desc: 'Thiết lập mã giảm giá', icon: Percent, tab: 'vouchers', color: 'text-amber-600 bg-amber-50/50 hover:bg-amber-50 border-amber-100' },
    { label: 'Duyệt danh mục', desc: 'Cấu hình trường thông số', icon: FolderTree, tab: 'categories', color: 'text-emerald-600 bg-emerald-50/50 hover:bg-emerald-50 border-emerald-100' },
    { label: 'Duyệt phản hồi', desc: 'Kiểm duyệt đánh giá', icon: ClipboardList, tab: 'reviews', color: 'text-indigo-600 bg-indigo-50/50 hover:bg-indigo-50 border-indigo-100' },
    { label: 'Bảo mật hệ thống', desc: 'Nhật ký audit an toàn', icon: ShieldCheck, tab: 'audit', color: 'text-slate-600 bg-slate-50 hover:bg-slate-100 border-slate-200' },
  ];
  const operationalAlerts = [
    {
      label: 'Đơn pending quá lâu',
      value: overview?.orders?.pendingOverdue || overview?.orders?.pending || 0,
      detail: 'Đơn hàng chờ xác nhận cần được xử lý trước khi trễ cam kết.',
    },
    {
      label: 'Hậu mãi trễ SLA',
      value: overview?.afterSales?.slaBreached || overview?.afterSalesSlaBreached || 0,
      detail: 'Hồ sơ đổi trả/bảo hành đã vượt thời hạn xử lý.',
    },
    {
      label: 'Tồn kho trên 180 ngày',
      value: overview?.inventoryAging?.over180Days || overview?.oldInventoryCount || 0,
      detail: 'Lô tồn lâu cần kiểm tra khuyến mãi, điều chuyển hoặc thanh lý.',
    },
    {
      label: 'Voucher sắp hết hạn',
      value: overview?.vouchers?.expiringSoon || overview?.riskyVoucherCount || 0,
      detail: 'Voucher gần hết hạn hoặc đã dùng quá 80% ngân sách.',
    },
    {
      label: 'IMEI lỗi chưa định đoạt',
      value: overview?.afterSales?.defectivePending || overview?.defectivePendingCount || 0,
      detail: 'IMEI lỗi còn chờ RTV, thanh lý, hủy hoặc xuất khỏi hệ thống.',
    },
    {
      label: 'Sản phẩm sắp hết hàng',
      value: overview?.lowStockCount || 0,
      detail: 'Tồn kho bé hơn hoặc bằng ngưỡng an toàn.',
    },
  ];

  return (
    <div className="space-y-6 text-slate-800">

      {/* Clean Corporate Light Header */}
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight sm:text-2xl">Tổng quan điều hành</h2>
          <p className="mt-1 text-sm text-slate-500 font-medium">Báo cáo tình hình kinh doanh, luồng vận hành đơn hàng và cảnh báo hệ thống.</p>
        </div>
        <div className="flex items-center gap-2 self-start rounded-lg border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-600 shadow-sm">
          <span>Hôm nay:</span>
          <span className="font-bold text-slate-900">
            {new Date().toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })}
          </span>
        </div>
      </div>

      {/* Clean Light Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const style = cardStyles[item.label] || cardStyles['Doanh thu'];
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className={`rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-md ${style.borderColor}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{item.label}</span>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${style.iconBg} ${style.iconColor}`}>
                  <Icon className="h-4.5 w-4.5" />
                </div>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl font-bold text-slate-900 tracking-tight">{item.value}</div>
                <p className="mt-1.5 text-[11px] font-medium text-slate-500 leading-normal">{item.caption}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Operations Grid: Order Fulfillment Flow & Quick Shortcuts */}
      <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">

        {/* Order Fulfillment Flow */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="h-4.5 w-4.5 text-slate-600" /> Tiến độ đơn hàng hôm nay
                </h3>
                <p className="text-xs text-slate-400 font-medium">Theo dõi luồng xử lý trên tổng số {ordersTotal} đơn hàng.</p>
              </div>
              <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600 uppercase">Live</span>
            </div>

            {/* Simple Step-by-step Pipeline Progress Bar */}
            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-3 text-center">
                <span className="text-xs font-bold text-amber-600">Chờ xác nhận</span>
                <div className="mt-1 text-xl font-bold text-slate-900">{ordersPending}</div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-3 text-center">
                <span className="text-xs font-bold text-blue-600">Đang đóng gói</span>
                <div className="mt-1 text-xl font-bold text-slate-900">{ordersProcessing}</div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-3 text-center">
                <span className="text-xs font-bold text-emerald-600">Đã hoàn thành</span>
                <div className="mt-1 text-xl font-bold text-slate-900">{ordersCompleted}</div>
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 grid-cols-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Sản phẩm hết/sắp hết</span>
              <div className="mt-0.5 text-lg font-bold text-slate-900">{overview?.lowStockCount || 0}</div>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Đánh giá mới chờ duyệt</span>
              <div className="mt-0.5 text-lg font-bold text-slate-900">{overview?.reviews?.pending || 0}</div>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Voucher hoạt động</span>
              <div className="mt-0.5 text-lg font-bold text-slate-900">{overview?.vouchers?.active || 0}</div>
            </div>
          </div>
        </div>

        {/* Quick Shortcuts */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Zap className="h-4.5 w-4.5 text-slate-600" /> Phím tắt tác vụ nhanh
            </h3>
            <p className="text-xs text-slate-400 font-medium">Lối tắt thao tác nhanh dành cho Admin.</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {quickActions.map((action) => {
              const ActionIcon = action.icon;
              return (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => setTab?.(action.tab)}
                  className={`flex items-center gap-2.5 p-2.5 rounded-lg border border-slate-200 bg-white text-left transition-colors duration-150 hover:bg-slate-50 cursor-pointer`}
                >
                  <div className={`p-1.5 rounded ${action.color} border shrink-0`}>
                    <ActionIcon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-slate-950 truncate">{action.label}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Revenue Charts Section */}
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">

        {/* Line Chart */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="h-4.5 w-4.5 text-indigo-600" /> Báo cáo doanh số 14 ngày qua
            </h3>
            <p className="text-xs text-slate-400 font-medium">Tổng quan doanh thu theo ngày gần nhất.</p>
          </div>
          <div className="min-h-72 min-w-0">
            <ResponsiveContainer width="100%" height={288} minWidth={0}>
              <AreaChart data={overview?.revenueByDay || []} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="adminRevenueLight" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.12} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f8fafc" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fontWeight: 600 }} stroke="#94a3b8" tickLine={false} axisLine={false} />
                <YAxis
                  tickFormatter={(value) => compactCurrency.format(Number(value))}
                  tick={{ fontSize: 10, fontWeight: 600 }}
                  stroke="#94a3b8"
                  width={52}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={renderTooltip} />
                <Area type="monotone" dataKey="total" stroke="#4f46e5" strokeWidth={2} fill="url(#adminRevenueLight)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar Chart */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="h-4.5 w-4.5 text-slate-600" /> Doanh số tích lũy tháng
            </h3>
            <p className="text-xs text-slate-400 font-medium">Báo cáo so sánh doanh số 6 tháng gần nhất.</p>
          </div>
          <div className="min-h-72 min-w-0">
            <ResponsiveContainer width="100%" height={288} minWidth={0}>
              <BarChart data={overview?.revenueByMonth || []} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f8fafc" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 10, fontWeight: 600 }} stroke="#94a3b8" tickLine={false} axisLine={false} />
                <YAxis
                  tickFormatter={(value) => compactCurrency.format(Number(value))}
                  tick={{ fontSize: 10, fontWeight: 600 }}
                  stroke="#94a3b8"
                  width={52}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={renderBarTooltip} />
                <Bar dataKey="total" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Top Selling, Refund Stats, System Alerts */}
      <div className="grid gap-5 xl:grid-cols-3">
        {/* Top Selling Products */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm flex flex-col justify-between">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShoppingBag className="h-4.5 w-4.5 text-slate-600" /> Top sản phẩm bán chạy
            </h3>
            <p className="text-xs text-slate-400 font-medium">Top 5 sản phẩm có doanh số bán cao nhất.</p>
          </div>

          <div className="space-y-2 flex-1">
            {(overview?.topProducts || []).map((product: any, index: number) => (
              <div
                key={product.id || product.name}
                className="flex items-center justify-between border-b border-slate-100 pb-2.5 last:border-b-0 last:pb-0"
              >
                <div className="min-w-0 flex-1 pr-3">
                  <div className="truncate text-xs font-bold text-slate-800" title={product.name}>{product.name}</div>
                  <div className="text-[10px] font-semibold text-slate-400 mt-0.5">{product.soldCount} sản phẩm đã bán</div>
                </div>
                <span className="text-xs font-bold text-slate-700 shrink-0">{compactCurrency.format(product.periodRevenue || 0)}</span>
              </div>
            ))}
            {(!overview?.topProducts || overview.topProducts.length === 0) && <EmptyState text="Chưa có dữ liệu bán chạy." />}
          </div>
        </div>

        {/* Refund & Cancel rates */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm flex flex-col justify-between">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <RotateCcw className="h-4.5 w-4.5 text-slate-600" /> Chỉ số hoàn hủy đơn hàng
            </h3>
            <p className="text-xs text-slate-400 font-medium">Báo cáo thống kê hiệu suất hủy và trả đơn.</p>
          </div>

          <div className="grid grid-cols-2 gap-3 flex-1 content-center">
            <div className="rounded-lg border border-slate-150 bg-slate-50/50 p-3.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tỉ lệ hủy đơn</span>
              <div className="mt-1 text-2xl font-bold text-slate-900">
                {overview?.orders?.total ? percent.format((overview.orders.cancelled || 0) / overview.orders.total) : '0%'}
              </div>
              <span className="text-[10px] font-medium text-slate-500 block mt-1">{overview?.orders?.cancelled || 0} đơn đã hủy</span>
            </div>

            <div className="rounded-lg border border-slate-150 bg-slate-50/50 p-3.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tỉ lệ hoàn trả</span>
              <div className="mt-1 text-2xl font-bold text-slate-900">
                {overview?.orders?.total ? percent.format((overview.orders.refunded || 0) / overview.orders.total) : '0%'}
              </div>
              <span className="text-[10px] font-medium text-slate-500 block mt-1">{overview?.orders?.refunded || 0} đơn hoàn tiền</span>
            </div>
          </div>
        </div>

        {/* Operating Alerts */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm flex flex-col justify-between">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="h-4.5 w-4.5 text-slate-600" /> Cảnh báo vận hành hệ thống
            </h3>
            <p className="text-xs text-slate-400 font-medium">Các điểm nghẽn cần xử lý trong bán hàng, kho và hậu mãi.</p>
          </div>

          <div className="space-y-2 flex-1 justify-center content-center">
            {operationalAlerts.map((alert) => (
              <AlertRow key={alert.label} label={alert.label} value={alert.value} detail={alert.detail} />
            ))}
          </div>
        </div>
      </div>

      {/* Role-based Dashboard Widgets */}
      <div className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="h-4.5 w-4.5 text-slate-600" /> Trạng thái phân hệ quản trị
          </h3>
          <p className="text-xs text-slate-400 font-medium font-semibold">Chỉ số thống kê phân bổ theo vai trò được cấu hình.</p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {roleDashboards.map((item) => {
            const Icon = item.icon || Boxes;
            return (
              <div key={item.role} className="rounded-lg border border-slate-200/60 bg-slate-50/20 p-4 hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  <Icon className="h-4 w-4 text-slate-400" />
                  {item.role}
                </div>
                <div className="mt-1 text-lg font-bold text-slate-900">{item.metric}</div>
                <p className="mt-1 text-xs text-slate-500 font-medium">{item.helper}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
