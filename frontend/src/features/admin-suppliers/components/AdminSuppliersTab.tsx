import { Edit2, EyeOff, Plus, RotateCcw, Trash2, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, Input, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';

type AdminSuppliersTabProps = Record<string, any>;

export default function AdminSuppliersTab(props: AdminSuppliersTabProps) {
  const {
    bulkUpdateSupplierStatus,
    checkSupplierCodeOnBlur,
    deleteSupplier,
    editSupplier,
    editingSupplierId,
    filteredSuppliers,
    handleSupplierSubmit,
    hideSupplier,
    query,
    reactivateSupplier,
    resetSupplierForm,
    selectedSupplierIds,
    setQuery,
    setSelectedSupplierIds,
    setSupplierCodeStatus,
    setSupplierForm,
    setSupplierFormOpen,
    setSupplierPage,
    setSupplierStatusFilter,
    supplierCodeStatus,
    supplierForm,
    supplierFormOpen,
    supplierPage,
    supplierStatusFilter,
    supplierTotal,
  } = props;

  return (
    <AdminPanel
      title="Quản lý nhà cung cấp"
      action={
        <button
          type="button"
          onClick={() => { resetSupplierForm(); setSupplierFormOpen(true); }}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"
        >
          <Plus className="h-4 w-4" /> Thêm
        </button>
      }
      filters={
        <>
          <Select noLabel={true} label="Trạng thái" value={supplierStatusFilter} onChange={setSupplierStatusFilter} options={[['all', 'Tất cả'], ['active', 'Đang hoạt động'], ['inactive', 'Đã ẩn']]} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm nhà cung cấp, mã, liên hệ, số điện thoại" />
        </>
      }
    >
      {supplierFormOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">{editingSupplierId ? 'Chỉnh sửa nhà cung cấp' : 'Thêm nhà cung cấp'}</h3>
              </div>
              <button type="button" onClick={() => { setSupplierFormOpen(false); resetSupplierForm(); }} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleSupplierSubmit} className="grid gap-3 p-5 md:grid-cols-6">
              <Input label="Tên nhà cung cấp" value={supplierForm.name} required onChange={(value) => setSupplierForm({ ...supplierForm, name: value })} />
              <Input label="Mã nhà cung cấp" value={supplierForm.code} required onBlur={checkSupplierCodeOnBlur} onChange={(value) => { setSupplierCodeStatus('idle'); setSupplierForm({ ...supplierForm, code: value }); }} />
              <Input label="Người liên hệ" value={supplierForm.contactName} onChange={(value) => setSupplierForm({ ...supplierForm, contactName: value })} />
              <Input label="Số điện thoại" value={supplierForm.phone} onChange={(value) => setSupplierForm({ ...supplierForm, phone: value })} />
              <Input label="Email" type="email" value={supplierForm.email} onChange={(value) => setSupplierForm({ ...supplierForm, email: value })} />
              <Input label="Mã số thuế" value={supplierForm.taxCode} onChange={(value) => setSupplierForm({ ...supplierForm, taxCode: value })} />
              <Input label="Website" value={supplierForm.website} onChange={(value) => setSupplierForm({ ...supplierForm, website: value })} />
              <Input label="Địa chỉ" value={supplierForm.address} onChange={(value) => setSupplierForm({ ...supplierForm, address: value })} />
              <Input label="Ghi chú" value={supplierForm.note} onChange={(value) => setSupplierForm({ ...supplierForm, note: value })} />
              <Select label="Trạng thái" value={supplierForm.isActive ? 'active' : 'inactive'} onChange={(value) => setSupplierForm({ ...supplierForm, isActive: value === 'active' })} options={[['active', 'Đang hoạt động'], ['inactive', 'Đã ẩn']]} />
              <div className="text-xs font-semibold text-slate-500 md:col-span-6">
                {supplierCodeStatus === 'checking' ? 'Đang kiểm tra mã...' : supplierCodeStatus === 'available' ? 'Mã có thể dùng' : supplierCodeStatus === 'taken' ? 'Mã đã tồn tại' : ''}
              </div>
              <div className="md:col-span-6">
                <SubmitButtons editing={Boolean(editingSupplierId)} onCancel={() => { setSupplierFormOpen(false); resetSupplierForm(); }} />
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedSupplierIds.length > 0 && (
        <div className="mb-3 flex gap-2">
          <button type="button" onClick={() => bulkUpdateSupplierStatus(false)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Ẩn đã chọn</button>
          <button type="button" onClick={() => bulkUpdateSupplierStatus(true)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Khôi phục đã chọn</button>
        </div>
      )}

      <AdminTable
        headers={['', 'Nhà cung cấp', 'Mã', 'Liên hệ', 'Số điện thoại', 'Email', 'Mã số thuế', 'Cập nhật', 'Trạng thái', 'Thao tác']}
        currentPage={supplierPage}
        totalPages={Math.max(1, Math.ceil(supplierTotal / 10))}
        onPageChange={setSupplierPage}
        totalCount={supplierTotal}
        itemName="nhà cung cấp"
      >
        {filteredSuppliers.map((supplier: any) => (
          <tr key={supplier.id}>
            <td className="px-4 py-3"><input type="checkbox" checked={selectedSupplierIds.includes(supplier.id)} onChange={(event) => setSelectedSupplierIds((ids: string[]) => event.target.checked ? [...ids, supplier.id] : ids.filter((id) => id !== supplier.id))} /></td>
            <td className="px-4 py-3">
              <div className="font-semibold text-slate-900">{supplier.name}</div>
              <div className="text-xs text-slate-500">{supplier.address || supplier.website || '-'}</div>
            </td>
            <td className="px-4 py-3 font-mono text-xs">{supplier.code}</td>
            <td className="px-4 py-3">{supplier.contactName || '-'}</td>
            <td className="px-4 py-3">{supplier.phone || '-'}</td>
            <td className="px-4 py-3">{supplier.email || '-'}</td>
            <td className="px-4 py-3">{supplier.taxCode || '-'}</td>
            <td className="px-4 py-3 text-xs">{supplier.updatedAt ? new Date(supplier.updatedAt).toLocaleString('vi-VN') : '-'}</td>
            <td className="px-4 py-3"><AdminBadge tone={supplier.isActive ? 'green' : 'slate'}>{supplier.isActive ? 'Đang hoạt động' : 'Đã ẩn'}</AdminBadge></td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-2">
                <button type="button" onClick={() => editSupplier(supplier)} title="Sửa" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
                  <Edit2 className="h-4 w-4" />
                </button>
                {supplier.isActive ? (
                  <button type="button" onClick={() => hideSupplier(supplier)} title="Ẩn" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
                    <EyeOff className="h-4 w-4" />
                  </button>
                ) : (
                  <button type="button" onClick={() => reactivateSupplier(supplier)} title="Khôi phục" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-emerald-200 bg-white text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-50">
                    <RotateCcw className="h-4 w-4" />
                  </button>
                )}
                <button type="button" onClick={() => deleteSupplier(supplier)} title="Xóa" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-red-200 bg-white text-red-600 transition hover:border-red-300 hover:bg-red-50">
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
