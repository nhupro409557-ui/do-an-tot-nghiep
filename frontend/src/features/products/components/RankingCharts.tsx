import { TrendingDown, TrendingUp, X } from 'lucide-react';
// react-doctor-disable-next-line react-doctor/prefer-dynamic-import -- This module is imported only through React.lazy in RankingsPage.
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function RankingSparkline({ data, isPositive }: { data: number[]; isPositive: boolean }) {
  if (!data || data.length === 0) return null;

  const chartData = data.map((value, index) => ({ name: index, value }));
  const strokeColor = isPositive ? '#10B981' : '#EF4444';
  const gradientId = isPositive ? 'colorGreen' : 'colorRed';

  return (
    <div className="h-16 w-36">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <defs>
            <linearGradient id="colorGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorRed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EF4444" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="name" hide />
          <YAxis hide domain={['dataMin - 5', 'dataMax + 5']} />
          <Tooltip
            cursor={{ stroke: 'rgba(0,0,0,0.05)', strokeWidth: 1, strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-lg bg-slate-900 px-2.5 py-1 text-xs font-bold text-white shadow-sm">
                  {payload[0].value}
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={strokeColor}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: strokeColor }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RankingChartModal({ detail, onClose }: { detail: any; onClose: () => void }) {
  const chartData = (detail.historyData?.length ? detail.historyData : [0]).map((value: number, index: number) => ({
    name: index + 1,
    value,
  }));
  const strokeColor = detail.isUp ? '#10B981' : '#EF4444';

  return (
    <div className="fixed inset-0 z-[1000] flex items-end justify-center bg-slate-950/50 px-3 py-4 backdrop-blur-sm sm:items-center">
      <button type="button" className="absolute inset-0 cursor-default" onClick={onClose} aria-label="Đóng biểu đồ" />
      <div className="relative w-full max-w-lg rounded-2xl bg-white p-4 shadow-2xl ring-1 ring-slate-200 sm:p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Biểu đồ xếp hạng</p>
            <h3 className="mt-1 line-clamp-2 text-base font-black text-slate-900 sm:text-lg">{detail.productName}</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                {detail.metric?.icon}
                {detail.metric?.label}
              </span>
              <span className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold ${detail.isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
                {detail.isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {Math.abs(Number(detail.trendPercent || 0))}%
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
            aria-label="Đóng"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        <div className="h-56 rounded-2xl bg-slate-50 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="rankingDetailGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={strokeColor} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={36} />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke={strokeColor} strokeWidth={3} fill="url(#rankingDetailGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
