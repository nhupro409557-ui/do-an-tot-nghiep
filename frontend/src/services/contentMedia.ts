import { API_BASE_URL } from './apiClient';
import { formatProductDemoData } from './productMedia';
import { resolveMediaUrl } from './resolveMediaUrl';

export function formatVideoMediaDataForBase(video: any, apiBaseUrl: string): any {
  if (!video) return video;
  const resolve = (url: string | null | undefined) => resolveMediaUrl(url, apiBaseUrl);
  return {
    ...video,
    videoUrl: resolve(video.videoUrl),
    thumbnailUrl: resolve(video.thumbnailUrl),
    bannerImageUrl: resolve(video.bannerImageUrl),
    cover: resolve(video.cover),
    coverUrl: resolve(video.coverUrl),
    youtubeThumbnailUrl: resolve(video.youtubeThumbnailUrl),
    product: video.product ? formatProductDemoData(video.product) : video.product,
  };
}

export function formatVideoMediaData(video: any): any {
  return formatVideoMediaDataForBase(video, API_BASE_URL);
}
