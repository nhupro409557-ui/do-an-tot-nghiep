import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Flame, Eye, Heart, Search, ShoppingBag, Star, Activity, BarChart2, Trophy, Filter, TrendingUp, TrendingDown, ChevronDown } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, YAxis, XAxis, Tooltip } from 'recharts';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { categoryApi } from '../../../services/categoryApi';
import { publicApi } from '../../../services/publicApi';

type RankingCriteria = 'trending' | 'search' | 'view' | 'like' | 'sold' | 'rating';
type TimeRange = '24h' | '7d' | '30d' | '1y';

const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });

const criteriaOptions: { value: RankingCriteria; label: string; icon: React.ReactNode; color: string; bg: string; hex: string }[] = [
  { value: 'trending', label: 'Xu hướng hiện tại', icon: <Flame className="h-5 w-5" />, color: 'text-red-500', bg: 'bg-red-50', hex: '#ef4444' },
  { value: 'search', label: 'Tìm kiếm nhiều nhất', icon: <Search className="h-5 w-5" />, color: 'text-blue-500', bg: 'bg-blue-50', hex: '#3b82f6' },
  { value: 'view', label: 'Lượt xem nhiều nhất', icon: <Eye className="h-5 w-5" />, color: 'text-purple-500', bg: 'bg-purple-50', hex: '#a855f7' },
  { value: 'like', label: 'Được yêu thích nhất', icon: <Heart className="h-5 w-5" />, color: 'text-pink-500', bg: 'bg-pink-50', hex: '#ec4899' },
  { value: 'sold', label: 'Bán chạy nhất', icon: <ShoppingBag className="h-5 w-5" />, color: 'text-emerald-500', bg: 'bg-emerald-50', hex: '#10b981' },
  { value: 'rating', label: 'Đánh giá cao nhất', icon: <Star className="h-5 w-5" />, color: 'text-amber-500', bg: 'bg-amber-50', hex: '#f59e0b' },
];

const timeRangeOptions: { value: TimeRange; label: string }[] = [
  { value: '24h', label: '24 giờ qua' },
  { value: '7d', label: '7 ngày qua' },
  { value: '30d', label: '30 ngày qua' },
  { value: '1y', label: '1 năm qua' },
];

function rankingCategoryValue(category: any) {
  return category?.slug || category?.id || category?.name || 'all';
}

function flattenRankingCategories(categories: any[]) {
  return categories.flatMap((category) => [
    { ...category, depth: 0 },
    ...(category.children || []).map((child: any) => ({ ...child, depth: 1 })),
  ]);
}

function salePrice(product: any) {
  return Number(product.discountPrice || product.salePrice || product.price || 0);
}

function originalPrice(product: any) {
  return Number(product.price || product.originalPrice || salePrice(product));
}

function discountPercent(product: any) {
  const original = originalPrice(product);
  const sale = salePrice(product);
  if (!original || sale >= original) return 0;
  return Math.round(((original - sale) / original) * 100);
}

function metricByRange(product: any, base: string, timeRange: TimeRange) {
  const suffix = timeRange === '24h' ? '24h' : timeRange;
  return Number(product?.[`${base}${suffix}`] ?? 0);
}

// Recharts Sparkline Component
function Sparkline({ data, isPositive }: { data: number[]; isPositive: boolean }) {
  if (!data || data.length === 0) return null;
  
  const chartData = data.map((val, i) => ({ name: i, value: val }));
  const strokeColor = isPositive ? '#10B981' : '#EF4444'; // Emerald for positive, Red for negative
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
              if (active && payload && payload.length) {
                return (
                  <div className="rounded-lg shadow-sm bg-slate-900 text-white text-xs px-2.5 py-1 font-bold">
                    {payload[0].value}
                  </div>
                );
              }
              return null;
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

export default function RankingsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [criteria, setCriteria] = useState<RankingCriteria>('trending');
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [isCatOpen, setIsCatOpen] = useState(false);

  useEffect(() => {
    categoryApi.listCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    publicApi.listRankings({ period: timeRange, criteria, category: selectedCategory, limit: 20 })
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [criteria, selectedCategory, timeRange]);

  const activeCriteria = criteriaOptions.find((opt) => opt.value === criteria) || criteriaOptions[0];
  const categoryOptions = flattenRankingCategories(categories);

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Hero Section */}
      <div className="bg-white px-4 py-12 sm:px-6 lg:px-8 shadow-sm">
        <div className="mx-auto max-w-5xl">
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-600">
              <Activity className="h-4 w-4" />
              <span>Cập nhật liên tục</span>
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
              Bảng xếp hạng <span className="text-primary">Thịnh hành</span>
            </h1>
            <p className="mt-4 max-w-2xl text-lg text-slate-500">
              Khám phá ngay những sản phẩm đang được quan tâm nhiều nhất. Dữ liệu được tổng hợp từ lượt tìm kiếm, lượt xem và tương tác trên toàn hệ thống.
            </p>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-8 max-w-5xl px-4 sm:px-6 lg:px-8">
        
        {/* Controls: Time & Category */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          {/* Custom Category Dropdown */}
          <div className="relative w-full sm:w-64">
            <button
              type="button"
              onClick={() => setIsCatOpen(!isCatOpen)}
              className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 focus:border-red-500 focus:ring-4 focus:ring-red-500/10"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Filter className="h-4.5 w-4.5 text-slate-400 shrink-0" />
                <span className="truncate">
                  {selectedCategory === 'all' 
                    ? 'Tất cả danh mục' 
                    : categoryOptions.find(c => rankingCategoryValue(c) === selectedCategory)?.name || 'Tất cả danh mục'}
                </span>
              </div>
              <ChevronDown className={`h-4 w-4 text-slate-400 shrink-0 transition-transform duration-200 ${isCatOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isCatOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setIsCatOpen(false)} />
                <div className="absolute left-0 right-0 z-20 mt-2 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg shadow-slate-100 focus:outline-none">
                  <button
                    type="button"
                    onClick={() => { setSelectedCategory('all'); setIsCatOpen(false); }}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${selectedCategory === 'all' ? 'bg-red-50 text-red-600 font-bold' : 'text-slate-700 hover:bg-slate-50'}`}
                  >
                    Tất cả danh mục
                  </button>
                  {categoryOptions.map((c) => {
                    const val = rankingCategoryValue(c);
                    const isSelected = selectedCategory === val;
                    return (
                      <button
                        key={c.id || c.slug || c.name}
                        type="button"
                        onClick={() => { setSelectedCategory(val); setIsCatOpen(false); }}
                        className={`flex w-full items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors ${c.depth ? 'pl-6 text-slate-500' : 'text-slate-700'} ${isSelected ? 'bg-red-50 text-red-600 font-bold' : 'hover:bg-slate-50'}`}
                      >
                        {c.name}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          {/* Time Range Tabs */}
          <div className="flex bg-slate-100/80 p-1.5 rounded-xl w-full sm:w-auto">
            {timeRangeOptions.map((opt) => {
              const isActive = timeRange === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setTimeRange(opt.value)}
                  className={`flex-1 sm:flex-none whitespace-nowrap rounded-lg px-4 py-2 text-sm font-bold transition-all duration-200 ${
                    isActive
                      ? 'bg-white text-red-600 shadow-sm'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Filters: Criteria (Grid layout to prevent layout overflow or loss of option) */}
        <div className="mb-8">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {criteriaOptions.map((option) => {
              const isActive = criteria === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setCriteria(option.value)}
                  className={`flex items-center gap-3 rounded-xl p-2.5 text-sm font-bold transition-all duration-300 border text-left group
                    ${isActive
                      ? `${option.bg} ${option.color} border-transparent shadow-sm shadow-slate-100 ring-2 ring-red-500/10`
                      : 'bg-white text-slate-600 border-slate-100 hover:bg-slate-50/50 hover:text-slate-900 hover:border-slate-200 shadow-sm'
                    }
                  `}
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors ${isActive ? 'bg-white shadow-sm' : 'bg-slate-50 text-slate-400 group-hover:bg-slate-100 group-hover:text-slate-600'}`}>
                    {option.icon}
                  </div>
                  <span className="leading-tight text-xs md:text-sm">{option.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Rankings Content */}
        {loading ? (
          <div className="flex items-center justify-center rounded-2xl bg-white p-20 shadow-sm ring-1 ring-inset ring-slate-100">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          </div>
        ) : products.length === 0 ? (
          <EmptyState text="Không tìm thấy sản phẩm nào phù hợp với bộ lọc hiện tại." />
        ) : (
          <div className="rounded-2xl bg-white shadow-sm overflow-hidden ring-1 ring-inset ring-slate-100">
            <div className="border-b border-slate-100 bg-slate-50/50 p-4 sm:px-6 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900">
                <BarChart2 className="h-6 w-6 text-primary" />
                Top 20 {activeCriteria.label.toLowerCase()}
              </h2>
              <span className="text-sm font-medium text-slate-500 hidden sm:block">Cập nhật lúc: {new Date().toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
            
            <div className="divide-y divide-slate-100">
              {products.map((product, index) => (
                <RankingRow 
                  key={product.id} 
                  product={product} 
                  rank={index + 1} 
                  criteria={criteria}
                  timeRange={timeRange}
                  activeColor={activeCriteria.color}
                  activeBg={activeCriteria.bg}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center text-slate-500">
      <Trophy className="mx-auto mb-3 h-10 w-10 text-slate-300" />
      <div className="font-semibold">{text}</div>
    </div>
  );
}

function RankingRow({ product, rank, criteria, timeRange, activeColor, activeBg }: { product: any; rank: number; criteria: RankingCriteria; timeRange: TimeRange; activeColor: string; activeBg: string }) {
  const image = product.imageUrl || product.images?.[0];
  const discount = discountPercent(product);

  const getMetricDisplay = () => {
    switch (criteria) {
      case 'search': return { label: 'Lượt tìm kiếm', value: Number(product.searchCount || 0).toLocaleString('vi-VN'), icon: <Search className="h-3.5 w-3.5" /> };
      case 'view': return { label: 'Lượt xem', value: Number(product.viewCount || 0).toLocaleString('vi-VN'), icon: <Eye className="h-3.5 w-3.5" /> };
      case 'like': return { label: 'Lượt thích', value: metricByRange(product, 'like', timeRange).toLocaleString('vi-VN'), icon: <Heart className="h-3.5 w-3.5" /> };
      case 'sold': return { label: 'Đã bán', value: Number(product.periodSoldCount ?? product.soldCount ?? 0).toLocaleString('vi-VN'), icon: <ShoppingBag className="h-3.5 w-3.5" /> };
      case 'rating': return { label: 'Đánh giá', value: `${metricByRange(product, 'rating', timeRange).toFixed(1)} / 5.0`, icon: <Star className="h-3.5 w-3.5" /> };
      case 'trending': default: return { label: 'Điểm xu hướng', value: Number(product.trendScore || 0).toLocaleString('vi-VN'), icon: <Flame className="h-3.5 w-3.5" /> };
    }
  };

  const metric = getMetricDisplay();

  const rankColor = rank === 1 ? 'bg-gradient-to-br from-amber-400 to-yellow-500 text-white shadow-md shadow-yellow-500/25 ring-0' : 
                    rank === 2 ? 'bg-gradient-to-br from-slate-300 to-slate-500 text-white shadow-md shadow-slate-400/30 ring-0' : 
                    rank === 3 ? 'bg-gradient-to-br from-orange-400 to-amber-600 text-white shadow-md shadow-orange-500/25 ring-0' : 
                    'text-slate-400 font-semibold bg-slate-50';

  const metricValue = Number(
    criteria === 'search' ? product.searchCount :
    criteria === 'view' ? product.viewCount :
    criteria === 'like' ? metricByRange(product, 'like', timeRange) :
    criteria === 'sold' ? (product.periodSoldCount ?? product.soldCount) :
    criteria === 'rating' ? metricByRange(product, 'rating', timeRange) :
    product.trendScore
  ) || 0;
  const previousValue = Number(
    criteria === 'search' ? product.previousSearchCount :
    criteria === 'view' ? product.previousViewCount :
    criteria === 'sold' ? product.previousPeriodSoldCount :
    criteria === 'trending' ? product.previousTrendScore :
    criteria === 'rating' ? product.rating :
    product.previousPeriodLikeCount
  ) || 0;
  const trendPercent = criteria === 'rating'
    ? Math.round((metricValue / 5) * 100)
    : previousValue > 0
      ? Math.round(((metricValue - previousValue) / previousValue) * 100)
      : (metricValue > 0 ? 100 : 0);
  const isUp = trendPercent >= 0;
  const historyData = Array.isArray(product.history)
    ? product.history.map((point: any) => Number(
        criteria === 'search' ? point.searchCount :
        criteria === 'view' ? point.viewCount :
        criteria === 'like' ? point.likeCount :
        criteria === 'sold' ? point.periodSoldCount :
        criteria === 'trending' ? point.trendScore :
        metricValue
      ) || 0)
    : [];

  return (
    <Link 
      to={`/product/${product.id || product.slug}`} 
      className="group flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 sm:px-6 transition-all duration-300 hover:bg-slate-50/80 relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-0 before:bg-red-500 before:transition-all before:duration-300 hover:before:w-1 overflow-hidden"
    >
      {/* Rank Number */}
      <div className="flex items-center gap-4 w-full sm:w-auto">
        <div className={`flex h-10 w-10 sm:h-12 sm:w-12 shrink-0 items-center justify-center rounded-xl text-lg sm:text-xl font-black transition-transform duration-300 group-hover:scale-105 ${rankColor}`}>
          {rank}
        </div>
        
        {/* Mobile Layout Title */}
        <div className="min-w-0 flex-1 sm:hidden">
          <div className="truncate font-bold text-slate-900 group-hover:text-red-600 transition-colors">{product.name}</div>
          <div className="text-sm text-slate-500">{product.category || product.brand || 'Sản phẩm'}</div>
        </div>
      </div>

      {/* Image */}
      <div className="flex h-20 w-20 sm:h-16 sm:w-16 shrink-0 items-center justify-center rounded-xl bg-white p-2 border border-slate-100 shadow-sm mx-auto sm:mx-0 overflow-hidden">
        {image ? (
          <ImageWithFallback src={image} alt={product.name} className="h-full w-full object-contain group-hover:scale-110 transition-transform duration-300" />
        ) : (
          <span className="text-xs font-bold text-slate-350">No img</span>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1 w-full text-center sm:text-left">
        <div className="hidden sm:block truncate font-bold text-lg text-slate-900 group-hover:text-red-600 transition-colors">{product.name}</div>
        <div className="hidden sm:block mt-1 text-sm text-slate-500">{product.category || product.brand || 'Khác'}</div>
        
        {/* Metric Badge */}
        <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-2">
          <div className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold shadow-sm ${activeBg} ${activeColor}`}>
            {metric.icon}
            {metric.value} {metric.label}
          </div>
          {/* Trend Indicator with Semantic Colors */}
          <div className={`inline-flex items-center gap-0.5 rounded-md px-2 py-1 text-xs font-bold ${isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
            {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(trendPercent)}%
          </div>
        </div>
      </div>

      {/* Sparkline Chart (Hidden on small screens) */}
      <div className="hidden lg:flex w-36 items-center justify-center shrink-0">
        <Sparkline data={historyData} isPositive={isUp} />
      </div>

      {/* Price & Action */}
      <div className="flex w-full sm:w-auto items-center justify-between sm:justify-end gap-6 sm:pl-4 border-t sm:border-t-0 border-slate-100 pt-3 sm:pt-0 mt-3 sm:mt-0">
        <div className="text-left sm:text-right">
          <div className="text-lg font-black text-slate-900">{currency.format(salePrice(product))}</div>
          {discount > 0 && (
            <div className="text-sm font-medium text-slate-400 line-through">{currency.format(originalPrice(product))}</div>
          )}
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-400 transition-all duration-300 group-hover:bg-red-600 group-hover:text-white group-hover:translate-x-1 shadow-sm">
          <ArrowRight className="h-5 w-5" />
        </div>
      </div>
    </Link>
  );
}

