import { useEffect, useMemo, useState } from 'react';
import { BatteryCharging, CheckCircle2, Search, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { resolveImageUrl } from '../../../services/productMedia';
import { usedProductsApi } from '../services/usedProductsApi';
import type { StorefrontUsedProductListItem } from '../types';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export default function UsedProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<StorefrontUsedProductListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const search = searchParams.get('search') || '';
  const grade = searchParams.get('grade') || '';
  const sort = searchParams.get('sort') || 'newest';
  const maxPrice = searchParams.get('maxPrice') || '';
  const [searchDraft, setSearchDraft] = useState(search);

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  useEffect(() => {
    if (searchDraft === search) return undefined;
    const timer = window.setTimeout(() => updateFilter('search', searchDraft), 300);
    return () => window.clearTimeout(timer);
  }, [search, searchDraft]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    void usedProductsApi.list({
      search,
      grade,
      sort,
      maxPrice: maxPrice ? Number(maxPrice) : undefined,
      limit: 48,
    }).then((result) => {
      if (!active) return;
      setItems(result.items || []);
      setTotal(Number(result.total || 0));
    }).catch((requestError: unknown) => {
      const message = requestError instanceof Error ? requestError.message : 'Không thể tải danh sách điện thoại cũ.';
      if (active) setError(message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [grade, maxPrice, search, sort]);

  const activeFilterCount = useMemo(
    () => [search, grade, maxPrice].filter(Boolean).length,
    [grade, maxPrice, search],
  );

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  return (
    <div className="mx-auto w-full max-w-7xl py-5 sm:py-7">
      <div className="mb-5 flex flex-col gap-3 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-sm font-bold text-emerald-700">
            <CheckCircle2 className="h-4 w-4" /> Đã thẩm định theo từng IMEI
          </div>
          <h1 className="text-2xl font-bold text-slate-950 sm:text-3xl">Điện thoại cũ đang bán</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Ảnh thực tế, tình trạng pin và mức tiết kiệm được công khai cho từng thiết bị.
          </p>
        </div>
        <div className="text-sm font-semibold text-slate-500">{total} thiết bị phù hợp</div>
      </div>

      <div className="mb-5 grid gap-3 rounded-lg border border-slate-200 bg-white p-3 md:grid-cols-[minmax(220px,1fr)_160px_190px_180px_auto]">
        <label className="relative">
          <span className="sr-only">Tìm điện thoại cũ</span>
          <Search className="absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
          <input
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Tìm theo tên sản phẩm"
            className="h-11 w-full rounded-md border border-slate-200 pl-9 pr-3 text-base outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          />
        </label>
        <label>
          <span className="sr-only">Hạng thiết bị</span>
          <select value={grade} onChange={(event) => updateFilter('grade', event.target.value)} className="h-11 w-full rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
            <option value="">Mọi tình trạng</option>
            <option value="A">Hạng A</option>
            <option value="B">Hạng B</option>
            <option value="C">Hạng C</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Khoảng giá</span>
          <select value={maxPrice} onChange={(event) => updateFilter('maxPrice', event.target.value)} className="h-11 w-full rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
            <option value="">Mọi mức giá</option>
            <option value="5000000">Dưới 5 triệu</option>
            <option value="10000000">Dưới 10 triệu</option>
            <option value="15000000">Dưới 15 triệu</option>
            <option value="20000000">Dưới 20 triệu</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Sắp xếp</span>
          <select value={sort} onChange={(event) => updateFilter('sort', event.target.value)} className="h-11 w-full rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
            <option value="newest">Mới đăng</option>
            <option value="price_asc">Giá thấp đến cao</option>
            <option value="price_desc">Giá cao đến thấp</option>
            <option value="savings">Tiết kiệm nhiều nhất</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setSearchParams({ sort: 'newest' })}
          disabled={activeFilterCount === 0}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SlidersHorizontal className="h-4 w-4" /> Xóa lọc
        </button>
      </div>

      {error && (
        <div role="alert" className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, index) => (
            <div key={`used-skeleton-${index}`} className="overflow-hidden rounded-lg border border-slate-200 bg-white">
              <div className="aspect-square animate-pulse bg-slate-100" />
              <div className="space-y-3 p-4"><div className="h-4 animate-pulse rounded bg-slate-100" /><div className="h-6 w-2/3 animate-pulse rounded bg-slate-100" /></div>
            </div>
          ))}
        </div>
      ) : items.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {items.map((item) => {
            const snapshot = item.originalSnapshot || {};
            const newPrice = Number(snapshot.newReferencePrice || 0);
            const salePrice = Number(item.salePrice || 0);
            const savings = Math.max(0, newPrice - salePrice);
            return (
              <Link key={item.id} to={`/used-products/${item.slug}`} className="group overflow-hidden rounded-lg border border-slate-200 bg-white transition duration-200 hover:border-emerald-300 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <div className="relative aspect-square overflow-hidden bg-slate-50">
                  <img
                    src={resolveImageUrl(item.images?.[0])}
                    alt={`Ảnh thực tế ${item.title}`}
                    loading="lazy"
                    className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03] motion-reduce:transform-none"
                  />
                  <div className="absolute left-2 top-2 rounded-md bg-slate-950/85 px-2 py-1 text-xs font-bold text-white">Hạng {item.conditionGrade}</div>
                </div>
                <div className="p-3 sm:p-4">
                  <h2 className="min-h-12 text-sm font-bold leading-6 text-slate-900 sm:text-base">{item.title}</h2>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold text-slate-600">
                    <span className="inline-flex items-center gap-1"><BatteryCharging className="h-3.5 w-3.5 text-emerald-600" /> Pin {item.batteryHealth ?? '-'}%</span>
                    <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5 text-sky-600" /> BH {item.warrantyMonths || 0} tháng</span>
                  </div>
                  <div className="mt-4 text-lg font-bold text-red-700">{currency.format(salePrice)}</div>
                  {newPrice > 0 && <div className="mt-1 text-xs text-slate-500">Máy mới: <span className="line-through">{currency.format(newPrice)}</span></div>}
                  {savings > 0 && <div className="mt-2 text-xs font-bold text-emerald-700">Tiết kiệm {currency.format(savings)}</div>}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white px-5 py-16 text-center">
          <Search className="mx-auto h-8 w-8 text-slate-400" />
          <h2 className="mt-3 text-lg font-bold text-slate-900">Chưa có thiết bị phù hợp</h2>
          <p className="mt-1 text-sm text-slate-500">Hãy thay đổi từ khóa hoặc bộ lọc tình trạng.</p>
        </div>
      )}
    </div>
  );
}
