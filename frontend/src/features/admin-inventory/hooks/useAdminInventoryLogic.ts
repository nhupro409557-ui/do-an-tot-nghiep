import { useState, type FormEvent } from 'react';
import { adminInventoryApi } from '../services/adminInventoryApi';

const DEFAULT_LOCATION_CODE = 'MAIN';
const DEFAULT_LOCATION_NAME = 'Kho chính';

type InventoryReceiptLineDraft = {
  id: string;
  productId: string;
  variantId: string;
  quantity: number;
  unitCost: number;
  reason: string;
  note: string;
};

type InventoryDraft = {
  mode: 'RECEIPT';
  editingReferenceCode?: string;
  referenceCode: string;
  receiptReasonCode: string;
  supplierId: string;
  supplierName: string;
  note: string;
  locationCode: string;
  locationName: string;
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
    quantity: 1,
    unitCost: 0,
    reason: 'Nhập kho',
    note: '',
  };
}

function normalizeText(value: string) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function useAdminInventoryLogic({ products, categories, suppliers, query, reloadCurrentTab }: UseAdminInventoryLogicParams) {
  const [inventoryDraft, setInventoryDraft] = useState<InventoryDraft | null>(null);
  const [inventoryLevels, setInventoryLevels] = useState<any[]>([]);
  const [inventoryReceipts, setInventoryReceipts] = useState<any[]>([]);
  const [receiptStatusFilter, setReceiptStatusFilter] = useState('');
  const [imeiReceipt, setImeiReceipt] = useState<any | null>(null);

  async function loadInventoryLevels(search = query) {
    const rows = await adminInventoryApi.adminListLevels(search.trim()).catch(() => []);
    setInventoryLevels(Array.isArray(rows) ? rows : []);
  }

  async function loadInventoryReceipts(search = query) {
    const rows = await adminInventoryApi.adminListReceipts(search.trim()).catch(() => []);
    setInventoryReceipts(Array.isArray(rows) ? rows : []);
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
      note: '',
      locationCode: DEFAULT_LOCATION_CODE,
      locationName: DEFAULT_LOCATION_NAME,
      pickerCategoryId: '',
      pickerBrandId: '',
      pickerSearch: '',
      selectedProductId: product?.id ? String(product.id) : '',
      selectedVariantIds: variant?.id ? [String(variant.id)] : [],
      lines: [newReceiptLine(product, variant)],
    });
  }

  function openReceiptEditDialog(receipt: any) {
    const supplier = suppliers.find((item: any) => String(item.name || '').trim() === String(receipt?.supplierName || '').trim());
    const lines = Array.isArray(receipt?.lines) && receipt.lines.length > 0
      ? receipt.lines.map((line: any) => ({
          id: String(line.id || `${Date.now()}-${Math.random().toString(36).slice(2)}`),
          productId: line.productId ? String(line.productId) : '',
          variantId: line.variantId ? String(line.variantId) : '',
          quantity: Math.max(1, Number(line.quantity || line.plannedQuantity || 1)),
          unitCost: Number(line.unitCost || 0),
          reason: line.reason || 'Nhập kho',
          note: line.note || '',
        }))
      : [newReceiptLine()];
    setInventoryDraft({
      mode: 'RECEIPT',
      editingReferenceCode: String(receipt?.referenceCode || ''),
      referenceCode: String(receipt?.referenceCode || ''),
      receiptReasonCode: String(receipt?.receiptReasonCode || 'NK_MUA'),
      supplierId: supplier?.id ? String(supplier.id) : '',
      supplierName: String(receipt?.supplierName || ''),
      note: String(receipt?.note || ''),
      locationCode: String(receipt?.locationCode || DEFAULT_LOCATION_CODE),
      locationName: String(receipt?.locationName || DEFAULT_LOCATION_NAME),
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
        quantity: line.quantity,
        unitCost: Number.isFinite(line.unitCost) && line.unitCost > 0 ? line.unitCost : null,
        reason: line.reason || 'Nhập kho',
        note: line.note || null,
      });
    }

    const payload = {
      referenceCode: inventoryDraft.referenceCode.trim(),
      receiptReasonCode: inventoryDraft.receiptReasonCode || 'NK_MUA',
      supplierName: inventoryDraft.supplierName.trim() || null,
      note: inventoryDraft.note || null,
      locationCode: inventoryDraft.locationCode || DEFAULT_LOCATION_CODE,
      locationName: inventoryDraft.locationName || DEFAULT_LOCATION_NAME,
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
    const cancelReason = status === 'CANCELLED'
      ? window.prompt('Nhập lý do hủy phiếu nhập kho:')?.trim()
      : undefined;
    if (status === 'CANCELLED' && !cancelReason) return;
    await adminInventoryApi.adminUpdateReceiptStatus(receipt.referenceCode, { status, cancelReason });
    await loadInventoryReceipts();
    await reloadCurrentTab();
  }

  function openReceiptImeiDialog(receipt: any) {
    setImeiReceipt(receipt);
  }

  async function submitReceiptImeis(referenceCode: string, lines: { lineId: string; imeis: string[]; serialNumbers?: string[]; acceptShortage?: boolean; shortageReason?: string | null }[], shortageReason: string) {
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
    inventoryReceipts,
    receiptStatusFilter,
    setReceiptStatusFilter,
    imeiReceipt,
    loadInventoryLevels,
    setInventoryReceipts,
    setInventoryDraft,
    setImeiReceipt,
    loadInventoryReceipts,
    suppliers,
    openInventoryDialog,
    openReceiptDialog,
    openReceiptEditDialog,
    addReceiptLine,
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
    reverseReceipt,
    deleteDraftReceipt,
    openReceiptImeiDialog,
    submitReceiptImeis,
    exportInventorySnapshot,
  };
}
