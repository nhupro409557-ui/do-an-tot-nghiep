import React from 'react';
import { AdminBadge, AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';
import { matchesSearch } from '../../admin-shell/pages/AdminDashboardConfig';

type AdminAuditTabProps = Record<string, any>;

export default function AdminAuditTab(props: AdminAuditTabProps) {
  const {
    auditLogs,
    query,
    setQuery,
  } = props;

  return (
    <AdminPanel 
      title="Nhật ký hoạt động Admin" 
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm event, resource, IP" />}
    >
      <AdminTable headers={['Thời gian', 'Sự kiện', 'Người thực hiện', 'IP', 'Tài nguyên', 'Kết quả']}>
        {auditLogs
          .filter((log: any) => matchesSearch({ ...log, resource: log.metadata?.resource, status: String(log.metadata?.status || '') }, query, ['eventType', 'userId', 'ipAddress', 'resource', 'status']))
          .map((log: any) => (
            <tr key={log.id}>
              <td className="px-4 py-3">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</td>
              <td className="px-4 py-3 font-semibold text-slate-900">{log.eventType}</td>
              <td className="px-4 py-3">{log.userId || log.email || '-'}</td>
              <td className="px-4 py-3">{log.ipAddress || '-'}</td>
              <td className="px-4 py-3">{log.metadata?.resource || log.metadata?.path || '-'}</td>
              <td className="px-4 py-3"><AdminBadge tone={Number(log.metadata?.status || 0) >= 400 ? 'red' : 'green'}>{log.metadata?.status || 'OK'}</AdminBadge></td>
            </tr>
          ))}
      </AdminTable>
    </AdminPanel>
  );
}
