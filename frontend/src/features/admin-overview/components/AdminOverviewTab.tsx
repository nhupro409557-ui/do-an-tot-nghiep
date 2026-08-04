import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Boxes,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Database,
  FolderTree,
  PackageOpen,
  Percent,
  PlusCircle,
  RotateCcw,
  ShieldCheck,
  ShoppingBag,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState } from '../../admin-shell/components/AdminDashboardParts';

type AdminOverviewTabProps = {
  stats: any[];
  overview: any;
  roleDashboards: any[];
  currency: Intl.NumberFormat;
  compactCurrency: Intl.NumberFormat;
  percent: Intl.NumberFormat;
  setTab?: (tab: string) => void;
};

const statToneStyles: Record<string, {
  accent: string;
  icon: string;
  iconBackground: string;
  value: string;
}> = {
  emerald: {
    accent: 'bg-emerald-500',
    icon: 'text-emerald-700',
    iconBackground: 'bg-emerald-50 ring-emerald-100',
    value: 'text-emerald-950',
  },
  amber: {
    accent: 'bg-amber-500',
    icon: 'text-amber-700',
    iconBackground: 'bg-amber-50 ring-amber-100',
    value: 'text-amber-950',
  },
  red: {
    accent: 'bg-rose-500',
    icon: 'text-rose-700',
    iconBackground: 'bg-rose-50 ring-rose-100',
    value: 'text-rose-950',
  },
  sky: {
    accent: 'bg-sky-500',
    icon: 'text-sky-700',
    iconBackground: 'bg-sky-50 ring-sky-100',
    value: 'text-sky-950',
  },
  indigo: {
    accent: 'bg-indigo-500',
    icon: 'text-indigo-700',
    iconBackground: 'bg-indigo-50 ring-indigo-100',
    value: 'text-indigo-950',
  },
};

const defaultStatTone = statToneStyles.indigo;

export default function AdminOverviewTab({
  stats,
  overview,
  roleDashboards,
  currency,
  compactCurrency,
  percent,
  setTab,
}: AdminOverviewTabProps) {
  const renderTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;

    return (
      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs shadow-xl shadow-slate-900/10">
        <p className="font-medium text-slate-500">Ngày {label}</p>
        <p className="mt-1 text-sm font-bold tabular-nums text-slate-950">
          {currency.format(payload[0].value)}
        </p>
      </div>
    );
  };

  const renderBarTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;

    return (
      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs shadow-xl shadow-slate-900/10">
        <p className="font-medium text-slate-500">Tháng {label}</p>
        <p className="mt-1 text-sm font-bold tabular-nums text-indigo-700">
          {currency.format(payload[0].value)}
        </p>
      </div>
    );
  };

  const ordersTotal = Number(overview?.orders?.total || 0);
  const ordersPending = Number(overview?.orders?.pending || 0);
  const ordersProcessing = Number(overview?.orders?.processing || 0);
  const ordersCancelled = Number(overview?.orders?.cancelled || 0);
  const ordersRefunded = Number(overview?.orders?.refunded || 0);
  const ordersCompleted = Math.max(0, ordersTotal - (ordersPending + ordersProcessing + ordersCancelled + ordersRefunded));
  const cancellationRate = ordersTotal ? ordersCancelled / ordersTotal : 0;
  const refundRate = ordersTotal ? ordersRefunded / ordersTotal : 0;
  const completionRate = ordersTotal ? ordersCompleted / ordersTotal : 0;

  const orderStages = [
    {
      label: 'Chờ xác nhận',
      value: ordersPending,
      percentage: ordersTotal ? Math.min(100, (ordersPending / ordersTotal) * 100) : 0,
      text: 'text-amber-700',
      background: 'bg-amber-500',
      surface: 'bg-amber-50/70',
    },
    {
      label: 'Đang xử lý',
      value: ordersProcessing,
      percentage: ordersTotal ? Math.min(100, (ordersProcessing / ordersTotal) * 100) : 0,
      text: 'text-sky-700',
      background: 'bg-sky-500',
      surface: 'bg-sky-50/70',
    },
    {
      label: 'Đã hoàn thành',
      value: ordersCompleted,
      percentage: ordersTotal ? Math.min(100, (ordersCompleted / ordersTotal) * 100) : 0,
      text: 'text-emerald-700',
      background: 'bg-emerald-500',
      surface: 'bg-emerald-50/70',
    },
  ];

  const quickActions = [
    { label: 'Thêm sản phẩm', description: 'Đăng bán sản phẩm mới', icon: PlusCircle, tab: 'products', iconClass: 'bg-blue-50 text-blue-700 ring-blue-100' },
    { label: 'Tác vụ kho', description: 'Đối soát và điều chỉnh kho', icon: Database, tab: 'inventory', iconClass: 'bg-sky-50 text-sky-700 ring-sky-100' },
    { label: 'Tạo khuyến mãi', description: 'Thiết lập mã giảm giá', icon: Percent, tab: 'vouchers', iconClass: 'bg-amber-50 text-amber-700 ring-amber-100' },
    { label: 'Duyệt danh mục', description: 'Cấu hình trường thông số', icon: FolderTree, tab: 'categories', iconClass: 'bg-emerald-50 text-emerald-700 ring-emerald-100' },
    { label: 'Duyệt phản hồi', description: 'Kiểm duyệt đánh giá', icon: ClipboardList, tab: 'reviews', iconClass: 'bg-violet-50 text-violet-700 ring-violet-100' },
    { label: 'Bảo mật hệ thống', description: 'Theo dõi nhật ký an toàn', icon: ShieldCheck, tab: 'audit', iconClass: 'bg-slate-100 text-slate-700 ring-slate-200' },
  ];

  const operationalAlerts = [
    {
      label: 'Đơn chờ xử lý quá lâu',
      value: overview?.orders?.pendingOverdue || overview?.orders?.pending || 0,
      detail: 'Đơn hàng chờ xác nhận cần được xử lý trước khi trễ cam kết.',
    },
    {
      label: 'Hậu mãi trễ SLA',
      value: overview?.afterSales?.slaBreached || overview?.afterSalesSlaBreached || 0,
      detail: 'Hồ sơ đổi trả hoặc bảo hành đã vượt thời hạn xử lý.',
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
      detail: 'IMEI lỗi còn chờ trả nhà cung cấp, thanh lý, hủy hoặc xuất kho.',
    },
    {
      label: 'Sản phẩm sắp hết hàng',
      value: overview?.lowStockCount || 0,
      detail: 'Tồn kho đang thấp hơn hoặc bằng ngưỡng an toàn.',
    },
  ];

  const dailyRevenue = overview?.revenueByDay || [];
  const monthlyRevenue = overview?.revenueByMonth || [];
  const topProducts = overview?.topProducts || [];
  const operationalAlertTotal = operationalAlerts.reduce((total, alert) => total + Number(alert.value || 0), 0);
  const formattedDate = new Date().toLocaleDateString('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });

  return (
    <div className="space-y-5 text-slate-800 sm:space-y-6">
      <section className="relative overflow-hidden rounded-3xl border border-indigo-100 bg-gradient-to-br from-white via-indigo-50/70 to-sky-50 px-5 py-6 text-slate-900 shadow-xl shadow-indigo-900/5 sm:px-7 sm:py-7">
        <div aria-hidden="true" className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-indigo-200/40 to-transparent" />
        <div aria-hidden="true" className="absolute -right-14 -top-16 h-48 w-48 rounded-full border-[28px] border-indigo-200/35" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">
              <Activity className="h-4 w-4" />
              Trung tâm vận hành
            </div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Tổng quan điều hành</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600 sm:text-base">
              Một góc nhìn tập trung về kinh doanh, đơn hàng, tồn kho và các điểm cần ưu tiên xử lý.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row lg:flex-col lg:items-end">
            <div className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-indigo-100 bg-white/80 px-3.5 text-sm font-medium text-slate-700 shadow-sm">
              <CalendarDays className="h-4 w-4 text-indigo-600" />
              <span className="first-letter:uppercase">{formattedDate}</span>
            </div>
            <div className={`inline-flex min-h-9 items-center gap-2 self-start rounded-full px-3 text-xs font-semibold lg:self-end ${
              operationalAlertTotal > 0 ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-700'
            }`}>
              {operationalAlertTotal > 0 ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
              {operationalAlertTotal > 0 ? `${operationalAlertTotal} điểm cần lưu ý` : 'Vận hành ổn định'}
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Các chỉ số kinh doanh chính" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {stats.map((item) => {
          const style = statToneStyles[item.tone] || defaultStatTone;
          const Icon = item.icon;

          return (
            <article
              key={item.label}
              className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition duration-200 hover:border-slate-300 hover:shadow-lg hover:shadow-slate-900/5 motion-reduce:transition-none"
            >
              <div aria-hidden="true" className={`absolute inset-x-0 top-0 h-1 ${style.accent}`} />
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{item.label}</p>
                  <p className={`mt-3 text-2xl font-bold tracking-tight tabular-nums sm:text-[1.7rem] ${style.value}`}>{item.value}</p>
                </div>
                <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1 ${style.iconBackground} ${style.icon}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <p className="mt-3 border-t border-slate-100 pt-3 text-xs font-medium leading-5 text-slate-500">{item.caption}</p>
            </article>
          );
        })}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100">
                  <Activity className="h-4 w-4" />
                </span>
                <div>
                  <h2 className="font-bold text-slate-950">Luồng xử lý đơn hàng</h2>
                  <p className="mt-0.5 text-xs text-slate-500">Theo dõi trạng thái trên tổng số {ordersTotal} đơn trong vùng dữ liệu.</p>
                </div>
              </div>
            </div>
            <span className="inline-flex self-start rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
              Hoàn tất {percent.format(completionRate)}
            </span>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {orderStages.map((stage) => (
              <div key={stage.label} className={`rounded-xl border border-slate-100 p-4 ${stage.surface}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-xs font-bold ${stage.text}`}>{stage.label}</span>
                  <span className="text-lg font-bold tabular-nums text-slate-950">{stage.value}</span>
                </div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white ring-1 ring-slate-200/70">
                  <div className={`h-full rounded-full ${stage.background}`} style={{ width: `${stage.percentage}%` }} />
                </div>
                <p className="mt-2 text-xs font-medium text-slate-500">{percent.format(stage.percentage / 100)} tổng đơn</p>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-3 border-t border-slate-100 pt-5 sm:grid-cols-3">
            {[
              { label: 'Sản phẩm sắp hết', value: overview?.lowStockCount || 0, icon: PackageOpen },
              { label: 'Đánh giá chờ duyệt', value: overview?.reviews?.pending || 0, icon: ClipboardList },
              { label: 'Voucher hoạt động', value: overview?.vouchers?.active || 0, icon: Percent },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3.5 py-3">
                  <Icon className="h-4 w-4 shrink-0 text-slate-500" />
                  <div className="min-w-0">
                    <p className="text-lg font-bold tabular-nums text-slate-950">{item.value}</p>
                    <p className="truncate text-xs font-medium text-slate-500">{item.label}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-50 text-amber-700 ring-1 ring-amber-100">
              <Zap className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-bold text-slate-950">Tác vụ nhanh</h2>
              <p className="mt-0.5 text-xs text-slate-500">Đi thẳng đến công việc thường dùng.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
            {quickActions.map((action) => {
              const ActionIcon = action.icon;
              return (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => setTab?.(action.tab)}
                  aria-label={`${action.label}: ${action.description}`}
                  className="group flex min-h-14 w-full cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left transition duration-200 hover:border-indigo-200 hover:bg-indigo-50/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 motion-reduce:transition-none"
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1 ${action.iconClass}`}>
                    <ActionIcon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-xs font-bold text-slate-900">{action.label}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{action.description}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-600 motion-reduce:transform-none motion-reduce:transition-none" />
                </button>
              );
            })}
          </div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="min-w-0 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100">
                <TrendingUp className="h-4 w-4" />
              </span>
              <div>
                <h2 className="font-bold text-slate-950">Xu hướng doanh thu</h2>
                <p className="mt-0.5 text-xs text-slate-500">Biến động doanh thu theo ngày gần nhất.</p>
              </div>
            </div>
            <span className="self-start rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700">14 ngày</span>
          </div>

          {dailyRevenue.length > 0 ? (
            <div className="h-72 min-w-0" role="img" aria-label="Biểu đồ xu hướng doanh thu trong 14 ngày gần nhất">
              <AreaChart
                responsive
                className="h-full w-full min-w-0"
                data={dailyRevenue}
                margin={{ top: 8, right: 8, left: -18, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="adminRevenueArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.22} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fontWeight: 600 }} stroke="#94a3b8" tickLine={false} axisLine={false} />
                <YAxis
                  tickFormatter={(value) => compactCurrency.format(Number(value))}
                  tick={{ fontSize: 11, fontWeight: 600 }}
                  stroke="#94a3b8"
                  width={56}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={renderTooltip} />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  fill="url(#adminRevenueArea)"
                  activeDot={{ r: 5, fill: '#4f46e5', stroke: '#ffffff', strokeWidth: 3 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </div>
          ) : (
            <div className="flex h-72 items-center justify-center"><EmptyState text="Chưa có dữ liệu doanh thu theo ngày." /></div>
          )}
        </article>

        <article className="min-w-0 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-50 text-sky-700 ring-1 ring-sky-100">
                <BarChart3 className="h-4 w-4" />
              </span>
              <div>
                <h2 className="font-bold text-slate-950">Doanh thu tích lũy</h2>
                <p className="mt-0.5 text-xs text-slate-500">So sánh hiệu suất theo tháng.</p>
              </div>
            </div>
            <span className="self-start rounded-full bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">6 tháng</span>
          </div>

          {monthlyRevenue.length > 0 ? (
            <div className="h-72 min-w-0" role="img" aria-label="Biểu đồ so sánh doanh thu trong 6 tháng gần nhất">
              <BarChart
                responsive
                className="h-full w-full min-w-0"
                data={monthlyRevenue}
                margin={{ top: 8, right: 8, left: -18, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fontWeight: 600 }} stroke="#94a3b8" tickLine={false} axisLine={false} />
                <YAxis
                  tickFormatter={(value) => compactCurrency.format(Number(value))}
                  tick={{ fontSize: 11, fontWeight: 600 }}
                  stroke="#94a3b8"
                  width={56}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={renderBarTooltip} cursor={{ fill: '#f8fafc' }} />
                <Bar dataKey="total" fill="#6366f1" radius={[6, 6, 2, 2]} maxBarSize={30} isAnimationActive={false} />
              </BarChart>
            </div>
          ) : (
            <div className="flex h-72 items-center justify-center"><EmptyState text="Chưa có dữ liệu doanh thu theo tháng." /></div>
          )}
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-rose-50 text-rose-700 ring-1 ring-rose-100">
              <ShoppingBag className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-bold text-slate-950">Sản phẩm bán chạy</h2>
              <p className="mt-0.5 text-xs text-slate-500">Xếp hạng theo doanh thu kỳ hiện tại.</p>
            </div>
          </div>

          <div className="mt-5 space-y-1.5">
            {topProducts.map((product: any, index: number) => (
              <div key={product.id || product.name} className="group flex items-center gap-3 rounded-xl px-2 py-2.5 transition hover:bg-slate-50">
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                  index === 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                }`}>
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900" title={product.name}>{product.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{product.soldCount || 0} sản phẩm đã bán</p>
                </div>
                <span className="shrink-0 text-xs font-bold tabular-nums text-slate-700">
                  {compactCurrency.format(product.periodRevenue || 0)}
                </span>
              </div>
            ))}
            {topProducts.length === 0 && <EmptyState text="Chưa có dữ liệu bán chạy." />}
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50 text-violet-700 ring-1 ring-violet-100">
              <RotateCcw className="h-4 w-4" />
            </span>
            <div>
              <h2 className="font-bold text-slate-950">Chất lượng đơn hàng</h2>
              <p className="mt-0.5 text-xs text-slate-500">Tỷ lệ hoàn tất, hủy và hoàn tiền.</p>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-teal-50 p-5 text-slate-900">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Tỷ lệ hoàn tất</p>
                <p className="mt-2 text-3xl font-bold tabular-nums">{percent.format(completionRate)}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-emerald-100">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, completionRate * 100)}%` }} />
            </div>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-rose-100 bg-rose-50/70 p-3.5">
              <p className="text-xs font-bold text-rose-700">Tỷ lệ hủy</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-rose-950">{percent.format(cancellationRate)}</p>
              <p className="mt-1 text-xs text-rose-700/80">{ordersCancelled} đơn đã hủy</p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/70 p-3.5">
              <p className="text-xs font-bold text-amber-700">Tỷ lệ hoàn tiền</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-amber-950">{percent.format(refundRate)}</p>
              <p className="mt-1 text-xs text-amber-700/80">{ordersRefunded} đơn hoàn tiền</p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-50 text-amber-700 ring-1 ring-amber-100">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <div>
                <h2 className="font-bold text-slate-950">Cảnh báo vận hành</h2>
                <p className="mt-0.5 text-xs text-slate-500">Các điểm nghẽn cần ưu tiên xử lý.</p>
              </div>
            </div>
            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold tabular-nums text-amber-800">{operationalAlertTotal}</span>
          </div>

          <div className="mt-5 space-y-2">
            {operationalAlerts.map((alert) => {
              const hasAlert = Number(alert.value || 0) > 0;
              return (
                <div key={alert.label} className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
                  <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                    hasAlert ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {hasAlert ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-bold text-slate-800">{alert.label}</p>
                      <span className={`text-sm font-bold tabular-nums ${hasAlert ? 'text-amber-800' : 'text-emerald-700'}`}>{alert.value}</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{alert.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700 ring-1 ring-slate-200">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <div>
            <h2 className="font-bold text-slate-950">Trạng thái phân hệ quản trị</h2>
            <p className="mt-0.5 text-xs text-slate-500">Chỉ số tổng hợp theo phạm vi và vai trò quản trị.</p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {roleDashboards.map((item) => {
            const Icon = item.icon || Boxes;
            return (
              <article key={item.role} className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                  <Icon className="h-4 w-4 text-slate-500" />
                  {item.role}
                </div>
                <p className="mt-3 text-xl font-bold tabular-nums text-slate-950">{item.metric}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{item.helper}</p>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
