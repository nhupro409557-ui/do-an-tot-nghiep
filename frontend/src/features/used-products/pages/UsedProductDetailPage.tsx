import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  BatteryCharging,
  Check,
  CircleDollarSign,
  ShieldCheck,
  Smartphone,
  ShoppingCart,
  X,
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
  screen: 'Màn hình và cảm ứng',
  camera: 'Camera',
  connectivity: 'Kết nối và SIM',
  biometric: 'Sinh trắc học',
  accountUnlocked: 'Đã thoát tài khoản và khóa máy',
};

export default function UsedProductDetailPage() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const [item, setItem] = useState<StorefrontUsedProductDetail | null>(null);
  const [activeImage, setActiveImage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
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
    return <div className="mx-auto max-w-7xl py-8"><div className="h-[520px] animate-pulse rounded-lg bg-slate-100" /></div>;
  }
  if (error || !item) {
    return (
      <div className="mx-auto max-w-3xl py-16 text-center">
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
    <div className="mx-auto w-full max-w-7xl py-5 sm:py-8">
      <Link to="/used-products" className="mb-5 inline-flex h-11 items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-950">
        <ArrowLeft className="h-4 w-4" /> Điện thoại cũ
      </Link>

      <div className="grid gap-7 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
        <section aria-label="Ảnh thực tế thiết bị">
          <div className="aspect-square overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            <img src={resolveImageUrl(images[activeImage])} alt={`Ảnh thực tế ${item.title}`} className="h-full w-full object-contain" />
          </div>
          <div className="mt-3 grid grid-cols-5 gap-2 sm:grid-cols-6">
            {images.map((image: string, index: number) => (
              <button
                key={image}
                type="button"
                onClick={() => setActiveImage(index)}
                aria-label={`Xem ảnh thực tế ${index + 1}`}
                aria-pressed={activeImage === index}
                className={`aspect-square overflow-hidden rounded-md border bg-white transition ${activeImage === index ? 'border-emerald-600 ring-2 ring-emerald-100' : 'border-slate-200 hover:border-slate-400'}`}
              >
                <img src={resolveImageUrl(image)} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </section>

        <section>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">Hạng {item.conditionGrade}</span>
            <span className="rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">Đã thẩm định</span>
            <span className="text-xs font-semibold text-slate-500">Mã máy {item.deviceCode}</span>
          </div>
          <h1 className="mt-4 text-2xl font-bold leading-tight text-slate-950 sm:text-3xl">{item.title}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">{item.description}</p>

          <div className="mt-6 border-y border-slate-200 py-5">
            <div className="text-3xl font-bold text-red-700">{currency.format(salePrice)}</div>
            {newPrice > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                <span className="text-slate-500">Giá máy mới: <span className="font-semibold line-through">{currency.format(newPrice)}</span></span>
                <span className="inline-flex items-center gap-1 font-bold text-emerald-700"><CircleDollarSign className="h-4 w-4" /> Tiết kiệm {currency.format(savings)} ({savingsPercent}%)</span>
              </div>
            )}
            {item.priceComparisonNote && <p className="mt-3 text-xs leading-5 text-slate-500">{item.priceComparisonNote}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3 border-b border-slate-200 py-5">
            <div className="flex min-h-16 items-center gap-3 rounded-lg bg-slate-50 px-3">
              <BatteryCharging className="h-6 w-6 text-emerald-600" />
              <div><div className="text-xs font-semibold text-slate-500">Sức khỏe pin</div><div className="font-bold text-slate-900">{item.batteryHealth ?? '-'}%</div></div>
            </div>
            <div className="flex min-h-16 items-center gap-3 rounded-lg bg-slate-50 px-3">
              <ShieldCheck className="h-6 w-6 text-sky-600" />
              <div><div className="text-xs font-semibold text-slate-500">Bảo hành hàng cũ</div><div className="font-bold text-slate-900">{item.warrantyMonths || 0} tháng</div></div>
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={() => addUsedDeviceToCart(true)}
              className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-md bg-red-700 px-4 text-base font-bold text-white transition hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              <ShoppingCart className="h-5 w-5" /> Mua máy này
            </button>
            <button
              type="button"
              onClick={() => addUsedDeviceToCart(false)}
              className="inline-flex h-12 flex-1 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-base font-bold text-slate-800 transition hover:bg-slate-50"
            >
              Thêm vào giỏ
            </button>
            <Link to="/return-warranty-policy" className="inline-flex h-12 flex-1 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-base font-bold text-slate-800 transition hover:bg-slate-50">
              Chính sách đổi trả
            </Link>
          </div>
          <div className="mt-3 text-center text-xs font-semibold text-slate-500">IMEI {item.maskedImei} · Mỗi bài đăng tương ứng một thiết bị duy nhất</div>
        </section>
      </div>

      <div className="mt-10 grid gap-8 border-t border-slate-200 pt-8 lg:grid-cols-2">
        <section>
          <h2 className="text-xl font-bold text-slate-950">Kết quả kiểm tra</h2>
          <div className="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white px-4">
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
        <section>
          <h2 className="text-xl font-bold text-slate-950">Thông số máy gốc</h2>
          <div className="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white px-4">
            {Object.entries(specifications).filter(([, value]) => value !== null && value !== undefined && value !== '').map(([key, value]) => (
              <div key={key} className="grid min-h-12 grid-cols-[minmax(110px,0.7fr)_1.3fr] gap-3 py-3 text-sm">
                <span className="font-semibold text-slate-500">{key}</span>
                <span className="font-semibold text-slate-800">{String(value)}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
