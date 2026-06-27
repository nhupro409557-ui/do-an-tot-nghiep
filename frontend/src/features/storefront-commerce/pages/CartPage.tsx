import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import {
  ArrowLeft,
  ChevronRight,
  Minus,
  PackageCheck,
  Plus,
  ShieldCheck,
  ShoppingBag,
  TicketPercent,
  Trash2,
  Truck,
} from 'lucide-react';
import { useCart } from '../../../context/CartContext';
import { publicApi } from '../../../services/publicApi';

const formatCurrency = (value: number) => `${value.toLocaleString('vi-VN')}đ`;

const EmptyCartIllustration = () => (
  <div className="mb-6 flex h-28 w-28 items-center justify-center rounded-full bg-rose-50 text-[#d70018]">
    <ShoppingBag className="h-12 w-12" strokeWidth={1.8} />
  </div>
);

const CartProductImage: React.FC<{ src: string; alt: string }> = ({ src, alt }) => {
  const [hasError, setHasError] = React.useState(false);

  if (hasError || !src) {
    return (
      <div className="flex h-full w-full items-center justify-center text-slate-300">
        <PackageCheck className="h-8 w-8" strokeWidth={1.6} />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="max-h-full max-w-full object-contain"
      onError={() => setHasError(true)}
    />
  );
};

export default function CartPage() {
  const { items, updateQuantity, removeFromCart, totalPrice, totalQuantity, toggleCheckItem, toggleCheckAll } = useCart();
  const navigate = useNavigate();
  
  // State lưu ngưỡng freeship động lấy từ backend
  const [freeShippingThreshold, setFreeShippingThreshold] = React.useState(3000000); // mặc định 3.000.000đ theo backend
  
  // State lưu sản phẩm gợi ý
  const [suggestedProducts, setSuggestedProducts] = React.useState<any[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = React.useState(true);

  // Gọi API lấy cấu hình phí vận chuyển
  React.useEffect(() => {
    publicApi.getShippingConfig()
      .then((config) => {
        if (config && typeof config.free_shipping_threshold === 'number') {
          setFreeShippingThreshold(config.free_shipping_threshold);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch shipping configuration from backend", err);
      });
  }, []);

  // Gọi API lấy sản phẩm gợi ý mua kèm
  React.useEffect(() => {
    setLoadingSuggestions(true);
    publicApi.listProducts({ limit: 12, featured: true })
      .then((products) => {
        // Lọc bỏ những sản phẩm đã có trong giỏ hàng để tránh gợi ý trùng
        const cartProductIds = new Set(items.map(item => item.productId.replace('-accessory', '').replace('-normal', '')));
        const filtered = products.filter(p => !cartProductIds.has(String(p.id)));
        setSuggestedProducts(filtered.slice(0, 4));
      })
      .catch((err) => {
        console.error("Failed to load product suggestions", err);
      })
      .finally(() => {
        setLoadingSuggestions(false);
      });
  }, [items]);

  const totalAllItemsCount = items.reduce((acc, item) => acc + item.quantity, 0);
  const amountToFreeShipping = Math.max(freeShippingThreshold - totalPrice, 0);
  const freeShippingPercent = Math.min((totalPrice / freeShippingThreshold) * 100, 100);
  const hasFreeShipping = amountToFreeShipping === 0;

  const isAllChecked = items.length > 0 && items.every((item) => item.checked !== false);

  const handleToggleAll = () => {
    toggleCheckAll(!isAllChecked);
  };

  const handleAddSuggestionToCart = (product: any) => {
    useCart().addToCart({
      productId: String(product.id),
      name: product.name,
      price: product.price || product.salePrice,
      imageUrl: product.imageUrl || product.images?.[0] || '',
      quantity: 1,
      originalPrice: product.originalPrice || product.price,
    });
  };

  if (items.length === 0) {
    return (
      <div className="mx-auto flex min-h-[62vh] max-w-lg flex-col items-center justify-center px-4 py-20 text-center">
        <EmptyCartIllustration />
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">Giỏ hàng đang trống</h1>
        <p className="mt-3 max-w-sm text-sm leading-6 text-slate-500">
          Hãy thêm sản phẩm yêu thích vào giỏ để kiểm tra giá, ưu đãi và tiến hành đặt hàng.
        </p>
        <Link
          to="/"
          className="mt-8 inline-flex w-full max-w-xs items-center justify-center gap-2 rounded-lg bg-[#d70018] px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#c00015]"
        >
          Tiếp tục mua sắm
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-0 py-6 sm:px-2 lg:py-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 px-4 sm:px-0">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại
        </button>
        <Link to="/" className="text-sm font-semibold text-[#d70018] hover:text-[#b80014]">
          Mua thêm sản phẩm
        </Link>
      </div>

      <div className="mb-6 rounded-lg border border-rose-100 bg-white p-4 shadow-sm sm:p-5 mx-4 sm:mx-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">Giỏ hàng của bạn</h1>
            <p className="mt-1 text-sm text-slate-500">
              Kiểm tra sản phẩm, số lượng và tạm tính trước khi thanh toán.
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-sm font-bold text-slate-700">
            <ShoppingBag className="h-4 w-4 text-[#d70018]" />
            {totalQuantity} / {totalAllItemsCount} sản phẩm được chọn
          </div>
        </div>

        <div className="mt-5 rounded-lg bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="flex items-center gap-2 font-semibold text-slate-800">
              <Truck className="h-4 w-4 text-emerald-600" />
              {hasFreeShipping ? 'Đơn hàng đã đạt điều kiện miễn phí vận chuyển' : 'Ưu đãi miễn phí vận chuyển'}
            </div>
            <span className="text-xs font-semibold text-slate-500">Mốc {formatCurrency(freeShippingThreshold)}</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
            <div
              className={`h-full rounded-full transition-all duration-500 ${hasFreeShipping ? 'bg-emerald-500' : 'bg-[#d70018]'}`}
              style={{ width: `${freeShippingPercent}%` }}
            />
          </div>
          {!hasFreeShipping && (
            <p className="mt-2 text-xs text-slate-500">
              Mua thêm <strong className="text-slate-900">{formatCurrency(amountToFreeShipping)}</strong> để được miễn phí vận chuyển.
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] px-4 sm:px-0">
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          {/* Header chọn tất cả */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-4 py-3 sm:px-5">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={isAllChecked}
                onChange={handleToggleAll}
                className="h-4.5 w-4.5 rounded border-slate-300 text-[#d70018] focus:ring-[#d70018] cursor-pointer"
                id="checkbox-select-all"
              />
              <label htmlFor="checkbox-select-all" className="text-sm font-bold text-slate-900 cursor-pointer select-none">
                Chọn tất cả ({totalAllItemsCount} sản phẩm)
              </label>
            </div>
          </div>

          <AnimatePresence mode="popLayout">
            {items.map((item) => (
              <motion.article
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.15 } }}
                key={item.cartItemId || item.productId}
                className="grid gap-4 border-b border-slate-100 p-4 last:border-b-0 grid-cols-[auto_80px_1fr] sm:grid-cols-[auto_112px_1fr] items-start sm:p-5"
              >
                {/* Checkbox chọn sản phẩm */}
                <div className="flex h-20 sm:h-28 items-center justify-center shrink-0">
                  <input
                    type="checkbox"
                    checked={item.checked !== false}
                    onChange={() => toggleCheckItem(item.cartItemId || item.productId)}
                    className="h-4.5 w-4.5 rounded border-slate-300 text-[#d70018] focus:ring-[#d70018] cursor-pointer"
                  />
                </div>

                {/* Hình ảnh */}
                <div className="flex h-20 w-20 sm:h-28 sm:w-28 items-center justify-center rounded-lg border border-slate-100 bg-slate-50 p-2 sm:p-3 shrink-0">
                  <CartProductImage src={item.imageUrl || ''} alt={item.name} />
                </div>

                {/* Chi tiết sản phẩm */}
                <div className="min-w-0">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <h3 className="line-clamp-2 text-sm font-bold leading-6 text-slate-900">{item.name}</h3>
                      
                      {/* Dịch vụ đi kèm */}
                      {item.attachedServices && item.attachedServices.length > 0 && (
                        <div className="mt-1.5 space-y-1">
                          {item.attachedServices.map((srv) => (
                            <div key={srv.serviceId} className="flex items-center gap-1.5 text-xs text-blue-600 font-medium">
                              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-blue-500" />
                              <span>{srv.name} (+{formatCurrency(srv.price)})</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Nhãn sản phẩm mua kèm */}
                      {item.isAccessory && (
                        <div className="mt-1.5 flex items-center gap-1.5 text-xs font-bold text-emerald-600">
                          <span className="rounded bg-emerald-50 px-2 py-0.5 border border-emerald-100">
                            🎁 Sản phẩm mua kèm được giảm giá (Số lượng tối đa: 1)
                          </span>
                        </div>
                      )}

                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className="text-base font-extrabold text-[#d70018]">{formatCurrency(item.price)}</span>
                        {item.originalPrice && item.originalPrice > item.price && (
                          <del className="text-sm text-slate-400">{formatCurrency(item.originalPrice)}</del>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeFromCart(item.cartItemId || item.productId)}
                      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-[#d70018] self-start md:self-auto"
                      aria-label="Xóa sản phẩm"
                      title="Xóa sản phẩm"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
                    <div className="inline-flex h-10 items-center overflow-hidden rounded-lg border border-slate-200 bg-white">
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.cartItemId || item.productId, item.quantity - 1)}
                        className="flex h-full w-10 items-center justify-center text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                        aria-label="Giảm số lượng"
                        title="Giảm số lượng"
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <span className="w-12 border-x border-slate-200 text-center text-sm font-bold text-slate-900">
                        {item.quantity}
                      </span>
                      <button
                        type="button"
                        disabled={item.isAccessory}
                        onClick={() => updateQuantity(item.cartItemId || item.productId, item.quantity + 1)}
                        className="flex h-full w-10 items-center justify-center text-slate-500 transition hover:bg-slate-50 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
                        aria-label="Tăng số lượng"
                        title={item.isAccessory ? "Sản phẩm mua kèm giảm giá tối đa là 1" : "Tăng số lượng"}
                      >
                        <Plus className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="text-right">
                      <p className="text-xs text-slate-500">Thành tiền</p>
                      <p className="text-lg font-extrabold text-slate-950">
                        {formatCurrency((item.price + (item.attachedServices?.reduce((sum, s) => sum + s.price, 0) || 0)) * item.quantity)}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </section>

        <aside className="h-fit rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-24">
          <h2 className="text-base font-bold text-slate-900">Tóm tắt đơn hàng</h2>

          <div className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-3 text-slate-600">
              <span>Tạm tính ({totalQuantity} sản phẩm)</span>
              <span className="font-semibold text-slate-900">{formatCurrency(totalPrice)}</span>
            </div>
            <div className="flex justify-between gap-3 text-slate-600">
              <span>Phí vận chuyển</span>
              <span className={hasFreeShipping && totalPrice > 0 ? 'font-bold text-emerald-600' : 'text-slate-500'}>
                {hasFreeShipping && totalPrice > 0 ? 'Miễn phí' : 'Tính khi thanh toán'}
              </span>
            </div>
            <div className="flex justify-between gap-3 text-slate-600">
              <span>Khuyến mãi</span>
              <span className="text-slate-500">Nhập ở bước thanh toán</span>
            </div>
          </div>

          <div className="mt-5 border-t border-slate-100 pt-5">
            <div className="flex items-end justify-between gap-3">
              <span className="font-bold text-slate-900">Tổng tiền</span>
              <span className="text-2xl font-black text-[#d70018]">{formatCurrency(totalPrice)}</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Tổng tiền chưa bao gồm voucher và phí vận chuyển thực tế nếu chưa đạt mốc miễn phí.
            </p>
          </div>

          <button
            type="button"
            disabled={totalQuantity === 0}
            onClick={() => navigate('/checkout')}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-[#d70018] px-5 py-3.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-[#c00015] disabled:bg-slate-300 disabled:cursor-not-allowed disabled:shadow-none"
          >
            Tiến hành đặt hàng
            <ChevronRight className="h-4 w-4" />
          </button>

          <div className="mt-5 grid gap-3 border-t border-slate-100 pt-5 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Thanh toán an toàn qua hệ thống
            </div>
            <div className="flex items-center gap-2">
              <PackageCheck className="h-4 w-4 text-blue-600" />
              Kiểm tra đơn trước khi xác nhận
            </div>
            <div className="flex items-center gap-2">
              <TicketPercent className="h-4 w-4 text-[#d70018]" />
              Có thể áp dụng mã ưu đãi ở bước sau
            </div>
          </div>
        </aside>
      </div>

      {/* Section sản phẩm gợi ý mua thêm */}
      {!loadingSuggestions && suggestedProducts.length > 0 && (
        <div className="mt-8 rounded-lg border border-slate-200 bg-white p-5 shadow-sm mx-4 sm:mx-0">
          <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
            🎁 Gợi ý mua thêm cho bạn
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {suggestedProducts.map((product) => (
              <div
                key={product.id}
                className="group relative flex flex-col rounded-lg border border-slate-100 p-3 transition hover:border-[#d70018] hover:shadow-md bg-white"
              >
                <div className="aspect-square w-full overflow-hidden rounded-md bg-slate-50 flex items-center justify-center p-2">
                  <img
                    src={product.imageUrl || product.images?.[0] || ''}
                    alt={product.name}
                    className="max-h-full max-w-full object-contain transition-transform duration-300 group-hover:scale-105"
                  />
                </div>
                <div className="mt-3 flex flex-1 flex-col justify-between">
                  <div>
                    <h3 className="line-clamp-2 text-xs font-bold text-slate-800 leading-5 group-hover:text-[#d70018]">
                      {product.name}
                    </h3>
                    <div className="mt-2 flex items-baseline gap-1.5 flex-wrap">
                      <span className="text-sm font-extrabold text-[#d70018]">
                        {formatCurrency(product.price || product.salePrice)}
                      </span>
                      {product.originalPrice && product.originalPrice > (product.price || product.salePrice) && (
                        <del className="text-xs text-slate-400">{formatCurrency(product.originalPrice)}</del>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddSuggestionToCart(product)}
                    className="mt-3 flex w-full items-center justify-center rounded bg-slate-100 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-[#d70018] hover:text-white"
                  >
                    Thêm vào giỏ
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
