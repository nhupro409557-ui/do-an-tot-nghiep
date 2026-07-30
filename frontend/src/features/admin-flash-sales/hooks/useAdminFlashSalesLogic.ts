import type React from 'react';
import { useMemo, useState } from 'react';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { adminFlashSalesApi } from '../services/adminFlashSalesApi';

export type FlashSaleForm = {
  productId: string;
  variantId: string;
  discountType: 'PERCENT' | 'FIXED';
  discountValue: number;
  quantityLimit: string;
  perUserLimit: string;
  startsAt: string;
  endsAt: string;
  status: 'ACTIVE' | 'INACTIVE';
};

const emptyFlashSaleForm: FlashSaleForm = {
  productId: '',
  variantId: '',
  discountType: 'PERCENT',
  discountValue: 10,
  quantityLimit: '',
  perUserLimit: '',
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
  categories: any[];
  brands: any[];
  query: string;
  reloadCurrentTab: () => Promise<void>;
}) {
  const { flashSales, products, categories, brands, query, reloadCurrentTab } = params;
  const [flashSaleForm, setFlashSaleForm] = useState<FlashSaleForm>(emptyFlashSaleForm);
  const [editingFlashSaleId, setEditingFlashSaleId] = useState<string | null>(null);
  const [flashSaleCategoryFilter, setFlashSaleCategoryFilter] = useState('');
  const [flashSaleBrandFilter, setFlashSaleBrandFilter] = useState('');
  const [flashSaleStatusFilter, setFlashSaleStatusFilter] = useState('');
  const [flashSaleProductSearch, setFlashSaleProductSearch] = useState('');

  const flashSaleProductChoices = useMemo(() => {
    const needle = flashSaleProductSearch.trim().toLowerCase();
    return products
      .filter((product: any) => !needle || `${product.name || ''} ${product.sku || ''} ${product.brand || ''}`.toLowerCase().includes(needle));
  }, [flashSaleProductSearch, products]);

  const filteredFlashSales = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return flashSales.filter((item) => {
      const product = products.find((candidate: any) => String(candidate.id) === String(item.productId));
      const matchesQuery = !needle || `${item.productName || ''} ${item.productSku || ''} ${item.status || ''}`.toLowerCase().includes(needle);
      const matchesCategory = !flashSaleCategoryFilter
        || String(product?.categoryId || '') === flashSaleCategoryFilter
        || String(product?.subcategoryId || '') === flashSaleCategoryFilter;
      const matchesBrand = !flashSaleBrandFilter || String(product?.brandId || '') === flashSaleBrandFilter;
      const runningStatus = item.isExhausted ? 'INACTIVE' : item.isRunning ? 'RUNNING' : item.status === 'ACTIVE' ? 'SCHEDULED' : 'INACTIVE';
      return matchesQuery && matchesCategory && matchesBrand && (!flashSaleStatusFilter || runningStatus === flashSaleStatusFilter);
    });
  }, [flashSaleBrandFilter, flashSaleCategoryFilter, flashSaleStatusFilter, flashSales, products, query]);

  const flashSaleCategoryOptions = useMemo(() => [
    ['', 'Tất cả danh mục'],
    ...categories.map((item: any) => [String(item.id), item.name] as [string, string]),
  ], [categories]);

  const flashSaleBrandOptions = useMemo(() => [
    ['', 'Tất cả thương hiệu'],
    ...brands.map((item: any) => [String(item.id), item.name] as [string, string]),
  ], [brands]);

  const resetFlashSaleForm = () => {
    setFlashSaleForm(emptyFlashSaleForm);
    setEditingFlashSaleId(null);
  };

  const editFlashSale = (item: any) => {
    setEditingFlashSaleId(item.id);
    setFlashSaleForm({
      productId: item.productId || '',
      variantId: item.variantId || '',
      discountType: item.discountType === 'FIXED' ? 'FIXED' : 'PERCENT',
      discountValue: Number(item.discountValue || 0),
      quantityLimit: item.quantityLimit ? String(item.quantityLimit) : '',
      perUserLimit: item.perUserLimit ? String(item.perUserLimit) : '',
      startsAt: toLocalDateTime(item.startsAt),
      endsAt: toLocalDateTime(item.endsAt),
      status: item.status === 'INACTIVE' ? 'INACTIVE' : 'ACTIVE',
    });
  };

  const flashSalePayload = () => ({
    productId: flashSaleForm.productId,
    variantId: flashSaleForm.variantId || null,
    discountType: flashSaleForm.discountType,
    discountValue: Number(flashSaleForm.discountValue || 0),
    quantityLimit: flashSaleForm.quantityLimit.trim() ? Number(flashSaleForm.quantityLimit) : null,
    perUserLimit: flashSaleForm.perUserLimit.trim() ? Number(flashSaleForm.perUserLimit) : null,
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
    const quantityLimitText = flashSaleForm.quantityLimit.trim();
    const quantityLimitNumber = Number(quantityLimitText);
    if (quantityLimitText && (!Number.isInteger(quantityLimitNumber) || quantityLimitNumber < 1)) {
      alert('Số lượng sale phải lớn hơn 0 hoặc để trống nếu không giới hạn.');
      return false;
    }
    const perUserLimitText = flashSaleForm.perUserLimit.trim();
    const perUserLimitNumber = Number(perUserLimitText);
    if (perUserLimitText && (!Number.isInteger(perUserLimitNumber) || perUserLimitNumber < 1)) {
      alert('Giới hạn mỗi khách phải lớn hơn 0 hoặc để trống nếu không giới hạn.');
      return false;
    }
    try {
      if (editingFlashSaleId) {
        await adminFlashSalesApi.adminUpdateFlashSale(editingFlashSaleId, flashSalePayload());
        notifyAdmin('Đã cập nhật flash sale.');
      } else {
        await adminFlashSalesApi.adminCreateFlashSale(flashSalePayload());
        notifyAdmin('Đã thêm flash sale.');
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
    await adminFlashSalesApi.adminDeleteFlashSale(item.id);
    await reloadCurrentTab();
  };

  return {
    flashSaleForm,
    setFlashSaleForm,
    editingFlashSaleId,
    flashSaleProductChoices,
    flashSaleProductSearch,
    setFlashSaleProductSearch,
    flashSaleCategoryFilter,
    setFlashSaleCategoryFilter,
    flashSaleBrandFilter,
    setFlashSaleBrandFilter,
    flashSaleStatusFilter,
    setFlashSaleStatusFilter,
    flashSaleCategoryOptions,
    flashSaleBrandOptions,
    filteredFlashSales,
    resetFlashSaleForm,
    editFlashSale,
    handleFlashSaleSubmit,
    deleteFlashSale,
  };
}
