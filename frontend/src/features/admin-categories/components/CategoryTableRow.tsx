import React from 'react';
import { Edit2, Eye, EyeOff, GripVertical, RotateCcw, Trash2 } from 'lucide-react';
import { AdminBadge } from '../../admin-shell/components/AdminDashboardParts';

const categoryStatusLabels: Record<string, string> = {
  ACTIVE: 'Hoạt động',
  INACTIVE: 'Tạm ẩn',
  DRAFT: 'Nháp',
  PENDING_REVIEW: 'Chờ duyệt',
  REJECTED: 'Bị từ chối',
  APPROVED: 'Đã duyệt',
};

const workflowStatusLabels: Record<string, string> = {
  PENDING: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Bị từ chối',
};

export function CategoryTableRow({
  category,
  level,
  onEdit,
  onView,
  onHide,
  onDelete,
  onRestore,
  onReorder,
}: {
  category: any;
  level: number;
  onEdit?: () => void;
  onView?: () => void;
  onHide?: () => void;
  onDelete?: () => void;
  onRestore?: () => void;
  onReorder?: (draggedId: string, targetId: string) => void;
}) {
  return (
    <tr
      draggable={Boolean(onReorder)}
      onDragStart={(event) => onReorder && event.dataTransfer.setData('categoryId', category.id)}
      onDragOver={(event) => onReorder && event.preventDefault()}
      onDrop={(event) =>
        onReorder?.(event.dataTransfer.getData('categoryId'), category.id)
      }
    >
      <td className="px-4 py-3 text-slate-400">
        {onReorder && <GripVertical className="h-4 w-4" />}
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
            {categoryStatusLabels[category.status || ''] || (category.isActive ? 'Hoạt động' : 'Tạm ẩn')}
          </AdminBadge>
          {category.workflowStatus && (
            <span className="text-xs font-semibold text-slate-500">
              Duyệt: {workflowStatusLabels[category.workflowStatus] || category.workflowStatus}
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
        <div className="flex items-center gap-2">
          {onView && (
            <button
              type="button"
              onClick={onView}
              title="Xem thông tin"
              className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            >
              <Eye className="h-4 w-4" />
            </button>
          )}
          {onEdit && <button
            type="button"
            onClick={onEdit}
            title="Sửa"
            className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
          >
            <Edit2 className="h-4 w-4" />
          </button>}
          {onHide && category.isActive ? (
            <button
              type="button"
              onClick={onHide}
              title="Ẩn"
              className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            >
              <EyeOff className="h-4 w-4" />
            </button>
          ) : (
            onRestore && (
              <button
                type="button"
                onClick={onRestore}
                title="Khôi phục"
                className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-emerald-200 bg-white text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-50"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )
          )}
          {onDelete && <button
            type="button"
            onClick={onDelete}
            title="Xóa"
            className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-red-200 bg-white text-red-600 transition hover:border-red-300 hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>}
        </div>
      </td>
    </tr>
  );
}
