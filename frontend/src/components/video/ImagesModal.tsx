import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Mousewheel } from 'swiper/modules';
import { Check, Heart, MessageCircle, Send, Share2, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import 'swiper/css';

interface ImagesModalProps {
  isOpen: boolean;
  playlist: any[];
  initialIndex?: number;
  onClose: () => void;
}

function priceOf(product: any) {
  return Number(product?.discountPrice || product?.price || 0).toLocaleString('vi-VN');
}

function likeCountOf(item: any, index: number) {
  const seed = String(item.id || item.productName || index).split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return `${(1.2 + ((seed % 240) / 10)).toFixed(1)}K`;
}

export default function ImagesModal({ isOpen, playlist, initialIndex = 0, onClose }: ImagesModalProps) {
  const [showComments, setShowComments] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeIdx, setActiveIdx] = useState(initialIndex);
  const [commentText, setCommentText] = useState('');

  const currentItem = playlist[activeIdx] || null;
  const commentCount = 3 + ((activeIdx * 3) % 12);

  useEffect(() => {
    if (!isOpen) return;
    setShowComments(false);
    setCopied(false);
    setActiveIdx(initialIndex);
    setCommentText('');
  }, [isOpen, initialIndex]);

  useEffect(() => {
    if (!isOpen || playlist.length === 0) return;
    const item = playlist[activeIdx];
    if (!item?.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('view', item.id);
    window.history.replaceState({}, '', url.toString());
  }, [isOpen, activeIdx, playlist]);

  useEffect(() => {
    if (isOpen) return;
    const url = new URL(window.location.href);
    url.searchParams.delete('view');
    window.history.replaceState({}, '', url.toString());
  }, [isOpen]);

  const comments = useMemo(() => {
    if (!currentItem) return [];
    return [
      { userName: 'Minh Anh', content: 'Hình ảnh thực tế rất đẹp!' },
      { userName: 'Khách hàng', content: 'Sản phẩm này còn hàng không shop?' }
    ];
  }, [currentItem]);

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

  const handleSlideChange = useCallback((swiper: any) => {
    setActiveIdx(swiper.activeIndex);
    setShowComments(false);
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

      <div className="relative h-[92vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-black shadow-2xl transition-[width,height] duration-300">
        <Swiper
          direction="vertical"
          mousewheel
          initialSlide={initialIndex}
          modules={[Mousewheel]}
          className="h-full w-full"
          onSlideChange={handleSlideChange}
        >
          {playlist.map((item, index) => (
            <SwiperSlide key={item.id} className="relative h-full w-full bg-zinc-950">
              {/* Ambient Blurred Background for Letterboxing */}
              <div
                className="absolute inset-0 bg-cover bg-center opacity-40 blur-3xl saturate-150"
                style={{ backgroundImage: `url(${item.url})` }}
              />

              <img
                src={item.url}
                alt={item.productName}
                className="relative z-0 h-full w-full object-contain"
              />

              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-black/15" />

              <div className="absolute inset-x-0 bottom-0 p-4">
                <div className="flex items-end justify-between gap-4 rounded-2xl border border-white/15 bg-black/40 p-4 shadow-lg backdrop-blur-md">
                  {/* Left: Title & Actions */}
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <h3 className="line-clamp-2 text-base font-bold text-white drop-shadow-md sm:text-lg">
                      {item.productName || 'Sản phẩm'}
                    </h3>
                    <div className="flex items-center gap-4 text-white">
                      <button type="button" className="group flex items-center gap-1.5 transition hover:text-red-400">
                        <Heart className="h-5 w-5 transition group-hover:scale-110" />
                        <span className="text-sm font-semibold">{likeCountOf(item, index)}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setShowComments((value) => !value);
                        }}
                        className="group flex items-center gap-1.5 transition hover:text-blue-400"
                      >
                        <MessageCircle className="h-5 w-5 transition group-hover:scale-110" />
                        <span className="text-sm font-semibold">{3 + ((index * 3) % 12)}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleShare();
                        }}
                        className="group flex items-center gap-1.5 transition hover:text-green-400"
                      >
                        {copied ? <Check className="h-5 w-5 text-green-400" /> : <Share2 className="h-5 w-5 transition group-hover:scale-110" />}
                        <span className="text-sm font-semibold">{copied ? 'Copy' : 'Share'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Right: Product Pill Tag */}
                  {item.product && (
                    <Link
                      to={item.product.url || `/product/${item.product.id}`}
                      className="flex shrink-0 items-center gap-2 rounded-full border border-white/20 bg-white/10 p-1.5 pr-3 shadow-inner transition hover:bg-white/20"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white">
                        <img src={item.url} alt="" className="h-full w-full object-contain" />
                      </span>
                      <div className="flex flex-col">
                        <span className="max-w-[120px] truncate text-xs font-bold text-white sm:max-w-[160px]">{item.product.name}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] font-black text-red-400">{priceOf(item.product)}đ</span>
                          <span className="text-[9px] font-black uppercase text-white/80">Mua ngay ➔</span>
                        </div>
                      </div>
                    </Link>
                  )}
                </div>
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
      </div>
    </div>
  );
}
