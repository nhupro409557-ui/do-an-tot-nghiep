import type React from 'react';
import { useState } from 'react';
import { Pencil, Plus, Trash2, X, Zap } from 'lucide-react';
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
    handleFlashSaleSubmit,
    productOptions,
    query,
    resetFlashSaleForm,
    setFlashSaleForm,
    setQuery,
  } = props;
  const [showForm, setShowForm] = useState(false);

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
      action={
        <button
          type="button"
          onClick={openCreateForm}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-3 text-sm font-bold text-white transition hover:bg-red-700"
        >
          <Plus className="h-4 w-4" />
          Tạo flash sale
        </button>
      }
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm đang flash sale" />}
    >
      {showForm && (
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
                <Select label="Sản phẩm" value={flashSaleForm.productId} onChange={(value) => setFlashSaleForm({ ...flashSaleForm, productId: value })} options={productOptions} />
              </div>
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
                  <div className="text-xs text-slate-500">{item.productSku || item.productId}</div>
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
                <button type="button" onClick={() => openEditForm(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50" title="Sửa flash sale">
                  <Pencil className="h-4 w-4" />
                </button>
                <button type="button" onClick={() => deleteFlashSale(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-red-100 text-red-600 hover:bg-red-50" title="Xóa flash sale">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
