import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, Heart, Search, Share2, Video } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import { publicApi } from '../../../services/publicApi';
import ReelsModal from '../components/ReelsModal';

type SortMode = 'newest' | 'views' | 'likes' | 'liked' | 'title';

const VIDEO_PAGE_LIMIT = 12;
const topicTabs = ['Tất cả', 'Liên quan sản phẩm', 'Tin tức', 'Mẹo hay', 'Dịch vụ', 'Đánh giá / trải nghiệm', 'Khác'];
const videoCategoryLabels: Record<string, string> = {
  PRODUCT: 'Liên quan sản phẩm',
  NEWS: 'Tin tức',
  TIPS: 'Mẹo hay',
  SERVICE: 'Dịch vụ',
  REVIEW: 'Đánh giá / trải nghiệm',
  OTHER: 'Khác',
};
function videoImage(video: any) {
  return video.thumbnailUrl || (isYouTubeVideo(video) ? video.youtubeThumbnailUrl : '') || video.cover || video.coverUrl || '';
}

function isYouTubeVideo(video: any) {
  const url = String(video.videoUrl || video.embedUrl || '');
  return video.videoSource === 'YOUTUBE' || url.includes('youtube.com') || url.includes('youtu.be');
}

function textOf(video: any) {
  return [video.category, video.type, video.topic, video.title, video.description].filter(Boolean).join(' ').toLowerCase();
}

function inferCategory(video: any) {
  if (video.videoCategory && videoCategoryLabels[video.videoCategory]) return videoCategoryLabels[video.videoCategory];
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

function formatDuration(seconds?: number) {
  if (!seconds || !Number.isFinite(seconds)) return '';
  const rounded = Math.floor(seconds);
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const remainSeconds = rounded % 60;
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainSeconds).padStart(2, '0')}`;
  return `${minutes}:${String(remainSeconds).padStart(2, '0')}`;
}

function demoLikeCount(video: any, index: number) {
  if (typeof video.likeCount === 'number') return video.likeCount.toLocaleString('vi-VN');
  return '0';
}

function numericCount(value: unknown) {
  const count = Number(value || 0);
  return Number.isFinite(count) ? count : 0;
}

function formatCount(value: unknown) {
  return numericCount(value).toLocaleString('vi-VN');
}

function findRelatedProduct(video: any, products: any[]) {
  if (Array.isArray(video.products) && video.products.length > 0) return video.products[0];
  if (!Array.isArray(video.productIds) || video.productIds.length === 0) return null;
  return products.find((product) => video.productIds.includes(product.id)) || null;
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

function likedVideoIds(videos: any[]) {
  const ids = new Set<string>();
  for (const video of videos) {
    if (localStorage.getItem(videoKey(video)) === '1') {
      ids.add(video.id);
    }
  }
  return ids;
}

function videoMatchesFilter(video: any, activeTab: string, keyword: string) {
  const category = inferCategory(video);
  if (activeTab !== 'Tất cả' && category !== activeTab) return false;
  if (!keyword) return true;
  return [video.title, video.description, category].filter(Boolean).join(' ').toLowerCase().includes(keyword);
}


function fallbackRatioForTile(index: number) {
  const ratios = [16 / 10, 4 / 5, 16 / 9, 1, 3 / 4, 16 / 11, 5 / 4, 9 / 12];
  return ratios[index % ratios.length];
}

function clampRatio(ratio: number) {
  return Math.max(0.72, Math.min(ratio, 1.85));
}

function shortDescription(video: any) {
  return video.shortDescription || video.description || 'Xem nhanh điểm nổi bật, trải nghiệm thực tế và thông tin cần biết trước khi chọn mua.';
}

async function shareVideo(video: any) {
  const url = `${window.location.origin}/video?watch=${encodeURIComponent(video.id)}`;
  if (navigator.share) {
    await navigator.share({ title: video.title || 'Video', url }).catch(() => undefined);
    return;
  }
  await navigator.clipboard?.writeText(url);
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
  const [posterRatio, setPosterRatio] = useState<number | null>(null);
  const [videoRatio, setVideoRatio] = useState<number | null>(null);
  const [durationLabel, setDurationLabel] = useState(video.duration || '');
  const [touched, setTouched] = useState(false);
  const [hovered, setHovered] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isActive = hovered || touched;
  const resolvedRatio = clampRatio(videoRatio ?? posterRatio ?? fallbackRatioForTile(index));
  const imageMediaClassName = 'relative z-10 h-full w-full object-contain transition-opacity duration-300';
  const videoMediaClassName = 'relative z-10 h-full w-full object-contain transition-opacity duration-300';

  function handleImageLoad(event: React.SyntheticEvent<HTMLImageElement>) {
    const { naturalWidth, naturalHeight } = event.currentTarget;
    if (naturalWidth && naturalHeight) setPosterRatio(naturalWidth / naturalHeight);
  }

  function handleVideoMetadata(event: React.SyntheticEvent<HTMLVideoElement>) {
    const videoEl = event.currentTarget;
    setDurationLabel(formatDuration(videoEl.duration));
    if (videoEl.videoWidth && videoEl.videoHeight) {
      setVideoRatio(videoEl.videoWidth / videoEl.videoHeight);
    }
  }

  function handleMouseEnter() {
    hoverTimer.current = setTimeout(() => {
      setHovered(true);
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
    document.addEventListener('touchstart', dismiss, { once: true, passive: true });
    return () => document.removeEventListener('touchstart', dismiss);
  }, [touched]);

  useEffect(() => {
    if (!isActive || !previewRef.current || !video.videoUrl) return;
    previewRef.current.currentTime = 0;
    previewRef.current.play().catch(() => undefined);
  }, [isActive, video.videoUrl]);

  return (
    <article
      style={{ aspectRatio: resolvedRatio }}
      className="group relative mb-4 inline-block w-full min-w-0 break-inside-avoid cursor-pointer overflow-hidden rounded-2xl border border-white/70 bg-slate-950 align-top shadow-[0_10px_28px_rgba(15,23,42,0.10)] ring-1 ring-slate-900/5 transition-[border-color,box-shadow,transform] duration-300 hover:-translate-y-0.5 hover:border-red-200 hover:shadow-[0_18px_36px_rgba(15,23,42,0.18)] motion-reduce:transform-none motion-reduce:transition-none"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role="group"
      aria-label={video.title || 'Video sản phẩm'}
    >
      <div className="absolute inset-0 bg-slate-950">
        {video.videoUrl && !isYouTubeVideo(video) && !videoRatio && (
          <video
            aria-label={video.title ? `Tải thông tin video ${video.title}` : 'Tải thông tin video'}
            src={video.videoUrl}
            preload="metadata"
            muted
            playsInline
            className="hidden"
            onLoadedMetadata={handleVideoMetadata}
          />
        )}
        {image && (
          <img
            src={image}
            alt=""
            aria-hidden="true"
            className="absolute inset-0 h-full w-full scale-110 object-cover opacity-45 blur-2xl saturate-125 transition-transform duration-700 group-hover:scale-[1.14]"
            loading="lazy"
          />
        )}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_36%,rgba(255,255,255,0.10),transparent_34%),linear-gradient(to_bottom,rgba(2,6,23,0.10),rgba(2,6,23,0.28))]" />
        {video.videoUrl && !isYouTubeVideo(video) && isActive ? (
          <video
            aria-label={video.title || 'Video sản phẩm'}
            ref={previewRef}
            src={video.videoUrl}
            poster={image}
            muted
            loop
            playsInline
            preload="metadata"
            onLoadedMetadata={handleVideoMetadata}
            className={videoMediaClassName}
          />
        ) : video.videoUrl && !isYouTubeVideo(video) && image ? (
          <img
            src={image}
            alt={video.title || 'Video'}
            className={imageMediaClassName}
            loading="lazy"
            onLoad={handleImageLoad}
          />
        ) : image ? (
          <img
            src={image}
            alt={video.title || 'Video'}
            className={imageMediaClassName}
            loading="lazy"
            onLoad={handleImageLoad}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm font-bold text-slate-400">Chưa có ảnh</div>
        )}
      </div>

      <button
        type="button"
        aria-label={video.title ? `Mở video ${video.title}` : 'Mở video sản phẩm'}
        className="absolute inset-0 z-10 cursor-pointer"
        onClick={onOpen}
        onTouchStart={handleTouch}
      />

      <div className={`pointer-events-none absolute inset-0 z-10 flex items-center justify-center transition-opacity duration-300 ${isActive ? 'opacity-0' : 'opacity-100'}`}>
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/40 bg-white/25 shadow-[0_10px_30px_rgba(15,23,42,0.25)] backdrop-blur-md transition-transform duration-300 group-hover:scale-105">
          <div className="ml-1 h-0 w-0 border-b-8 border-l-[14px] border-t-8 border-b-transparent border-l-white border-t-transparent" />
        </div>
      </div>

      <div className={`absolute left-2 right-2 top-2 z-20 flex items-start justify-between gap-1.5 transition-opacity duration-300 sm:left-3 sm:right-3 sm:top-3 ${isActive ? 'opacity-0' : 'opacity-100'}`}>
        <span className="max-w-[70%] truncate rounded-full border border-white/70 bg-white/95 px-2 py-1 text-[8px] font-black uppercase text-primary shadow-sm sm:px-2.5 sm:text-[9px] lg:text-xs lg:normal-case">{inferCategory(video)}</span>
        {(durationLabel || isYouTubeVideo(video)) && <span className="rounded-full bg-slate-950/80 px-2 py-1 text-[8px] font-bold text-white shadow-sm backdrop-blur-md sm:px-2.5 sm:text-[9px] lg:text-xs lg:font-medium">{durationLabel || 'YouTube'}</span>}
      </div>

      <div className={`absolute inset-x-0 bottom-0 z-20 transition-transform duration-300 ease-out ${isActive ? 'translate-y-0' : 'translate-y-0 lg:translate-y-full'}`}>
        <div className="flex flex-col gap-1 px-2 pb-2 pt-10 sm:gap-1.5 sm:px-3 sm:pb-3" style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.35) 55%, transparent 100%)' }}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 flex-1 text-[11px] font-bold leading-tight text-white sm:text-sm sm:font-medium sm:leading-snug">{video.title || 'Video sản phẩm'}</h3>
            <div className="flex shrink-0 gap-1 pt-0.5 sm:gap-1.5">
              <button
                type="button"
                onClick={(event) => { event.stopPropagation(); onLike(); }}
                className={`relative z-30 flex h-11 w-11 items-center justify-center transition-colors sm:h-8 sm:w-8 ${liked ? 'text-red-400' : 'text-gray-300 hover:text-white'}`}
                aria-label={liked ? 'Bỏ thích video' : 'Thích video'}
                aria-pressed={liked}
              >
                <Heart className={`h-[18px] w-[18px] ${liked ? 'fill-current' : ''}`} />
              </button>
              <button
                type="button"
                onClick={(event) => { event.stopPropagation(); onShare(); }}
                className="relative z-30 flex h-11 w-11 items-center justify-center text-gray-300 transition-colors hover:text-white sm:h-8 sm:w-8"
                aria-label="Chia sẻ video"
              >
                <Share2 className="h-[18px] w-[18px]" />
              </button>
            </div>
          </div>

          <div className="-mt-0.5 hidden flex-wrap gap-x-3 gap-y-1 text-[11px] font-medium text-gray-400 sm:flex">
            <span>{video.commentCount} bình luận</span>
            <span className="inline-flex items-center gap-1"><Eye className="h-3 w-3" />{formatCount(video.viewCount)} lượt xem</span>
            <span>{demoLikeCount(video, index)} lượt thích</span>
          </div>

          {video.product && (
            <Link
              to={`/product/${video.product.id}`}
              onClick={(event) => event.stopPropagation()}
              className="relative z-30 mt-1 hidden w-max max-w-full items-center gap-2 rounded-full border border-white/15 bg-white/10 px-2 py-1.5 backdrop-blur-md transition-colors hover:bg-white/20 sm:flex"
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
        {video.title}. {inferCategory(video)}. {durationLabel}. {video.commentCount} bình luận. {formatCount(video.viewCount)} lượt xem. {demoLikeCount(video, index)} lượt thích.
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
  const indexedVideos = useMemo(() => videos.map((v, i) => ({ ...v, _origIndex: i })), [videos]);

  return (
    <div className="min-w-0 columns-1 gap-4 sm:columns-2 lg:columns-3">
      {indexedVideos.map((video: any) => (
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
  );
}

export default function VideoPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('Tất cả');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortMode>('newest');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [modalPlaylist, setModalPlaylist] = useState<any[]>([]);
  const [videos, setVideos] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const videoPageRef = useRef(1);
  const [hasMoreVideos, setHasMoreVideos] = useState(false);
  const [likedIds, setLikedIds] = useState<Set<string>>(new Set());
  const dismissedWatchRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const loadMoreInFlightRef = useRef(false);
  const tabsRef = useRef<HTMLDivElement | null>(null);
  const likeRequestVersionsRef = useRef<Map<string, number> | null>(null);
  if (!likeRequestVersionsRef.current) likeRequestVersionsRef.current = new Map<string, number>();
  const likeRequestVersions = likeRequestVersionsRef.current;

  useEffect(() => {
    mountedRef.current = true;
    publicApi.listVideosPage({ page: 1, limit: VIDEO_PAGE_LIMIT })
      .catch(() => ({ items: [], page: 1, hasMore: false }))
      .then((videoData) => {
        if (!mountedRef.current) return;
        const items = Array.isArray(videoData) ? videoData : videoData.items || [];
        setVideos(items);
        setLikedIds(likedVideoIds(items));
        videoPageRef.current = Number(videoData.page || 1);
        setHasMoreVideos(Boolean(videoData.hasMore));
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false);
      });

    publicApi.listProducts({ limit: 100 })
      .then((productData) => {
        if (mountedRef.current) setProducts(productData);
      })
      .catch(() => undefined);

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const [searchParams, setSearchParams] = useSearchParams();

  const availableTabs = useMemo(() => {
    const realTabs = new Set<string>(videos.map(inferCategory));
    return topicTabs.filter((tab) => tab === 'Tất cả' || realTabs.has(tab));
  }, [videos]);

  const filteredVideos = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const matchedVideos: any[] = [];
    for (const video of videos) {
      if (videoMatchesFilter(video, activeTab, keyword)) {
        matchedVideos.push(video);
      }
    }
    return matchedVideos
      .sort((a, b) => {
        if (sort === 'views') return numericCount(b.viewCount) - numericCount(a.viewCount);
        if (sort === 'likes') return numericCount(b.likeCount) - numericCount(a.likeCount);
        if (sort === 'liked') return Number(likedIds.has(b.id)) - Number(likedIds.has(a.id));
        if (sort === 'title') return String(a.title || '').localeCompare(String(b.title || ''), 'vi');
        return new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime();
      });
  }, [activeTab, likedIds, query, sort, videos]);

  const displayVideos = useMemo(() => {
    return filteredVideos.map((video, index) => ({
      ...video,
      product: video.product || findRelatedProduct(video, products),
      comments: Array.isArray(video.comments) ? video.comments : [],
      commentCount: typeof video.commentCount === 'number'
        ? video.commentCount
        : (Array.isArray(video.comments) ? video.comments.length : 0),
    }));
  }, [filteredVideos, products]);

  useEffect(() => {
    const watchId = searchParams.get('watch');
    if (!watchId) {
      dismissedWatchRef.current = null;
      return;
    }
    if (watchId === dismissedWatchRef.current || loading || displayVideos.length === 0) return;
    const idx = displayVideos.findIndex((v: any) => v.id === watchId);
    if (idx >= 0 && !isModalOpen) {
      setModalPlaylist(displayVideos);
      setActiveIndex(idx);
      setIsModalOpen(true);
    }
  }, [searchParams, loading, displayVideos, isModalOpen]);

  useEffect(() => {
    if (!isModalOpen || modalPlaylist.length === 0) return;
    setModalPlaylist((current) => current.map((video) => displayVideos.find((item: any) => item.id === video.id) || video));
  }, [displayVideos, isModalOpen, modalPlaylist.length]);

  function openVideo(index: number) {
    setModalPlaylist(displayVideos);
    setActiveIndex(index);
    setIsModalOpen(true);
  }

  function closeVideoModal() {
    dismissedWatchRef.current = searchParams.get('watch');
    setIsModalOpen(false);
    setSearchParams((params) => {
      const next = new URLSearchParams(params);
      next.delete('watch');
      return next;
    }, { replace: true });
  }

  async function toggleLike(video: any) {
    if (!user) {
      window.alert('Vui lòng đăng nhập để thích video.');
      return;
    }
    const wasLiked = likedIds.has(video.id);
    const requestVersion = (likeRequestVersions.get(video.id) || 0) + 1;
    likeRequestVersions.set(video.id, requestVersion);
    const next = new Set(likedIds);
    if (wasLiked) {
      next.delete(video.id);
      localStorage.removeItem(videoKey(video));
    } else {
      next.add(video.id);
      localStorage.setItem(videoKey(video), '1');
    }
    setLikedIds(next);
    setVideos((items) => items.map((item) => {
      if (item.id !== video.id || typeof item.likeCount !== 'number') return item;
      return { ...item, likeCount: Math.max(0, item.likeCount + (wasLiked ? -1 : 1)) };
    }));
    publicApi.toggleVideoLike(video.id).then((result) => {
      if (!mountedRef.current || likeRequestVersions.get(video.id) !== requestVersion) return;
      if (typeof result?.liked === 'boolean') {
        setLikedIds((current) => {
          const synced = new Set(current);
          if (result.liked) {
            synced.add(video.id);
            localStorage.setItem(videoKey(video), '1');
          } else {
            synced.delete(video.id);
            localStorage.removeItem(videoKey(video));
          }
          return synced;
        });
      }
      if (typeof result?.likeCount === 'number') {
        setVideos((items) => items.map((item) => item.id === video.id ? { ...item, likeCount: result.likeCount } : item));
      }
    }).catch(() => undefined);
  }

  async function loadMoreVideos() {
    if (loadMoreInFlightRef.current || !hasMoreVideos) return;
    loadMoreInFlightRef.current = true;
    setLoadingMore(true);
    const nextPage = videoPageRef.current + 1;
    try {
      const data = await publicApi.listVideosPage({ page: nextPage, limit: VIDEO_PAGE_LIMIT });
      if (!mountedRef.current) return;
      const items = Array.isArray(data) ? data : data.items || [];
      setVideos((current) => {
        const seen = new Set(current.map((item) => item.id));
        return [...current, ...items.filter((item: any) => !seen.has(item.id))];
      });
      setLikedIds((current) => {
        const nextLikedIds = new Set(current);
        for (const item of items) {
          if (localStorage.getItem(videoKey(item)) === '1') nextLikedIds.add(item.id);
        }
        return nextLikedIds;
      });
      videoPageRef.current = Number(data.page || nextPage);
      setHasMoreVideos(Boolean(data.hasMore));
    } finally {
      loadMoreInFlightRef.current = false;
      if (mountedRef.current) setLoadingMore(false);
    }
  }

  const scrollTabs = useCallback((direction: -1 | 1) => {
    tabsRef.current?.scrollBy({ left: direction * 280, behavior: 'smooth' });
  }, []);

  return (
    <div className="min-h-screen overflow-x-hidden bg-background">
      <div className="mx-auto w-full max-w-7xl px-3 py-4 sm:px-5 sm:py-6 lg:px-8">
        <section className="mb-4 rounded-lg border border-red-100 bg-white px-4 py-4 shadow-sm sm:px-5 lg:mb-5">
          <div className="flex flex-col gap-3 sm:gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="flex items-center gap-2 border-b-2 border-primary pb-2.5 text-xl font-black text-primary sm:pb-3 sm:text-2xl">
                <Video className="h-5 w-5 sm:h-6 sm:w-6" />
                Video
              </h1>
              <p className="mt-2 text-xs font-medium text-slate-500 sm:mt-3 sm:text-sm">Kho video sản phẩm, mẹo chọn mua và hướng dẫn dịch vụ từ Echophone.</p>
            </div>

            <div className="grid gap-2 sm:grid-cols-[minmax(0,320px)_150px]">
              <label className="relative block">
                <span className="sr-only">Tìm video</span>
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Tìm video, chủ đề..."
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-base shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-red-100 sm:h-10 sm:text-sm lg:shadow-none"
                />
              </label>
              <label>
                <span className="sr-only">Sắp xếp video</span>
                <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)} className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 shadow-sm outline-none focus:border-primary sm:h-10 sm:font-semibold lg:shadow-none">
                  <option value="newest">Mới nhất</option>
                  <option value="views">Xem nhiều</option>
                  <option value="likes">Thích nhiều</option>
                  <option value="liked">Đã thích</option>
                  <option value="title">Tên A-Z</option>
                </select>
              </label>
            </div>
          </div>
        </section>

        <div className="sticky top-0 z-10 mb-4 flex min-w-0 items-center gap-2 rounded-lg border border-slate-200 bg-white/95 px-2.5 py-2.5 shadow-sm backdrop-blur sm:mb-5 sm:px-3 sm:py-3">
          <button type="button" onClick={() => scrollTabs(-1)} className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-700 ring-1 ring-slate-200 transition-colors hover:bg-slate-100 sm:flex" aria-label="Cuộn chủ đề sang trái">
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div ref={tabsRef} className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {availableTabs.map((category) => (
              <button type="button"
                key={category}
                onClick={() => setActiveTab(category)}
                aria-pressed={activeTab === category}
                className={`h-10 shrink-0 whitespace-nowrap rounded-md px-3 text-xs font-bold transition-colors sm:px-4 sm:text-sm ${
                  activeTab === category ? 'bg-primary text-white shadow-sm shadow-red-100' : 'bg-slate-50 text-slate-700 ring-1 ring-slate-100 hover:bg-slate-100'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => scrollTabs(1)} className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-md bg-slate-50 text-slate-700 ring-1 ring-slate-200 transition-colors hover:bg-slate-100 sm:flex" aria-label="Cuộn chủ đề sang phải">
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
          <>
            <MasonryGrid
              videos={displayVideos}
              likedIds={likedIds}
              onOpen={openVideo}
              onLike={toggleLike}
              onShare={shareVideo}
            />
            {hasMoreVideos && activeTab === 'Tất cả' && !query.trim() && (
              <div className="mt-2 flex justify-center pb-8">
                <button
                  type="button"
                  onClick={loadMoreVideos}
                  disabled={loadingMore}
                  className="h-11 rounded-md bg-primary px-5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-wait disabled:opacity-70"
                >
                  {loadingMore ? 'Đang tải...' : 'Xem thêm video'}
                </button>
              </div>
            )}
          </>
        )}

        <ReelsModal
          isOpen={isModalOpen}
          playlist={modalPlaylist}
          initialIndex={activeIndex}
          onClose={closeVideoModal}
          likedIds={likedIds}
          onToggleLike={toggleLike}
        />
      </div>
    </div>
  );
}
