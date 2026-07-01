import React, { useEffect, useMemo, useReducer, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { SlidersHorizontal, X } from 'lucide-react';
import { brandApi } from '../../../services/brandApi';
import { publicApi } from '../../../services/publicApi';
import { ProductCard } from '../components/ProductCard';
import { ProductSkeleton } from '../components/ProductSkeleton';
import { priceRanges } from '../../../data/categories';
import { useCatalog } from '../../../hooks/useCatalog';

const MAX_PRICE_FILTER = 100000000;
const PRICE_STEP = 500000;
const skeletonSlots = ['skeleton-1', 'skeleton-2', 'skeleton-3', 'skeleton-4', 'skeleton-5', 'skeleton-6', 'skeleton-7', 'skeleton-8'];

type ProductListState = {
  products: any[];
  activeBrands: any[];
  loading: boolean;
};

const initialProductListState: ProductListState = {
  products: [],
  activeBrands: [],
  loading: true,
};

function mergeProductListState(state: ProductListState, patch: Partial<ProductListState>): ProductListState {
  return { ...state, ...patch };
}

const parsePriceParam = (value: string | null) => {
  const price = value ? Number(value) : 0;
  if (!Number.isFinite(price)) return 0;
  return Math.min(Math.max(price, 0), MAX_PRICE_FILTER);
};

const formatPriceShort = (value: number) => `${(value / 1000000).toLocaleString('vi-VN')} triệu`;

export default function ProductListPage() {
  const { categoryName } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [{ products, activeBrands, loading }, setPageState] = useReducer(
    mergeProductListState,
    initialProductListState,
  );
  const { categories, findCategoryById, loading: catalogLoading } = useCatalog();

  const keyword = searchParams.get('q') || '';
  const categoryFilter = searchParams.get('category') || categoryName || 'all';
  const brandFilter = searchParams.get('brand') || 'all';
  const priceFilter = searchParams.get('price') || 'all';
  const minPriceParam = searchParams.get('min_price');
  const maxPriceParam = searchParams.get('max_price');
  const sort = searchParams.get('sort') || 'default';
  const selectedCategory = findCategoryById(categoryFilter);
  const selectedMinPrice = parsePriceParam(minPriceParam);
  const selectedMaxPrice = parsePriceParam(maxPriceParam);
  const rangeMinValue = selectedMinPrice;
  const rangeMaxValue = selectedMaxPrice || MAX_PRICE_FILTER;
  const rangeMinPercent = (rangeMinValue / MAX_PRICE_FILTER) * 100;
  const rangeMaxPercent = (rangeMaxValue / MAX_PRICE_FILTER) * 100;

  const customPriceLabel = useMemo(() => {
    const minPrice = minPriceParam ? Number(minPriceParam) : undefined;
    const maxPrice = maxPriceParam ? Number(maxPriceParam) : undefined;
    if (priceFilter !== 'all' || (minPrice === undefined && maxPrice === undefined)) return '';
    if (minPrice !== undefined && maxPrice !== undefined) return `${formatPriceShort(minPrice)} - ${formatPriceShort(maxPrice)}`;
    if (minPrice !== undefined) return `Trên ${formatPriceShort(minPrice)}`;
    if (maxPrice !== undefined) return `Dưới ${formatPriceShort(maxPrice)}`;
    return '';
  }, [maxPriceParam, minPriceParam, priceFilter]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (keyword) count += 1;
    if (selectedCategory) count += 1;
    if (brandFilter !== 'all') count += 1;
    if (priceFilter !== 'all' || minPriceParam || maxPriceParam) count += 1;
    return count;
  }, [brandFilter, keyword, maxPriceParam, minPriceParam, priceFilter, selectedCategory]);

  useEffect(() => {
    if (!isMobileFilterOpen) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsMobileFilterOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileFilterOpen]);

  useEffect(() => {
    setPageState({ loading: true });
    const range = priceRanges.find((item) => item.id === priceFilter);
    const directMinPrice = minPriceParam ? Number(minPriceParam) : undefined;
    const directMaxPrice = maxPriceParam ? Number(maxPriceParam) : undefined;
    Promise.all([
      publicApi.listProducts({
        q: keyword || undefined,
        category: categoryFilter !== 'all' ? categoryFilter : undefined,
        brand: brandFilter !== 'all' ? brandFilter : undefined,
        minPrice: range?.min ?? directMinPrice,
        maxPrice: Number.isFinite(range?.max) ? range?.max : directMaxPrice,
        sort,
      }),
      brandApi.listBrands().catch(() => []),
    ])
      .then(([productData, brandData]) => {
        setPageState({ products: productData, activeBrands: brandData });
      })
      .catch((err) => {
        console.error(err);
        setPageState({ products: [], activeBrands: [] });
      })
      .finally(() => setPageState({ loading: false }));
  }, [brandFilter, categoryFilter, keyword, maxPriceParam, minPriceParam, priceFilter, sort]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (key === 'price') {
      next.delete('min_price');
      next.delete('max_price');
    }
    if (value === 'all' || value === '') next.delete(key);
    else next.set(key, value);
    setSearchParams(next);
  };

  const updateMinPrice = (value: string) => {
    const next = new URLSearchParams(searchParams);
    const price = parsePriceParam(value);
    const normalizedPrice = Math.min(price, rangeMaxValue);
    next.delete('price');
    if (normalizedPrice > 0) next.set('min_price', String(normalizedPrice));
    else next.delete('min_price');
    setSearchParams(next);
  };

  const updateMaxPrice = (value: string) => {
    const next = new URLSearchParams(searchParams);
    const price = parsePriceParam(value);
    const normalizedPrice = Math.max(price, rangeMinValue);
    next.delete('price');
    if (normalizedPrice > 0 && normalizedPrice < MAX_PRICE_FILTER) next.set('max_price', String(normalizedPrice));
    else next.delete('max_price');
    setSearchParams(next);
  };

  const brands = useMemo(() => {
    const activeBrandNames = activeBrands.flatMap((brand) => brand.name ? [brand.name] : []).sort();
    if (selectedCategory?.brands.length) {
      const activeBrandSet = new Set(activeBrandNames);
      return selectedCategory.brands
        .map((brand) => brand.name)
        .filter((brand) => activeBrandSet.has(brand));
    }
    return activeBrandNames;
  }, [activeBrands, selectedCategory]);

  const title = keyword
    ? `Tìm kiếm: ${keyword}`
    : selectedCategory?.name || 'Tất cả sản phẩm';

  const rangeInputClass = 'pointer-events-none absolute inset-x-0 top-0 h-8 w-full appearance-none bg-transparent accent-primary [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white [&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:shadow';

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex flex-wrap items-center gap-2 text-sm text-slate-500">
        <Link to="/" className="hover:text-primary">Trang chủ</Link>
        <span>/</span>
        <span className="font-bold text-slate-900">{title}</span>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <aside className="hidden w-full shrink-0 lg:block lg:w-72 lg:self-start">
          <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-sm lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3 font-bold text-slate-800">
              <SlidersHorizontal className="h-4 w-4" />
              Bộ lọc
            </div>

            <div className="border-b border-slate-100 p-4">
              <label htmlFor="desktop-category-filter" className="mb-3 block text-sm font-bold">Danh mục</label>
              <select
                id="desktop-category-filter"
                value={selectedCategory?.id || 'all'}
                onChange={(event) => updateFilter('category', event.target.value)}
                disabled={catalogLoading}
                className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="all">{catalogLoading ? 'Đang tải danh mục...' : 'Tất cả danh mục'}</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>

            <div className="border-b border-slate-100 p-4">
              <label htmlFor="desktop-brand-filter" className="mb-3 block text-sm font-bold">Hãng</label>
              <select
                id="desktop-brand-filter"
                value={brandFilter}
                onChange={(event) => updateFilter('brand', event.target.value)}
                className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
              >
                <option value="all">Tất cả hãng</option>
                {brands.map((brand) => (
                  <option key={brand} value={brand}>{brand}</option>
                ))}
              </select>
            </div>

            <div className="p-4">
              <h3 className="mb-3 text-sm font-bold">Mức giá</h3>
              <div className="mb-4 rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="mb-3 flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-slate-700">Khoảng giá</span>
                  <span className="font-bold text-primary">
                    {formatPriceShort(rangeMinValue)} - {formatPriceShort(rangeMaxValue)}
                  </span>
                </div>

                <div className="relative h-8">
                  <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-slate-200" />
                  <div
                    className="absolute top-3 h-2 rounded-full bg-primary"
                    style={{
                      left: `${rangeMinPercent}%`,
                      right: `${100 - rangeMaxPercent}%`,
                    }}
                  />
                  <input
                    aria-label="Giá tối thiểu"
                    type="range"
                    min="0"
                    max={MAX_PRICE_FILTER}
                    step={PRICE_STEP}
                    value={rangeMinValue}
                    onChange={(event) => updateMinPrice(event.target.value)}
                    className={`${rangeInputClass} z-20`}
                  />
                  <input
                    aria-label="Giá tối đa"
                    type="range"
                    min="0"
                    max={MAX_PRICE_FILTER}
                    step={PRICE_STEP}
                    value={rangeMaxValue}
                    onChange={(event) => updateMaxPrice(event.target.value)}
                    className={`${rangeInputClass} z-10`}
                  />
                </div>

                <div className="mt-3 grid grid-cols-2 gap-3">
                  <label className="block text-xs font-medium text-slate-500">
                    Từ
                    <input
                      type="number"
                      min="0"
                      max={MAX_PRICE_FILTER}
                      step={PRICE_STEP}
                      value={selectedMinPrice || ''}
                      onChange={(event) => updateMinPrice(event.target.value)}
                      placeholder="0"
                      className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-primary"
                    />
                  </label>
                  <label className="block text-xs font-medium text-slate-500">
                    Đến
                    <input
                      type="number"
                      min="0"
                      max={MAX_PRICE_FILTER}
                      step={PRICE_STEP}
                      value={selectedMaxPrice || ''}
                      onChange={(event) => updateMaxPrice(event.target.value)}
                      placeholder="100.000.000"
                      className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-primary"
                    />
                  </label>
                </div>

                <div className="mt-2 flex justify-between text-xs text-slate-400">
                  <span>0đ</span>
                  <span>100 triệu</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => updateFilter('price', 'all')}
                  className={`rounded-full border px-3 py-2 text-sm ${priceFilter === 'all' && !maxPriceParam && !minPriceParam ? 'border-primary text-primary' : 'border-slate-200'}`}
                >
                  Tất cả
                </button>
                {priceRanges.map((range) => (
                  <button type="button" key={range.id} onClick={() => updateFilter('price', range.id)} className={`rounded-full border px-3 py-2 text-sm ${priceFilter === range.id ? 'border-primary text-primary' : 'border-slate-200'}`}>
                    {range.label}
                  </button>
                ))}
                {customPriceLabel && (
                  <button type="button" className="rounded-full border border-primary px-3 py-2 text-sm text-primary">
                    {customPriceLabel}
                  </button>
                )}
              </div>
            </div>
          </div>
        </aside>

        <section className="flex-1">
          <div className="mb-4 flex flex-col justify-between gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-sm md:flex-row md:items-center">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
              <p className="text-sm text-slate-500">{products.length} sản phẩm phù hợp</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setIsMobileFilterOpen(true)}
                className="relative flex h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-semibold text-slate-700 transition hover:border-primary hover:text-primary lg:hidden"
              >
                <SlidersHorizontal className="h-4 w-4" />
                Bộ lọc
                {activeFilterCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-white">
                    {activeFilterCount}
                  </span>
                )}
              </button>
              {(keyword || selectedCategory || brandFilter !== 'all' || priceFilter !== 'all' || minPriceParam || maxPriceParam) && (
                <Link to="/products" className="flex h-10 items-center gap-1 rounded-lg border border-slate-200 px-3 text-sm hover:border-primary hover:text-primary">
                  <X className="h-4 w-4" />
                  Xóa lọc
                </Link>
              )}
              <select value={sort} onChange={(e) => updateFilter('sort', e.target.value)} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary">
                <option value="default">Sắp xếp mặc định</option>
                <option value="price-asc">Giá thấp đến cao</option>
                <option value="price-desc">Giá cao đến thấp</option>
                <option value="name-asc">Tên A-Z</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
            {loading ? (
              skeletonSlots.map((slot) => <ProductSkeleton key={slot} />)
            ) : products.length > 0 ? (
              products.map((product, index) => <ProductCard key={product.id} p={product} index={index} />)
            ) : (
              <div className="col-span-full rounded-xl border border-slate-100 bg-white py-20 text-center text-slate-500">
                Không tìm thấy sản phẩm phù hợp.
              </div>
            )}
          </div>
        </section>
      </div>

      {isMobileFilterOpen && (
        <div className="fixed inset-0 z-[80] lg:hidden" role="dialog" aria-modal="true" aria-labelledby="mobile-filter-title">
          <button
            type="button"
            aria-label="Đóng bộ lọc"
            className="absolute inset-0 h-full w-full bg-slate-950/50"
            onClick={() => setIsMobileFilterOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[86dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <div>
                <h2 id="mobile-filter-title" className="text-base font-extrabold text-slate-950">Bộ lọc sản phẩm</h2>
                <p className="text-xs text-slate-500">{products.length} sản phẩm phù hợp</p>
              </div>
              <button
                type="button"
                onClick={() => setIsMobileFilterOpen(false)}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-600"
                aria-label="Đóng bộ lọc"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="max-h-[calc(86dvh-8.5rem)] overflow-y-auto">
              <div className="border-b border-slate-100 p-4">
                <label htmlFor="mobile-category-filter" className="mb-3 block text-sm font-bold">Danh mục</label>
                <select
                  id="mobile-category-filter"
                  value={selectedCategory?.id || 'all'}
                  onChange={(event) => updateFilter('category', event.target.value)}
                  disabled={catalogLoading}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary disabled:bg-slate-50 disabled:text-slate-400"
                >
                  <option value="all">{catalogLoading ? 'Đang tải danh mục...' : 'Tất cả danh mục'}</option>
                  {categories.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>

              <div className="border-b border-slate-100 p-4">
                <label htmlFor="mobile-brand-filter" className="mb-3 block text-sm font-bold">Hãng</label>
                <select
                  id="mobile-brand-filter"
                  value={brandFilter}
                  onChange={(event) => updateFilter('brand', event.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary"
                >
                  <option value="all">Tất cả hãng</option>
                  {brands.map((brand) => (
                    <option key={brand} value={brand}>{brand}</option>
                  ))}
                </select>
              </div>

              <div className="p-4">
                <h3 className="mb-3 text-sm font-bold">Mức giá</h3>
                <div className="mb-4 rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <div className="mb-3 flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-slate-700">Khoảng giá</span>
                    <span className="font-bold text-primary">
                      {formatPriceShort(rangeMinValue)} - {formatPriceShort(rangeMaxValue)}
                    </span>
                  </div>

                  <div className="relative h-8">
                    <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-slate-200" />
                    <div
                      className="absolute top-3 h-2 rounded-full bg-primary"
                      style={{
                        left: `${rangeMinPercent}%`,
                        right: `${100 - rangeMaxPercent}%`,
                      }}
                    />
                    <input
                      aria-label="Giá tối thiểu"
                      type="range"
                      min="0"
                      max={MAX_PRICE_FILTER}
                      step={PRICE_STEP}
                      value={rangeMinValue}
                      onChange={(event) => updateMinPrice(event.target.value)}
                      className={`${rangeInputClass} z-20`}
                    />
                    <input
                      aria-label="Giá tối đa"
                      type="range"
                      min="0"
                      max={MAX_PRICE_FILTER}
                      step={PRICE_STEP}
                      value={rangeMaxValue}
                      onChange={(event) => updateMaxPrice(event.target.value)}
                      className={`${rangeInputClass} z-10`}
                    />
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <label className="block text-xs font-medium text-slate-500">
                      Từ
                      <input
                        type="number"
                        min="0"
                        max={MAX_PRICE_FILTER}
                        step={PRICE_STEP}
                        value={selectedMinPrice || ''}
                        onChange={(event) => updateMinPrice(event.target.value)}
                        placeholder="0"
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-primary"
                      />
                    </label>
                    <label className="block text-xs font-medium text-slate-500">
                      Đến
                      <input
                        type="number"
                        min="0"
                        max={MAX_PRICE_FILTER}
                        step={PRICE_STEP}
                        value={selectedMaxPrice || ''}
                        onChange={(event) => updateMaxPrice(event.target.value)}
                        placeholder="100.000.000"
                        className="mt-1 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-primary"
                      />
                    </label>
                  </div>

                  <div className="mt-2 flex justify-between text-xs text-slate-400">
                    <span>0đ</span>
                    <span>100 triệu</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => updateFilter('price', 'all')}
                    className={`min-h-10 rounded-full border px-3 py-2 text-sm ${priceFilter === 'all' && !maxPriceParam && !minPriceParam ? 'border-primary text-primary' : 'border-slate-200'}`}
                  >
                    Tất cả
                  </button>
                  {priceRanges.map((range) => (
                    <button type="button" key={range.id} onClick={() => updateFilter('price', range.id)} className={`min-h-10 rounded-full border px-3 py-2 text-sm ${priceFilter === range.id ? 'border-primary text-primary' : 'border-slate-200'}`}>
                      {range.label}
                    </button>
                  ))}
                  {customPriceLabel && (
                    <button type="button" className="min-h-10 rounded-full border border-primary px-3 py-2 text-sm text-primary">
                      {customPriceLabel}
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-[auto_1fr] gap-3 border-t border-slate-100 bg-white px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-3">
              <Link
                to="/products"
                onClick={() => setIsMobileFilterOpen(false)}
                className="flex h-11 items-center justify-center rounded-lg border border-slate-200 px-4 text-sm font-bold text-slate-700"
              >
                Xóa lọc
              </Link>
              <button
                type="button"
                onClick={() => setIsMobileFilterOpen(false)}
                className="flex h-11 items-center justify-center rounded-lg bg-primary px-4 text-sm font-extrabold text-white shadow-sm"
              >
                Xem sản phẩm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
