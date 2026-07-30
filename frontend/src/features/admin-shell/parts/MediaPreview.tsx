import React from 'react';
import { GripVertical, Star, X } from 'lucide-react';

export function MediaPreview({
  title,
  items,
  onRemove,
  onReorder,
  onSetPrimary,
  primaryItem,
}: {
  title: string;
  items: string[];
  onRemove?: (url: string) => void;
  onReorder?: (items: string[]) => void;
  onSetPrimary?: (url: string) => void;
  primaryItem?: string;
}) {
  if (items.length === 0) return null;

  const moveItem = (fromIndex: number, toIndex: number) => {
    if (!onReorder || fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
    const nextItems = [...items];
    const [movedItem] = nextItems.splice(fromIndex, 1);
    nextItems.splice(toIndex, 0, movedItem);
    onReorder(nextItems);
  };

  return (
    <div className="md:col-span-4">
      <div className="mb-2 text-xs font-bold text-slate-500">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <div
            key={`${item}-${index}`}
            draggable={Boolean(onReorder)}
            onDragStart={(event) => {
              event.dataTransfer.setData('text/plain', String(index));
              event.dataTransfer.effectAllowed = 'move';
            }}
            onDragOver={(event) => {
              if (!onReorder) return;
              event.preventDefault();
              event.dataTransfer.dropEffect = 'move';
            }}
            onDrop={(event) => {
              if (!onReorder) return;
              event.preventDefault();
              moveItem(Number(event.dataTransfer.getData('text/plain')), index);
            }}
            className={`relative h-16 w-16 rounded-md border bg-white p-1 shadow-sm ${
              primaryItem === item ? 'border-amber-300 ring-2 ring-amber-100' : 'border-slate-200'
            } ${onReorder ? 'cursor-grab active:cursor-grabbing' : ''}`}
          >
            <img src={item} alt="" className="h-full w-full object-contain" />
            {onReorder && (
              <span className="absolute bottom-1 left-1 rounded bg-white/90 p-0.5 text-slate-500 shadow-sm" title="Kéo để đổi thứ tự">
                <GripVertical className="h-3 w-3" />
              </span>
            )}
            {onSetPrimary && (
              <button
                type="button"
                onClick={() => onSetPrimary(item)}
                title={primaryItem === item ? 'Ảnh đại diện hiện tại' : 'Đặt làm ảnh đại diện'}
                className={`absolute -left-2 -top-2 rounded-full p-1 shadow-sm ${
                  primaryItem === item ? 'bg-amber-500 text-white' : 'bg-white text-slate-600 hover:bg-amber-50 hover:text-amber-600'
                }`}
              >
                <Star className={`h-3 w-3 ${primaryItem === item ? 'fill-current' : ''}`} />
              </button>
            )}
            {onRemove && (
              <button
                type="button"
                onClick={() => onRemove(item)}
                title="Xóa ảnh"
                className="absolute -right-2 -top-2 rounded-full bg-red-600 p-1 text-white shadow-sm"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
