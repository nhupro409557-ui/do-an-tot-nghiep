import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { customerCenterApi } from '../services/customerCenterApi';
import { publicApi } from '../../../services/publicApi';

type FilePreview = { url: string; type: string; name: string };

const progressSteps = [
  { key: 'SUBMITTED', label: 'Gửi yêu cầu' },
  { key: 'QC', label: 'Kiểm QC' },
  { key: 'PROCESSING', label: 'Xử lý' },
  { key: 'COMPLETED', label: 'Hoàn tất' }
];

const qcStatuses = new Set(['RECEIVED', 'QC_IN_PROGRESS']);
const processingStatuses = new Set([
  'QC_APPROVED', 'WARRANTY_ACCEPTED', 'REPAIRING', 'REPLACEMENT_APPROVED',
  'WAITING_FOR_STOCK', 'WAITING_FOR_EXCHANGE_PAYMENT', 'EXCHANGE_PROCESSING', 'REPLACEMENT_PROCESSING',
  'REFUND_PROCESSING', 'REPAIR_COMPLETED', 'READY_TO_RETURN', 'RETURNING_TO_CUSTOMER'
]);
const closedStatuses = new Set(['REJECTED', 'CANCELLED', 'CLOSED_EXPIRED']);

const revokeFilePreviews = (previews: FilePreview[]) => {
  previews.forEach(item => URL.revokeObjectURL(item.url));
};

const getProgressSteps = (status: string) => {
  let currentStepIndex = 0;
  if (qcStatuses.has(status)) {
    currentStepIndex = 1;
  } else if (processingStatuses.has(status)) {
    currentStepIndex = 2;
  } else if (status === 'COMPLETED') {
    currentStepIndex = 3;
  }

  if (closedStatuses.has(status)) {
    return { isSpecial: true, statusText: statusLabel[status] || status };
  }

  return {
    isSpecial: false,
    currentStepIndex,
    steps: progressSteps
  };
};

const statusLabel: Record<string, string> = {
  SUBMITTED: 'Đã gửi yêu cầu',
  RECEIVED: 'Kho đã tiếp nhận',
  QC_IN_PROGRESS: 'Đang kiểm tra QC',
  QC_APPROVED: 'Đã duyệt đổi trả',
  WARRANTY_ACCEPTED: 'Đã nhận bảo hành',
  REPAIRING: 'Máy bảo hành của bạn đang được sửa',
  REPAIR_COMPLETED: 'Máy bảo hành của bạn đã sửa xong',
  REPLACEMENT_APPROVED: 'Đã duyệt thay máy',
  WAITING_FOR_STOCK: 'Đang chờ hàng',
  EXCHANGE_PROCESSING: 'Đang xử lý đổi máy',
  REPLACEMENT_PROCESSING: 'Đang xử lý máy thay thế',
  REFUND_PROCESSING: 'Đang hoàn tiền',
  READY_TO_RETURN: 'Sẵn sàng trả máy',
  RETURNING_TO_CUSTOMER: 'Đang gửi máy về cho bạn',
  COMPLETED: 'Hoàn tất xử lý',
  REJECTED: 'Bị từ chối',
  CANCELLED: 'Đã hủy',
  CLOSED_EXPIRED: 'Đã hết hạn',
};

const statusStyles: Record<string, { bg: string; text: string; border: string }> = {
  SUBMITTED: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  RECEIVED: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  QC_IN_PROGRESS: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  QC_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WARRANTY_ACCEPTED: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
  REPAIRING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  REPAIR_COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  REPLACEMENT_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WAITING_FOR_STOCK: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  EXCHANGE_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REPLACEMENT_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REFUND_PROCESSING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  READY_TO_RETURN: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  RETURNING_TO_CUSTOMER: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  REJECTED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  CANCELLED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-250' },
  CLOSED_EXPIRED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-250' },
};

statusLabel.WAITING_FOR_EXCHANGE_PAYMENT = 'Chờ thanh toán chênh lệch';
statusStyles.WAITING_FOR_EXCHANGE_PAYMENT = { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' };

const DAY_MS = 24 * 60 * 60 * 1000;

const customerAfterSalesStatusLabel = (item: any) => {
  if (item.status === 'REPAIRING' && item.repairChannel === 'MANUFACTURER') {
    return item.repairProviderName
      ? `Đã gửi bảo hành tại ${item.repairProviderName}`
      : 'Đã gửi bảo hành hãng';
  }
  if (item.status === 'WARRANTY_ACCEPTED' && item.resolutionType === 'REPAIR') return 'Chờ sửa chữa';
  return statusLabel[item.status] || item.status;
};

type WarrantyTone = 'emerald' | 'rose' | 'slate' | 'blue';

type WarrantyInfo = {
  eligible: boolean;
  label: string;
  detail?: string;
  tone: WarrantyTone;
};

type PurchasedIdentifier = {
  imei?: string | null;
  secondaryImei?: string | null;
  serialNumber?: string | null;
  deviceStatus?: string | null;
};

type PurchasedEligibility = {
  eligible: boolean;
  status: 'ACTIVE' | 'EXPIRED' | 'UNSUPPORTED' | 'UNKNOWN_END_DATE' | 'RECOVERED';
  remainingDays: number | null;
  endsAt: string | null;
  tone: WarrantyTone;
  months?: number;
  days?: number;
};

type PurchasedItem = {
  id: string;
  orderId: string;
  orderCode: string;
  orderItemId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  completedAt?: string;
  attachedServices?: Array<Record<string, any>>;
  identifiers?: PurchasedIdentifier[];
  deviceLifecycle?: 'ACTIVE' | 'RECOVERED';
  warranty: PurchasedEligibility;
  returnPolicy: PurchasedEligibility;
};

type ReturnDraftLine = {
  orderItemId: string;
  quantity: number;
  imei: string;
  serialNumber: string;
};

const warrantyToneStyles: Record<WarrantyTone, { bg: string; text: string; border: string }> = {
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  rose: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  slate: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  blue: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
};

const formatCurrency = (value: number | string | null | undefined) => {
  const amount = Number(value || 0);
  return amount.toLocaleString('vi-VN', { style: 'currency', currency: 'VND' });
};

const formatDate = (value?: string | null) => {
  if (!value) return 'Chưa ghi nhận';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Chưa ghi nhận' : parsed.toLocaleDateString('vi-VN');
};

const serviceName = (service: Record<string, any>) => (
  service.name || service.serviceName || service.label || service.code || service.serviceCode || 'Dịch vụ mua kèm'
);

const eligibilityLabel = (policy: PurchasedEligibility, type: 'return' | 'warranty') => {
  if (policy.status === 'UNSUPPORTED') {
    return type === 'return' ? 'Không hỗ trợ đổi trả' : 'Không hỗ trợ bảo hành';
  }
  if (policy.status === 'UNKNOWN_END_DATE') {
    return type === 'return'
      ? `Đổi trả ${policy.days || 0} ngày`
      : `Bảo hành ${policy.months || 0} tháng`;
  }
  if (policy.status === 'EXPIRED') {
    return type === 'return' ? 'Đã hết hạn đổi trả' : 'Đã hết hạn bảo hành';
  }
  const remaining = Number(policy.remainingDays || 0).toLocaleString('vi-VN');
  return type === 'return' ? `Còn ${remaining} ngày đổi trả` : `Còn ${remaining} ngày bảo hành`;
};

const primaryIdentifier = (item: PurchasedItem): PurchasedIdentifier => {
  const recoveredStatuses = new Set(['DEFECTIVE_RETURNED', 'RETURNED', 'RETIRED', 'SCRAP']);
  return (item.identifiers || []).find(identifier =>
    (identifier.imei || identifier.serialNumber)
    && !recoveredStatuses.has(String(identifier.deviceStatus || '').toUpperCase())
  ) || {};
};

const getWarrantyStartDate = (order: any) => {
  const rawDate = order?.completedAt;
  if (!rawDate) return null;

  const parsed = new Date(rawDate);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const getWarrantyInfo = (order: any, item: any, isReturn: boolean): WarrantyInfo | null => {
  if (isReturn) return null;

  const months = Number(item?.warrantyMonthsSnapshot ?? 0);
  if (!Number.isFinite(months) || months <= 0) {
    return {
      eligible: false,
      label: 'Không hỗ trợ bảo hành',
      detail: 'Sản phẩm này không có thời hạn bảo hành tại thời điểm đặt hàng.',
      tone: 'slate',
    };
  }

  const startDate = getWarrantyStartDate(order);
  if (!startDate) {
    return {
      eligible: true,
      label: `Bảo hành ${months.toLocaleString('vi-VN')} tháng`,
      detail: 'Chưa có ngày hoàn thành đơn hàng để tính ngày hết hạn.',
      tone: 'blue',
    };
  }

  const endsAt = new Date(startDate.getTime() + months * 30 * DAY_MS);
  const remainingDays = Math.ceil((endsAt.getTime() - Date.now()) / DAY_MS);

  if (remainingDays < 0) {
    return {
      eligible: false,
      label: `Đã hết hạn bảo hành từ ${endsAt.toLocaleDateString('vi-VN')}`,
      detail: `Thời hạn snapshot: ${months.toLocaleString('vi-VN')} tháng.`,
      tone: 'rose',
    };
  }

  return {
    eligible: true,
    label: remainingDays === 0 ? 'Còn bảo hành đến hôm nay' : `Còn ${remainingDays.toLocaleString('vi-VN')} ngày bảo hành`,
    detail: `Hết hạn dự kiến: ${endsAt.toLocaleDateString('vi-VN')} (${months.toLocaleString('vi-VN')} tháng).`,
    tone: 'emerald',
  };
};

type Props = {
  kind: 'return' | 'warranty';
  orders: any[];
};

export function AfterSalesTab({ kind, orders }: Props) {
  const isReturn = kind === 'return';
  const api = isReturn ? customerCenterApi.listReturns : customerCenterApi.listWarranties;
  const createApi = isReturn ? customerCenterApi.createReturn : customerCenterApi.createWarranty;
  const cancelApi = isReturn ? customerCenterApi.cancelReturn : customerCenterApi.cancelWarranty;
  const uploadApi = isReturn ? customerCenterApi.uploadReturnFiles : customerCenterApi.uploadWarrantyFiles;

  const [items, setItems] = useState<any[]>([]);
  const [purchasedItems, setPurchasedItems] = useState<PurchasedItem[]>([]);
  const [purchasedLoading, setPurchasedLoading] = useState(false);
  const [requestLoadError, setRequestLoadError] = useState('');
  const [purchasedLoadError, setPurchasedLoadError] = useState('');
  const [orderId, setOrderId] = useState('');
  const [orderItemId, setOrderItemId] = useState('');
  const [reason, setReason] = useState('');
  const [imei, setImei] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  const [returnDraftLines, setReturnDraftLines] = useState<ReturnDraftLine[]>([]);
  const [exchangeProducts, setExchangeProducts] = useState<any[]>([]);
  const [exchangeProductSearch, setExchangeProductSearch] = useState('');
  const [exchangeProductsLoading, setExchangeProductsLoading] = useState(false);
  const [exchangeProductsError, setExchangeProductsError] = useState('');
  const [exchangeProductId, setExchangeProductId] = useState('');
  const [exchangeVariantId, setExchangeVariantId] = useState('');
  const [hasAccessories, setHasAccessories] = useState(false);
  const [goodAppearance, setGoodAppearance] = useState(false);
  const [accountUnlocked, setAccountUnlocked] = useState(false);
  const [hasVatInvoice, setHasVatInvoice] = useState(false);
  const filesRef = useRef<File[]>([]);
  const formRef = useRef<HTMLFormElement | null>(null);
  const [filePreviews, setFilePreviews] = useState<FilePreview[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  // Backend chỉ cho phép tạo hậu mãi khi đơn hàng đã hoàn thành.
  const validOrders = useMemo(() => {
    return (orders || []).filter(order => order.status === 'COMPLETED');
  }, [orders]);

  const selectedOrder = useMemo(() => {
    return validOrders.find(order => String(order.id) === orderId);
  }, [validOrders, orderId]);

  const selectedOrderItems = useMemo(() => {
    return selectedOrder?.items || [];
  }, [selectedOrder]);

  const selectedPurchasedItems = useMemo(() => {
    return purchasedItems.filter(item => String(item.orderId) === orderId);
  }, [orderId, purchasedItems]);

  const returnProductOptions = useMemo(() => {
    if (!isReturn) return [];
    if (selectedPurchasedItems.length > 0) return selectedPurchasedItems;
    return selectedOrderItems.map((item: any) => ({
      id: String(item.id),
      orderItemId: String(item.id),
      orderId,
      orderCode: selectedOrder?.orderCode || '',
      productName: item.productName,
      quantity: Number(item.quantity || 1),
      unitPrice: Number(item.price || item.unitPrice || 0),
      totalPrice: Number(item.totalPrice || 0),
      completedAt: selectedOrder?.completedAt,
      identifiers: Array.isArray(item.identifiers) ? item.identifiers : [],
      attachedServices: Array.isArray(item.attachedServices) ? item.attachedServices : [],
      returnPolicy: { eligible: true, status: 'ACTIVE', remainingDays: null, endsAt: null, tone: 'blue' },
      warranty: { eligible: true, status: 'ACTIVE', remainingDays: null, endsAt: null, tone: 'blue' },
    } as PurchasedItem));
  }, [isReturn, orderId, selectedOrder, selectedOrderItems, selectedPurchasedItems]);

  const selectedOrderItem = useMemo(() => {
    if (isReturn) {
      return returnProductOptions.find(item => String(item.orderItemId) === orderItemId);
    }
    return selectedOrderItems.find((item: any) => String(item.id) === orderItemId);
  }, [isReturn, orderItemId, returnProductOptions, selectedOrderItems]);

  const selectedWarrantyInfo = useMemo(() => {
    return selectedOrderItem ? getWarrantyInfo(selectedOrder, selectedOrderItem, isReturn) : null;
  }, [isReturn, selectedOrder, selectedOrderItem]);

  const selectedOrderItemIdentifiers = useMemo(() => {
    return Array.isArray(selectedOrderItem?.identifiers) ? selectedOrderItem.identifiers : [];
  }, [selectedOrderItem]);

  const selectedOrderHistory = useMemo(() => {
    if (!orderId) return [];
    return items.filter(item => String(item.orderId) === orderId);
  }, [items, orderId]);

  const selectedExchangeProduct = useMemo(() => {
    return exchangeProducts.find(product => String(product.id) === exchangeProductId);
  }, [exchangeProducts, exchangeProductId]);

  const selectedExchangeVariants = useMemo(() => {
    return Array.isArray(selectedExchangeProduct?.variants) ? selectedExchangeProduct.variants : [];
  }, [selectedExchangeProduct]);

  const selectedExchangeVariant = useMemo(() => {
    return selectedExchangeVariants.find((variant: any) => String(variant.id) === exchangeVariantId);
  }, [selectedExchangeVariants, exchangeVariantId]);

  const exchangeUnitPrice = Number(
    selectedExchangeVariant?.salePrice
    ?? selectedExchangeVariant?.price
    ?? selectedExchangeProduct?.salePrice
    ?? selectedExchangeProduct?.price
    ?? 0
  );

  const hasEligibleWarrantyItem = useMemo(() => {
    if (isReturn || !selectedOrder) return true;
    return selectedOrderItems.some((item: any) => getWarrantyInfo(selectedOrder, item, false)?.eligible);
  }, [isReturn, selectedOrder, selectedOrderItems]);

  const load = useCallback(async () => {
    try {
      const data = await api({ page: 1, limit: 50 });
      setItems(data.items || []);
      setRequestLoadError('');
    } catch (error) {
      setRequestLoadError(error instanceof Error ? error.message : 'Không thể tải lịch sử yêu cầu hậu mãi.');
    }
  }, [api]);

  const loadPurchasedItems = useCallback(async () => {
    setPurchasedLoading(true);
    try {
      const data = await customerCenterApi.listPurchasedAfterSalesItems();
      setPurchasedItems(Array.isArray(data) ? data : []);
      setPurchasedLoadError('');
    } catch (error) {
      setPurchasedLoadError(error instanceof Error ? error.message : 'Không thể tải danh sách sản phẩm đã mua.');
    } finally {
      setPurchasedLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadPurchasedItems();
  }, [loadPurchasedItems]);

  useEffect(() => {
    if (!isReturn) return undefined;

    const query = exchangeProductSearch.trim();
    if (query.length < 2) {
      setExchangeProducts(current => {
        const selected = current.find(product => String(product.id) === exchangeProductId);
        return selected ? [selected] : [];
      });
      setExchangeProductsLoading(false);
      setExchangeProductsError('');
      return undefined;
    }

    let cancelled = false;
    setExchangeProductsLoading(true);
    setExchangeProductsError('');

    const timeoutId = window.setTimeout(async () => {
      try {
        const data = await publicApi.listProducts({ q: query, limit: 20 });
        if (cancelled) return;
        setExchangeProducts(current => {
          const selected = current.find(product => String(product.id) === exchangeProductId);
          const results = Array.isArray(data) ? data : [];
          if (!selected || results.some(product => String(product.id) === String(selected.id))) {
            return results;
          }
          return [selected, ...results];
        });
      } catch (error) {
        if (cancelled) return;
        setExchangeProducts(current => current.filter(product => String(product.id) === exchangeProductId));
        setExchangeProductsError(error instanceof Error ? error.message : 'Không thể tìm sản phẩm lúc này.');
      } finally {
        if (!cancelled) setExchangeProductsLoading(false);
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [exchangeProductId, exchangeProductSearch, isReturn]);

  useEffect(() => {
    setExchangeVariantId('');
  }, [exchangeProductId]);

  useEffect(() => {
    return () => revokeFilePreviews(filePreviews);
  }, [filePreviews]);

  const syncFiles = (nextFiles: File[]) => {
    filesRef.current = nextFiles;

    const nextPreviews = nextFiles.map(file => ({
      url: URL.createObjectURL(file),
      type: file.type,
      name: file.name
    }));

    setFilePreviews(nextPreviews);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    // Khống chế tối đa 5 files
    syncFiles([...filesRef.current, ...selectedFiles].slice(0, 5));
    event.target.value = '';
  };

  const removeFile = (index: number) => {
    syncFiles(filesRef.current.filter((_, i) => i !== index));
  };

  const fillFromPurchasedItem = (item: PurchasedItem) => {
    const identifier = primaryIdentifier(item);
    setOrderId(item.orderId);
    setOrderItemId(item.orderItemId);
    setImei(identifier.imei || '');
    setSerialNumber(identifier.serialNumber || '');
    setMessage(
      isReturn
        ? `Đã điền thông tin sản phẩm ${item.productName}. Vui lòng mô tả lỗi và tự xác nhận các điều kiện đổi trả.`
        : `Đã điền thông tin sản phẩm ${item.productName}. Vui lòng mô tả lỗi trước khi gửi yêu cầu.`,
    );
    window.requestAnimationFrame(() => {
      formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  const selectIdentifier = (identifier: PurchasedIdentifier) => {
    setImei(identifier.imei || '');
    setSerialNumber(identifier.serialNumber || '');
  };

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!orderId || !orderItemId) {
      setMessage('Vui lòng chọn đơn hàng và sản phẩm.');
      return;
    }
    if (!isReturn && selectedWarrantyInfo && !selectedWarrantyInfo.eligible) {
      setMessage(selectedWarrantyInfo.label);
      return;
    }
    if (isReturn && (!hasAccessories || !goodAppearance || !accountUnlocked || !hasVatInvoice)) {
      setMessage('Bạn phải xác nhận thiết bị đáp ứng tất cả các điều kiện chính sách đổi trả.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const created = await createApi({
        order_id: orderId,
        reason,
        items: [{
          order_item_id: orderItemId,
          quantity: 1,
          imei: imei.trim() || null,
          serial_number: serialNumber.trim() || null,
        }],
        has_accessories: isReturn ? hasAccessories : true,
        good_appearance: isReturn ? goodAppearance : true,
        account_unlocked: isReturn ? accountUnlocked : true,
        has_vat_invoice: isReturn ? hasVatInvoice : true,
        exchange_product_id: isReturn && exchangeProductId ? exchangeProductId : null,
        exchange_variant_id: isReturn && exchangeVariantId ? exchangeVariantId : null,
        exchange_quantity: 1,
      });
      if (filesRef.current.length) {
        await uploadApi(created.id, filesRef.current);
      }
      setReason('');
      setImei('');
      setSerialNumber('');
      setHasAccessories(false);
      setGoodAppearance(false);
      setAccountUnlocked(false);
      setHasVatInvoice(false);
      setExchangeProductId('');
      setExchangeVariantId('');
      syncFiles([]);
      setMessage(`Đã gửi thành công yêu cầu ${created.requestCode}.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tạo yêu cầu.');
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id: string) {
    if (!window.confirm('Bạn có chắc chắn muốn hủy yêu cầu này?')) return;
    try {
      await cancelApi(id);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể hủy yêu cầu.');
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-50 pb-3">
          <div>
            <h3 className="text-lg font-extrabold text-slate-900">Sản phẩm đã mua của bạn</h3>
            <p className="mt-1 text-xs font-medium text-slate-500">
              Chọn nhanh sản phẩm để hệ thống tự điền đơn hàng, IMEI và Serial vào biểu mẫu bên dưới.
            </p>
          </div>
          {purchasedLoading && (
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-500">
              Đang tải...
            </span>
          )}
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {purchasedItems.map(item => {
            const policy = isReturn ? item.returnPolicy : item.warranty;
            const tone = warrantyToneStyles[policy.tone] || warrantyToneStyles.slate;
            const identifiers = item.identifiers || [];
            const recovered = item.deviceLifecycle === 'RECOVERED';
            const disabled = !policy.eligible || recovered;

            return (
              <article key={`${item.orderItemId}-${item.orderCode}`} className="rounded-xl border border-slate-150 p-4 shadow-sm transition-colors hover:border-slate-300">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h4 className="text-sm font-extrabold text-slate-900">{item.productName}</h4>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      #{item.orderCode} · Nhận máy: {formatDate(item.completedAt)}
                    </div>
                  </div>
                  <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${tone.bg} ${tone.text} ${tone.border}`}>
                    {recovered ? 'Đã thu hồi · Đã thay thế' : eligibilityLabel(policy, isReturn ? 'return' : 'warranty')}
                  </span>
                </div>

                <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                  <div className="rounded-lg bg-slate-50 p-2">
                    <span className="block font-bold text-slate-500">Giá lúc mua</span>
                    <span className="font-extrabold text-slate-900">{formatCurrency(item.unitPrice)}</span>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2">
                    <span className="block font-bold text-slate-500">Số lượng</span>
                    <span className="font-extrabold text-slate-900">{Number(item.quantity || 0).toLocaleString('vi-VN')}</span>
                  </div>
                </div>

                {identifiers.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {identifiers.map((identifier, index) => (
                      <div key={`${identifier.imei || ''}-${identifier.serialNumber || ''}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-mono text-[11px] text-slate-700">
                        {identifier.imei && <div>IMEI: {identifier.imei}</div>}
                        {identifier.secondaryImei && <div>IMEI 2: {identifier.secondaryImei}</div>}
                        {identifier.serialNumber && <div>S/N: {identifier.serialNumber}</div>}
                        {['DEFECTIVE_RETURNED', 'RETURNED', 'RETIRED', 'SCRAP'].includes(String(identifier.deviceStatus || '').toUpperCase()) && (
                          <div className="mt-1 font-sans font-bold text-slate-500">Đã thu hồi</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {(item.attachedServices || []).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(item.attachedServices || []).map((service, index) => (
                      <span key={`${serviceName(service)}-${index}`} className="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">
                        {serviceName(service)}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-4 flex justify-end">
                  <button
                    type="button"
                    onClick={() => fillFromPurchasedItem(item)}
                    disabled={disabled}
                    className="rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-bold text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
                  >
                    {recovered ? 'Thiết bị đã được thay thế' : (isReturn ? 'Yêu cầu đổi trả nhanh' : 'Yêu cầu bảo hành nhanh')}
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        {!purchasedLoading && !purchasedItems.length && (
          <div className="py-10 text-center text-sm font-medium text-slate-400">
            Chưa có sản phẩm đã mua trong các đơn hàng hoàn thành.
          </div>
        )}
      </section>

      {/* Form Tạo Yêu Cầu */}
      <form ref={formRef} onSubmit={submit} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-extrabold text-slate-900 border-b border-slate-50 pb-3">
          Tạo yêu cầu {isReturn ? 'đổi trả hàng' : 'bảo hành thiết bị'}
        </h3>

        <div className="mt-5 grid gap-5 md:grid-cols-2">
          {/* Dropdown Đơn hàng */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="after-sales-order" className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đơn hàng của bạn</label>
            <select
              id="after-sales-order"
              value={orderId}
              onChange={event => { setOrderId(event.target.value); setOrderItemId(''); }}
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
              required
            >
              <option value="">-- Chọn đơn hàng hợp lệ --</option>
              {validOrders.map(order => (
                <option key={order.id} value={order.id}>
                  #{order.orderCode} (Đã giao)
                </option>
              ))}
            </select>
          </div>

          {/* Dropdown Sản phẩm */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="after-sales-order-item" className="text-xs font-bold text-slate-500 uppercase tracking-wider">Sản phẩm lỗi</label>
            <select
              id="after-sales-order-item"
              value={orderItemId}
              onChange={event => setOrderItemId(event.target.value)}
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors disabled:opacity-60"
              required
              disabled={!selectedOrder}
            >
              <option value="">-- Chọn sản phẩm cần bảo trì --</option>
              {selectedOrderItems.map((item: any) => {
                const warrantyInfo = getWarrantyInfo(selectedOrder, item, isReturn);
                const disabled = Boolean(!isReturn && warrantyInfo && !warrantyInfo.eligible);
                const label = !isReturn && warrantyInfo ? `${item.productName} · ${warrantyInfo.label}` : item.productName;

                return (
                  <option key={item.id} value={item.id} disabled={disabled}>
                    {label}
                  </option>
                );
              })}
            </select>
            {!isReturn && selectedOrder && !hasEligibleWarrantyItem && (
              <p className="text-xs font-medium text-rose-600">
                Đơn hàng này chưa có sản phẩm còn hiệu lực bảo hành.
              </p>
            )}
            {!isReturn && selectedWarrantyInfo && (
              <div className={`rounded-xl border p-3 text-xs ${warrantyToneStyles[selectedWarrantyInfo.tone].bg} ${warrantyToneStyles[selectedWarrantyInfo.tone].text} ${warrantyToneStyles[selectedWarrantyInfo.tone].border}`}>
                <div className="font-bold">{selectedWarrantyInfo.label}</div>
                {selectedWarrantyInfo.detail && <div className="mt-1">{selectedWarrantyInfo.detail}</div>}
              </div>
            )}
          </div>

          {!isReturn && selectedOrder && selectedOrderItems.length > 0 && (
            <div className="md:col-span-2 rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Tình trạng bảo hành theo từng sản phẩm
              </div>
              <div className="mt-3 grid gap-2">
                {selectedOrderItems.map((item: any) => {
                  const warrantyInfo = getWarrantyInfo(selectedOrder, item, false);
                  if (!warrantyInfo) return null;
                  const tone = warrantyToneStyles[warrantyInfo.tone];

                  return (
                    <div key={item.id} className="flex flex-col gap-1 rounded-lg border border-white bg-white p-3 text-xs shadow-sm sm:flex-row sm:items-center sm:justify-between">
                      <div className="font-semibold text-slate-800">{item.productName}</div>
                      <div className="flex flex-col gap-1 sm:items-end">
                        <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 font-bold ${tone.bg} ${tone.text} ${tone.border}`}>
                          {warrantyInfo.label}
                        </span>
                        {warrantyInfo.detail && <span className="text-slate-500">{warrantyInfo.detail}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {selectedOrderItemIdentifiers.length > 0 && (
            <div className="md:col-span-2 rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Chọn IMEI/Serial đã bán trong đơn hàng
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedOrderItemIdentifiers.map((identifier: PurchasedIdentifier, index: number) => {
                  const active = (identifier.imei || '') === imei && (identifier.serialNumber || '') === serialNumber;
                  const recoveredIdentifier = ['DEFECTIVE_RETURNED', 'RETURNED', 'RETIRED', 'SCRAP']
                    .includes(String(identifier.deviceStatus || '').toUpperCase());
                  return (
                    <button
                      key={`${identifier.imei || ''}-${identifier.serialNumber || ''}-${index}`}
                      type="button"
                      onClick={() => selectIdentifier(identifier)}
                      disabled={recoveredIdentifier}
                      className={`rounded-lg border px-3 py-2 text-left font-mono text-[11px] transition ${
                        active
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : recoveredIdentifier
                            ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                      }`}
                    >
                      {identifier.imei && <div>IMEI: {identifier.imei}</div>}
                      {identifier.secondaryImei && <div>IMEI 2: {identifier.secondaryImei}</div>}
                      {identifier.serialNumber && <div>S/N: {identifier.serialNumber}</div>}
                      {recoveredIdentifier && <div className="mt-1 font-sans font-bold">Đã thu hồi · không còn bảo hành</div>}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {isReturn && (
            <div className="md:col-span-2 grid gap-3 rounded-xl border border-slate-100 bg-slate-50/70 p-4 md:grid-cols-2">
              <div className="md:col-span-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                Sản phẩm muốn đổi sang
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="after-sales-exchange-product-search" className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Tìm sản phẩm mới
                </label>
                <input
                  id="after-sales-exchange-product-search"
                  value={exchangeProductSearch}
                  onChange={event => setExchangeProductSearch(event.target.value)}
                  placeholder="Nhập tên sản phẩm cần đổi"
                  autoComplete="off"
                  className="rounded-xl border border-slate-200 bg-white p-3 text-sm focus:border-slate-900 focus:outline-none"
                />
                <p className="text-xs text-slate-500">
                  Nhập ít nhất 2 ký tự. Hệ thống chỉ hiển thị tối đa 20 kết quả phù hợp.
                </p>
                <select
                  aria-label="Sản phẩm mới"
                  value={exchangeProductId}
                  onChange={event => setExchangeProductId(event.target.value)}
                  disabled={exchangeProductsLoading || (exchangeProductSearch.trim().length < 2 && exchangeProducts.length === 0)}
                  className="rounded-xl border border-slate-200 bg-white p-3 text-sm focus:border-slate-900 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">-- Chưa chọn, chỉ gửi yêu cầu trả/đổi theo QC --</option>
                  {exchangeProducts.map(product => (
                    <option key={product.id} value={product.id}>
                      {product.name} · {formatCurrency(product.salePrice ?? product.price)}
                    </option>
                  ))}
                </select>
                <div aria-live="polite" className="min-h-5 text-xs font-medium">
                  {exchangeProductsLoading && <span className="text-slate-500">Đang tìm sản phẩm...</span>}
                  {!exchangeProductsLoading && exchangeProductsError && (
                    <span className="text-red-600">{exchangeProductsError}</span>
                  )}
                  {!exchangeProductsLoading
                    && !exchangeProductsError
                    && exchangeProductSearch.trim().length >= 2
                    && exchangeProducts.length === 0 && (
                      <span className="text-slate-500">Không tìm thấy sản phẩm phù hợp. Hãy thử tên hoặc từ khóa khác.</span>
                    )}
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Biến thể</label>
                <select
                  value={exchangeVariantId}
                  onChange={event => setExchangeVariantId(event.target.value)}
                  disabled={!exchangeProductId || selectedExchangeVariants.length === 0}
                  className="rounded-xl border border-slate-200 bg-white p-3 text-sm focus:border-slate-900 focus:outline-none disabled:opacity-60"
                >
                  <option value="">-- Dùng sản phẩm gốc hoặc chưa có biến thể --</option>
                  {selectedExchangeVariants.map((variant: any) => (
                    <option key={variant.id} value={variant.id}>
                      {[variant.sku, variant.colorName, variant.storage, variant.ram, variant.configuration].filter(Boolean).join(' · ')}
                      {' · '}
                      {formatCurrency(variant.salePrice ?? variant.price)}
                    </option>
                  ))}
                </select>
              </div>
              {exchangeProductId && (
                <div className="md:col-span-2 rounded-lg border border-orange-100 bg-orange-50 px-3 py-2 text-xs font-semibold text-orange-700">
                  Tạm tính giá sản phẩm mới: {formatCurrency(exchangeUnitPrice)}. Phí đổi máy và chênh lệch cuối cùng sẽ được nhân viên QC chốt sau khi nhận máy cũ.
                </div>
              )}
            </div>
          )}

          {/* Nhập IMEI */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="after-sales-imei" className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã IMEI</label>
            <input
              id="after-sales-imei"
              aria-label="Mã IMEI"
              value={imei}
              onChange={event => setImei(event.target.value)}
              placeholder="Nhập IMEI (Thường ghi trên thân máy/vỏ hộp)"
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
            />
          </div>

          {/* Nhập Serial Number */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="after-sales-serial-number" className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã Serial Number (S/N)</label>
            <input
              id="after-sales-serial-number"
              aria-label="Mã Serial Number"
              value={serialNumber}
              onChange={event => setSerialNumber(event.target.value)}
              placeholder="Nhập Serial number (nếu có)"
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Lý do và mô tả chi tiết */}
        <div className="mt-5 flex flex-col gap-1.5">
          <label htmlFor="after-sales-reason" className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mô tả tình trạng lỗi của sản phẩm</label>
          <textarea
            id="after-sales-reason"
            aria-label="Mô tả tình trạng lỗi của sản phẩm"
            value={reason}
            onChange={event => setReason(event.target.value)}
            minLength={10}
            required
            placeholder="Vui lòng cung cấp chi tiết lỗi của máy để kỹ thuật viên kiểm tra QC nhanh nhất (ví dụ: màn hình sọc ngang, loa rè, không sạc được pin, ...)"
            className="min-h-28 w-full rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
          />
        </div>

        {isReturn && (
          <div className="mt-5 space-y-3.5 rounded-xl border border-slate-100 bg-slate-50/10 p-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Xác nhận điều kiện chính sách đổi trả</div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex items-center gap-2.5 py-1 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasAccessories}
                  onChange={e => setHasAccessories(e.target.checked)}
                  className="h-4.5 w-4.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="text-xs font-semibold text-slate-700">Thiết bị có đầy đủ phụ kiện đi kèm</span>
              </label>

              <label className="flex items-center gap-2.5 py-1 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={goodAppearance}
                  onChange={e => setGoodAppearance(e.target.checked)}
                  className="h-4.5 w-4.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="text-xs font-semibold text-slate-700">Ngoại quan nguyên vẹn (Không nứt vỡ, trầy xước nặng)</span>
              </label>

              <label className="flex items-center gap-2.5 py-1 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={accountUnlocked}
                  onChange={e => setAccountUnlocked(e.target.checked)}
                  className="h-4.5 w-4.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="text-xs font-semibold text-slate-700">Đã thoát tài khoản iCloud/Google khỏi thiết bị</span>
              </label>

              <label className="flex items-center gap-2.5 py-1 select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasVatInvoice}
                  onChange={e => setHasVatInvoice(e.target.checked)}
                  className="h-4.5 w-4.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="text-xs font-semibold text-slate-700">Có hóa đơn mua hàng / VAT đi kèm</span>
              </label>
            </div>
          </div>
        )}

        {/* Tải file và xem trước */}
        <div className="mt-5 flex flex-col gap-1.5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Hình ảnh / Video minh chứng lỗi (Tối đa 5 tệp)</span>
          <div className="mt-1 flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-200 border-dashed rounded-xl cursor-pointer bg-slate-50/50 hover:bg-slate-100/50 transition-colors">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <svg className="w-8 h-8 mb-2.5 text-slate-400" fill="none" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="mb-1 text-sm text-slate-500 font-medium">Click để chọn ảnh hoặc video minh họa</p>
                <p className="text-xs text-slate-400">Chấp nhận JPG, PNG, WEBP, MP4, MOV (Dưới 20MB)</p>
              </div>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>

          {/* Preview Zone */}
          {filePreviews.length > 0 && (
            <div className="mt-4 grid grid-cols-5 gap-3">
              {filePreviews.map((preview, index) => (
                <div key={preview.url} className="relative group rounded-lg overflow-hidden border border-slate-200 bg-slate-100 aspect-square">
                  {preview.type.startsWith('video/') ? (
                    <div className="flex h-full w-full items-center justify-center bg-slate-900 text-white">
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  ) : (
                    <img src={preview.url} alt={preview.name} className="h-full w-full object-cover" />
                  )}
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="absolute -top-1 -right-1 m-1.5 h-5 w-5 bg-rose-500 text-white rounded-full flex items-center justify-center text-xs font-bold opacity-90 hover:opacity-100 shadow-sm"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Nút gửi */}
        <div className="mt-6 flex justify-end">
          <button type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center rounded-xl bg-slate-900 px-6 py-3 text-sm font-bold text-white shadow-md hover:bg-slate-800 focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Đang gửi yêu cầu...
              </>
            ) : 'Gửi yêu cầu bảo hành/đổi trả'}
          </button>
        </div>

        {message && (
          <div className="mt-4 rounded-xl bg-slate-50 border border-slate-100 p-3.5 text-sm text-slate-700 font-medium">
            {message}
          </div>
        )}
      </form>

      {(requestLoadError || purchasedLoadError) && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm font-medium text-rose-700">
          {[requestLoadError, purchasedLoadError].filter(Boolean).join(' ')}
        </div>
      )}

      {/* Lịch Sử Yêu Cầu */}
      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-extrabold text-slate-900 border-b border-slate-50 pb-3">
          Lịch sử yêu cầu đã gửi
        </h3>

        <div className="mt-5 space-y-4">
          {items.map(item => {
            const progress = getProgressSteps(item.status);
            const style = statusStyles[item.status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };

            return (
              <article key={item.id} className="rounded-xl border border-slate-150 p-5 hover:border-slate-350 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-50 pb-3 mb-4">
                  <div>
                    <div className="font-extrabold text-slate-900 text-base">{item.requestCode}</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Đơn hàng #{item.orderCode} · Đã gửi ngày {new Date(item.createdAt).toLocaleString('vi-VN')}
                    </div>
                  </div>
                  <span className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-bold border ${style.bg} ${style.text} ${style.border}`}>
                    {customerAfterSalesStatusLabel(item)}
                  </span>
                </div>

                <div className="space-y-2">
                  <p className="text-sm leading-relaxed text-slate-650 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <span className="font-bold text-slate-800 text-xs block mb-1 uppercase tracking-wide">Mô tả lỗi:</span>
                    {item.reason}
                  </p>

                  <div className="text-xs text-slate-400 flex flex-wrap gap-1.5 items-center mt-2.5">
                    <span className="font-bold text-slate-500">Sản phẩm lỗi:</span>
                    {(item.items || []).map((line: any) => (
                      <span key={line.id} className="inline-flex items-center bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-slate-600 font-medium">
                        {line.productName}
                        {line.imei && ` (IMEI: ${line.imei})`}
                        {line.replacementImei && ` ➔ Đã đổi sang máy: ${line.replacementImei}`}
                      </span>
                    ))}
                  </div>
                  {item.repairSummary?.diagnosis && (
                    <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-xs text-emerald-900">
                      <div className="font-extrabold">Kết quả sửa chữa</div>
                      <div className="mt-1">Chẩn đoán: {item.repairSummary.diagnosis}</div>
                      {item.repairSummary.action && <div className="mt-1">Đã xử lý: {item.repairSummary.action}</div>}
                    </div>
                  )}
                  {item.status === 'WAITING_FOR_EXCHANGE_PAYMENT' && (
                    <div className="mt-3 rounded-lg border border-orange-100 bg-orange-50 p-3 text-xs font-semibold text-orange-800">
                      <div>Khách cần thanh toán chênh lệch: {formatCurrency(item.balanceAmount)}</div>
                      {item.paymentDueAt && (
                        <div className="mt-1">
                          Hạn thanh toán: {new Date(item.paymentDueAt).toLocaleString('vi-VN')}
                        </div>
                      )}
                    </div>
                  )}
                  {item.fulfillmentOrder && (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50 p-3">
                      <div className="text-xs text-blue-800">
                        <div className="font-extrabold">Đơn giao máy #{item.fulfillmentOrder.orderCode}</div>
                        <div className="mt-1 font-medium">
                          {item.fulfillmentOrder.trackingCode
                            ? `${item.fulfillmentOrder.shippingProvider || 'Đơn vị vận chuyển'} · ${item.fulfillmentOrder.trackingCode}`
                            : 'Đơn đang được chuẩn bị và chưa có mã vận đơn.'}
                        </div>
                      </div>
                      <Link
                        to={`/orders/${item.fulfillmentOrder.id}`}
                        className="inline-flex rounded-lg bg-blue-700 px-3 py-2 text-xs font-bold text-white transition hover:bg-blue-800"
                      >
                        Theo dõi giao máy
                      </Link>
                    </div>
                  )}
                </div>

                {/* Stepper */}
                {!progress.isSpecial && progress.steps && (
                  <div className="mt-5 border-t border-slate-50 pt-5">
                    <div className="flex items-center justify-between relative max-w-xl mx-auto">
                      <div className="absolute top-[13px] left-[16px] right-[16px] h-0.5 bg-slate-100 z-0" />
                      <div
                        className="absolute top-[13px] left-[16px] h-0.5 bg-emerald-500 z-0 transition-all duration-300"
                        style={{ width: `${(progress.currentStepIndex / (progress.steps.length - 1)) * 100}%` }}
                      />

                      {progress.steps.map((step, idx) => {
                        const isDone = idx < (progress.currentStepIndex ?? 0);
                        const isActive = idx === progress.currentStepIndex;
                        return (
                          <div key={step.key} className="flex flex-col items-center z-10">
                            <div
                              className={`h-7 w-7 rounded-full flex items-center justify-center border text-xs font-bold transition-all duration-300 ${
                                isDone
                                  ? 'bg-emerald-500 border-emerald-500 text-white ring-4 ring-emerald-50'
                                  : isActive
                                  ? 'bg-slate-900 border-slate-900 text-white ring-4 ring-slate-100 animate-pulse'
                                  : 'bg-white border-slate-200 text-slate-400'
                              }`}
                            >
                              {isDone ? '✓' : idx + 1}
                            </div>
                            <span className={`text-[10px] font-bold mt-1.5 ${
                              isActive ? 'text-slate-900' : isDone ? 'text-emerald-600' : 'text-slate-400'
                            }`}>
                              {step.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {progress.isSpecial && (
                  <div className="mt-4 border-t border-slate-50 pt-4 text-xs text-slate-500">
                    Hồ sơ đã đóng với trạng thái: <strong className="text-slate-700">{progress.statusText}</strong>
                  </div>
                )}

                {['SUBMITTED', 'WAITING_FOR_STOCK', 'WAITING_FOR_EXCHANGE_PAYMENT'].includes(item.status) && (
                  <div className="mt-4 border-t border-slate-50 pt-4 flex justify-end">
                    <button
                      type="button"
                      onClick={() => void cancel(item.id)}
                      className="text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Hủy yêu cầu
                    </button>
                  </div>
                )}
              </article>
            );
          })}
          {!items.length && (
            <div className="py-12 text-center text-sm text-slate-400 font-medium">
              Chưa có yêu cầu đổi trả hoặc bảo hành nào được tạo.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
