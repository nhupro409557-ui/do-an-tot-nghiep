import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Heart, Scale } from "lucide-react";
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
      className="group relative flex h-full flex-col rounded-xl border border-slate-100 bg-white p-3 shadow-sm transition-all duration-300 hover:border-red-100 hover:shadow-xl md:p-4"
    >
      {p.badge && (
        <div className="absolute left-2 top-2 z-10 rounded-lg bg-red-500 px-2 py-1 text-[10px] font-bold uppercase text-white shadow-sm">
          {p.badge}
        </div>
      )}

      <div className="group/image relative">
        <Link to={`/product/${p.id}`} className="relative mb-2 flex h-40 items-center justify-center overflow-hidden rounded-lg bg-white p-2">
          {displayImage ? (
            <ImageWithFallback src={displayImage} alt={p.name} className="h-full w-full object-contain transition-transform duration-300 group-hover/image:scale-105" />
          ) : (
            <span className="font-bold text-slate-300">Chưa có ảnh</span>
          )}
        </Link>
        {images.length > 1 && (
          <div className="absolute bottom-4 left-0 right-0 z-20 flex justify-center gap-1.5 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            {images.map((_: any, idx: number) => (
              <button
                key={idx}
                onMouseEnter={() => setHoverImageIdx(idx)}
                onMouseLeave={() => setHoverImageIdx(null)}
                onClick={(e) => {
                  e.preventDefault();
                  setMainImageIdx(idx);
                }}
                className={`h-1 w-6 cursor-pointer rounded-full transition-colors ${mainImageIdx === idx ? "bg-primary" : hoverImageIdx === idx ? "bg-slate-400" : "bg-slate-300"}`}
                aria-label={`Chọn ảnh ${idx + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      <Link to={`/product/${p.id}`} className="flex flex-col">
        <h4 className="mb-2 h-[40px] text-[13px] font-bold text-slate-800 line-clamp-2 transition-colors group-hover:text-primary md:text-sm">
          {p.name}
        </h4>
        {p.specs && (
          <div className="mb-3 grid grid-cols-2 gap-x-2 gap-y-1 rounded-lg border border-gray-100 bg-gray-50 p-2 text-[10px] text-gray-600 md:text-[11px]">
            {p.specs.processor && <span className="truncate">CPU: {p.specs.processor}</span>}
            {p.specs.ram && <span className="truncate">RAM: {p.specs.ram}</span>}
            {p.specs.screenSize && <span className="col-span-2 truncate">Màn hình: {p.specs.screenSize}</span>}
          </div>
        )}
      </Link>

      <div className="mt-auto flex flex-col justify-end pt-2">
        <Link to={`/product/${p.id}`} className="mb-2 flex items-baseline gap-2">
          <span className="text-sm font-bold text-primary md:text-base">{p.price?.toLocaleString("vi-VN") || 0}đ</span>
          {p.discountPrice && p.discountPrice > p.price && (
            <span className="text-[11px] text-gray-400 line-through md:text-xs">{p.discountPrice.toLocaleString("vi-VN")}đ</span>
          )}
        </Link>

        {p.memberDeal && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-[4px] border border-red-100/50 bg-red-50 px-2 py-1 text-[10px] font-semibold text-primary">
              {p.memberDeal}
            </div>
          </div>
        )}

        <div className="mt-1 flex items-center justify-between border-t border-gray-100 pt-3 text-[10px] text-gray-500 md:text-[11px]">
          <div className="flex items-center gap-1">
            <span className="text-yellow-400">★</span>
            <span>{p.rating ? `${p.rating} (${p.reviewCount || 0} đánh giá)` : "Chưa có đánh giá"}</span>
          </div>
          <button className="flex items-center gap-1 transition-colors hover:text-red-600" type="button">
            <Heart className="h-3.5 w-3.5" />
            Yêu thích
          </button>
        </div>

        <div className="mt-3 border-t border-slate-100 pt-2">
          <Link
            to={`/compare?product=${p.id}`}
            className="flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-red-100 bg-red-50 text-xs font-bold text-primary transition-colors hover:border-primary hover:bg-primary hover:text-white"
          >
            <Scale className="h-4 w-4" />
            So sánh
          </Link>
        </div>
      </div>
    </motion.div>
  );
};
