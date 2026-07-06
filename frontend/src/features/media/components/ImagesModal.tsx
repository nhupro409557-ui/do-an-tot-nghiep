import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { Check, Heart, MessageCircle, Send, Share2, X, Play, Pause } from 'lucide-react';
import { Link } from 'react-router-dom';
import { publicApi } from '../../../services/publicApi';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { useAuth } from '../../../context/AuthContext';

interface Product {
  id: string;
  name: string;
  url?: string;
  price?: number;
  discountPrice?: number;
  favoriteCount?: number;
}

interface GalleryItem {
  id: string;
  url: string;
  productId?: string;
  productName?: string;
  category?: string;
  brand?: string;
  favoriteCount?: number;
  product?: Product;
  displayId?: string;
  variantColorName?: string;
  variantColorCode?: string;
  variantConfiguration?: string;
}

interface CommentItem {
  id: string;
  userName?: string;
  content?: string;
  parentId?: string | null;
  replyToUserName?: string | null;
  isRetracted?: boolean;
  isPending?: boolean;
  isFailed?: boolean;
  imageUrl?: string;
  replies?: CommentItem[];
}

interface ImagesModalProps {
  isOpen: boolean;
  playlist: GalleryItem[];
  initialIndex?: number;
  onClose: () => void;
}

function priceOf(product: any) {
  return Number(product?.discountPrice || product?.price || 0).toLocaleString('vi-VN');
}

function likeCountOf(item: any, index: number) {
  if (typeof item?.product?.favoriteCount === 'number') return item.product.favoriteCount;
  if (typeof item?.favoriteCount === 'number') return item.favoriteCount;
  const seed = String(item.id || item.productName || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return Math.floor(12 + (seed % 88));
}

export default function ImagesModal({ isOpen, playlist, initialIndex = 0, onClose }: ImagesModalProps) {
  if (!isOpen || playlist.length === 0) return null;
  const modalKey = `${initialIndex}-${playlist.map((item) => item.id).join('|')}`;
  return <ImagesModalContent key={modalKey} playlist={playlist} initialIndex={initialIndex} onClose={onClose} />;
}

function ImagesModalContent({ playlist, initialIndex = 0, onClose }: Omit<ImagesModalProps, 'isOpen'>) {
  const { user } = useAuth();
  const [showComments, setShowComments] = useState(false);
  const [copied, setCopied] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() => (
    typeof window !== 'undefined' && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  ));

  // Real database comments and local actions
  const [imageComments, setImageComments] = useState<CommentItem[]>([]);
  const [replyTarget, setReplyTarget] = useState<CommentItem | null>(null);
  const [expandedReplies, setExpandedReplies] = useState<Set<string>>(new Set());
  const [likedIds, setLikedIds] = useState<Set<string>>(new Set());

  // 360 Spin / 3D Carousel states
  const [isDragging, setIsDragging] = useState(false);
  const [rotationY, setRotationY] = useState(0);
  const [zoom, setZoom] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number | null>(null);
  const startXRef = useRef(0);
  const startRotationYRef = useRef(0);

  // Responsive Card Dimensions
  const [cardDim, setCardDim] = useState(() => {
    const width = typeof window !== 'undefined' ? window.innerWidth : 1024;
    if (width >= 1024) return { w: 360, h: 360 };
    if (width >= 640) return { w: 300, h: 300 };
    return { w: 230, h: 230 };
  });

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) setCardDim({ w: 360, h: 360 });
      else if (window.innerWidth >= 640) setCardDim({ w: 300, h: 300 });
      else setCardDim({ w: 230, h: 230 });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!query) return;
    const updateReducedMotion = () => setReducedMotion(query.matches);
    query.addEventListener?.('change', updateReducedMotion);
    return () => query.removeEventListener?.('change', updateReducedMotion);
  }, []);

  // INERTIA STATE REFS
  const lastXRef = useRef(0);
  const lastTimeRef = useRef(0);
  const velocityRef = useRef(0);

  // ESC key to close
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const isCarouselMode = playlist.length >= 3;
  const singleImageIndex = Math.min(Math.max(initialIndex, 0), Math.max(playlist.length - 1, 0));

  const displayPlaylist = useMemo(() => {
    if (!isCarouselMode) return [];
    if (playlist.length === 0) return [];
    return playlist.map((item, idx) => ({ ...item, displayId: `${item.id}-${idx}` }));
  }, [isCarouselMode, playlist]);

  const N = displayPlaylist.length;
  const radius = N <= 1 ? 0 : Math.round((cardDim.w / 2 + 60) / Math.tan(Math.PI / N));
  const initialRotationOffset = N <= 1 ? 0 : -initialIndex * (360 / N);
  const effectiveRotationY = rotationY + initialRotationOffset;
  const effectiveZoom = zoom ?? (isCarouselMode ? -radius : 0);

  const activeCardIndex = useMemo(() => {
    if (N <= 1) return 0;
    const anglePerCard = 360 / N;
    let idx = Math.round(-effectiveRotationY / anglePerCard) % N;
    if (idx < 0) idx += N;
    return idx;
  }, [effectiveRotationY, N]);

  const activeIdx = activeCardIndex;
  const currentItem = isCarouselMode ? displayPlaylist[activeIdx] || null : playlist[singleImageIndex] || null;

  useEffect(() => {
    if (!currentItem?.productId) return;
    publicApi.listProductImageComments(currentItem.productId)
      .then((data) => setImageComments(data || []))
      .catch(() => setImageComments([]));
  }, [currentItem?.productId]);

  const comments = useMemo(() => {
    return imageComments.filter((comment) => String(comment.content || '').trim() !== '');
  }, [imageComments]);

  const commentThreads = useMemo(() => {
    const roots = comments.filter((comment) => !comment.parentId);
    const replies = comments.filter((comment) => comment.parentId);
    return roots.map((root) => ({
      ...root,
      replies: replies.filter((reply) => reply.parentId === root.id),
    }));
  }, [comments]);

  const commentCount = comments.length;

  const isLiked = currentItem?.productId ? likedIds.has(currentItem.productId) : false;

  const handleToggleLike = useCallback((event: React.MouseEvent) => {
    event.stopPropagation();
    if (!user) return alert('Vui lòng đăng nhập để lưu sản phẩm yêu thích.');
    if (!currentItem?.productId) return;

    const productId = currentItem.productId;
    setLikedIds((prev) => {
      const next = new Set(prev);
      next.has(productId) ? next.delete(productId) : next.add(productId);
      return next;
    });

    publicApi.toggleFavorite(productId).catch(() => {
      setLikedIds((prev) => {
        const next = new Set(prev);
        next.has(productId) ? next.delete(productId) : next.add(productId);
        return next;
      });
    });
  }, [currentItem?.productId, user]);

  const baseLikes = useMemo(() => {
    if (!currentItem) return 0;
    return Number(likeCountOf(currentItem, activeIdx) || 0);
  }, [currentItem, activeIdx]);

  const displayLikes = isLiked ? baseLikes + 1 : baseLikes;

  useEffect(() => {
    if (!isCarouselMode || !isAutoPlaying || reducedMotion || isDragging || N <= 1) return;

    let lastTime = performance.now();
    const animate = (time: number) => {
      const delta = Math.min(50, time - lastTime);
      lastTime = time;
      setRotationY((prev) => prev - delta * 0.006);
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    };
  }, [isCarouselMode, isAutoPlaying, reducedMotion, isDragging, N]);

  useEffect(() => {
    if (!isCarouselMode) return;
    const el = containerRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      setZoom((prev) => {
        const next = (prev ?? effectiveZoom) - e.deltaY * 0.16;
        return Math.min(450, Math.max(-2200, next));
      });
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleWheel);
    };
  }, [effectiveZoom, isCarouselMode]);

  useEffect(() => {
    if (!currentItem?.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('view', currentItem.id);
    window.history.replaceState({}, '', url.toString());
  }, [currentItem?.id]);

  useEffect(() => {
    return () => {
      const url = new URL(window.location.href);
      url.searchParams.delete('view');
      window.history.replaceState({}, '', url.toString());
    };
  }, []);

  const handleShare = useCallback(async () => {
    if (!currentItem) return;
    const url = `${window.location.origin}/images?view=${encodeURIComponent(currentItem.id)}`;
    if (navigator.share) {
      await navigator.share({ title: currentItem.productName || 'Hình ảnh', url }).catch(() => undefined);
      return;
    }
    await navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }, [currentItem]);

  const handleStart = (clientX: number) => {
    if (!isCarouselMode) return;
    setIsDragging(true);
    startXRef.current = clientX;
    startRotationYRef.current = rotationY;
    setIsAutoPlaying(false);

    lastXRef.current = clientX;
    lastTimeRef.current = performance.now();
    velocityRef.current = 0;
  };

  const handleMove = (clientX: number) => {
    if (!isCarouselMode || !isDragging || N <= 1) return;
    const deltaX = clientX - startXRef.current;
    const speed = 0.18;
    setRotationY(startRotationYRef.current + deltaX * speed);

    const now = performance.now();
    const dt = now - lastTimeRef.current;
    if (dt > 1) {
      velocityRef.current = (clientX - lastXRef.current) / dt;
    }
    lastXRef.current = clientX;
    lastTimeRef.current = now;
  };

  const handleEnd = () => {
    if (!isCarouselMode || !isDragging) return;
    setIsDragging(false);

    const projectedDeltaX = velocityRef.current * 70;
    const projectedRotationY = rotationY + projectedDeltaX * 0.18;

    const anglePerCard = 360 / N;
    const targetRotation = Math.round(projectedRotationY / anglePerCard) * anglePerCard;
    setRotationY(targetRotation);
  };

  async function handleSubmitComment(event: React.FormEvent) {
    event.preventDefault();
    if (!user) return alert('Vui lòng đăng nhập để gửi bình luận.');
    const content = commentText.trim();
    if (!content || !currentItem?.productId) return;
    const parentId = replyTarget?.parentId || replyTarget?.id || null;
    const replyToUserName = replyTarget?.userName || null;
    const tempId = `local-${Date.now()}`;
    const optimisticComment: CommentItem = {
      id: tempId,
      userName: 'Bạn',
      content,
      parentId,
      replyToUserName,
      isPending: true,
    };
    setImageComments((prev) => [...prev, optimisticComment]);
    setCommentText('');
    setReplyTarget(null);
    try {
      const created = await publicApi.createProductImageComment(currentItem.productId, {
        body: content,
        imageUrl: currentItem.url,
        parentId,
        replyToUserName,
      });
      if (created?.id) {
        setImageComments((prev) =>
          prev.map((comment) => comment.id === tempId ? created : comment)
        );
      }
    } catch {
      setImageComments((prev) =>
        prev.map((comment) =>
          comment.id === tempId
            ? { ...comment, isPending: false, isFailed: true }
            : comment
        )
      );
    }
  }

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/95 px-3 py-4 backdrop-blur-md">
      <button type="button"
        onClick={onClose}
        className="absolute right-6 top-6 z-[60] rounded-full bg-zinc-900/60 border border-white/10 p-3 text-white transition-all duration-300 hover:bg-zinc-800/80 hover:scale-105 active:scale-95 shadow-lg backdrop-blur-md cursor-pointer"
        aria-label="Đóng"
      >
        <X className="h-5 w-5" />
      </button>

      {isCarouselMode && (
      <button
        type="button"
        onClick={() => setIsAutoPlaying(!isAutoPlaying)}
        className="absolute left-6 top-6 z-[60] flex items-center gap-2 rounded-full bg-zinc-900/60 border border-white/10 px-4 py-2.5 text-xs font-bold text-white shadow-lg backdrop-blur-md transition-all duration-300 hover:bg-zinc-800/80 hover:scale-105 active:scale-95 cursor-pointer"
      >
        {isAutoPlaying ? <Pause className="h-4 w-4 text-red-500 animate-pulse" /> : <Play className="h-4 w-4 text-green-400" />}
        <span className="text-white">{isAutoPlaying ? 'Tạm dừng 360' : 'Tự xoay 360'}</span>
      </button>
      )}

      <div className="relative h-[92vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-zinc-950 border border-white/5 shadow-2xl">
        <div
          className="relative h-full w-full touch-none select-none overflow-hidden cursor-grab active:cursor-grabbing"
          role="application"
          aria-label={currentItem?.productName || 'Ảnh sản phẩm'}
          onMouseDown={(e) => handleStart(e.clientX)}
          onMouseMove={(e) => handleMove(e.clientX)}
          onMouseUp={handleEnd}
          onMouseLeave={handleEnd}
          onTouchStart={(e) => handleStart(e.touches[0].clientX)}
          onTouchMove={(e) => handleMove(e.touches[0].clientX)}
          onTouchEnd={handleEnd}
        >
          {currentItem?.url && (
            <div
              className="absolute inset-0 bg-cover bg-center opacity-30 blur-3xl saturate-200 scale-110 pointer-events-none transition-all duration-700"
              style={{ backgroundImage: `url(${currentItem.url})` }}
            />
          )}

          <div className="absolute inset-0 bg-black/40 pointer-events-none" />

          <div
            ref={containerRef}
            className="absolute inset-0 flex items-center justify-center pb-24"
            style={{ perspective: '1200px' }}
          >
            <div
              className={`relative ${isCarouselMode ? '' : 'hidden'}`}
              style={{
                width: `${cardDim.w}px`,
                height: `${cardDim.h}px`,
                transformStyle: 'preserve-3d',
                transform: `translateZ(${effectiveZoom}px) rotateY(${effectiveRotationY}deg)`,
                transition: isDragging || isAutoPlaying || reducedMotion ? 'none' : 'transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1)',
              }}
            >
              {displayPlaylist.map((item, cardIndex) => {
                const cardAngle = cardIndex * (360 / N);
                let globalAngle = (effectiveRotationY + cardAngle) % 360;
                if (globalAngle < 0) globalAngle += 360;
                let diffFromCenter = globalAngle;
                if (diffFromCenter > 180) diffFromCenter = 360 - diffFromCenter;

                const isCulled = diffFromCenter > 135;

                if (isCulled) {
                  return (
                    <div
                      key={item.displayId || item.id}
                      className="absolute top-0 left-0"
                      style={{
                        width: `${cardDim.w}px`,
                        height: `${cardDim.h}px`,
                        transform: `rotateY(${cardAngle}deg) translateZ(${radius}px)`,
                        visibility: 'hidden',
                        pointerEvents: 'none'
                      }}
                    />
                  );
                }

                const blurDiff = Math.max(0, diffFromCenter - 80);
                const blurRatio = Math.min(1, blurDiff / 55);
                const blurAmount = blurRatio * 8;
                const opacAmount = 1 - (blurRatio * 0.8);

                return (
                <div
                  key={item.displayId || item.id}
                  className={`absolute top-0 left-0 flex flex-col items-center justify-center transition-all duration-300 ${
                    cardIndex === activeIdx
                      ? 'scale-100 z-30'
                      : 'scale-95 z-10'
                  }`}
                  style={{
                    width: `${cardDim.w}px`,
                    height: `${cardDim.h}px`,
                    transform: `rotateY(${cardAngle}deg) translateZ(${radius}px)`,
                    opacity: opacAmount,
                    filter: `blur(${blurAmount}px)`,
                    backfaceVisibility: 'hidden',
                  }}
                >
                  <div className="h-full w-full relative transition-transform duration-300 flex items-center justify-center">
                    <ImageWithFallback
                      src={item.url}
                      alt={item.productName || 'Hình ảnh'}
                      className="max-h-[94%] max-w-[94%] rounded-xl object-contain drop-shadow-[0_18px_35px_rgba(0,0,0,0.45)]"
                      loading="lazy"
                      draggable={false}
                    />
                  </div>
                </div>
                );
              })}
            </div>
            {!isCarouselMode && (
              <div className="relative flex h-[min(62vh,540px)] w-full max-w-3xl items-center justify-center px-4 sm:px-8">
                <div className="absolute inset-x-3 inset-y-0 rounded-[2rem] border border-white/10 bg-white/[0.04] shadow-2xl shadow-black/40 sm:inset-x-6" />
                <div className="absolute inset-x-6 bottom-6 h-px bg-white/10 sm:inset-x-12" />
                <ImageWithFallback
                  src={currentItem?.url || ''}
                  alt={currentItem?.productName || 'Hình ảnh sản phẩm'}
                  className="relative z-10 max-h-[94%] max-w-[94%] rounded-2xl object-contain drop-shadow-[0_28px_55px_rgba(0,0,0,0.55)]"
                  loading="eager"
                  draggable={false}
                />
              </div>
            )}
          </div>

          <div className="hidden">
            <div className="hidden rounded-full bg-zinc-950/80 border border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white/80 shadow-xl backdrop-blur-md">
              KÉO ĐỂ XOAY 3D • CUỘN ĐỂ PHÓNG TO
            </div>
            <div className="rounded-full bg-zinc-950/80 border border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white/80 shadow-xl backdrop-blur-md">
              {isCarouselMode ? 'Kéo để xoay 3D - cuộn để phóng to' : 'Chế độ xem ảnh sản phẩm'}
            </div>
          </div>

          <div className="pointer-events-none absolute inset-0 z-20 bg-gradient-to-t from-zinc-950/90 via-transparent to-transparent" />

          {/* Bottom Bar */}
          <div className="absolute inset-x-0 bottom-0 z-30 p-4 pointer-events-auto">
            <div className="mx-auto max-w-4xl flex flex-col sm:flex-row items-center sm:items-center justify-between gap-4 rounded-2xl border border-white/10 bg-zinc-950/70 p-4 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-col gap-2.5 min-w-0 flex-1 w-full text-left">
                <span className="text-[10px] font-extrabold uppercase tracking-widest text-red-500">
                  {currentItem?.category || currentItem?.brand || 'Thư viện nổi bật'}
                </span>
                <h3 className="line-clamp-1 text-base font-black text-white sm:text-lg">
                  {currentItem?.productName || 'Sản phẩm'}
                </h3>
                {(currentItem?.variantColorName || currentItem?.variantConfiguration) && (
                  <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-white/80">
                    {currentItem?.variantColorName && (
                      <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
                        {currentItem.variantColorCode && (
                          <span
                            className="h-3 w-3 rounded-full border border-white/60"
                            style={{ backgroundColor: currentItem.variantColorCode }}
                          />
                        )}
                        Màu: {currentItem.variantColorName}
                      </span>
                    )}
                    {currentItem?.variantConfiguration && (
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                        {currentItem.variantConfiguration}
                      </span>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-3 text-white mt-0.5">
                  <button
                    type="button"
                    onClick={handleToggleLike}
                    className={`group flex items-center gap-2 px-3 py-1.5 rounded-full border text-white transition-all duration-300 cursor-pointer ${
                      isLiked
                        ? 'bg-red-500/10 border-red-500/40 text-red-400'
                        : 'bg-white/5 border-white/10 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400'
                    }`}
                  >
                    <Heart className={`h-4 w-4 shrink-0 transition group-hover:scale-110 ${isLiked ? 'fill-red-500 text-red-500' : ''}`} />
                    <span className="text-xs font-bold">{displayLikes}</span>
                  </button>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setShowComments((value) => !value);
                    }}
                    className="group flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-white transition-all duration-300 hover:bg-blue-500/10 hover:border-blue-500/30 hover:text-blue-400 cursor-pointer"
                  >
                    <MessageCircle className="h-4 w-4 shrink-0 transition group-hover:scale-110" />
                    <span className="text-xs font-bold">{commentCount}</span>
                  </button>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleShare();
                    }}
                    className="group flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-white transition-all duration-300 hover:bg-green-500/10 hover:border-green-500/30 hover:text-green-400 cursor-pointer"
                  >
                    {copied ? <Check className="h-4 w-4 shrink-0 text-green-400" /> : <Share2 className="h-4 w-4 shrink-0 transition group-hover:scale-110" />}
                    <span className="text-xs font-bold">{copied ? 'Đã chép' : 'Chia sẻ'}</span>
                  </button>
                </div>
              </div>

              {currentItem?.product && (
                <Link
                  to={currentItem.product.url || `/product/${currentItem.product.id}`}
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950/60 p-2 shadow-lg backdrop-blur-md transition duration-300 hover:bg-zinc-900/80 hover:border-red-500/40 group/prod w-full sm:w-auto shrink-0"
                  onClick={(event) => event.stopPropagation()}
                >
                  <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded-lg bg-white p-0.5 shadow-inner">
                    <ImageWithFallback src={currentItem.url} alt="" className="h-full w-full object-contain" />
                  </div>
                  <div className="flex flex-col min-w-0 pr-2 text-left">
                    <span className="truncate text-xs font-bold text-white group-hover/prod:text-red-400 transition-colors max-w-[120px] sm:max-w-[160px]">
                      {currentItem.product.name}
                    </span>
                    <span className="text-[11px] font-black text-red-400 mt-0.5">
                      {priceOf(currentItem.product)}đ
                    </span>
                  </div>
                  <div className="shrink-0 rounded-full bg-red-600 px-3 py-1.5 text-[9px] font-black uppercase text-white shadow-md transition group-hover/prod:bg-red-500 ml-auto sm:ml-0">
                    Mua ngay ➔
                  </div>
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Comment Drawer Section */}
        <div
          className={`absolute bottom-0 right-0 top-0 z-50 w-full max-w-sm bg-zinc-950/95 border-l border-white/10 text-white shadow-2xl backdrop-blur transition-transform duration-300 ${
            showComments ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3.5">
              <h4 className="text-sm font-black uppercase tracking-wider text-zinc-300">Bình luận ({commentCount})</h4>
              <button type="button"
                onClick={() => setShowComments(false)}
                className="rounded-full p-2 text-white/70 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
                aria-label="Đóng bình luận"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-thin scrollbar-thumb-zinc-800">
              {commentThreads.length > 0 ? (
                <div className="space-y-4">
                  {commentThreads.map((comment: CommentItem) => (
                    <div key={comment.id} className="space-y-2">
                      <div className={`flex gap-3 items-start bg-white/5 border border-white/5 p-3 rounded-xl ${comment.isPending ? 'opacity-50' : ''}`}>
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white shadow-sm">
                          {(comment.isRetracted ? '!' : (comment.userName || 'K')[0]).toUpperCase()}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-black text-zinc-300">{comment.isRetracted ? 'Hệ thống' : comment.userName || 'Khách hàng'}</p>
                          <p className={`mt-1 text-xs leading-normal ${comment.isRetracted ? 'italic text-zinc-500' : 'text-zinc-400'}`}>{comment.content}</p>
                          {comment.isFailed && <p className="text-[10px] text-red-500 mt-1">Lỗi khi gửi</p>}
                          {!comment.isRetracted && !comment.isPending && (
                            <button type="button" onClick={() => setReplyTarget(comment)} className="mt-2 text-[11px] font-bold text-red-300 hover:text-red-200 cursor-pointer">
                              Trả lời
                            </button>
                          )}
                        </div>
                      </div>
                      {comment.replies && comment.replies.length > 0 && (
                        <div className="ml-8 space-y-2 border-l border-white/10 pl-3">
                          {(expandedReplies.has(comment.id) ? comment.replies : comment.replies.slice(0, 2)).map((reply: CommentItem) => (
                            <div key={reply.id} className={`rounded-xl bg-white/[0.03] px-3 py-2 ${reply.isPending ? 'opacity-50' : ''}`}>
                              <p className="text-xs font-black text-zinc-300">{reply.isRetracted ? 'Hệ thống' : reply.userName || 'Khách hàng'}</p>
                              <p className={`mt-1 text-xs leading-normal ${reply.isRetracted ? 'italic text-zinc-500' : 'text-zinc-400'}`}>
                                {reply.replyToUserName && !reply.isRetracted && <span className="font-bold text-red-300">@{reply.replyToUserName} </span>}
                                {reply.content}
                              </p>
                              {reply.isFailed && <p className="text-[10px] text-red-500 mt-1">Lỗi khi gửi</p>}
                              {!reply.isRetracted && !reply.isPending && (
                                <button type="button" onClick={() => setReplyTarget(reply)} className="mt-1 text-[11px] font-bold text-red-300 hover:text-red-200 cursor-pointer">
                                  Trả lời
                                </button>
                              )}
                            </div>
                          ))}
                          {comment.replies.length > 2 && (
                            <button
                               type="button"
                               onClick={() => setExpandedReplies((prev) => {
                                 const next = new Set(prev);
                                 if (next.has(comment.id)) next.delete(comment.id);
                                 else next.add(comment.id);
                                 return next;
                               })}
                               className="text-[11px] font-bold text-white/60 hover:text-white cursor-pointer"
                            >
                               {expandedReplies.has(comment.id) ? 'Thu gọn câu trả lời' : `Xem ${comment.replies.length - 2} câu trả lời`}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center text-sm text-white/50">Chưa có bình luận nào</div>
              )}
            </div>

            <form onSubmit={handleSubmitComment} className="border-t border-white/10 p-4 bg-zinc-950">
              {replyTarget && (
                <div className="mb-2 flex items-center justify-between rounded-xl bg-white/5 px-3 py-2 text-xs text-zinc-300">
                  <span>Đang trả lời {replyTarget.userName || 'khách hàng'}</span>
                  <button type="button" onClick={() => setReplyTarget(null)} className="font-bold text-red-300 hover:text-red-200 cursor-pointer">Hủy</button>
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  aria-label={replyTarget ? `Trả lời ${replyTarget.userName || 'khách hàng'}` : 'Viết bình luận ảnh'}
                  value={commentText}
                  onChange={(event) => setCommentText(event.target.value)}
                  placeholder={replyTarget ? `Trả lời ${replyTarget.userName || 'khách hàng'}...` : 'Viết bình luận...'}
                  className="h-11 flex-1 rounded-full border border-white/5 bg-white/5 px-4 text-xs text-white outline-none placeholder:text-zinc-500 focus:border-red-500/40 focus:ring-1 focus:ring-red-500/20 transition-all duration-300"
                />
                <button
                  type="submit"
                  disabled={!commentText.trim()}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-600 text-white transition hover:bg-red-500 disabled:opacity-40 cursor-pointer shadow-lg shadow-red-600/10 hover:shadow-red-600/20"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
