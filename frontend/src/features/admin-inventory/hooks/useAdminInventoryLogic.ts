import { useRef, useState, type FormEvent } from 'react';
import { adminInventoryApi } from '../services/adminInventoryApi';

const DEFAULT_LOCATION_CODE = 'MAIN';
const DEFAULT_LOCATION_NAME = 'Kho chính';
const INVENTORY_PAGE_SIZE = 50;

type InventoryReceiptLineDraft = {
  id: string;
  productId: string;
  variantId: string;
  warehouseLocationId: string;
  quantity: number;
  unitCost: number;
  reason: string;
  note: string;
  storageLocationCode: string;
  storageLocationName: string;
  purchaseOrderLineId: string;
};

type InventoryDraft = {
  mode: 'RECEIPT';
  editingReferenceCode?: string;
  referenceCode: string;
  receiptReasonCode: string;
  supplierId: string;
  supplierName: string;
  purchaseOrderId: string;
  invoiceNumber: string;
  invoiceDate: string;
  paymentMode: string;
  paymentTermDays: number;
  dueDate: string;
  paidAmount: number;
  discountAmount: number;
  shippingFee: number;
  payableNote: string;
  note: string;
  locationCode: string;
  locationName: string;
  qualityStatus: string;
  qualityNote: string;
  quarantine: boolean;
  quarantineLocation: string;
  attachments: any[];
  discrepancies: any[];
  pickerCategoryId: string;
  pickerBrandId: string;
  pickerSearch: string;
  selectedProductId: string;
  selectedVariantIds: string[];
  lines: InventoryReceiptLineDraft[];
};

type UseAdminInventoryLogicParams = {
  products: any[];
  categories: any[];
  suppliers: any[];
  query: string;
  inventoryCategoryFilter: string;
  inventoryBrandFilter: string;
  reloadCurrentTab: () => Promise<void>;
};

function generateReceiptCode() {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  const date = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  const time = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `NK${date}-${time}`;
}

function newReceiptLine(product?: any, variant?: any): InventoryReceiptLineDraft {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    productId: product?.id ? String(product.id) : '',
    variantId: variant?.id ? String(variant.id) : '',
    warehouseLocationId: '',
    quantity: 1,
    unitCost: 0,
    reason: 'Nhập kho',
    note: '',
    storageLocationCode: '',
    storageLocationName: '',
    purchaseOrderLineId: '',
  };
}

function normalizeText(value: string) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function useAdminInventoryLogic({ products, categories, suppliers, query, inventoryCategoryFilter, inventoryBrandFilter, reloadCurrentTab }: UseAdminInventoryLogicParams) {
  const [inventoryDraft, setInventoryDraft] = useState<InventoryDraft | null>(null);
  const receiptStatusUpdatingRef = useRef<Set<string>>(new Set());
  const [inventoryLevels, setInventoryLevels] = useState<any[]>([]);
  const [inventoryPage, setInventoryPage] = useState(1);
  const [inventoryTotal, setInventoryTotal] = useState(0);
  const [inventoryTotalPages, setInventoryTotalPages] = useState(1);
  const [inventoryLocations, setInventoryLocations] = useState<any[]>([]);
  const [inventoryAllLocations, setInventoryAllLocations] = useState<any[]>([]);
  const [inventoryDashboard, setInventoryDashboard] = useState<any>({ totalSku: 0, lowStockCount: 0, inventoryValue: 0, reservedSkuCount: 0, topStock: [], topNeedRestock: [] });
  const [inventoryLedger, setInventoryLedger] = useState<any[]>([]);
  const [ledgerPage, setLedgerPage] = useState(1);
  const [ledgerTotal, setLedgerTotal] = useState(0);
  const [ledgerTotalPages, setLedgerTotalPages] = useState(1);
  const [inventoryStockFilter, setInventoryStockFilter] = useState('');
  const [inventoryLocationFilter, setInventoryLocationFilter] = useState('');
  const [ledgerDateFrom, setLedgerDateFrom] = useState('');
  const [ledgerDateTo, setLedgerDateTo] = useState('');
  const [ledgerTransactionType, setLedgerTransactionType] = useState('');
  const [ledgerReason, setLedgerReason] = useState('');
  const [inventoryReceipts, setInventoryReceipts] = useState<any[]>([]);
  const [receiptPage, setReceiptPage] = useState(1);
  const [receiptTotal, setReceiptTotal] = useState(0);
  const [receiptTotalPages, setReceiptTotalPages] = useState(1);
  const [inventoryReceiptReport, setInventoryReceiptReport] = useState<any>({ daily: [], monthly: [], suppliers: [] });
  const [receiptStatusFilter, setReceiptStatusFilter] = useState('');
  const [receiptDateFrom, setReceiptDateFrom] = useState('');
  const [receiptDateTo, setReceiptDateTo] = useState('');
  const [imeiReceipt, setImeiReceipt] = useState<any | null>(null);

  async function loadInventoryLevels(search = query, page = 1) {
    const [result, dashboard, locations] = await Promise.all([
      adminInventoryApi.adminListLevels(search.trim(), inventoryStockFilter, inventoryLocationFilter.trim(), inventoryCategoryFilter, inventoryBrandFilter, page, INVENTORY_PAGE_SIZE).catch(() => ({ items: [], total: 0, totalPages: 1 })),
      adminInventoryApi.adminGetInventoryDashboard(search.trim()).catch(() => ({ totalSku: 0, lowStockCount: 0, inventoryValue: 0, reservedSkuCount: 0, topStock: [], topNeedRestock: [] })),
      adminInventoryApi.adminListLocations('', true).catch(() => []),
    ]);
    setInventoryLevels(Array.isArray(result?.items) ? result.items : []);
    setInventoryPage(Number(result?.page || page));
    setInventoryTotal(Number(result?.total || 0));
    setInventoryTotalPages(Number(result?.totalPages || 1));
    setInventoryLocations(Array.isArray(locations) ? locations : []);
    setInventoryAllLocations(Array.isArray(locations) ? locations : []);
    setInventoryDashboard(dashboard || { totalSku: 0, lowStockCount: 0, inventoryValue: 0, reservedSkuCount: 0, topStock: [], topNeedRestock: [] });
  }

  async function loadInventoryLocations(search = '', filters: any = {}) {
    const rows = await adminInventoryApi.adminListLocations(search, true, filters).catch(() => []);
    setInventoryLocations(Array.isArray(rows) ? rows : []);
    if (!search && Object.keys(filters || {}).length === 0) {
      setInventoryAllLocations(Array.isArray(rows) ? rows : []);
    }
  }

  async function loadInventoryLedger(search = query, page = 1) {
    const result = await adminInventoryApi.adminListInventoryLedger({
      search: search.trim(),
      dateFrom: ledgerDateFrom,
      dateTo: ledgerDateTo,
      transactionType: ledgerTransactionType,
      reason: ledgerReason,
      page,
      pageSize: INVENTORY_PAGE_SIZE,
    }).catch(() => ({ items: [], total: 0, totalPages: 1 }));
    setInventoryLedger(Array.isArray(result?.items) ? result.items : []);
    setLedgerPage(Number(result?.page || page));
    setLedgerTotal(Number(result?.total || 0));
    setLedgerTotalPages(Number(result?.totalPages || 1));
  }

  async function applyInventoryAdvancedFilters() {
    await loadInventoryLevels(query, 1);
  }

  async function clearInventoryAdvancedFilters() {
    setInventoryStockFilter('');
    setInventoryLocationFilter('');
    const [result, dashboard] = await Promise.all([
      adminInventoryApi.adminListLevels(query.trim(), '', '', inventoryCategoryFilter, inventoryBrandFilter, 1, INVENTORY_PAGE_SIZE).catch(() => ({ items: [], total: 0, totalPages: 1 })),
      adminInventoryApi.adminGetInventoryDashboard(query.trim()).catch(() => ({ totalSku: 0, lowStockCount: 0, inventoryValue: 0, reservedSkuCount: 0, topStock: [], topNeedRestock: [] })),
    ]);
    setInventoryLevels(Array.isArray(result?.items) ? result.items : []);
    setInventoryPage(1);
    setInventoryTotal(Number(result?.total || 0));
    setInventoryTotalPages(Number(result?.totalPages || 1));
    setInventoryDashboard(dashboard || { totalSku: 0, lowStockCount: 0, inventoryValue: 0, reservedSkuCount: 0, topStock: [], topNeedRestock: [] });
  }

  async function applyInventoryLedgerFilters() {
    await loadInventoryLedger(query);
  }

  async function clearInventoryLedgerFilters() {
    setLedgerDateFrom('');
    setLedgerDateTo('');
    setLedgerTransactionType('');
    setLedgerReason('');
    const result = await adminInventoryApi.adminListInventoryLedger({ search: query.trim(), page: 1, pageSize: INVENTORY_PAGE_SIZE }).catch(() => ({ items: [], total: 0, totalPages: 1 }));
    setInventoryLedger(Array.isArray(result?.items) ? result.items : []);
    setLedgerPage(1);
    setLedgerTotal(Number(result?.total || 0));
    setLedgerTotalPages(Number(result?.totalPages || 1));
  }

  async function loadInventoryReceipts(search = query, page = 1, status = receiptStatusFilter) {
    const [result, report, locations] = await Promise.all([
      adminInventoryApi.adminListReceipts(search.trim(), receiptDateFrom, receiptDateTo, status, page, INVENTORY_PAGE_SIZE).catch(() => ({ items: [], total: 0, totalPages: 1 })),
      adminInventoryApi.adminGetReceiptReport().catch(() => ({ daily: [], monthly: [], suppliers: [] })),
      adminInventoryApi.adminListLocations('', true).catch(() => []),
    ]);
    setInventoryReceipts(Array.isArray(result?.items) ? result.items : []);
    setReceiptPage(Number(result?.page || page));
    setReceiptTotal(Number(result?.total || 0));
    setReceiptTotalPages(Number(result?.totalPages || 1));
    setInventoryLocations(Array.isArray(locations) ? locations : []);
    setInventoryReceiptReport(report || { daily: [], monthly: [], suppliers: [] });
  }

  async function applyReceiptDateFilter() {
    await loadInventoryReceipts(query, 1);
  }

  async function clearReceiptDateFilter() {
    setReceiptDateFrom('');
    setReceiptDateTo('');
    const [result, report] = await Promise.all([
      adminInventoryApi.adminListReceipts(query.trim(), '', '', receiptStatusFilter, 1, INVENTORY_PAGE_SIZE).catch(() => ({ items: [], total: 0, totalPages: 1 })),
      adminInventoryApi.adminGetReceiptReport().catch(() => ({ daily: [], monthly: [], suppliers: [] })),
    ]);
    setInventoryReceipts(Array.isArray(result?.items) ? result.items : []);
    setReceiptPage(1);
    setReceiptTotal(Number(result?.total || 0));
    setReceiptTotalPages(Number(result?.totalPages || 1));
    setInventoryReceiptReport(report || { daily: [], monthly: [], suppliers: [] });
  }

  function resolveProduct(productId: string) {
    return products.find((product) => String(product.id) === String(productId));
  }

  function resolveVariant(product: any, variantId: string) {
    return (product?.variants || []).find((variant: any) => String(variant.id) === String(variantId));
  }

  function categoryTracksImei(product: any) {
    const salesConfig = product?.salesConfig || {};
    const imeiPolicy = salesConfig.imeiPolicy || {};
    if (String(imeiPolicy.mode || 'CATEGORY').toUpperCase() === 'MANUAL') {
      return Boolean(imeiPolicy.trackImei);
    }
    const child = categories.find((category: any) => String(category.id) === String(product?.subcategoryId));
    const parentId = product?.categoryId || child?.parentId;
    const parent = categories.find((category: any) => String(category.id) === String(parentId));
    const childPolicy = child?.inventoryPolicy || {};
    const parentPolicy = parent?.inventoryPolicy || {};
    if (child && childPolicy.inheritImeiPolicy === false) {
      return Boolean(childPolicy.trackImei);
    }
    return Boolean(parentPolicy.trackImei);
  }

  function categoryTracksSerialNumber(product: any) {
    const salesConfig = product?.salesConfig || {};
    const serialPolicy = salesConfig.serialPolicy || {};
    if (String(serialPolicy.mode || 'CATEGORY').toUpperCase() === 'MANUAL') {
      return Boolean(serialPolicy.trackSerialNumber);
    }
    const child = categories.find((category: any) => String(category.id) === String(product?.subcategoryId));
    const parentId = product?.categoryId || child?.parentId;
    const parent = categories.find((category: any) => String(category.id) === String(parentId));
    const childPolicy = child?.inventoryPolicy || {};
    const parentPolicy = parent?.inventoryPolicy || {};
    if (child && childPolicy.inheritSerialPolicy === false) {
      return Boolean(childPolicy.trackSerialNumber);
    }
    return Boolean(parentPolicy.trackSerialNumber);
  }

  function receiptProductBlockReason(product: any) {
    const status = String(product?.status || '').toUpperCase();
    if (status && status !== 'ACTIVE') {
      return `Sản phẩm đang ở trạng thái ${status}, không được nhập kho.`;
    }
    if (product?.hiddenByCategory || product?.hidden_by_category || product?.hiddenByBrand || product?.hidden_by_brand) {
      return 'Sản phẩm đang bị ẩn theo danh mục hoặc thương hiệu, không được nhập kho.';
    }
    return '';
  }

  function receiptVariantAvailable(variant: any) {
    const status = String(variant?.status || 'active').toLowerCase();
    return variant?.deletedAt == null
      && variant?.deleted_at == null
      && variant?.isActive !== false
      && !['deleted', 'archived'].includes(status);
  }

  function openReceiptDialog(product?: any, variant?: any) {
    if (product) {
      const blockedReason = receiptProductBlockReason(product);
      if (blockedReason) {
        window.alert(blockedReason);
        return;
      }
    }
    if (variant && !receiptVariantAvailable(variant)) {
      window.alert('Biến thể đã ngừng hoạt động hoặc bị xóa, không được nhập kho.');
      return;
    }
    setInventoryDraft({
      mode: 'RECEIPT',
      referenceCode: generateReceiptCode(),
      receiptReasonCode: 'NK_MUA',
      supplierId: '',
      supplierName: '',
      purchaseOrderId: '',
      invoiceNumber: '',
      invoiceDate: '',
      paymentMode: 'DEBT',
      paymentTermDays: 0,
      dueDate: '',
      paidAmount: 0,
      discountAmount: 0,
      shippingFee: 0,
      payableNote: '',
      note: '',
      locationCode: DEFAULT_LOCATION_CODE,
      locationName: DEFAULT_LOCATION_NAME,
      qualityStatus: 'PENDING',
      qualityNote: '',
      quarantine: false,
      quarantineLocation: '',
      attachments: [],
      discrepancies: [],
      pickerCategoryId: '',
      pickerBrandId: '',
      pickerSearch: '',
      selectedProductId: product?.id ? String(product.id) : '',
      selectedVariantIds: variant?.id ? [String(variant.id)] : [],
      lines: [newReceiptLine(product, variant)],
    });
  }

  function openReceiptEditDialog(receipt: any) {
    const supplier = suppliers.find((item: any) => String(item.id || '') === String(receipt?.supplierId || ''))
      || suppliers.find((item: any) => String(item.name || '').trim() === String(receipt?.supplierName || '').trim());
    const lines = Array.isArray(receipt?.lines) && receipt.lines.length > 0
      ? receipt.lines.map((line: any) => ({
          id: String(line.id || `${Date.now()}-${Math.random().toString(36).slice(2)}`),
          productId: line.productId ? String(line.productId) : '',
          variantId: line.variantId ? String(line.variantId) : '',
          quantity: Math.max(1, Number(line.quantity || line.plannedQuantity || 1)),
          unitCost: Number(line.quotedUnitCost ?? line.unitCost ?? 0),
          reason: line.reason || 'Nhập kho',
          note: line.note || '',
          warehouseLocationId: String(line.locationId || line.warehouseLocationId || ''),
          storageLocationCode: String(line.storageLocationCode || ''),
          storageLocationName: String(line.storageLocationName || ''),
          purchaseOrderLineId: String(line.purchaseOrderLineId || ''),
        }))
      : [newReceiptLine()];
    setInventoryDraft({
      mode: 'RECEIPT',
      editingReferenceCode: String(receipt?.referenceCode || ''),
      referenceCode: String(receipt?.referenceCode || ''),
      receiptReasonCode: String(receipt?.receiptReasonCode || 'NK_MUA'),
      supplierId: supplier?.id ? String(supplier.id) : '',
      supplierName: String(receipt?.supplierName || ''),
      purchaseOrderId: String(receipt?.purchaseOrderId || ''),
      invoiceNumber: String(receipt?.invoiceNumber || ''),
      invoiceDate: receipt?.invoiceDate ? String(receipt.invoiceDate).slice(0, 10) : '',
      paymentMode: String(receipt?.paymentMode || 'DEBT'),
      paymentTermDays: Number(receipt?.paymentTermDays || 0),
      dueDate: receipt?.dueDate ? String(receipt.dueDate).slice(0, 10) : '',
      paidAmount: Number(receipt?.paidAmount || 0),
      discountAmount: Number(receipt?.discountAmount || 0),
      shippingFee: Number(receipt?.shippingFee || 0),
      payableNote: String(receipt?.payableNote || ''),
      note: String(receipt?.note || ''),
      locationCode: String(receipt?.locationCode || DEFAULT_LOCATION_CODE),
      locationName: String(receipt?.locationName || DEFAULT_LOCATION_NAME),
      qualityStatus: String(receipt?.qualityStatus || 'PENDING'),
      qualityNote: String(receipt?.qualityNote || ''),
      quarantine: Boolean(receipt?.quarantine),
      quarantineLocation: String(receipt?.quarantineLocation || ''),
      attachments: Array.isArray(receipt?.attachments) ? receipt.attachments : [],
      discrepancies: Array.isArray(receipt?.discrepancies) ? receipt.discrepancies : [],
      pickerCategoryId: '',
      pickerBrandId: '',
      pickerSearch: '',
      selectedProductId: '',
      selectedVariantIds: [],
      lines,
    });
  }

  async function openInventoryDialog(product: any, variant?: any) {
    openReceiptDialog(product, variant);
  }

  function updateReceiptLine(lineId: string, patch: Partial<InventoryReceiptLineDraft>) {
    setInventoryDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        lines: current.lines.map((line) => {
          if (line.id !== lineId) return line;
          const next = { ...line, ...patch };
          if (patch.productId !== undefined) {
            next.variantId = '';
          }
          return next;
        }),
      };
    });
  }

  function addReceiptLine() {
    setInventoryDraft((current) => (current ? { ...current, lines: [...current.lines, newReceiptLine()] } : current));
  }

  function addReceiptShelfAllocation(lineId: string) {
    setInventoryDraft((current) => {
      if (!current) return current;
      const sourceIndex = current.lines.findIndex((line) => line.id === lineId);
      if (sourceIndex < 0) return current;
      const source = current.lines[sourceIndex];
      if (source.quantity <= 1) {
        window.alert('Dòng này chỉ có 1 sản phẩm nên không thể tách thêm kệ. Hãy tăng số lượng trước khi tách.');
        return current;
      }
      const nextLines = [...current.lines];
      nextLines[sourceIndex] = { ...source, quantity: source.quantity - 1 };
      nextLines.splice(sourceIndex + 1, 0, {
        ...source,
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        warehouseLocationId: '',
        storageLocationCode: '',
        storageLocationName: '',
        quantity: 1,
      });
      return { ...current, lines: nextLines };
    });
  }

  function removeReceiptLine(lineId: string) {
    setInventoryDraft((current) => {
      if (!current || current.lines.length <= 1) return current;
      return { ...current, lines: current.lines.filter((line) => line.id !== lineId) };
    });
  }

  function productMatchesReceiptFilters(product: any, draft = inventoryDraft) {
    if (!draft) return true;
    if (receiptProductBlockReason(product)) return false;
    if (draft.pickerCategoryId) {
      const matchesCategory = String(product.categoryId) === draft.pickerCategoryId || String(product.subcategoryId) === draft.pickerCategoryId;
      const matchesChild = categories.some((category: any) => String(category.parentId) === draft.pickerCategoryId && (String(product.categoryId) === String(category.id) || String(product.subcategoryId) === String(category.id)));
      if (!matchesCategory && !matchesChild) return false;
    }
    if (draft.pickerBrandId && String(product.brandId) !== draft.pickerBrandId) return false;
    const search = normalizeText(draft.pickerSearch);
    if (search) {
      const haystack = normalizeText(`${product.name || ''} ${product.sku || ''} ${(product.variants || []).map((variant: any) => variant.sku).join(' ')}`);
      if (!haystack.includes(search)) return false;
    }
    return true;
  }

  function selectReceiptPickerProduct(productId: string) {
    const product = resolveProduct(productId);
    if (product && receiptProductBlockReason(product)) return;
    setInventoryDraft((current) => current ? { ...current, selectedProductId: productId, selectedVariantIds: [] } : current);
  }

  function toggleReceiptVariantSelection(variantId: string) {
    setInventoryDraft((current) => {
      if (!current) return current;
      const exists = current.selectedVariantIds.includes(variantId);
      return {
        ...current,
        selectedVariantIds: exists
          ? current.selectedVariantIds.filter((id) => id !== variantId)
          : [...current.selectedVariantIds, variantId],
      };
    });
  }

  function clearReceiptVariantSelection() {
    setInventoryDraft((current) => (current ? { ...current, selectedVariantIds: [] } : current));
  }

  function selectAllPickerVariants() {
    setInventoryDraft((current) => {
      if (!current?.selectedProductId) return current;
      const product = resolveProduct(current.selectedProductId);
      if (!product || receiptProductBlockReason(product)) return current;
      const variantIds = (product?.variants || []).filter(receiptVariantAvailable).map((variant: any) => String(variant.id));
      return { ...current, selectedVariantIds: variantIds };
    });
  }

  function addSelectedVariantsToReceipt() {
    setInventoryDraft((current) => {
      if (!current?.selectedProductId) return current;
      const product = resolveProduct(current.selectedProductId);
      if (!product) return current;
      if (receiptProductBlockReason(product)) return current;
      const variants = product.variants || [];
      const selectedVariants = variants.length > 0
        ? variants.filter((variant: any) => receiptVariantAvailable(variant) && current.selectedVariantIds.includes(String(variant.id)))
        : [undefined];
      if (variants.length > 0 && selectedVariants.length === 0) return current;

      const existingKeys = new Set(current.lines.map((line) => `${line.productId}:${line.variantId || ''}`));
      const nextLines = [...current.lines];
      for (const variant of selectedVariants) {
        const key = `${product.id}:${variant?.id || ''}`;
        if (!existingKeys.has(key)) {
          nextLines.push(newReceiptLine(product, variant));
          existingKeys.add(key);
        }
      }
      const cleanedLines = nextLines.filter((line, index) => index > 0 || line.productId || nextLines.length === 1);
      return { ...current, lines: cleanedLines.length ? cleanedLines : [newReceiptLine()] };
    });
  }

  async function submitInventoryDraft(event?: FormEvent) {
    event?.preventDefault();
    if (!inventoryDraft) return;
    if (!inventoryDraft.referenceCode.trim()) {
      window.alert('Vui lòng nhập mã phiếu nhập.');
      return;
    }

    if (inventoryDraft.receiptReasonCode === 'NK_KHAC' && !inventoryDraft.note.trim()) {
      window.alert('Nhập khác phải ghi rõ lý do trong ghi chú chung.');
      return;
    }

    const payloadLines = [];
    for (const [index, line] of inventoryDraft.lines.entries()) {
      const product = resolveProduct(line.productId);
      if (!product) {
        window.alert(`Dòng ${index + 1}: vui lòng chọn sản phẩm.`);
        return;
      }
      const blockedReason = receiptProductBlockReason(product);
      if (blockedReason) {
        window.alert(`Dòng ${index + 1}: ${blockedReason}`);
        return;
      }
      const variants = product.variants || [];
      if (variants.length > 1 && !line.variantId) {
        window.alert(`Dòng ${index + 1}: sản phẩm có nhiều biến thể, vui lòng chọn biến thể.`);
        return;
      }
      if (line.variantId) {
        const variant = variants.find((item: any) => String(item.id) === String(line.variantId));
        if (!variant || !receiptVariantAvailable(variant)) {
          window.alert(`Dòng ${index + 1}: biến thể đã ngừng hoạt động hoặc bị xóa, không được nhập kho.`);
          return;
        }
      }
      if (!Number.isFinite(line.quantity) || line.quantity <= 0) {
        window.alert(`Dòng ${index + 1}: số lượng nhập phải lớn hơn 0.`);
        return;
      }
      payloadLines.push({
        productId: line.productId,
        variantId: line.variantId || null,
        warehouseLocationId: line.warehouseLocationId || null,
        quantity: line.quantity,
        unitCost: Number.isFinite(line.unitCost) && line.unitCost > 0 ? line.unitCost : null,
        reason: line.reason || 'Nhập kho',
        note: line.note || null,
        storageLocationCode: line.storageLocationCode?.trim() || null,
        storageLocationName: line.storageLocationName?.trim() || null,
        purchaseOrderLineId: line.purchaseOrderLineId || null,
      });
    }

    const payload = {
      referenceCode: inventoryDraft.referenceCode.trim(),
      receiptReasonCode: inventoryDraft.receiptReasonCode || 'NK_MUA',
      supplierId: inventoryDraft.supplierId || null,
      supplierName: inventoryDraft.supplierName.trim() || null,
      purchaseOrderId: inventoryDraft.purchaseOrderId || null,
      invoiceNumber: inventoryDraft.invoiceNumber.trim() || null,
      invoiceDate: inventoryDraft.invoiceDate ? new Date(inventoryDraft.invoiceDate).toISOString() : null,
      paymentMode: inventoryDraft.paymentMode || 'DEBT',
      paymentTermDays: Number(inventoryDraft.paymentTermDays || 0),
      dueDate: inventoryDraft.dueDate ? new Date(inventoryDraft.dueDate).toISOString() : null,
      paidAmount: Number(inventoryDraft.paidAmount || 0),
      discountAmount: Number(inventoryDraft.discountAmount || 0),
      shippingFee: Number(inventoryDraft.shippingFee || 0),
      payableNote: inventoryDraft.payableNote.trim() || null,
      note: inventoryDraft.note || null,
      locationCode: inventoryDraft.locationCode || DEFAULT_LOCATION_CODE,
      locationName: inventoryDraft.locationName || DEFAULT_LOCATION_NAME,
      qualityStatus: inventoryDraft.qualityStatus || 'PENDING',
      qualityNote: inventoryDraft.qualityNote.trim() || null,
      quarantine: Boolean(inventoryDraft.quarantine),
      quarantineLocation: inventoryDraft.quarantineLocation.trim() || null,
      attachments: (inventoryDraft.attachments || [])
        .filter((item: any) => String(item.name || '').trim() || String(item.url || '').trim())
        .map((item: any) => ({
          type: item.type || 'OTHER',
          name: String(item.name || '').trim(),
          url: String(item.url || '').trim(),
          note: String(item.note || '').trim() || null,
        })),
      discrepancies: (inventoryDraft.discrepancies || [])
        .filter((item: any) => String(item.description || '').trim())
        .map((item: any) => ({
          type: item.type || 'OTHER',
          description: String(item.description || '').trim(),
          quantity: Number.isFinite(Number(item.quantity)) && Number(item.quantity) >= 0 ? Number(item.quantity) : null,
          action: String(item.action || '').trim() || null,
        })),
      status: 'DRAFT',
      lines: payloadLines,
    };
    if (inventoryDraft.editingReferenceCode) {
      await adminInventoryApi.adminUpdateReceipt(inventoryDraft.editingReferenceCode, payload);
    } else {
      await adminInventoryApi.adminCreateReceipt(payload);
    }
    setInventoryDraft(null);
    await loadInventoryReceipts();
    await reloadCurrentTab();
  }

  async function updateReceiptStatus(receipt: any, status: string) {
    const actionKey = `${receipt.referenceCode}:${status}`;
    if (receiptStatusUpdatingRef.current.has(actionKey)) return;
    const cancelReason = status === 'CANCELLED'
      ? window.prompt('Nhập lý do hủy phiếu nhập kho:')?.trim()
      : undefined;
    if (status === 'CANCELLED' && !cancelReason) return;
    receiptStatusUpdatingRef.current.add(actionKey);
    try {
      await adminInventoryApi.adminUpdateReceiptStatus(receipt.referenceCode, { status, cancelReason });
      await loadInventoryReceipts();
      await reloadCurrentTab();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể cập nhật trạng thái phiếu nhập kho.');
    } finally {
      receiptStatusUpdatingRef.current.delete(actionKey);
    }
  }

  async function submitReceiptQuality(referenceCode: string, payload: any) {
    await adminInventoryApi.adminUpdateReceiptQuality(referenceCode, payload);
    await loadInventoryReceipts();
    await reloadCurrentTab();
  }

  function openReceiptImeiDialog(receipt: any) {
    setImeiReceipt(receipt);
  }

  async function submitReceiptImeis(referenceCode: string, lines: { lineId: string; imeis: string[]; secondaryImeis?: string[]; serialNumbers?: string[]; acceptShortage?: boolean; shortageReason?: string | null }[], shortageReason: string) {
    const result = await adminInventoryApi.adminSubmitReceiptImeis(referenceCode, { lines, shortageReason: shortageReason || null });
    setImeiReceipt(null);
    await loadInventoryReceipts();
    await reloadCurrentTab();
    return result;
  }

  async function reverseReceipt(receipt: any) {
    const reason = window.prompt('Nhập lý do đảo phiếu nhập kho:')?.trim();
    if (!reason) return;
    const note = window.prompt('Ghi chú đảo phiếu nhập kho (không bắt buộc):')?.trim() || null;
    await adminInventoryApi.adminReverseReceipt(receipt.referenceCode, { reason, note });
    await loadInventoryReceipts();
    await reloadCurrentTab();
  }

  async function deleteDraftReceipt(receipt: any) {
    if ((receipt.status || 'COMPLETED') !== 'DRAFT') {
      window.alert('Chỉ có thể xóa phiếu nhập còn ở trạng thái nháp.');
      return;
    }
    const confirmed = window.confirm(`Xóa phiếu nháp ${receipt.referenceCode}? Thao tác này không thể hoàn tác.`);
    if (!confirmed) return;
    await adminInventoryApi.adminDeleteReceipt(receipt.referenceCode);
    await loadInventoryReceipts();
    await reloadCurrentTab();
  }

  async function exportInventorySnapshot() {
    const blob = await adminInventoryApi.adminExportInventory(query.trim());
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `inventory-export-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return {
    inventoryDraft,
    inventoryLevels,
    inventoryPage,
    inventoryTotal,
    inventoryTotalPages,
    inventoryLocations,
    inventoryAllLocations,
    inventoryDashboard,
    inventoryLedger,
    ledgerPage,
    ledgerTotal,
    ledgerTotalPages,
    inventoryStockFilter,
    setInventoryStockFilter,
    inventoryLocationFilter,
    setInventoryLocationFilter,
    ledgerDateFrom,
    setLedgerDateFrom,
    ledgerDateTo,
    setLedgerDateTo,
    ledgerTransactionType,
    setLedgerTransactionType,
    ledgerReason,
    setLedgerReason,
    inventoryReceipts,
    receiptPage,
    receiptTotal,
    receiptTotalPages,
    inventoryReceiptReport,
    receiptStatusFilter,
    setReceiptStatusFilter,
    receiptDateFrom,
    setReceiptDateFrom,
    receiptDateTo,
    setReceiptDateTo,
    imeiReceipt,
    loadInventoryLevels,
    loadInventoryLocations,
    loadInventoryLedger,
    applyInventoryAdvancedFilters,
    clearInventoryAdvancedFilters,
    applyInventoryLedgerFilters,
    clearInventoryLedgerFilters,
    setInventoryReceipts,
    setInventoryDraft,
    setImeiReceipt,
    loadInventoryReceipts,
    applyReceiptDateFilter,
    clearReceiptDateFilter,
    suppliers,
    openInventoryDialog,
    openReceiptDialog,
    openReceiptEditDialog,
    addReceiptLine,
    addReceiptShelfAllocation,
    removeReceiptLine,
    updateReceiptLine,
    resolveProduct,
    resolveVariant,
    categoryTracksImei,
    categoryTracksSerialNumber,
    productMatchesReceiptFilters,
    selectReceiptPickerProduct,
    toggleReceiptVariantSelection,
    clearReceiptVariantSelection,
    selectAllPickerVariants,
    addSelectedVariantsToReceipt,
    submitInventoryDraft,
    updateReceiptStatus,
    submitReceiptQuality,
    reverseReceipt,
    deleteDraftReceipt,
    openReceiptImeiDialog,
    submitReceiptImeis,
    exportInventorySnapshot,
  };
}
