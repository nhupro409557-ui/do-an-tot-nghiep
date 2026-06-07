import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { Autoplay } from 'swiper/modules';
import { CategoryMegaMenu } from '../../../components/layout/CategoryMegaMenu';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { adminContentApi } from '../../admin-content/services/adminContentApi';

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
    adminContentApi.listBanners()
      .then((items) => setBanners(items.filter((item: any) => item.imageUrl)))
      .catch(() => setBanners([]));
  }, []);

  const displayBanners = useMemo(() => (banners.length ? banners : fallbackBanners), [banners]);
  const activeBanner = displayBanners[activeIndex] || displayBanners[0];

  const scrollBannerTabs = (direction: 'left' | 'right') => {
    const tabList = document.getElementById('home-banner-tabs');
    tabList?.scrollBy({ left: direction === 'left' ? -220 : 220, behavior: 'smooth' });
  };

  return (
    <div className="my-4 grid gap-3 lg:grid-cols-[274px_minmax(0,1fr)]">
      <div className="relative z-30 hidden lg:block">
        <CategoryMegaMenu compact />
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
        <div className="relative">
          <div id="home-banner-tabs" className="flex overflow-x-auto rounded-t-2xl bg-white px-8 text-center [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {displayBanners.map((banner, index) => (
            <button
              key={banner.id}
              type="button"
              onClick={() => {
                setActiveIndex(index);
                if (displayBanners.length > 1) {
                  swiper?.slideToLoop(index);
                } else {
                  swiper?.slideTo(index);
                }
              }}
              className={`min-h-[58px] w-[150px] flex-none border-b px-3 py-2 transition sm:w-[180px] lg:min-h-[64px] lg:w-[210px] ${activeIndex === index ? 'rounded-b-3xl bg-slate-100 text-red-600' : 'border-slate-100 text-slate-600 hover:bg-slate-50'}`}
            >
              <div className="line-clamp-1 text-[13px] font-black uppercase lg:text-base">{banner.title}</div>
                <div className="mt-0.5 line-clamp-1 text-xs font-medium text-slate-500 lg:text-sm">{banner.description || 'Ưu đãi hôm nay'}</div>
            </button>
          ))}
          </div>
          <div className="pointer-events-none absolute inset-y-0 left-0 w-7 bg-gradient-to-r from-white to-transparent" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-7 bg-gradient-to-l from-white to-transparent" />
          {displayBanners.length > 1 && (
            <>
              <button
                type="button"
                onClick={() => scrollBannerTabs('left')}
                aria-label="Lướt banner sang trái"
                className="absolute left-1 top-1/2 z-10 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-slate-600 shadow-sm transition hover:border-red-200 hover:text-primary"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => scrollBannerTabs('right')}
                aria-label="Lướt banner sang phải"
                className="absolute right-1 top-1/2 z-10 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white/95 text-slate-600 shadow-sm transition hover:border-red-200 hover:text-primary"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </>
          )}
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
