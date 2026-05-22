import React, { useEffect, useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Autoplay } from 'swiper/modules';
import { Link } from 'react-router-dom';
import { apiDb } from '../../services/apiDb';

import 'swiper/css';
import 'swiper/css/navigation';

import { ProductCard } from '../product/ProductCard';

export const FlashSale = () => {
  const [flashSaleProducts, setFlashSaleProducts] = useState<any[]>([]);

  useEffect(() => {
    apiDb.listProducts()
      .then(products => setFlashSaleProducts(products.filter((product: any) => product.isFlashSale).slice(0, 12)))
      .catch(err => {
        console.error(err);
        setFlashSaleProducts([]);
      });
  }, []);

  if (flashSaleProducts.length === 0) return null;

  return (
    <div className="mt-8 bg-white rounded-xl overflow-hidden border border-primary shadow-sm">
      <div className="bg-primary px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl md:text-2xl font-bold italic text-white flex items-center gap-2 font-display tracking-widest">
            ⚡ FLASH SALE
          </h2>
        </div>
        <Link to="/search" className="text-white text-sm hover:underline">Xem tất cả &gt;</Link>
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
