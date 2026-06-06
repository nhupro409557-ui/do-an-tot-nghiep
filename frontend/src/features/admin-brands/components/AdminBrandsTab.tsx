import React from 'react';
import { Edit2, EyeOff, RotateCcw, Trash2 } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, BrandLogo, CollapsibleSection, FileInput, Input, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';
import { slugifyText } from '../../admin-shell/pages/AdminDashboardConfig';
import { resolveImageUrl } from '../../../services/productMedia';
import { brandApi } from '../../../services/brandApi';

type AdminBrandsTabProps = Record<string, any>;

export default function AdminBrandsTab(props: AdminBrandsTabProps) {
  const {
    activeBrandImportJob,
    brandCodeStatus,
    brandCloseSignal,
    brandForm,
    brandImportJobs,
    brandImportMode,
    brandPage,
    brandStatusFilter,
    brandTotal,
    bulkUpdateBrandStatus,
    checkBrandCodeOnBlur,
    confirmDelete,
    editBrand,
    editingBrandId,
    filteredBrands,
    handleBrandImportFile,
    handleBrandSubmit,
    hideBrand,
    query,
    reactivateBrand,
    resetBrandForm,
    selectedBrandIds,
    setBrandCodeStatus,
    setBrandForm,
    setBrandImportMode,
    setBrandPage,
    setBrandStatusFilter,
    setQuery,
    setSelectedBrandIds,
    uploadFiles,
  } = props;

  const logoPreviewUrl = resolveImageUrl(brandForm.logoUrl);

  return (
    <AdminPanel
      title="Quản lý thương hiệu và logo"
      filters={
        <>
          <Select noLabel={true} label="Trạng thái" value={brandStatusFilter} onChange={setBrandStatusFilter} options={[['all', 'Tất cả'], ['active', 'Đang hiển thị'], ['inactive', 'Đã ẩn']]} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm thương hiệu, mã" />
        </>
      }
    >
      <CollapsibleSection title={editingBrandId ? 'Đang chỉnh sửa thương hiệu' : 'Thêm thương hiệu mới'} description="Mở khi cần tạo hoặc cập nhật tên, mã và logo thương hiệu." defaultOpen={false} forceOpen={Boolean(editingBrandId)} forceOpenKey={editingBrandId} closeSignal={brandCloseSignal} onClose={resetBrandForm}>
        <form onSubmit={handleBrandSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-6">
          <Input label="Tên thương hiệu" value={brandForm.name} required onChange={(value) => setBrandForm({ ...brandForm, name: value, slug: brandForm.slug || slugifyText(value) })} />
          <Input label="Mã thương hiệu" value={brandForm.code} required onBlur={checkBrandCodeOnBlur} onChange={(value) => { setBrandCodeStatus('idle'); setBrandForm({ ...brandForm, code: value }); }} />
          <Input label="Slug landing" value={brandForm.slug} onChange={(value) => setBrandForm({ ...brandForm, slug: value })} />
          <Input label="Thứ tự" type="number" value={brandForm.order} onChange={(value) => setBrandForm({ ...brandForm, order: Number(value) })} />
          <FileInput label="Logo từ máy tính" accept="image/*" onFiles={async (files) => {
            const urls = await uploadFiles(files, 'brands');
            setBrandForm({ ...brandForm, logoUrl: urls[0] || brandForm.logoUrl });
          }} />
          <Input label="Alt text logo" value={brandForm.logoAltText} onChange={(value) => setBrandForm({ ...brandForm, logoAltText: value })} />
          {logoPreviewUrl && (
            <div className="md:col-span-6">
              <div className="mb-2 text-xs font-bold text-slate-500">Xem trước logo</div>
              <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:flex-row sm:items-center">
                <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-2">
                  <img src={logoPreviewUrl} alt={brandForm.logoAltText || brandForm.name || 'Logo thương hiệu'} className="max-h-full max-w-full object-contain" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-semibold text-slate-500">{brandForm.logoUrl}</div>
                  <button type="button" onClick={() => setBrandForm({ ...brandForm, logoUrl: '' })} className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
                    Xóa logo đã chọn
                  </button>
                </div>
              </div>
            </div>
          )}
          <Input label="Tiêu đề landing" value={brandForm.landingTitle} onChange={(value) => setBrandForm({ ...brandForm, landingTitle: value })} />
          <div className="text-xs font-semibold text-slate-500 md:col-span-2">{brandCodeStatus === 'checking' ? 'Đang kiểm tra mã...' : brandCodeStatus === 'available' ? 'Mã có thể dùng' : brandCodeStatus === 'taken' ? 'Mã đã tồn tại' : ''}</div>
          <SubmitButtons editing={Boolean(editingBrandId)} onCancel={resetBrandForm} />
        </form>
      </CollapsibleSection>
      <CollapsibleSection title="Import thương hiệu hàng loạt" description="Upload CSV có cột: Tên, Mã, Logo URL, Thứ tự. Dữ liệu có dấu phẩy nên đặt trong dấu ngoặc kép." defaultOpen={false}>
        <div className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4">
          <Select label="Chế độ import" value={brandImportMode} onChange={setBrandImportMode} options={[['skip', 'Thêm mới, bỏ qua trùng'], ['upsert', 'Thêm mới, cập nhật theo mã']]} />
          <FileInput label="File CSV" accept=".csv,text/csv" onFiles={handleBrandImportFile} />
          {activeBrandImportJob && (
            <div className="rounded-md bg-white p-3 text-sm text-slate-700">
              <div className="mb-2 flex justify-between">
                <span>Job {activeBrandImportJob.id}</span>
                <span>{activeBrandImportJob.status} - {activeBrandImportJob.progress || 0}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full bg-red-600" style={{ width: `${activeBrandImportJob.progress || 0}%` }} />
              </div>
              <div className="mt-2 text-xs text-slate-500">
                Đã xử lý {activeBrandImportJob.processedRows || 0}/{activeBrandImportJob.totalRows || 0} dòng,
                thêm {activeBrandImportJob.importedRows || 0}, cập nhật {activeBrandImportJob.updatedRows || 0}, bỏ qua {activeBrandImportJob.skippedRows || 0}
              </div>
              {activeBrandImportJob.errorMessage && <div className="mt-2 text-xs font-semibold text-red-600">{activeBrandImportJob.errorMessage}</div>}
            </div>
          )}
          <div className="rounded-md bg-white p-3 text-xs text-slate-600">
            {brandImportJobs.slice(0, 3).map((job: any) => (
              <div key={job.id} className="border-b border-slate-100 py-2 last:border-0">
                <div className="flex flex-wrap justify-between gap-2">
                  <span>{job.sourceFilename || 'Import thủ công'} - {job.mode} - {job.status}</span>
                  <span>Thêm {job.importedRows}, cập nhật {job.updatedRows}, bỏ qua {job.skippedRows}</span>
                </div>
                {Array.isArray(job.report) && job.report.length > 0 && (
                  <details className="mt-1">
                    <summary className="cursor-pointer font-semibold text-slate-500">Xem dòng bị bỏ qua</summary>
                    <div className="mt-1 space-y-1">
                      {job.report.slice(0, 5).map((item: any, index: number) => <div key={`${job.id}-${index}`}>Dòng {item.row}: {item.reason}</div>)}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      </CollapsibleSection>
      {selectedBrandIds.length > 0 && <div className="mb-3 flex gap-2"><button type="button" onClick={() => bulkUpdateBrandStatus(false)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Ẩn đã chọn</button><button type="button" onClick={() => bulkUpdateBrandStatus(true)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Khôi phục đã chọn</button></div>}
      <AdminTable
        headers={['', 'Logo', 'Thương hiệu', 'Mã', 'Landing', 'Sản phẩm', 'Số danh mục', 'Thứ tự', 'Cập nhật', 'Trạng thái', 'Thao tác']}
        currentPage={brandPage}
        totalPages={Math.max(1, Math.ceil(brandTotal / 10))}
        onPageChange={setBrandPage}
        totalCount={brandTotal}
        itemName="thương hiệu"
      >
        {filteredBrands.map((brand: any) => (
          <tr key={brand.id}>
            <td className="px-4 py-3"><input type="checkbox" checked={selectedBrandIds.includes(brand.id)} onChange={(event) => setSelectedBrandIds((ids: string[]) => event.target.checked ? [...ids, brand.id] : ids.filter((id) => id !== brand.id))} /></td>
            <td className="px-4 py-3"><BrandLogo brand={brand} /></td>
            <td className="px-4 py-3 font-semibold text-slate-900">{brand.name}</td>
            <td className="px-4 py-3 font-mono text-xs">{brand.code || '-'}</td>
            <td className="px-4 py-3 text-xs text-red-600">{brand.slug ? `/brands/${brand.slug}` : '-'}</td>
            <td className="px-4 py-3">{brand.productCount || 0}</td>
            <td className="px-4 py-3">{brand.categoryIds?.length || 0}</td>
            <td className="px-4 py-3">{brand.order || 0}</td>
            <td className="px-4 py-3 text-xs">{brand.updatedAt ? new Date(brand.updatedAt).toLocaleString('vi-VN') : '-'}</td>
            <td className="px-4 py-3"><AdminBadge tone={brand.isActive ? 'green' : 'slate'}>{brand.isActive ? 'ACTIVE' : 'INACTIVE'}</AdminBadge></td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => editBrand(brand)}
                  title="Sửa"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                {brand.isActive ? (
                  <button
                    type="button"
                    onClick={() => hideBrand(brand)}
                    title="Ẩn"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                  >
                    <EyeOff className="h-4 w-4" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => reactivateBrand(brand)}
                    title="Khôi phục"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-emerald-200 bg-white text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-50"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => confirmDelete(brand.name, () => brandApi.adminDeleteBrand(brand.id))}
                  title="Xóa"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-red-200 bg-white text-red-600 transition hover:border-red-300 hover:bg-red-50"
                >
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
