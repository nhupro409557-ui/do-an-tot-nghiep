import { useMemo, useState } from 'react';
import { AdminBadge, AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';
import { resolveImageUrl } from '../../../services/productMedia';

type AdminProductInteractionsTabProps = Record<string, any>;
type InteractionMode = 'comments' | 'questions';

function isQuestion(item: any) {
  return item.interactionType === 'PRODUCT_QA';
}

function modeMatches(item: any, mode: InteractionMode) {
  return mode === 'questions' ? isQuestion(item) : !isQuestion(item);
}

export default function AdminProductInteractionsTab(props: AdminProductInteractionsTabProps) {
  const {
    filteredImageComments,
    imageCommentMetrics,
    query,
    replyToImageComment,
    setQuery,
    toggleImageCommentHidden,
    usePermission,
  } = props;
  const canUpdateReview = usePermission('review:update');
  const [mode, setMode] = useState<InteractionMode>('comments');
  const rows = useMemo(
    () => filteredImageComments.filter((item: any) => modeMatches(item, mode)),
    [filteredImageComments, mode],
  );
  const metrics = useMemo(() => {
    const items = filteredImageComments.filter((item: any) => modeMatches(item, mode));
    return {
      total: items.length,
      hidden: items.filter((item: any) => item.isHidden).length,
      retracted: items.filter((item: any) => item.isRetracted).length,
    };
  }, [filteredImageComments, mode]);
  const title = mode === 'questions' ? 'Hỏi đáp sản phẩm' : 'Bình luận sản phẩm';

  return (
    <AdminPanel
      title="Quản lý bình luận & hỏi đáp"
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, khách hàng hoặc nội dung" />}
    >
      <div className="mb-4 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-sm font-black uppercase tracking-wide text-slate-800">{title}</h3>
          <p className="text-xs text-slate-500">Bình luận và hỏi đáp dùng mô hình 2 tầng: câu gốc và các phản hồi tuyến tính bên dưới.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => setMode('comments')} className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${mode === 'comments' ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50'}`}>Bình luận</button>
          <button type="button" onClick={() => setMode('questions')} className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${mode === 'questions' ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50'}`}>Hỏi đáp</button>
        </div>
      </div>
      <div className="mb-4 flex flex-wrap gap-2 text-xs font-bold text-slate-600">
        <span className="rounded-full bg-slate-100 px-3 py-1">Tổng {metrics.total}</span>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">Đã ẩn {metrics.hidden}</span>
        <span className="rounded-full bg-rose-100 px-3 py-1 text-rose-700">Thu hồi {metrics.retracted}</span>
        {imageCommentMetrics.total !== metrics.total && <span className="rounded-full bg-sky-100 px-3 py-1 text-sky-800">Toàn bộ {imageCommentMetrics.total}</span>}
      </div>
      <AdminTable headers={['Sản phẩm', 'Người gửi', 'Nội dung', 'Ảnh', 'Trạng thái', 'Thao tác']}>
        {rows.length === 0 ? (
          <tr><td colSpan={6} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy nội dung phù hợp.</td></tr>
        ) : rows.map((comment: any) => (
          <tr key={comment.id}>
            <td className="px-4 py-3">
              <div className="font-semibold text-slate-900">{comment.productName || '-'}</div>
              <div className="mt-1 text-xs font-medium text-slate-500">
                SKU: {comment.productSku || '-'} · ID: {String(comment.productId || '-').slice(0, 8)}
              </div>
            </td>
            <td className="px-4 py-3">{comment.isRetracted ? 'Đã thu hồi' : comment.userName || 'Khách hàng'}</td>
            <td className="max-w-md px-4 py-3 text-sm text-slate-600">
              {comment.replyToUserName && <span className="mr-1 font-bold text-sky-700">@{comment.replyToUserName}</span>}
              <span className={comment.isRetracted ? 'italic text-slate-400' : ''}>{comment.content || '-'}</span>
              {comment.parentId && <div className="mt-1 text-xs font-semibold text-slate-400">Phản hồi tuyến tính</div>}
              {comment.moderationReason && <div className="mt-1 text-xs font-semibold text-amber-700">Tự động ẩn: {comment.moderationReason}</div>}
            </td>
            <td className="px-4 py-3">
              {comment.imageUrl ? <img src={resolveImageUrl(comment.imageUrl)} alt="" className="h-12 w-12 rounded-lg object-cover" /> : '-'}
            </td>
            <td className="px-4 py-3">
              <AdminBadge tone={comment.isHidden ? 'amber' : comment.isRetracted ? 'slate' : 'green'}>
                {comment.isHidden ? 'Đã ẩn' : comment.isRetracted ? 'Đã thu hồi' : 'Đang hiển thị'}
              </AdminBadge>
            </td>
            <td className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                {canUpdateReview && <button type="button" onClick={() => toggleImageCommentHidden(comment)} className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                  {comment.isHidden ? 'Hiện lại' : 'Ẩn'}
                </button>}
                {canUpdateReview && <button type="button" onClick={() => replyToImageComment(comment)} className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">
                  Phản hồi
                </button>}
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
