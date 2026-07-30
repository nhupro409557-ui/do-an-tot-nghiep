import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  BatteryCharging,
  BadgeCheck,
  Check,
  CircleDollarSign,
  ClipboardCheck,
  PackageCheck,
  ShieldCheck,
  Sparkles,
  Smartphone,
  ShoppingCart,
  ZoomIn,
  X,
  ChevronLeft,
  ChevronRight,
  Info
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { resolveImageUrl } from '../../../services/productMedia';
import { useCart } from '../../../context/CartContext';
import { usedProductsApi } from '../services/usedProductsApi';
import type { StorefrontUsedProductDetail } from '../types';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

const checklistLabels: Record<string, string> = {
  imeiVerified: 'IMEI trên máy khớp hồ sơ',
  screen: 'Màn hình và cảm ứng',
  camera: 'Camera',
  connectivity: 'Kết nối và SIM',
  biometric: 'Sinh trắc học',
  accountUnlocked: 'Đã thoát tài khoản và khóa máy',
  dataErased: 'Đã xóa dữ liệu cá nhân',
  charging: 'Sạc và cổng kết nối',
  audioAndButtons: 'Loa, mic và phím vật lý',
};

const GradeTooltip = ({ grade }: { grade: string }) => {
  const info: Record<string, string> = {
    'A': 'Máy đẹp như mới, hầu như không xước xát, pin tốt, mọi chức năng hoàn hảo.',
    'B': 'Máy có dấu hiệu sử dụng, xước nhẹ, chức năng hoạt động tốt hoàn toàn.',
    'C': 'Máy có cấn móp nhẹ hoặc xước nhiều, chức năng ổn định, giá tốt.'
  };
  return (
    <button type="button" className="group relative ml-1 inline-flex items-center justify-center focus:outline-none">
      <Info className="h-4 w-4 text-slate-400 hover:text-slate-200" />
      <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-64 -translate-x-1/2 rounded bg-slate-800 p-2 text-xs font-normal text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus:opacity-100">
        {info[grade] || 'Hàng cũ đã qua sử dụng'}
        <div className="absolute left-1/2 top-full -mt-1 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
      </div>
    </button>
  );
};

export default function UsedProductDetailPage() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const [item, setItem] = useState<StorefrontUsedProductDetail | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lightboxOpen, setLightboxOpen] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    void usedProductsApi.detail(slug).then((result) => {
      if (!active) return;
      setItem(result);
      setActiveImage(0);
    }).catch((requestError: unknown) => {
      const message = requestError instanceof Error ? requestError.message : 'Không thể tải thông tin thiết bị cũ.';
      if (active) setError(message);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [slug]);

  useEffect(() => {
    if (!lightboxOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setLightboxOpen(false);
      if (e.key === 'ArrowLeft') setActiveImage((prev) => (prev > 0 ? prev - 1 : (item?.images?.length || 1) - 1));
      if (e.key === 'ArrowRight') setActiveImage((prev) => (prev < (item?.images?.length || 1) - 1 ? prev + 1 : 0));
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxOpen, item?.images?.length]);

  const specifications = useMemo(() => {
    const snapshot = item?.originalSnapshot || {};
    return {
      ...(snapshot.productSpecs || {}),
      ...(snapshot.variantSpecs || {}),
      Màu: snapshot.colorName,
      'Bộ nhớ': snapshot.storage,
      RAM: snapshot.ram,
      'Cấu hình': snapshot.configuration,
    };
  }, [item]);

  if (loading) {
    return <div className="min-h-screen bg-slate-50 px-4 py-8"><div className="mx-auto h-[620px] max-w-7xl animate-pulse rounded-[2rem] bg-white shadow-sm" /></div>;
  }
  if (error || !item) {
    return (
      <div className="mx-auto my-12 max-w-3xl rounded-[2rem] border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
        <Smartphone className="mx-auto h-10 w-10 text-slate-400" />
        <h1 className="mt-4 text-xl font-bold text-slate-900">Không tìm thấy thiết bị</h1>
        <p role="alert" className="mt-2 text-sm text-slate-600">{error || 'Thiết bị không còn được đăng bán.'}</p>
        <Link to="/used-products" className="mt-5 inline-flex h-11 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-bold text-white"><ArrowLeft className="h-4 w-4" /> Quay lại hàng cũ</Link>
      </div>
    );
  }

  const images = item.images || [];
  const snapshot = item.originalSnapshot || {};
  const newPrice = Number(snapshot.newReferencePrice || 0);
  const salePrice = Number(item.salePrice || 0);
  const savings = Math.max(0, newPrice - salePrice);
  const savingsPercent = newPrice > 0 ? Math.round((savings / newPrice) * 100) : 0;
  const primaryImage = images[0] || '';
  const addUsedDeviceToCart = (goCheckout = false) => {
    addToCart({
      productId: String(item.productId || item.deviceCode),
      usedDeviceId: item.deviceId,
      cartItemId: `used-${item.deviceId}`,
      isUsedDevice: true,
      name: item.title,
      price: salePrice,
      originalPrice: newPrice || undefined,
      imageUrl: resolveImageUrl(primaryImage),
      quantity: 1,
      checked: true,
    });
    if (goCheckout) {
      navigate('/checkout');
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.08),_transparent_28%),linear-gradient(to_bottom,_#f8fafc,_#ffffff_45%)] px-4 pb-16 pt-5 sm:px-6 sm:pt-8 lg:px-8">
      <div className="mx-auto w-full max-w-7xl">
      <Link to="/used-products" className="mb-5 inline-flex h-11 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-bold text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500">
        <ArrowLeft className="h-4 w-4" /> Quay lại hàng cũ
      </Link>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(390px,0.88fr)] lg:items-start xl:gap-10">
        <section aria-label="Ảnh thực tế thiết bị" className="lg:sticky lg:top-24">
          <div 
            className="group relative aspect-square cursor-zoom-in overflow-hidden rounded-[2rem] border border-slate-800 bg-[radial-gradient(circle_at_50%_42%,_#334155,_#0f172a_68%)] shadow-2xl shadow-slate-900/15"
            onClick={() => setLightboxOpen(true)}
          >
            <div className="absolute left-4 top-4 z-10 inline-flex items-center gap-2 rounded-full border border-white/15 bg-slate-950/60 px-3 py-1.5 text-xs font-bold text-white backdrop-blur-md">
              <BadgeCheck className="h-4 w-4 text-emerald-400" /> Ảnh máy thực tế
            </div>
            <div className="absolute right-4 top-4 z-10 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold text-white/90 backdrop-blur-md">
              <ZoomIn className="h-3.5 w-3.5" /> Phóng to
            </div>
            <img src={resolveImageUrl(images[activeImage])} alt={`Ảnh thực tế ${item.title}`} className="h-full w-full object-contain p-6 transition-transform duration-300 group-hover:scale-[1.03] sm:p-10" />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/65 to-transparent px-5 pb-5 pt-16 text-sm font-semibold text-white/80">
              Ảnh {activeImage + 1}/{Math.max(images.length, 1)} · Nhấn để xem toàn màn hình
            </div>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-2 sm:gap-3">
            {images.map((image: string, index: number) => (
              <button
                key={image}
                type="button"
                onClick={() => setActiveImage(index)}
                aria-label={`Xem ảnh thực tế ${index + 1}`}
                aria-pressed={activeImage === index}
                className={`h-20 w-20 shrink-0 overflow-hidden rounded-2xl border bg-white p-1.5 shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 sm:h-24 sm:w-24 ${activeImage === index ? 'border-emerald-500 ring-2 ring-emerald-100' : 'border-slate-200 hover:border-slate-400'}`}
              >
                <img src={resolveImageUrl(image)} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white p-5 shadow-xl shadow-slate-900/[0.06] sm:p-7 lg:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-slate-950 px-3 py-1.5 text-xs font-bold text-white">
              Hạng {item.conditionGrade}
              <GradeTooltip grade={item.conditionGrade || ''} />
            </span>
            {item.conditionScore && (
              <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-700">Điểm: {item.conditionScore}/100</span>
            )}
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700"><BadgeCheck className="h-3.5 w-3.5" /> Đã thẩm định</span>
          </div>
          <div className="mt-5 text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Thiết bị độc bản · {item.deviceCode}</div>
          <h1 className="mt-2 text-3xl font-black leading-[1.15] tracking-tight text-slate-950 sm:text-4xl">{item.title}</h1>
          <p className="mt-4 text-[15px] leading-7 text-slate-600">{item.description}</p>
          
          {item.highlights && item.highlights.length > 0 && (
            <ul className="mt-5 grid gap-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
              {item.highlights.map((hl, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  <span>{hl}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-6 rounded-3xl border border-rose-100 bg-gradient-to-br from-rose-50 to-white p-5">
            <div className="text-xs font-bold uppercase tracking-wider text-rose-500">Giá bán thiết bị này</div>
            <div className="mt-1 text-4xl font-black tracking-tight text-rose-700">{currency.format(salePrice)}</div>
            {newPrice > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                <span className="text-slate-500">Giá máy mới: <span className="font-semibold line-through">{currency.format(newPrice)}</span></span>
                <span className="inline-flex items-center gap-1 font-bold text-emerald-700"><CircleDollarSign className="h-4 w-4" /> Tiết kiệm {currency.format(savings)} ({savingsPercent}%)</span>
              </div>
            )}
            {item.priceComparisonNote && <p className="mt-3 text-xs leading-5 text-slate-500">{item.priceComparisonNote}</p>}
          </div>

          <div className={`mt-4 grid gap-3 ${item.manufacturerWarrantyEnabled ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-2'}`}>
            <div className="flex min-h-20 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4">
              <BatteryCharging className="h-6 w-6 text-emerald-600" />
              <div><div className="text-xs font-semibold text-slate-500">Sức khỏe pin</div><div className="font-bold text-slate-900">{item.batteryHealth ?? '-'}%</div></div>
            </div>
            {item.manufacturerWarrantyEnabled && (
              <div className="flex min-h-20 items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/60 px-4">
                <ShieldCheck className="h-6 w-6 text-emerald-600" />
                <div>
                  <div className="text-xs font-semibold text-slate-500">Bảo hành chính hãng</div>
                  <div className="font-bold text-slate-900">Còn {item.manufacturerWarrantyRemainingMonths || 0} tháng</div>
                  <div className="text-xs text-slate-500">Đến {item.manufacturerWarrantyExpiresAt || '-'}</div>
                </div>
              </div>
            )}
            <div className="flex min-h-20 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4">
              <ShieldCheck className="h-6 w-6 text-sky-600" />
              <div><div className="text-xs font-semibold text-slate-500">Bảo hành hàng cũ</div><div className="font-bold text-slate-900">{item.warrantyMonths || 0} tháng</div></div>
            </div>
          </div>

          <div className="mt-5 grid gap-2 sm:grid-cols-[1.15fr_0.85fr]">
            <button
              type="button"
              onClick={() => addUsedDeviceToCart(true)}
              className="inline-flex h-14 items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 text-base font-bold text-white shadow-lg shadow-slate-950/20 transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
            >
              <ShoppingCart className="h-5 w-5" /> Mua máy này
            </button>
            <button
              type="button"
              onClick={() => addUsedDeviceToCart(false)}
              className="inline-flex h-14 items-center justify-center rounded-2xl border border-slate-300 bg-white px-4 text-base font-bold text-slate-800 transition hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            >
              Thêm vào giỏ
            </button>
          </div>
          
          <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
            <h3 className="flex items-center gap-2 text-sm font-extrabold text-emerald-950"><ShieldCheck className="h-5 w-5 text-emerald-600" /> An tâm mua sắm hàng cũ</h3>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-emerald-950/75">
              <li className="flex gap-2"><ClipboardCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> Máy đã qua quy trình kiểm định chất lượng.</li>
              <li className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> Bảo hành riêng cho máy này: {item.warrantyMonths || 0} tháng.</li>
              {item.manufacturerWarrantyEnabled && <li className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> Bảo hành chính hãng còn {item.manufacturerWarrantyRemainingMonths || 0} tháng, đến {item.manufacturerWarrantyExpiresAt || '-'}.</li>}
              <li className="flex gap-2"><PackageCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> Áp dụng đổi trả theo chính sách hiện hành.</li>
            </ul>
            <Link to="/return-warranty-policy" className="mt-2 inline-block text-xs font-semibold text-sky-600 hover:underline">
              Xem chi tiết chính sách đổi trả &rarr;
            </Link>
          </div>

          <div className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-center text-xs font-semibold text-slate-500"><Sparkles className="h-3.5 w-3.5 text-amber-500" /> IMEI {item.maskedImei} · Mỗi bài đăng là một thiết bị duy nhất</div>
        </section>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <section className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="flex items-center gap-2 text-xl font-black text-slate-950"><ClipboardCheck className="h-6 w-6 text-emerald-600" /> Kết quả kiểm tra</h2>
          <p className="mt-2 text-sm text-slate-500">Tình trạng được ghi nhận trực tiếp trong lần QC gần nhất.</p>
          <div className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white px-4">
            {Object.entries(item.inspectionChecklist || {}).map(([key, value]) => (
              <div key={key} className="flex min-h-12 items-center justify-between gap-3 py-3">
                <span className="text-sm font-semibold text-slate-700">{checklistLabels[key] || key}</span>
                <span className={`inline-flex items-center gap-1 text-sm font-bold ${value ? 'text-emerald-700' : 'text-red-700'}`}>
                  {value ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />} {value ? 'Đạt' : 'Chưa đạt'}
                </span>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="flex items-center gap-2 text-xl font-black text-slate-950"><Smartphone className="h-6 w-6 text-sky-600" /> Thông số máy gốc</h2>
          <p className="mt-2 text-sm text-slate-500">Thông tin tham chiếu từ sản phẩm và cấu hình ban đầu.</p>
          <div className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white px-4">
            {Object.entries(specifications).filter(([, value]) => value !== null && value !== undefined && value !== '').map(([key, value]) => (
              <div key={key} className="grid min-h-12 grid-cols-[minmax(110px,0.7fr)_1.3fr] gap-3 py-3 text-sm">
                <span className="font-semibold text-slate-500">{key}</span>
                <span className="font-semibold text-slate-800">{String(value)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      {lightboxOpen && (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-slate-950/95 p-4 backdrop-blur-md sm:p-8" role="dialog" aria-modal="true" aria-label="Xem ảnh thiết bị toàn màn hình">
          <button 
            type="button" aria-label="Đóng ảnh toàn màn hình" className="absolute right-4 top-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            onClick={() => setLightboxOpen(false)}
          >
            <X className="h-6 w-6" />
          </button>
          
          <button 
            type="button" aria-label="Xem ảnh trước" className="absolute left-3 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white sm:left-6"
            onClick={() => setActiveImage(activeImage > 0 ? activeImage - 1 : images.length - 1)}
          >
            <ChevronLeft className="h-8 w-8" />
          </button>
          
          <img 
            src={resolveImageUrl(images[activeImage])} 
            alt={`Ảnh thực tế ${activeImage + 1} của ${item.title}`}
            className="max-h-[86vh] max-w-[88vw] rounded-2xl object-contain" 
          />
          
          <button 
            type="button" aria-label="Xem ảnh tiếp theo" className="absolute right-3 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white sm:right-6"
            onClick={() => setActiveImage(activeImage < images.length - 1 ? activeImage + 1 : 0)}
          >
            <ChevronRight className="h-8 w-8" />
          </button>
          
          <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2">
            {images.map((_, i) => (
              <div key={i} className={`h-2 w-2 rounded-full ${i === activeImage ? 'bg-white' : 'bg-white/30'}`} />
            ))}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
