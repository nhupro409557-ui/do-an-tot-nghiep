import { useState, type FormEvent } from 'react';
import { apiDb } from '../../../services/apiDb';
import { getInventorySettings } from '../AdminDashboardConfig';

type InventoryDraft = {
  product: any;
  variant?: any;
  transactionType: string;
  delta: number;
  referenceCode: string;
  reason: string;
  note: string;
  supplierName: string;
  unitCost: number;
  locationCode: string;
  locationName: string;
  imeis: string;
  minimumStock: number;
  blockSaleWhenOutOfStock: boolean;
  cycleCountDays: number;
  logs: any[];
};

type UseAdminInventoryLogicParams = {
  query: string;
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminInventoryLogic({ query, reloadCurrentTab }: UseAdminInventoryLogicParams) {
  const [inventoryDraft, setInventoryDraft] = useState<InventoryDraft | null>(null);

  async function openInventoryDialog(product: any, variant?: any) {
    const detail = await apiDb.adminGetProductInventory(product.id);
    const inventorySettings = getInventorySettings(detail);
    setInventoryDraft({
      product,
      variant,
      transactionType: 'RECEIPT',
      delta: 1,
      referenceCode: '',
      reason: variant ? `Điều chỉnh ${variant.sku || 'biến thể'}` : `Điều chỉnh ${product.sku || product.name}`,
      note: '',
      supplierName: '',
      unitCost: 0,
      locationCode: detail.preferredLocationCode || inventorySettings.preferredLocationCode || '',
      locationName: detail.preferredLocationName || inventorySettings.preferredLocationName || '',
      imeis: '',
      minimumStock: detail.minimumStock ?? inventorySettings.minimumStock,
      blockSaleWhenOutOfStock: detail.blockSaleWhenOutOfStock ?? inventorySettings.blockSaleWhenOutOfStock,
      cycleCountDays: detail.cycleCountDays ?? inventorySettings.cycleCountDays,
      logs: detail.logs || [],
    });
  }

  async function submitInventoryDraft(event: FormEvent) {
    event.preventDefault();
    if (!inventoryDraft) return;
    if (!inventoryDraft.referenceCode.trim()) {
      window.alert('Vui lòng nhập mã phiếu tham chiếu.');
      return;
    }
    if (!Number.isFinite(inventoryDraft.delta) || inventoryDraft.delta === 0) {
      window.alert('Số lượng thay đổi phải khác 0.');
      return;
    }
    await apiDb.adminUpdateInventorySettings(inventoryDraft.product.id, {
      minimumStock: inventoryDraft.minimumStock,
      blockSaleWhenOutOfStock: inventoryDraft.blockSaleWhenOutOfStock,
      preferredLocationCode: inventoryDraft.locationCode.trim(),
      preferredLocationName: inventoryDraft.locationName.trim(),
      cycleCountDays: inventoryDraft.cycleCountDays,
    });
    await apiDb.adminAdjustInventory(inventoryDraft.product.id, {
      variantId: inventoryDraft.variant?.id || null,
      delta: inventoryDraft.delta,
      transactionType: inventoryDraft.transactionType,
      referenceCode: inventoryDraft.referenceCode.trim(),
      reason: inventoryDraft.reason || inventoryDraft.transactionType,
      note: inventoryDraft.note || null,
      supplierName: inventoryDraft.supplierName.trim() || null,
      unitCost: Number.isFinite(inventoryDraft.unitCost) && inventoryDraft.unitCost > 0 ? inventoryDraft.unitCost : null,
      locationCode: inventoryDraft.locationCode.trim() || null,
      locationName: inventoryDraft.locationName.trim() || null,
      imeis: inventoryDraft.imeis.split(/[\n,]/).map((item) => item.trim()).filter(Boolean),
    });
    setInventoryDraft(null);
    await reloadCurrentTab();
  }

  async function exportInventorySnapshot() {
    const blob = await apiDb.adminExportInventory(query.trim());
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
    setInventoryDraft,
    openInventoryDialog,
    submitInventoryDraft,
    exportInventorySnapshot,
  };
}
