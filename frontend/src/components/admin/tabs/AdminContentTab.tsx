import React from 'react';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, CollapsibleSection, FileInput, Input, MediaPreview, SearchBox, Select, VideoPreview } from '../AdminDashboardParts';
import { Edit2, Eye, MessageSquare, Plus, Trash2, X } from 'lucide-react';
import { contentStatusOptions, videoCategoryOptions, videoSourceOptions } from '../../../pages/AdminDashboardConfig';

type AdminContentTabProps = Record<string, any>;

export default function AdminContentTab(props: AdminContentTabProps) {
  const {
    activeVideoCommentsItem,
    apiDb,
    brands,
    canDeleteContent,
    canCreateContent,
    canUpdateContent,
    categories,
    confirmDelete,
    contentCloseSignal,
    contentForm,
    contentNotice,
    contentSaving,
    contentStatusFilter,
    contentTypeFilter,
    editContent,
    editingContentId,
    filteredContentItems,
    handleContentSubmit,
    query,
    replyVideoComment,
    resetContentForm,
    selectedVideoProductIds,
    setActiveVideoCommentsItem,
    setContentForm,
    setContentStatusFilter,
    setContentTypeFilter,
    setQuery,
    setVideoProductBrandFilter,
    setVideoProductCategoryFilter,
    setVideoProductSearch,
    setVideoProductSelected,
    setVideoReplyDrafts,
    toggleVideoCommentHidden,
    uploadFiles,
    videoProductBrandFilter,
    videoProductCategoryFilter,
    videoProductChoices,
    videoProductSearch,
    videoReplyDrafts,
  } = props;

  return (
    <AdminPanel
      title="Quản lý video"
      filters={
        <>
          <Select noLabel={true} label="Nhóm" value={contentTypeFilter} onChange={setContentTypeFilter} options={[['all', 'Tất cả nhóm'], ...videoCategoryOptions]} />
          <Select noLabel={true} label="Trạng thái" value={contentStatusFilter} onChange={setContentStatusFilter} options={[['all', 'Tất cả trạng thái'], ...contentStatusOptions]} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm tiêu đề, loại, mô tả" />
        </>
      }
    >
      {contentNotice && (
        <div className={`mb-3 rounded-md border px-3 py-2 text-sm font-semibold ${contentNotice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
          {contentNotice.text}
        </div>
      )}
      {(canCreateContent || canUpdateContent) && <CollapsibleSection
        title={editingContentId ? 'Đang chỉnh sửa nội dung' : 'Thêm video, banner hoặc trang marketing'}
        description="Quản trị nội dung tập trung cho video, banner và bài marketing. Có thể gắn sản phẩm, danh mục, hẹn lịch đăng và nhập sẵn bình luận mẫu để kiểm duyệt."
        defaultOpen={false}
        forceOpen={Boolean(editingContentId)}
        forceOpenKey={editingContentId}
        closeSignal={contentCloseSignal}
        onClose={resetContentForm}
      >
        <form onSubmit={handleContentSubmit} className="grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
          {contentNotice && (
            <div className={`md:col-span-4 rounded-md border px-3 py-2 text-sm font-semibold ${contentNotice.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
              {contentNotice.text}
            </div>
          )}
          <Input label="Tiêu đề" value={contentForm.title} required onChange={(value) => setContentForm({ ...contentForm, title: value })} />
          <Select label="Nguồn video" value={contentForm.videoSource} onChange={(value) => setContentForm({ ...contentForm, videoSource: value, videoUrl: '' })} options={videoSourceOptions} />
          <Select label="Nhóm nội dung" value={contentForm.videoCategory} onChange={(value) => setContentForm({ ...contentForm, videoCategory: value })} options={videoCategoryOptions} />
          <Input label="Thứ tự hiển thị" type="number" value={contentForm.sortOrder} onChange={(value) => setContentForm({ ...contentForm, sortOrder: Number(value || 0) })} />
          <Checkbox label="Đang hiển thị" checked={contentForm.isActive} onChange={(checked) => setContentForm({ ...contentForm, isActive: checked })} />
          <div className="md:col-span-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold text-slate-500">Mô tả ngắn</span>
              <textarea className="min-h-20 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" value={contentForm.description} onChange={(event) => setContentForm({ ...contentForm, description: event.target.value })} />
            </label>
          </div>
          {contentForm.videoSource === 'UPLOAD' ? (
            <FileInput label="Upload video" accept="video/*" onFiles={async (files) => setContentForm({ ...contentForm, videoUrl: (await uploadFiles(files, 'content'))[0] || contentForm.videoUrl })} />
          ) : (
            <Input label="Link YouTube" value={contentForm.videoUrl} required onChange={(value) => setContentForm({ ...contentForm, videoUrl: value })} />
          )}
          <FileInput label="Upload thumbnail" accept="image/*" onFiles={async (files) => setContentForm({ ...contentForm, thumbnailUrl: (await uploadFiles(files, 'content'))[0] || contentForm.thumbnailUrl })} />
          {contentForm.videoUrl && <div className="md:col-span-2"><VideoPreview title="Video đang chọn" url={contentForm.videoUrl} onRemove={() => setContentForm({ ...contentForm, videoUrl: '' })} /></div>}
          {contentForm.thumbnailUrl && <div className="md:col-span-2"><MediaPreview title="Thumbnail đang chọn" items={[contentForm.thumbnailUrl]} onRemove={() => setContentForm({ ...contentForm, thumbnailUrl: '' })} /></div>}
          <div className="md:col-span-4 rounded-lg border border-slate-200 bg-white p-3">
            <div className="mb-3 text-xs font-bold text-slate-500">Sản phẩm liên kết</div>
            <div className="grid gap-2 md:grid-cols-3">
              <Input label="Tìm sản phẩm" value={videoProductSearch} onChange={setVideoProductSearch} />
              <Select label="Lọc danh mục" value={videoProductCategoryFilter} onChange={setVideoProductCategoryFilter} options={[['all', 'Tất cả danh mục'], ...categories.map((category: any) => [String(category.id || category.code || category.slug), category.name] as [string, string])]} />
              <Select label="Lọc thương hiệu" value={videoProductBrandFilter} onChange={setVideoProductBrandFilter} options={[['all', 'Tất cả thương hiệu'], ...brands.map((brand: any) => [String(brand.id || brand.name), brand.name] as [string, string])]} />
            </div>
            <div className="mt-3 grid max-h-72 gap-2 overflow-y-auto md:grid-cols-2">
              {videoProductChoices.map((product: any) => (
                <label key={product.id} className="flex cursor-pointer items-center gap-3 rounded-md border border-slate-200 p-2 text-sm transition hover:bg-slate-50">
                  <input type="checkbox" checked={selectedVideoProductIds.includes(product.id)} onChange={(event) => setVideoProductSelected(product.id, event.target.checked)} className="h-4 w-4 accent-red-600" />
                  {product.imageUrl && <img src={product.imageUrl} alt="" className="h-10 w-10 rounded bg-slate-50 object-contain" />}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-slate-900">{product.name}</span>
                    <span className="block truncate text-xs text-slate-500">{product.brand || product.categoryName || product.category || 'Sản phẩm'}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
          <Input label="Lịch đăng" type="datetime-local" value={contentForm.scheduledAt} onChange={(value) => setContentForm({ ...contentForm, scheduledAt: value })} />
          <Input label="Ngày public" type="datetime-local" value={contentForm.publishedAt} onChange={(value) => setContentForm({ ...contentForm, publishedAt: value })} />
          <div className="md:col-span-4 rounded-md border border-dashed border-slate-200 bg-white p-3 text-xs text-slate-500">Lượt xem, lượt thích và bình luận được lấy từ tương tác thực tế của người dùng.</div>
          <div className="flex items-end gap-2">
            <button disabled={contentSaving} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60">
              <Plus className="h-4 w-4" /> {contentSaving ? 'Đang lưu...' : editingContentId ? 'Lưu' : 'Thêm'}
            </button>
            {editingContentId && <button type="button" disabled={contentSaving} onClick={resetContentForm} title="Hủy chỉnh sửa" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"><X className="h-4 w-4" /></button>}
          </div>
        </form>
      </CollapsibleSection>}
      <AdminTable headers={['Tiêu đề', 'Media', 'Loại', 'Liên kết', 'Lịch & thứ tự', 'Tương tác', 'Trạng thái', 'Thao tác']}>
        {filteredContentItems.length === 0 ? (
          <tr><td colSpan={8} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy nội dung phù hợp.</td></tr>
        ) : filteredContentItems.map((item: any) => (
          <tr key={item.id}>
            <td className="px-4 py-3">
              <div className="font-semibold text-slate-900">{item.title}</div>
              <div className="mt-1 text-xs text-slate-500">{item.description || '-'}</div>
            </td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-2">
                {(item.thumbnailUrl || item.bannerImageUrl) ? (
                  <img src={item.thumbnailUrl || item.bannerImageUrl} alt="" className="h-14 w-20 rounded-md border border-slate-200 object-cover" />
                ) : (
                  <div className="flex h-14 w-20 items-center justify-center rounded-md border border-dashed border-slate-200 text-[10px] font-bold text-slate-400">NO MEDIA</div>
                )}
                {item.videoUrl && (
                  <a href={item.videoUrl} target="_blank" rel="noreferrer" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700" title="Mở video">
                    <Eye className="h-4 w-4" />
                  </a>
                )}
              </div>
            </td>
            <td className="px-4 py-3">
              <div>{videoCategoryOptions.find(([value]) => value === item.videoCategory)?.[1] || item.videoCategory || 'Video'}</div>
              <div className="mt-1 text-xs text-slate-500">{item.videoSource === 'YOUTUBE' ? 'YouTube' : 'Upload'}</div>
            </td>
            <td className="px-4 py-3 text-xs text-slate-600">
              <div>{Array.isArray(item.products) && item.products.length ? `${item.products.length} sản phẩm` : 'Chưa gắn sản phẩm'}</div>
              <div>{Array.isArray(item.categories) && item.categories.length ? `${item.categories.length} danh mục` : 'Chưa gắn danh mục'}</div>
            </td>
            <td className="px-4 py-3 text-xs text-slate-600">
              <div>Thứ tự: {item.sortOrder || 0}</div>
              <div>{item.scheduledAt ? `Lên lịch: ${new Date(item.scheduledAt).toLocaleString('vi-VN')}` : 'Đăng ngay / không lịch'}</div>
            </td>
            <td className="px-4 py-3 text-xs text-slate-600">
              <div>{item.likeCount || 0} thích</div>
              <div>{item.viewCount || 0} xem • {item.commentCount || 0} bình luận</div>
            </td>
            <td className="px-4 py-3">
              <div className="flex flex-col gap-2">
                <AdminBadge tone={item.isActive ? 'green' : 'slate'}>{item.isActive ? 'Đang hiển thị' : 'Đã ẩn'}</AdminBadge>
                {item.scheduledAt && new Date(item.scheduledAt).getTime() > Date.now() && <span className="text-xs font-semibold text-sky-700">Đang hẹn lịch</span>}
              </div>
            </td>
            <td className="px-4 py-3">
              <div className="flex items-center gap-2">
                {Array.isArray(item.comments) && item.comments.length > 0 && (
                  <button type="button" onClick={() => setActiveVideoCommentsItem(item)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900" title={`${item.comments.length} Bình luận`}>
                    <div className="relative">
                      <MessageSquare className="h-4 w-4" />
                      <span className="absolute -right-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">{item.comments.length}</span>
                    </div>
                  </button>
                )}
                {canUpdateContent && (
                  <button type="button" onClick={() => editContent(item)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700">
                    <Edit2 className="h-4 w-4" />
                  </button>
                )}
                {canDeleteContent && (
                  <button type="button" onClick={() => void confirmDelete(item.title, () => apiDb.adminDeleteVideo(item.id))} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
                {!canUpdateContent && !canDeleteContent && <span className="text-xs text-slate-400">Chỉ xem</span>}
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
      
      {activeVideoCommentsItem && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Bình luận video</h3>
                <p className="mt-1 text-sm text-slate-500">{activeVideoCommentsItem.title}</p>
              </div>
              <button type="button" onClick={() => setActiveVideoCommentsItem(null)} title="Đóng" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">
              <div className="space-y-4">
                {activeVideoCommentsItem.comments.map((comment: any) => (
                  <div key={comment.id} className={`rounded-lg border bg-slate-50 p-3 text-sm ${comment.isHidden ? 'border-amber-200 opacity-70' : 'border-slate-200'}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="font-bold text-slate-900">{comment.userName || 'Khách hàng'}</span>
                        {comment.replyToUserName && <span className="ml-1 text-slate-500">trả lời @{comment.replyToUserName}</span>}
                        <p className="mt-1.5 text-slate-700">{comment.content}</p>
                        {comment.isHidden && <p className="mt-1.5 font-semibold text-amber-700">Đang ẩn{comment.moderationReason ? `: ${comment.moderationReason}` : ''}</p>}
                      </div>
                      <button type="button" onClick={() => toggleVideoCommentHidden(activeVideoCommentsItem, comment)} className="shrink-0 rounded border border-slate-200 bg-white px-2 py-1 font-bold text-slate-600 hover:bg-slate-50">{comment.isHidden ? 'Hiện' : 'Ẩn'}</button>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <input value={videoReplyDrafts[comment.id] || ''} onChange={(event) => setVideoReplyDrafts((drafts: any) => ({ ...drafts, [comment.id]: event.target.value }))} placeholder={`Trả lời ${comment.userName || 'khách hàng'}`} className="h-9 flex-1 rounded-md border border-slate-200 px-3 outline-none focus:border-red-400" />
                      <button type="button" onClick={() => replyVideoComment(activeVideoCommentsItem, comment)} className="rounded-md bg-red-600 px-4 font-bold text-white transition hover:bg-red-700">Gửi</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </AdminPanel>
  );
}
