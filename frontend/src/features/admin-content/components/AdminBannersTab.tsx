import type React from 'react';
import { useState } from 'react';
import { Image, Pencil, Plus, Trash2, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, FileInput, Input, MediaPreview, SearchBox, Select, SubmitButtons } from '../../admin-shell/components/AdminDashboardParts';

type AdminBannersTabProps = Record<string, any>;

export default function AdminBannersTab(props: AdminBannersTabProps) {
  const {
    bannerForm,
    bannerNotice,
    categories,
    deleteBanner,
    editBanner,
    editingBannerId,
    filteredBanners,
    handleBannerSubmit,
    products,
    query,
    resetBannerForm,
    setBannerForm,
    setQuery,
    uploadFiles,
  } = props;
  const [showForm, setShowForm] = useState(false);

  const categoryOptions = [
    ['', 'Chọn danh mục'],
    ...categories.map((item: any) => [String(item.id), item.parentName ? `${item.parentName} / ${item.name}` : item.name] as [string, string]),
  ];
  const productOptions = [
    ['', 'Không gắn sản phẩm'],
    ...products.map((item: any) => [String(item.id), `${item.name}${item.sku ? ` - ${item.sku}` : ''}`] as [string, string]),
  ];

  const openCreateForm = () => {
    resetBannerForm();
    setShowForm(true);
  };

  const openEditForm = (item: any) => {
    editBanner(item);
    setShowForm(true);
  };

  const closeForm = () => {
    resetBannerForm();
    setShowForm(false);
  };

  const submitForm = async (event: React.FormEvent) => {
    const saved = await handleBannerSubmit(event);
    if (saved) setShowForm(false);
  };

  return (
    <AdminPanel
      title="Quản lý banner trang chủ"
      action={
        <button type="button" onClick={openCreateForm} className="inline-flex h-10 items-center gap-2 rounded-lg bg-red-600 px-3 text-sm font-bold text-white transition hover:bg-red-700">
          <Plus className="h-4 w-4" />
          Tạo banner
        </button>
      }
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm banner theo tiêu đề hoặc mô tả" />}
    >
      {bannerNotice && (
        <div className={`mb-3 rounded-md border px-3 py-2 text-sm font-semibold ${bannerNotice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
          {bannerNotice.text}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6 backdrop-blur-sm">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h2 className="text-lg font-black text-slate-900">{editingBannerId ? 'Sửa banner' : 'Tạo banner'}</h2>
                <p className="mt-1 text-sm font-medium text-slate-500">Banner cần có danh mục. Sản phẩm là tùy chọn để ưu tiên dẫn đến trang chi tiết.</p>
              </div>
              <button type="button" onClick={closeForm} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50" title="Đóng">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={submitForm} className="grid gap-3 p-5 md:grid-cols-2">
              <Input label="Tiêu đề" value={bannerForm.title} required onChange={(value) => setBannerForm({ ...bannerForm, title: value })} />
              <Input label="Mô tả cực ngắn" value={bannerForm.description} onChange={(value) => setBannerForm({ ...bannerForm, description: value })} />
              <Select label="Danh mục đi kèm" value={bannerForm.categoryId} onChange={(value) => setBannerForm({ ...bannerForm, categoryId: value })} options={categoryOptions} />
              <Select label="Sản phẩm đi kèm" value={bannerForm.productId} onChange={(value) => setBannerForm({ ...bannerForm, productId: value })} options={productOptions} />
              <Input label="Thứ tự hiển thị" type="number" value={bannerForm.sortOrder} onChange={(value) => setBannerForm({ ...bannerForm, sortOrder: Number(value || 0) })} />
              <Select label="Trạng thái" value={bannerForm.isActive ? 'ACTIVE' : 'INACTIVE'} onChange={(value) => setBannerForm({ ...bannerForm, isActive: value === 'ACTIVE', status: value === 'ACTIVE' ? 'PUBLISHED' : 'ARCHIVED' })} options={[['ACTIVE', 'Đang hiển thị'], ['INACTIVE', 'Tạm ẩn']]} />
              <FileInput label="Upload banner" accept="image/*" onFiles={async (files) => setBannerForm({ ...bannerForm, bannerImageUrl: (await uploadFiles(files, 'content'))[0] || bannerForm.bannerImageUrl })} />
              <Input label="Hoặc nhập URL ảnh" value={bannerForm.bannerImageUrl} onChange={(value) => setBannerForm({ ...bannerForm, bannerImageUrl: value })} />
              {bannerForm.bannerImageUrl && (
                <div className="md:col-span-2">
                  <MediaPreview title="Banner đang chọn" items={[bannerForm.bannerImageUrl]} onRemove={() => setBannerForm({ ...bannerForm, bannerImageUrl: '' })} />
                </div>
              )}
              <div className="md:col-span-2">
                <SubmitButtons editing={Boolean(editingBannerId)} onCancel={closeForm} />
              </div>
            </form>
          </div>
        </div>
      )}

      <AdminTable headers={['Banner', 'Liên kết', 'Thứ tự', 'Trạng thái', 'Thao tác']}>
        {filteredBanners.map((item: any) => {
          const product = Array.isArray(item.products) ? item.products[0] : null;
          const category = Array.isArray(item.categories) ? item.categories[0] : null;
          return (
            <tr key={item.id}>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  {item.bannerImageUrl || item.thumbnailUrl ? <img src={item.bannerImageUrl || item.thumbnailUrl} alt="" className="h-14 w-24 rounded-md object-cover" /> : <div className="flex h-14 w-24 items-center justify-center rounded-md bg-slate-100 text-slate-400"><Image className="h-5 w-5" /></div>}
                  <div>
                    <div className="font-semibold text-slate-900">{item.title}</div>
                    <div className="text-xs text-slate-500">{item.description || '-'}</div>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                <div>{category ? `Danh mục: ${category.name}` : 'Chưa chọn danh mục'}</div>
                <div>{product ? `Sản phẩm: ${product.name}` : 'Không gắn sản phẩm'}</div>
              </td>
              <td className="px-4 py-3 font-semibold text-slate-700">{item.sortOrder || 0}</td>
              <td className="px-4 py-3">
                <AdminBadge tone={item.isActive ? 'green' : 'slate'}>{item.isActive ? 'Đang hiển thị' : 'Tạm ẩn'}</AdminBadge>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => openEditForm(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50" title="Sửa banner">
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button type="button" onClick={() => deleteBanner(item)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-red-100 text-red-600 hover:bg-red-50" title="Xóa banner">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          );
        })}
      </AdminTable>
    </AdminPanel>
  );
}
