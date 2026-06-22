import type React from 'react';
import { useState } from 'react';
import { Check, Pencil, Plus, Search, Trash2, X, Zap } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, Input, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';

type AdminFlashSalesTabProps = Record<string, any>;

export default function AdminFlashSalesTab(props: AdminFlashSalesTabProps) {
  const {
    currency,
    deleteFlashSale,
    editFlashSale,
    editingFlashSaleId,
    filteredFlashSales,
    flashSaleForm,
    flashSaleBrandFilter,
    flashSaleBrandOptions,
    flashSaleCategoryFilter,
    flashSaleCategoryOptions,
    flashSaleProductChoices,
    flashSaleProductSearch,
    flashSaleStatusFilter,
    handleFlashSaleSubmit,
    products,
    query,
    resetFlashSaleForm,
    setFlashSaleForm,
    setFlashSaleBrandFilter,
    setFlashSaleCategoryFilter,
    setFlashSaleProductSearch,
    setFlashSaleStatusFilter,
    setQuery,
    usePermission,
  } = props;
  const [showForm, setShowForm] = useState(false);
  const canManageFlashSale = usePermission('product:update');
  const selectedFlashSaleProduct = (products || flashSaleProductChoices).find(
    (product: any) => String(product.id) === String(flashSaleForm.productId),
  );
  const variantOptions = [
    ['', 'Toàn bộ sản phẩm'],
    ...((selectedFlashSaleProduct?.variants || []).map((variant: any) => [
      String(variant.id),
      [variant.sku, variant.configuration, variant.storage, variant.ram, variant.colorName].filter(Boolean).join(' · '),
    ])),
  ];

  const openCreateForm = () => {
    resetFlashSaleForm();
    setShowForm(true);
  };

  const openEditForm = (item: any) => {
    editFlashSale(item);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    resetFlashSaleForm();
  };

  const submitForm = async (event: React.FormEvent) => {
    const saved = await handleFlashSaleSubmit(event);
    if (saved) setShowForm(false);
  };

  return (
    <AdminPanel
      title="Quản lý flash sale"
      action={canManageFlashSale ? (
        <button
          type="button"
          onClick={openCreateForm}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-3 text-sm font-bold text-white transition hover:bg-red-700"
        >
          <Plus className="h-4 w-4" />
          Tạo flash sale
        </button>
      ) : undefined}
      filters={(
        <div className="relative z-10 grid items-end gap-3 pb-1 sm:grid-cols-2 xl:grid-cols-[minmax(280px,1.35fr)_repeat(3,minmax(190px,1fr))]">
          <div>
            <div className="mb-1 text-sm font-semibold text-slate-600">Tìm kiếm</div>
            <SearchBox value={query} onChange={setQuery} placeholder="Tên sản phẩm hoặc SKU" />
          </div>
          <Select label="Danh mục" value={flashSaleCategoryFilter} onChange={setFlashSaleCategoryFilter} options={flashSaleCategoryOptions} />
          <Select label="Thương hiệu" value={flashSaleBrandFilter} onChange={setFlashSaleBrandFilter} options={flashSaleBrandOptions} />
          <Select
            label="Trạng thái"
            value={flashSaleStatusFilter}
            onChange={setFlashSaleStatusFilter}
            options={[['', 'Tất cả trạng thái'], ['RUNNING', 'Đang chạy'], ['SCHEDULED', 'Đã lên lịch'], ['INACTIVE', 'Tạm tắt']]}
          />
        </div>
      )}
    >
      {showForm && canManageFlashSale && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6 backdrop-blur-sm">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h2 className="text-lg font-black text-slate-900">{editingFlashSaleId ? 'Sửa flash sale' : 'Tạo flash sale'}</h2>
                <p className="mt-1 text-sm font-medium text-slate-500">Cài giá sale, thời gian bắt đầu và thời gian kết thúc cho sản phẩm.</p>
              </div>
              <button type="button" onClick={closeForm} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50" title="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={submitForm} className="grid gap-3 p-5 md:grid-cols-2">
              <div className="md:col-span-2">
                <span className="mb-1.5 block text-xs font-bold text-slate-500">Sản phẩm áp dụng</span>
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                  <label className="relative block border-b border-slate-200">
                    <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      value={flashSaleProductSearch}
                      onChange={(event) => setFlashSaleProductSearch(event.target.value)}
                      placeholder="Tìm theo tên, SKU hoặc thương hiệu"
                      className="h-11 w-full bg-white pl-10 pr-4 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                    />
                  </label>
                  <div className="border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500">
                    {flashSaleProductChoices.length} sản phẩm phù hợp
                  </div>
                  <div className="max-h-60 overflow-y-auto p-2">
                    {flashSaleProductChoices.length > 0 ? flashSaleProductChoices.map((product: any) => {
                      const selected = String(product.id) === String(flashSaleForm.productId);
                      return (
                        <button
                          key={product.id}
                          type="button"
                          onClick={() => setFlashSaleForm({ ...flashSaleForm, productId: String(product.id), variantId: '' })}
                          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                            selected ? 'bg-red-50 ring-1 ring-red-200' : 'hover:bg-slate-50'
                          }`}
                        >
                          {product.imageUrl ? (
                            <img src={product.imageUrl} alt="" className="h-10 w-10 shrink-0 rounded-lg border border-slate-100 bg-white object-contain" />
                          ) : (
                            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-400">
                              <Zap className="h-4 w-4" />
                            </span>
                          )}
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-bold text-slate-800">{product.name}</span>
                            <span className="block truncate text-xs text-slate-500">
                              {[product.sku, product.brand].filter(Boolean).join(' · ')}
                            </span>
                          </span>
                          {selected && <Check className="h-5 w-5 shrink-0 text-red-600" />}
                        </button>
                      );
                    }) : (
                      <div className="px-3 py-6 text-center text-sm text-slate-500">Không tìm thấy sản phẩm phù hợp.</div>
                    )}
                  </div>
                </div>
              </div>
              {flashSaleForm.productId && (
                <Select
                  label="Phạm vi áp dụng"
                  value={flashSaleForm.variantId}
                  onChange={(value) => setFlashSaleForm({ ...flashSaleForm, variantId: value })}
                  options={variantOptions}
                />
              )}
              <Select label="Kiểu giảm" value={flashSaleForm.discountType} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, discountType: value as 'PERCENT' | 'FIXED' })} options={[['PERCENT', 'Theo %'], ['FIXED', 'Theo số tiền']]} />
              <Input label={flashSaleForm.discountType === 'PERCENT' ? 'Giảm (%)' : 'Giảm (VND)'} type="number" value={flashSaleForm.discountValue} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, discountValue: Number(value) })} />
              <Input label="Bắt đầu" type="datetime-local" value={flashSaleForm.startsAt} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, startsAt: value })} />
              <Input label="Kết thúc" type="datetime-local" value={flashSaleForm.endsAt} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, endsAt: value })} />
              <Select label="Trạng thái" value={flashSaleForm.status} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, status: value as 'ACTIVE' | 'INACTIVE' })} options={[['ACTIVE', 'Đang bật'], ['INACTIVE', 'Tạm tắt']]} />
              <div className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm font-medium text-slate-600">
                Để trống thời gian bắt đầu để sale có hiệu lực ngay. Để trống thời gian kết thúc nếu sale không có thời hạn.
              </div>
              <div className="md:col-span-2">
                <SubmitButtons editing={Boolean(editingFlashSaleId)} onCancel={closeForm} />
              </div>
            </form>
          </div>
        </div>
      )}

      <AdminTable headers={['Sản phẩm', 'Giá hiện tại', 'Giá flash sale', 'Thời gian', 'Trạng thái', 'Thao tác']}>
        {filteredFlashSales.map((item: any) => (
          <tr key={item.id}>
            <td className="px-4 py-3">
              <div className="flex items-center gap-3">
                {item.imageUrl ? <img src={item.imageUrl} alt="" className="h-11 w-11 rounded-md object-contain" /> : <div className="flex h-11 w-11 items-center justify-center rounded-md bg-red-50 text-red-600"><Zap className="h-5 w-5" /></div>}
                <div>
                  <div className="font-semibold text-slate-900">{item.productName}</div>
                  <div className="text-xs text-slate-500">
                    {item.variantId
                      ? `Biến thể: ${[item.variantSku, item.variantName].filter(Boolean).join(' · ')}`
                      : `Toàn bộ sản phẩm · ${item.productSku || item.productId}`}
                  </div>
                </div>
              </div>
            </td>
            <td className="px-4 py-3 font-semibold text-slate-700">{currency.format(Number(item.currentPrice || 0))}</td>
            <td className="px-4 py-3">
              <div className="font-black text-red-600">{currency.format(Number(item.salePrice || 0))}</div>
              <div className="text-xs font-semibold text-slate-500">
                {item.discountType === 'PERCENT' ? `Giảm ${item.discountValue}%` : `Giảm ${currency.format(Number(item.discountValue || 0))}`}
              </div>
            </td>
            <td className="px-4 py-3 text-sm text-slate-600">
              <div>{item.startsAt ? new Date(item.startsAt).toLocaleString('vi-VN') : 'Có hiệu lực ngay'}</div>
              <div>{item.endsAt ? new Date(item.endsAt).toLocaleString('vi-VN') : 'Không có thời hạn'}</div>
            </td>
            <td className="px-4 py-3">
              <AdminBadge tone={item.isRunning ? 'green' : item.status === 'ACTIVE' ? 'blue' : 'slate'}>
                {item.isRunning ? 'Đang chạy' : item.status === 'ACTIVE' ? 'Đã lên lịch' : 'Tạm tắt'}
              </AdminBadge>
            </td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-2">
                {canManageFlashSale && <button type="button" onClick={() => openEditForm(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50" title="Sửa flash sale">
                  <Pencil className="h-4 w-4" />
                </button>}
                {canManageFlashSale && <button type="button" onClick={() => deleteFlashSale(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-red-100 text-red-600 hover:bg-red-50" title="Xóa flash sale">
                  <Trash2 className="h-4 w-4" />
                </button>}
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
