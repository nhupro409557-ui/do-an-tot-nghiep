import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BadgePercent, ChevronLeft, ChevronRight, ShieldCheck, ShoppingBag, Truck } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { Autoplay } from 'swiper/modules';
import { CategoryMegaMenu } from '../../../components/layout/CategoryMegaMenu';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { adminContentApi } from '../../admin-content/services/adminContentApi';

import 'swiper/css';

export const HomeBanner = () => {
  const [banners, setBanners] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);
  const [swiper, setSwiper] = useState<SwiperType | null>(null);
  const tabListRef = useRef<HTMLDivElement | null>(null);
  const tabDragRef = useRef({ active: false, moved: false, startX: 0, startScrollLeft: 0 });
  const tabAnimationRef = useRef<number | null>(null);

  useEffect(() => {
    adminContentApi.listBanners()
      .then(setBanners)
      .catch(() => setBanners([]))
      .finally(() => setLoading(false));
  }, []);

  const activeBanner = banners[activeIndex] || banners[0];

  const animateBannerTabs = (targetLeft: number) => {
    const tabList = tabListRef.current;
    if (!tabList) return;
    const firstTab = tabList.querySelector<HTMLElement>('[data-banner-tab]');
    const columnWidth = firstTab?.offsetWidth || tabList.clientWidth;
    const maxScrollLeft = Math.max(0, tabList.scrollWidth - tabList.clientWidth);
    const alignedTarget = Math.min(maxScrollLeft, Math.max(0, Math.round(targetLeft / columnWidth) * columnWidth));
    if (tabAnimationRef.current !== null) cancelAnimationFrame(tabAnimationRef.current);
    const startLeft = tabList.scrollLeft;
    const distance = alignedTarget - startLeft;
    const duration = 320;
    const startTime = performance.now();
    const animate = (time: number) => {
      const progress = Math.min((time - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      tabList.scrollLeft = startLeft + distance * eased;
      if (progress < 1) {
        tabAnimationRef.current = requestAnimationFrame(animate);
      } else {
        tabAnimationRef.current = null;
      }
    };
    tabAnimationRef.current = requestAnimationFrame(animate);
  };

  const scrollBannerTabs = (direction: 'left' | 'right') => {
    const tabList = tabListRef.current;
    if (!tabList) return;
    const firstTab = tabList.querySelector<HTMLElement>('[data-banner-tab]');
    const columnWidth = firstTab?.offsetWidth || tabList.clientWidth;
    animateBannerTabs(tabList.scrollLeft + (direction === 'left' ? -columnWidth : columnWidth));
  };

  const revealActiveBannerTab = (index: number) => {
    const tabList = tabListRef.current;
    if (!tabList) return;
    const tabs = Array.from(tabList.querySelectorAll<HTMLElement>('[data-banner-tab]'));
    const activeTab = tabs[index];
    if (!activeTab) return;
    const visibleLeft = tabList.scrollLeft;
    const visibleRight = visibleLeft + tabList.clientWidth;
    const tabLeft = activeTab.offsetLeft;
    const tabRight = tabLeft + activeTab.offsetWidth;
    if (tabLeft < visibleLeft) {
      animateBannerTabs(index * activeTab.offsetWidth);
    } else if (tabRight > visibleRight) {
      const visibleColumns = Math.max(1, Math.round(tabList.clientWidth / activeTab.offsetWidth));
      animateBannerTabs((index - visibleColumns + 1) * activeTab.offsetWidth);
    }
  };

  const selectBanner = (index: number) => {
    setActiveIndex(index);
    requestAnimationFrame(() => revealActiveBannerTab(index));
  };

  const finishBannerTabDrag = () => {
    const tabList = tabListRef.current;
    const drag = tabDragRef.current;
    if (!tabList || !drag.active) return;
    drag.active = false;
    const firstTab = tabList.querySelector<HTMLElement>('[data-banner-tab]');
    const columnWidth = firstTab?.offsetWidth || tabList.clientWidth;
    const distance = tabList.scrollLeft - drag.startScrollLeft;
    if (Math.abs(distance) < 12) {
      animateBannerTabs(drag.startScrollLeft);
      return;
    }
    animateBannerTabs(drag.startScrollLeft + (distance > 0 ? columnWidth : -columnWidth));
  };

  return (
    <div className="my-4 grid gap-3 lg:h-[clamp(454px,38vw,568px)] lg:grid-cols-[274px_minmax(0,1fr)]">
      <div className="relative z-30 hidden min-h-0 lg:block">
        <CategoryMegaMenu compact />
      </div>

      <div className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
        <div className="flex items-stretch bg-white">
          {banners.length > 1 && (
            <button
              type="button"
              onClick={() => scrollBannerTabs('left')}
              aria-label="Lướt banner sang trái"
              className="z-10 flex w-9 shrink-0 items-center justify-center border-r border-slate-100 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-primary"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          )}
          <div
            ref={tabListRef}
            id="home-banner-tabs"
            onWheel={(event) => {
              if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
              event.preventDefault();
              scrollBannerTabs(event.deltaY > 0 ? 'right' : 'left');
            }}
            onPointerDown={(event) => {
              if (event.pointerType !== 'mouse' || event.button !== 0) return;
              const tabList = tabListRef.current;
              if (!tabList) return;
              if (tabAnimationRef.current !== null) {
                cancelAnimationFrame(tabAnimationRef.current);
                tabAnimationRef.current = null;
              }
              tabDragRef.current = {
                active: true,
                moved: false,
                startX: event.clientX,
                startScrollLeft: tabList.scrollLeft,
              };
            }}
            onPointerMove={(event) => {
              const tabList = tabListRef.current;
              const drag = tabDragRef.current;
              if (!tabList || !drag.active) return;
              const distance = event.clientX - drag.startX;
              if (Math.abs(distance) > 5) drag.moved = true;
              tabList.scrollLeft = drag.startScrollLeft - distance;
            }}
            onPointerUp={finishBannerTabDrag}
            onPointerLeave={finishBannerTabDrag}
            onPointerCancel={finishBannerTabDrag}
            className="flex min-w-0 flex-1 snap-x snap-mandatory overflow-x-auto overscroll-x-contain text-center touch-pan-x select-none [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
          {banners.map((banner, index) => (
            <button
              key={banner.id}
              data-banner-tab
              type="button"
              onClick={(event) => {
                if (tabDragRef.current.moved) {
                  event.preventDefault();
                  tabDragRef.current.moved = false;
                  return;
                }
                selectBanner(index);
                if (banners.length > 1) {
                  swiper?.slideToLoop(index);
                } else {
                  swiper?.slideTo(index);
                }
              }}
              className={`min-h-[58px] w-1/2 flex-none snap-start border-b px-3 py-2 transition md:w-1/3 lg:min-h-[64px] xl:w-1/4 ${activeIndex === index ? 'rounded-b-3xl bg-slate-100 text-red-600' : 'border-slate-100 text-slate-600 hover:bg-slate-50'}`}
            >
              <div className="overflow-hidden whitespace-nowrap text-[13px] font-black uppercase lg:text-base">{banner.title}</div>
                <div className="mt-0.5 overflow-hidden whitespace-nowrap text-xs font-medium text-slate-500 lg:text-sm">{banner.description || 'Ưu đãi hôm nay'}</div>
            </button>
          ))}
          </div>
          {banners.length > 1 && (
            <button
              type="button"
              onClick={() => scrollBannerTabs('right')}
              aria-label="Lướt banner sang phải"
              className="z-10 flex w-9 shrink-0 items-center justify-center border-l border-slate-100 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-primary"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="relative min-h-[210px] flex-1 sm:min-h-[280px] lg:min-h-[390px]">
          {banners.length ? (
            <Swiper
              modules={[Autoplay]}
              onSwiper={setSwiper}
              onSlideChange={(instance) => selectBanner(instance.realIndex)}
              autoplay={{ delay: 4500, disableOnInteraction: false }}
              loop={banners.length > 1}
              className="absolute inset-0 h-full w-full"
            >
              {banners.map((banner) => (
                <SwiperSlide key={banner.id}>
                  <Link to={banner.href || '/products'} className="relative block h-full w-full overflow-hidden bg-slate-100">
                    {banner.imageUrl ? (
                      <ImageWithFallback
                        src={banner.imageUrl}
                        alt={banner.title}
                        className="h-full w-full object-fill"
                        loading="eager"
                      />
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center bg-gradient-to-br from-red-600 via-red-500 to-orange-400 px-8 text-center text-white">
                        <div className="text-2xl font-black uppercase sm:text-3xl lg:text-4xl">{banner.title}</div>
                        {banner.description && <div className="mt-3 max-w-2xl text-sm font-semibold sm:text-base lg:text-lg">{banner.description}</div>}
                      </div>
                    )}
                  </Link>
                </SwiperSlide>
              ))}
            </Swiper>
          ) : loading ? (
            <div className="absolute inset-0 overflow-hidden bg-slate-50">
              <div className="h-full w-full animate-pulse bg-gradient-to-r from-slate-100 via-white to-slate-100" />
              <div className="absolute inset-x-6 bottom-6 space-y-3 sm:inset-x-10 sm:bottom-10">
                <div className="h-4 w-28 rounded-full bg-white/80" />
                <div className="h-8 w-3/4 max-w-xl rounded-full bg-white/80" />
                <div className="h-4 w-1/2 max-w-md rounded-full bg-white/80" />
              </div>
            </div>
          ) : (
            <Link
              to="/products"
              className="absolute inset-0 flex overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-red-700 text-white"
            >
              <div className="relative z-10 flex h-full max-w-3xl flex-col justify-center px-6 py-8 sm:px-10 lg:px-14">
                <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-bold uppercase text-white/90">
                  <BadgePercent className="h-3.5 w-3.5" />
                  Ưu đãi thiết bị chính hãng
                </div>
                <h2 className="max-w-2xl text-2xl font-black leading-tight tracking-tight sm:text-4xl lg:text-5xl">
                  Mua sắm điện thoại, laptop và phụ kiện dễ hơn mỗi ngày
                </h2>
                <p className="mt-4 max-w-xl text-sm leading-6 text-white/75 sm:text-base">
                  Khám phá danh mục sản phẩm nổi bật, so sánh nhanh cấu hình và nhận gợi ý phù hợp với nhu cầu của bạn.
                </p>
                <div className="mt-6 inline-flex h-11 w-fit items-center justify-center gap-2 rounded-lg bg-white px-4 text-sm font-extrabold text-primary shadow-lg shadow-black/20">
                  <ShoppingBag className="h-4 w-4" />
                  Xem sản phẩm
                </div>
                <div className="mt-6 grid max-w-xl gap-2 text-xs font-semibold text-white/80 sm:grid-cols-3">
                  <span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Chính hãng</span>
                  <span className="flex items-center gap-2"><Truck className="h-4 w-4" /> Giao nhanh</span>
                  <span className="flex items-center gap-2"><BadgePercent className="h-4 w-4" /> Nhiều ưu đãi</span>
                </div>
              </div>
              <div className="absolute right-8 top-10 hidden h-24 w-36 rounded-2xl border border-white/10 bg-white/10 lg:block" />
              <div className="absolute bottom-10 right-28 hidden h-32 w-44 rounded-2xl border border-white/10 bg-white/10 lg:block" />
            </Link>
          )}

          {activeBanner && (
            <div className="absolute bottom-3 right-3 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-slate-700 shadow-sm">
              {activeIndex + 1}/{banners.length}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
