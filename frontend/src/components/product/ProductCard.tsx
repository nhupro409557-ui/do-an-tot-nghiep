import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ImageWithFallback } from "../ui/ImageWithFallback";
import { motion } from "motion/react";

export const ProductCard = ({ p, index = 0 }: { p: any; index?: number }) => {
  const images = p.images && p.images.length > 0 ? p.images : p.imageUrl ? [p.imageUrl] : [];
  const [hoverImageIdx, setHoverImageIdx] = useState<number | null>(null);
  const [mainImageIdx, setMainImageIdx] = useState<number>(0);
  const displayImage = hoverImageIdx !== null && images[hoverImageIdx] ? images[hoverImageIdx] : images[mainImageIdx];

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
      className="bg-white p-3 md:p-4 rounded-xl shadow-sm border border-slate-100 flex flex-col h-full group hover:shadow-xl hover:border-red-100 transition-all duration-300 relative"
    >
      {p.badge && (
        <div className="absolute top-2 left-2 z-10 px-2 py-1 bg-red-500 text-white text-[10px] font-bold rounded-lg uppercase shadow-sm">
          {p.badge}
        </div>
      )}
      <div className="relative group/image">
        <Link to={`/product/${p.id}`} className="bg-white h-40 rounded-lg mb-2 flex items-center justify-center p-2 relative overflow-hidden block">
          {displayImage ? (
            <ImageWithFallback src={displayImage} alt={p.name} className="w-full h-full object-contain transition-transform duration-300 group-hover/image:scale-105" />
          ) : (
            <span className="text-slate-300 font-bold">Chưa có ảnh</span>
          )}
        </Link>
        {images.length > 1 && (
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-20">
            {images.map((_: any, idx: number) => (
              <button
                key={idx}
                onMouseEnter={() => setHoverImageIdx(idx)}
                onMouseLeave={() => setHoverImageIdx(null)}
                onClick={(e) => {
                  e.preventDefault();
                  setMainImageIdx(idx);
                }}
                className={`w-6 h-1 rounded-full cursor-pointer transition-colors ${mainImageIdx === idx ? "bg-primary" : hoverImageIdx === idx ? "bg-slate-400" : "bg-slate-300"}`}
                aria-label={`Select image ${idx + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      <Link to={`/product/${p.id}`} className="flex flex-col">
        <h4 className="font-bold text-[13px] md:text-sm mb-2 line-clamp-2 text-slate-800 group-hover:text-primary transition-colors h-[40px]">
          {p.name}
        </h4>
        {p.specs && (
          <div className="bg-gray-50 rounded-lg p-2 mb-3 text-[10px] md:text-[11px] text-gray-600 grid grid-cols-2 gap-y-1 gap-x-2 border border-gray-100">
            {p.specs.processor && <span className="truncate">CPU: {p.specs.processor}</span>}
            {p.specs.ram && <span className="truncate">RAM: {p.specs.ram}</span>}
            {p.specs.screenSize && <span className="col-span-2 truncate">Màn hình: {p.specs.screenSize}</span>}
          </div>
        )}
      </Link>

      {/* KẾT CẤU MT-AUTO ĐỂ ĐẨY FOOTER XUỐNG ĐÁY */}
      <div className="mt-auto flex flex-col justify-end pt-2">
        <Link to={`/product/${p.id}`} className="flex items-baseline gap-2 mb-2">
          <span className="text-primary font-bold text-sm md:text-base">{p.price?.toLocaleString("vi-VN") || 0}₫</span>
          {p.discountPrice && p.discountPrice > p.price && (
            <span className="text-[11px] md:text-xs text-gray-400 line-through">{p.discountPrice.toLocaleString("vi-VN")}₫</span>
          )}
        </Link>

        {p.memberDeal && (
          <div className="mb-2 flex gap-2 flex-wrap items-center">
            <div className="bg-red-50 text-primary text-[10px] px-2 py-1 rounded-[4px] font-semibold flex items-center gap-1 border border-red-100/50">
              {p.memberDeal}
            </div>
          </div>
        )}

        <div className="flex justify-between items-center text-[10px] md:text-[11px] text-gray-500 border-t border-gray-100 pt-3 mt-1">
          <div className="flex items-center gap-1">
            <span className="text-yellow-400">⭐</span>
            <span>{p.rating ? `${p.rating} (${p.reviewCount || 0} đánh giá)` : 'Chưa có đánh giá'}</span>
          </div>
          <button className="hover:text-red-600 transition-colors flex items-center gap-1">❤️ Yêu thích</button>
        </div>

        <div className="lg:hidden mt-3 pt-2 border-t border-slate-100">
          <Link to={`/compare?product=${p.id}`} className="w-full text-center py-1.5 block bg-gray-50 text-primary border border-red-100 rounded text-xs font-bold">+ So sánh</Link>
        </div>
      </div>

      <div className="hidden lg:flex absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-white via-white to-transparent opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 items-center justify-center gap-2 pb-4">
        <Link to={`/compare?product=${p.id}`} className="flex-1 text-center py-2 bg-primary text-white text-xs font-bold rounded shadow-md hover:bg-red-700 transition-colors">So sánh</Link>
      </div>
    </motion.div>
  );
};
