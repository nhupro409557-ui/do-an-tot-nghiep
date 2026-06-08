import { AdminBadge, AdminPanel, AdminTable, Checkbox, Input, RowActions, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';
import { Plus, X } from 'lucide-react';
import { matchesSearch } from '../../admin-shell/pages/AdminDashboardConfig';

type AdminServicesTabProps = Record<string, any>;

export default function AdminServicesTab(props: AdminServicesTabProps) {
  const {
    attachedServices,
    currency,
    deactivateService,
    deleteService,
    editService,
    editingServiceId,
    handleServiceSubmit,
    query,
    reactivateService,
    resetServiceForm,
    serviceAttributeGroupLabel,
    serviceAttributeGroupOptions,
    serviceForm,
    serviceFormOpen,
    setQuery,
    setServiceForm,
    setServiceFormOpen,
    warrantyDurationOptions,
  } = props;

  return (
    <AdminPanel
      title="Quản lý dịch vụ đi kèm"
      action={
        <button type="button" onClick={() => { resetServiceForm(); setServiceFormOpen(true); }} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"><Plus className="h-4 w-4" /> Thêm</button>
      }
      filters={
        <SearchBox value={query} onChange={setQuery} placeholder="Tìm dịch vụ, mã, nhóm" />
      }
    >
      {serviceFormOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">{editingServiceId ? 'Đang chỉnh sửa dịch vụ' : 'Thêm dịch vụ đi kèm'}</h3>
                <p className="mt-1 text-sm text-slate-500">Tạo các gói bảo hành, 1 đổi 1, lắp đặt, vệ sinh hoặc hỗ trợ để chọn trong form sản phẩm.</p>
              </div>
              <button type="button" onClick={resetServiceForm} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">
              <form onSubmit={handleServiceSubmit} className="grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
                <Input label="Mã dịch vụ" value={serviceForm.code} required onChange={(value) => setServiceForm({ ...serviceForm, code: value })} />
                <Input label="Tên dịch vụ" value={serviceForm.name} required onChange={(value) => setServiceForm({ ...serviceForm, name: value })} />
                <Select label="Loại dịch vụ" value={serviceForm.serviceType} onChange={(value) => setServiceForm({ ...serviceForm, serviceType: value, attributeGroup: value === 'PRODUCT_SERVICE' && !serviceForm.attributeGroup ? 'WARRANTY' : serviceForm.attributeGroup, priceMode: value === 'PRODUCT_SERVICE' ? 'TIERED_AMOUNT' : serviceForm.priceMode, fixedPrice: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.fixedPrice, percentValue: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.percentValue, baseAmount: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.baseAmount })} options={[['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'], ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ']]} />
                <Select label="Nhóm dịch vụ" value={serviceForm.attributeGroup} onChange={(value) => setServiceForm({ ...serviceForm, attributeGroup: value })} options={[['', 'Chọn nhóm'], ...serviceAttributeGroupOptions]} />
                <Select label="Thời hạn" value={String(serviceForm.durationMonths || 0)} onChange={(value) => setServiceForm({ ...serviceForm, durationMonths: Number(value) })} options={warrantyDurationOptions} />
                {serviceForm.serviceType === 'PRODUCT_SERVICE' ? (
                  <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 md:col-span-4">Biểu phí theo chính sách</div>
                ) : (
                  <>
                    <Select label="Cách tính giá" value={serviceForm.priceMode} onChange={(value) => setServiceForm({ ...serviceForm, priceMode: value })} options={[['FIXED', 'Giá cố định'], ['PERCENT', 'Theo % sản phẩm'], ['TIERED_AMOUNT', 'Theo định mức']]} />
                    <Input label="Giá cố định" type="number" value={serviceForm.fixedPrice} onChange={(value) => setServiceForm({ ...serviceForm, fixedPrice: Number(value) })} />
                    <Input label="Phần trăm" type="number" value={serviceForm.percentValue} onChange={(value) => setServiceForm({ ...serviceForm, percentValue: Number(value) })} />
                    <Input label="Định mức" type="number" value={serviceForm.baseAmount} onChange={(value) => setServiceForm({ ...serviceForm, baseAmount: Number(value) })} />
                  </>
                )}
                <Checkbox label="Đang bật" checked={serviceForm.isActive} onChange={(checked) => setServiceForm({ ...serviceForm, isActive: checked })} />
                <SubmitButtons editing={Boolean(editingServiceId)} onCancel={resetServiceForm} />
              </form>
            </div>
          </div>
        </div>
      )}
      <AdminTable headers={['Mã', 'Tên dịch vụ', 'Loại', 'Nhóm', 'Thời hạn', 'Giá', 'Trạng thái', 'Thao tác']}>
        {attachedServices.filter((item: any) => matchesSearch(item, query, ['code', 'name', 'serviceType', 'attributeGroup'])).map((service: any) => (
          <tr key={service.id}>
            <td className="px-4 py-3 font-mono text-xs">{service.code}</td>
            <td className="px-4 py-3 font-semibold text-slate-900">{service.name}</td>
            <td className="px-4 py-3">{service.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}</td>
            <td className="px-4 py-3">{serviceAttributeGroupLabel[service.attributeGroup] || service.attributeGroup || '-'}</td>
            <td className="px-4 py-3">{service.durationMonths ? `${service.durationMonths} tháng` : '-'}</td>
            <td className="px-4 py-3">{service.priceMode === 'PERCENT' ? `${service.percentValue || 0}%` : service.priceMode === 'TIERED_AMOUNT' ? 'Theo biểu phí' : currency.format(Number(service.fixedPrice || service.baseAmount || 0))}</td>
            <td className="px-4 py-3"><AdminBadge tone={service.isActive ? 'green' : 'slate'}>{service.isActive ? 'Đang bật' : 'Tạm tắt'}</AdminBadge></td>
            <td className="px-4 py-3">
              <RowActions
                onEdit={() => editService(service)}
                onHide={service.isActive ? () => deactivateService(service) : undefined}
                onRestore={!service.isActive ? () => reactivateService(service) : undefined}
                onDelete={() => deleteService(service)}
              />
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
