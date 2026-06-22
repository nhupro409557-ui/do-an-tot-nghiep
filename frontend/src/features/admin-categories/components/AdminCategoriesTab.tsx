import React from 'react';
import { Download, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { categoryApi } from '../../../services/categoryApi';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, CollapsibleSection, FileInput, Input, MetricCard, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';
import { CategoryTableRow } from './CategoryTableRow';

type AdminCategoriesTabProps = Record<string, any>;

function IdentifierPolicyMigrationPanel({ migrations, onScan, onComplete, onCancel }: any) {
  const [drafts, setDrafts] = React.useState<Record<string, string>>({});
  const [error, setError] = React.useState('');
  const [busyKey, setBusyKey] = React.useState('');
  const activeMigrations = (migrations || []).filter((item: any) => ['PENDING', 'IN_PROGRESS'].includes(item.status));
  if (activeMigrations.length === 0) return null;

  async function submitLine(migration: any, line: any) {
    const key = `${migration.id}-${line.id}`;
    const identifiers = String(drafts[key] || '').split(/[\s,;]+/).map((value) => value.trim()).filter(Boolean);
    if (identifiers.length === 0) {
      setError('Hãy quét hoặc dán ít nhất một mã.');
      return;
    }
    setError('');
    setBusyKey(key);
    try {
      await onScan(migration.id, line.id, identifiers);
      setDrafts((current) => ({ ...current, [key]: '' }));
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : 'Không thể lưu danh sách mã.');
    } finally {
      setBusyKey('');
    }
  }

  async function completeMigration(migrationId: string) {
    setError('');
    setBusyKey(`complete-${migrationId}`);
    try {
      await onComplete(migrationId);
    } catch (completeError) {
      setError(completeError instanceof Error ? completeError.message : 'Không thể hoàn tất tác vụ.');
    } finally {
      setBusyKey('');
    }
  }

  async function cancelMigration(migrationId: string) {
    setError('');
    try {
      await onCancel(migrationId);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : 'Không thể hủy tác vụ.');
    }
  }

  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 md:col-span-5">
      <div className="mb-2 text-sm font-bold text-amber-900">Tác vụ bổ sung IMEI/Serial cho tồn kho cũ</div>
      <p className="mb-3 text-xs font-medium text-amber-800">Chính sách mới chỉ được kích hoạt sau khi tất cả dòng tồn kho đã có đủ mã hợp lệ.</p>
      {error && <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div>}
      <div className="space-y-3">
        {activeMigrations.map((migration: any) => {
          const complete = Number(migration.stagedIdentifierCount || 0) === Number(migration.requiredIdentifierCount || 0);
          return (
            <div key={migration.id} className="rounded-md border border-amber-200 bg-white p-3">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-bold text-slate-800">{migration.identifierType}</div>
                  <div className="text-xs font-semibold text-slate-500">Đã quét {migration.stagedIdentifierCount}/{migration.requiredIdentifierCount} mã</div>
                </div>
                <div className="flex gap-2">
                  <button type="button" disabled={!complete || busyKey === `complete-${migration.id}`} onClick={() => completeMigration(migration.id)} className="rounded-md bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:opacity-40">{busyKey === `complete-${migration.id}` ? 'Đang hoàn tất...' : 'Hoàn tất và kích hoạt'}</button>
                  <button type="button" onClick={() => cancelMigration(migration.id)} className="rounded-md border border-red-200 px-3 py-2 text-xs font-bold text-red-600">Hủy tác vụ</button>
                </div>
              </div>
              <div className="space-y-2">
                {(migration.lines || []).map((line: any) => {
                  const remaining = Number(line.requiredIdentifierCount || 0) - Number(line.stagedIdentifierCount || 0);
                  const key = `${migration.id}-${line.id}`;
                  return (
                    <div key={line.id} className="grid gap-2 rounded-md bg-slate-50 p-2 lg:grid-cols-[minmax(220px,1fr)_120px_minmax(280px,1.5fr)_90px] lg:items-end">
                      <div>
                        <div className="text-sm font-bold text-slate-700">{line.productName}</div>
                        <div className="text-xs font-medium text-slate-500">{line.variantName || 'Sản phẩm không có biến thể'}</div>
                      </div>
                      <div className="text-xs font-bold text-slate-600">Còn thiếu: {remaining}</div>
                      <label className="block">
                        <span className="mb-1 block text-xs font-bold text-slate-500">Quét hoặc dán danh sách mã</span>
                        <textarea disabled={remaining <= 0} value={drafts[key] || ''} onChange={(event) => setDrafts((current) => ({ ...current, [key]: event.target.value }))} className="min-h-16 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 disabled:bg-slate-100" placeholder="Mỗi mã một dòng hoặc cách nhau bằng dấu phẩy" />
                      </label>
                      <button type="button" disabled={remaining <= 0 || busyKey === key} onClick={() => submitLine(migration, line)} className="h-10 rounded-md bg-indigo-600 px-3 text-xs font-bold text-white disabled:opacity-40">{busyKey === key ? 'Đang lưu...' : 'Lưu mã'}</button>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AdminCategoriesTab(props: AdminCategoriesTabProps) {
  const {
    addCategoryFilter,
    addSpecField,
    categoryAuditLogs,
    categoryForm,
    categoryMetrics = {},
    categoryMigrationJobs,
    identifierPolicyMigrations,
    categoryPanelBusy,
    categoryParentMigrationHint,
    categoryCloseSignal,
    categoryStatusFilter,
    categoryViewOnly,
    categorySlugStatus,
    categorySlugTaken,
    categoryStatusOptions,
    checkCategorySlug,
    compactId,
    confirmDelete,
    derivedCategoryFilters,
    editCategory,
    editingCategory,
    editingCategoryId,
    filteredCategoryTree,
    filteredRootCategories,
    handleCategorySubmit,
    hideCategory,
    patchCategoryFilter,
    patchSpecField,
    scanIdentifierPolicyMigration,
    completeIdentifierPolicyMigration,
    cancelIdentifierPolicyMigration,
    query,
    reactivateCategory,
    refreshCategoryWorkspace,
    reorderCategory,
    resetCategoryForm,
    rootCategories,
    setCategoryForm,
    setCategorySlugStatus,
    setCategoryStatusFilter,
    setQuery,
    slugifyText,
    uploadFiles,
    viewCategory,
    usePermission,
  } = props;
  const canCreateCategory = usePermission('category:create');
  const canUpdateCategory = usePermission('category:update');
  const canDeleteCategory = usePermission('category:delete');
  return (
    <AdminPanel 
      title="Quản lý danh mục và form thông số" 
      filters={
        <>
          <Select noLabel={true} label="Trạng thái" value={categoryStatusFilter} onChange={setCategoryStatusFilter} options={[['all', 'Tất cả'], ['active', 'Đang hiển thị'], ['inactive', 'Đã ẩn']]} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm danh mục, slug, danh mục cha" />
        </>
      }
    >
      {(canCreateCategory || canUpdateCategory || categoryViewOnly) && <CollapsibleSection title={categoryViewOnly ? 'Đang xem thông tin danh mục' : editingCategoryId ? 'Đang chỉnh sửa danh mục' : 'Thêm danh mục và form thông số'} description="Mở khi cần tạo danh mục cha, danh mục con hoặc cấu hình form thông số kỹ thuật cho danh mục cha." defaultOpen={false} forceOpen={Boolean(editingCategoryId)} forceOpenKey={editingCategoryId} closeSignal={categoryCloseSignal} onClose={resetCategoryForm}>
        <form onSubmit={categoryViewOnly ? (event) => event.preventDefault() : handleCategorySubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-5">
          <fieldset disabled={Boolean(categoryViewOnly)} className="contents">
          <Input label="Tên danh mục" value={categoryForm.name} required onChange={(value) => setCategoryForm({ ...categoryForm, name: value, slug: categoryForm.slug || slugifyText(value) })} />
          <Input label="Slug" value={categoryForm.slug} onBlur={checkCategorySlug} onChange={(value) => {
            setCategorySlugStatus('idle');
            setCategoryForm({ ...categoryForm, slug: slugifyText(value) });
          }} />
          <Input label="Icon" value={categoryForm.icon} onChange={(value) => setCategoryForm({ ...categoryForm, icon: value })} />
          <Select label="Danh mục cha" value={categoryForm.parentId} onChange={(value) => setCategoryForm({ ...categoryForm, parentId: value })} options={[['', 'Là danh mục cha'], ...rootCategories.map((item) => [item.id, item.name] as [string, string])]} />
          <Input label="Thứ tự" type="number" value={categoryForm.order} onChange={(value) => setCategoryForm({ ...categoryForm, order: Number(value) })} />
          <Select label="Trạng thái" value={categoryForm.status} onChange={(value) => setCategoryForm({ ...categoryForm, status: value, isActive: ['ACTIVE', 'APPROVED'].includes(value) })} options={categoryStatusOptions} />
          {categoryParentMigrationHint && <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800 md:col-span-5">Danh mục này đang có sản phẩm. Nếu đổi danh mục cha, hệ thống sẽ tạo tác vụ nền để chuẩn hóa lại thông số sản phẩm theo cây mới.</div>}
          {(categorySlugTaken || categorySlugStatus !== 'idle') && (
            <div className={`rounded-md border px-3 py-2 text-sm font-semibold md:col-span-5 ${categorySlugStatus === 'available' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
              {categorySlugStatus === 'checking' ? 'Đang kiểm tra slug...' : categorySlugStatus === 'available' ? 'Slug có thể sử dụng.' : 'Slug này đã tồn tại. Hãy đổi slug trước khi lưu.'}
            </div>
          )}
          {!categoryViewOnly && (
            <>
              <FileInput label="Icon/hình danh mục" accept="image/*" onFiles={async (files) => setCategoryForm({ ...categoryForm, iconUrl: (await uploadFiles(files, 'categories'))[0] || categoryForm.iconUrl })} />
              <FileInput label="Banner danh mục" accept="image/*" onFiles={async (files) => setCategoryForm({ ...categoryForm, bannerUrl: (await uploadFiles(files, 'categories'))[0] || categoryForm.bannerUrl })} />
            </>
          )}
          {(categoryForm.iconUrl || categoryForm.bannerUrl) && (
            <div className="grid gap-3 md:col-span-3 md:grid-cols-2">
              {categoryForm.iconUrl && <img src={categoryForm.iconUrl} alt="" className="h-24 w-full rounded-md border border-slate-200 object-cover" />}
              {categoryForm.bannerUrl && <img src={categoryForm.bannerUrl} alt="" className="h-24 w-full rounded-md border border-slate-200 object-cover" />}
            </div>
          )}
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
            <div className="mb-3 text-sm font-bold text-slate-700">Tồn kho và bảo hành mặc định</div>
            <div className="grid gap-3 md:grid-cols-5">
              <Checkbox label="Theo IMEI của cha" checked={Boolean(categoryForm.inventoryPolicy.inheritImeiPolicy)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, inheritImeiPolicy: checked } })} />
              <Checkbox label="Quản lý IMEI" checked={Boolean(categoryForm.inventoryPolicy.trackImei)} disabled={Boolean(categoryForm.inventoryPolicy.inheritImeiPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, trackImei: checked } })} />
              <Checkbox label="Theo serial của cha" checked={Boolean(categoryForm.inventoryPolicy.inheritSerialPolicy)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, inheritSerialPolicy: checked } })} />
              <Checkbox label="Quản lý serial number" checked={Boolean(categoryForm.inventoryPolicy.trackSerialNumber)} disabled={Boolean(categoryForm.inventoryPolicy.inheritSerialPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, trackSerialNumber: checked } })} />
              <Checkbox label="Theo kích thước của cha" checked={Boolean(categoryForm.inventoryPolicy.inheritStorageDimensions)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, inheritStorageDimensions: checked } })} />
              <Input label="Dài đóng gói (cm)" type="number" value={Number(categoryForm.inventoryPolicy.packageLengthCm || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, packageLengthCm: Math.max(0, Number(value)) } })} />
              <Input label="Rộng đóng gói (cm)" type="number" value={Number(categoryForm.inventoryPolicy.packageWidthCm || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, packageWidthCm: Math.max(0, Number(value)) } })} />
              <Input label="Cao đóng gói (cm)" type="number" value={Number(categoryForm.inventoryPolicy.packageHeightCm || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, packageHeightCm: Math.max(0, Number(value)) } })} />
              <Input label="Hệ số xếp hàng" type="number" value={Number(categoryForm.inventoryPolicy.packingRatio || 0.7)} onChange={(value) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, packingRatio: Math.min(1, Math.max(0.01, Number(value))) } })} />
              <Checkbox label="Theo bảo hành của cha" checked={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, inheritWarrantyPolicy: checked } })} />
              <Checkbox label="Có bảo hành" checked={Boolean(categoryForm.warrantyPolicy.hasWarranty)} disabled={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, hasWarranty: checked } })} />
              <Input label="Tháng bảo hành" type="number" value={Number(categoryForm.warrantyPolicy.warrantyMonths || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, warrantyMonths: Math.max(0, Number(value)) } })} />
              <Checkbox label="Có 1 đổi 1" checked={Boolean(categoryForm.warrantyPolicy.allowOneForOne)} disabled={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, allowOneForOne: checked } })} />
              <Input label="Ngày 1 đổi 1" type="number" value={Number(categoryForm.warrantyPolicy.oneForOneDays || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, oneForOneDays: Math.max(0, Number(value)) } })} />
            </div>
          </div>
          <IdentifierPolicyMigrationPanel
            migrations={identifierPolicyMigrations}
            onScan={scanIdentifierPolicyMigration}
            onComplete={completeIdentifierPolicyMigration}
            onCancel={cancelIdentifierPolicyMigration}
          />
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <span className="text-sm font-bold text-slate-700">Form thông số kỹ thuật</span>
                <p className="mt-1 text-xs font-medium text-slate-500">{categoryForm.parentId ? 'Danh mục con kế thừa thông số chung từ danh mục cha và có thể thêm thông số đặc thù riêng.' : 'Danh mục cha lưu thông số chung. Danh mục con có thể cộng thêm thông số riêng nếu cần.'}</p>
              </div>
              {!categoryViewOnly && <button type="button" onClick={addSpecField} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 px-3 text-sm font-semibold text-slate-700 transition"><Plus className="h-4 w-4" /> Thêm trường</button>}
            </div>
            <div className="space-y-2">
              {categoryForm.specFields.map((field, index) => (
                <div key={index} className="grid gap-2 rounded-md bg-slate-50 p-2 md:grid-cols-2 xl:grid-cols-4">
                  <Input label="Mã trường" value={field.key} onChange={(value) => patchSpecField(index, { key: value })} />
                  <Input label="Tên hiển thị" value={field.label} onChange={(value) => patchSpecField(index, { label: value })} />
                  <Input label="Nhóm cha" value={field.group || ''} onChange={(value) => patchSpecField(index, { group: value })} />
                  <Select label="Kiểu" value={field.type} onChange={(value) => patchSpecField(index, { type: value })} options={[['text', 'Chữ'], ['number', 'Số'], ['select', 'Lựa chọn'], ['color', 'Màu']]} />
                  <Checkbox label="Bắt buộc" checked={field.required} onChange={(checked) => patchSpecField(index, { required: checked })} />
                  <Checkbox label="Dùng cho biến thể" checked={field.variant} onChange={(checked) => patchSpecField(index, { variant: checked })} />
                  <Checkbox label="Dùng làm lọc" checked={Boolean(field.isFilterable)} onChange={(checked) => patchSpecField(index, { isFilterable: checked })} />
                  <Select label="Kiểu lọc" value={field.filterType || (field.type === 'number' ? 'range' : 'checkbox')} onChange={(value) => patchSpecField(index, { filterType: value })} options={[['checkbox', 'Checkbox'], ['range', 'Khoảng'], ['select', 'Danh sách']]} />
                  {!categoryViewOnly && <button type="button" aria-label={`Xóa trường ${field.label || field.key || index + 1}`} onClick={() => setCategoryForm({ ...categoryForm, specFields: categoryForm.specFields.filter((_, i) => i !== index) })} className="justify-self-end text-red-600 md:col-span-2 xl:col-span-4"><Trash2 className="h-4 w-4" /></button>}
                </div>
              ))}
              {categoryForm.specFields.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-500">Chưa có trường thông số. Hãy thêm các trường như màn hình, chip, pin, camera, chất liệu...</div>}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <span className="text-sm font-bold text-slate-700">Bộ lọc hiển thị ngoài trang khách hàng</span>
                <p className="mt-1 text-xs font-medium text-slate-500">Chọn các thuộc tính sẽ xuất hiện ở sidebar/bộ lọc của trang danh mục.</p>
              </div>
              {!categoryViewOnly && <button type="button" onClick={addCategoryFilter} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 px-3 text-sm font-semibold text-slate-700 transition"><Plus className="h-4 w-4" /> Thêm bộ lọc</button>}
            </div>
            <div className="space-y-2">
              {derivedCategoryFilters.map((field, index) => {
                const manualIndex = categoryForm.filterConfig.findIndex((item) => item.key === field.key && item.source !== 'attribute');
                const isAttributeFilter = field.source === 'attribute';
                return (
                  <div key={`${field.source || 'manual'}-${field.key}-${index}`} className="grid gap-2 rounded-md bg-slate-50 p-2 md:grid-cols-[1fr_1fr_150px_110px_110px_40px]">
                    <Input label="Mã lọc" value={field.key} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { key: value })} />
                    <Input label="Tên hiển thị" value={field.label} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { label: value })} />
                    <Select label="Kiểu lọc" value={field.type} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { type: value })} options={[['checkbox', 'Checkbox'], ['range', 'Khoảng giá/số'], ['select', 'Danh sách']]} />
                    <Checkbox label="Hiển thị" checked={field.enabled} disabled={isAttributeFilter} onChange={(checked) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { enabled: checked })} />
                    <span className="mt-5 rounded-md bg-slate-200 px-2 py-1 text-center text-xs font-bold text-slate-700">{isAttributeFilter ? 'Từ thông số' : 'Thủ công'}</span>
                    {!categoryViewOnly && <button type="button" disabled={isAttributeFilter} onClick={() => manualIndex >= 0 && setCategoryForm({ ...categoryForm, filterConfig: categoryForm.filterConfig.filter((_, i) => i !== manualIndex) })} className="mt-5 text-red-600 disabled:text-slate-300"><Trash2 className="h-4 w-4" /></button>}
                  </div>
                );
              })}
              {derivedCategoryFilters.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-500">Chưa có bộ lọc. Đánh dấu "Dùng làm lọc" ở thông số kỹ thuật hoặc thêm bộ lọc thủ công.</div>}
            </div>
          </div>
          </fieldset>
          {categoryViewOnly ? (
            <div className="flex items-end gap-2">
              <button type="button" onClick={resetCategoryForm} className="inline-flex h-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
                Đóng
              </button>
            </div>
          ) : (
            <SubmitButtons editing={Boolean(editingCategoryId)} onCancel={resetCategoryForm} />
          )}
        </form>
      </CollapsibleSection>}
      <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Quản lý form thông số theo danh mục cha</h3>
            <p className="text-xs font-medium text-slate-500">Chỉ danh mục cha có form thông số; danh mục con kế thừa khi tạo sản phẩm.</p>
          </div>
          <AdminBadge tone="blue">{filteredRootCategories.length}/{rootCategories.length} danh mục cha</AdminBadge>
        </div>
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {filteredRootCategories.map((category) => (
            <button key={category.id} type="button" onClick={() => editCategory(category)} className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-red-200 hover:bg-red-50">
              <div className="min-w-0">
                <div className="truncate text-sm font-bold text-slate-900">{category.name}</div>
                <div className="mt-1 text-xs font-medium text-slate-500">{category.slug || category.id}</div>
              </div>
              <span className="ml-3 rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">{category.specFields?.length || 0} trường</span>
            </button>
          ))}
        </div>
      </div>
      <div className="mb-5 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Tình trạng vận hành danh mục</h3>
              <p className="text-xs font-medium text-slate-500">Theo dõi cache, job di trú và các cảnh báo tự phục hồi của cây danh mục.</p>
            </div>
            <button type="button" onClick={() => refreshCategoryWorkspace()} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700">
              <RefreshCw className={`h-4 w-4 ${categoryPanelBusy ? 'animate-spin' : ''}`} />
              Làm mới
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Tỉ lệ cache hit" value={`${Math.round(Number(categoryMetrics.cacheHitRatio ?? 0) * 100)}%`} tone="emerald" />
            <MetricCard label="P99 đọc danh mục" value={`${Number(categoryMetrics.latencyP99Ms ?? 0)} ms`} tone="sky" />
            <MetricCard label="Job đang chạy" value={String(categoryMetrics.migrationRunningJobs ?? 0)} tone="amber" />
            <MetricCard label="Job stale đã cứu" value={String(categoryMetrics.migrationWatchdogRecoveredJobs ?? 0)} tone="slate" />
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3">
            <h3 className="text-sm font-bold text-slate-900">Nhật ký danh mục đang chọn</h3>
            <p className="text-xs font-medium text-slate-500">{editingCategory ? `Đang xem: ${editingCategory.name}` : 'Chọn một danh mục để xem lịch sử thay đổi và job nền.'}</p>
          </div>
          {editingCategory ? (
            <div className="space-y-4">
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Migration jobs</div>
                <div className="space-y-2">
                  {categoryMigrationJobs.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">Chưa có job di trú nào cho danh mục này.</div>}
                  {categoryMigrationJobs.slice(0, 4).map((job) => (
                    <div key={job.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-mono text-xs text-slate-500">{compactId(job.id)}</span>
                        <AdminBadge tone={job.status === 'COMPLETED' ? 'green' : job.status === 'FAILED' ? 'red' : 'amber'}>{job.status}</AdminBadge>
                      </div>
                      <div className="mt-1 text-xs text-slate-600">Đã xử lý {job.processedProducts || 0}/{job.totalProducts || 0} sản phẩm</div>
                      {job.errorMessage && <div className="mt-1 text-xs font-medium text-red-600">{job.errorMessage}</div>}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Audit gần nhất</div>
                <div className="space-y-2">
                  {categoryAuditLogs.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">Chưa có lịch sử thay đổi gần đây.</div>}
                  {categoryAuditLogs.slice(0, 5).map((log) => (
                    <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-semibold text-slate-800">{String(log.actionType || '').replaceAll('_', ' ')}</div>
                        <div className="text-xs text-slate-500">{new Date(log.createdAt).toLocaleString('vi-VN')}</div>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">Actor: {compactId(log.actorId)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-sm text-slate-500">Danh sách lịch sử và job nền sẽ hiện ở đây khi bạn mở một danh mục để chỉnh sửa.</div>
          )}
        </div>
      </div>
      <AdminTable headers={['Sắp xếp', 'Ảnh', 'Tên', 'Slug', 'Loại', 'Danh mục cha', 'Thông số / lọc', 'Trạng thái', 'Thao tác']}>
        {filteredCategoryTree.flatMap((category) => [category, ...(category.children || [])]).map((category) => (
          <CategoryTableRow
            key={category.id}
            category={category}
            level={category.parentId ? 1 : 0}
            onView={() => viewCategory(category)}
            onEdit={canUpdateCategory ? () => editCategory(category) : undefined}
            onHide={canUpdateCategory ? () => hideCategory(category) : undefined}
            onDelete={canDeleteCategory ? () => confirmDelete(category.name, () => categoryApi.adminDeleteCategory(category.id)) : undefined}
            onRestore={canUpdateCategory && !category.isActive ? () => reactivateCategory(category) : undefined}
            onReorder={canUpdateCategory ? reorderCategory : undefined}
          />
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
