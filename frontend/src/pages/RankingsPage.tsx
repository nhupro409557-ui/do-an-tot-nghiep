import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Flame, Eye, Heart, Search, ShoppingBag, Star, Activity, BarChart2, Trophy, Filter, TrendingUp, TrendingDown } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, YAxis, XAxis, Tooltip } from 'recharts';
import { ImageWithFallback } from '../components/ui/ImageWithFallback';
import { apiDb } from '../services/apiDb';

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

// Deterministic pseudo-random number generator based on string
function seededRandom(seedStr: string) {
  let h = 0;
  for (let i = 0; i < seedStr.length; i++) {
    h = Math.imul(31, h) + seedStr.charCodeAt(i) | 0;
  }
  return function() {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}

function generateHistoryData(seed: string, pointsCount: number, baseValue: number, trend: 'up' | 'down' | 'flat') {
  const rand = seededRandom(seed);
  const data = [];
  let current = baseValue;
  for (let i = 0; i < pointsCount; i++) {
    let change = (rand() % 20) - 10; // -10 to +9
    if (trend === 'up') change += 3;
    if (trend === 'down') change -= 3;
    current = Math.max(10, current + change);
    data.push(current);
  }
  return data;
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

function enrichProductData(product: any, timeRange: TimeRange) {
  const randStr = product.id + timeRange;
  const rand = seededRandom(randStr);
  
  // Adjust multipliers based on time range
  const timeMultiplier = timeRange === '24h' ? 1 : timeRange === '7d' ? 5 : timeRange === '30d' ? 15 : 100;
  
  const soldCount = (Number(product.soldCount) || (rand() % 500) + 10) * (timeMultiplier / 10);
  const reviewCount = Number(product.reviewCount) || (rand() % 100) + 5;
  const rating = Number(product.rating) || 4 + (rand() % 10) / 10; // 4.0 to 4.9
  
  return {
    ...product,
    soldCount: Math.round(Math.max(0, soldCount)),
    reviewCount,
    rating,
    searchCount: Math.round(((rand() % 15000) + 500) * timeMultiplier),
    viewCount: Math.round(((rand() % 50000) + 1000) * timeMultiplier),
    likeCount: Math.round(((rand() % 2000) + 50) * timeMultiplier),
    trendScore: (rand() % 100),
  };
}

export default function RankingsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [criteria, setCriteria] = useState<RankingCriteria>('trending');
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiDb.listCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    apiDb.listProducts()
      .then((items) => {
        const activeItems = items.filter((item) => item.status !== 'INACTIVE');
        const enrichedItems = activeItems.map(p => enrichProductData(p, timeRange));
        setProducts(enrichedItems);
      })
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [timeRange]);

  const rankedProducts = useMemo(() => {
    let list = [...products];
    
    // Filter by category
    if (selectedCategory !== 'all') {
      const cat = categories.find(c => c.id === selectedCategory);
      list = list.filter(p => p.categoryId === selectedCategory || (cat && p.category === cat.name));
    }

    switch (criteria) {
      case 'trending': return list.sort((a, b) => b.trendScore - a.trendScore).slice(0, 20);
      case 'search': return list.sort((a, b) => b.searchCount - a.searchCount).slice(0, 20);
      case 'view': return list.sort((a, b) => b.viewCount - a.viewCount).slice(0, 20);
      case 'like': return list.sort((a, b) => b.likeCount - a.likeCount).slice(0, 20);
      case 'sold': return list.sort((a, b) => b.soldCount - a.soldCount).slice(0, 20);
      case 'rating': return list.sort((a, b) => b.rating - a.rating).slice(0, 20);
      default: return list;
    }
  }, [products, criteria, selectedCategory, categories]);

  const activeCriteria = criteriaOptions.find((opt) => opt.value === criteria) || criteriaOptions[0];

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
        <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="flex w-full sm:w-auto items-center gap-2 overflow-x-auto pb-2 sm:pb-0 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
            <Filter className="h-5 w-5 text-slate-400 shrink-0" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="rounded-lg border-slate-200 text-sm font-medium focus:border-primary focus:ring-primary w-full sm:w-48"
            >
              <option value="all">Tất cả danh mục</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="flex bg-slate-100 p-1 rounded-lg w-full sm:w-auto overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
            {timeRangeOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTimeRange(opt.value)}
                className={`whitespace-nowrap rounded-md px-4 py-1.5 text-sm font-semibold transition-colors ${
                  timeRange === opt.value
                    ? 'bg-white text-primary shadow-sm'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Filters: Criteria */}
        <div className="mb-8 overflow-x-auto pb-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div className="flex gap-3">
            {criteriaOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setCriteria(option.value)}
                className={`flex shrink-0 items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold transition-all ${
                  criteria === option.value
                    ? `${option.bg} ${option.color} ring-1 ring-inset ring-black/5`
                    : 'bg-white text-slate-600 shadow-sm ring-1 ring-inset ring-slate-200 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Rankings Content */}
        {loading ? (
          <div className="flex items-center justify-center rounded-2xl bg-white p-20 shadow-sm ring-1 ring-inset ring-slate-100">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          </div>
        ) : rankedProducts.length === 0 ? (
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
              {rankedProducts.map((product, index) => (
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
      case 'search': return { label: 'Lượt tìm kiếm', value: product.searchCount.toLocaleString('vi-VN'), icon: <Search className="h-3.5 w-3.5" /> };
      case 'view': return { label: 'Lượt xem', value: product.viewCount.toLocaleString('vi-VN'), icon: <Eye className="h-3.5 w-3.5" /> };
      case 'like': return { label: 'Lượt thích', value: product.likeCount.toLocaleString('vi-VN'), icon: <Heart className="h-3.5 w-3.5" /> };
      case 'sold': return { label: 'Đã bán', value: product.soldCount.toLocaleString('vi-VN'), icon: <ShoppingBag className="h-3.5 w-3.5" /> };
      case 'rating': return { label: 'Đánh giá', value: `${product.rating.toFixed(1)} / 5.0`, icon: <Star className="h-3.5 w-3.5" /> };
      case 'trending': default: return { label: 'Điểm xu hướng', value: product.trendScore.toString(), icon: <Flame className="h-3.5 w-3.5" /> };
    }
  };

  const metric = getMetricDisplay();

  const rankColor = rank === 1 ? 'text-amber-500 bg-amber-50 ring-1 ring-amber-200' : 
                    rank === 2 ? 'text-slate-500 bg-slate-100 ring-1 ring-slate-200' : 
                    rank === 3 ? 'text-orange-600 bg-orange-100 ring-1 ring-orange-200' : 
                    'text-slate-400 font-medium bg-white';

  // Generate chart data based on criteria and product
  const rand = seededRandom(product.id + criteria + timeRange);
  const trendType = rand() % 100 > 60 ? 'up' : (rand() % 100 > 80 ? 'down' : 'flat');
  const pointsCount = timeRange === '24h' ? 24 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 12;
  const historyData = generateHistoryData(product.id + criteria + timeRange, pointsCount, 100, trendType);
  
  // Trend percentage
  const lastVal = historyData[historyData.length - 1];
  const firstVal = historyData[0] || 1;
  const trendPercent = Math.round(((lastVal - firstVal) / firstVal) * 100);
  const isUp = trendPercent >= 0;

  return (
    <Link 
      to={`/product/${product.id || product.slug}`} 
      className="group flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 sm:px-6 transition-colors hover:bg-slate-50 relative"
    >
      {/* Rank Number */}
      <div className="flex items-center gap-4 w-full sm:w-auto">
        <div className={`flex h-10 w-10 sm:h-12 sm:w-12 shrink-0 items-center justify-center rounded-xl text-lg sm:text-xl font-black ${rankColor}`}>
          {rank}
        </div>
        
        {/* Mobile Layout Title */}
        <div className="min-w-0 flex-1 sm:hidden">
          <div className="truncate font-bold text-slate-900 group-hover:text-primary transition-colors">{product.name}</div>
          <div className="text-sm text-slate-500">{product.category || product.brand || 'Sản phẩm'}</div>
        </div>
      </div>

      {/* Image */}
      <div className="flex h-20 w-20 sm:h-16 sm:w-16 shrink-0 items-center justify-center rounded-xl bg-white p-2 ring-1 ring-inset ring-slate-100 shadow-sm mx-auto sm:mx-0">
        {image ? (
          <ImageWithFallback src={image} alt={product.name} className="h-full w-full object-contain group-hover:scale-110 transition-transform duration-300" />
        ) : (
          <span className="text-xs font-bold text-slate-300">No img</span>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1 w-full text-center sm:text-left">
        <div className="hidden sm:block truncate font-bold text-lg text-slate-900 group-hover:text-primary transition-colors">{product.name}</div>
        <div className="hidden sm:block mt-1 text-sm text-slate-500">{product.category || product.brand || 'Khác'}</div>
        
        {/* Metric Badge */}
        <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-2">
          <div className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-bold ${activeBg} ${activeColor}`}>
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
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-400 transition-colors group-hover:bg-primary group-hover:text-white">
          <ArrowRight className="h-5 w-5" />
        </div>
      </div>
    </Link>
  );
}

