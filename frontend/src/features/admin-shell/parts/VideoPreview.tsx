import React from 'react';
import { resolveImageUrl } from '../../../services/productMedia';

export function VideoPreview({
  title,
  url,
  onRemove,
}: {
  title: string;
  url: string;
  onRemove?: () => void;
}) {
  const mediaUrl = resolveImageUrl(url);
  const embedUrl = (() => {
    if (mediaUrl.includes('youtube.com/embed/')) return mediaUrl;
    if (mediaUrl.includes('youtu.be/'))
      return `https://www.youtube.com/embed/${mediaUrl.split('youtu.be/')[1].split(/[/?&]/)[0]}`;
    if (mediaUrl.includes('youtube.com/shorts/'))
      return `https://www.youtube.com/embed/${mediaUrl.split('youtube.com/shorts/')[1].split(/[/?&]/)[0]}`;
    if (mediaUrl.includes('youtube.com/watch') && mediaUrl.includes('v='))
      return `https://www.youtube.com/embed/${mediaUrl.split('v=')[1].split('&')[0]}`;
    return '';
  })();
  return (
    <div className="md:col-span-4">
      <div className="mb-2 text-xs font-bold text-slate-500">{title}</div>
      <div className="rounded-xl border border-slate-200 bg-slate-955 p-3 shadow-sm">
        {embedUrl ? (
          <iframe
            src={embedUrl}
            title={title}
            className="aspect-video w-full rounded-lg bg-black"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        ) : (
          <video src={mediaUrl} controls className="max-h-72 w-full rounded-lg bg-black" />
        )}
        {onRemove && (
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={onRemove}
              className="rounded-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700"
            >
              Xóa video đã chọn
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
