import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, m } from 'motion/react';
import { ImagePlus, Pencil, Star, Trash2, X } from 'lucide-react';
import { publicApi } from '../../../services/publicApi';
import { resolveImageUrl } from '../../../services/productMedia';
import { useAuth } from '../../../context/AuthContext';

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

const ratingStars = [1, 2, 3, 4, 5];
const allowedReviewImageTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
const maxReviewImages = 5;
const maxReviewImageBytes = 5 * 1024 * 1024;

type SelectedReviewImage = {
  file: File;
  previewUrl: string;
};

type ProductReviewsProps = {
  productId: string;
  displayMode?: 'full' | 'form' | 'list';
};

export function ProductReviews({ productId, displayMode = 'full' }: ProductReviewsProps) {
  const { user } = useAuth();
  return <ProductReviewsContent key={`${productId}-${user?.uid || 'guest'}-${displayMode}`} productId={productId} user={user} displayMode={displayMode} />;
}

function ProductReviewsContent({ productId, user, displayMode }: ProductReviewsProps & { user: any }) {
  const isFormOnly = displayMode === 'form';
  const isListOnly = displayMode === 'list';
  const previewUrlsRef = useRef(new Set<string>());
  const [reviews, setReviews] = useState<Review[]>([]);
  const [newReview, setNewReview] = useState('');
  const [mediaUrls, setMediaUrls] = useState<string[]>([]);
  const [selectedImages, setSelectedImages] = useState<SelectedReviewImage[]>([]);
  const [rating, setRating] = useState(5);
  const [loading, setLoading] = useState(!isFormOnly);
  const [eligibility, setEligibility] = useState<any>(null);
  const [eligibilityLoading, setEligibilityLoading] = useState(Boolean(user));
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');
  const [editingReviewId, setEditingReviewId] = useState<string | null>(null);

  const applyExistingReview = useCallback((existingReview: any) => {
    if (!existingReview) return;
    setEditingReviewId(existingReview.id || null);
    setNewReview(existingReview.comment || '');
    setRating(Number(existingReview.rating || 5));
    setMediaUrls(Array.isArray(existingReview.mediaUrls) ? existingReview.mediaUrls : []);
  }, []);

  const clearSelectedImages = useCallback(() => {
    previewUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
    previewUrlsRef.current.clear();
    setSelectedImages([]);
  }, []);

  useEffect(() => () => {
    previewUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
    previewUrlsRef.current.clear();
  }, []);

  useEffect(() => {
    if (isFormOnly) return;
    let isActive = true;
    const fetchReviews = async () => {
      try {
        const items = await publicApi.listReviews(productId);
        if (!isActive) return;
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
        if (!isActive) return;
        console.error(err);
        setReviews([]);
      } finally {
        if (!isActive) return;
        setLoading(false);
      }
    };
    fetchReviews();
    return () => {
      isActive = false;
    };
  }, [isFormOnly, productId]);

  useEffect(() => {
    if (!user) return;
    let isActive = true;
    publicApi.reviewEligibility(productId)
      .then((data) => {
        if (!isActive) return;
        setEligibility(data);
        applyExistingReview(data?.existingReview);
      })
      .catch(() => {
        if (!isActive) return;
        setEligibility({
          canReview: false,
          message: 'Không thể kiểm tra quyền đánh giá lúc này.',
        });
      })
      .finally(() => {
        if (isActive) setEligibilityLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [applyExistingReview, productId, user]);

  const handleImageSelection = (files: FileList | null) => {
    const nextFiles = Array.from(files || []);
    if (nextFiles.length === 0) return;
    if (mediaUrls.length + selectedImages.length + nextFiles.length > maxReviewImages) {
      setSubmitError(`Mỗi đánh giá chỉ được tối đa ${maxReviewImages} ảnh.`);
      return;
    }
    const unsupportedFile = nextFiles.find(file => !allowedReviewImageTypes.has(file.type));
    if (unsupportedFile) {
      setSubmitError(`Ảnh ${unsupportedFile.name} không đúng định dạng JPG, PNG hoặc WEBP.`);
      return;
    }
    const oversizedFile = nextFiles.find(file => file.size > maxReviewImageBytes);
    if (oversizedFile) {
      setSubmitError(`Ảnh ${oversizedFile.name} vượt quá 5 MB.`);
      return;
    }

    const nextImages = nextFiles.map(file => {
      const previewUrl = URL.createObjectURL(file);
      previewUrlsRef.current.add(previewUrl);
      return { file, previewUrl };
    });
    setSelectedImages(current => [...current, ...nextImages]);
    setSubmitError('');
  };

  const removeSelectedImage = (previewUrl: string) => {
    URL.revokeObjectURL(previewUrl);
    previewUrlsRef.current.delete(previewUrl);
    setSelectedImages(current => current.filter(image => image.previewUrl !== previewUrl));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newReview.trim()) return;
    const canUpdateExisting = Boolean(editingReviewId && eligibility?.canEdit);
    if (!eligibility?.canReview && !canUpdateExisting) {
      setSubmitError(eligibility?.message || 'Bạn chưa đủ điều kiện đánh giá sản phẩm này.');
      return;
    }

    const userName = user?.displayName || user?.email || 'Khách hàng';
    const normalizedComment = newReview.trim();
    let uploadedUrls: string[] = [];
    setSubmitting(true);
    setSubmitError('');
    setSubmitSuccess('');
    try {
      if (selectedImages.length > 0) {
        const uploadedImages = await publicApi.uploadReviewImages(productId, selectedImages.map(image => image.file));
        uploadedUrls = uploadedImages.map(image => image.fileKey);
      }
      const nextMediaUrls = [...mediaUrls, ...uploadedUrls];
      const response = editingReviewId
        ? await publicApi.updateOwnReview(productId, editingReviewId, {
            userName,
            rating,
            comment: normalizedComment,
            mediaUrls: nextMediaUrls,
          })
        : await publicApi.createReview(productId, {
            userName,
            rating,
            comment: normalizedComment,
            mediaUrls: nextMediaUrls,
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
          comment: normalizedComment,
          mediaUrls: nextMediaUrls,
          status: response.status || 'PENDING',
        },
      });
      setEditingReviewId(nextReviewId || null);
      setMediaUrls(nextMediaUrls);
      clearSelectedImages();
      setSubmitSuccess(response.message || 'Đánh giá đã được gửi.');
    } catch (err: any) {
      if (uploadedUrls.length > 0) {
        setMediaUrls(current => Array.from(new Set([...current, ...uploadedUrls])));
        clearSelectedImages();
      }
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
      await publicApi.deleteOwnReview(productId, editingReviewId);
      setEditingReviewId(null);
      setNewReview('');
      setMediaUrls([]);
      clearSelectedImages();
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
    <div className={isFormOnly ? 'mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4' : 'mt-8 rounded-xl border border-gray-100 bg-white p-6 shadow-sm'}>
      <h3 className="mb-4 text-xl font-bold">
        {isFormOnly ? 'Đánh giá sản phẩm' : isListOnly ? 'Đánh giá từ khách hàng' : 'Đánh giá & Nhận xét'}
      </h3>

      {!isListOnly && (!user ? (
        <div className={`${isFormOnly ? '' : 'mb-8'} rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800`}>
          Vui lòng đăng nhập và chỉ những đơn hàng đã hoàn thành mới có thể đánh giá sản phẩm.
        </div>
      ) : eligibilityLoading ? (
        <div role="status" className={`${isFormOnly ? '' : 'mb-8'} rounded-lg border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-500`}>
          Đang kiểm tra điều kiện đánh giá...
        </div>
      ) : !eligibility?.canReview && !eligibility?.canEdit ? (
        <div className={`${isFormOnly ? '' : 'mb-8'} rounded-lg border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-600`}>
          {eligibility?.message || 'Chỉ khách hàng có đơn hàng đã hoàn thành mới có thể đánh giá sản phẩm này.'}
        </div>
      ) : null)}

      {!isListOnly && (eligibility?.canReview || eligibility?.canEdit) && (
        <form onSubmit={handleSubmit} className={`${isFormOnly ? '' : 'mb-8'} rounded-lg border border-gray-200 bg-white p-4`}>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm font-semibold">Đánh giá của bạn:</span>
            <div className="flex gap-1" aria-label="Chọn số sao đánh giá">
              {ratingStars.map((star) => (
                <button
                  key={star}
                  type="button"
                  aria-label={`Chọn ${star} sao`}
                  aria-pressed={rating === star}
                  onClick={() => setRating(star)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-amber-300"
                >
                  <Star className={`h-5 w-5 ${star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                </button>
              ))}
            </div>
          </div>
          <textarea
            aria-label="Nhập nhận xét về sản phẩm"
            placeholder="Nhập nhận xét của bạn về sản phẩm này..."
            className="mb-3 min-h-[100px] w-full rounded-lg border border-gray-300 p-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            value={newReview}
            onChange={(event) => setNewReview(event.target.value)}
          />
          <div className="mb-3">
            <label
              aria-disabled={submitting || mediaUrls.length + selectedImages.length >= maxReviewImages}
              className={`inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-bold text-slate-700 transition focus-within:ring-2 focus-within:ring-slate-300 ${submitting || mediaUrls.length + selectedImages.length >= maxReviewImages ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-slate-50'}`}
            >
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                disabled={submitting || mediaUrls.length + selectedImages.length >= maxReviewImages}
                onChange={(event) => {
                  handleImageSelection(event.currentTarget.files);
                  event.currentTarget.value = '';
                }}
                className="sr-only"
              />
              <ImagePlus className="h-4 w-4" />
              Thêm hình ảnh
            </label>
            <p className="mt-1.5 text-xs font-medium text-slate-500">Tối đa 5 ảnh JPG, PNG hoặc WEBP; mỗi ảnh không quá 5 MB.</p>
          </div>
          {(mediaUrls.length > 0 || selectedImages.length > 0) && (
            <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {mediaUrls.map(url => {
                const isVideo = /\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(url);
                return (
                  <div key={url} className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                    {isVideo ? (
                      <video src={resolveImageUrl(url)} controls aria-label="Video đã tải lên cho đánh giá" className="h-28 w-full bg-black object-cover">
                        <track kind="captions" />
                      </video>
                    ) : (
                      <img src={resolveImageUrl(url)} alt="Ảnh đã tải lên cho đánh giá" className="h-28 w-full object-cover" />
                    )}
                    <button
                      type="button"
                      aria-label={isVideo ? 'Xóa video đã tải lên' : 'Xóa ảnh đã tải lên'}
                      onClick={() => setMediaUrls(current => current.filter(item => item !== url))}
                      className="absolute right-1.5 top-1.5 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950/75 text-white transition hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-white"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                );
              })}
              {selectedImages.map(image => (
                <div key={image.previewUrl} className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                  <img src={image.previewUrl} alt={`Ảnh đã chọn: ${image.file.name}`} className="h-28 w-full object-cover" />
                  <button
                    type="button"
                    aria-label={`Bỏ ảnh ${image.file.name}`}
                    onClick={() => removeSelectedImage(image.previewUrl)}
                    className="absolute right-1.5 top-1.5 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950/75 text-white transition hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
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

      {!isFormOnly && <div className="space-y-4">
        {loading && <div className="text-sm text-gray-400">Đang tải đánh giá...</div>}
        {!loading && reviews.length === 0 && <div className="text-sm text-gray-400">Chưa có đánh giá nào cho sản phẩm này.</div>}
        <LazyMotion features={domAnimation}>
          <AnimatePresence>
            {reviews.map((review) => (
              <m.div
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
                  {ratingStars.map((star) => (
                    <Star key={`${review.id}-star-${star}`} className={`h-3.5 w-3.5 ${star <= review.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
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
                      <video key={url} aria-label="Video đính kèm đánh giá" src={resolveImageUrl(url)} controls className="h-28 w-full rounded-lg border border-gray-200 bg-black object-cover">
                        <track kind="captions" />
                      </video>
                    ) : (
                      <img key={url} src={resolveImageUrl(url)} alt="Đính kèm đánh giá" className="h-28 w-full rounded-lg border border-gray-200 object-cover" />
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
              </m.div>
            ))}
          </AnimatePresence>
        </LazyMotion>
      </div>}
    </div>
  );
}
