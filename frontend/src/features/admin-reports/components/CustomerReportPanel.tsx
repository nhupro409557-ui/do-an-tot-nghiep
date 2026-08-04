import {
  AdminPagination,
  AdminPanel,
  AdminTable,
  MetricCard,
} from '../../admin-shell/components/AdminDashboardParts';
import type { CustomerReport, CustomerRetentionReport } from '../types';
import CustomerRetentionMatrix from './CustomerRetentionMatrix';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

const segmentLabels: Record<string, string> = {
  FIRST_TIME: 'Mua lần đầu',
  RETURNING: 'Quay lại',
  NEW_NO_ORDER: 'Mới, chưa mua',
};

export default function CustomerReportPanel({
  report,
  retention,
  onPageChange,
}: {
  report: CustomerReport;
  retention: CustomerRetentionReport | null;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Khách mới" value={String(report.summary.newCustomers)} tone="sky" />
        <MetricCard label="Khách có mua" value={String(report.summary.activeCustomers)} tone="emerald" />
        <MetricCard label="Khách quay lại" value={String(report.summary.returningCustomers)} tone="amber" />
        <MetricCard label="Tỷ lệ mua lại" value={`${Number(report.summary.repeatPurchaseRate).toFixed(2)}%`} />
      </div>
      <AdminPanel title="Phân bổ theo hạng thành viên">
        <AdminTable headers={['Hạng', 'Số khách', 'Doanh thu ròng']}>
          {report.tiers.length === 0 ? (
            <tr>
              <td colSpan={3} className="px-4 py-8 text-center text-slate-500">
                Chưa có dữ liệu phân hạng trong kỳ.
              </td>
            </tr>
          ) : report.tiers.map((item) => (
            <tr key={item.tier}>
              <td className="px-4 py-3 font-semibold">{item.tier}</td>
              <td className="px-4 py-3">{item.customers}</td>
              <td className="px-4 py-3">{currency.format(Number(item.netRevenue))}</td>
            </tr>
          ))}
        </AdminTable>
      </AdminPanel>
      <CustomerRetentionMatrix report={retention} />
      <AdminPanel
        title="Khách hàng trong kỳ"
        action={
          <AdminPagination
            currentPage={report.pagination.page}
            totalPages={report.pagination.totalPages}
            onPageChange={onPageChange}
          />
        }
      >
        <AdminTable headers={['Khách hàng', 'Hạng', 'Phân nhóm', 'Số đơn', 'Chi tiêu ròng']}>
          {report.items.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                Không có khách hàng phù hợp.
              </td>
            </tr>
          ) : report.items.map((item) => (
            <tr key={item.id}>
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900">{item.fullName}</div>
                <div className="text-xs text-slate-500">{item.email}</div>
              </td>
              <td className="px-4 py-3">{item.tier}</td>
              <td className="px-4 py-3">{segmentLabels[item.segment] || item.segment}</td>
              <td className="px-4 py-3">{item.orderCount}</td>
              <td className="px-4 py-3">{currency.format(Number(item.netSpent))}</td>
            </tr>
          ))}
        </AdminTable>
      </AdminPanel>
    </div>
  );
}
