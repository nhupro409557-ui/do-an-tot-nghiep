import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, Heart, Scale } from "lucide-react";
import { ImageWithFallback } from "../../../components/ui/ImageWithFallback";
import { motion } from "motion/react";

const getFlashSaleRemaining = (endsAt?: string) => {
  const distance = endsAt ? Math.max(new Date(endsAt).getTime() - Date.now(), 0) : 0;
  const days = Math.floor(distance / 86400000);
  const hours = Math.floor((distance / 3600000) % 24);
  const minutes = Math.floor((distance / 60000) % 60);
  const seconds = Math.floor((distance / 1000) % 60);
  return { days, hours, minutes, seconds };
};

function ProductFlashSaleTimer({ endsAt }: { endsAt: string }) {
  const [remaining, setRemaining] = useState(() => getFlashSaleRemaining(endsAt));

  useEffect(() => {
    setRemaining(getFlashSaleRemaining(endsAt));
    const timer = window.setInterval(() => setRemaining(getFlashSaleRemaining(endsAt)), 1000);
    return () => window.clearInterval(timer);
  }, [endsAt]);

  return (
    <div className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-red-100 bg-gradient-to-r from-red-50 to-orange-50 px-2.5 py-2 text-primary">
      <span className="flex shrink-0 items-center gap-1 text-[10px] font-black uppercase">
        <Clock3 className="h-3.5 w-3.5" />
        Còn lại
      </span>
      <span className="truncate text-[11px] font-black tabular-nums">
        {remaining.days > 0 ? `${remaining.days} ngày ` : ''}
        {String(remaining.hours).padStart(2, '0')}:
        {String(remaining.minutes).padStart(2, '0')}:
        {String(remaining.seconds).padStart(2, '0')}
      </span>
    </div>
  );
}

function FlashSaleDiscountLabel({ flashSale }: { flashSale: any }) {
  if (!flashSale) return null;
  const discountValue = Number(flashSale.discountValue || 0);
  if (discountValue <= 0) return null;
  const label = flashSale.discountType === 'PERCENT'
    ? `Giảm ${discountValue.toLocaleString('vi-VN')}%`
    : `Giảm ${discountValue.toLocaleString('vi-VN')}đ`;

  return (
    <span className="rounded-md bg-red-600 px-2 py-1 text-[10px] font-black uppercase text-white shadow-sm">
      {label}
    </span>
  );
}

export const ProductCard = ({ p, index = 0 }: { p: any; index?: number }) => {
  const productHref = `/product/${p.id}${p.flashSaleVariantId ? `?variant=${encodeURIComponent(p.flashSaleVariantId)}` : ''}`;
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
      className="group relative flex h-full min-w-0 flex-col rounded-xl border border-slate-100 bg-white p-2.5 shadow-sm transition-all duration-300 hover:border-red-100 hover:shadow-xl sm:p-3 lg:p-4"
    >
      {p.badge && !p.flashSale && (
        <div className="absolute left-2 top-2 z-10 rounded-lg bg-red-500 px-2 py-1 text-[10px] font-bold uppercase text-white shadow-sm">
          {p.badge}
        </div>
      )}
        {p.flashSale && !isDiscontinued && (
        <div className="absolute left-2 top-2 z-10 flex items-center gap-1.5">
          <span className="rounded-lg bg-red-600 px-2 py-1 text-[10px] font-bold uppercase text-white shadow-sm">
            HOT
          </span>
          <FlashSaleDiscountLabel flashSale={p.flashSale} />
        </div>
      )}

      <div className="group/image relative -mx-0.5 -mt-0.5 sm:-mx-1 sm:-mt-1 lg:-mx-2 lg:-mt-2">
        <Link to={productHref} className="relative mb-2.5 flex h-40 items-center justify-center overflow-hidden rounded-lg bg-white p-0 sm:h-44 md:h-48 lg:h-56">
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

      <Link to={productHref} className="flex flex-col">
        <h4 className="mb-2 h-[38px] text-[12.5px] font-bold leading-[1.25] text-slate-800 line-clamp-2 transition-colors group-hover:text-primary sm:text-[13px] lg:text-sm">
          {p.name}
        </h4>
        {p.specs && (
          <div className="mb-2 grid grid-cols-1 gap-x-2 gap-y-1 rounded-lg border border-gray-100 bg-gray-50 p-2 text-[10px] text-gray-600 sm:grid-cols-2 lg:text-[11px]">
            {p.specs.processor && <span className="truncate">CPU: {p.specs.processor}</span>}
            {p.specs.ram && <span className="truncate">RAM: {p.specs.ram}</span>}
            {p.specs.screenSize && <span className="truncate sm:col-span-2">Màn hình: {p.specs.screenSize}</span>}
          </div>
        )}
      </Link>

      <div className="mt-1 flex flex-col justify-end pt-1">
        {p.flashSale?.endsAt && !isDiscontinued && <ProductFlashSaleTimer endsAt={p.flashSale.endsAt} />}
        <Link to={productHref} className="mb-2 flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
          {isDiscontinued ? (
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-black uppercase text-slate-700">Ngừng kinh doanh</span>
          ) : (
            <>
              <span className="text-[13px] font-bold text-primary sm:text-sm lg:text-base">{displayPrice.toLocaleString("vi-VN")}đ</span>
              {hasSale && (
                <span className="max-w-full truncate text-[10px] text-gray-400 line-through sm:text-[11px] lg:text-xs">{originalPrice.toLocaleString("vi-VN")}đ</span>
              )}
            </>
          )}
        </Link>

        {p.memberDeal && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <div className="flex min-w-0 items-start gap-1 rounded-[4px] border border-red-100/50 bg-red-50 px-2 py-1 text-[10px] font-semibold text-primary">
              {p.memberDeal}
            </div>
          </div>
        )}

        <div className="mt-1 flex min-w-0 items-start justify-between gap-2 border-t border-gray-100 pt-3 text-[10px] text-gray-500 lg:text-[11px]">
          <div className="flex min-w-0 items-start gap-1">
            <span className="text-yellow-400">★</span>
            <span className="line-clamp-2">{p.rating ? `${p.rating} (${p.reviewCount || 0} đánh giá)` : "Chưa có đánh giá"}</span>
          </div>
          {!isDiscontinued && (
            <button className="flex shrink-0 items-center gap-1 transition-colors hover:text-red-600" type="button">
              <Heart className="h-3.5 w-3.5" />
              <span className="hidden min-[390px]:inline">Yêu thích</span>
            </button>
          )}
        </div>

        {!isDiscontinued && <div className="mt-2 border-t border-slate-100 pt-2">
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
