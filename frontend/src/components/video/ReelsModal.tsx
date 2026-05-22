import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Mousewheel } from 'swiper/modules';
import { Check, Heart, MessageCircle, Pause, Play, Send, Share2, Volume2, VolumeX, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import 'swiper/css';

interface ReelsModalProps {
  isOpen: boolean;
  playlist: any[];
  initialIndex?: number;
  onClose: () => void;
}

function mediaPoster(video: any) {
  return video.thumbnailUrl || video.cover || video.coverUrl || '';
}

function priceOf(product: any) {
  return Number(product?.discountPrice || product?.price || 0).toLocaleString('vi-VN');
}

function durationOf(video: any, index: number) {
  if (video.duration) return video.duration;
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const seconds = 14 + (seed % 48);
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function likeCountOf(video: any, index: number) {
  if (typeof video.likeCount === 'number') return video.likeCount.toLocaleString('vi-VN');
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return `${(1.2 + ((seed % 240) / 10)).toFixed(1)}K`;
}

export default function ReelsModal({ isOpen, playlist, initialIndex = 0, onClose }: ReelsModalProps) {
  const [muted, setMuted] = useState(false);
  const [paused, setPaused] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeIdx, setActiveIdx] = useState(initialIndex);
  const [commentText, setCommentText] = useState('');
  const [progress, setProgress] = useState(0);
  const [videoSizes, setVideoSizes] = useState<Record<number, { width: number; height: number }>>({});
  const videoRefs = useRef<Map<number, HTMLVideoElement>>(new Map());

  const currentVideo = playlist[activeIdx] || null;
  const commentCount = currentVideo?.commentCount || currentVideo?.comments?.length || 0;
  const activeSize = videoSizes[activeIdx];
  const activeRatio = activeSize ? activeSize.width / activeSize.height : 9 / 16;
  const isPortraitVideo = activeRatio < 1;
  const frameClassName = isPortraitVideo
    ? 'h-[92vh] max-h-[92vh] w-auto max-w-[calc(100vw-1.5rem)]'
    : 'w-full max-w-5xl max-h-[92vh]';

  useEffect(() => {
    if (!isOpen) return;
    setPaused(false);
    setShowComments(false);
    setCopied(false);
    setActiveIdx(initialIndex);
    setCommentText('');
    setProgress(0);
  }, [isOpen, initialIndex]);

  useEffect(() => {
    if (!isOpen || playlist.length === 0) return;
    const video = playlist[activeIdx];
    if (!video?.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('watch', video.id);
    window.history.replaceState({}, '', url.toString());
  }, [isOpen, activeIdx, playlist]);

  useEffect(() => {
    if (isOpen) return;
    const url = new URL(window.location.href);
    url.searchParams.delete('watch');
    window.history.replaceState({}, '', url.toString());
  }, [isOpen]);

  const comments = useMemo(() => {
    if (!currentVideo || !Array.isArray(currentVideo.comments)) return [];
    return currentVideo.comments.slice(0, 8);
  }, [currentVideo]);

  const togglePlay = useCallback(() => {
    const el = videoRefs.current.get(activeIdx);
    if (!el) return;
    if (el.paused) {
      el.play().catch(() => undefined);
      setPaused(false);
    } else {
      el.pause();
      setPaused(true);
    }
  }, [activeIdx]);

  const handleShare = useCallback(async () => {
    if (!currentVideo) return;
    const url = `${window.location.origin}/video?watch=${encodeURIComponent(currentVideo.id)}`;
    if (navigator.share) {
      await navigator.share({ title: currentVideo.title || 'Video', url }).catch(() => undefined);
      return;
    }
    await navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }, [currentVideo]);

  const handleSlideChange = useCallback((swiper: any) => {
    videoRefs.current.forEach((el) => {
      el.pause();
      el.currentTime = 0;
    });
    setActiveIdx(swiper.activeIndex);
    setPaused(false);
    setShowComments(false);
    setProgress(0);
    const next = videoRefs.current.get(swiper.activeIndex);
    next?.play().catch(() => undefined);
  }, []);

  function handleSubmitComment(event: React.FormEvent) {
    event.preventDefault();
    if (!commentText.trim()) return;
    setCommentText('');
  }

  if (!isOpen || playlist.length === 0) return null;

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/95 px-3 py-4 backdrop-blur-sm">
      <button
        onClick={onClose}
        className="absolute right-4 top-4 z-[60] rounded-full bg-white/10 p-3 text-white transition hover:bg-white/20"
        aria-label="Đóng"
      >
        <X className="h-6 w-6" />
      </button>

      <button
        onClick={() => setMuted((value) => !value)}
        className="absolute left-4 top-4 z-[60] rounded-full bg-white/10 p-3 text-white transition hover:bg-white/20"
        title={muted ? 'Bật âm thanh' : 'Tắt âm thanh'}
      >
        {muted ? <VolumeX className="h-6 w-6" /> : <Volume2 className="h-6 w-6" />}
      </button>

      <div
        className={`relative overflow-hidden rounded-2xl bg-black shadow-2xl transition-[width,height] duration-300 ${frameClassName}`}
        style={{ aspectRatio: `${activeSize?.width || 9} / ${activeSize?.height || 16}` }}
      >
        <Swiper
          direction="vertical"
          mousewheel
          initialSlide={initialIndex}
          modules={[Mousewheel]}
          className="h-full w-full"
          onSlideChange={handleSlideChange}
        >
          {playlist.map((video, index) => (
            <SwiperSlide key={video.id} className="relative h-full w-full bg-zinc-950">
              {/* Ambient Blurred Background for Letterboxing */}
              {mediaPoster(video) && (
                <div
                  className="absolute inset-0 bg-cover bg-center opacity-40 blur-3xl saturate-150"
                  style={{ backgroundImage: `url(${mediaPoster(video)})` }}
                />
              )}

              {video.videoUrl ? (
                <video
                  ref={(el) => {
                    if (el) videoRefs.current.set(index, el);
                  }}
                  src={video.videoUrl}
                  poster={mediaPoster(video)}
                  autoPlay={index === initialIndex}
                  loop
                  muted={muted}
                  playsInline
                  className="relative z-0 h-full w-full cursor-pointer object-contain"
                  onClick={togglePlay}
                  onLoadedMetadata={(event) => {
                    const el = event.currentTarget;
                    if (!el.videoWidth || !el.videoHeight) return;
                    setVideoSizes((sizes) => ({
                      ...sizes,
                      [index]: { width: el.videoWidth, height: el.videoHeight },
                    }));
                  }}
                  onTimeUpdate={(e) => {
                    if (index === activeIdx) {
                      const el = e.currentTarget;
                      if (el.duration) setProgress((el.currentTime / el.duration) * 100);
                    }
                  }}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-zinc-900 p-6 text-center text-sm font-semibold text-white/70">
                  Video này chưa có file phát.
                </div>
              )}

              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-black/15" />

              <span className="absolute right-5 top-5 rounded-lg bg-black/45 px-3 py-1.5 text-sm font-semibold text-white shadow-sm backdrop-blur-md">
                {durationOf(video, index)}
              </span>

              {paused && index === activeIdx && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-black/50 backdrop-blur-sm">
                    <Play fill="white" className="ml-1 h-7 w-7 text-white" />
                  </div>
                </div>
              )}

              <div className={`absolute inset-x-0 bottom-0 ${isPortraitVideo ? 'p-3' : 'p-4'}`}>
                <div className={`rounded-2xl border border-white/15 bg-black/40 shadow-lg backdrop-blur-md ${
                  isPortraitVideo ? 'flex flex-col gap-3 p-3' : 'flex items-end justify-between gap-4 p-4'
                }`}>
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <h3 className={`font-bold text-white drop-shadow-md ${
                      isPortraitVideo ? 'line-clamp-2 text-base leading-snug' : 'line-clamp-2 text-base sm:text-lg'
                    }`}>
                      {video.title || 'Video sản phẩm'}
                    </h3>
                    <div className={`flex items-center text-white ${isPortraitVideo ? 'justify-between gap-2' : 'gap-4'}`}>
                      <button type="button" className="group flex min-w-0 items-center gap-1.5 transition hover:text-red-400">
                        <Heart className="h-5 w-5 transition group-hover:scale-110" />
                        <span className="text-sm font-semibold">{likeCountOf(video, index)}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setShowComments((value) => !value);
                        }}
                        className="group flex min-w-0 items-center gap-1.5 transition hover:text-blue-400"
                      >
                        <MessageCircle className="h-5 w-5 transition group-hover:scale-110" />
                        <span className="text-sm font-semibold">{commentCount}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleShare();
                        }}
                        className="group flex min-w-0 items-center gap-1.5 transition hover:text-green-400"
                      >
                        {copied ? <Check className="h-5 w-5 text-green-400" /> : <Share2 className="h-5 w-5 transition group-hover:scale-110" />}
                        <span className="text-sm font-semibold">{copied ? 'Copy' : 'Chia sẻ'}</span>
                      </button>
                    </div>
                  </div>

                  {video.product && (
                    <Link
                      to={video.product.url || `/product/${video.product.id}`}
                      className={`flex min-w-0 shrink-0 items-center gap-2 border border-white/20 bg-white/10 p-1.5 shadow-inner transition hover:bg-white/20 ${
                        isPortraitVideo ? 'w-full rounded-xl pr-2' : 'rounded-full pr-3'
                      }`}
                      onClick={(event) => event.stopPropagation()}
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white">
                        {(video.product.imageUrl || video.product.image) ? (
                          <img src={video.product.imageUrl || video.product.image} alt="" className="h-full w-full object-contain" />
                        ) : (
                          <span className="text-[10px] font-bold text-slate-400">SP</span>
                        )}
                      </span>
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className={`${isPortraitVideo ? 'max-w-full' : 'max-w-[120px] sm:max-w-[160px]'} truncate text-xs font-bold text-white`}>
                          {video.product.name}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] font-black text-red-400">{priceOf(video.product)}đ</span>
                          <span className="text-[9px] font-black uppercase text-white/80">Mua ngay</span>
                        </div>
                      </div>
                    </Link>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="absolute inset-x-0 bottom-0 h-[3px] bg-white/20">
                <div
                  className="h-full bg-white transition-all duration-75 ease-linear"
                  style={{ width: `${index === activeIdx ? progress : 0}%` }}
                />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>

        <div
          className={`absolute bottom-0 right-0 top-0 z-50 w-full max-w-sm bg-zinc-950/95 text-white shadow-2xl backdrop-blur transition-transform duration-300 ${
            showComments ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <h4 className="text-sm font-bold">Bình luận ({commentCount})</h4>
              <button onClick={() => setShowComments(false)} className="rounded-full p-2 text-white/70 transition hover:bg-white/10 hover:text-white" aria-label="Đóng bình luận">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              {comments.length > 0 ? (
                <div className="space-y-4">
                  {comments.map((comment: any, commentIndex: number) => (
                    <div key={comment.id || commentIndex} className="flex gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold">
                        {(comment.userName || 'K')[0].toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold">{comment.userName || 'Khách hàng'}</p>
                        <p className="mt-1 text-sm leading-5 text-white/75">{comment.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center text-sm text-white/50">Chưa có bình luận nào</div>
              )}
            </div>

            <form onSubmit={handleSubmitComment} className="flex items-center gap-2 border-t border-white/10 p-4">
              <input
                value={commentText}
                onChange={(event) => setCommentText(event.target.value)}
                placeholder="Viết bình luận..."
                className="h-10 flex-1 rounded-full border border-white/10 bg-white/5 px-4 text-sm text-white outline-none placeholder:text-white/40 focus:border-white/30"
              />
              <button type="submit" disabled={!commentText.trim()} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white transition hover:bg-red-700 disabled:opacity-40">
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>

        <button
          onClick={togglePlay}
          className="absolute left-5 top-5 z-40 rounded-full bg-white/10 p-3 text-white transition hover:bg-white/20"
          aria-label={paused ? 'Phát video' : 'Tạm dừng video'}
        >
          {paused ? <Play className="h-5 w-5 fill-current" /> : <Pause className="h-5 w-5 fill-current" />}
        </button>
      </div>
    </div>
  );
}
