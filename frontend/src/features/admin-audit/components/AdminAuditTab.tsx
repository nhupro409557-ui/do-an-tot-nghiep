import React from 'react';
import { AdminBadge, AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';
import { matchesSearch } from '../../admin-shell/pages/AdminDashboardConfig';
import { adminActorLabel } from '../utils/adminActorLabel';

type AdminAuditTabProps = Record<string, any>;

export default function AdminAuditTab(props: AdminAuditTabProps) {
  const {
    auditLogs,
    query,
    setQuery,
  } = props;

  const actionLabel = (log: any) => {
    const method = String(log.metadata?.method || '').toUpperCase();
    const labels: Record<string, string> = { POST: 'Tạo mới/Thực hiện', PUT: 'Cập nhật', PATCH: 'Thay đổi trạng thái/Dữ liệu', DELETE: 'Xóa/Ngừng sử dụng' };
    return labels[method] || log.eventType;
  };
  const resourceLabel = (log: any) => {
    const resource = String(log.metadata?.resource || '').toLowerCase();
    const labels: Record<string, string> = {
      products: 'Sản phẩm', categories: 'Danh mục', brands: 'Thương hiệu', inventory: 'Tồn kho',
      'used-products': 'Hàng cũ', orders: 'Đơn hàng', 'purchase-orders': 'Đơn mua hàng',
      'after-sales': 'Hậu mãi', vouchers: 'Voucher', customers: 'Khách hàng', users: 'Người dùng',
      roles: 'Vai trò và phân quyền', content: 'Nội dung', banners: 'Banner', services: 'Dịch vụ',
    };
    return labels[resource] || resource || 'Quản trị hệ thống';
  };
  const resultLabel = (status: number) => {
    if (!status) return 'Thành công';
    if (status < 300) return 'Thành công';
    if (status < 400) return 'Đã chuyển hướng';
    if (status === 403) return 'Bị từ chối quyền';
    if (status === 404) return 'Không tìm thấy';
    if (status === 409) return 'Xung đột dữ liệu';
    if (status < 500) return 'Dữ liệu không hợp lệ';
    return 'Lỗi hệ thống';
  };

  return (
    <AdminPanel 
      title="Nhật ký hoạt động Admin" 
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm event, resource, IP" />}
    >
      <AdminTable headers={['Thời gian', 'Sự kiện', 'Người thực hiện', 'IP', 'Tài nguyên', 'Kết quả']}>
        {auditLogs
          .filter((log: any) => matchesSearch({ ...log, resource: log.metadata?.resource, status: String(log.metadata?.status || '') }, query, ['eventType', 'userId', 'actorName', 'email', 'actorRole', 'ipAddress', 'resource', 'status']))
          .map((log: any) => {
            const actor = adminActorLabel(log);
            return (
            <tr key={log.id}>
              <td className="px-4 py-3">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</td>
              <td className="px-4 py-3"><div className="font-semibold text-slate-900">{actionLabel(log)}</div><div className="mt-1 text-xs text-slate-500">{log.eventType}</div></td>
              <td className="px-4 py-3"><div className="font-semibold text-slate-900">{actor.name}</div><div className="mt-1 text-xs text-slate-500">{[actor.role, actor.email].filter(Boolean).join(' · ') || (actor.isSystem ? 'Tự động' : log.userId || '-')}</div></td>
              <td className="px-4 py-3">{log.ipAddress || '-'}</td>
              <td className="px-4 py-3"><div className="font-semibold text-slate-900">{resourceLabel(log)}</div><div className="mt-1 text-xs text-slate-500">{log.metadata?.resource_id ? `Mã: ${log.metadata.resource_id}` : log.metadata?.path || '-'}</div></td>
              <td className="px-4 py-3"><AdminBadge tone={Number(log.metadata?.status || 0) >= 400 ? 'red' : 'green'}>{resultLabel(Number(log.metadata?.status || 0))}</AdminBadge><div className="mt-1 text-xs text-slate-500">HTTP {log.metadata?.status || 200}</div></td>
            </tr>
          );})}
      </AdminTable>
    </AdminPanel>
  );
}
