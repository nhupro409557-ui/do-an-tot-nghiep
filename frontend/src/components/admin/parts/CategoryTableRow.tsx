import React from 'react';
import { GripVertical } from 'lucide-react';
import { AdminBadge, RowActions } from './BaseUI';

export function CategoryTableRow({
  category,
  level,
  onEdit,
  onDelete,
  onRestore,
  onReorder,
}: {
  category: any;
  level: number;
  onEdit: () => void;
  onDelete: () => void;
  onRestore?: () => void;
  onReorder: (draggedId: string, targetId: string) => void;
}) {
  return (
    <tr
      draggable
      onDragStart={(event) => event.dataTransfer.setData('categoryId', category.id)}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) =>
        onReorder(event.dataTransfer.getData('categoryId'), category.id)
      }
    >
      <td className="px-4 py-3 text-slate-400">
        <GripVertical className="h-4 w-4" />
      </td>
      <td className="px-4 py-3">
        {category.iconUrl ? (
          <img
            src={category.iconUrl}
            alt=""
            className="h-10 w-10 rounded-md border border-slate-200 object-cover"
          />
        ) : (
          <span className="text-xs font-semibold text-slate-400">
            {category.icon || '-'}
          </span>
        )}
      </td>
      <td className="px-4 py-3 font-semibold text-slate-900">
        <div className="flex items-center gap-2" style={{ paddingLeft: level * 24 }}>
          {level > 0 && <span className="h-px w-4 bg-slate-300" />}
          <span>{category.name}</span>
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs">{category.slug}</td>
      <td className="px-4 py-3">{category.parentId ? 'Danh mục con' : 'Danh mục cha'}</td>
      <td className="px-4 py-3">{category.parentName || '-'}</td>
      <td className="px-4 py-3">
        {category.specFields?.length || 0} trường / {category.filterConfig?.length || 0}{' '}
        lọc
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col items-start gap-1">
          <AdminBadge
            tone={
              category.status === 'DRAFT' || category.status === 'PENDING_REVIEW'
                ? 'yellow'
                : category.isActive
                ? 'green'
                : category.status === 'REJECTED'
                ? 'red'
                : 'slate'
            }
          >
            {category.status || (category.isActive ? 'ACTIVE' : 'INACTIVE')}
          </AdminBadge>
          {category.workflowStatus && (
            <span className="text-xs font-semibold text-slate-500">
              Duyệt: {category.workflowStatus}
            </span>
          )}
          {category.hiddenByParent && (
            <span className="text-xs font-semibold text-amber-600">
              Ẩn theo danh mục cha
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <RowActions onEdit={onEdit} onDelete={onDelete} onRestore={onRestore} />
      </td>
    </tr>
  );
}
