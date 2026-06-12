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
  imeis: string;
};

type InventoryDraft = {
  mode: 'RECEIPT';
  referenceCode: string;
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
    imeis: '',
  };
}

function splitImeis(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeText(value: string) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function useAdminInventoryLogic({ products, categories, suppliers, query, reloadCurrentTab }: UseAdminInventoryLogicParams) {
  const [inventoryDraft, setInventoryDraft] = useState<InventoryDraft | null>(null);
  const [inventoryReceipts, setInventoryReceipts] = useState<any[]>([]);

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

  function openReceiptDialog(product?: any, variant?: any) {
    setInventoryDraft({
      mode: 'RECEIPT',
      referenceCode: generateReceiptCode(),
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
            next.imeis = '';
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
      const variantIds = (product?.variants || []).map((variant: any) => String(variant.id));
      return { ...current, selectedVariantIds: variantIds };
    });
  }

  function addSelectedVariantsToReceipt() {
    setInventoryDraft((current) => {
      if (!current?.selectedProductId) return current;
      const product = resolveProduct(current.selectedProductId);
      if (!product) return current;
      const variants = product.variants || [];
      const selectedVariants = variants.length > 0
        ? variants.filter((variant: any) => current.selectedVariantIds.includes(String(variant.id)))
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

  async function submitInventoryDraft(event: FormEvent) {
    event.preventDefault();
    if (!inventoryDraft) return;
    if (!inventoryDraft.referenceCode.trim()) {
      window.alert('Vui lòng nhập mã phiếu nhập.');
      return;
    }
    if (!inventoryDraft.supplierName.trim()) {
      window.alert('Vui lòng chọn nhà cung cấp.');
      return;
    }

    const payloadLines = [];
    for (const [index, line] of inventoryDraft.lines.entries()) {
      const product = resolveProduct(line.productId);
      if (!product) {
        window.alert(`Dòng ${index + 1}: vui lòng chọn sản phẩm.`);
        return;
      }
      const variants = product.variants || [];
      if (variants.length > 1 && !line.variantId) {
        window.alert(`Dòng ${index + 1}: sản phẩm có nhiều biến thể, vui lòng chọn biến thể.`);
        return;
      }
      if (!Number.isFinite(line.quantity) || line.quantity <= 0) {
        window.alert(`Dòng ${index + 1}: số lượng nhập phải lớn hơn 0.`);
        return;
      }
      const tracksImei = categoryTracksImei(product);
      const imeis = splitImeis(line.imeis);
      if (tracksImei && imeis.length !== line.quantity) {
        window.alert(`Dòng ${index + 1}: sản phẩm cần đúng ${line.quantity} IMEI.`);
        return;
      }
      if (!tracksImei && imeis.length > 0) {
        window.alert(`Dòng ${index + 1}: sản phẩm này không bật quản lý IMEI.`);
        return;
      }
      payloadLines.push({
        productId: line.productId,
        variantId: line.variantId || null,
        quantity: line.quantity,
        unitCost: Number.isFinite(line.unitCost) && line.unitCost > 0 ? line.unitCost : null,
        reason: line.reason || 'Nhập kho',
        note: line.note || null,
        imeis,
      });
    }

    await adminInventoryApi.adminCreateReceipt({
      referenceCode: inventoryDraft.referenceCode.trim(),
      supplierName: inventoryDraft.supplierName.trim(),
      note: inventoryDraft.note || null,
      locationCode: DEFAULT_LOCATION_CODE,
      locationName: DEFAULT_LOCATION_NAME,
      lines: payloadLines,
    });
    setInventoryDraft(null);
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
    inventoryReceipts,
    setInventoryReceipts,
    setInventoryDraft,
    loadInventoryReceipts,
    suppliers,
    openInventoryDialog,
    openReceiptDialog,
    addReceiptLine,
    removeReceiptLine,
    updateReceiptLine,
    resolveProduct,
    resolveVariant,
    categoryTracksImei,
    productMatchesReceiptFilters,
    selectReceiptPickerProduct,
    toggleReceiptVariantSelection,
    clearReceiptVariantSelection,
    selectAllPickerVariants,
    addSelectedVariantsToReceipt,
    submitInventoryDraft,
    exportInventorySnapshot,
  };
}
