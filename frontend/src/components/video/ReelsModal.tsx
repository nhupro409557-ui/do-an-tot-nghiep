import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Mousewheel } from 'swiper/modules';
import { Check, Heart, MessageCircle, Pause, Play, Send, Share2, Volume2, VolumeX, X, ShoppingBag } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiDb } from '../../services/apiDb';
import 'swiper/css';

interface ReelsModalProps {
  isOpen: boolean;
  playlist: any[];
  initialIndex?: number;
  onClose: () => void;
  likedIds: Set<string>;
  onToggleLike: (video: any) => void;
}

const VIDEO_MUTED_KEY = 'video_reels_muted';

function initialMutedPreference() {
  if (typeof window === 'undefined') return true;
  return localStorage.getItem(VIDEO_MUTED_KEY) !== '0';
}

function mediaPoster(video: any) {
  return video.thumbnailUrl || (youtubeEmbedUrl(video) ? video.youtubeThumbnailUrl : '') || video.cover || video.coverUrl || '';
}

function priceOf(product: any) {
  return Number(product?.discountPrice || product?.price || 0).toLocaleString('vi-VN');
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

function durationOf(video: any, measuredDuration?: number) {
  if (video.duration) return video.duration;
  return formatDuration(measuredDuration) || (youtubeEmbedUrl(video) ? 'YouTube' : '');
}

function likeCountOf(video: any, index: number) {
  if (typeof video.likeCount === 'number') return video.likeCount.toLocaleString('vi-VN');
  const seed = String(video.id || video.title || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return `${(1.2 + ((seed % 240) / 10)).toFixed(1)}K`;
}

function inferCategory(video: any) {
  return video.category || 'Reels';
}

function youtubeEmbedUrl(video: any) {
  const url = String(video?.embedUrl || video?.videoUrl || '');
  if (!url) return '';
  if (url.includes('youtube.com/embed/')) return url;
  if (url.includes('youtu.be/')) return `https://www.youtube.com/embed/${url.split('youtu.be/')[1].split(/[/?&]/)[0]}`;
  if (url.includes('youtube.com/shorts/')) return `https://www.youtube.com/embed/${url.split('youtube.com/shorts/')[1].split(/[/?&]/)[0]}`;
  if (url.includes('youtube.com/watch') && url.includes('v=')) return `https://www.youtube.com/embed/${url.split('v=')[1].split('&')[0]}`;
  return '';
}

function youtubePlayerUrl(video: any, active: boolean, muted: boolean) {
  const url = youtubeEmbedUrl(video);
  if (!url) return '';
  const [base, query = ''] = url.split('?');
  const params = new URLSearchParams(query);
  params.set('playsinline', '1');
  params.set('rel', '0');
  if (active) {
    params.set('autoplay', '1');
    params.set('mute', muted ? '1' : '0');
  } else {
    params.delete('autoplay');
    params.delete('mute');
  }
  return `${base}?${params.toString()}`;
}

export default function ReelsModal({ isOpen, playlist, initialIndex = 0, onClose, likedIds, onToggleLike }: ReelsModalProps) {
  if (!isOpen || playlist.length === 0) return null;
  const modalKey = `${initialIndex}-${playlist.map((item) => item.id).join('|')}`;
  return (
    <ReelsModalContent
      key={modalKey}
      playlist={playlist}
      initialIndex={initialIndex}
      onClose={onClose}
      likedIds={likedIds}
      onToggleLike={onToggleLike}
    />
  );
}

function ReelsModalContent({ playlist, initialIndex = 0, onClose, likedIds, onToggleLike }: Omit<ReelsModalProps, 'isOpen'>) {
  const [muted, setMuted] = useState(initialMutedPreference);
  const [paused, setPaused] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeIdx, setActiveIdx] = useState(initialIndex);
  const [commentText, setCommentText] = useState('');
  const [replyTarget, setReplyTarget] = useState<any | null>(null);
  const [progress, setProgress] = useState(0);
  const [videoSizes, setVideoSizes] = useState<Record<number, { width: number; height: number }>>({});
  const [videoDurations, setVideoDurations] = useState<Record<number, number>>({});
  const [localComments, setLocalComments] = useState<Record<string, any[]>>({});
  const [expandedReplies, setExpandedReplies] = useState<Set<string>>(new Set());
  const videoRefs = useRef<Map<number, HTMLVideoElement>>(new Map());

  const currentVideo = playlist[activeIdx] || null;
  const commentCount = (currentVideo?.commentCount || currentVideo?.comments?.length || 0) + (currentVideo?.id ? (localComments[currentVideo.id] || []).length : 0);
  const activeSize = videoSizes[activeIdx];
  const activeRatio = activeSize ? activeSize.width / activeSize.height : 9 / 16;
  const isPortraitVideo = activeRatio < 1;
  const isYoutube = Boolean(youtubeEmbedUrl(currentVideo));
  const frameClassName = isYoutube
    ? 'w-full max-w-6xl max-h-[86vh]'
    : isPortraitVideo
      ? 'h-[92vh] max-h-[92vh] w-auto max-w-[calc(100vw-1.5rem)]'
      : 'w-full max-w-5xl max-h-[92vh]';

  function toggleMuted() {
    setMuted((value) => {
      const next = !value;
      localStorage.setItem(VIDEO_MUTED_KEY, next ? '1' : '0');
      return next;
    });
  }

  useEffect(() => {
    if (!currentVideo?.id) return;
    let id = sessionStorage.getItem('video_device_id');
    if (!id) {
      id = crypto.randomUUID?.() || String(Date.now());
      sessionStorage.setItem('video_device_id', id);
    }
    const timer = window.setInterval(() => {
      const el = videoRefs.current.get(activeIdx);
      const visible = document.visibilityState === 'visible' && !paused;
      if (!visible) return;
      const positionSeconds = el?.currentTime || Number(sessionStorage.getItem(`video_pos_${currentVideo.id}`) || 0);
      apiDb.recordVideoView(currentVideo.id, { watchedSeconds: 10, positionSeconds, visible }, id).catch(() => undefined);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [activeIdx, currentVideo?.id, paused]);

  useEffect(() => {
    if (!currentVideo?.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('watch', currentVideo.id);
    window.history.replaceState({}, '', url.toString());
  }, [activeIdx, currentVideo?.id]);

  useEffect(() => {
    return () => {
      const url = new URL(window.location.href);
      url.searchParams.delete('watch');
      window.history.replaceState({}, '', url.toString());
    };
  }, []);

  const comments = useMemo(() => {
    if (!currentVideo || !Array.isArray(currentVideo.comments)) return [];
    return [...currentVideo.comments, ...(localComments[currentVideo.id] || [])].slice(0, 20);
  }, [currentVideo, localComments]);
  const commentThreads = useMemo(() => {
    const roots = comments.filter((comment: any) => !comment.parentId);
    const replies = comments.filter((comment: any) => comment.parentId);
    return roots.map((root: any) => ({
      ...root,
      replies: replies.filter((reply: any) => reply.parentId === root.id),
    }));
  }, [comments]);

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

  function rememberPosition(videoId: string, currentTime: number) {
    sessionStorage.setItem(`video_pos_${videoId}`, String(Math.floor(currentTime)));
  }

  function handleSubmitComment(event: React.FormEvent) {
    event.preventDefault();
    const content = commentText.trim();
    if (!content || !currentVideo?.id) return;
    const parentId = replyTarget?.parentId || replyTarget?.id || null;
    const replyToUserName = replyTarget?.userName || null;
    apiDb.createVideoComment(currentVideo.id, { body: content, parentId, replyToUserName }).catch(() => undefined);
    setLocalComments((items) => ({
      ...items,
      [currentVideo.id]: [
        ...(items[currentVideo.id] || []),
        { id: `local-${Date.now()}`, userName: 'Bạn', content, parentId, replyToUserName },
      ],
    }));
    setCommentText('');
    setReplyTarget(null);
  }

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/95 px-3 py-4 backdrop-blur-sm">
      <button
        onClick={toggleMuted}
        className="absolute left-4 top-4 z-[60] flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-black/40 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-105 active:scale-95"
        title={muted ? 'Bật âm thanh' : 'Tắt âm thanh'}
      >
        {muted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
      </button>

      <button
        onClick={onClose}
        className="absolute right-4 top-4 z-[60] flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-black/40 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-105 hover:rotate-90 active:scale-95"
        aria-label="Đóng"
      >
        <X className="h-5 w-5" />
      </button>

      <div
        className={`relative overflow-hidden rounded-2xl bg-black shadow-2xl transition-[width,height] duration-300 border border-white/10 ${frameClassName}`}
        style={{ aspectRatio: isYoutube ? '16 / 9' : `${activeSize?.width || 9} / ${activeSize?.height || 16}` }}
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
            <SwiperSlide key={video.id} className="relative h-full w-full bg-zinc-950 overflow-hidden">
              {mediaPoster(video) && (
                <div
                  className="absolute inset-0 bg-cover bg-center opacity-30 blur-3xl saturate-150 scale-110 pointer-events-none"
                  style={{ backgroundImage: `url(${mediaPoster(video)})` }}
                />
              )}

              {youtubeEmbedUrl(video) ? (
                <>
                  <iframe
                    src={youtubePlayerUrl(video, index === activeIdx, muted)}
                    title={video.title || 'Video'}
                    className="pointer-events-none relative z-0 h-full w-full bg-black"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  />
                </>
              ) : video.videoUrl ? (
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
                    const saved = Number(sessionStorage.getItem(`video_pos_${video.id}`) || 0);
                    if (saved > 0 && saved < el.duration - 3) el.currentTime = saved;
                    if (!el.videoWidth || !el.videoHeight) return;
                    setVideoSizes((sizes) => ({
                      ...sizes,
                      [index]: { width: el.videoWidth, height: el.videoHeight },
                    }));
                    setVideoDurations((durations) => ({
                      ...durations,
                      [index]: el.duration,
                    }));
                  }}
                  onTimeUpdate={(e) => {
                    if (index === activeIdx) {
                      const el = e.currentTarget;
                      rememberPosition(video.id, el.currentTime);
                      if (el.duration) setProgress((el.currentTime / el.duration) * 100);
                    }
                  }}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-zinc-900 p-6 text-center text-sm font-semibold text-white/70">
                  Video này chưa có file phát.
                </div>
              )}

              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/90 via-black/40 to-transparent z-10" />
              <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-black/40 to-transparent z-10" />

              {paused && index === activeIdx && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center z-20">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-black/60 border border-white/10 shadow-xl backdrop-blur-sm transition-transform duration-300 scale-100 animate-pulse">
                    <Play fill="white" className="ml-1 h-7 w-7 text-white" />
                  </div>
                </div>
              )}

              <div className="absolute right-4 bottom-28 z-30 flex flex-col items-center gap-4">
                <div className="flex flex-col items-center">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onToggleLike(video);
                    }}
                    className={`group flex h-12 w-12 items-center justify-center rounded-full bg-black/40 border border-white/10 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-110 active:scale-95 ${likedIds.has(video.id) ? 'border-red-500/30 bg-red-950/20' : ''}`}
                    aria-pressed={likedIds.has(video.id)}
                  >
                    <Heart className={`h-5 w-5 transition duration-200 group-hover:text-red-500 group-hover:scale-110 ${likedIds.has(video.id) ? 'fill-red-500 text-red-500 scale-110' : 'text-white'}`} />
                  </button>
                  <span className="mt-1 text-[11px] font-bold text-white drop-shadow-md select-none">{likeCountOf(video, index)}</span>
                </div>

                <div className="flex flex-col items-center">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setShowComments((value) => !value);
                    }}
                    className="group flex h-12 w-12 items-center justify-center rounded-full bg-black/40 border border-white/10 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-110 active:scale-95"
                  >
                    <MessageCircle className="h-5 w-5 transition duration-200 group-hover:text-blue-400 group-hover:scale-110 text-white" />
                  </button>
                  <span className="mt-1 text-[11px] font-bold text-white drop-shadow-md select-none">{commentCount}</span>
                </div>

                <div className="flex flex-col items-center">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleShare();
                    }}
                    className="group flex h-12 w-12 items-center justify-center rounded-full bg-black/40 border border-white/10 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-110 active:scale-95"
                  >
                    {copied ? <Check className="h-5 w-5 text-green-400" /> : <Share2 className="h-5 w-5 transition duration-200 group-hover:text-green-400 group-hover:scale-110 text-white" />}
                  </button>
                  <span className="mt-1 text-[11px] font-bold text-white drop-shadow-md select-none">{copied ? 'Copied' : 'Chia sẻ'}</span>
                </div>

                <div className="flex flex-col items-center">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      togglePlay();
                    }}
                    className="group flex h-12 w-12 items-center justify-center rounded-full bg-black/40 border border-white/10 text-white shadow-lg backdrop-blur-md transition duration-300 hover:bg-black/60 hover:scale-110 active:scale-95"
                    aria-label={paused ? 'Phát video' : 'Tạm dừng video'}
                  >
                    {paused ? <Play className="h-5 w-5 fill-current" /> : <Pause className="h-5 w-5 fill-current" />}
                  </button>
                  <span className="mt-1 text-[11px] font-bold text-white drop-shadow-md select-none">{paused ? 'Phát' : 'Tạm dừng'}</span>
                </div>
              </div>

              <div className={`absolute inset-x-0 bottom-0 z-20 ${isPortraitVideo ? 'p-4' : 'p-6'} bg-gradient-to-t from-black/85 via-black/45 to-transparent pt-20 pointer-events-none`}>
                <div className="flex flex-col gap-2.5 max-w-[85%] pointer-events-auto">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-red-600/90 border border-red-500/30 px-3 py-1 text-[11px] font-black uppercase tracking-wider text-white shadow-sm shadow-red-900/20 backdrop-blur-sm">
                      {inferCategory(video)}
                    </span>
                    <span className="rounded-full bg-white/10 border border-white/5 px-2.5 py-1 text-[11px] font-medium text-white/95 backdrop-blur-sm">
                      {durationOf(video, videoDurations[index])}
                    </span>
                  </div>

                  <h3 className={`font-bold text-white tracking-wide leading-snug drop-shadow-lg ${
                    isPortraitVideo ? 'line-clamp-2 text-base' : 'line-clamp-2 text-lg sm:text-xl'
                  }`}>
                    {video.title || 'Video sản phẩm'}
                  </h3>

                  {video.product && (
                    <Link
                      to={video.product.url || `/product/${video.product.id}`}
                      className="mt-1 flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950/60 p-2 shadow-lg backdrop-blur-md transition duration-300 hover:bg-zinc-950/80 hover:border-red-500/40 w-full group/prod max-w-md"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="relative h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-white p-0.5">
                        {(video.product.imageUrl || video.product.image) ? (
                          <img src={video.product.imageUrl || video.product.image} alt="" className="h-full w-full object-contain" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center bg-slate-100 text-[10px] font-bold text-slate-400">
                            <ShoppingBag className="h-4 w-4" />
                          </div>
                        )}
                      </div>
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate text-xs font-bold text-white group-hover/prod:text-red-400 transition-colors">
                          {video.product.name}
                        </span>
                        <div className="flex items-baseline gap-2 mt-0.5">
                          <span className="text-[11px] font-black text-red-400">{priceOf(video.product)}đ</span>
                          {video.product.price && Number(video.product.price) > Number(video.product.discountPrice || 0) && (
                            <span className="text-[9px] font-medium text-white/40 line-through">
                              {Number(video.product.price).toLocaleString('vi-VN')}đ
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 rounded-full bg-red-600 px-3 py-1.5 text-[10px] font-black uppercase text-white shadow-md transition group-hover/prod:bg-red-500">
                        Mua ngay ➔
                      </div>
                    </Link>
                  )}
                </div>
              </div>

              <div className="absolute inset-x-0 bottom-0 h-1 bg-white/10 z-30">
                <div
                  className="h-full bg-gradient-to-r from-red-500 via-rose-500 to-amber-500 transition-all duration-75 ease-linear shadow-[0_0_8px_rgba(239,68,68,0.8)]"
                  style={{ width: `${index === activeIdx ? progress : 0}%` }}
                />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>

        <div
          className={`absolute bottom-0 right-0 top-0 z-50 w-full max-w-sm bg-zinc-950/90 text-white shadow-2xl backdrop-blur-2xl border-l border-white/10 transition-transform duration-300 ${
            showComments ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 bg-zinc-950/40">
              <h4 className="text-sm font-bold tracking-wide">Bình luận ({commentCount})</h4>
              <button onClick={() => setShowComments(false)} className="rounded-full p-2 text-white/70 transition hover:bg-white/10 hover:text-white" aria-label="Đóng bình luận">
                <X className="h-4.5 w-4.5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 [scrollbar-width:thin] scrollbar-color-zinc">
              {commentThreads.length > 0 ? (
                <div className="space-y-4">
                  {commentThreads.map((comment: any, commentIndex: number) => (
                    <div key={comment.id || commentIndex} className="flex gap-3 bg-white/5 hover:bg-white/10 p-3 rounded-xl transition duration-200 border border-white/5">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-red-500 to-rose-600 text-xs font-black shadow-inner">
                        {(comment.userName || 'K')[0].toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold text-white">{comment.userName || 'Khách hàng'}</p>
                        <p className={`mt-1 text-sm leading-relaxed ${comment.isRetracted ? 'italic text-white/45' : 'text-white/80'}`}>
                          {comment.isRetracted ? 'Bình luận này đã bị thu hồi' : comment.content}
                        </p>
                        {!comment.isRetracted && (
                          <button
                            type="button"
                            onClick={() => setReplyTarget(comment)}
                            className="mt-1 text-xs font-bold text-red-400 hover:text-red-300 transition-colors"
                          >
                            Trả lời
                          </button>
                        )}

                        {comment.replies?.length > 0 && (
                          <div className="mt-3 space-y-3 border-l border-white/10 pl-3">
                            {comment.replies.length > 2 && !expandedReplies.has(comment.id) && (
                              <button
                                type="button"
                                onClick={() => setExpandedReplies((items) => new Set(items).add(comment.id))}
                                className="text-xs font-bold text-white/60 hover:text-white"
                              >
                                Xem {comment.replies.length} câu trả lời
                              </button>
                            )}
                            {(expandedReplies.has(comment.id) ? comment.replies : comment.replies.slice(0, 2)).map((reply: any) => (
                              <div key={reply.id} className="mt-2 bg-white/5 p-2 rounded-lg border border-white/5">
                                <p className="text-xs font-bold text-white/90">
                                  {reply.userName || 'Khách hàng'}{' '}
                                  {reply.replyToUserName && (
                                    <span className="font-semibold text-red-400">@{reply.replyToUserName}</span>
                                  )}
                                </p>
                                <p className={`mt-1 text-xs leading-relaxed ${reply.isRetracted ? 'italic text-white/40' : 'text-white/80'}`}>
                                  {reply.isRetracted ? 'Bình luận này đã bị thu hồi' : reply.content}
                                </p>
                                {!reply.isRetracted && (
                                  <button
                                    type="button"
                                    onClick={() => setReplyTarget(reply)}
                                    className="mt-1 text-[10px] font-bold text-red-400 hover:text-red-300 transition-colors"
                                  >
                                    Trả lời
                                  </button>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex h-32 items-center justify-center text-sm text-white/50">Chưa có bình luận nào</div>
              )}
            </div>

            <form onSubmit={handleSubmitComment} className="flex flex-col gap-2 border-t border-white/10 p-4 bg-zinc-950/40">
              {replyTarget && (
                <div className="flex items-center justify-between rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-1.5 text-xs text-red-400">
                  <span>Đang trả lời <strong>@{replyTarget.userName}</strong></span>
                  <button type="button" onClick={() => setReplyTarget(null)} className="font-bold text-white/60 hover:text-white ml-2">
                    Hủy
                  </button>
                </div>
              )}
              <div className="flex items-center gap-2">
                <input
                  value={commentText}
                  onChange={(event) => setCommentText(event.target.value)}
                  placeholder={replyTarget ? `Trả lời @${replyTarget.userName}...` : "Viết bình luận..."}
                  className="h-11 flex-1 rounded-full border border-white/10 bg-white/5 px-4 text-sm text-white outline-none placeholder:text-white/40 focus:border-red-500/50 focus:bg-white/10 transition-all duration-300"
                />
                <button
                  type="submit"
                  disabled={!commentText.trim()}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-600 text-white transition duration-300 hover:bg-red-500 active:scale-95 disabled:opacity-40 disabled:pointer-events-none shadow-md shadow-red-600/20"
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
