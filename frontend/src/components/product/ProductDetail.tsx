import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { FreeMode, Pagination, Thumbs } from 'swiper/modules';
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Gift,
  Heart,
  ListChecks,
  MessageCircle,
  Minus,
  PackageCheck,
  PlayCircle,
  Plus,
  PlusCircle,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Star,
  Truck,
  X,
  Zap,
} from 'lucide-react';
import { ProductReviews } from './ProductReviews';
import { SuggestedProducts } from './SuggestedProducts';
import { useCart } from '../../context/CartContext';
import { ImageWithFallback } from '../ui/ImageWithFallback';
import 'swiper/css';
import 'swiper/css/free-mode';
import 'swiper/css/pagination';
import 'swiper/css/thumbs';

interface ProductDetailProps {
  product?: any;
}

interface Spec {
  label: string;
  value: string;
  group?: string;
}

interface ProductMediaItem {
  key: string;
  type: 'video' | 'feature' | 'image';
  url: string;
  label: string;
  color?: string;
  poster?: string;
}

const colorFallback: Record<string, string> = {
  den: '#111827',
  'đen': '#111827',
  trang: '#f8fafc',
  'trắng': '#f8fafc',
  xanh: '#8fb7c9',
  do: '#d70018',
  'đỏ': '#d70018',
  vang: '#e7c76f',
  'vàng': '#e7c76f',
  titan: '#c8c0b5',
  bac: '#d1d5db',
  'bạc': '#d1d5db',
};

function formatPrice(value?: number | null) {
  if (!value) return 'Liên hệ';
  return `${value.toLocaleString('vi-VN')}đ`;
}

function asArray(value: any) {
  return Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];
}

function normalizeImages(product: any) {
  const images = product?.images?.length ? product.images : product?.imageUrl ? [product.imageUrl] : [];
  return images.filter(Boolean);
}

function firstVariantImage(variant: any) {
  return variant?.imageUrl || variant?.image || variant?.images?.[0] || null;
}

function buildOptions(product: any, key: string, fallback: any[] = []) {
  const fromVariants = (product.variants || [])
    .map((variant: any) => variant?.specs?.[key] || (key === 'storage' ? variant?.storage : undefined))
    .filter(Boolean);
  return Array.from(new Set([...(fallback || []), ...fromVariants]));
}

function inferSpecGroup(key: string) {
  const normalized = key.toLowerCase();
  if (/(screen|display|màn|man|resolution|refresh|hz|inch)/i.test(normalized)) return 'Màn hình';
  if (/(cpu|chip|processor|ram|storage|rom|gpu|hiệu năng|hieu nang)/i.test(normalized)) return 'Hiệu năng';
  if (/(camera|video|zoom)/i.test(normalized)) return 'Camera';
  if (/(battery|pin|charge|sạc|sac)/i.test(normalized)) return 'Pin & sạc';
  if (/(weight|material|dimension|design|nặng|nang|chất liệu|chat lieu)/i.test(normalized)) return 'Thiết kế';
  if (/(connect|wifi|bluetooth|sim|nfc|network)/i.test(normalized)) return 'Kết nối';
  return 'Thông số khác';
}

function buildMediaItems(product: any): ProductMediaItem[] {
  const items: ProductMediaItem[] = [];
  const seen = new Set<string>();
  const poster = product?.imageUrl || product?.images?.[0] || firstVariantImage(product?.variants?.[0]);

  const add = (item: ProductMediaItem) => {
    if (!item.url || seen.has(`${item.type}:${item.url}`)) return;
    seen.add(`${item.type}:${item.url}`);
    items.push(item);
  };

  if (product?.videoUrl) {
    add({ key: `video-${product.videoUrl}`, type: 'video', url: product.videoUrl, label: 'Video sản phẩm', poster });
  }

  [
    ...asArray(product?.featureImages),
    ...asArray(product?.featuredImages),
    ...asArray(product?.highlightImages),
    ...asArray(product?.featureMedia),
    ...asArray(product?.highlightMedia),
  ].forEach((url: string, index: number) => {
    add({
      key: `feature-${index}-${url}`,
      type: 'feature',
      url,
      label: index === 0 ? 'Tính năng nổi bật' : `Tính năng ${index + 1}`,
    });
  });

  (product?.variants || []).forEach((variant: any) => {
    const image = firstVariantImage(variant);
    const color = variant?.colorName || variant?.specs?.color;
    if (image) {
      add({
        key: `variant-${variant.id || variant.sku || color || image}`,
        type: 'image',
        url: image,
        label: color ? `Màu ${color}` : 'Ảnh biến thể',
        color,
      });
    }
  });

  normalizeImages(product).forEach((url: string, index: number) => {
    add({ key: `image-${index}-${url}`, type: 'image', url, label: index === 0 ? 'Ảnh sản phẩm' : `Ảnh ${index + 1}` });
  });

  return items;
}

function groupSpecs(specs: Spec[]) {
  return specs.reduce<{ title: string; specs: Spec[] }[]>((items, spec) => {
    const title = spec.group?.trim() || 'Thông số khác';
    const existing = items.find((item) => item.title === title);
    if (existing) existing.specs.push(spec);
    else items.push({ title, specs: [spec] });
    return items;
  }, []);
}

function SpecsPreview({ specs, onShowAll }: { specs: Spec[]; onShowAll: () => void }) {
  const previewSpecs = specs.slice(0, 6);
  if (!previewSpecs.length) return null;

  return (
    <section className="overflow-hidden rounded-lg bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <ListChecks className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Thông số kỹ thuật</h2>
      </div>
      <div className="divide-y divide-gray-100">
        {previewSpecs.map((spec, index) => (
          <div
            key={`${spec.group || 'spec'}-${spec.label}-${index}`}
            className={`grid grid-cols-[42%_1fr] gap-3 px-4 py-3 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/80'}`}
          >
            <span className="font-medium text-gray-500">{spec.label}</span>
            <span className="line-clamp-2 font-semibold leading-relaxed text-gray-800">{spec.value}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-gray-100 p-3">
        <button
          onClick={onShowAll}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary bg-white py-2.5 text-sm font-bold text-primary hover:bg-red-50"
        >
          Xem tất cả thông số
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}

function SpecsModal({
  specs,
  activeGroup,
  onSelectGroup,
  onClose,
}: {
  specs: Spec[];
  activeGroup: string;
  onSelectGroup: (group: string) => void;
  onClose: () => void;
}) {
  const groups = groupSpecs(specs);
  const visibleGroups = activeGroup === 'all' ? groups : groups.filter((group) => group.title === activeGroup);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-3 py-5">
      <div className="flex max-h-[92vh] w-full max-w-[900px] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h2 className="text-xl font-bold text-gray-900">Thông số kỹ thuật</h2>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200"
            aria-label="Đóng thông số kỹ thuật"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex gap-5 overflow-x-auto border-b border-gray-200 px-5">
          <button
            onClick={() => onSelectGroup('all')}
            className={`shrink-0 border-b-2 py-3 text-sm font-bold ${activeGroup === 'all' ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
          >
            Tất cả
          </button>
          {groups.map((group) => (
            <button
              key={group.title}
              onClick={() => onSelectGroup(group.title)}
              className={`shrink-0 border-b-2 py-3 text-sm font-bold ${activeGroup === group.title ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
            >
              {group.title}
            </button>
          ))}
        </div>

        <div className="overflow-y-auto px-5 py-4">
          <div className="space-y-6">
            {visibleGroups.map((group) => (
              <section key={group.title}>
                <h3 className="mb-3 text-lg font-bold text-gray-800">{group.title}</h3>
                <div className="overflow-hidden rounded-xl border border-gray-200">
                  {group.specs.map((spec, index) => (
                    <div
                      key={`${group.title}-${spec.label}-${index}`}
                      className="grid grid-cols-[34%_1fr] border-b border-gray-200 text-sm last:border-b-0 sm:text-base"
                    >
                      <div className="bg-gray-100 px-4 py-3 font-medium text-gray-700">{spec.label}</div>
                      <div className="px-4 py-3 leading-relaxed text-gray-700">{spec.value}</div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureHighlights({ product }: { product: any }) {
  const features = useMemo(() => {
    const lines = String(product.description || '')
      .split(/[.\n]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 24);

    const fromSpecs = [
      product.specs?.processor && `Hiệu năng mạnh mẽ với ${product.specs.processor}`,
      product.specs?.screenSize && `Màn hình ${product.specs.screenSize} hiển thị sắc nét`,
      product.specs?.camera && `Camera ${product.specs.camera} hỗ trợ chụp ảnh linh hoạt`,
      product.specs?.battery && `Dung lượng pin ${product.specs.battery} đáp ứng nhu cầu cả ngày`,
    ].filter(Boolean) as string[];

    return (lines.length ? lines : fromSpecs).slice(0, 5);
  }, [product]);

  if (!features.length) return null;

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-bold">Đặc điểm nổi bật</h2>
      <div className="space-y-3">
        {features.map((feature, index) => (
          <div key={feature} className="flex gap-3 text-sm leading-relaxed text-gray-700">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-primary">
              {index + 1}
            </span>
            <span>{feature}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function BundleOffers({ price }: { price: number }) {
  const offers = [
    { name: 'Ốp lưng chống sốc', detail: 'Giảm 20% khi mua cùng sản phẩm', price: 99000 },
    { name: 'Kính cường lực', detail: 'Dán miễn phí tại cửa hàng', price: 79000 },
    { name: 'Củ sạc nhanh chính hãng', detail: 'Ưu đãi thêm khi thanh toán online', price: 290000 },
  ];

  return (
    <section className="rounded-lg bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <Gift className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Ưu đãi mua kèm</h2>
      </div>
      <div className="space-y-2">
        {offers.map((offer) => (
          <label key={offer.name} className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-100 p-3 transition-colors hover:border-red-100 hover:bg-red-50/40">
            <input type="checkbox" className="h-4 w-4 accent-primary" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-bold text-gray-800">{offer.name}</div>
              <div className="text-xs text-gray-500">{offer.detail}</div>
            </div>
            <div className="text-sm font-bold text-primary">{formatPrice(offer.price)}</div>
          </label>
        ))}
      </div>
      <div className="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-xs leading-relaxed text-gray-500">
        Có thể chọn thêm khi mua, tổng tiền sẽ được tính tại giỏ hàng. Giá sản phẩm hiện tại: <span className="font-bold text-gray-800">{formatPrice(price)}</span>
      </div>
    </section>
  );
}

const ProductDetail = ({ product: externalProduct }: ProductDetailProps) => {
  const { addToCart } = useCart();
  const leftColumnRef = useRef<HTMLElement | null>(null);
  const rightColumnRef = useRef<HTMLElement | null>(null);
  const [selectedMediaIndex, setSelectedMediaIndex] = useState(0);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedCapacity, setSelectedCapacity] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [liked, setLiked] = useState(false);
  const [addedToCart, setAddedToCart] = useState(false);
  const [showSpecsModal, setShowSpecsModal] = useState(false);
  const [activeSpecGroup, setActiveSpecGroup] = useState('all');
  const [showMediaViewer, setShowMediaViewer] = useState(false);
  const [mainSwiper, setMainSwiper] = useState<SwiperType | null>(null);
  const [thumbsSwiper, setThumbsSwiper] = useState<SwiperType | null>(null);

  const product = useMemo(() => {
    if (!externalProduct) return null;
    return {
      ...externalProduct,
      images: normalizeImages(externalProduct),
      salePrice: externalProduct.price || externalProduct.salePrice || 0,
      originalPrice: externalProduct.discountPrice || externalProduct.originalPrice || null,
      capacities: buildOptions(externalProduct, 'storage', externalProduct.capacities || []),
      colors: externalProduct.colors || [],
      promotions: externalProduct.promotions?.length
        ? externalProduct.promotions
        : [
            'Giảm thêm khi thanh toán qua ví điện tử hoặc thẻ ngân hàng áp dụng.',
            'Tặng gói bảo hành rơi vỡ trong 30 ngày đầu.',
            'Hỗ trợ thu cũ đổi mới, trợ giá theo tình trạng máy.',
          ],
    };
  }, [externalProduct]);

  const mediaItems = useMemo(() => (product ? buildMediaItems(product) : []), [product]);

  useEffect(() => {
    if (!product) return;
    setSelectedMediaIndex(0);
    setSelectedImage(mediaItems.find((item) => item.type !== 'video')?.url || product.images?.[0] || null);
    setSelectedCapacity(product.capacities?.[0] || '');
    setSelectedColor(product.colors?.[0]?.name || '');
    setQuantity(1);
  }, [product, mediaItems]);

  if (!product) {
    return <div className="mx-auto max-w-7xl px-4 py-16 text-center text-gray-500">Không tìm thấy dữ liệu sản phẩm.</div>;
  }

  const activeVariant = product.variants?.find((variant: any) => {
    const variantSpecs = variant.specs || {};
    if (selectedCapacity && variantSpecs.storage && variantSpecs.storage !== selectedCapacity && variant.storage !== selectedCapacity) return false;
    if (selectedColor) {
      const variantColor = variant.colorName || variantSpecs.color;
      if (variantColor && String(variantColor).toLowerCase() !== selectedColor.toLowerCase()) return false;
    }
    return true;
  });

  const displayPrice = activeVariant?.salePrice || activeVariant?.price || product.salePrice;
  const displayOriginalPrice = activeVariant?.price || product.originalPrice;
  const discount =
    displayOriginalPrice && displayOriginalPrice > displayPrice
      ? Math.round(((displayOriginalPrice - displayPrice) / displayOriginalPrice) * 100)
      : 0;
  const monthlyPrice = displayPrice ? Math.ceil(displayPrice / 12 / 1000) * 1000 : 0;

  const specFieldMap = new Map(
    (product.specFields || []).map((field: any) => [
      field.key,
      {
        label: field.label || field.key,
        group: field.group || inferSpecGroup(field.key || field.label || ''),
      },
    ]),
  );

  const specs: Spec[] = Object.entries(product.specs || {})
    .filter(([key]) => key !== '_variantSpecKeys')
    .map(([key, value]) => {
      const field = specFieldMap.get(key) as { label?: string; group?: string } | undefined;
      return {
        label: field?.label || key,
        value: String(value),
        group: field?.group || inferSpecGroup(key),
      };
    });

  const routeWheelScroll = (target: HTMLElement, deltaY: number) => {
    const { scrollTop, scrollHeight, clientHeight } = target;
    const maxScrollTop = Math.max(0, scrollHeight - clientHeight);

    if (maxScrollTop <= 0) {
      window.scrollBy(0, deltaY);
      return;
    }

    const nextScrollTop = Math.min(maxScrollTop, Math.max(0, scrollTop + deltaY));
    const consumedDelta = nextScrollTop - scrollTop;
    const remainingDelta = deltaY - consumedDelta;

    if (consumedDelta !== 0) {
      target.scrollTop = nextScrollTop;
    }

    if (remainingDelta !== 0) {
      window.scrollBy(0, remainingDelta);
    }
  };

  const handleDesktopColumnWheel = (event: React.WheelEvent<HTMLElement>) => {
    if (window.innerWidth < 1024) return;
    event.preventDefault();
    routeWheelScroll(event.currentTarget, event.deltaY);
  };

  const selectMedia = (index: number) => {
    if (!mediaItems.length) return;
    const boundedIndex = (index + mediaItems.length) % mediaItems.length;
    const item = mediaItems[boundedIndex];
    setSelectedMediaIndex(boundedIndex);
    if (item.type !== 'video') setSelectedImage(item.url);
    mainSwiper?.slideTo(boundedIndex);
    thumbsSwiper?.slideTo(Math.max(0, boundedIndex - 2));
  };

  const selectColor = (colorName: string) => {
    setSelectedColor(colorName);
    const variant = product.variants?.find((item: any) => {
      const variantColor = item?.colorName || item?.specs?.color;
      return variantColor && String(variantColor).toLowerCase() === String(colorName).toLowerCase();
    });
    const image = firstVariantImage(variant);
    if (!image) return;
    const targetIndex = mediaItems.findIndex((item) => item.url === image);
    setSelectedImage(image);
    if (targetIndex >= 0) selectMedia(targetIndex);
  };

  const closeMediaViewer = () => {
    setShowMediaViewer(false);
    document.body.style.overflow = '';
  };

  const openMediaViewer = (index: number) => {
    selectMedia(index);
    setShowMediaViewer(true);
    document.body.style.overflow = 'hidden';
  };

  const viewMedia = (index: number) => {
    selectMedia(index);
  };

  useEffect(() => {
    if (!showMediaViewer) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMediaViewer();
      if (event.key === 'ArrowLeft') viewMedia(selectedMediaIndex - 1);
      if (event.key === 'ArrowRight') viewMedia(selectedMediaIndex + 1);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [showMediaViewer, selectedMediaIndex]);

  const handleAddToCart = () => {
    addToCart({
      productId: product.id,
      name: [product.name, selectedCapacity, selectedColor].filter(Boolean).join(' - '),
      price: displayPrice,
      imageUrl: selectedImage || product.images[0],
      quantity,
      originalPrice: displayOriginalPrice,
    });
    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 1800);
  };

  const handleBuyNow = () => {
    handleAddToCart();
    window.location.href = '/checkout';
  };

  const fallbackImage = product.images?.[0] || firstVariantImage(product.variants?.[0]) || undefined;
  return (
    <div className="bg-background pb-24 md:pb-8">
      <div className="mx-auto max-w-[1200px] px-3 py-3 sm:px-4">
        <nav className="mb-3 flex items-center gap-1 overflow-hidden text-sm text-gray-500">
          <Link to="/" className="shrink-0 hover:text-primary">Trang chủ</Link>
          <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
          {product.category && (
            <>
              <Link to={`/products/${product.categorySlug || ''}`} className="shrink-0 hover:text-primary">
                {product.category}
              </Link>
              <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
            </>
          )}
          <span className="truncate font-medium text-gray-700">{product.name}</span>
        </nav>

        <div className="mb-3 rounded-lg bg-white px-4 py-3 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-xl font-bold leading-snug text-gray-900 md:text-2xl">{product.name}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-gray-500">
                <span className="flex items-center gap-1 font-semibold text-amber-500">
                  {[...Array(5)].map((_, index) => (
                    <Star key={index} className={`h-4 w-4 ${index < Math.round(product.rating || 4.8) ? 'fill-amber-400' : 'text-gray-300'}`} />
                  ))}
                  <span>{product.rating || 4.8}</span>
                </span>
                <span>{product.reviewCount || 0} đánh giá</span>
                <span className="hidden text-gray-300 sm:inline">|</span>
                <span>Đã bán {product.soldCount || 128}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <button onClick={() => setLiked(!liked)} className={`flex h-10 items-center gap-1.5 rounded-lg border px-3 font-bold ${liked ? 'border-red-200 bg-red-50 text-primary' : 'border-gray-200 text-blue-600 hover:text-primary'}`}>
                <Heart className={`h-5 w-5 ${liked ? 'fill-primary' : ''}`} />
                <span>Yêu thích</span>
              </button>
              <a href="#product-reviews" className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-blue-600 hover:text-primary">
                <MessageCircle className="h-5 w-5" />
                <span>Hỏi đáp</span>
              </a>
              <button
                onClick={() => {
                  setActiveSpecGroup('all');
                  setShowSpecsModal(true);
                }}
                className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-blue-600 hover:text-primary"
              >
                <ListChecks className="h-5 w-5" />
                <span>Thông số</span>
              </button>
              <Link to={`/compare?product=${product.id}`} className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-blue-600 hover:text-primary">
                <PlusCircle className="h-5 w-5" />
                <span>So sánh</span>
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          <aside
            ref={leftColumnRef}
            onWheel={handleDesktopColumnWheel}
            className="hide-scrollbar lg:max-h-[calc(100vh-1.5rem)] lg:overflow-y-auto lg:[scrollbar-gutter:stable]"
          >
            <div className="space-y-3">
              <div className="group/main-media relative overflow-hidden rounded-2xl bg-white shadow-sm">
                {discount > 0 && (
                  <span className="absolute left-3 top-3 z-20 rounded-lg bg-primary px-2 py-1 text-xs font-bold text-white">
                    Giảm {discount}%
                  </span>
                )}

                {mediaItems.length > 1 && (
                  <>
                    <button onClick={() => selectMedia(selectedMediaIndex - 1)} className="absolute left-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100" aria-label="Ảnh trước">
                      <ChevronLeft className="h-5 w-5" />
                    </button>
                    <button onClick={() => selectMedia(selectedMediaIndex + 1)} className="absolute right-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100" aria-label="Ảnh sau">
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </>
                )}

                <Swiper
                  modules={[Pagination, Thumbs]}
                  onSwiper={setMainSwiper}
                  onSlideChange={(swiper) => {
                    const item = mediaItems[swiper.activeIndex];
                    if (!item) return;
                    setSelectedMediaIndex(swiper.activeIndex);
                    if (item.type !== 'video') setSelectedImage(item.url);
                    thumbsSwiper?.slideTo(Math.max(0, swiper.activeIndex - 2));
                  }}
                  thumbs={{ swiper: thumbsSwiper && !thumbsSwiper.destroyed ? thumbsSwiper : null }}
                  pagination={{ clickable: true }}
                  className="product-main-swiper"
                >
                  {mediaItems.map((item, index) => (
                    <SwiperSlide key={item.key}>
                      <div
                        className="relative flex aspect-square cursor-pointer items-center justify-center overflow-hidden bg-white p-4"
                        onClick={() => openMediaViewer(index)}
                        onMouseEnter={() => {
                          const next = mediaItems[index + 1];
                          if (next?.type !== 'video' && next?.url) {
                            const image = new Image();
                            image.src = next.url;
                          }
                        }}
                      >
                        {item.type === 'video' ? (
                          <video
                            src={item.url}
                            poster={item.poster}
                            controls
                            preload={index === 0 ? 'metadata' : 'none'}
                            className="max-h-full w-full bg-black object-contain"
                            onClick={(event) => event.stopPropagation()}
                          />
                        ) : (
                          <ImageWithFallback
                            src={item.url}
                            fallbackSrc={fallbackImage}
                            alt={product.name}
                            loading={index === 0 ? 'eager' : 'lazy'}
                            decoding="async"
                            className="h-auto max-h-full w-full object-contain"
                          />
                        )}
                      </div>
                    </SwiperSlide>
                  ))}
                </Swiper>
              </div>

              {mediaItems.length > 1 && (
                <div className="group relative rounded-lg bg-white p-2 shadow-sm">
                  <button onClick={() => selectMedia(selectedMediaIndex - 1)} className="absolute left-2 top-1/2 z-10 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-lg ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex" aria-label="Ảnh con trước">
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <Swiper modules={[FreeMode, Thumbs]} onSwiper={setThumbsSwiper} freeMode watchSlidesProgress slidesPerView="auto" spaceBetween={8} className="product-thumbs-swiper">
                    {mediaItems.map((item, index) => (
                      <SwiperSlide key={`thumb-${item.key}`} className="!h-[74px] !w-[82px]">
                        <button
                          data-media-index={index}
                          onClick={() => selectMedia(index)}
                          className={`relative flex h-full w-full items-center justify-center overflow-hidden rounded-lg border p-1 transition-all ${selectedMediaIndex === index ? 'border-primary ring-1 ring-primary' : 'border-gray-200 opacity-70 hover:border-gray-400 hover:opacity-100'}`}
                          aria-label={item.label}
                        >
                          {item.type === 'video' ? (
                            <>
                              {item.poster ? <ImageWithFallback src={item.poster} fallbackSrc={fallbackImage} alt="" loading="lazy" className="h-full w-full object-contain opacity-80" /> : <PlayCircle className="h-8 w-8 text-primary" />}
                              <span className="absolute inset-0 flex items-center justify-center bg-black/10"><PlayCircle className="h-6 w-6 text-white drop-shadow" /></span>
                            </>
                          ) : (
                            <ImageWithFallback src={item.url} fallbackSrc={fallbackImage} alt="" loading="lazy" className="h-full w-full object-contain" />
                          )}
                        </button>
                      </SwiperSlide>
                    ))}
                  </Swiper>
                  <button onClick={() => selectMedia(selectedMediaIndex + 1)} className="absolute right-2 top-1/2 z-10 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-lg ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex" aria-label="Ảnh con sau">
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 rounded-lg bg-white p-3 text-sm shadow-sm">
                {[
                  [ShieldCheck, 'Máy mới 100%', 'Chính hãng, nguyên seal'],
                  [RotateCcw, 'Đổi trả 7 ngày', 'Theo chính sách cửa hàng'],
                  [Truck, 'Giao nhanh 2 giờ', 'Nội thành áp dụng'],
                  [PackageCheck, 'Bảo hành 12 tháng', 'Tại trung tâm uỷ quyền'],
                ].map(([Icon, title, desc]: any) => (
                  <div key={title} className="flex gap-2 rounded-lg border border-gray-100 p-2">
                    <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                    <div>
                      <div className="font-bold text-gray-800">{title}</div>
                      <div className="text-xs leading-snug text-gray-500">{desc}</div>
                    </div>
                  </div>
                ))}
              </div>

              <SpecsPreview
                specs={specs}
                onShowAll={() => {
                  setActiveSpecGroup('all');
                  setShowSpecsModal(true);
                }}
              />
            </div>
          </aside>

          <main
            ref={rightColumnRef}
            onWheel={handleDesktopColumnWheel}
            className="hide-scrollbar space-y-3 lg:max-h-[calc(100vh-1.5rem)] lg:overflow-y-auto lg:[scrollbar-gutter:stable]"
          >
            <section className="rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-3 rounded-lg border border-red-100 bg-red-50 p-3">
                <div className="flex flex-wrap items-end gap-2">
                  <span className="text-3xl font-extrabold text-primary">{formatPrice(displayPrice)}</span>
                  {displayOriginalPrice && displayOriginalPrice > displayPrice && (
                    <span className="pb-1 text-base font-medium text-gray-400 line-through">
                      {formatPrice(displayOriginalPrice)}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-sm text-gray-600">
                  Trả góp từ <span className="font-bold text-gray-900">{formatPrice(monthlyPrice)}/tháng</span> qua thẻ hoặc công ty tài chính.
                </div>
              </div>

              {product.capacities.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-bold text-gray-800">Phiên bản</div>
                  <div className="grid grid-cols-3 gap-2">
                    {product.capacities.map((capacity: string) => (
                      <button
                        key={capacity}
                        onClick={() => setSelectedCapacity(capacity)}
                        className={`relative rounded-lg border px-3 py-4 text-sm font-bold ${selectedCapacity === capacity ? 'border-primary bg-red-50 text-primary' : 'border-gray-200 text-gray-700'}`}
                      >
                        {selectedCapacity === capacity && <Check className="absolute right-2 top-2 h-3.5 w-3.5" />}
                        {capacity}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {product.colors.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-bold text-gray-800">Màu sắc: <span className="font-semibold text-primary">{selectedColor}</span></div>
                  <div className="grid grid-cols-2 gap-2">
                    {product.colors.map((color: any) => {
                      const colorCode = color.code || colorFallback[String(color.name).toLowerCase()] || '#e5e7eb';
                      return (
                        <button
                          key={color.name}
                          onClick={() => selectColor(color.name)}
                          className={`relative flex items-center gap-3 rounded-lg border px-4 py-4 text-left ${selectedColor === color.name ? 'border-primary bg-red-50' : 'border-gray-200'}`}
                        >
                          <span className="h-7 w-7 shrink-0 rounded-full border border-gray-200" style={{ backgroundColor: colorCode }} />
                          <span className="text-sm font-bold text-gray-800">{color.name}</span>
                          {selectedColor === color.name && <Check className="ml-auto h-4 w-4 text-primary" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>

            <section className="overflow-hidden rounded-lg border border-red-200 bg-white shadow-sm">
              <div className="flex items-center gap-2 bg-primary px-4 py-2.5 text-white">
                <Gift className="h-5 w-5" />
                <h2 className="text-base font-bold text-white">Khuyến mãi</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {product.promotions.map((promotion: string, index: number) => (
                  <div key={`${promotion}-${index}`} className="flex gap-3 px-4 py-3 text-sm text-gray-700">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">
                      {index + 1}
                    </span>
                    <span>{promotion}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-bold">Số lượng</h2>
                <div className="flex overflow-hidden rounded-lg border border-gray-200">
                  <button onClick={() => setQuantity(Math.max(1, quantity - 1))} className="flex h-9 w-9 items-center justify-center text-gray-600">
                    <Minus className="h-4 w-4" />
                  </button>
                  <div className="flex h-9 w-10 items-center justify-center border-x border-gray-200 text-sm font-bold">{quantity}</div>
                  <button onClick={() => setQuantity(quantity + 1)} className="flex h-9 w-9 items-center justify-center text-gray-600">
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-[1fr_58px] gap-2">
                <button onClick={handleBuyNow} className="rounded-lg bg-primary px-4 py-3 text-center text-white shadow-sm hover:bg-red-700">
                  <span className="block text-base font-extrabold">MUA NGAY</span>
                  <span className="block text-xs font-medium opacity-90">Giao tận nơi hoặc nhận tại cửa hàng</span>
                </button>
                <button
                  onClick={handleAddToCart}
                  className={`flex items-center justify-center rounded-lg border-2 ${addedToCart ? 'border-green-500 bg-green-50 text-green-600' : 'border-primary text-primary hover:bg-red-50'}`}
                  title="Thêm vào giỏ hàng"
                >
                  {addedToCart ? <Check className="h-6 w-6" /> : <ShoppingCart className="h-6 w-6" />}
                </button>
              </div>
              <button className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-bold text-blue-700">
                <Zap className="h-4 w-4" />
                Mua trả góp 0%
              </button>
            </section>

            <BundleOffers price={displayPrice} />
          </main>
        </div>

        <div className="mt-4 space-y-4">
          <FeatureHighlights product={product} />
          {product.description && (
            <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-bold">Thông tin sản phẩm</h2>
              <p className="whitespace-pre-line text-sm leading-7 text-gray-700">{product.description}</p>
            </section>
          )}
        </div>

        <SuggestedProducts currentProductId={product.id} category={product.categorySlug} />
        <div id="product-reviews">
          <ProductReviews productId={product.id} />
        </div>
      </div>

      <div className="fixed bottom-[56px] left-0 right-0 z-[49] border-t border-gray-200 bg-white p-3 shadow-[0_-4px_16px_rgba(0,0,0,0.08)] md:hidden">
        <div className="flex items-center gap-2">
          <button onClick={handleAddToCart} className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${addedToCart ? 'border-green-400 bg-green-50 text-green-600' : 'border-primary text-primary'}`}>
            {addedToCart ? <Check className="h-5 w-5" /> : <ShoppingCart className="h-5 w-5" />}
          </button>
          <button onClick={handleBuyNow} className="flex flex-1 flex-col items-center rounded-lg bg-primary py-2 text-white">
            <span className="text-sm font-extrabold">MUA NGAY</span>
            <span className="text-xs font-semibold opacity-90">{formatPrice(displayPrice)}</span>
          </button>
        </div>
      </div>

      {showSpecsModal && (
        <SpecsModal
          specs={specs}
          activeGroup={activeSpecGroup}
          onSelectGroup={setActiveSpecGroup}
          onClose={() => setShowSpecsModal(false)}
        />
      )}

      {showMediaViewer && mediaItems[selectedMediaIndex] && (
        <div className="fixed inset-0 z-[100] flex flex-col bg-black/95">
          <div className="flex h-14 items-center justify-between px-4 text-white">
            <div className="text-sm font-semibold">
              {selectedMediaIndex + 1} / {mediaItems.length}
            </div>
            <button
              onClick={closeMediaViewer}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/20"
              aria-label="Đóng xem ảnh"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 pb-5">
            {mediaItems.length > 1 && (
              <button
                onClick={() => viewMedia(selectedMediaIndex - 1)}
                className="absolute left-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh trước"
              >
                <ChevronLeft className="h-7 w-7" />
              </button>
            )}

            {mediaItems[selectedMediaIndex].type === 'video' ? (
              <video
                src={mediaItems[selectedMediaIndex].url}
                poster={mediaItems[selectedMediaIndex].poster}
                controls
                autoPlay
                className="max-h-[82vh] max-w-full bg-black object-contain"
              />
            ) : (
              <ImageWithFallback
                src={mediaItems[selectedMediaIndex].url}
                fallbackSrc={fallbackImage}
                alt={product.name}
                className="max-h-[82vh] max-w-full object-contain"
              />
            )}

            {mediaItems.length > 1 && (
              <button
                onClick={() => viewMedia(selectedMediaIndex + 1)}
                className="absolute right-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh sau"
              >
                <ChevronRight className="h-7 w-7" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductDetail;
