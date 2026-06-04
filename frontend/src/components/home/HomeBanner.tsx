import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { Autoplay } from 'swiper/modules';
import { CategoryMegaMenu } from '../layout/CategoryMegaMenu';
import { ImageWithFallback } from '../ui/ImageWithFallback';
import { apiDb } from '../../services/apiDb';

import 'swiper/css';

const fallbackBanners = [
  {
    id: 'fallback-phone',
    title: 'ĐIỆN THOẠI NỔI BẬT',
    description: 'Ưu đãi đang mở',
    imageUrl: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1400&auto=format&fit=crop',
    href: '/products',
  },
  {
    id: 'fallback-laptop',
    title: 'LAPTOP LÀM VIỆC',
    description: 'Mỏng nhẹ, hiệu năng cao',
    imageUrl: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1400&auto=format&fit=crop',
    href: '/products',
  },
  {
    id: 'fallback-audio',
    title: 'PHỤ KIỆN CHÍNH HÃNG',
    description: 'Giá tốt mỗi ngày',
    imageUrl: 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=1400&auto=format&fit=crop',
    href: '/products',
  },
];

export const HomeBanner = () => {
  const [banners, setBanners] = useState<any[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [swiper, setSwiper] = useState<SwiperType | null>(null);

  useEffect(() => {
    apiDb.listBanners()
      .then((items) => setBanners(items.filter((item: any) => item.imageUrl)))
      .catch(() => setBanners([]));
  }, []);

  const displayBanners = useMemo(() => (banners.length ? banners : fallbackBanners), [banners]);
  const activeBanner = displayBanners[activeIndex] || displayBanners[0];

  return (
    <div className="my-4 grid gap-3 lg:grid-cols-[274px_minmax(0,1fr)]">
      <div className="relative z-30 hidden lg:block">
        <CategoryMegaMenu compact />
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
        <div className="grid grid-cols-2 overflow-hidden rounded-t-2xl bg-white text-center md:grid-cols-4">
          {displayBanners.slice(0, 4).map((banner, index) => (
            <button
              key={banner.id}
              type="button"
              onClick={() => {
                setActiveIndex(index);
                swiper?.slideTo(index);
              }}
              className={`min-h-[64px] border-b px-2 py-2 transition ${activeIndex === index ? 'rounded-b-3xl bg-slate-100 text-red-600' : 'border-slate-100 text-slate-600 hover:bg-slate-50'}`}
            >
              <div className="line-clamp-1 text-sm font-black uppercase md:text-base">{banner.title}</div>
              <div className="mt-0.5 line-clamp-1 text-xs font-medium text-slate-500 md:text-sm">{banner.description || 'Ưu đãi hôm nay'}</div>
            </button>
          ))}
        </div>

        <div className="relative">
          <Swiper
            modules={[Autoplay]}
            onSwiper={setSwiper}
            onSlideChange={(instance) => setActiveIndex(instance.realIndex)}
            autoplay={{ delay: 4500, disableOnInteraction: false }}
            loop={displayBanners.length > 1}
            className="h-[210px] w-full sm:h-[280px] lg:h-[390px]"
          >
            {displayBanners.map((banner) => (
              <SwiperSlide key={banner.id}>
                <Link to={banner.href || '/products'} className="relative block h-full w-full overflow-hidden bg-slate-100">
                  <ImageWithFallback
                    src={banner.imageUrl}
                    alt={banner.title}
                    className="h-full w-full object-cover"
                    loading="eager"
                  />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/35 to-transparent" />
                  <div className="pointer-events-none absolute bottom-4 left-4 hidden text-white drop-shadow sm:block">
                    <div className="text-xl font-black uppercase">{banner.title}</div>
                    {banner.description && <div className="mt-1 text-sm font-semibold">{banner.description}</div>}
                  </div>
                </Link>
              </SwiperSlide>
            ))}
          </Swiper>

          {activeBanner && (
            <div className="absolute bottom-3 right-3 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-slate-700 shadow-sm">
              {activeIndex + 1}/{displayBanners.length}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
