import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Clock, Heart, Play, Search, Share2, Video } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiDb } from '../services/apiDb';
import ReelsModal from '../components/video/ReelsModal';

type SortMode = 'newest' | 'liked' | 'title';

const topicTabs = ['Tất cả', 'Tuyển chọn', 'Điện thoại', 'Laptop', 'Phụ kiện', 'Đồng hồ', 'Camera', 'Mẹo sử dụng', 'Chính sách'];
const demoComments = [
  'Shop tư vấn rõ, video dễ hiểu.',
  'Mẫu này nhìn thực tế hơn ảnh sản phẩm.',
  'Có thể thêm so sánh giá ở video sau không?',
  'Đúng thứ mình đang cần xem trước khi mua.',
  'Video ngắn nhưng đủ thông tin chính.',
];

const aspectTestVideos = [
  {
    id: 'aspect-test-landscape',
    title: '[TEST] Video ngang 16:9',
    description: 'Video mẫu để kiểm tra khung mở video tự đổi sang bố cục ngang.',
    videoUrl: 'https://samplefile.com/samples/download/video/mp4/mp4_h264_aac_360p_sample.mp4',
    thumbnailUrl: '',
    category: 'Tuyển chọn',
    createdAt: '2999-01-03T00:00:00.000Z',
  },
  {
    id: 'aspect-test-portrait',
    title: '[TEST] Video dọc 9:16',
    description: 'Video mẫu để kiểm tra khung mở video tự đổi sang bố cục dọc.',
    videoUrl: 'https://samplefile.com/samples/download/video/mp4/mp4_portrait_h264_aac_sample.mp4',
    thumbnailUrl: '',
    category: 'Tuyển chọn',
    createdAt: '2999-01-02T00:00:00.000Z',
  },
  {
    id: 'aspect-test-square',
    title: '[TEST] Video vuông 1:1',
    description: 'Video mẫu để kiểm tra khung mở video tự đổi sang bố cục vuông.',
    videoUrl: 'https://samplefile.com/samples/download/video/mp4/mp4_square_h264_aac_sample.mp4',
    thumbnailUrl: '',
    category: 'Tuyển chọn',
    createdAt: '2999-01-01T00:00:00.000Z',
  },
];

function videoImage(video: any) {
  return video.thumbnailUrl || video.cover || video.coverUrl || '';
}

function textOf(video: any) {
  return [video.category, video.type, video.topic, video.title, video.description].filter(Boolean).join(' ').toLowerCase();
}

function inferCategory(video: any) {
  const text = textOf(video);
  if (text.includes('iphone') || text.includes('samsung') || text.includes('oppo') || text.includes('điện thoại')) return 'Điện thoại';
  if (text.includes('laptop') || text.includes('macbook') || text.includes('asus') || text.includes('it')) return 'Laptop';
  if (text.includes('airpods') || text.includes('sạc') || text.includes('cáp') || text.includes('phụ kiện')) return 'Phụ kiện';
  if (text.includes('watch') || text.includes('đồng hồ')) return 'Đồng hồ';
  if (text.includes('dji') || text.includes('camera') || text.includes('vlog')) return 'Camera';
  if (text.includes('chính sách') || text.includes('bảo hành') || text.includes('đổi trả')) return 'Chính sách';
  if (text.includes('mẹo') || text.includes('cách chọn')) return 'Mẹo sử dụng';
  return 'Tuyển chọn';
}

function videoKey(video: any) {
  return `video_like_${video.id}`;
}

function demoDuration(video: any, index: number) {
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const seconds = 14 + (seed % 48);
  return `00:${String(seconds).padStart(2, '0')}`;
}

function demoLikeCount(video: any, index: number) {
  if (typeof video.likeCount === 'number') return video.likeCount.toLocaleString('vi-VN');
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const value = 1.2 + ((seed % 240) / 10);
  return `${value.toFixed(1)}K`;
}

function commentFor(video: any, index: number) {
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return demoComments[seed % demoComments.length];
}

function findRelatedProduct(video: any, products: any[]) {
  const text = textOf(video);
  const direct = products.find((product) => {
    const name = String(product.name || '').toLowerCase();
    return name && (text.includes(name) || name.split(/\s+/).filter((part) => part.length > 2).some((part) => text.includes(part)));
  });
  if (direct) return direct;

  const category = inferCategory(video);
  return products.find((product) => String(product.category || product.categoryName || '').toLowerCase().includes(category.toLowerCase()))
    || products.find((product) => String(product.categorySlug || '').toLowerCase().includes(category === 'Điện thoại' ? 'smartphones' : category.toLowerCase()))
    || products[0];
}


function heightForTile(index: number) {
  const heights = [420, 300, 360, 280, 400, 320, 340, 380, 260, 440];
  return heights[index % heights.length];
}

function useColumns(containerRef: React.RefObject<HTMLDivElement | null>) {
  const [cols, setCols] = useState(3);
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width;
      setCols(w >= 1024 ? 4 : w >= 768 ? 3 : 2);
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, [containerRef]);
  return cols;
}

function distributeToColumns<T>(items: T[], colCount: number, getHeight: (item: T, i: number) => number) {
  const columns: T[][] = Array.from({ length: colCount }, () => []);
  const heights = new Array(colCount).fill(0);
  items.forEach((item, i) => {
    const shortest = heights.indexOf(Math.min(...heights));
    columns[shortest].push(item);
    heights[shortest] += getHeight(item, i);
  });
  return columns;
}

function shortDescription(video: any) {
  return video.shortDescription || video.description || 'Xem nhanh điểm nổi bật, trải nghiệm thực tế và thông tin cần biết trước khi chọn mua.';
}

interface VideoTileProps {
  video: any;
  index: number;
  liked: boolean;
  onOpen: () => void;
  onLike: () => void;
  onShare: () => void;
}

function VideoTile({ video, index, liked, onOpen, onLike, onShare }: VideoTileProps) {
  const previewRef = React.useRef<HTMLVideoElement | null>(null);
  const image = videoImage(video);
  const h = heightForTile(index);
  const [touched, setTouched] = useState(false);
  const [hovered, setHovered] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isActive = hovered || touched;

  function handleMouseEnter() {
    hoverTimer.current = setTimeout(() => {
      setHovered(true);
      if (previewRef.current && video.videoUrl) {
        previewRef.current.currentTime = 0;
        previewRef.current.play().catch(() => undefined);
      }
    }, 150);
  }

  function handleMouseLeave() {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHovered(false);
    if (previewRef.current) {
      previewRef.current.pause();
      previewRef.current.currentTime = 0;
    }
  }

  function handleTouch(event: React.TouchEvent) {
    if (!touched) {
      event.preventDefault();
      setTouched(true);
    }
  }

  useEffect(() => {
    if (!touched) return;
    function dismiss() { setTouched(false); }
    document.addEventListener('touchstart', dismiss, { once: true });
    return () => document.removeEventListener('touchstart', dismiss);
  }, [touched]);

  return (
    <article
      style={{ height: h }}
      className="relative mb-4 cursor-pointer overflow-hidden rounded-xl bg-gray-900 shadow-md transition-all duration-300 hover:shadow-2xl"
      onClick={onOpen}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onTouchStart={handleTouch}
      role="group"
      aria-label={video.title || 'Video sản phẩm'}
    >
      <div className="absolute inset-0">
        {video.videoUrl ? (
          <video
            ref={previewRef}
            src={video.videoUrl}
            poster={image}
            muted
            loop
            playsInline
            preload="metadata"
            className={`h-full w-full object-cover transition-all duration-500 ${isActive ? 'scale-[1.03] blur-[2px]' : ''}`}
          />
        ) : image ? (
          <img
            src={image}
            alt={video.title || 'Video'}
            className={`h-full w-full object-cover transition-all duration-500 ${isActive ? 'scale-[1.03] blur-[2px]' : ''}`}
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm font-bold text-slate-400">Chưa có ảnh</div>
        )}
      </div>

      <div className={`absolute inset-0 z-10 flex items-center justify-center transition-opacity duration-300 ${isActive ? 'pointer-events-none opacity-0' : 'opacity-100'}`}>
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/30 bg-white/20 shadow-lg backdrop-blur-sm">
          <div className="ml-1 h-0 w-0 border-b-8 border-l-[14px] border-t-8 border-b-transparent border-l-white border-t-transparent" />
        </div>
      </div>

      <div className={`absolute left-3 right-3 top-3 z-20 flex items-start justify-between transition-opacity duration-300 ${isActive ? 'opacity-0' : 'opacity-100'}`}>
        <span className="rounded-full bg-white/95 px-2.5 py-1 text-xs font-bold text-primary shadow-sm">{inferCategory(video)}</span>
        <span className="rounded-full bg-black/70 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-md">{demoDuration(video, index)}</span>
      </div>

      <div className={`absolute inset-x-0 bottom-0 z-20 transition-transform duration-300 ease-out ${isActive ? 'translate-y-0' : 'translate-y-full'}`}>
        <div className="flex flex-col gap-1.5 px-3 pb-3 pt-10" style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.35) 55%, transparent 100%)' }}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 flex-1 text-sm font-medium leading-snug text-white">{video.title || 'Video sản phẩm'}</h3>
            <div className="flex shrink-0 gap-2 pt-0.5">
              <button
                type="button"
                onClick={(event) => { event.stopPropagation(); onLike(); }}
                className={`transition-colors ${liked ? 'text-red-400' : 'text-gray-300 hover:text-white'}`}
                aria-label={liked ? 'Bỏ thích video' : 'Thích video'}
                aria-pressed={liked}
              >
                <Heart className={`h-[18px] w-[18px] ${liked ? 'fill-current' : ''}`} />
              </button>
              <button
                type="button"
                onClick={(event) => { event.stopPropagation(); onShare(); }}
                className="text-gray-300 transition-colors hover:text-white"
                aria-label="Chia sẻ video"
              >
                <Share2 className="h-[18px] w-[18px]" />
              </button>
            </div>
          </div>

          <div className="-mt-0.5 flex gap-3 text-[11px] font-medium text-gray-400">
            <span>{video.commentCount} bình luận</span>
            <span>{demoLikeCount(video, index)} lượt thích</span>
          </div>

          {video.product && (
            <Link
              to={`/product/${video.product.id}`}
              onClick={(event) => event.stopPropagation()}
              className="mt-1 flex w-max max-w-full items-center gap-2 rounded-full border border-white/15 bg-white/10 px-2 py-1.5 backdrop-blur-md transition-colors hover:bg-white/20"
            >
              {video.product.imageUrl ? (
                <span className="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white">
                  <img src={video.product.imageUrl} alt="" className="h-full w-full object-contain" loading="lazy" />
                </span>
              ) : (
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/20 text-[9px] text-white/50">SP</span>
              )}
              <span className="min-w-0 flex-1 truncate text-xs font-medium text-white">{video.product.name}</span>
              <span className="shrink-0 pr-1 text-xs font-bold text-red-400">{Number(video.product.discountPrice || video.product.price || 0).toLocaleString('vi-VN')}đ</span>
            </Link>
          )}
        </div>
      </div>

      <span className="sr-only">
        {video.title}. {inferCategory(video)}. {demoDuration(video, index)}. {video.commentCount} bình luận. {demoLikeCount(video, index)} lượt thích.
      </span>
    </article>
  );
}

interface MasonryGridProps {
  videos: any[];
  likedIds: Set<string>;
  onOpen: (index: number) => void;
  onLike: (video: any) => void;
  onShare: (video: any) => void;
}

function MasonryGrid({ videos, likedIds, onOpen, onLike, onShare }: MasonryGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cols = useColumns(containerRef);

  const indexedVideos = useMemo(() => videos.map((v, i) => ({ ...v, _origIndex: i })), [videos]);

  const columns = useMemo(
    () => distributeToColumns(indexedVideos, cols, (_item: any, i: number) => heightForTile(i) + 80),
    [indexedVideos, cols],
  );

  return (
    <div ref={containerRef} className="flex gap-4">
      {columns.map((col, colIdx) => (
        <div key={colIdx} className="flex-1 min-w-0">
          {col.map((video: any) => (
            <VideoTile
              key={video.id}
              video={video}
              index={video._origIndex}
              liked={likedIds.has(video.id)}
              onOpen={() => onOpen(video._origIndex)}
              onLike={() => onLike(video)}
              onShare={() => onShare(video)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function VideoPage() {
  const [activeTab, setActiveTab] = useState('Tất cả');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortMode>('newest');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [videos, setVideos] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [likedIds, setLikedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    Promise.all([
      apiDb.listVideos().catch(() => []),
      apiDb.listProducts().catch(() => []),
    ])
      .then(([videoData, productData]) => {
        setVideos([...aspectTestVideos, ...videoData]);
        setProducts(productData);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setLikedIds(new Set(videos.filter((video) => localStorage.getItem(videoKey(video)) === '1').map((video) => video.id)));
  }, [videos]);

  const [searchParams] = useSearchParams();

  const availableTabs = useMemo(() => {
    const realTabs = new Set<string>(videos.map(inferCategory));
    return topicTabs.filter((tab) => tab === 'Tất cả' || realTabs.has(tab));
  }, [videos]);

  const filteredVideos = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return videos
      .filter((video) => activeTab === 'Tất cả' || inferCategory(video) === activeTab)
      .filter((video) => !keyword || [video.title, video.description, inferCategory(video)].filter(Boolean).join(' ').toLowerCase().includes(keyword))
      .sort((a, b) => {
        if (sort === 'liked') return Number(likedIds.has(b.id)) - Number(likedIds.has(a.id));
        if (sort === 'title') return String(a.title || '').localeCompare(String(b.title || ''), 'vi');
        return new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime();
      });
  }, [activeTab, likedIds, query, sort, videos]);

  const displayVideos = useMemo(() => {
    return filteredVideos.map((video, index) => ({
      ...video,
      product: video.product || findRelatedProduct(video, products),
      comments: video.comments || [
        { id: `${video.id}-comment-1`, userName: 'Minh Anh', content: commentFor(video, index) },
        { id: `${video.id}-comment-2`, userName: 'Echophone', content: 'Cảm ơn bạn đã xem video. Shop có thể tư vấn thêm sản phẩm phù hợp với nhu cầu của bạn.' },
      ],
      commentCount: video.commentCount || 8 + ((index * 7) % 56),
    }));
  }, [filteredVideos, products]);

  useEffect(() => {
    const watchId = searchParams.get('watch');
    if (!watchId || loading || displayVideos.length === 0) return;
    const idx = displayVideos.findIndex((v: any) => v.id === watchId);
    if (idx >= 0 && !isModalOpen) {
      setActiveIndex(idx);
      setIsModalOpen(true);
    }
  }, [searchParams, loading, displayVideos, isModalOpen]);

  function openVideo(index: number) {
    setActiveIndex(index);
    setIsModalOpen(true);
  }

  function toggleLike(video: any) {
    const next = new Set(likedIds);
    if (next.has(video.id)) {
      next.delete(video.id);
      localStorage.removeItem(videoKey(video));
    } else {
      next.add(video.id);
      localStorage.setItem(videoKey(video), '1');
    }
    setLikedIds(next);
  }

  async function shareVideo(video: any) {
    const url = `${window.location.origin}/video?watch=${encodeURIComponent(video.id)}`;
    if (navigator.share) {
      await navigator.share({ title: video.title || 'Video', url }).catch(() => undefined);
      return;
    }
    await navigator.clipboard?.writeText(url);
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-5 rounded-lg border border-red-100 bg-white px-4 py-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="flex items-center gap-2 border-b-2 border-primary pb-3 text-2xl font-black text-primary">
                <Video className="h-6 w-6" />
                Video
              </div>
              <p className="mt-3 text-sm font-medium text-slate-500">Kho video sản phẩm, mẹo chọn mua và hướng dẫn dịch vụ từ Echophone.</p>
            </div>

            <div className="grid gap-2 sm:grid-cols-[minmax(0,320px)_150px]">
              <label className="relative block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Tìm video, chủ đề..."
                  className="h-10 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-red-100"
                />
              </label>
              <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)} className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-primary">
                <option value="newest">Mới nhất</option>
                <option value="liked">Đã thích</option>
                <option value="title">Tên A-Z</option>
              </select>
            </div>
          </div>
        </div>

        <div className="sticky top-0 z-10 mb-5 flex items-center gap-2 rounded-lg border border-slate-100 bg-white/95 px-3 py-3 shadow-sm backdrop-blur">
          <button type="button" className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-700 ring-1 ring-slate-100 sm:flex" aria-label="Cuộn trái">
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {availableTabs.map((category) => (
              <button
                key={category}
                onClick={() => setActiveTab(category)}
                className={`h-9 shrink-0 whitespace-nowrap rounded-md px-4 text-sm font-bold transition-colors ${
                  activeTab === category ? 'bg-primary text-white shadow-sm shadow-red-100' : 'bg-slate-50 text-slate-700 ring-1 ring-slate-100 hover:bg-slate-100'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
          <button type="button" className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-700 ring-1 ring-slate-100 sm:flex" aria-label="Cuộn phải">
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {loading ? (
          <div className="rounded-lg bg-white py-16 text-center text-gray-400 shadow-sm">Đang tải video...</div>
        ) : displayVideos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white py-16 text-center text-sm font-semibold text-gray-400">
            Chưa có video phù hợp để hiển thị.
          </div>
        ) : (
          <MasonryGrid
            videos={displayVideos}
            likedIds={likedIds}
            onOpen={openVideo}
            onLike={toggleLike}
            onShare={shareVideo}
          />
        )}

        <ReelsModal isOpen={isModalOpen} playlist={displayVideos} initialIndex={activeIndex} onClose={() => setIsModalOpen(false)} />
      </div>
    </div>
  );
}
