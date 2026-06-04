import { useMemo, useState, type FormEvent } from 'react';
import { apiDb } from '../../../services/apiDb';
import { emptyContentForm, matchesSearch, splitIds } from '../AdminDashboardConfig';

type UseAdminContentLogicParams = {
  contentItems: any[];
  products: any[];
  query: string;
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminContentLogic({ contentItems, products, query, reloadCurrentTab }: UseAdminContentLogicParams) {
  const [contentTypeFilter, setContentTypeFilter] = useState('all');
  const [contentStatusFilter, setContentStatusFilter] = useState('all');
  const [videoProductSearch, setVideoProductSearch] = useState('');
  const [videoProductCategoryFilter, setVideoProductCategoryFilter] = useState('all');
  const [videoProductBrandFilter, setVideoProductBrandFilter] = useState('all');
  const [videoReplyDrafts, setVideoReplyDrafts] = useState<Record<string, string>>({});
  const [activeVideoCommentsItem, setActiveVideoCommentsItem] = useState<any | null>(null);
  const [contentForm, setContentForm] = useState(emptyContentForm);
  const [editingContentId, setEditingContentId] = useState<string | null>(null);
  const [contentSaving, setContentSaving] = useState(false);
  const [contentCloseSignal, setContentCloseSignal] = useState(0);
  const [contentNotice, setContentNotice] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const filteredContentItems = useMemo(() => {
    return contentItems.filter((item) => {
      const matchesQuery = matchesSearch(item, query, ['title', 'description', 'status', 'contentType']);
      const matchesType = contentTypeFilter === 'all' || item.videoCategory === contentTypeFilter;
      const matchesStatus = contentStatusFilter === 'all' || item.status === contentStatusFilter;
      return matchesQuery && matchesType && matchesStatus;
    });
  }, [contentItems, contentStatusFilter, contentTypeFilter, query]);

  const selectedVideoProductIds = useMemo(() => splitIds(contentForm.productIds), [contentForm.productIds]);

  const videoProductChoices = useMemo(() => {
    const keyword = videoProductSearch.trim().toLowerCase();
    return products
      .filter((product) => {
        if (videoProductCategoryFilter !== 'all' && String(product.categoryId || product.category_id || product.category || '') !== videoProductCategoryFilter) return false;
        if (videoProductBrandFilter !== 'all' && String(product.brandId || product.brand_id || product.brand || '') !== videoProductBrandFilter) return false;
        if (!keyword) return true;
        return [product.name, product.sku, product.brand, product.categoryName, product.category]
          .some((value) => String(value || '').toLowerCase().includes(keyword));
      })
      .slice(0, 30);
  }, [products, videoProductBrandFilter, videoProductCategoryFilter, videoProductSearch]);

  function resetContentForm() {
    setEditingContentId(null);
    setContentForm(emptyContentForm);
    setContentSaving(false);
  }

  function serializeContentComments(value: string) {
    return value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const [userName, ...rest] = line.split(':');
        const content = rest.join(':').trim();
        return {
          id: `draft-${index + 1}`,
          userName: (content ? userName : 'Khách hàng').trim() || 'Khách hàng',
          isHidden: false,
        };
      });
  }

  async function handleContentSubmit(event: FormEvent) {
    event.preventDefault();
    if (contentSaving) return;
    setContentSaving(true);
    setContentNotice(null);
    const payload = {
      ...contentForm,
      contentType: 'VIDEO',
      productIds: splitIds(contentForm.productIds),
      categoryIds: [],
      comments: [],
      sortOrder: Number(contentForm.sortOrder || 0),
      scheduledAt: contentForm.scheduledAt || null,
      publishedAt: contentForm.publishedAt || null,
      videoUrl: contentForm.videoUrl.trim() || null,
      thumbnailUrl: contentForm.thumbnailUrl.trim() || null,
      bannerImageUrl: null,
      ctaLabel: contentForm.ctaLabel.trim() || null,
      ctaUrl: contentForm.ctaUrl.trim() || null,
      version: editingContentId ? Number(contentForm.version || 1) : undefined,
    };
    try {
      if (editingContentId) await apiDb.adminUpdateVideo(editingContentId, payload);
      setContentNotice({ type: 'success', text: editingContentId ? 'Đã lưu video thành công.' : 'Đã thêm video thành công.' });
      resetContentForm();
      setContentCloseSignal((value) => value + 1);
      await reloadCurrentTab();
    } catch (error) {
      setContentNotice({ type: 'error', text: error instanceof Error ? error.message : 'Không thể lưu video. Vui lòng kiểm tra lại thông tin.' });
    }
  }

  function editContent(item: any) {
    setEditingContentId(item.id);
    setContentForm({
      title: item.title || '',
      description: item.description || '',
      contentType: item.contentType || 'VIDEO',
      videoSource: item.videoSource || 'UPLOAD',
      videoCategory: item.videoCategory || 'PRODUCT',
      status: item.status || 'DRAFT',
      videoUrl: item.videoUrl || '',
      thumbnailUrl: item.thumbnailUrl || '',
      bannerImageUrl: item.bannerImageUrl || '',
      contentBody: item.contentBody || '',
      ctaLabel: item.ctaLabel || '',
      ctaUrl: item.ctaUrl || '',
      productIds: Array.isArray(item.productIds) ? item.productIds.join(', ') : '',
      categoryIds: Array.isArray(item.categoryIds) ? item.categoryIds.join(', ') : '',
      commentsText: Array.isArray(item.comments) ? item.comments.map((comment: any) => `${comment.userName || 'Khách hàng'}: ${comment.content || ''}`).join('\n') : '',
      likeCount: Number(item.likeCount || 0),
      viewCount: Number(item.viewCount || 0),
      sortOrder: Number(item.sortOrder || 0),
      scheduledAt: item.scheduledAt ? String(item.scheduledAt).slice(0, 16) : '',
      publishedAt: item.publishedAt ? String(item.publishedAt).slice(0, 16) : '',
      isActive: item.isActive !== false,
      version: Number(item.version || 1),
    });
  }

  function setVideoProductSelected(productId: string, selected: boolean) {
    const current = new Set(splitIds(contentForm.productIds));
    if (selected) current.add(productId);
    else current.delete(productId);
    setContentForm({ ...contentForm, productIds: Array.from(current).join(', ') });
  }

  async function replyVideoComment(video: any, comment: any) {
    const body = (videoReplyDrafts[comment.id] || '').trim();
    if (!body) return;
    await apiDb.adminReplyVideoComment(video.id, comment.id, body);
    setVideoReplyDrafts((drafts) => ({ ...drafts, [comment.id]: '' }));
    await reloadCurrentTab();
  }

  async function toggleVideoCommentHidden(video: any, comment: any) {
    await apiDb.adminUpdateVideoComment(video.id, comment.id, { isHidden: !comment.isHidden });
    await reloadCurrentTab();
  }

  async function deleteContentVideo(videoId: string) {
    await apiDb.adminDeleteVideo(videoId);
    await reloadCurrentTab();
  }

  return {
    contentTypeFilter,
    setContentTypeFilter,
    contentStatusFilter,
    setContentStatusFilter,
    videoProductSearch,
    setVideoProductSearch,
    videoProductCategoryFilter,
    setVideoProductCategoryFilter,
    videoProductBrandFilter,
    setVideoProductBrandFilter,
    videoReplyDrafts,
    setVideoReplyDrafts,
    activeVideoCommentsItem,
    setActiveVideoCommentsItem,
    contentForm,
    setContentForm,
    editingContentId,
    setEditingContentId,
    contentSaving,
    setContentSaving,
    contentCloseSignal,
    setContentCloseSignal,
    contentNotice,
    setContentNotice,
    filteredContentItems,
    selectedVideoProductIds,
    videoProductChoices,
    resetContentForm,
    serializeContentComments,
    handleContentSubmit,
    editContent,
    setVideoProductSelected,
    replyVideoComment,
    toggleVideoCommentHidden,
    deleteContentVideo,
  };
}
