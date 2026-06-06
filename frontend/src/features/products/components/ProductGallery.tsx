import React, { useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { FreeMode, Pagination, Thumbs } from 'swiper/modules';
import { ChevronLeft, ChevronRight, PlayCircle } from 'lucide-react';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { youtubeEmbedUrl, youtubeThumbnailUrl, type ProductMediaItem } from '../utils/ProductDetailUtils';

import 'swiper/css';
import 'swiper/css/free-mode';
import 'swiper/css/pagination';
import 'swiper/css/thumbs';

interface ProductGalleryProps {
  product: any;
  mediaItems: ProductMediaItem[];
  selectedMediaIndex: number;
  setSelectedMediaIndex: (index: number) => void;
  setSelectedImage: (url: string | null) => void;
  discount: number;
  fallbackImage: string;
  openMediaViewer: (index: number) => void;
}

export function ProductGallery({
  product,
  mediaItems,
  selectedMediaIndex,
  setSelectedMediaIndex,
  setSelectedImage,
  discount,
  fallbackImage,
  openMediaViewer,
}: ProductGalleryProps) {
  const [mainSwiper, setMainSwiper] = useState<SwiperType | null>(null);
  const [thumbsSwiper, setThumbsSwiper] = useState<SwiperType | null>(null);

  const selectMedia = (index: number) => {
    if (!mediaItems.length) return;
    const boundedIndex = (index + mediaItems.length) % mediaItems.length;
    const item = mediaItems[boundedIndex];
    setSelectedMediaIndex(boundedIndex);
    if (item.type !== 'video') setSelectedImage(item.url);
    mainSwiper?.slideTo(boundedIndex);
    thumbsSwiper?.slideTo(Math.max(0, boundedIndex - 2));
  };

  return (
    <div className="w-full space-y-3">
      <div className="group/main-media relative overflow-hidden rounded-2xl bg-white w-full border border-gray-200">
        {discount > 0 && (
          <span className="absolute left-3 top-3 z-20 rounded-lg bg-primary px-2 py-1 text-xs font-bold text-white">
            Giảm {discount}%
          </span>
        )}

        {mediaItems.length > 1 && (
          <>
            <button
              onClick={() => selectMedia(selectedMediaIndex - 1)}
              className="absolute left-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100 cursor-pointer"
              aria-label="Ảnh trước"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              onClick={() => selectMedia(selectedMediaIndex + 1)}
              className="absolute right-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100 cursor-pointer"
              aria-label="Ảnh sau"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </>
        )}

        <Swiper
          modules={[Pagination, Thumbs]}
          onSwiper={setMainSwiper}
          onSlideChange={(swiper) => {
            const item = mediaItems[swiper.activeIndex];
            if (!item) return;
            setSelectedMediaIndex(swiper.activeIndex);
            if (item.type !== 'video') setSelectedImage(item.url);
            thumbsSwiper?.slideTo(Math.max(0, swiper.activeIndex - 2));
          }}
          thumbs={{ swiper: thumbsSwiper && !thumbsSwiper.destroyed ? thumbsSwiper : null }}
          pagination={{ clickable: true }}
          className="product-main-swiper"
        >
          {mediaItems.map((item, index) => (
            <SwiperSlide key={item.key}>
              <div
                className="relative flex aspect-square cursor-pointer items-center justify-center overflow-hidden bg-white p-4"
                onClick={() => openMediaViewer(index)}
                onMouseEnter={() => {
                  const next = mediaItems[index + 1];
                  if (next?.type !== 'video' && next?.url) {
                    const image = new Image();
                    image.src = next.url;
                  }
                }}
              >
                {item.type === 'video' ? (
                  youtubeEmbedUrl(item.url) ? (
                    <iframe
                      src={youtubeEmbedUrl(item.url)}
                      title={item.label}
                      className="aspect-video w-full max-w-full rounded-xl bg-black"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                      onClick={(event) => event.stopPropagation()}
                    />
                  ) : (
                    <video
                      src={item.url}
                      poster={item.poster}
                      controls
                      preload={index === 0 ? 'metadata' : 'none'}
                      className="w-[90%] h-[90%] max-w-full max-h-full object-contain"
                      onClick={(event) => event.stopPropagation()}
                    />
                  )
                ) : (
                  <ImageWithFallback
                    src={item.url}
                    fallbackSrc={fallbackImage}
                    alt={product.name}
                    loading={index === 0 ? 'eager' : 'lazy'}
                    decoding="async"
                    className="w-[90%] h-[90%] max-w-full max-h-full object-contain transition-transform duration-300 hover:scale-105"
                  />
                )}
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>

      {mediaItems.length > 1 && (
        <div className="group relative w-full py-1.5 flex justify-center">
          <button
            onClick={() => selectMedia(selectedMediaIndex - 1)}
            className="absolute left-1 top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-md ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex cursor-pointer"
            aria-label="Ảnh con trước"
          >
            <ChevronLeft className="h-4.5 w-4.5" />
          </button>
          <div className="w-full px-1">
            <Swiper
              modules={[FreeMode, Thumbs]}
              onSwiper={setThumbsSwiper}
              freeMode
              watchSlidesProgress
              slidesPerView="auto"
              spaceBetween={8}
              className="product-thumbs-swiper"
            >
              {mediaItems.map((item, index) => (
                <SwiperSlide key={`thumb-${item.key}`} className="!h-[74px] !w-[82px]">
                  <button
                    data-media-index={index}
                    onClick={() => selectMedia(index)}
                    className={`relative flex h-full w-full items-center justify-center overflow-hidden rounded-xl border-2 transition-all cursor-pointer ${selectedMediaIndex === index ? 'border-primary bg-white' : 'border-gray-200 bg-white opacity-70 hover:border-gray-400 hover:opacity-100'}`}
                    aria-label={item.label}
                  >
                    {item.type === 'video' ? (
                      <>
                        {(youtubeThumbnailUrl(item.url) || item.poster) ? (
                          <ImageWithFallback
                            src={youtubeThumbnailUrl(item.url) || item.poster}
                            fallbackSrc={fallbackImage}
                            alt=""
                            loading="lazy"
                            className="h-full w-full object-cover opacity-80"
                          />
                        ) : (
                          <PlayCircle className="h-8 w-8 text-primary" />
                        )}
                        <span className="absolute inset-0 flex items-center justify-center bg-black/10">
                          <PlayCircle className="h-6 w-6 text-white drop-shadow" />
                        </span>
                      </>
                    ) : (
                      <ImageWithFallback
                        src={item.url}
                        fallbackSrc={fallbackImage}
                        alt=""
                        loading="lazy"
                        className="h-full w-full object-contain"
                      />
                    )}
                  </button>
                </SwiperSlide>
              ))}
            </Swiper>
          </div>
          <button
            onClick={() => selectMedia(selectedMediaIndex + 1)}
            className="absolute right-1 top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-md ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex cursor-pointer"
            aria-label="Ảnh con sau"
          >
            <ChevronRight className="h-4.5 w-4.5" />
          </button>
        </div>
      )}
    </div>
  );
}

