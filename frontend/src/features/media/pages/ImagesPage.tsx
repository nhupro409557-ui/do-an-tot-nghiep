import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Eye, Heart, Image as ImageIcon, Layers, Search, SlidersHorizontal, Sparkles, X } from 'lucide-react';
import { publicApi } from '../../../services/publicApi';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import ImagesModal from '../components/ImagesModal';

interface Product {
  id: string;
  name: string;
  brand?: string;
  category?: string;
  imageUrl?: string;
  images?: string[];
  price?: number;
  discountPrice?: number;
  favoriteCount?: number;
  viewCount?: number;
  trendScore?: number;
}

interface ImageItem {
  id: string;
  url: string;
  productId: string;
  productName: string;
  brand?: string;
  category?: string;
  favoriteCount?: number;
  viewCount?: number;
  product: Product;
}

interface ProductCard {
  id: string;
  mainUrl: string;
  productId: string;
  productName: string;
  brand?: string;
  category?: string;
  product: Product;
  imageCount: number;
  favoriteCount?: number;
  viewCount?: number;
  trendScore?: number;
  images: ImageItem[];
}

type SortMode = 'trending' | 'views' | 'likes' | 'name';

function priceOf(product: Product) {
  return Number(product?.discountPrice || product?.price || 0).toLocaleString('vi-VN');
}

function numericCount(value: unknown) {
  const count = Number(value || 0);
  return Number.isFinite(count) ? count : 0;
}

function productMetric(item: ProductCard, key: 'favoriteCount' | 'viewCount' | 'trendScore') {
  return numericCount(item[key] ?? item.product?.[key]);
}

function formatCount(value: unknown) {
  return numericCount(value).toLocaleString('vi-VN');
}

function resolveCardImage(cards: ProductCard[], viewId: string) {
  for (const card of cards) {
    if (card.id === viewId) return { cardId: card.id, imageIndex: 0 };
    for (let imageIndex = 0; imageIndex < card.images.length; imageIndex += 1) {
      if (card.images[imageIndex].id === viewId) return { cardId: card.id, imageIndex };
    }
  }
  return null;
}

function SkeletonTile() {
  return (
    <div className="h-full min-h-0 overflow-hidden rounded-xl border border-gray-200/80 bg-gray-100 animate-pulse lg:rounded-2xl">
      <div className="relative h-full w-full">
        <div className="absolute inset-0 bg-gradient-to-t from-gray-200 via-gray-100/40 to-transparent" />
        <div className="absolute left-3 top-3 h-5 w-16 rounded-full bg-gray-200" />
        <div className="absolute inset-x-0 bottom-0 space-y-2 p-4">
          <div className="h-4 w-3/4 rounded bg-gray-200" />
          <div className="h-3 w-1/2 rounded bg-gray-200/60" />
          <div className="mt-3 h-8 w-full rounded-xl bg-gray-200/40" />
        </div>
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid auto-rows-[clamp(7.5rem,34vw,9rem)] grid-cols-2 gap-[clamp(0.5rem,2.2vw,1rem)] sm:auto-rows-[clamp(8.25rem,21vw,10rem)] sm:grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] lg:auto-rows-[9rem] lg:grid-cols-4 lg:gap-5">
      {Array.from({ length: 12 }).map((_, i) => <SkeletonTile key={i} />)}
    </div>
  );
}

function tileSpanClass(index: number) {
  const pattern = [
    'row-span-2 sm:row-span-3 lg:row-span-3',
    'row-span-2 sm:row-span-2 lg:row-span-2',
    'row-span-2 sm:row-span-2 lg:row-span-2',
    'row-span-2 sm:row-span-3 lg:row-span-3',
    'row-span-2 sm:row-span-2 lg:row-span-2',
    'row-span-2 sm:row-span-3 lg:row-span-3',
    'row-span-2 sm:row-span-2 lg:row-span-2',
    'row-span-2 sm:row-span-2 lg:row-span-2',
  ];
  return pattern[index % pattern.length];
}

function ImageTile({ item, index, onOpen }: { item: ProductCard; index: number; onOpen: () => void }) {
  const [hovered, setHovered] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    hoverTimer.current = setTimeout(() => setHovered(true), 120);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHovered(false);
  }, []);

  useEffect(() => () => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
  }, []);

  return (
    <article
      className={`group relative min-h-0 cursor-pointer overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-0.5 hover:border-red-200 hover:shadow-[0_10px_24px_rgba(220,38,38,0.12)] lg:rounded-2xl lg:shadow-sm lg:duration-500 lg:hover:-translate-y-1 lg:hover:shadow-xl lg:hover:shadow-red-100/40 ${tileSpanClass(index)}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="absolute inset-0 bg-gray-100">
        <ImageWithFallback
          src={item.mainUrl}
          alt={item.productName}
          className={`h-full w-full object-contain p-2 transition-all duration-700 ease-out lg:p-3 ${hovered ? 'scale-105 brightness-105' : 'scale-100'}`}
          loading="lazy"
          draggable={false}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent transition-opacity duration-300 lg:from-black/70" />
      </div>

      <button
        type="button"
        aria-label={`Xem ảnh ${item.productName}`}
        className="absolute inset-0 z-10 cursor-pointer"
        onClick={onOpen}
      />

      <div className="pointer-events-none absolute left-2 right-2 top-2 z-20 flex items-start justify-between gap-1.5 lg:left-3 lg:right-3 lg:top-3">
        <span className="max-w-[78%] truncate rounded-md border border-red-100 bg-white/95 px-1.5 py-0.5 text-[8px] font-black uppercase text-red-600 shadow-sm transition-all duration-300 group-hover:border-red-500 group-hover:bg-red-600 group-hover:text-white sm:px-2 sm:py-1 sm:text-[9px] lg:rounded-full lg:border-gray-200 lg:bg-white/90 lg:px-2.5 lg:text-[10px] lg:tracking-widest lg:backdrop-blur-md">
          {item.category || item.brand || 'Sản phẩm'}
        </span>
        {item.imageCount > 1 && (
          <span className="flex items-center gap-0.5 rounded-md border border-slate-200 bg-white/95 px-1.5 py-0.5 text-[8px] font-black text-gray-700 shadow-sm sm:px-2 sm:py-1 sm:text-[9px] lg:gap-1 lg:rounded-full lg:bg-white/90 lg:text-[10px] lg:font-bold lg:backdrop-blur-md">
            <Layers className="h-2.5 w-2.5 lg:h-3 lg:w-3" />
            {item.imageCount}
          </span>
        )}
      </div>

      <div className={`absolute inset-x-0 bottom-0 z-20 flex flex-col gap-1 p-2 transition-all duration-300 ease-out sm:p-3 lg:gap-1.5 lg:p-4 lg:duration-500 ${hovered ? 'translate-y-0 opacity-100' : 'translate-y-0 opacity-100 lg:translate-y-16 lg:opacity-95'}`}>
        <h3 className="line-clamp-2 text-[11px] font-black leading-tight text-white drop-shadow-lg transition-colors duration-300 group-hover:text-red-300 sm:text-sm lg:leading-snug">
          {item.productName}
        </h3>

        <span className="text-[10px] font-black text-red-300 drop-shadow-md lg:text-xs">
          {priceOf(item.product)}đ
        </span>

        <div className={`hidden flex-wrap gap-x-3 gap-y-1 text-[11px] font-semibold text-white/75 transition-all duration-500 lg:flex ${hovered ? 'opacity-100' : 'opacity-0'}`}>
          <span className="inline-flex items-center gap-1"><Eye className="h-3 w-3" />{formatCount(productMetric(item, 'viewCount'))} lượt xem</span>
          <span className="inline-flex items-center gap-1"><Heart className="h-3 w-3" />{formatCount(productMetric(item, 'favoriteCount'))} lượt thích</span>
        </div>

        <Link
          to={`/product/${item.productId}`}
          className={`mt-1 hidden items-center gap-2.5 rounded-xl border border-white/30 bg-white/20 p-1.5 backdrop-blur-lg transition-all duration-500 ease-out hover:border-white/50 hover:bg-white/35 lg:flex ${hovered ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}
          onClick={(event) => event.stopPropagation()}
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white p-0.5 shadow-sm">
            <ImageWithFallback src={item.mainUrl} alt="" className="h-full w-full object-contain" loading="lazy" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-bold leading-tight text-white drop-shadow-sm">
              {item.product.name}
            </p>
          </div>
          <span className="mr-0.5 shrink-0 rounded-full bg-red-600 px-2.5 py-1 text-[9px] font-black uppercase text-white shadow-md transition-colors hover:bg-red-500">
            Mua
          </span>
        </Link>
      </div>
    </article>
  );
}

export default function ImagesPage() {
  const [productCards, setProductCards] = useState<ProductCard[]>([]);
  const [categories, setCategories] = useState<{ label: string; count: number }[]>([]);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [sort, setSort] = useState<SortMode>('trending');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [resolvedCard, setResolvedCard] = useState<ProductCard | null>(null);
  const [activeCategory, setActiveCategory] = useState('all');
  const [totalImages, setTotalImages] = useState(0);
  const [totalProducts, setTotalProducts] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      setDebouncedQuery(query);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const handleCategoryChange = (category: string) => {
    setPage(1);
    setActiveCategory(category);
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    publicApi.listProductImages({
      q: debouncedQuery || undefined,
      category: activeCategory !== 'all' ? activeCategory : undefined,
      page,
      limit: 30,
    })
      .then((data) => {
        if (!active) return;
        setProductCards(data.items || []);
        setCategories(data.categories || []);
        setTotalImages(Number(data.totalImages || 0));
        setTotalProducts(Number(data.totalProducts || 0));
        setTotalPages(Number(data.totalPages || 1));
        setHasMore(Boolean(data.hasMore));
      })
      .catch(() => {
        if (!active) return;
        setProductCards([]);
        setCategories([]);
        setTotalImages(0);
        setTotalProducts(0);
        setTotalPages(1);
        setHasMore(false);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [activeCategory, debouncedQuery, page]);

  const activeCard = useMemo(
    () => productCards.find((card) => card.id === activeCardId) || (resolvedCard?.id === activeCardId ? resolvedCard : null),
    [productCards, resolvedCard, activeCardId],
  );
  const filteredCards = useMemo(() => {
    return [...productCards].sort((a, b) => {
      if (sort === 'views') return productMetric(b, 'viewCount') - productMetric(a, 'viewCount');
      if (sort === 'likes') return productMetric(b, 'favoriteCount') - productMetric(a, 'favoriteCount');
      if (sort === 'name') return String(a.productName || '').localeCompare(String(b.productName || ''), 'vi');
      return productMetric(b, 'trendScore') - productMetric(a, 'trendScore');
    });
  }, [productCards, sort]);
  const lastViewId = useRef<string | null>(null);

  useEffect(() => {
    const viewId = searchParams.get('view');
    if (!viewId) {
      lastViewId.current = null;
      setResolvedCard(null);
      return;
    }
    if (loading || viewId === lastViewId.current) return;

    let cancelled = false;
    const resolvedImage = resolveCardImage(filteredCards, viewId);
    const targetCardId = resolvedImage?.cardId || null;
    const imageIdx = resolvedImage?.imageIndex || 0;

    if (targetCardId) {
      setResolvedCard(null);
      setActiveCardId(targetCardId);
      setActiveImageIndex(imageIdx);
      setIsModalOpen(true);
      lastViewId.current = viewId;
      return;
    }

    publicApi.resolveProductImage(viewId, { limit: 30 })
      .then((data) => {
        if (cancelled || !data?.item) return;
        setResolvedCard(data.item);
        setActiveCardId(data.item.id);
        setActiveImageIndex(Number(data.imageIndex || 0));
        setPage(Number(data.page || 1));
        setIsModalOpen(true);
        lastViewId.current = viewId;
      })
      .catch(() => {
        if (!cancelled) lastViewId.current = viewId;
      });

    return () => {
      cancelled = true;
    };
  }, [filteredCards, loading, searchParams]);

  function closeImagesModal() {
    setIsModalOpen(false);
    setResolvedCard(null);
    setSearchParams((params) => {
      const next = new URLSearchParams(params);
      next.delete('view');
      return next;
    }, { replace: true });
  }

  return (
    <div className="min-h-screen bg-gray-50/80 text-gray-900">
      <div className="relative overflow-hidden border-b border-gray-200 bg-white">
        <div className="absolute -left-32 -top-32 h-64 w-64 rounded-full bg-red-100/60 blur-[100px]" />
        <div className="absolute -right-32 -bottom-32 h-64 w-64 rounded-full bg-violet-100/50 blur-[100px]" />
        <div className="absolute left-1/2 top-0 h-48 w-48 -translate-x-1/2 rounded-full bg-blue-100/40 blur-[80px]" />

        <div className="relative z-10 mx-auto max-w-7xl px-3 py-6 sm:px-5 sm:py-8 lg:px-8 lg:py-10">
          <div className="flex flex-col gap-4 sm:gap-5 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
            <div className="space-y-2.5 sm:space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-red-200 bg-red-600 shadow-lg shadow-red-100 sm:h-12 sm:w-12 sm:rounded-2xl sm:border-0 sm:bg-gradient-to-br sm:from-red-500 sm:to-red-600 sm:shadow-red-200">
                  <ImageIcon className="h-5 w-5 text-white sm:h-6 sm:w-6" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-2xl font-black tracking-tight text-gray-900 sm:text-3xl">Thư viện ảnh 3D</h1>
                  <p className="mt-0.5 text-xs font-medium text-gray-500 sm:text-sm">Trải nghiệm xem sản phẩm 360° chất lượng cao</p>
                </div>
              </div>

              {!loading && (
                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-red-100 bg-red-50 px-2.5 py-1.5 text-[10px] font-black text-red-600 shadow-sm sm:rounded-full sm:px-3 sm:text-[11px] sm:font-bold sm:shadow-none">
                    <Sparkles className="h-3 w-3 text-red-500" />
                    {totalImages} hình ảnh
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-blue-100 bg-blue-50 px-2.5 py-1.5 text-[10px] font-black text-blue-600 shadow-sm sm:rounded-full sm:px-3 sm:text-[11px] sm:font-bold sm:shadow-none">
                    <SlidersHorizontal className="h-3 w-3 text-blue-500" />
                    {totalProducts} sản phẩm
                  </span>
                </div>
              )}
            </div>

            <div className="grid w-full gap-2 sm:max-w-xl sm:grid-cols-[minmax(0,1fr)_160px]">
              <label className="group relative block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-red-500 sm:left-4 sm:h-[18px] sm:w-[18px]" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Tìm ảnh theo tên sản phẩm, thương hiệu..."
                  className="h-11 w-full rounded-xl border border-slate-200 bg-gray-50 pl-10 pr-9 text-sm text-gray-900 shadow-sm outline-none transition-all duration-300 placeholder:text-gray-400 focus:border-red-400 focus:bg-white focus:ring-2 focus:ring-red-100 sm:h-12 sm:rounded-2xl sm:pl-12 sm:pr-10"
                />
                {query && (
                  <button type="button" onClick={() => setQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-gray-400 transition-all hover:bg-gray-100 hover:text-gray-700">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </label>
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as SortMode)}
                className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-gray-700 shadow-sm outline-none transition-all hover:border-red-300 focus:border-red-400 focus:ring-2 focus:ring-red-100 sm:h-12 sm:rounded-2xl sm:px-4 sm:font-bold sm:hover:border-gray-300"
              >
                <option value="trending">Nổi bật</option>
                <option value="views">Xem nhiều</option>
                <option value="likes">Thích nhiều</option>
                <option value="name">Tên A-Z</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {!loading && categories.length > 0 && (
        <div className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur-sm">
          <div className="mx-auto max-w-7xl px-3 py-2.5 sm:px-5 sm:py-3 lg:px-8">
            <div className="relative inline-block w-full sm:w-64">
              <select
                value={activeCategory}
                onChange={(e) => handleCategoryChange(e.target.value)}
                className="w-full appearance-none rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-black text-gray-700 shadow-sm transition-all hover:border-red-300 focus:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-100 sm:rounded-2xl sm:px-4 sm:font-bold sm:hover:border-gray-300"
              >
                <option value="all">Tất cả danh mục ({totalProducts})</option>
                {categories.map((cat) => (
                  <option key={cat.label} value={cat.label}>
                    {cat.label} ({cat.count})
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-7xl px-2.5 py-4 sm:px-5 sm:py-6 lg:px-8 lg:py-8">
        {loading ? (
          <SkeletonGrid />
        ) : filteredCards.length === 0 ? (
          <div className="mx-1 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-900 bg-white px-4 py-16 text-center shadow-[4px_4px_0_rgba(17,24,39,0.10)] sm:rounded-3xl sm:border-gray-300 sm:py-24 sm:shadow-sm">
            <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-3xl border border-gray-200 bg-gray-100">
              <ImageIcon className="h-10 w-10 text-gray-300" />
            </div>
            <h3 className="text-lg font-bold text-gray-500">Không tìm thấy hình ảnh</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-gray-400">
              {query ? `Không có hình ảnh nào phù hợp với "${query}". Hãy thử từ khóa khác.` : 'Chưa có hình ảnh sản phẩm nào trong hệ thống.'}
            </p>
            {(query || activeCategory !== 'all') && (
              <button
                type="button"
                onClick={() => {
                  setQuery('');
                  handleCategoryChange('all');
                }}
                className="mt-5 rounded-full bg-red-600 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-red-200 transition-colors hover:bg-red-500"
              >
                Xóa bộ lọc
              </button>
            )}
          </div>
        ) : (
          <>
            {(query || activeCategory !== 'all') && (
              <p className="mb-3 px-1 text-xs font-semibold text-gray-400 sm:mb-5">
                Hiển thị trang {page} / {totalPages} · {filteredCards.length} / {totalProducts} sản phẩm
              </p>
            )}

            <div className="grid auto-rows-[clamp(7.5rem,34vw,9rem)] grid-cols-2 gap-[clamp(0.5rem,2.2vw,1rem)] sm:auto-rows-[clamp(8.25rem,21vw,10rem)] sm:grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] lg:auto-rows-[9rem] lg:grid-cols-4 lg:gap-5">
              {filteredCards.map((card, index) => (
                <ImageTile
                  key={card.id}
                  item={card}
                  index={index}
                  onOpen={() => {
                    setActiveCardId(card.id);
                    setActiveImageIndex(0);
                    setIsModalOpen(true);
                  }}
                />
              ))}
            </div>

            {totalPages > 1 && (
              <div className="mt-6 grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-1 sm:mt-8 sm:flex sm:justify-center sm:gap-3 sm:px-0">
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1}
                  className="rounded-xl border-2 border-gray-900 bg-white px-2 py-2 text-xs font-black text-slate-700 shadow-[3px_3px_0_rgba(17,24,39,0.10)] transition hover:border-red-500 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50 sm:rounded-full sm:border-slate-200 sm:px-5 sm:py-2.5 sm:text-sm sm:font-bold sm:shadow-sm sm:hover:border-red-300"
                >
                  Trang trước
                </button>
                <span className="rounded-xl border-2 border-gray-900 bg-slate-100 px-3 py-2 text-xs font-black text-slate-700 sm:rounded-full sm:border-0 sm:px-4 sm:text-sm sm:font-bold">
                  {page} / {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={!hasMore}
                  className="rounded-xl border-2 border-gray-900 bg-white px-2 py-2 text-xs font-black text-slate-700 shadow-[3px_3px_0_rgba(17,24,39,0.10)] transition hover:border-red-500 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50 sm:rounded-full sm:border-slate-200 sm:px-5 sm:py-2.5 sm:text-sm sm:font-bold sm:shadow-sm sm:hover:border-red-300"
                >
                  Trang sau
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <ImagesModal
        isOpen={isModalOpen}
        playlist={isModalOpen && activeCard ? activeCard.images : []}
        initialIndex={activeImageIndex}
        onClose={closeImagesModal}
      />
    </div>
  );
}
