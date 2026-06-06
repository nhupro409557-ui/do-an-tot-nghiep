import type React from 'react';
import { useMemo, useState } from 'react';
import { matchesSearch } from '../../admin-shell/components/AdminDashboardConfig';
import { adminContentApi } from '../services/adminContentApi';

type BannerForm = {
  title: string;
  description: string;
  bannerImageUrl: string;
  categoryId: string;
  productId: string;
  sortOrder: number;
  status: string;
  isActive: boolean;
  version: number;
};

const emptyBannerForm: BannerForm = {
  title: '',
  description: '',
  bannerImageUrl: '',
  categoryId: '',
  productId: '',
  sortOrder: 0,
  status: 'PUBLISHED',
  isActive: true,
  version: 1,
};

export function useAdminBannersLogic(params: {
  banners: any[];
  query: string;
  reloadCurrentTab: () => Promise<void>;
}) {
  const { banners, query, reloadCurrentTab } = params;
  const [bannerForm, setBannerForm] = useState<BannerForm>(emptyBannerForm);
  const [editingBannerId, setEditingBannerId] = useState<string | null>(null);
  const [bannerSaving, setBannerSaving] = useState(false);
  const [bannerNotice, setBannerNotice] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const filteredBanners = useMemo(() => {
    return banners.filter((item) => matchesSearch(item, query, ['title', 'description', 'status']));
  }, [banners, query]);

  function resetBannerForm() {
    setBannerForm(emptyBannerForm);
    setEditingBannerId(null);
    setBannerSaving(false);
  }

  function editBanner(item: any) {
    setEditingBannerId(item.id);
    setBannerForm({
      title: item.title || '',
      description: item.description || '',
      bannerImageUrl: item.bannerImageUrl || item.thumbnailUrl || '',
      categoryId: Array.isArray(item.categoryIds) ? item.categoryIds[0] || '' : '',
      productId: Array.isArray(item.productIds) ? item.productIds[0] || '' : '',
      sortOrder: Number(item.sortOrder || 0),
      status: item.status || 'PUBLISHED',
      isActive: item.isActive !== false,
      version: Number(item.version || 1),
    });
  }

  function bannerPayload() {
    return {
      title: bannerForm.title.trim(),
      description: bannerForm.description.trim(),
      contentType: 'BANNER',
      videoSource: 'UPLOAD',
      videoCategory: 'OTHER',
      status: bannerForm.status,
      videoUrl: null,
      thumbnailUrl: bannerForm.bannerImageUrl.trim() || null,
      bannerImageUrl: bannerForm.bannerImageUrl.trim() || null,
      contentBody: '',
      ctaLabel: null,
      ctaUrl: null,
      productIds: bannerForm.productId ? [bannerForm.productId] : [],
      categoryIds: bannerForm.categoryId ? [bannerForm.categoryId] : [],
      comments: [],
      sortOrder: Number(bannerForm.sortOrder || 0),
      scheduledAt: null,
      publishedAt: null,
      isActive: bannerForm.isActive,
      version: editingBannerId ? bannerForm.version : undefined,
    };
  }

  async function handleBannerSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (bannerSaving) return false;
    if (!bannerForm.title.trim()) {
      setBannerNotice({ type: 'error', text: 'Vui lòng nhập tiêu đề banner.' });
      return false;
    }
    if (!bannerForm.bannerImageUrl.trim()) {
      setBannerNotice({ type: 'error', text: 'Vui lòng tải hoặc nhập ảnh banner.' });
      return false;
    }
    if (!bannerForm.categoryId) {
      setBannerNotice({ type: 'error', text: 'Vui lòng chọn danh mục đi kèm cho banner.' });
      return false;
    }
    setBannerSaving(true);
    setBannerNotice(null);
    try {
      if (editingBannerId) {
        await adminContentApi.adminUpdateBanner(editingBannerId, bannerPayload());
        setBannerNotice({ type: 'success', text: 'Đã cập nhật banner.' });
      } else {
        await adminContentApi.adminCreateBanner(bannerPayload());
        setBannerNotice({ type: 'success', text: 'Đã thêm banner.' });
      }
      resetBannerForm();
      await reloadCurrentTab();
      return true;
    } catch (error) {
      setBannerSaving(false);
      setBannerNotice({ type: 'error', text: error instanceof Error ? error.message : 'Không thể lưu banner.' });
      return false;
    }
  }

  async function deleteBanner(item: any) {
    if (!window.confirm(`Xóa banner "${item.title}"?`)) return;
    await adminContentApi.adminDeleteBanner(item.id);
    await reloadCurrentTab();
  }

  return {
    bannerForm,
    setBannerForm,
    editingBannerId,
    bannerSaving,
    bannerNotice,
    setBannerNotice,
    filteredBanners,
    resetBannerForm,
    editBanner,
    handleBannerSubmit,
    deleteBanner,
  };
}
