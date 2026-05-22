import React from 'react';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination, Navigation } from 'swiper/modules';
import { CategoryMegaMenu } from '../layout/CategoryMegaMenu';

import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/navigation';

export const HomeBanner = () => {
  const banners = [
    { id: 1, title: 'Sản phẩm nổi bật', bg: 'bg-gradient-to-r from-gray-900 to-gray-700' },
    { id: 2, title: 'Ưu đãi laptop và PC', bg: 'bg-gradient-to-r from-blue-700 to-blue-500' },
    { id: 3, title: 'Phụ kiện chính hãng', bg: 'bg-gradient-to-r from-red-600 to-orange-500' },
  ];

  return (
    <div className="grid grid-cols-12 gap-4 my-4">
      <div className="hidden lg:block lg:col-span-3 relative z-30">
        <CategoryMegaMenu compact />
      </div>

      <div className="col-span-12 lg:col-span-9 rounded-xl overflow-hidden shadow-sm relative group">
        <Swiper
          spaceBetween={0}
          centeredSlides={true}
          autoplay={{
            delay: 4000,
            disableOnInteraction: false,
          }}
          pagination={{
            clickable: true,
            dynamicBullets: true,
          }}
          navigation={true}
          modules={[Autoplay, Pagination, Navigation]}
          className="h-[200px] md:h-[350px] w-full rounded-xl"
        >
          {banners.map((banner) => (
            <SwiperSlide key={banner.id}>
              <div className={`w-full h-full flex flex-col items-center justify-center text-white ${banner.bg}`}>
                <h2 className="text-2xl md:text-4xl font-bold mb-4 px-4 text-center">{banner.title}</h2>
                <Link to="/products" className="bg-white text-black px-6 py-2 rounded-full font-semibold hover:scale-105 transition-transform text-sm md:text-base">
                  Xem ngay
                </Link>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>

        <style>{`
          .swiper-button-next, .swiper-button-prev {
            color: #4b5563;
            background-color: rgba(255, 255, 255, 0.8);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            opacity: 0;
            transition: opacity 0.3s;
          }
          .swiper-button-next:after, .swiper-button-prev:after {
            font-size: 16px;
            font-weight: bold;
          }
          .group:hover .swiper-button-next, .group:hover .swiper-button-prev {
            opacity: 1;
          }
          .swiper-pagination-bullet-active {
            background-color: #D70018 !important;
          }
        `}</style>
      </div>
    </div>
  );
};
