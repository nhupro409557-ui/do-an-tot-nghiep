import React, { useEffect, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Autoplay } from 'swiper/modules';
import { Link } from 'react-router-dom';
import { publicApi } from '../../../services/publicApi';

import 'swiper/css';
import 'swiper/css/navigation';

import { ProductCard } from '../../products/components/ProductCard';
import { FlashSaleCountdown } from './FlashSaleCountdown';

export const FlashSale = () => {
  const [flashSaleProducts, setFlashSaleProducts] = useState<any[]>([]);
  const nearestEndTime = flashSaleProducts
    .map((product) => product.flashSale?.endsAt)
    .filter(Boolean)
    .sort((left, right) => new Date(left).getTime() - new Date(right).getTime())[0];

  useEffect(() => {
    publicApi.listProducts({ flashSale: true, limit: 12 })
      .then(setFlashSaleProducts)
      .catch(err => {
        console.error(err);
        setFlashSaleProducts([]);
      });
  }, []);

  if (flashSaleProducts.length === 0) return null;

  return (
    <div className="mt-4 bg-white rounded-xl overflow-hidden border border-primary shadow-sm">
      <div className="flex flex-col gap-3 bg-gradient-to-r from-red-700 via-primary to-orange-500 px-4 py-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-4">
          <h2 className="text-xl md:text-2xl font-bold italic text-white flex items-center gap-2 font-display tracking-widest">
            ⚡ FLASH SALE
          </h2>
          <FlashSaleCountdown endsAt={nearestEndTime} />
        </div>
        <Link to="/flash-sale" className="shrink-0 text-sm font-bold text-white hover:underline">Xem tất cả &gt;</Link>
      </div>

      <div className="p-4 relative group flash-sale-swiper">
        <Swiper
          modules={[Navigation, Autoplay]}
          spaceBetween={16}
          slidesPerView={2.2}
          navigation={{
            enabled: window.innerWidth > 768,
          }}
          autoplay={{ delay: 5000, disableOnInteraction: false }}
          breakpoints={{
            640: { slidesPerView: 3.2 },
            768: { slidesPerView: 4 },
            1024: { slidesPerView: 5 },
          }}
          className="w-full"
        >
          {flashSaleProducts.map((product) => (
            <SwiperSlide key={product.id}>
              <ProductCard p={product} />
            </SwiperSlide>
          ))}
        </Swiper>

        <style>{`
          .flash-sale-swiper .swiper-wrapper {
            align-items: stretch;
          }
          .flash-sale-swiper .swiper-slide {
            height: auto;
            display: flex;
            flex-direction: column;
          }
          .flash-sale-swiper .swiper-slide > div {
            flex: 1;
            width: 100%;
          }
          .flash-sale-swiper .swiper-button-next,
          .flash-sale-swiper .swiper-button-prev {
            background-color: white;
            color: var(--color-primary);
            width: 35px;
            height: 35px;
            border-radius: 50%;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            opacity: 0;
            transition: all 0.3s ease;
          }
          .flash-sale-swiper .swiper-button-next:after,
          .flash-sale-swiper .swiper-button-prev:after {
            font-size: 14px;
            font-weight: 900;
          }
          .flash-sale-swiper:hover .swiper-button-next,
          .flash-sale-swiper:hover .swiper-button-prev {
            opacity: 1;
          }
          .flash-sale-swiper .swiper-button-next { right: 0px; }
          .flash-sale-swiper .swiper-button-prev { left: 0px; }
        `}</style>
      </div>
    </div>
  );
};
