import { adminContentApi } from '../../admin-content/services/adminContentApi';
import { adminReviewsApi } from '../services/adminReviewsApi';

type UseAdminReviewsLogicParams = {
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminReviewsLogic({ reloadCurrentTab }: UseAdminReviewsLogicParams) {
  async function updateReviewStatus(review: any, status: 'PENDING' | 'PUBLISHED' | 'HIDDEN' | 'REJECTED') {
    await adminReviewsApi.adminUpdateReview(review.id, { status });
    await reloadCurrentTab();
  }

  async function replyToReview(review: any) {
    const nextReply = window.prompt(`Phản hồi đánh giá cho ${review.userName || 'khách hàng'}`, review.shopReply || '');
    if (nextReply === null) return;
    await adminReviewsApi.adminUpdateReview(review.id, { shopReply: nextReply });
    await reloadCurrentTab();
  }

  async function flagReview(review: any) {
    const reason = window.prompt(`Lý do báo cáo/đánh dấu đánh giá của ${review.userName || 'khách hàng'}`, review.flaggedReason || 'Có dấu hiệu nội dung xấu hoặc cần xem xét thêm');
    if (reason === null) return;
    await adminReviewsApi.adminUpdateReview(review.id, { flaggedReason: reason, status: review.status === 'PUBLISHED' ? 'HIDDEN' : review.status });
    await reloadCurrentTab();
  }

  async function markReviewSpam(review: any) {
    const reason = window.prompt(`Lý do đánh dấu spam cho đánh giá của ${review.userName || 'khách hàng'}`, review.spamReason || 'Spam hoặc nội dung lặp bất thường');
    if (reason === null) return;
    await adminReviewsApi.adminUpdateReview(review.id, { isSpam: true, spamReason: reason, status: 'REJECTED', moderationNote: 'Đánh dấu spam bởi quản trị viên.' });
    await reloadCurrentTab();
  }

  async function deleteReview(review: any) {
    if (!window.confirm(`Xóa vĩnh viễn đánh giá của ${review.userName || 'khách hàng'} cho sản phẩm ${review.productName}?`)) return;
    await adminReviewsApi.adminDeleteReview(review.id);
    await reloadCurrentTab();
  }

  async function replyToImageComment(comment: any) {
    const body = window.prompt(`Trả lời bình luận ảnh của ${comment.userName || 'khách hàng'}`, '');
    if (body === null || !body.trim()) return;
    await adminContentApi.adminReplyImageComment(comment.id, body.trim());
    await reloadCurrentTab();
  }

  async function toggleImageCommentHidden(comment: any) {
    await adminContentApi.adminUpdateImageComment(comment.id, { isHidden: !comment.isHidden });
    await reloadCurrentTab();
  }

  return {
    updateReviewStatus,
    replyToReview,
    flagReview,
    markReviewSpam,
    deleteReview,
    replyToImageComment,
    toggleImageCommentHidden,
  };
}
