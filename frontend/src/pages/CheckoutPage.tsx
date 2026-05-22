import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { apiDb } from '../services/apiDb';

export default function CheckoutPage() {
  const { items, totalPrice, clearCart } = useCart();
  const { user, userData } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [voucherCode, setVoucherCode] = useState('');
  const [discount, setDiscount] = useState(0);
  const [voucherError, setVoucherError] = useState('');
  const [voucherHint, setVoucherHint] = useState('');
  const [shippingFee, setShippingFee] = useState(0);
  const [shippingQuoteNote, setShippingQuoteNote] = useState('');
  const [shippingDetails, setShippingDetails] = useState({
    name: user?.displayName || '',
    phone: '',
    address: '',
  });
  const [shippingError, setShippingError] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'vnpay' | 'momo'>('cash');

  if (items.length === 0) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-20">
        <p className="mb-2 text-2xl font-bold text-gray-800 font-display">Giỏ hàng trống</p>
        <p className="mb-8 text-sm text-gray-500">Hãy thêm sản phẩm vào giỏ hàng trước khi thanh toán.</p>
        <button onClick={() => navigate('/')} className="w-full max-w-sm rounded-xl bg-[#d70018] px-8 py-3.5 text-center font-bold text-white shadow-md transition-colors hover:bg-[#c00015]">
          Quay lại mua sắm
        </button>
      </div>
    );
  }

  const finalPrice = Math.max(0, totalPrice - discount + shippingFee);

  useEffect(() => {
    if (!shippingDetails.address || shippingDetails.address.trim().length < 10) {
      setShippingFee(0);
      setShippingQuoteNote('');
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const quote = await apiDb.quoteShipping({
          shipping_address: shippingDetails.address,
          subtotal_amount: totalPrice,
          item_count: items.reduce((sum, item) => sum + item.quantity, 0),
        });
        setShippingFee(Number(quote.shipping_fee || quote.shippingFee || 0));
        setShippingQuoteNote(quote.note || '');
      } catch {
        setShippingFee(0);
        setShippingQuoteNote('');
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [shippingDetails.address, totalPrice, items]);

  const applyVoucher = async () => {
    if (!voucherCode) return;
    try {
      const deviceId = localStorage.getItem('voucher_device_id') || crypto.randomUUID();
      localStorage.setItem('voucher_device_id', deviceId);
      const voucher = await apiDb.validateVoucher(voucherCode, totalPrice, {
        user_id: user?.uid || null,
        user_tier: userData?.tier || null,
        device_id: deviceId,
        product_ids: items.map((item) => item.productId),
      });
      if (!voucher.valid) {
        setVoucherError(voucher.message || 'Mã ưu đãi không hợp lệ hoặc đã hết hạn.');
        const shortfallAmount = Number(voucher?.metadata?.shortfall_amount || 0);
        setVoucherHint(shortfallAmount > 0 ? `Mua thêm ${shortfallAmount.toLocaleString('vi-VN')}đ để đủ điều kiện áp mã.` : '');
        setDiscount(0);
      } else {
        setDiscount(Number(voucher.discount_amount || voucher.discountAmount || 0));
        setVoucherError('');
        setVoucherHint('');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckout = async () => {
    if (!user) {
      window.alert('Vui lòng đăng nhập để thanh toán!');
      navigate('/login');
      return;
    }
    if (!shippingDetails.name || !shippingDetails.phone || !shippingDetails.address) {
      setShippingError('Vui lòng điền đầy đủ thông tin giao hàng.');
      return;
    }
    setShippingError('');
    setLoading(true);
    try {
      const deviceId = localStorage.getItem('voucher_device_id') || crypto.randomUUID();
      localStorage.setItem('voucher_device_id', deviceId);
      const order = await apiDb.createOrder({
        user_id: user.uid,
        idempotency_key: crypto.randomUUID(),
        items: items.map((item) => ({
          product_id: item.productId,
          product_name: item.name,
          quantity: item.quantity,
          unit_price: item.price,
        })),
        shipping: {
          recipient_name: shippingDetails.name,
          recipient_phone: shippingDetails.phone,
          shipping_address: shippingDetails.address,
        },
        payment_method: paymentMethod === 'cash' ? 'COD' : paymentMethod.toUpperCase(),
        voucher_code: voucherCode || null,
        voucher_device_id: deviceId,
        loyalty_points_used: 0,
      });
      clearCart();
      if (order.checkout_url || order.checkoutUrl) {
        window.location.href = order.checkout_url || order.checkoutUrl;
        return;
      }
      window.alert(`Đặt hàng thành công!\nĐơn hàng #${order.order_code || order.orderCode}\nBạn được cộng ${order.loyalty_points_earned || Math.floor(finalPrice / 10000)} điểm khi đơn hoàn tất.`);
      navigate('/dashboard');
    } catch (err: any) {
      console.error(err);
      window.alert(`Đã có lỗi xảy ra: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-[800px] px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-gray-800">Thanh toán</h1>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-bold text-gray-800">Sản phẩm</h2>
        {items.map((item) => (
          <div key={item.productId} className="flex items-center justify-between border-b border-gray-100 py-2 text-sm last:border-0">
            <div>
              <p className="font-medium">{item.name}</p>
              <p className="text-gray-500">Số lượng: {item.quantity}</p>
            </div>
            <p className="font-bold text-gray-800">{(item.price * item.quantity).toLocaleString('vi-VN')}đ</p>
          </div>
        ))}
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-bold text-gray-800">Thông tin giao hàng</h2>
        <div className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Họ tên</label>
            <input type="text" className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-red-500" value={shippingDetails.name} onChange={(event) => setShippingDetails({ ...shippingDetails, name: event.target.value })} placeholder="Họ và tên người nhận" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Số điện thoại</label>
            <input type="tel" className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-red-500" value={shippingDetails.phone} onChange={(event) => setShippingDetails({ ...shippingDetails, phone: event.target.value })} placeholder="0987654321" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Địa chỉ nhận hàng</label>
            <textarea className="w-full rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-red-500" value={shippingDetails.address} onChange={(event) => setShippingDetails({ ...shippingDetails, address: event.target.value })} placeholder="Số nhà, Tên đường, Phường/Xã, Quận/Huyện, Tỉnh/TP" />
          </div>
          {shippingError && <p className="text-sm text-red-500">{shippingError}</p>}
        </div>
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-bold text-gray-800">Phương thức thanh toán</h2>
        <div className="flex flex-col gap-3">
          <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 transition-colors hover:bg-slate-50">
            <input type="radio" name="payment" value="cash" checked={paymentMethod === 'cash'} onChange={() => setPaymentMethod('cash')} className="h-4 w-4 text-[#d70018] focus:ring-[#d70018]" />
            <div className="flex flex-col">
              <span className="text-sm font-bold text-slate-800">Thanh toán tiền mặt khi nhận hàng (COD)</span>
              <span className="text-xs text-slate-500">Thanh toán bằng tiền mặt khi đơn hàng được giao đến.</span>
            </div>
          </label>

          <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 transition-colors hover:bg-slate-50">
            <input type="radio" name="payment" value="vnpay" checked={paymentMethod === 'vnpay'} onChange={() => setPaymentMethod('vnpay')} className="h-4 w-4 text-[#d70018] focus:ring-[#d70018]" />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div className="hidden h-5 items-center rounded bg-blue-600 px-2 py-0.5 text-[10px] font-black uppercase text-white sm:flex">VNPAY</div>
                <span className="text-sm font-bold text-slate-800">Thanh toán qua VNPAY</span>
              </div>
              <span className="text-xs text-slate-500">Thanh toán an toàn qua cổng VNPAY bằng QR hoặc thẻ ngân hàng sandbox.</span>
            </div>
          </label>

          <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 transition-colors hover:bg-slate-50">
            <input type="radio" name="payment" value="momo" checked={paymentMethod === 'momo'} onChange={() => setPaymentMethod('momo')} className="h-4 w-4 text-[#d70018] focus:ring-[#d70018]" />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div className="hidden h-5 items-center rounded bg-[#a50064] px-2 py-0.5 text-[10px] font-black uppercase text-white sm:flex">MoMo Sandbox</div>
                <span className="text-sm font-bold text-slate-800">Ví MoMo (Sandbox)</span>
              </div>
              <span className="text-xs text-slate-500">Backend sẽ tạo payUrl MoMo sandbox và chuyển bạn sang màn hình thanh toán thử nghiệm.</span>
            </div>
          </label>
        </div>
      </div>

      <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-bold text-gray-800">Khuyến mãi</h2>
        <div className="flex gap-2">
          <input type="text" placeholder="Nhập mã giảm giá..." className="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm uppercase outline-none focus:border-red-500" value={voucherCode} onChange={(event) => setVoucherCode(event.target.value.toUpperCase())} />
          <button onClick={applyVoucher} className="rounded-lg bg-gray-800 px-6 py-2 text-sm font-bold text-white transition-colors hover:bg-gray-900">
            ÁP DỤNG
          </button>
        </div>
        {voucherError && <p className="mt-2 text-xs text-red-500">{voucherError}</p>}
        {voucherHint && <p className="mt-1 text-xs text-amber-600">{voucherHint}</p>}
        {discount > 0 && <p className="mt-2 flex items-center gap-1 font-mono text-xs font-bold text-green-600">Áp dụng mã thành công! Giảm -{discount.toLocaleString('vi-VN')}đ</p>}
      </div>

      <div className="mb-8 rounded-xl bg-white p-6 shadow-sm">
        <div className="mb-2 flex justify-between text-sm text-gray-600">
          <span>Tạm tính:</span>
          <span>{totalPrice.toLocaleString('vi-VN')}đ</span>
        </div>
        <div className="mb-2 flex justify-between text-sm text-gray-600">
          <span>Chiết khấu:</span>
          <span>-{discount.toLocaleString('vi-VN')}đ</span>
        </div>
        <div className="mb-2 flex justify-between text-sm text-gray-600">
          <span>Phí vận chuyển:</span>
          <span>{shippingFee.toLocaleString('vi-VN')}đ</span>
        </div>
        {shippingQuoteNote && <div className="mb-2 text-xs text-slate-500">{shippingQuoteNote}</div>}
        {userData && (
          <div className="mt-2 flex justify-between border-t border-gray-100 pt-2 text-sm font-bold text-blue-600">
            <span>Điểm thưởng tích lũy dự kiến:</span>
            <span>+{Math.floor(finalPrice / 10000)} điểm</span>
          </div>
        )}
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
          <span className="font-bold text-gray-800">Thành tiền:</span>
          <span className="text-2xl font-bold text-[#d70018]">{finalPrice.toLocaleString('vi-VN')}đ</span>
        </div>
      </div>

      <button onClick={handleCheckout} disabled={loading} className="w-full rounded-xl bg-[#d70018] py-4 text-lg font-bold text-white shadow-md transition-colors hover:bg-[#c00015] disabled:bg-red-400">
        {loading ? 'ĐANG XỬ LÝ...' : 'XÁC NHẬN ĐẶT HÀNG'}
      </button>
    </div>
  );
}
