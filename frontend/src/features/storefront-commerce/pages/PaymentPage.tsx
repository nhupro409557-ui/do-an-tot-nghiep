import { useCallback, useEffect, useMemo, useReducer } from 'react';
import { CheckCircle2, Clock3, ExternalLink, RefreshCw, XCircle, Copy, Check } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { adminOrdersApi } from '../../admin-orders/services/adminOrdersApi';

function remainingSeconds(expiresAt?: string | null) {
  if (!expiresAt) return 0;
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

type PaymentPageState = {
  payment: any | null;
  secondsLeft: number;
  busy: boolean;
  error: string;
  copiedField: string | null;
};

type PaymentPageAction =
  | Partial<PaymentPageState>
  | ((state: PaymentPageState) => PaymentPageState);

const initialPaymentPageState: PaymentPageState = {
  payment: null,
  secondsLeft: 0,
  busy: true,
  error: '',
  copiedField: null,
};

function mergePaymentPageState(state: PaymentPageState, action: PaymentPageAction): PaymentPageState {
  return typeof action === 'function' ? action(state) : { ...state, ...action };
}

export default function PaymentPage() {
  const { paymentId = '' } = useParams();
  const location = useLocation();
  const paymentResult = new URLSearchParams(location.search).get('payment');
  const navigate = useNavigate();
  const [{ payment, secondsLeft, busy, error, copiedField }, setPageState] = useReducer(
    mergePaymentPageState,
    initialPaymentPageState,
  );

  const handleCopy = (text: string, field: string) => {
    void navigator.clipboard.writeText(text);
    setPageState({ copiedField: field });
    setTimeout(() => setPageState({ copiedField: null }), 2000);
  };

  const vietQrUrl = useMemo(() => {
    if (!payment) return '';
    const orderCode = payment.order_code || payment.orderCode || '';
    const amount = Number(payment.amount || 0);
    const addInfo = encodeURIComponent(`thanh toan ${orderCode}`);
    return `https://img.vietqr.io/image/VCB-SBSEPAYACWGUOXNBTDS-compact.png?amount=${amount}&addInfo=${addInfo}&accountName=CONG%20TY%20TNHH%20TEST%2069B2`;
  }, [payment]);

  const terminal = useMemo(
    () => payment && ['PAID', 'PAID_LATE', 'FAILED', 'EXPIRED', 'REFUNDED'].includes(payment.status),
    [payment],
  );

  const cancelAndGoToOrder = useCallback(async () => {
    if (!paymentId) return;
    setPageState({ busy: true });
    try {
      const next = await adminOrdersApi.cancelPayment(paymentId);
      setPageState({ payment: next });
      navigate(`/orders/${next.order_id || next.orderId}`);
    } catch (err: any) {
      setPageState({ error: err.message || 'Không thể hủy phiên thanh toán.', busy: false });
    }
  }, [navigate, paymentId]);

  const loadStatus = useCallback(async (silent = false) => {
    if (!paymentId) return;
    if (!silent) setPageState({ busy: true });
    try {
      const next = await adminOrdersApi.getPaymentStatus(paymentId);
      setPageState({
        payment: next,
        secondsLeft: remainingSeconds(next.expires_at || next.expiresAt),
        error: '',
      });
    } finally {
      if (!silent) setPageState({ busy: false });
    }
  }, [paymentId]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (paymentResult === 'cancel' || paymentResult === 'error') {
      void cancelAndGoToOrder();
    }
  }, [cancelAndGoToOrder, paymentResult]);

  useEffect(() => {
    if (!payment || terminal) return;
    const poll = window.setInterval(() => void loadStatus(true), 4000);
    const timer = window.setInterval(() => setPageState((state) => ({ ...state, secondsLeft: Math.max(0, state.secondsLeft - 1) })), 1000);
    return () => {
      window.clearInterval(poll);
      window.clearInterval(timer);
    };
  }, [loadStatus, payment, terminal]);

  async function retry() {
    setPageState({ busy: true });
    try {
      const next = await adminOrdersApi.retryPayment(paymentId);
      window.location.replace(`/payment/${next.id}`);
    } catch (err: any) {
      setPageState({ error: err.message || 'Không thể tạo phiên thanh toán mới.', busy: false });
    }
  }

  if (busy && !payment) {
    return <div className="mx-auto max-w-xl py-20 text-center text-slate-500">Đang tải phiên thanh toán...</div>;
  }

  if (error && !payment) {
    return <div className="mx-auto max-w-xl py-20 text-center text-red-600">{error}</div>;
  }

  const minutes = Math.floor(secondsLeft / 60).toString().padStart(2, '0');
  const seconds = (secondsLeft % 60).toString().padStart(2, '0');
  const checkoutUrl = payment?.checkout_url || payment?.checkoutUrl;
  const checkoutFields = payment?.checkout_fields || payment?.checkoutFields || {};
  const isZaloPay = payment?.provider === 'ZALOPAY';
  const isSePay = payment?.provider === 'SEPAY';
  const providerName = isSePay ? 'SePay' : isZaloPay ? 'ZaloPay' : 'MoMo';
  const providerColor = isSePay ? '#0f766e' : isZaloPay ? '#0068ff' : '#a50064';

  return (
    <section className="mx-auto my-10 max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-center">
        <div className="text-xs font-black uppercase tracking-[0.2em]" style={{ color: providerColor }}>{providerName}</div>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Thanh toán đơn {payment?.order_code || payment?.orderCode}</h1>
        <p className="mt-2 text-sm text-slate-500">
          {isSePay ? 'Bạn sẽ được chuyển sang cổng SePay để hoàn tất thanh toán.' : 'Thanh toán an toàn và bảo mật.'}
        </p>
      </div>

      <div className="mt-6 rounded-xl bg-slate-50 p-5 text-center">
        <div className="text-sm text-slate-500">Số tiền thanh toán</div>
        <div className="mt-1 text-3xl font-black text-slate-900">
          {Number(payment?.amount || 0).toLocaleString('vi-VN')}đ
        </div>
        {payment?.status === 'PENDING' && (
          <div className="mt-4 flex items-center justify-center gap-2 font-bold text-amber-700">
            <Clock3 size={18} /> Còn {minutes}:{seconds}
          </div>
        )}
      </div>

      {payment?.status === 'PENDING' && (
        <div className="mt-6 space-y-3">
          {isSePay ? (
            <div className="rounded-xl border border-slate-200 p-5 space-y-4">
              <div className="text-center font-bold text-slate-800 text-sm">
                Quét mã VietQR qua App Ngân hàng của bạn để thanh toán
              </div>

              <div className="flex flex-col items-center justify-center bg-slate-50 p-4 rounded-lg border border-slate-100">
                <img
                  src={vietQrUrl}
                  alt="VietQR Payment Code"
                  className="w-60 h-60 object-contain rounded-md shadow-sm border border-slate-200"
                />
                <a
                  href={vietQrUrl}
                  download={`VietQR-${payment?.order_code || 'payment'}.png`}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 text-xs font-bold text-[#0f766e] hover:underline flex items-center gap-1"
                >
                  📥 Tải ảnh QR về máy
                </a>
              </div>

              <div className="space-y-2.5 text-xs text-slate-700 pt-2">
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Ngân hàng</span>
                  <span className="font-bold text-slate-900">Vietcombank</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Số tài khoản</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-900 font-mono">SBSEPAYACWGUOXNBTDS</span>
                    <button
                      type="button"
                      onClick={() => handleCopy('SBSEPAYACWGUOXNBTDS', 'account')}
                      className="text-xs text-[#0f766e] hover:text-[#0d5c56] font-bold flex items-center gap-0.5"
                    >
                      {copiedField === 'account' ? <Check size={12} /> : <Copy size={12} />}
                      {copiedField === 'account' ? 'Đã chép' : 'Sao chép'}
                    </button>
                  </div>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Chủ tài khoản</span>
                  <span className="font-bold text-slate-900">CONG TY TNHH TEST 69B2</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100 bg-amber-50 px-2 rounded-md border border-amber-100">
                  <span className="text-amber-800 font-bold">Nội dung chuyển khoản</span>
                  <div className="flex items-center gap-1.5 py-0.5">
                    <span className="font-extrabold text-red-700 font-mono bg-white px-2 py-0.5 rounded border border-red-200">
                      {`thanh toan ${payment?.order_code || payment?.orderCode || ''}`}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(`thanh toan ${payment?.order_code || payment?.orderCode || ''}`, 'content')}
                      className="text-xs text-red-700 hover:text-red-900 font-bold flex items-center gap-0.5"
                    >
                      {copiedField === 'content' ? <Check size={12} /> : <Copy size={12} />}
                      {copiedField === 'content' ? 'Đã chép' : 'Sao chép'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="text-[11px] text-center text-slate-500 italic mt-3 leading-relaxed">
                Lưu ý: Không chuyển tiền thật; hệ thống chỉ dùng dữ liệu giả lập để xác nhận thanh toán.
              </div>
            </div>
          ) : (
            <a
              href={checkoutUrl}
              target="_blank"
              rel="noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 font-bold text-white"
              style={{ backgroundColor: providerColor }}
            >
              Mở cổng {providerName} <ExternalLink size={18} />
            </a>
          )}
          <button
            type="button"
            onClick={() => void loadStatus()}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-3 font-bold text-slate-700"
          >
            <RefreshCw size={18} /> Kiểm tra trạng thái
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={cancelAndGoToOrder}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 px-4 py-3 font-bold text-red-700 disabled:opacity-50"
          >
            <XCircle size={18} /> Hủy thanh toán
          </button>
        </div>
      )}

      {payment?.status === 'PAID' && (
        <div className="mt-6 rounded-xl bg-emerald-50 p-5 text-center text-emerald-700">
          <CheckCircle2 className="mx-auto mb-2" size={38} />
          <div className="font-bold">{providerName} đã xác nhận thanh toán.</div>
        </div>
      )}

      {payment?.status === 'PAID_LATE' && (
        <div className="mt-6 rounded-xl bg-amber-50 p-5 text-center text-amber-700">
          <Clock3 className="mx-auto mb-2" size={38} />
          <div className="font-bold">Thanh toán được ghi nhận sau khi đơn đã đóng.</div>
          <div className="mt-1 text-sm">Cửa hàng sẽ đối soát và xử lý thủ công.</div>
        </div>
      )}

      {['FAILED', 'EXPIRED'].includes(payment?.status) && (
        <div className="mt-6">
          <div className="rounded-xl bg-red-50 p-5 text-center text-red-700">
            <XCircle className="mx-auto mb-2" size={38} />
            <div className="font-bold">
              {payment.status === 'EXPIRED' ? 'Phiên thanh toán đã hết hạn.' : 'Thanh toán thất bại.'}
            </div>
            {payment.failure_message && <div className="mt-1 text-sm">{payment.failure_message}</div>}
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={retry}
            className="mt-3 w-full rounded-xl px-4 py-3 font-bold text-white disabled:opacity-50"
            style={{ backgroundColor: providerColor }}
          >
            Tạo phiên {providerName} mới
          </button>
        </div>
      )}

      {error && <p className="mt-4 text-center text-sm text-red-600">{error}</p>}
      <Link to={payment?.order_id || payment?.orderId ? `/orders/${payment.order_id || payment.orderId}` : '/dashboard'} className="mt-6 block text-center text-sm font-semibold text-slate-600 hover:text-slate-900">
        Xem chi tiết đơn hàng
      </Link>
    </section>
  );
}
