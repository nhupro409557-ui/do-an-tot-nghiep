import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, CreditCard, MapPin, PackageCheck, Plus, ShieldCheck, Tag } from 'lucide-react';
import { useCart } from '../../../context/CartContext';
import { useAuth } from '../../../context/AuthContext';
import { updateUserProfile } from '../../../services/authDb';
import { VietnamAddressSelector, type AddressData } from '../../shipping/components/VietnamAddressSelector';
import type { AccountAddress } from '../../account/types/accountDashboardTypes';
import { adminOrdersApi } from '../../admin-orders/services/adminOrdersApi';
import { adminVouchersApi } from '../../admin-vouchers/services/adminVouchersApi';
import { adminPaymentMethodsApi, type PaymentMethodData } from '../../admin-payment-methods/services/adminPaymentMethodsApi';

const emptyAddressData: AddressData = {
  provinceId: '',
  provinceName: '',
  districtId: '',
  districtName: '',
  wardId: '',
  wardName: '',
  street: '',
};

const formatCurrency = (value: number) => `${value.toLocaleString('vi-VN')}đ`;

const getVoucherDeviceId = () => {
  const existingDeviceId = localStorage.getItem('voucher_device_id');
  if (existingDeviceId) return existingDeviceId;
  const deviceId = crypto.randomUUID();
  localStorage.setItem('voucher_device_id', deviceId);
  return deviceId;
};

const CheckoutProductImage: React.FC<{ src: string; alt: string }> = ({ src, alt }) => {
  const [hasError, setHasError] = useState(false);

  if (hasError || !src) {
    return (
      <div className="flex h-full w-full items-center justify-center text-slate-300">
        <PackageCheck className="h-6 w-6" strokeWidth={1.6} />
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

const mapDbCodeToClientMethod = (code: string): 'cash' | 'momo' | 'zalopay' | 'sepay' | 'vnpay' => {
  switch (code) {
    case 'COD': return 'cash';
    case 'MOMO': return 'momo';
    case 'ZALOPAY': return 'zalopay';
    case 'SEPAY': return 'sepay';
    case 'VNPAY': return 'vnpay';
    default: return 'cash';
  }
};

const formatMaintenanceTime = (startsAtStr: string | null, endsAtStr: string | null): string => {
  if (!startsAtStr || !endsAtStr) return '';
  try {
    const startsAt = new Date(startsAtStr);
    const endsAt = new Date(endsAtStr);

    const pad = (num: number) => String(num).padStart(2, '0');
    const formatTime = (date: Date) => `${pad(date.getHours())}:${pad(date.getMinutes())}`;
    const formatDate = (date: Date) => `${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;

    if (startsAt.toDateString() === endsAt.toDateString()) {
      return `(Dự kiến từ ${formatTime(startsAt)} đến ${formatTime(endsAt)} ngày ${formatDate(startsAt)})`;
    }

    return `(Dự kiến từ ${formatTime(startsAt)} ngày ${formatDate(startsAt)} đến ${formatTime(endsAt)} ngày ${formatDate(endsAt)})`;
  } catch (err) {
    console.error('Error formatting maintenance window', err);
    return '';
  }
};

export default function CheckoutPage() {
  const { items, totalPrice, clearCheckedItems } = useCart();
  const checkedItems = useMemo(
    () => items.filter(item => item.checked !== false),
    [items],
  );
  const { user, userData } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [voucherCode, setVoucherCode] = useState('');
  const [appliedVoucherCode, setAppliedVoucherCode] = useState('');
  const [discount, setDiscount] = useState(0);
  const [voucherError, setVoucherError] = useState('');
  const [voucherHint, setVoucherHint] = useState('');
  const [isValidatingVoucher, setIsValidatingVoucher] = useState(false);
  const [shippingQuote, setShippingQuote] = useState({ fee: 0, note: '' });
  const shippingQuoteRequestIdRef = useRef(0);
  const voucherValidationIdRef = useRef(0);
  const validatedVoucherContextRef = useRef('');
  const { fee: shippingFee, note: shippingQuoteNote } = shippingQuote;
  const [shippingDetails, setShippingDetails] = useState({
    name: user?.displayName || '',
    phone: '',
    address: '',
  });
  const addresses = useMemo(
    () => (userData?.addresses || []) as AccountAddress[],
    [userData?.addresses],
  );
  const [selectedAddressId, setSelectedAddressId] = useState('');
  const [isAddingAddress, setIsAddingAddress] = useState(false);
  const [newAddress, setNewAddress] = useState({
    receiverName: user?.displayName || '',
    receiverPhone: '',
    addressData: emptyAddressData,
    note: '',
  });
  const [addressFormError, setAddressFormError] = useState('');
  const [shippingError, setShippingError] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'vnpay' | 'momo' | 'zalopay' | 'sepay'>('cash');
  const [dbPaymentMethods, setDbPaymentMethods] = useState<PaymentMethodData[]>([]);
  const totalQuantity = checkedItems.reduce((sum, item) => sum + item.quantity, 0);

  useEffect(() => {
    let isActive = true;
    const fetchPaymentMethods = async () => {
      try {
        const methods = await adminPaymentMethodsApi.listStorefrontPaymentMethods();
        if (!isActive) return;
        setDbPaymentMethods(methods);

        // Nếu phương thức COD (cash) mặc định bị bảo trì, chuyển sang phương thức khả dụng đầu tiên
        const codMethod = methods.find(m => m.code === 'COD');
        if (codMethod && !codMethod.is_available) {
          const firstAvailable = methods.find(m => m.is_available);
          if (firstAvailable) {
            setPaymentMethod(mapDbCodeToClientMethod(firstAvailable.code));
          }
        }
      } catch (err) {
        console.error('Failed to fetch payment methods', err);
      }
    };
    void fetchPaymentMethods();
    return () => {
      isActive = false;
    };
  }, []);
  const finalPrice = Math.max(0, totalPrice - discount + shippingFee);
  const checkoutPaymentMethod = (method: typeof paymentMethod = paymentMethod) => method === 'cash' ? 'COD' : method.toUpperCase();

  useEffect(() => {
    if (!user) return;
    if (addresses.length === 0) return;
    if (selectedAddressId && addresses.some(address => address.id === selectedAddressId)) return;
    const preferredAddress = addresses.find(address => address.isDefault) || addresses[0];
    setSelectedAddressId(preferredAddress.id);
    setShippingDetails({
      name: preferredAddress.receiverName,
      phone: preferredAddress.receiverPhone,
      address: preferredAddress.addressLine,
    });
  }, [addresses, selectedAddressId, user]);

  useEffect(() => {
    const requestId = shippingQuoteRequestIdRef.current + 1;
    shippingQuoteRequestIdRef.current = requestId;
    if (!shippingDetails.address || shippingDetails.address.trim().length < 10) {
      setShippingQuote({ fee: 0, note: '' });
      return;
    }
    const selectedAddress = addresses.find(address => address.id === selectedAddressId);
    let isActive = true;
    const timer = window.setTimeout(async () => {
      try {
        const quote = await adminOrdersApi.quoteShipping({
          shipping_address: shippingDetails.address,
          subtotal_amount: totalPrice,
          item_count: checkedItems.reduce((sum, item) => sum + item.quantity, 0),
          lat: selectedAddress?.lat,
          lng: selectedAddress?.lng,
        });
        if (!isActive || shippingQuoteRequestIdRef.current !== requestId) return;
        setShippingQuote({
          fee: Number(quote.shipping_fee || quote.shippingFee || 0),
          note: quote.note || '',
        });
      } catch {
        if (isActive && shippingQuoteRequestIdRef.current === requestId) {
          setShippingQuote({ fee: 0, note: '' });
        }
      }
    }, 300);
    return () => {
      isActive = false;
      window.clearTimeout(timer);
    };
  }, [addresses, checkedItems, selectedAddressId, shippingDetails.address, totalPrice]);

  const voucherProductKey = checkedItems
    .map((item) => `${item.usedDeviceId || item.productId}:${item.quantity}:${item.price}`)
    .join('|');

  const voucherContext = (code: string, method: typeof paymentMethod) => [
    code,
    method,
    totalPrice,
    user?.uid || '',
    userData?.tier || '',
    voucherProductKey,
  ].join('::');

  const applyVoucher = async (
    method: typeof paymentMethod = paymentMethod,
    code: string = voucherCode,
  ) => {
    const normalizedCode = code.trim().toUpperCase();
    if (!normalizedCode) return;
    setIsValidatingVoucher(true);
    const validationId = voucherValidationIdRef.current + 1;
    voucherValidationIdRef.current = validationId;
    const context = voucherContext(normalizedCode, method);
    try {
      const deviceId = getVoucherDeviceId();
      const voucher = await adminVouchersApi.validateVoucher(normalizedCode, totalPrice, {
        user_id: user?.uid || null,
        user_tier: userData?.tier || null,
        device_id: deviceId,
        payment_method: checkoutPaymentMethod(method),
        channel: 'WEB',
        product_ids: checkedItems.map((item) => item.productId.replace('-accessory', '').replace('-normal', '')),
      });
      if (voucherValidationIdRef.current !== validationId) return;
      if (!voucher.valid) {
        setAppliedVoucherCode('');
        validatedVoucherContextRef.current = '';
        setVoucherError(voucher.message || 'Mã ưu đãi không hợp lệ hoặc đã hết hạn.');
        const shortfallAmount = Number(voucher?.metadata?.shortfall_amount || 0);
        setVoucherHint(shortfallAmount > 0 ? `Mua thêm ${formatCurrency(shortfallAmount)} để đủ điều kiện áp mã.` : '');
        setDiscount(0);
      } else {
        setAppliedVoucherCode(normalizedCode);
        validatedVoucherContextRef.current = context;
        setDiscount(Number(voucher.discount_amount || voucher.discountAmount || 0));
        setVoucherError('');
        setVoucherHint('');
      }
    } catch (err) {
      if (voucherValidationIdRef.current !== validationId) return;
      console.error(err);
      setAppliedVoucherCode('');
      validatedVoucherContextRef.current = '';
      setVoucherError('Không thể kiểm tra mã ưu đãi. Vui lòng thử lại.');
      setVoucherHint('');
      setDiscount(0);
    } finally {
      if (voucherValidationIdRef.current === validationId) {
        setIsValidatingVoucher(false);
      }
    }
  };
  const applyVoucherRef = useRef(applyVoucher);
  applyVoucherRef.current = applyVoucher;

  const changePaymentMethod = (method: typeof paymentMethod) => {
    setPaymentMethod(method);
    if (appliedVoucherCode) void applyVoucher(method, appliedVoucherCode);
  };

  const changeVoucherCode = (code: string) => {
    voucherValidationIdRef.current += 1;
    validatedVoucherContextRef.current = '';
    setVoucherCode(code.toUpperCase());
    setAppliedVoucherCode('');
    setDiscount(0);
    setVoucherError('');
    setVoucherHint('');
  };

  const removeVoucher = () => {
    voucherValidationIdRef.current += 1;
    validatedVoucherContextRef.current = '';
    setVoucherCode('');
    setAppliedVoucherCode('');
    setDiscount(0);
    setVoucherError('');
    setVoucherHint('');
  };

  const appliedVoucherContext = appliedVoucherCode
    ? voucherContext(appliedVoucherCode, paymentMethod)
    : '';

  useEffect(() => {
    if (!appliedVoucherCode) return;
    if (validatedVoucherContextRef.current === appliedVoucherContext) return;
    void applyVoucherRef.current(paymentMethod, appliedVoucherCode);
  }, [appliedVoucherCode, appliedVoucherContext, paymentMethod]);

  useEffect(() => {
    if (totalPrice <= 0) return;
    const savedVoucher = localStorage.getItem('selectedVoucherCode');
    if (savedVoucher) {
      localStorage.removeItem('selectedVoucherCode');
      setVoucherCode(savedVoucher.toUpperCase());
      void applyVoucherRef.current(paymentMethod, savedVoucher);
    }
  }, [totalPrice, paymentMethod]);

  const selectSavedAddress = (address: AccountAddress) => {
    setSelectedAddressId(address.id);
    setIsAddingAddress(false);
    setAddressFormError('');
    setShippingError('');
    setShippingDetails({
      name: address.receiverName,
      phone: address.receiverPhone,
      address: address.addressLine,
    });
  };

  const saveNewAddress = () => {
    if (!user) return;
    const receiverName = newAddress.receiverName.trim();
    const receiverPhone = newAddress.receiverPhone.trim();
    const { addressData } = newAddress;
    const addressLine = [
      addressData.street,
      addressData.wardName,
      addressData.districtName,
      addressData.provinceName,
    ].filter(Boolean).join(', ');

    if (receiverName.length < 2) {
      setAddressFormError('Tên người nhận phải có ít nhất 2 ký tự.');
      return;
    }
    if (receiverPhone.length < 8) {
      setAddressFormError('Số điện thoại phải có ít nhất 8 ký tự.');
      return;
    }
    if (!addressData.provinceId || !addressData.districtId || !addressData.wardId || !addressData.street.trim()) {
      setAddressFormError('Vui lòng chọn đầy đủ tỉnh/thành phố, quận/huyện, phường/xã và nhập địa chỉ cụ thể.');
      return;
    }

    const savedAddress: AccountAddress = {
      id: crypto.randomUUID(),
      receiverName,
      receiverPhone,
      addressLine,
      addressData,
      note: newAddress.note.trim(),
      isDefault: addresses.length === 0,
      isMapVerified: false,
    };
    updateUserProfile(user.uid, { addresses: [...addresses, savedAddress] });
    selectSavedAddress(savedAddress);
    setNewAddress({
      receiverName: user.displayName || '',
      receiverPhone: '',
      addressData: emptyAddressData,
      note: '',
    });
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
    if (shippingDetails.name.trim().length < 2) {
      setShippingError('Tên người nhận phải có ít nhất 2 ký tự.');
      return;
    }
    if (shippingDetails.phone.trim().length < 8) {
      setShippingError('Số điện thoại phải có ít nhất 8 ký tự.');
      return;
    }
    if (shippingDetails.address.trim().length < 10) {
      setShippingError('Địa chỉ giao hàng phải có ít nhất 10 ký tự.');
      return;
    }
    setShippingError('');
    setLoading(true);
    try {
      const deviceId = getVoucherDeviceId();
      const selectedAddress = addresses.find(address => address.id === selectedAddressId);
      const order = await adminOrdersApi.createOrder({
        user_id: user.uid,

        idempotency_key: crypto.randomUUID(),
        items: checkedItems.map((item) => {
          let name = item.name;
          let price = item.price;
          if (item.attachedServices && item.attachedServices.length > 0) {
            const servicesText = item.attachedServices.map(s => `${s.name} (+${s.price.toLocaleString('vi-VN')}đ)`).join(', ');
            name = `${item.name} [Dịch vụ: ${servicesText}]`;
            price = item.price + item.attachedServices.reduce((sum, s) => sum + s.price, 0);
          }
          return {
            product_id: item.isUsedDevice ? null : item.productId.replace('-accessory', '').replace('-normal', ''),
            variant_id: item.isUsedDevice ? null : item.variantId || null,
            used_device_id: item.usedDeviceId || null,
            product_name: name,
            quantity: item.isUsedDevice ? 1 : item.quantity,
            unit_price: price,
            attached_services: (item.attachedServices || []).map((s: any) => ({
              service_id: s.serviceId || s.service_id || s.id,
              code: s.code,
              name: s.name,
              price: s.price,
            })),
          };
        }),
        shipping: {
          recipient_name: shippingDetails.name,
          recipient_phone: shippingDetails.phone,
          shipping_address: shippingDetails.address,
          lat: selectedAddress?.lat,
          lng: selectedAddress?.lng,
        },

        payment_method: checkoutPaymentMethod(),
        voucher_code: appliedVoucherCode || null,
        voucher_device_id: deviceId,
        loyalty_points_used: 0,
      });
      clearCheckedItems();
      const paymentTransactionId = order.payment_transaction_id || order.paymentTransactionId;
      if (paymentTransactionId) {
        navigate(`/payment/${paymentTransactionId}`);
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

  if (checkedItems.length === 0) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-4 py-20 text-center">
        <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <PackageCheck className="h-10 w-10" strokeWidth={1.7} />
        </div>
        <h1 className="text-2xl font-extrabold text-slate-950">Giỏ hàng trống</h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          Hãy thêm sản phẩm vào giỏ hàng trước khi thực hiện thanh toán.
        </p>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="mt-8 w-full max-w-xs rounded-lg bg-[#d70018] px-6 py-3 text-sm font-bold text-white transition hover:bg-[#c00015]"
        >
          Quay lại mua sắm
        </button>
      </div>
    );
  }

  return (
    <div className="bg-slate-50 py-6 lg:py-8">
      <div className="mx-auto max-w-7xl px-0 sm:px-2">
        <div className="mb-5 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate('/cart')}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Giỏ hàng
          </button>
          <div className="text-right">
            <h1 className="text-xl font-extrabold text-slate-950 sm:text-2xl">Đặt hàng</h1>
            <p className="mt-1 text-xs text-slate-500">{totalQuantity} sản phẩm</p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-4 sm:px-5">
                <div className="flex items-center gap-3">
                  <MapPin className="h-5 w-5 text-[#d70018]" />
                  <h2 className="font-bold text-slate-950">Địa chỉ nhận hàng</h2>
                </div>
                {addresses.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setIsAddingAddress(value => !value)}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
                  >
                    {!isAddingAddress && <Plus className="h-3.5 w-3.5" />}
                    {isAddingAddress ? 'Đóng' : 'Thêm mới'}
                  </button>
                )}
              </div>

              <div className="p-4 sm:p-5">
                {addresses.length === 0 && !isAddingAddress && (
                  <div className="text-center py-8 px-4 border border-dashed border-slate-300 rounded-xl bg-slate-50/50">
                    <p className="text-slate-600 text-sm mb-4">
                      Bạn chưa có địa chỉ nhận hàng. Vui lòng thêm địa chỉ để tiếp tục đặt hàng.
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => setIsAddingAddress(true)}
                        className="inline-flex items-center gap-2 rounded-lg bg-[#d70018] px-5 py-2.5 text-sm font-bold text-white transition hover:bg-[#c00015] shadow-sm"
                      >
                        <Plus className="h-4 w-4" />
                        Thêm địa chỉ tại đây
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate('/dashboard?tab=addresses&action=new&redirect=/checkout')}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 shadow-sm"
                      >
                        Đến trang cá nhân
                      </button>
                    </div>
                  </div>
                )}

                {addresses.length > 0 && (
                  <div className="grid gap-3 md:grid-cols-2">
                    {addresses.map(address => {
                      const isSelected = selectedAddressId === address.id && !isAddingAddress;
                      return (
                        <button
                          type="button"
                          key={address.id}
                          onClick={() => selectSavedAddress(address)}
                          className={`rounded-lg border p-4 text-left transition ${
                            isSelected
                              ? 'border-[#d70018] bg-rose-50/50'
                              : 'border-slate-200 bg-white hover:border-slate-300'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="font-bold text-slate-900">{address.receiverName}</p>
                              <p className="mt-1 text-sm text-slate-600">{address.receiverPhone}</p>
                            </div>
                            {isSelected && <Check className="h-5 w-5 shrink-0 text-[#d70018]" />}
                          </div>
                          <p className="mt-2 line-clamp-2 text-sm leading-5 text-slate-500">{address.addressLine}</p>
                          {address.isDefault && (
                            <span className="mt-3 inline-flex rounded bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600">
                              Mặc định
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}

                {isAddingAddress && (
                  <div className={addresses.length > 0 ? 'mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4' : ''}>
                    {addresses.length === 0 && (
                      <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                        Bạn chưa có địa chỉ nhận hàng. Vui lòng thêm địa chỉ để tiếp tục.
                      </p>
                    )}
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="block">
                        <span className="mb-1 block text-sm font-semibold text-slate-700">Người nhận</span>
                        <input
                          type="text"
                          value={newAddress.receiverName}
                          onChange={event => setNewAddress({ ...newAddress, receiverName: event.target.value })}
                          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-[#d70018]"
                          placeholder="Họ và tên"
                        />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-sm font-semibold text-slate-700">Số điện thoại</span>
                        <input
                          type="tel"
                          value={newAddress.receiverPhone}
                          onChange={event => setNewAddress({ ...newAddress, receiverPhone: event.target.value })}
                          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-[#d70018]"
                          placeholder="Số điện thoại"
                        />
                      </label>
                      <div className="md:col-span-2">
                        <span className="mb-2 block text-sm font-semibold text-slate-700">Địa chỉ</span>
                        <VietnamAddressSelector
                          value={newAddress.addressData}
                          onChange={addressData => setNewAddress({ ...newAddress, addressData })}
                        />
                      </div>
                      <label className="block md:col-span-2">
                        <span className="mb-1 block text-sm font-semibold text-slate-700">Ghi chú</span>
                        <input
                          type="text"
                          value={newAddress.note}
                          onChange={event => setNewAddress({ ...newAddress, note: event.target.value })}
                          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-[#d70018]"
                          placeholder="Không bắt buộc"
                        />
                      </label>
                    </div>
                    {addressFormError && <p className="mt-3 text-sm font-semibold text-red-600">{addressFormError}</p>}
                    <div className="mt-4 flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setIsAddingAddress(false)}
                        className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-white"
                      >
                        Hủy
                      </button>
                      <button
                        type="button"
                        onClick={saveNewAddress}
                        className="rounded-lg bg-[#d70018] px-4 py-2.5 text-sm font-bold text-white transition hover:bg-[#c00015]"
                      >
                        Lưu địa chỉ
                      </button>
                    </div>
                  </div>
                )}

                {!isAddingAddress && selectedAddressId && (
                  <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                    Giao đến <strong className="text-slate-900">{shippingDetails.name}</strong>, số điện thoại{' '}
                    <strong className="text-slate-900">{shippingDetails.phone}</strong>.
                  </div>
                )}
                {shippingError && <p className="mt-3 text-sm font-semibold text-red-600">{shippingError}</p>}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-4 sm:px-5">
                <CreditCard className="h-5 w-5 text-[#d70018]" />
                <h2 className="font-bold text-slate-950">Thanh toán</h2>
              </div>

              <div className="grid gap-3 p-4 sm:p-5 md:grid-cols-2">
                {(dbPaymentMethods.length > 0 ? dbPaymentMethods : [
                  { id: '1', code: 'COD', name: 'Thanh toán khi nhận hàng', description: 'Khách hàng thanh toán bằng tiền mặt khi nhận hàng.', is_available: true, maintenance_message: null, maintenance_starts_at: null, maintenance_ends_at: null },
                  { id: '2', code: 'MOMO', name: 'Ví MoMo Sandbox', description: 'Cổng thanh toán thử nghiệm qua ví điện tử MoMo.', is_available: true, maintenance_message: null, maintenance_starts_at: null, maintenance_ends_at: null },
                  { id: '3', code: 'ZALOPAY', name: 'Ví ZaloPay Sandbox', description: 'Cổng thanh toán thử nghiệm qua ví điện tử ZaloPay.', is_available: true, maintenance_message: null, maintenance_starts_at: null, maintenance_ends_at: null },
                  { id: '4', code: 'VNPAY', name: 'Cổng VNPAY', description: 'Cổng thanh toán điện tử VNPAY.', is_available: false, maintenance_message: 'Phương thức VNPAY tạm thời chưa được hỗ trợ.', maintenance_starts_at: null, maintenance_ends_at: null },
                ]).map(method => {
                  const clientVal = mapDbCodeToClientMethod(method.code);
                  const isSelected = paymentMethod === clientVal;
                  const isAvailable = method.is_available !== false;

                  if (!isAvailable) {
                    const timeInfo = formatMaintenanceTime(method.maintenance_starts_at, method.maintenance_ends_at);
                    return (
                      <label
                        key={method.code}
                        className="flex cursor-not-allowed gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 opacity-60"
                        title={method.maintenance_message || "Phương thức này đang tạm khóa."}
                      >
                        <input
                          type="radio"
                          name="payment"
                          value={clientVal}
                          checked={isSelected}
                          disabled
                          readOnly
                          className="mt-1 h-4 w-4"
                        />
                        <div className="flex-1">
                          <span className="block text-sm font-bold text-slate-700">{method.name}</span>
                          <span className="mt-1 block text-xs leading-5 text-slate-500">{method.description}</span>
                          {(method.maintenance_message || timeInfo) && (
                            <span className="mt-1.5 block text-xs font-semibold text-red-600">
                              ⚠️ {method.maintenance_message || "Phương thức đang bảo trì."} {timeInfo}
                            </span>
                          )}
                        </div>
                      </label>
                    );
                  }

                  return (
                    <label
                      key={method.code}
                      className={`flex cursor-pointer gap-3 rounded-lg border p-4 transition ${
                        isSelected
                          ? 'border-[#d70018] bg-rose-50/50'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="payment"
                        value={clientVal}
                        checked={isSelected}
                        onChange={() => changePaymentMethod(clientVal)}
                        className="mt-1 h-4 w-4 text-[#d70018] focus:ring-[#d70018]"
                      />
                      <div>
                        <span className="block text-sm font-bold text-slate-900">{method.name}</span>
                        <span className="mt-1 block text-xs leading-5 text-slate-500">{method.description}</span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className="mb-4 flex items-center gap-3">
                <Tag className="h-5 w-5 text-[#d70018]" />
                <h2 className="font-bold text-slate-950">Mã giảm giá</h2>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  aria-label="Mã giảm giá"
                  type="text"
                  placeholder="Nhập mã giảm giá"
                  className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2.5 text-sm uppercase outline-none transition focus:border-[#d70018] disabled:bg-slate-50"
                  value={voucherCode}
                  disabled={isValidatingVoucher}
                  onChange={(event) => changeVoucherCode(event.target.value)}
                />
                <button
                  type="button"
                  disabled={isValidatingVoucher || !voucherCode.trim()}
                  onClick={() => applyVoucher()}
                  className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-slate-800 disabled:opacity-50"
                >
                  {isValidatingVoucher ? 'Đang áp dụng...' : 'Áp dụng'}
                </button>
              </div>
              {voucherError && <p className="mt-2 text-sm font-semibold text-red-600">{voucherError}</p>}
              {voucherHint && <p className="mt-2 text-sm font-semibold text-amber-600">{voucherHint}</p>}
              {discount > 0 && (
                <div className="mt-2 flex items-center justify-between rounded-lg bg-emerald-50 p-2.5">
                  <p className="text-sm font-semibold text-emerald-700">
                    Đã áp dụng mã. Giảm {formatCurrency(discount)}.
                  </p>
                  <button
                    type="button"
                    onClick={removeVoucher}
                    className="text-xs font-bold text-red-600 hover:text-red-800 transition"
                  >
                    Hủy áp dụng
                  </button>
                </div>
              )}
            </section>
          </div>

          <aside className="h-fit rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-24">
            <h2 className="text-base font-bold text-slate-950">Tóm tắt đơn hàng</h2>

            <div className="mt-4 max-h-72 space-y-3 overflow-y-auto pr-1">
              {checkedItems.map((item) => (
                <div key={item.cartItemId || item.productId} className="flex gap-3">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-slate-100 bg-slate-50 p-2">
                    <CheckoutProductImage src={item.imageUrl} alt={item.name} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-sm font-semibold leading-5 text-slate-900">{item.name}</p>

                    {/* Dịch vụ đi kèm */}
                    {item.attachedServices && item.attachedServices.length > 0 && (
                      <div className="mt-1 space-y-0.5">
                        {item.attachedServices.map((srv) => (
                          <div key={srv.serviceId} className="flex items-center gap-1 text-[10px] text-blue-600 font-medium">
                            <ShieldCheck className="h-3 w-3 shrink-0 text-blue-500" />
                            <span>{srv.name} (+{formatCurrency(srv.price)})</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Nhãn sản phẩm mua kèm */}
                    {item.isAccessory && (
                      <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-emerald-600">
                        <span className="rounded bg-emerald-50 px-1.5 py-0.2 border border-emerald-100">
                          🎁 Mua kèm giảm giá
                        </span>
                      </div>
                    )}
                    {item.isUsedDevice && (
                      <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-emerald-700">
                        <span className="rounded bg-emerald-50 px-1.5 py-0.5">
                          Hàng cũ đã thẩm định
                        </span>
                      </div>
                    )}

                    <p className="mt-1 text-xs text-slate-500">{formatCurrency(item.price)} x {item.quantity}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 space-y-3 border-t border-slate-100 pt-5 text-sm">
              <div className="flex justify-between gap-3 text-slate-600">
                <span>Tạm tính</span>
                <span className="font-semibold text-slate-900">{formatCurrency(totalPrice)}</span>
              </div>
              <div className="flex justify-between gap-3 text-slate-600">
                <span>Giảm giá</span>
                <span className={discount > 0 ? 'font-semibold text-emerald-600' : 'text-slate-500'}>
                  {discount > 0 ? `-${formatCurrency(discount)}` : '0đ'}
                </span>
              </div>
              <div className="flex justify-between gap-3 text-slate-600">
                <span>Vận chuyển</span>
                <span className="font-semibold text-slate-900">{formatCurrency(shippingFee)}</span>
              </div>
              {shippingQuoteNote && (
                <p className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-500">{shippingQuoteNote}</p>
              )}
              {userData && (
                <div className="flex justify-between gap-3 text-xs text-slate-500">
                  <span>Điểm dự kiến</span>
                  <span className="font-bold text-emerald-600">+{Math.floor(finalPrice / 10000)} điểm</span>
                </div>
              )}
            </div>

            <div className="mt-5 border-t border-slate-100 pt-5">
              <div className="flex items-end justify-between gap-3">
                <span className="font-bold text-slate-950">Cần thanh toán</span>
                <span className="text-2xl font-black text-[#d70018]">{formatCurrency(finalPrice)}</span>
              </div>
              <button
                type="button"
                onClick={handleCheckout}
                disabled={loading}
                className="mt-5 w-full rounded-lg bg-[#d70018] px-5 py-3.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-[#c00015] disabled:bg-red-300"
              >
                {loading ? 'Đang xử lý...' : 'Xác nhận đặt hàng'}
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
