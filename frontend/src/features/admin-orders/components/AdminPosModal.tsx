import React, { useState, useEffect, useRef } from 'react';
import { Search, Plus, Minus, Trash2, X, Printer, Check, Percent, CreditCard, User, ShoppingBag } from 'lucide-react';
import { request } from '../../../services/apiClient';

interface AdminPosModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  currency: { format: (val: number) => string };
}

function listFromResponse(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function customerPoints(customer: any): number {
  return Number(customer?.loyalty_points_balance ?? customer?.loyaltyPointsBalance ?? customer?.points ?? 0);
}

function moneyValue(...values: any[]): number {
  for (const value of values) {
    const amount = Number(value);
    if (Number.isFinite(amount) && amount > 0) return amount;
  }
  return 0;
}

function productPrice(product: any): number {
  return moneyValue(product?.salePrice, product?.discountPrice, product?.price);
}

function variantLabel(variant: any): string {
  return variant?.name
    || variant?.configuration
    || [variant?.colorName, variant?.storage, variant?.ram].filter(Boolean).join(' - ')
    || variant?.sku
    || 'Biến thể';
}

function variantPrice(product: any, variant: any): number {
  return moneyValue(variant?.salePrice, variant?.price, productPrice(product));
}

function splitIdentifiers(value: string): string[] {
  return value
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

const normalizePosCart = (currentCart: any[]): any[] => {
  const rules = new Map<string, { discountType: string; discountValue: number; parentProductId: string }>();
  currentCart.forEach(item => {
    const offers = item.salesConfig?.accessoryOffers || [];
    offers.forEach((offer: any) => {
      if (offer && offer.productId) {
        rules.set(String(offer.productId), {
          discountType: offer.discountType,
          discountValue: Number(offer.discountValue || 0),
          parentProductId: item.productId,
        });
      }
    });
  });

  const parentQuantities = new Map<string, number>();
  currentCart.forEach(item => {
    if (!item.cartItemId.includes('-accessory-discount') && !item.cartItemId.includes('-accessory-normal')) {
      parentQuantities.set(item.productId, (parentQuantities.get(item.productId) || 0) + item.quantity);
    }
  });

  const accessoriesGroup: Record<string, { totalQty: number; originalItem: any }> = {};
  const newCart: any[] = [];

  currentCart.forEach(item => {
    const productIdStr = String(item.productId);
    const rule = rules.get(productIdStr);
    const hasParent = rule && (parentQuantities.get(rule.parentProductId) || 0) > 0;

    if (hasParent) {
      if (!accessoriesGroup[productIdStr]) {
        const cleanName = item.productName
          .replace(' (Mua kèm giảm giá)', '')
          .replace(' (Giảm giá)', '');

        const originalPrice = Number(item.originalPrice || (item.cartItemId.endsWith('-discount') ? (item.originalPrice || item.unitPrice / 0.75) : item.unitPrice));

        accessoriesGroup[productIdStr] = {
          totalQty: 0,
          originalItem: {
            ...item,
            productName: cleanName,
            originalPrice: originalPrice,
          }
        };
      }
      accessoriesGroup[productIdStr].totalQty += item.quantity;
    } else {
      const cleanName = item.productName
        .replace(' (Mua kèm giảm giá)', '')
        .replace(' (Giảm giá)', '');

      const originalPrice = Number(item.originalPrice || item.unitPrice);

      newCart.push({
        ...item,
        productName: cleanName,
        unitPrice: item.cartItemId.includes('-discount') ? originalPrice : item.unitPrice,
        originalPrice: undefined,
      });
    }
  });

  Object.entries(accessoriesGroup).forEach(([productId, data]) => {
    const rule = rules.get(productId)!;
    const parentQty = parentQuantities.get(rule.parentProductId) || 0;

    const discountQty = Math.min(data.totalQty, parentQty);
    const normalQty = data.totalQty - discountQty;

    const originalItem = data.originalItem;
    const originalPrice = originalItem.originalPrice;

    if (discountQty > 0) {
      let discountPrice = originalPrice;
      if (rule.discountType === 'PERCENT') {
        discountPrice = Math.max(0, Math.round(originalPrice * (1 - rule.discountValue / 100)));
      } else if (['FIXED', 'AMOUNT', 'FIXED_AMOUNT'].includes(rule.discountType)) {
        discountPrice = Math.max(0, Math.round(originalPrice - rule.discountValue));
      }

      if (discountPrice <= 0 && originalPrice > 0) {
        discountPrice = Math.round(originalPrice * 0.75);
      }

      newCart.push({
        ...originalItem,
        cartItemId: `${originalItem.productId}-accessory-discount`,
        productName: `${originalItem.productName} (Mua kèm giảm giá)`,
        unitPrice: discountPrice,
        quantity: discountQty,
        originalPrice: originalPrice,
      });
    }

    if (normalQty > 0) {
      newCart.push({
        ...originalItem,
        cartItemId: `${originalItem.productId}-accessory-normal`,
        productName: originalItem.productName,
        unitPrice: originalPrice,
        quantity: normalQty,
        originalPrice: undefined,
      });
    }
  });

  return newCart;
};

export default function AdminPosModal({ isOpen, onClose, onSuccess, currency }: AdminPosModalProps) {
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [customerSearch, setCustomerSearch] = useState('');

  const [products, setProducts] = useState<any[]>([]);
  const [productSearch, setProductSearch] = useState('');
  const [productError, setProductError] = useState('');

  // Category & Brand states
  const [categories, setCategories] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('');
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');

  const [cart, setCart] = useState<any[]>([]);
  const [paymentMethod, setPaymentMethod] = useState<'COD' | 'SEPAY' | 'MOMO' | 'ZALOPAY'>('COD');
  const [internalNote, setInternalNote] = useState('');

  // Voucher states
  const [voucherCode, setVoucherCode] = useState('');
  const [appliedVoucher, setAppliedVoucher] = useState<any | null>(null);
  const [voucherError, setVoucherError] = useState('');
  const [voucherChecking, setVoucherChecking] = useState(false);
  const [voucherDiscount, setVoucherDiscount] = useState(0);

  // Loyalty states
  const [loyaltyPointsUsed, setLoyaltyPointsUsed] = useState(0);
  const [loyaltyDiscount, setLoyaltyDiscount] = useState(0);

  // Payment cash states
  const [cashReceived, setCashReceived] = useState<string>('');

  // Guest states (when selectedCustomer is null)
  const [guestName, setGuestName] = useState('Khách vãng lai');
  const [guestPhone, setGuestPhone] = useState('');
  const [guestEmail, setGuestEmail] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdOrder, setCreatedOrder] = useState<any | null>(null);

  const printAreaRef = useRef<HTMLDivElement>(null);

  // Load Initial Customers & Products
  useEffect(() => {
    if (isOpen) {
      loadCustomers('');
      loadProducts('');
      loadCategories();
      loadBrands();
      // Reset state
      setCart([]);
      setSelectedCustomer(null);
      setCustomerSearch('');
      setProductSearch('');
      setSelectedCategoryId('');
      setSelectedBrandId('');
      setAppliedVoucher(null);
      setVoucherCode('');
      setVoucherError('');
      setLoyaltyPointsUsed(0);
      setLoyaltyDiscount(0);
      setCashReceived('');
      setInternalNote('');
      setCreatedOrder(null);
      setGuestName('Khách vãng lai');
      setGuestPhone('');
      setGuestEmail('');
      setProductError('');
    }
  }, [isOpen]);

  const loadCustomers = async (search: string) => {
    try {
      const q = search ? `search=${encodeURIComponent(search)}&limit=20` : 'limit=50';
      const data = await request<any>(`/admin/customers?${q}`);
      setCustomers(listFromResponse(data));
    } catch (e) {
      console.error(e);
      setCustomers([]);
    }
  };

  const loadCategories = async () => {
    try {
      const data = await request<any>('/admin/categories?limit=100');
      setCategories(listFromResponse(data));
    } catch (e) {
      console.error('Không thể tải danh mục', e);
    }
  };

  const loadBrands = async () => {
    try {
      const data = await request<any>('/admin/brands?limit=100');
      setBrands(listFromResponse(data));
    } catch (e) {
      console.error('Không thể tải thương hiệu', e);
    }
  };

  const loadProducts = async (search: string, catId?: string, brId?: string) => {
    try {
      setProductError('');
      const activeCatId = catId !== undefined ? catId : selectedCategoryId;
      const activeBrId = brId !== undefined ? brId : selectedBrandId;
      const catParam = activeCatId ? `&categoryId=${activeCatId}` : '';
      const brParam = activeBrId ? `&brandId=${activeBrId}` : '';

      const q = search
        ? `page=1&search=${encodeURIComponent(search)}&status=ACTIVE&limit=30${catParam}${brParam}`
        : `page=1&status=ACTIVE&limit=50${catParam}${brParam}`;
      const data = await request<any>(`/admin/products?${q}`);
      const list = listFromResponse(data);
      setProducts(list);
      if (list.length === 0) {
        setProductError('Không tìm thấy sản phẩm nào từ hệ thống.');
      }
    } catch (e: any) {
      console.error(e);
      setProductError(e?.message || 'Không thể tải danh sách sản phẩm.');
      setProducts([]);
    }
  };

  const handleCustomerSearchChange = (val: string) => {
    setCustomerSearch(val);
    loadCustomers(val);
  };

  const handleProductSearchChange = (val: string) => {
    setProductSearch(val);
    loadProducts(val, selectedCategoryId, selectedBrandId);
  };

  const handleCategoryChange = (val: string) => {
    setSelectedCategoryId(val);
    loadProducts(productSearch, val, selectedBrandId);
  };

  const handleBrandChange = (val: string) => {
    setSelectedBrandId(val);
    loadProducts(productSearch, selectedCategoryId, val);
  };

  // Add Item to POS Cart
  const addToCart = (product: any, variant?: any) => {
    const cartItemId = variant ? `${product.id}-${variant.id}` : `${product.id}`;
    const existingIndex = cart.findIndex(item => item.cartItemId === cartItemId);

    const price = variant ? variantPrice(product, variant) : productPrice(product);
    const stockQty = variant ? Number(variant.stock_quantity ?? variant.stockQuantity ?? 99) : Number(product.stock_quantity ?? product.stockQuantity ?? 99);

    let newCart = [...cart];
    if (existingIndex > -1) {
      const newQty = cart[existingIndex].quantity + 1;
      if (newQty > stockQty) {
        window.alert(`Không đủ tồn kho khả dụng cho sản phẩm này (Tối đa: ${stockQty})`);
        return;
      }
      newCart[existingIndex].quantity = newQty;
    } else {
      if (stockQty < 1) {
        window.alert('Sản phẩm đã hết hàng trong kho.');
        return;
      }
      newCart.push({
        cartItemId,
        productId: product.id,
        variantId: variant?.id || null,
        productName: product.name + (variant ? ` (${variantLabel(variant)})` : ''),
        unitPrice: price,
        quantity: 1,
        maxStock: stockQty,
        sku: variant?.sku || product.sku || '',
        imeiInput: '',
        serialInput: '',
        salesConfig: product.salesConfig, // Lưu salesConfig để tự động giảm giá sản phẩm mua kèm
      });
    }
    setCart(normalizePosCart(newCart));
  };

  // Helper to calculate correct accessory offer price
  const calculateAccessoryPrice = (offer: any): number => {
    const offerPrice = moneyValue(offer.price);
    if (offerPrice > 0) return Math.round(offerPrice);

    const normalPrice = moneyValue(offer.normalDiscountPrice, offer.salePrice, offer.originalPrice);
    const discountType = String(offer.discountType || '').toUpperCase();
    const discountValue = Number(offer.discountValue || 0);

    let calculated = 0;
    if (discountType === 'PERCENT') {
      calculated = Math.max(0, Math.round(normalPrice * (1 - discountValue / 100)));
    } else if (['FIXED', 'AMOUNT', 'FIXED_AMOUNT'].includes(discountType)) {
      calculated = Math.max(0, Math.round(normalPrice - discountValue));
    } else {
      calculated = Math.round(normalPrice);
    }

    if (calculated <= 0 && normalPrice > 0) {
      return Math.round(normalPrice * 0.75); // tự giảm 25% nếu bị 0đ
    }
    return calculated;
  };

  const tieredServicePrice = (service: any, mainPrice: number): number | null => {
    const tiers = Array.isArray(service?.metadata?.priceTiers) ? service.metadata.priceTiers : [];
    if (!tiers.length || mainPrice <= 0) return null;

    const matchedTier = tiers.find((tier: any) => {
      const min = Number(tier.min || 0);
      const max = tier.max === null || tier.max === undefined ? Number.POSITIVE_INFINITY : Number(tier.max);
      return mainPrice >= min && mainPrice <= max;
    });
    const price = Number(matchedTier?.price);
    return Number.isFinite(price) && price > 0 ? price : null;
  };

  // Helper to calculate correct attached service price based on main product
  const calculateServicePrice = (product: any, service: any): number => {
    const mainPrice = productPrice(product);
    const overridePrice = Number(service.overridePrice);
    if (Number.isFinite(overridePrice) && overridePrice > 0) {
      return Math.round(overridePrice);
    }

    const priceMode = String(service.priceMode || '').toUpperCase();
    if (priceMode === 'FIXED') {
      return Math.round(moneyValue(service.fixedPrice));
    }
    if (priceMode === 'PERCENT') {
      const percentValue = Number(service.percentValue || 0);
      const baseAmount = moneyValue(service.baseAmount, mainPrice);
      return Math.max(0, Math.round((baseAmount * percentValue) / 100));
    }
    if (priceMode === 'TIERED_AMOUNT') {
      return Math.round(tieredServicePrice(service, mainPrice) || 0);
    }
    return 0;
  };

  // Add Accessory Offer (discounted price) to POS Cart
  const addAccessoryOfferToCart = (offer: any) => {
    const stockQty = Number(offer.stockQuantity ?? 99);
    if (stockQty < 1) {
      window.alert('Phụ kiện mua kèm này đã hết hàng trong kho.');
      return;
    }

    const price = offer.originalPrice || offer.salePrice || offer.price || 0;

    // Tìm hoặc thêm raw item
    let newCart = [...cart];

    // Tìm tổng số lượng phụ kiện này đã có
    const discountItem = cart.find(item => item.cartItemId === `${offer.productId}-accessory-discount`);
    const normalItem = cart.find(item => item.cartItemId === `${offer.productId}-accessory-normal`);
    const currentTotalQty = (discountItem?.quantity || 0) + (normalItem?.quantity || 0);

    if (currentTotalQty + 1 > stockQty) {
      window.alert(`Không đủ tồn kho khả dụng cho phụ kiện này (Tối đa: ${stockQty})`);
      return;
    }

    // Nếu đã có item trong giỏ hàng (bất kể dòng discount hay normal), ta chỉ cần cộng thêm 1 vào một trong các dòng thô
    const anyIdx = cart.findIndex(item => item.productId === offer.productId);
    if (anyIdx > -1) {
      newCart = cart.map((item, idx) => {
        if (idx === anyIdx) {
          return { ...item, quantity: item.quantity + 1 };
        }
        return item;
      });
    } else {
      newCart.push({
        cartItemId: `${offer.productId}`,
        productId: offer.productId,
        variantId: null,
        productName: offer.productName || offer.name || 'Phụ kiện',
        unitPrice: price,
        quantity: 1,
        maxStock: stockQty,
        sku: offer.productSku || offer.sku || '',
      });
    }
    setCart(normalizePosCart(newCart));
  };

  // Add Attached Service to POS Cart
  const addAttachedServiceToCart = (product: any, service: any) => {
    const cartItemId = `service-${product.id}-${service.serviceId || service.id}`;
    const existingIndex = cart.findIndex(item => item.cartItemId === cartItemId);
    const price = calculateServicePrice(product, service);

    if (existingIndex > -1) {
      const updated = [...cart];
      updated[existingIndex].quantity += 1;
      setCart(updated);
    } else {
      setCart([...cart, {
        cartItemId,
        productId: 'd0a0d752-5a18-4a8a-9e27-960431d635e8', // System Virtual Service Product ID
        variantId: null,
        productName: `[Dịch vụ] ${service.name || 'Dịch vụ'}`,
        unitPrice: price,
        quantity: 1,
        maxStock: 9999, // Phi vật lý
        sku: service.code || '',
      }]);
    }
  };

  const updateCartQty = (index: number, delta: number) => {
    const item = cart[index];
    const newQty = item.quantity + delta;
    if (newQty < 1) {
      removeFromCart(index);
      return;
    }
    if (item.cartItemId && item.cartItemId.endsWith('-discount') && newQty > 1) {
      window.alert('Sản phẩm mua kèm được giảm giá tối đa là 1 chiếc. Số lượng thêm sẽ tính theo giá gốc.');
      return;
    }
    if (newQty > item.maxStock) {
      window.alert(`Không đủ tồn kho khả dụng cho sản phẩm này (Tối đa: ${item.maxStock})`);
      return;
    }
    const updatedRaw = cart.map((it, idx) => {
      if (idx === index) {
        return { ...it, quantity: newQty };
      }
      return it;
    });
    setCart(normalizePosCart(updatedRaw));
  };

  const removeFromCart = (index: number) => {
    const updatedRaw = cart.filter((_, i) => i !== index);
    setCart(normalizePosCart(updatedRaw));
  };

  const updateCartIdentifierInput = (index: number, field: 'imeiInput' | 'serialInput', value: string) => {
    setCart(cart.map((item, idx) => (idx === index ? { ...item, [field]: value } : item)));
  };

  // Calculate Money details
  const subtotal = cart.reduce((acc, item) => acc + (item.unitPrice * item.quantity), 0);
  const totalDiscount = voucherDiscount + loyaltyDiscount;
  const totalAmount = Math.max(0, subtotal - totalDiscount);

  // Validate Voucher
  const handleCheckVoucher = async () => {
    if (!voucherCode) return;
    setVoucherChecking(true);
    setVoucherError('');
    try {
      const res = await request<any>('/vouchers/validate', {
        method: 'POST',
        body: JSON.stringify({
          code: voucherCode,
          subtotal_amount: subtotal,
          user_id: selectedCustomer?.id || null,
          channel: 'WEB',
          payment_method: paymentMethod,
          product_ids: cart.map(i => i.productId),
        })
      });
      if (res.valid) {
        setAppliedVoucher(res);
        setVoucherDiscount(Number(res.discount_amount || 0));
        setVoucherError('');
      } else {
        setVoucherError(res.message || 'Mã giảm giá không hợp lệ.');
        setAppliedVoucher(null);
        setVoucherDiscount(0);
      }
    } catch (e: any) {
      setVoucherError(e.message || 'Không thể kiểm tra mã giảm giá.');
      setAppliedVoucher(null);
      setVoucherDiscount(0);
    } finally {
      setVoucherChecking(false);
    }
  };

  // Trigger voucher validate when cart subtotal or payment method changes
  useEffect(() => {
    if (appliedVoucher) {
      handleCheckVoucher();
    }
  }, [subtotal, paymentMethod]);

  // Handle Loyalty Points Change
  const handlePointsChange = (points: number) => {
    if (!selectedCustomer) return;
    const maxPoints = customerPoints(selectedCustomer);
    const cleanPoints = Math.min(Math.max(0, points), maxPoints);

    // Tỷ lệ quy đổi: 1 điểm = 1000đ
    const pointsDiscountVal = cleanPoints * 1000;

    if (pointsDiscountVal > subtotal - voucherDiscount) {
      // Giới hạn giảm giá điểm thưởng không vượt quá tổng hóa đơn sau voucher
      const allowedDiscount = subtotal - voucherDiscount;
      const allowedPoints = Math.floor(allowedDiscount / 1000);
      setLoyaltyPointsUsed(allowedPoints);
      setLoyaltyDiscount(allowedPoints * 1000);
    } else {
      setLoyaltyPointsUsed(cleanPoints);
      setLoyaltyDiscount(pointsDiscountVal);
    }
  };

  // Submit Order Creation (POS)
  const handleCheckout = async () => {
    if (cart.length === 0) {
      window.alert('Giỏ hàng trống!');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        user_id: selectedCustomer?.id || null,
        items: cart.map(item => ({
          product_id: item.productId,
          variant_id: item.variantId,
          product_name: item.productName,
          quantity: item.quantity,
          unit_price: item.unitPrice,
          imeis: splitIdentifiers(item.imeiInput || ''),
          serial_numbers: splitIdentifiers(item.serialInput || ''),
        })),
        shipping: {
          recipient_name: selectedCustomer?.fullName || guestName || 'Khách vãng lai',
          recipient_phone: selectedCustomer?.phone || guestPhone || '0000000000',
          recipient_email: selectedCustomer?.email || guestEmail || null,
          shipping_address: 'Mua trực tiếp tại cửa hàng'
        },
        payment_method: paymentMethod,
        voucher_code: appliedVoucher ? voucherCode : null,
        loyalty_points_used: loyaltyPointsUsed,
        is_offline: true,
        internal_note: internalNote
      };

      const res = await request<any>('/orders', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (res.order_id) {
        setCreatedOrder({
          id: res.order_id,
          orderCode: res.order_code,
          recipientName: selectedCustomer?.fullName || guestName || 'Khách vãng lai',
          recipientPhone: selectedCustomer?.phone || guestPhone || '-',
          recipientEmail: selectedCustomer?.email || guestEmail || '-',
          paymentMethod,
          subtotal,
          voucherDiscount,
          loyaltyDiscount,
          totalAmount,
          cashReceived: cashReceived ? Number(cashReceived) : totalAmount,
          createdAt: new Date().toLocaleString('vi-VN'),
        });
      }
    } catch (e: any) {
      window.alert(e.message || 'Lỗi khi tạo đơn hàng POS.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Print Receipt function
  const handlePrint = () => {
    const printContent = printAreaRef.current?.innerHTML;
    if (!printContent) return;

    // Tạo iframe in ấn tạm thời để không bị vỡ layout React chính
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);

    const doc = iframe.contentWindow?.document || iframe.contentDocument;
    if (doc) {
      doc.write(`
        <html>
          <head>
            <title>In Hóa Đơn</title>
            <style>
              @page { size: 80mm auto; margin: 0; }
              body {
                font-family: 'Courier New', Courier, monospace;
                font-size: 12px;
                line-height: 1.4;
                padding: 10px;
                width: 72mm;
                margin: 0;
                color: #000;
              }
              .text-center { text-align: center; }
              .text-right { text-align: right; }
              .font-bold { font-weight: bold; }
              .divider { border-top: 1px dashed #000; margin: 8px 0; }
              table { width: 100%; border-collapse: collapse; }
              th, td { padding: 3px 0; text-align: left; }
              .total-row td { font-weight: bold; }
              .header { margin-bottom: 12px; }
              .footer { margin-top: 15px; font-size: 11px; }
            </style>
          </head>
          <body>
            ${printContent}
            <script>
              window.onload = function() {
                window.print();
                setTimeout(function() {
                  window.frameElement.remove();
                }, 100);
              };
            </script>
          </body>
        </html>
      `);
      doc.close();
    }
  };

  const handleFinish = () => {
    onSuccess();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="relative flex h-[90vh] w-full max-w-6xl flex-col rounded-3xl bg-white shadow-2xl overflow-hidden border border-slate-100">

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <ShoppingBag className="h-6 w-6 text-red-600" />
            <h3 className="text-lg font-bold text-slate-800">Tạo Đơn Hàng Tại Quầy (POS Bán Lẻ)</h3>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition">
            <X className="h-5 w-5" />
          </button>
        </div>

        {createdOrder ? (
          /* SUCCESS SCREEN & RECEIPT PRINT PREVIEW */
          <div className="flex flex-1 flex-col items-center justify-center p-8 overflow-y-auto">
            <div className="mb-4 rounded-full bg-green-100 p-3 text-green-600">
              <Check className="h-10 w-10" />
            </div>
            <h4 className="text-xl font-bold text-slate-900">Đơn Hàng Đã Tạo Thành Công!</h4>
            <p className="mt-1 text-sm text-slate-500">Đã cập nhật hoàn thành trạng thái đơn và xuất kho FIFO.</p>

            {/* Thermal Receipt Preview Area */}
            <div className="mt-6 border border-dashed border-slate-300 rounded-xl bg-slate-50 p-6 shadow-inner w-full max-w-sm">
              <div ref={printAreaRef} className="bg-white p-4 shadow-sm font-mono text-xs text-black border border-slate-200">
                <div className="text-center header">
                  <h3 className="font-bold text-sm uppercase m-0">ANTIGRAVITY STORE</h3>
                  <p className="m-0 mt-1">Đ/c: Đại học Công nghệ Thông tin</p>
                  <p className="m-0">SĐT: 0398.888.888</p>
                  <div className="divider"></div>
                  <h4 className="font-bold text-xs m-1 uppercase">HÓA ĐƠN BÁN LẺ (POS)</h4>
                  <p className="m-0 font-bold">Mã đơn: {createdOrder.orderCode}</p>
                  <p className="m-0">Ngày: {createdOrder.createdAt}</p>
                </div>

                <div className="divider"></div>

                <div className="mb-2">
                  <p className="m-0">Khách: {createdOrder.recipientName}</p>
                  <p className="m-0">SĐT: {createdOrder.recipientPhone}</p>
                  {createdOrder.recipientEmail && createdOrder.recipientEmail !== '-' && (
                    <p className="m-0">Email: {createdOrder.recipientEmail}</p>
                  )}
                </div>

                <div className="divider"></div>

                <table>
                  <thead>
                    <tr>
                      <th className="font-bold">Sản phẩm</th>
                      <th className="font-bold text-center" style={{ width: '30px' }}>SL</th>
                      <th className="font-bold text-right" style={{ width: '80px' }}>Đơn giá</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cart.map((item, idx) => (
                      <tr key={idx}>
                        <td>{item.productName}</td>
                        <td className="text-center">{item.quantity}</td>
                        <td className="text-right">{currency.format(item.unitPrice)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="divider"></div>

                <table>
                  <tbody>
                    <tr>
                      <td>Cộng tiền hàng:</td>
                      <td className="text-right">{currency.format(createdOrder.subtotal)}</td>
                    </tr>
                    {createdOrder.voucherDiscount > 0 && (
                      <tr>
                        <td>Voucher giảm:</td>
                        <td className="text-right">-{currency.format(createdOrder.voucherDiscount)}</td>
                      </tr>
                    )}
                    {createdOrder.loyaltyDiscount > 0 && (
                      <tr>
                        <td>Điểm Loyalty giảm:</td>
                        <td className="text-right">-{currency.format(createdOrder.loyaltyDiscount)}</td>
                      </tr>
                    )}
                    <tr className="total-row">
                      <td className="font-bold">TỔNG CỘNG:</td>
                      <td className="text-right font-bold">{currency.format(createdOrder.totalAmount)}</td>
                    </tr>
                    <tr className="divider"></tr>
                    <tr>
                      <td>Khách đưa:</td>
                      <td className="text-right">{currency.format(createdOrder.cashReceived)}</td>
                    </tr>
                    <tr>
                      <td>Tiền trả lại:</td>
                      <td className="text-right">{currency.format(Math.max(0, createdOrder.cashReceived - createdOrder.totalAmount))}</td>
                    </tr>
                  </tbody>
                </table>

                <div className="divider"></div>
                <div className="text-center footer">
                  <p className="m-0 font-bold">CẢM ƠN QUÝ KHÁCH & HẸN GẶP LẠI!</p>
                  <p className="m-0">Powered by Antigravity POS</p>
                </div>
              </div>
            </div>

            <div className="mt-8 flex gap-4">
              <button
                type="button"
                onClick={handlePrint}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold px-6 py-3 transition shadow cursor-pointer"
              >
                <Printer className="h-5 w-5" /> In Hóa Đơn (K80)
              </button>
              <button
                type="button"
                onClick={handleFinish}
                className="inline-flex items-center gap-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold px-6 py-3 transition shadow cursor-pointer"
              >
                Hoàn tất & Đóng
              </button>
            </div>
          </div>
        ) : (
          /* ACTIVE POS INTERFACE */
          <div className="flex flex-1 overflow-hidden">

            {/* Left Column: Product Selector & Customer search */}
            <div className="flex flex-1 flex-col p-6 overflow-y-auto border-r border-slate-100 gap-5">

              {/* Product Finder & Filters */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Tìm kiếm sản phẩm & Bộ lọc</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="relative">
                    <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={productSearch}
                      onChange={(e) => handleProductSearchChange(e.target.value)}
                      placeholder="Tìm theo tên sản phẩm, SKU..."
                      className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/20"
                    />
                  </div>

                  <div>
                    <select
                      value={selectedCategoryId}
                      onChange={(e) => handleCategoryChange(e.target.value)}
                      className="w-full rounded-2xl border border-slate-200 bg-white py-3 px-4 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/20 cursor-pointer"
                    >
                      <option value="">Tất cả danh mục</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <select
                      value={selectedBrandId}
                      onChange={(e) => handleBrandChange(e.target.value)}
                      className="w-full rounded-2xl border border-slate-200 bg-white py-3 px-4 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/20 cursor-pointer"
                    >
                      <option value="">Tất cả thương hiệu</option>
                      {brands.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Product Grid Results */}
                <div className="mt-3 grid grid-cols-2 gap-3 overflow-y-auto max-h-[300px] p-1 bg-slate-50/50 rounded-2xl border border-slate-100">
                  {products.length === 0 ? (
                    <div className="col-span-2 py-8 text-center text-xs text-red-500 font-semibold">{productError || 'Không tìm thấy sản phẩm nào'}</div>
                  ) : (
                    products.map((product) => {
                      const variants = product.variants || [];
                      return (
                        <div key={product.id} className="rounded-xl border border-slate-200/80 bg-white p-3 shadow-sm flex flex-col justify-between">
                          <div>
                            <div className="font-semibold text-slate-900 text-sm line-clamp-1">{product.name}</div>
                            <div className="mt-0.5 text-xs font-mono text-slate-400">SKU: {product.sku || '-'}</div>
                            <div className="mt-1 font-bold text-red-600 text-sm">{currency.format(productPrice(product))}</div>
                          </div>

                          <div className="mt-2.5">
                            {variants.length > 0 ? (
                              /* If product has variants, show options to select */
                              <div className="flex flex-wrap gap-1 mt-1">
                                {variants.map((v: any) => (
                                  <button
                                    key={v.id}
                                    type="button"
                                    onClick={() => addToCart(product, v)}
                                    className="rounded-lg bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-700 hover:bg-red-50 hover:text-red-700 transition cursor-pointer"
                                    title={`Tồn kho: ${v.stock_quantity ?? v.stockQuantity ?? 0}`}
                                  >
                                    {variantLabel(v)} ({v.stock_quantity ?? v.stockQuantity ?? 0})
                                  </button>
                                ))}
                              </div>
                            ) : (
                              /* Standard product add */
                              <button
                                type="button"
                                onClick={() => addToCart(product)}
                                className="w-full inline-flex h-8 items-center justify-center gap-1.5 rounded-xl bg-slate-800 text-xs font-bold text-white hover:bg-red-600 transition cursor-pointer"
                              >
                                <Plus className="h-3.5 w-3.5" /> Thêm nhanh
                              </button>
                            )}

                            {/* Accessories & Attached Services options */}
                            {(product.salesConfig?.accessoryOffers?.length > 0 || product.salesConfig?.attachedServices?.length > 0) && (
                              <div className="mt-2 border-t border-slate-100 pt-2 space-y-1.5 text-[10px]">
                                {product.salesConfig?.accessoryOffers?.length > 0 && (
                                  <div>
                                    <span className="font-semibold text-slate-500 block mb-0.5">Mua kèm phụ kiện:</span>
                                    <div className="flex flex-wrap gap-1">
                                      {product.salesConfig.accessoryOffers.map((offer: any) => (
                                        <button
                                          key={offer.productId}
                                          type="button"
                                          onClick={() => addAccessoryOfferToCart(offer)}
                                          className="rounded bg-red-50 text-red-600 px-1.5 py-0.5 font-medium hover:bg-red-100 transition cursor-pointer"
                                          title={`Tồn: ${offer.stockQuantity}`}
                                        >
                                          + {offer.productName} ({currency.format(calculateAccessoryPrice(offer))})
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {product.salesConfig?.attachedServices?.length > 0 && (
                                  <div>
                                    <span className="font-semibold text-slate-500 block mb-0.5">Dịch vụ đi kèm:</span>
                                    <div className="flex flex-wrap gap-1">
                                      {product.salesConfig.attachedServices.map((service: any) => (
                                        <button
                                          key={service.serviceId || service.id}
                                          type="button"
                                          onClick={() => addAttachedServiceToCart(product, service)}
                                          className="rounded bg-blue-50 text-blue-600 px-1.5 py-0.5 font-medium hover:bg-blue-100 transition cursor-pointer"
                                        >
                                          + {service.name} ({currency.format(calculateServicePrice(product, service))})
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Customer Selector */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Thành viên tích điểm (Khách hàng)</label>
                <div className="relative">
                  <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={customerSearch}
                    onChange={(e) => handleCustomerSearchChange(e.target.value)}
                    placeholder="Tìm khách hàng theo tên, SĐT, Email..."
                    className="w-full rounded-2xl border border-slate-200 py-3 pl-11 pr-4 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/20"
                  />
                </div>

                {selectedCustomer ? (
                  /* Selected Customer Card */
                  <div className="mt-3 flex items-center justify-between rounded-2xl border border-red-100 bg-red-50/40 p-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-red-100 p-2.5 text-red-600">
                        <User className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-bold text-slate-900 text-sm">{selectedCustomer.fullName}</div>
                        <div className="text-xs text-slate-500">{selectedCustomer.phone || 'Không có SĐT'} | Điểm: <span className="font-bold text-red-600">{customerPoints(selectedCustomer)}</span></div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedCustomer(null);
                        setLoyaltyPointsUsed(0);
                        setLoyaltyDiscount(0);
                      }}
                      className="rounded-lg p-1 text-slate-400 hover:bg-red-100 hover:text-red-700 transition cursor-pointer"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  /* Customer Search Dropdown */
                  customers.length > 0 && (
                    <div className="mt-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg max-h-[180px] overflow-y-auto">
                      {customers.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => {
                            setSelectedCustomer(c);
                            setCustomerSearch('');
                          }}
                          className="w-full text-left rounded-xl p-2 hover:bg-slate-50 flex justify-between items-center transition cursor-pointer"
                        >
                          <div>
                            <div className="font-semibold text-slate-800 text-xs">{c.fullName}</div>
                            <div className="text-[10px] text-slate-400">{c.phone || c.email || 'Khách vãng lai'}</div>
                          </div>
                          <div className="text-[10px] bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-bold">
                            {customerPoints(c)} Điểm
                          </div>
                        </button>
                      ))}
                    </div>
                  )
                )}

                {!selectedCustomer && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 rounded-2xl border border-slate-100 bg-slate-50/50 p-4">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Tên khách vãng lai</label>
                      <input
                        type="text"
                        value={guestName}
                        onChange={(e) => setGuestName(e.target.value)}
                        placeholder="Họ tên khách lẻ..."
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-red-400"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Số điện thoại</label>
                      <input
                        type="text"
                        value={guestPhone}
                        onChange={(e) => setGuestPhone(e.target.value)}
                        placeholder="SĐT nhận hóa đơn..."
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-red-400"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Email nhận hóa đơn</label>
                      <input
                        type="email"
                        value={guestEmail}
                        onChange={(e) => setGuestEmail(e.target.value)}
                        placeholder="Email (vd: Gmail...)"
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-red-400"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Internal Notes */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Ghi chú hóa đơn (Nội bộ)</label>
                <textarea
                  value={internalNote}
                  onChange={(e) => setInternalNote(e.target.value)}
                  placeholder="Ghi chú thêm về đơn hàng hoặc yêu cầu riêng..."
                  rows={2}
                  className="w-full rounded-2xl border border-slate-200 p-3 text-sm outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/20 resize-none"
                />
              </div>

            </div>

            {/* Right Column: POS Cart Checkout Summary */}
            <div className="flex w-[400px] flex-col bg-slate-50/50 p-6 overflow-y-auto gap-4">

              {/* Order Cart list */}
              <div className="flex-1 min-h-[220px]">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Giỏ hàng thanh toán</h4>
                {cart.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
                    <ShoppingBag className="h-8 w-8 text-slate-300" />
                    <span className="text-xs">Chưa có sản phẩm nào</span>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                    {cart.map((item, idx) => (
                      <div key={item.cartItemId} className="flex items-center justify-between rounded-xl bg-white p-3 border border-slate-200/60 shadow-sm">
                        <div className="flex-1 min-w-0 pr-3">
                          <div className="font-semibold text-slate-900 text-xs truncate" title={item.productName}>
                            {item.productName}
                          </div>
                          <div className="mt-0.5 font-bold text-red-600 text-xs">
                            {currency.format(item.unitPrice)}
                          </div>
                          {!String(item.cartItemId || '').startsWith('service-') && (
                            <div className="mt-2 grid grid-cols-1 gap-1.5">
                              <textarea
                                value={item.imeiInput || ''}
                                onChange={(event) => updateCartIdentifierInput(idx, 'imeiInput', event.target.value)}
                                placeholder={`IMEI đã quét (${splitIdentifiers(item.imeiInput || '').length}/${item.quantity})`}
                                rows={1}
                                className="w-full resize-none rounded-lg border border-slate-200 px-2 py-1 text-[10px] outline-none focus:border-red-400"
                              />
                              <textarea
                                value={item.serialInput || ''}
                                onChange={(event) => updateCartIdentifierInput(idx, 'serialInput', event.target.value)}
                                placeholder={`Serial đã quét (${splitIdentifiers(item.serialInput || '').length}/${item.quantity})`}
                                rows={1}
                                className="w-full resize-none rounded-lg border border-slate-200 px-2 py-1 text-[10px] outline-none focus:border-red-400"
                              />
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => updateCartQty(idx, -1)} className="rounded-lg p-1 bg-slate-100 hover:bg-slate-200 text-slate-600 transition cursor-pointer">
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="text-xs font-bold text-slate-800 w-5 text-center">{item.quantity}</span>
                          <button type="button" onClick={() => updateCartQty(idx, 1)} className="rounded-lg p-1 bg-slate-100 hover:bg-slate-200 text-slate-600 transition cursor-pointer">
                            <Plus className="h-3 w-3" />
                          </button>

                          <button type="button" onClick={() => removeFromCart(idx)} className="rounded-lg p-1 text-slate-400 hover:bg-red-50 hover:text-red-700 transition ml-1 cursor-pointer">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Promo & Loyalty Redeem section */}
              <div className="border-t border-slate-200/80 pt-4 space-y-3">

                {/* Apply Voucher */}
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="relative flex-1">
                      <Percent className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input
                        type="text"
                        value={voucherCode}
                        onChange={(e) => setVoucherCode(e.target.value.toUpperCase())}
                        disabled={cart.length === 0}
                        placeholder="Nhập mã Voucher shop"
                        className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-xs outline-none focus:border-red-400 focus:ring-1 focus:ring-red-400/10 disabled:bg-slate-100 disabled:text-slate-400"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleCheckVoucher}
                      disabled={!voucherCode || voucherChecking || cart.length === 0}
                      className="rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs px-3.5 py-2.5 transition disabled:opacity-50 cursor-pointer"
                    >
                      {voucherChecking ? 'Đang check...' : 'Áp dụng'}
                    </button>
                  </div>
                  {voucherError && <p className="mt-1 text-[10px] text-red-500 font-medium">{voucherError}</p>}
                  {appliedVoucher && <p className="mt-1 text-[10px] text-green-600 font-bold">✓ Đã áp dụng: Giảm {currency.format(voucherDiscount)}</p>}
                </div>

                {/* Loyalty Point Slider/Redeem */}
                {selectedCustomer && (
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Sử dụng điểm Loyalty (Số dư: {customerPoints(selectedCustomer)})
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        min={0}
                        max={customerPoints(selectedCustomer)}
                        value={loyaltyPointsUsed || ''}
                        onChange={(e) => handlePointsChange(parseInt(e.target.value) || 0)}
                        placeholder="Số điểm dùng"
                        className="w-24 rounded-lg border border-slate-200 py-1.5 px-2 text-xs outline-none focus:border-red-400"
                      />
                      <span className="text-[10px] text-slate-500 font-bold">
                        = Giảm {currency.format(loyaltyDiscount)}
                      </span>
                    </div>
                  </div>
                )}

              </div>

              {/* Payment Methods */}
              <div className="border-t border-slate-200/80 pt-4">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Hình thức thanh toán</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['COD', 'SEPAY', 'MOMO', 'ZALOPAY'] as const).map((method) => (
                    <button
                      key={method}
                      type="button"
                      onClick={() => setPaymentMethod(method)}
                      className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-xl border text-xs font-bold transition cursor-pointer ${
                        paymentMethod === method
                          ? 'border-red-600 bg-red-50/50 text-red-700'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <CreditCard className="h-3.5 w-3.5" />
                      {method === 'COD' ? 'Tiền mặt' : method === 'SEPAY' ? 'Chuyển khoản' : method}
                    </button>
                  ))}
                </div>
              </div>

              {/* Calculate Cash Return (Tiền thừa) for Cash payment */}
              {paymentMethod === 'COD' && (
                <div className="bg-slate-100/60 rounded-xl p-3 border border-slate-200/50 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                    <span>Số tiền khách đưa:</span>
                    <input
                      type="number"
                      value={cashReceived}
                      onChange={(e) => setCashReceived(e.target.value)}
                      placeholder={String(totalAmount)}
                      className="w-28 text-right rounded-lg border border-slate-200 py-1 px-2 text-xs outline-none focus:border-red-400"
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                    <span>Tiền thừa trả khách:</span>
                    <span className="text-red-600 font-mono">
                      {cashReceived && Number(cashReceived) > totalAmount
                        ? currency.format(Number(cashReceived) - totalAmount)
                        : currency.format(0)}
                    </span>
                  </div>
                </div>
              )}

              {/* Bill Details Summary */}
              <div className="border-t border-slate-200/80 pt-4 space-y-1 text-xs text-slate-600">
                <div className="flex justify-between">
                  <span>Tiền hàng:</span>
                  <span className="font-semibold text-slate-900">{currency.format(subtotal)}</span>
                </div>
                {voucherDiscount > 0 && (
                  <div className="flex justify-between text-red-600">
                    <span>Voucher:</span>
                    <span>-{currency.format(voucherDiscount)}</span>
                  </div>
                )}
                {loyaltyDiscount > 0 && (
                  <div className="flex justify-between text-red-600">
                    <span>Tích điểm loyalty:</span>
                    <span>-{currency.format(loyaltyDiscount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-base font-bold text-slate-900 pt-2 border-t border-slate-100">
                  <span>TỔNG THANH TOÁN:</span>
                  <span className="text-red-600 font-mono">{currency.format(totalAmount)}</span>
                </div>
              </div>

              {/* Confirm Submit buttons */}
              <button
                type="button"
                onClick={handleCheckout}
                disabled={cart.length === 0 || isSubmitting}
                className="w-full inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-red-600 font-bold text-white hover:bg-red-700 transition shadow-md disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? 'Đang hoàn tất...' : 'Hoàn tất & In hóa đơn'}
              </button>

            </div>

          </div>
        )}

      </div>
    </div>
  );
}
