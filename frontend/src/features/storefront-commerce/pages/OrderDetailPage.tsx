import { useEffect, useReducer, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { customerCenterApi } from '../../account/services/customerCenterApi';
import { adminOrdersApi } from '../../admin-orders/services/adminOrdersApi';

const statusLabels: Record<string, string> = {
  PENDING: 'Chờ xử lý',
  PROCESSING: 'Đang xử lý',
  SHIPPED: 'Đang giao hàng',
  COMPLETED: 'Hoàn tất',
  CANCELLED: 'Đã hủy',
  PAYMENT_FAILED: 'Thanh toán thất bại',
  RETURNING: 'Đang hoàn hàng',
  RETURNED: 'Đã hoàn hàng',
  REFUNDED: 'Đã hoàn tiền',
};

const statusStyles: Record<string, { bg: string; text: string; border: string }> = {
  PENDING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  PROCESSING: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  SHIPPED: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  CANCELLED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  PAYMENT_FAILED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  RETURNING: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  RETURNED: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
  REFUNDED: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
};

const paymentLabels: Record<string, string> = {
  NO_PAYMENT: 'Không yêu cầu thanh toán',
  COD: 'Thanh toán khi nhận hàng (COD)',
  MOMO: 'Ví MoMo Sandbox',
  ZALOPAY: 'Ví ZaloPay Sandbox',
  SEPAY: 'SePay Sandbox',
  VNPAY: 'VNPAY',
};

const paymentStatusLabels: Record<string, string> = {
  UNPAID: 'Chưa thanh toán',
  PAID: 'Đã thanh toán',
  PAID_LATE: 'Thanh toán trễ cần đối soát',
  FAILED: 'Thanh toán thất bại',
  PENDING: 'Đang chờ thanh toán',
  EXPIRED: 'Đã hết hạn',
  REFUNDED: 'Đã ghi nhận hoàn tiền',
};

const paymentStatusStyles: Record<string, { text: string; bg: string }> = {
  UNPAID: { text: 'text-amber-700', bg: 'bg-amber-50' },
  PAID: { text: 'text-emerald-700', bg: 'bg-emerald-50' },
  PAID_LATE: { text: 'text-amber-700', bg: 'bg-amber-50' },
  FAILED: { text: 'text-rose-700', bg: 'bg-rose-50' },
  PENDING: { text: 'text-amber-700', bg: 'bg-amber-50' },
  EXPIRED: { text: 'text-rose-700', bg: 'bg-rose-50' },
  REFUNDED: { text: 'text-slate-700', bg: 'bg-slate-50' },
};

type OrderDetailState = {
  order: any | null;
  loading: boolean;
  error: string;
  shipmentEvents: any[];
};

const initialOrderDetailState: OrderDetailState = {
  order: null,
  loading: true,
  error: '',
  shipmentEvents: [],
};

function mergeOrderDetailState(state: OrderDetailState, patch: Partial<OrderDetailState>): OrderDetailState {
  return { ...state, ...patch };
}

function formatCurrency(value: unknown) {
  return Number(value || 0).toLocaleString('vi-VN') + 'đ';
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString('vi-VN');
}

function orderItemUsedDeviceId(item: any) {
  return String(item?.usedDeviceId || item?.used_device_id || '');
}

// Icons SVGs
const BackIcon = () => (
  <svg className="h-4 w-4 mr-1.5 transition-transform group-hover:-translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

const CopyIcon = () => (
  <svg className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
  </svg>
);

const CheckIcon = () => (
  <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

const CartIcon = () => (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
  </svg>
);

const ProcessingIcon = () => (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const ShippingIcon = () => (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 011-1v-4h3m4 4h-4m4 0a2 2 0 002-2v-3a2 2 0 00-2-2h-3m-1 5v-5a1 1 0 00-1-1h-1m-6 0h2" />
  </svg>
);

const CompletedIcon = () => (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const UserIcon = () => (
  <svg className="h-5 w-5 text-slate-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const PhoneIcon = () => (
  <svg className="h-5 w-5 text-slate-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.94.725l.548 2.2a1 1 0 01-.321.988l-1.305.98a10.582 10.582 0 004.872 4.872l.98-1.305a1 1 0 01.988-.321l2.2.548a1 1 0 01.725.94V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
  </svg>
);

const MapPinIcon = () => (
  <svg className="h-5 w-5 text-slate-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const CreditCardIcon = () => (
  <svg className="h-5 w-5 text-slate-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
  </svg>
);

const BoxIcon = () => (
  <svg className="h-5 w-5 text-slate-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
  </svg>
);

const ProductPlaceholderIcon = () => (
  <svg className="h-8 w-8 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
);

const AlertCircleIcon = () => (
  <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const orderSteps = [
  { label: 'Đã đặt đơn', desc: 'Đặt hàng thành công', icon: CartIcon },
  { label: 'Đang xử lý', desc: 'Shop đang chuẩn bị hàng', icon: ProcessingIcon },
  { label: 'Đang giao hàng', desc: 'Vận chuyển mô phỏng đã nhận', icon: ShippingIcon },
  { label: 'Hoàn tất', desc: 'Đã nhận hàng thành công', icon: CompletedIcon },
];

export default function OrderDetailPage() {
  const { orderId = '' } = useParams();
  const [{ order, loading, error, shipmentEvents }, setPageState] = useReducer(
    mergeOrderDetailState,
    initialOrderDetailState,
  );
  const [copied, setCopied] = useState(false);
  const [showCancelForm, setShowCancelForm] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelBusy, setCancelBusy] = useState(false);
  const [cancelError, setCancelError] = useState('');

  useEffect(() => {
    if (!orderId) return;
    let isActive = true;
    setPageState({ loading: true });

    Promise.all([
      adminOrdersApi.getOrderDetail(orderId),
      customerCenterApi.shipmentTimeline(orderId).catch(() => []),
    ])
      .then(([orderData, timeline]) => {
        if (!isActive) return;
        setPageState({ order: orderData, shipmentEvents: timeline, error: '' });
      })
      .catch((err: any) => {
        if (!isActive) return;
        setPageState({ error: err.message || 'Không thể tải chi tiết đơn hàng.' });
      })
      .finally(() => {
        if (!isActive) return;
        setPageState({ loading: false });
      });

    return () => {
      isActive = false;
    };
  }, [orderId]);

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCancelOrder = async () => {
    const normalizedReason = cancelReason.trim();
    if (normalizedReason.length < 3) {
      setCancelError('Vui lòng nhập lý do hủy đơn có ít nhất 3 ký tự.');
      return;
    }
    setCancelBusy(true);
    setCancelError('');
    try {
      await customerCenterApi.cancelOrder(orderId, normalizedReason);
      const detail = await adminOrdersApi.getOrderDetail(orderId);
      setPageState({ order: detail, error: '' });
      setShowCancelForm(false);
      setCancelReason('');
    } catch (error) {
      setCancelError(error instanceof Error ? error.message : 'Không thể hủy đơn hàng.');
    } finally {
      setCancelBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl py-32 text-center">
        <output
          aria-label="Đang tải chi tiết đơn hàng"
          className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-slate-300 border-r-transparent align-[-0.125em]"
        />
        <div className="mt-4 text-sm font-medium text-slate-500">Đang tải chi tiết đơn hàng...</div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="mx-auto max-w-md px-4 py-24 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 text-rose-500">
          <AlertCircleIcon />
        </div>
        <h1 className="mt-4 text-lg font-bold text-slate-900">Không thể mở đơn hàng</h1>
        <p className="mt-2 text-sm text-rose-600">{error || 'Không tìm thấy đơn hàng.'}</p>
        <Link to="/dashboard" className="mt-8 inline-flex items-center justify-center rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 transition-colors">
          Quay lại tài khoản
        </Link>
      </div>
    );
  }

  const getStepState = (index: number) => {
    const statusOrder: Record<string, number> = {
      PENDING: 0,
      PROCESSING: 1,
      SHIPPED: 2,
      COMPLETED: 3,
    };

    // Nếu trạng thái đặc biệt
    if (['CANCELLED', 'PAYMENT_FAILED', 'RETURNING', 'RETURNED', 'REFUNDED'].includes(order.status)) {
      return 'disabled';
    }

    const currentLevel = statusOrder[order.status] ?? 0;
    if (index < currentLevel) return 'completed';
    if (index === currentLevel) return 'active';
    return 'upcoming';
  };

  const isSpecialStatus = ['CANCELLED', 'PAYMENT_FAILED', 'RETURNING', 'RETURNED', 'REFUNDED'].includes(order.status);
  const badgeStyle = statusStyles[order.status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };
  const latestPendingPayment = (order.payments || []).reduce((latest: any, payment: any) => {
    if (payment.status !== 'PENDING') return latest;
    if (!latest) return payment;
    return Number(payment.attemptNumber || 0) > Number(latest.attemptNumber || 0) ? payment : latest;
  }, undefined);
  const pendingPaymentExpiresAt = latestPendingPayment?.expiresAt ? new Date(latestPendingPayment.expiresAt).getTime() : 0;
  const hasValidPaymentLink = Boolean(
    latestPendingPayment?.id
      && latestPendingPayment?.checkoutUrl
      && (!pendingPaymentExpiresAt || pendingPaymentExpiresAt > Date.now())
      && order.status === 'PENDING',
  );

  return (
    <div className="min-h-screen bg-slate-50/50 py-10">
      <div className="container mx-auto max-w-5xl px-4">

        {/* Navigation & Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link to="/dashboard" className="group inline-flex items-center text-xs font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-800 transition-colors">
              <BackIcon /> Quay lại đơn hàng của tôi
            </Link>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Đơn hàng</h1>
              <div className="inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-1 text-sm font-semibold text-slate-800 shadow-sm border border-slate-100">
                <span>#{order.orderCode}</span>
                <button type="button"
                  onClick={() => handleCopyCode(order.orderCode)}
                  className="group relative p-1 rounded-md hover:bg-slate-50"
                  aria-label="Sao chép mã đơn hàng"
                >
                  {copied ? <CheckIcon /> : <CopyIcon />}
                  {copied && (
                    <span className="absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 rounded bg-slate-800 px-2 py-1 text-[10px] font-medium text-white shadow-sm">
                      Đã sao chép!
                    </span>
                  )}
                </button>
              </div>
            </div>
            <p className="mt-1.5 text-sm text-slate-500">Đặt lúc {formatDate(order.createdAt)}</p>
            {order.orderType && order.orderType !== 'SALE' && (
              <div className="mt-3 inline-flex rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
                {order.orderType === 'WARRANTY_REPLACEMENT' ? 'Đơn giao máy bảo hành' : 'Đơn giao máy đổi trả'}
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <span className={`inline-flex items-center rounded-xl px-4 py-1.5 text-xs font-bold uppercase tracking-wider border ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}>
              {statusLabels[order.status] || order.status}
            </span>
            {order.status === 'PENDING' && (
              <button
                type="button"
                onClick={() => { setShowCancelForm(value => !value); setCancelError(''); }}
                className="inline-flex min-h-10 items-center justify-center rounded-xl border border-rose-200 bg-white px-4 text-sm font-bold text-rose-700 transition hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-200"
              >
                Hủy đơn
              </button>
            )}
          </div>
        </div>

        {showCancelForm && order.status === 'PENDING' && (
          <section className="mb-8 rounded-2xl border border-rose-200 bg-white p-5 shadow-sm" aria-labelledby="cancel-order-title">
            <h2 id="cancel-order-title" className="font-bold text-slate-900">Xác nhận hủy đơn hàng</h2>
            <p className="mt-1 text-sm text-slate-600">Đơn chỉ có thể tự hủy khi còn chờ xử lý. Hàng đang giữ sẽ được trả lại tồn kho.</p>
            <label htmlFor="customer-cancel-reason" className="mt-4 block text-sm font-semibold text-slate-700">
              Lý do hủy <span className="text-rose-600">*</span>
            </label>
            <textarea
              id="customer-cancel-reason"
              value={cancelReason}
              onChange={event => { setCancelReason(event.target.value); setCancelError(''); }}
              className="mt-2 min-h-24 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
              placeholder="Ví dụ: Tôi muốn thay đổi địa chỉ nhận hàng."
              maxLength={1000}
              disabled={cancelBusy}
            />
            {cancelError && <p role="alert" className="mt-2 text-sm font-semibold text-rose-700">{cancelError}</p>}
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => { setShowCancelForm(false); setCancelError(''); }}
                disabled={cancelBusy}
                className="min-h-10 rounded-xl border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
              >
                Giữ đơn hàng
              </button>
              <button
                type="button"
                onClick={() => void handleCancelOrder()}
                disabled={cancelBusy}
                className="min-h-10 rounded-xl bg-rose-600 px-4 text-sm font-bold text-white transition hover:bg-rose-700 disabled:cursor-wait disabled:bg-rose-300"
              >
                {cancelBusy ? 'Đang hủy...' : 'Xác nhận hủy đơn'}
              </button>
            </div>
          </section>
        )}

        {/* Banner trạng thái đặc biệt nếu có */}
        {isSpecialStatus && (
          <div className="mb-8 flex items-start gap-3 rounded-2xl border border-rose-100 bg-rose-50/30 p-5 text-rose-800">
            <div className="mt-0.5 text-rose-500">
              <AlertCircleIcon />
            </div>
            <div>
              <h4 className="font-bold text-rose-900">
                Trạng thái: {statusLabels[order.status] || order.status}
              </h4>
              {order.cancellationReason && (
                <p className="mt-1 text-sm text-rose-700">Lý do: {order.cancellationReason}</p>
              )}
              {order.cancelledAt && (
                <p className="mt-1 text-xs text-rose-500">Ghi nhận vào lúc: {formatDate(order.cancelledAt)}</p>
              )}
              {order.refundedAt && (
                <p className="mt-1 text-xs text-rose-500">Ghi nhận hoàn tiền lúc: {formatDate(order.refundedAt)}</p>
              )}
            </div>
          </div>
        )}

        {/* Stepper tiến trình đơn hàng (ẩn nếu là trạng thái đặc biệt) */}
        {!isSpecialStatus && (
          <div className="mb-8 rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center">
              {orderSteps.map((step, index) => {
                const state = getStepState(index);
                const StepIcon = step.icon;

                return (
                  <div key={step.label} className="flex flex-1 items-center gap-4 md:flex-col md:text-center relative">
                    {/* Line nối giữa các bước */}
                    {index < orderSteps.length - 1 && (
                      <div className="hidden md:block absolute top-5 left-[calc(50%+24px)] right-[calc(-50%+24px)] h-0.5 bg-slate-100 z-0">
                        <div
                          className={`h-full transition-all duration-500 ${
                            state === 'completed' ? 'w-full bg-emerald-500' : 'w-0 bg-slate-100'
                          }`}
                        />
                      </div>
                    )}

                    {/* Vòng tròn Icon */}
                    <div
                      className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
                        state === 'completed'
                          ? 'bg-emerald-500 text-white ring-8 ring-emerald-50'
                          : state === 'active'
                          ? 'bg-slate-900 text-white ring-8 ring-slate-100 animate-pulse'
                          : 'bg-slate-50 text-slate-400 border border-slate-200'
                      }`}
                    >
                      {state === 'completed' ? <CheckIcon /> : <StepIcon />}
                    </div>

                    {/* Thông tin bước */}
                    <div className="flex flex-col">
                      <span className={`text-sm font-bold ${state === 'upcoming' ? 'text-slate-400' : 'text-slate-800'}`}>
                        {step.label}
                      </span>
                      <span className="text-xs text-slate-400 mt-0.5 max-w-[150px] md:mx-auto">
                        {step.desc}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Grid Details */}
        <div className="grid gap-8 lg:grid-cols-[1fr_360px]">

          {/* Cột trái (Thông tin chính) */}
          <div className="space-y-8">

            {/* Card Sản phẩm */}
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-4 mb-4 flex items-center gap-2">
                Danh sách sản phẩm
              </h2>
              <div className="divide-y divide-slate-100">
                {(order.items || []).map((item: any) => {
                  const usedDeviceId = orderItemUsedDeviceId(item);
                  return (
                    <div key={item.id || usedDeviceId || item.productName} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-3.5">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-50 border border-slate-100 shrink-0">
                          <ProductPlaceholderIcon />
                        </div>
                        <div>
                          <p className="font-semibold text-slate-800 text-sm hover:text-slate-900 cursor-default transition-colors">{item.productName}</p>
                          {usedDeviceId ? (
                            <div className="mt-1 inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                              Hàng cũ đã thẩm định
                            </div>
                          ) : null}
                          <p className="mt-1 text-xs font-medium text-slate-400">
                            {formatCurrency(item.price)} <span className="mx-1 text-slate-300">×</span> {item.quantity}
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="font-bold text-slate-900 text-sm">{formatCurrency(item.totalPrice)}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Card Lịch trình vận chuyển (Timeline) */}
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-4 mb-5">
                Cập nhật vận chuyển mô phỏng
              </h2>
              <div className="relative pl-6 space-y-6 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-100">
                {shipmentEvents.map((event, index) => {
                  const isNewest = index === 0;
                  return (
                    <div key={event.id} className="relative flex gap-4">
                      {/* Node Timeline */}
                      <span className={`absolute -left-[23px] top-1.5 z-10 h-3.5 w-3.5 rounded-full border-2 bg-white transition-all duration-300 ${
                        isNewest ? 'border-emerald-500 ring-4 ring-emerald-50 scale-110' : 'border-slate-300'
                      }`} />

                      <div className="flex-1">
                        <p className={`text-sm font-semibold ${isNewest ? 'text-slate-900' : 'text-slate-700'}`}>
                          {event.title}
                        </p>
                        {event.description && (
                          <p className="mt-1 text-xs leading-relaxed text-slate-500">
                            {event.description}
                          </p>
                        )}
                        <p className="mt-1.5 text-[10px] font-medium tracking-wider text-slate-400 uppercase">
                          {formatDate(event.occurredAt)}
                        </p>
                      </div>
                    </div>
                  );
                })}
                {!shipmentEvents.length && (
                  <div className="py-2 text-center text-sm text-slate-400">
                    Chưa có cập nhật vận chuyển mô phỏng nào cho đơn hàng này.
                  </div>
                )}
              </div>
            </section>

            {/* Card Thông tin nhận hàng */}
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-4 mb-5">
                Thông tin giao hàng
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex gap-3">
                  <UserIcon />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Người nhận</span>
                    <p className="mt-0.5 text-sm font-semibold text-slate-800">{order.recipientName}</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <PhoneIcon />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Số điện thoại</span>
                    <p className="mt-0.5 text-sm font-semibold text-slate-800">{order.recipientPhone}</p>
                  </div>
                </div>
                <div className="flex gap-3 sm:col-span-2">
                  <MapPinIcon />
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Địa chỉ giao hàng</span>
                    <p className="mt-0.5 text-sm leading-relaxed text-slate-600">{order.shippingAddress}</p>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Cột phải (Hóa đơn và trạng thái thanh toán) */}
          <div className="space-y-8">

            {/* Card Thanh toán & Vận chuyển */}
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-4 mb-5">
                Thanh toán & Vận chuyển
              </h2>
              <div className="space-y-5">
                <div className="flex items-start gap-3">
                  <CreditCardIcon />
                  <div className="flex-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Phương thức</span>
                    <p className="mt-0.5 text-sm font-medium text-slate-700">
                      {paymentLabels[order.paymentMethod] || order.paymentMethod}
                    </p>
                    <div className="mt-2">
                      <span className={`inline-flex items-center rounded-lg px-2.5 py-0.5 text-xs font-semibold ${
                        paymentStatusStyles[order.paymentStatus]?.bg || 'bg-slate-50'
                      } ${paymentStatusStyles[order.paymentStatus]?.text || 'text-slate-700'}`}>
                        {order.paymentRequirement === 'NO_PAYMENT_REQUIRED'
                          ? 'Không phát sinh thanh toán'
                          : (paymentStatusLabels[order.paymentStatus] || order.paymentStatus)}
                      </span>
                    </div>
                    {hasValidPaymentLink && (
                      <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-3">
                        <p className="text-xs font-semibold text-amber-800">
                          Đơn hàng đang chờ thanh toán đến {formatDate(latestPendingPayment.expiresAt)}.
                        </p>
                        <Link
                          to={`/payment/${latestPendingPayment.id}`}
                          className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-slate-800"
                        >
                          Tiếp tục thanh toán
                        </Link>
                      </div>
                    )}
                    {order.status === 'PAYMENT_FAILED' && (
                      <p className="mt-3 rounded-xl bg-rose-50 p-3 text-xs font-medium leading-relaxed text-rose-700">
                        Phiên thanh toán đã bị hủy, thất bại hoặc hết hạn. Đơn hàng này không còn giữ hàng.
                      </p>
                    )}
                  </div>
                </div>

                {(order.shippingProvider || order.trackingCode) && (
                  <div className="border-t border-slate-100 pt-5 flex items-start gap-3">
                    <BoxIcon />
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Đơn vị vận chuyển demo</span>
                      {order.shippingProvider && (
                        <p className="mt-0.5 text-sm font-semibold text-slate-800">{order.shippingProvider}</p>
                      )}
                      {order.trackingCode && (
                        <div className="mt-1 flex items-center gap-1.5">
                          <span className="text-xs text-slate-500">Mã vận đơn:</span>
                          <strong className="text-xs font-mono text-slate-800 bg-slate-50 border border-slate-100 px-1.5 py-0.5 rounded">
                            {order.trackingCode}
                          </strong>
                        </div>
                      )}
                      <p className="mt-2 text-[11px] leading-4 text-slate-400">
                        Vận đơn này phục vụ demo luận văn, không được gửi sang hãng vận chuyển thật.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* Card Tổng đơn hàng */}
            <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm relative overflow-hidden">
              {/* Receipt top border design */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-slate-200 via-slate-400 to-slate-200" />

              <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-4 mb-4">
                Tổng cộng
              </h2>
              <div className="space-y-3.5 text-sm">
                <div className="flex justify-between text-slate-500">
                  <span>Tạm tính</span>
                  <span className="font-medium text-slate-700">{formatCurrency(order.subtotalAmount)}</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Giảm giá</span>
                  <span className="font-medium text-emerald-600">-{formatCurrency(order.discountAmount)}</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Phí vận chuyển</span>
                  <span className="font-medium text-slate-700">{formatCurrency(order.shippingFee)}</span>
                </div>

                <div className="border-t border-slate-100 pt-4 mt-4 flex items-baseline justify-between">
                  <span className="font-bold text-slate-900 text-base">Tổng tiền</span>
                  <div className="text-right">
                    <span className="text-xl font-extrabold text-slate-900">
                      {formatCurrency(order.totalAmount)}
                    </span>
                    <p className="text-[10px] text-slate-400 mt-0.5">Đã bao gồm VAT (nếu có)</p>
                  </div>
                </div>
              </div>
            </section>

          </div>
        </div>

      </div>
    </div>
  );
}
