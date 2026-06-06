import React from 'react';
import { X } from 'lucide-react';

export function MediaPreview({
  title,
  items,
  onRemove,
}: {
  title: string;
  items: string[];
  onRemove: (url: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="md:col-span-4">
      <div className="mb-2 text-xs font-bold text-slate-500">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <div
            key={item}
            className="relative h-16 w-16 rounded-md border border-slate-200 bg-white p-1 shadow-sm"
          >
            <img src={item} alt="" className="h-full w-full object-contain" />
            <button
              type="button"
              onClick={() => onRemove(item)}
              title="Xóa ảnh"
              className="absolute -right-2 -top-2 rounded-full bg-red-600 p-1 text-white shadow-sm"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
