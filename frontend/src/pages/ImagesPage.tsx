import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Heart, Image as ImageIcon, Search, Share2 } from 'lucide-react';
import { apiDb } from '../services/apiDb';
import ImagesModal from '../components/video/ImagesModal';

function heightForTile(index: number) {
  const heights = [420, 300, 360, 280, 400, 320, 340, 380, 260, 440];
  return heights[index % heights.length];
}

function ImageTile({ item, index, onOpen }: { item: any; index: number; onOpen: () => void }) {
  const [hovered, setHovered] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleMouseEnter() {
    hoverTimer.current = setTimeout(() => setHovered(true), 150);
  }

  function handleMouseLeave() {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHovered(false);
  }

  const isActive = hovered;
  const likeCount = 12 + ((index * 7) % 56);
  const commentCount = 3 + ((index * 3) % 12);
  const h = heightForTile(index);

  return (
    <article
      style={{ height: h }}
      className="group relative mb-4 cursor-pointer break-inside-avoid overflow-hidden rounded-xl bg-gray-900 shadow-md transition-all duration-300 hover:shadow-2xl"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onOpen}
    >
      <div className="absolute inset-0 bg-white/5">
        <img
          src={item.url}
          alt={item.productName}
          className={`h-full w-full object-cover transition-all duration-500 ${isActive ? 'scale-[1.03]' : ''}`}
          loading="lazy"
        />
      </div>

      <div className={`absolute left-3 right-3 top-3 z-20 flex items-start justify-between transition-opacity duration-300 ${isActive ? 'opacity-0' : 'opacity-100'}`}>
        <span className="rounded-full bg-white/95 px-2.5 py-1 text-xs font-bold text-primary shadow-sm">
          {item.category || item.brand || 'Sản phẩm'}
        </span>
      </div>

      <div className={`absolute inset-x-0 bottom-0 z-20 transition-transform duration-300 ease-out ${isActive ? 'translate-y-0' : 'translate-y-full'}`}>
        <div className="flex flex-col gap-1.5 px-3 pb-3 pt-10" style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.35) 55%, transparent 100%)' }}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 flex-1 text-sm font-medium leading-snug text-white">
              {item.productName}
            </h3>
            <div className="flex shrink-0 gap-2 pt-0.5">
              <button className="text-gray-300 transition-colors hover:text-red-400" aria-label="Thích hình ảnh">
                <Heart className="h-[18px] w-[18px]" />
              </button>
              <button className="text-gray-300 transition-colors hover:text-white" aria-label="Chia sẻ hình ảnh">
                <Share2 className="h-[18px] w-[18px]" />
              </button>
            </div>
          </div>

          <div className="-mt-0.5 flex gap-3 text-[11px] font-medium text-gray-400">
            <span>{commentCount} bình luận</span>
            <span>{likeCount} lượt thích</span>
          </div>

          <Link
            to={`/product/${item.productId}`}
            className="mt-1 flex w-max max-w-full items-center gap-2 rounded-full border border-white/15 bg-white/10 px-2 py-1.5 backdrop-blur-md transition-colors hover:bg-white/20"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white">
              <img src={item.url} alt="" className="h-full w-full object-contain" loading="lazy" />
            </span>
            <span className="min-w-0 flex-1 truncate text-xs font-medium text-white">
              {item.productName}
            </span>
            <span className="shrink-0 pr-1 text-xs font-bold text-red-400">
              Chi tiết →
            </span>
          </Link>
        </div>
      </div>
    </article>
  );
}

export default function ImagesPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const [searchParams] = useSearchParams();

  useEffect(() => {
    apiDb.listProducts()
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, []);

  const images = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return products
      .flatMap((product) => {
        const urls = product.images?.length ? product.images : product.imageUrl ? [product.imageUrl] : [];
        return urls.map((url: string, index: number) => ({
          id: `${product.id}-${index}`,
          url,
          productId: product.id,
          productName: product.name,
          brand: product.brand,
          category: product.categoryName || product.category,
          product,
        }));
      })
      .filter((item) => {
        if (!keyword) return true;
        return [item.productName, item.brand, item.category].join(' ').toLowerCase().includes(keyword);
      });
  }, [products, query]);

  useEffect(() => {
    const viewId = searchParams.get('view');
    if (!viewId || loading || images.length === 0) return;
    const idx = images.findIndex((img) => img.id === viewId);
    if (idx >= 0 && !isModalOpen) {
      setActiveIndex(idx);
      setIsModalOpen(true);
    }
  }, [searchParams, loading, images, isModalOpen]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-5 rounded-lg border border-red-100 bg-white px-4 py-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="flex items-center gap-2 border-b-2 border-primary pb-3 text-2xl font-black text-primary">
                <ImageIcon className="h-6 w-6" />
                Hình ảnh
              </div>
              <p className="mt-3 text-sm font-medium text-slate-500">
                Thư viện hình ảnh sản phẩm, thiết kế và góc nhìn thực tế.
              </p>
            </div>

            <div className="grid gap-2 sm:grid-cols-[minmax(0,320px)]">
              <label className="relative block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Tìm ảnh theo sản phẩm, hãng..."
                  className="h-10 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-red-100"
                />
              </label>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="rounded-lg bg-white py-16 text-center text-gray-400 shadow-sm">Đang tải hình ảnh...</div>
        ) : images.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white py-16 text-center text-sm font-semibold text-gray-400">
            Chưa có hình ảnh phù hợp.
          </div>
        ) : (
          <div className="columns-2 gap-4 sm:columns-3 lg:columns-4">
            {images.map((item, index) => (
              <ImageTile
                key={item.id}
                item={item}
                index={index}
                onOpen={() => {
                  setActiveIndex(index);
                  setIsModalOpen(true);
                }}
              />
            ))}
          </div>
        )}

        <ImagesModal
          isOpen={isModalOpen}
          playlist={images}
          initialIndex={activeIndex}
          onClose={() => setIsModalOpen(false)}
        />
      </div>
    </div>
  );
}
