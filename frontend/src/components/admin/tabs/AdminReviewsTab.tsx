import { AdminBadge, AdminPanel, AdminTable, MiniMetric, SearchBox, Select } from '../AdminDashboardParts';
import { reviewStarOptions, reviewStatusLabel, reviewStatusOptions } from '../../../pages/AdminDashboardConfig';

type AdminReviewsTabProps = Record<string, any>;

export default function AdminReviewsTab(props: AdminReviewsTabProps) {
  const {
    deleteReview,
    filteredReviews,
    flagReview,
    markReviewSpam,
    query,
    replyToReview,
    reviewMetrics,
    reviewStarFilter,
    reviewStatusFilter,
    reviewSummary,
    setQuery,
    setReviewStarFilter,
    setReviewStatusFilter,
    updateReviewStatus,
  } = props;

  return (
    <AdminPanel
      title="Quản lý đánh giá theo sản phẩm"
      filters={
        <>
          <Select noLabel={true} label="Số sao" value={reviewStarFilter} onChange={setReviewStarFilter} options={reviewStarOptions} />
          <Select noLabel={true} label="Trạng thái" value={reviewStatusFilter} onChange={setReviewStatusFilter} options={reviewStatusOptions} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, khách hàng, nội dung" />
        </>
      }
    >
      <div className="mb-5 grid gap-3 md:grid-cols-4">
        <MiniMetric label="Tổng đánh giá" value={reviewMetrics.total} helper="Tất cả trạng thái" />
        <MiniMetric label="Chờ duyệt" value={reviewMetrics.pending} helper="Kiểm duyệt trước khi public" />
        <MiniMetric label="Đang hiển thị" value={reviewMetrics.published} helper="Đánh giá đang public" />
        <MiniMetric label="Cần xem lại" value={reviewMetrics.flagged} helper="Bị báo xấu hoặc nghi spam" />
      </div>
      <div className="mb-6 overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50/70">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs font-bold uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3">Sản phẩm</th>
              <th className="px-4 py-3">TB sao</th>
              <th className="px-4 py-3">Đã public</th>
              <th className="px-4 py-3">Chờ duyệt</th>
              <th className="px-4 py-3">Bị gắn cờ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {reviewSummary.slice(0, 6).map((item: any) => (
              <tr key={item.productId}>
                <td className="px-4 py-3 font-semibold text-slate-900">{item.productName}</td>
                <td className="px-4 py-3 font-bold text-amber-600">{item.averageRating ? `${item.averageRating}/5` : '-'}</td>
                <td className="px-4 py-3">{item.publishedReviews || 0}</td>
                <td className="px-4 py-3">{item.pendingReviews || 0}</td>
                <td className="px-4 py-3">{item.flaggedReviews || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <AdminTable headers={['Sản phẩm', 'Khách hàng', 'Điểm', 'Nội dung', 'Media / phản hồi', 'Ngày', 'Trạng thái', 'Thao tác']}>
        {filteredReviews.length === 0 ? (
          <tr><td colSpan={8} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy đánh giá phù hợp.</td></tr>
        ) : filteredReviews.map((review: any) => (
          <tr key={review.id}>
            <td className="px-4 py-3 font-semibold text-slate-900">{review.productName}</td>
            <td className="px-4 py-3">{review.userName}</td>
            <td className="px-4 py-3 font-bold text-amber-600">{review.rating}/5</td>
            <td className="max-w-md px-4 py-3 text-sm text-slate-600">{review.comment || '-'}</td>
            <td className="px-4 py-3 text-sm text-slate-600">
              <div>{Array.isArray(review.mediaUrls) && review.mediaUrls.length ? `${review.mediaUrls.length} tệp` : 'Không có media'}</div>
              <div className="mt-1 text-xs">
                {review.shopReply ? `Shop đã phản hồi` : 'Chưa phản hồi'}
                {review.flaggedReason ? ` • Báo xấu` : ''}
                {review.isSpam ? ` • Spam` : ''}
                {review.orderOutcome ? ` • ${review.orderOutcome === 'DA_HOAN_TIEN' ? 'Đã hoàn tiền' : 'Đã trả hàng'}` : ''}
              </div>
            </td>
            <td className="px-4 py-3">{review.createdAt ? new Date(review.createdAt).toLocaleDateString('vi-VN') : '-'}</td>
            <td className="px-4 py-3">
              <div className="flex flex-col gap-2">
                <AdminBadge tone={review.status === 'PUBLISHED' ? 'green' : review.status === 'PENDING' ? 'blue' : review.status === 'REJECTED' ? 'red' : 'slate'}>{reviewStatusLabel[review.status] || review.status}</AdminBadge>
                {review.flaggedReason && <span className="text-xs font-semibold text-amber-700">Báo xấu: {review.flaggedReason}</span>}
                {review.moderationNote && <span className="text-xs text-slate-500">Ghi chú: {review.moderationNote}</span>}
              </div>
            </td>
            <td className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                {review.status === 'PENDING' ? (
                  <button type="button" onClick={() => updateReviewStatus(review, 'PUBLISHED')} className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100">Duyệt</button>
                ) : review.status === 'PUBLISHED' ? (
                  <button type="button" onClick={() => updateReviewStatus(review, 'HIDDEN')} className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50">Ẩn</button>
                ) : (
                  <button type="button" onClick={() => updateReviewStatus(review, 'PUBLISHED')} className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100">Hiện lại</button>
                )}
                <button type="button" onClick={() => updateReviewStatus(review, 'REJECTED')} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800 transition hover:bg-amber-100">Từ chối</button>
                <button type="button" onClick={() => replyToReview(review)} className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">Phản hồi</button>
                <button type="button" onClick={() => flagReview(review)} className="rounded-md border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-bold text-orange-700 transition hover:bg-orange-100">Báo xấu</button>
                <button type="button" onClick={() => markReviewSpam(review)} className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100">Spam</button>
                <button type="button" onClick={() => deleteReview(review)} className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100">Xóa</button>
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
