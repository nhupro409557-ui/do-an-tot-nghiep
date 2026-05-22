import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Pencil, Star, Trash2 } from 'lucide-react';
import { apiDb } from '../../services/apiDb';
import { useAuth } from '../../context/AuthContext';

interface Review {
  id: string;
  author: string;
  rating: number;
  content: string;
  date: string;
  mediaUrls: string[];
  shopReply?: string;
  shopRepliedAt?: string;
  orderOutcome?: string;
}

export function ProductReviews({ productId }: { productId: string }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [newReview, setNewReview] = useState('');
  const [mediaInput, setMediaInput] = useState('');
  const [rating, setRating] = useState(5);
  const [loading, setLoading] = useState(true);
  const [eligibility, setEligibility] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');
  const [editingReviewId, setEditingReviewId] = useState<string | null>(null);

  useEffect(() => {
    const fetchReviews = async () => {
      try {
        const items = await apiDb.listReviews(productId);
        items.sort((a: any, b: any) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        setReviews(items.map((data: any) => ({
          id: data.id,
          author: data.userName || data.author || 'Khách hàng',
          rating: data.rating || 0,
          content: data.comment || data.content || '',
          date: data.createdAt ? new Date(data.createdAt).toISOString().split('T')[0] : '',
          mediaUrls: Array.isArray(data.mediaUrls) ? data.mediaUrls : [],
          shopReply: data.shopReply || '',
          shopRepliedAt: data.shopRepliedAt || '',
          orderOutcome: data.orderOutcome || '',
        })));
      } catch (err) {
        console.error(err);
        setReviews([]);
      } finally {
        setLoading(false);
      }
    };
    fetchReviews();
  }, [productId]);

  useEffect(() => {
    if (!user) {
      setEligibility(null);
      return;
    }
    apiDb.reviewEligibility(productId)
      .then(setEligibility)
      .catch(() => setEligibility({
        canReview: false,
        message: 'Không thể kiểm tra quyền đánh giá lúc này.',
      }));
  }, [productId, user]);

  useEffect(() => {
    if (!eligibility?.existingReview) return;
    const own = eligibility.existingReview;
    setEditingReviewId(own.id || null);
    setNewReview(own.comment || '');
    setRating(Number(own.rating || 5));
    setMediaInput(Array.isArray(own.mediaUrls) ? own.mediaUrls.join('\n') : '');
  }, [eligibility?.existingReview?.id]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newReview.trim()) return;
    const canUpdateExisting = Boolean(editingReviewId && eligibility?.canEdit);
    if (!eligibility?.canReview && !canUpdateExisting) {
      setSubmitError(eligibility?.message || 'Bạn chưa đủ điều kiện đánh giá sản phẩm này.');
      return;
    }

    const userName = user?.displayName || user?.email || 'Khách hàng';
    const mediaUrls = mediaInput.split('\n').map((item) => item.trim()).filter(Boolean);
    setSubmitting(true);
    setSubmitError('');
    setSubmitSuccess('');
    try {
      const response = editingReviewId
        ? await apiDb.updateOwnReview(productId, editingReviewId, {
            userName,
            rating,
            comment: newReview.trim(),
            mediaUrls,
          })
        : await apiDb.createReview(productId, {
            userName,
            rating,
            comment: newReview.trim(),
            mediaUrls,
          });
      const nextReviewId = editingReviewId || ('id' in response ? response.id : editingReviewId);
      setEligibility({
        ...eligibility,
        canReview: false,
        alreadyReviewed: true,
        canEdit: true,
        canDelete: true,
        message: response.message || 'Đánh giá của bạn đang chờ duyệt.',
        existingReview: {
          ...(eligibility?.existingReview || {}),
          id: nextReviewId,
          userName,
          rating,
          comment: newReview.trim(),
          mediaUrls,
          status: response.status || 'PENDING',
        },
      });
      setEditingReviewId(nextReviewId || null);
      setNewReview('');
      setMediaInput('');
      setRating(5);
      setSubmitSuccess(response.message || 'Đánh giá đã được gửi.');
    } catch (err: any) {
      setSubmitError(err.message || 'Không thể gửi đánh giá.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteOwnReview = async () => {
    if (!editingReviewId || !eligibility?.canDelete) return;
    if (!window.confirm('Xóa đánh giá của bạn cho sản phẩm này?')) return;
    setSubmitting(true);
    setSubmitError('');
    setSubmitSuccess('');
    try {
      await apiDb.deleteOwnReview(productId, editingReviewId);
      setEditingReviewId(null);
      setNewReview('');
      setMediaInput('');
      setRating(5);
      setEligibility({
        ...eligibility,
        canReview: eligibility?.withinReviewWindow && !eligibility?.orderOutcome,
        alreadyReviewed: false,
        canEdit: false,
        canDelete: false,
        existingReview: null,
        message: 'Đánh giá đã được xóa. Bạn có thể gửi lại nếu vẫn còn trong thời gian cho phép.',
      });
      setSubmitSuccess('Đánh giá của bạn đã được xóa.');
    } catch (err: any) {
      setSubmitError(err.message || 'Không thể xóa đánh giá.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-8 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <h3 className="mb-6 font-display text-xl font-bold">Đánh giá & Nhận xét</h3>

      {!user ? (
        <div className="mb-8 rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
          Vui lòng đăng nhập và chỉ những đơn hàng đã hoàn thành mới có thể đánh giá sản phẩm.
        </div>
      ) : !eligibility?.canReview && !eligibility?.canEdit ? (
        <div className="mb-8 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm font-semibold text-slate-600">
          {eligibility?.message || 'Chỉ khách hàng có đơn hàng đã hoàn thành mới có thể đánh giá sản phẩm này.'}
        </div>
      ) : null}

      {(eligibility?.canReview || eligibility?.canEdit) && (
        <form onSubmit={handleSubmit} className="mb-8 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm font-semibold">Đánh giá của bạn:</span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  className={`h-5 w-5 cursor-pointer ${star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`}
                  onClick={() => setRating(star)}
                />
              ))}
            </div>
          </div>
          <textarea
            placeholder="Nhập nhận xét của bạn về sản phẩm này..."
            className="mb-3 min-h-[100px] w-full rounded-lg border border-gray-300 p-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            value={newReview}
            onChange={(event) => setNewReview(event.target.value)}
          />
          <textarea
            placeholder="Tùy chọn: dán link ảnh/video, mỗi dòng một URL"
            className="mb-3 min-h-[88px] w-full rounded-lg border border-gray-300 p-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            value={mediaInput}
            onChange={(event) => setMediaInput(event.target.value)}
          />
          {submitError && <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{submitError}</div>}
          {submitSuccess && <div className="mb-3 rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">{submitSuccess}</div>}
          <div className="flex justify-end gap-3">
            {editingReviewId && eligibility?.canDelete && (
              <button type="button" disabled={submitting} onClick={handleDeleteOwnReview} className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-5 py-2 text-sm font-bold text-red-700 transition hover:bg-red-100 disabled:opacity-60">
                <Trash2 className="h-4 w-4" />
                Xóa đánh giá
              </button>
            )}
            <button type="submit" disabled={submitting} className="rounded-lg bg-primary px-6 py-2 text-sm font-bold text-white transition hover:bg-red-700 disabled:opacity-60">
              {submitting ? 'Đang gửi...' : editingReviewId ? 'Cập nhật đánh giá' : 'Gửi đánh giá'}
            </button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {loading && <div className="text-sm text-gray-400">Đang tải đánh giá...</div>}
        {!loading && reviews.length === 0 && <div className="text-sm text-gray-400">Chưa có đánh giá nào cho sản phẩm này.</div>}
        <AnimatePresence>
          {reviews.map((review) => (
            <motion.div
              key={review.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="border-b border-gray-100 pb-4 last:border-0 last:pb-0"
            >
              <div className="mb-2 flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-sm font-bold text-gray-500">
                    {review.author.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{review.author}</p>
                    <p className="font-mono text-xs text-gray-400">{review.date}</p>
                  </div>
                </div>
                <div className="flex gap-0.5">
                  {[...Array(5)].map((_, index) => (
                    <Star key={index} className={`h-3.5 w-3.5 ${index < review.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                  ))}
                </div>
              </div>
              <p className="pl-10 text-sm text-gray-600">{review.content}</p>
              {review.orderOutcome && (
                <div className="mt-2 ml-10 inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                  {review.orderOutcome === 'DA_HOAN_TIEN' ? 'Đơn liên quan đã hoàn tiền' : 'Đơn liên quan đã trả hàng'}
                </div>
              )}
              {review.mediaUrls.length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-3 pl-10 sm:grid-cols-3">
                  {review.mediaUrls.map((url) => {
                    const isVideo = /\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(url);
                    return isVideo ? (
                      <video key={url} controls className="h-28 w-full rounded-lg border border-gray-200 bg-black object-cover">
                        <source src={url} />
                      </video>
                    ) : (
                      <img key={url} src={url} alt="Đính kèm đánh giá" className="h-28 w-full rounded-lg border border-gray-200 object-cover" />
                    );
                  })}
                </div>
              )}
              {review.shopReply && (
                <div className="mt-3 ml-10 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                  <p className="font-semibold">Phản hồi từ shop</p>
                  <p className="mt-1 whitespace-pre-line">{review.shopReply}</p>
                  {review.shopRepliedAt && <p className="mt-2 text-xs font-medium text-blue-700">Cập nhật {new Date(review.shopRepliedAt).toLocaleDateString('vi-VN')}</p>}
                </div>
              )}
              {eligibility?.existingReview?.id === review.id && (
                <div className="mt-3 ml-10 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700">
                  <Pencil className="h-3.5 w-3.5" />
                  Đây là đánh giá của bạn
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
