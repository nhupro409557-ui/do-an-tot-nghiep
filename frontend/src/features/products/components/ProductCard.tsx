import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Heart, Scale } from "lucide-react";
import { ImageWithFallback } from "../../../components/ui/ImageWithFallback";
import { motion } from "motion/react";

export const ProductCard = ({ p, index = 0 }: { p: any; index?: number }) => {
  const primaryImages = [
    p.imageUrl,
    ...(Array.isArray(p.variants) ? p.variants.map((variant: any) => variant.imageUrl).filter(Boolean) : []),
  ];
  const images = Array.from(new Set(primaryImages.filter(Boolean)));
  const [hoverImageIdx, setHoverImageIdx] = useState<number | null>(null);
  const [mainImageIdx, setMainImageIdx] = useState<number>(0);
  const displayImage = hoverImageIdx !== null && images[hoverImageIdx] ? images[hoverImageIdx] : images[mainImageIdx];
  const displayPrice = Number(p.salePrice || p.discountPrice || p.price || 0);
  const originalPrice = Number(p.originalPrice || p.price || 0);
  const hasSale = originalPrice > displayPrice;
  const isDiscontinued = p.status === 'DISCONTINUED';

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
      className="group relative flex h-full flex-col rounded-xl border border-slate-100 bg-white p-3 shadow-sm transition-all duration-300 hover:border-red-100 hover:shadow-xl md:p-4"
    >
      {p.badge && !p.flashSale && (
        <div className="absolute left-2 top-2 z-10 rounded-lg bg-red-500 px-2 py-1 text-[10px] font-bold uppercase text-white shadow-sm">
          {p.badge}
        </div>
      )}
        {p.flashSale && !isDiscontinued && (
        <div className="absolute left-2 top-2 z-10 rounded-lg bg-red-600 px-2 py-1 text-[10px] font-bold uppercase text-white shadow-sm">
          HOT
        </div>
      )}

      <div className="group/image relative -mx-1 -mt-1 md:-mx-2 md:-mt-2">
        <Link to={`/product/${p.id}`} className="relative mb-3 flex h-48 items-center justify-center overflow-hidden rounded-lg bg-white p-0 md:h-52">
          {displayImage ? (
            <ImageWithFallback src={displayImage} alt={p.name} className="h-full w-full object-contain transition-transform duration-300 group-hover/image:scale-[1.03]" />
          ) : (
            <span className="font-bold text-slate-300">Chưa có ảnh</span>
          )}
        </Link>
        {images.length > 1 && (
          <div className="absolute bottom-5 left-0 right-0 z-20 flex justify-center gap-1.5 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
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
          {isDiscontinued ? (
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black uppercase text-slate-700">Ngừng kinh doanh</span>
          ) : (
            <>
              <span className="text-sm font-bold text-primary md:text-base">{displayPrice.toLocaleString("vi-VN")}đ</span>
              {hasSale && (
                <span className="text-[11px] text-gray-400 line-through md:text-xs">{originalPrice.toLocaleString("vi-VN")}đ</span>
              )}
            </>
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
          {!isDiscontinued && (
            <button className="flex items-center gap-1 transition-colors hover:text-red-600" type="button">
              <Heart className="h-3.5 w-3.5" />
              Yêu thích
            </button>
          )}
        </div>

        {!isDiscontinued && <div className="mt-3 border-t border-slate-100 pt-2">
          <Link
            to={`/compare?product=${p.id}`}
            className="flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-red-100 bg-red-50 text-xs font-bold text-primary transition-colors hover:border-primary hover:bg-primary hover:text-white"
          >
            <Scale className="h-4 w-4" />
            So sánh
          </Link>
        </div>}
      </div>
    </motion.div>
  );
};
