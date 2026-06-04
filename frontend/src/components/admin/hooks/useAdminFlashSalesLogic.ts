import type React from 'react';
import { useMemo, useState } from 'react';
import { apiDb } from '../../../services/apiDb';

export type FlashSaleForm = {
  productId: string;
  discountType: 'PERCENT' | 'FIXED';
  discountValue: number;
  startsAt: string;
  endsAt: string;
  status: 'ACTIVE' | 'INACTIVE';
};

const emptyFlashSaleForm: FlashSaleForm = {
  productId: '',
  discountType: 'PERCENT',
  discountValue: 10,
  startsAt: '',
  endsAt: '',
  status: 'ACTIVE',
};

function toLocalDateTime(value?: string | null) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

function toIsoOrNull(value: string) {
  return value ? new Date(value).toISOString() : null;
}

export function useAdminFlashSalesLogic(params: {
  flashSales: any[];
  products: any[];
  query: string;
  reloadCurrentTab: () => Promise<void>;
}) {
  const { flashSales, products, query, reloadCurrentTab } = params;
  const [flashSaleForm, setFlashSaleForm] = useState<FlashSaleForm>(emptyFlashSaleForm);
  const [editingFlashSaleId, setEditingFlashSaleId] = useState<string | null>(null);

  const productOptions = useMemo(() => {
    return [
      ['', 'Chọn sản phẩm'],
      ...products.map((product: any) => [
        String(product.id),
        `${product.name}${product.sku ? ` - ${product.sku}` : ''}`,
      ] as [string, string]),
    ];
  }, [products]);

  const filteredFlashSales = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return flashSales;
    return flashSales.filter((item) => `${item.productName || ''} ${item.productSku || ''} ${item.status || ''}`.toLowerCase().includes(needle));
  }, [flashSales, query]);

  const resetFlashSaleForm = () => {
    setFlashSaleForm(emptyFlashSaleForm);
    setEditingFlashSaleId(null);
  };

  const editFlashSale = (item: any) => {
    setEditingFlashSaleId(item.id);
    setFlashSaleForm({
      productId: item.productId || '',
      discountType: item.discountType === 'FIXED' ? 'FIXED' : 'PERCENT',
      discountValue: Number(item.discountValue || 0),
      startsAt: toLocalDateTime(item.startsAt),
      endsAt: toLocalDateTime(item.endsAt),
      status: item.status === 'INACTIVE' ? 'INACTIVE' : 'ACTIVE',
    });
  };

  const flashSalePayload = () => ({
    productId: flashSaleForm.productId,
    discountType: flashSaleForm.discountType,
    discountValue: Number(flashSaleForm.discountValue || 0),
    startsAt: toIsoOrNull(flashSaleForm.startsAt),
    endsAt: toIsoOrNull(flashSaleForm.endsAt),
    status: flashSaleForm.status,
  });

  const handleFlashSaleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!flashSaleForm.productId) {
      alert('Vui lòng chọn sản phẩm cho flash sale.');
      return false;
    }
    try {
      if (editingFlashSaleId) {
        await apiDb.adminUpdateFlashSale(editingFlashSaleId, flashSalePayload());
        alert('Đã cập nhật flash sale.');
      } else {
        await apiDb.adminCreateFlashSale(flashSalePayload());
        alert('Đã thêm flash sale.');
      }
      resetFlashSaleForm();
      await reloadCurrentTab();
      return true;
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể lưu flash sale.');
      return false;
    }
  };

  const deleteFlashSale = async (item: any) => {
    if (!window.confirm(`Xóa flash sale của ${item.productName || 'sản phẩm này'}?`)) return;
    await apiDb.adminDeleteFlashSale(item.id);
    await reloadCurrentTab();
  };

  return {
    flashSaleForm,
    setFlashSaleForm,
    editingFlashSaleId,
    productOptions,
    filteredFlashSales,
    resetFlashSaleForm,
    editFlashSale,
    handleFlashSaleSubmit,
    deleteFlashSale,
  };
}
