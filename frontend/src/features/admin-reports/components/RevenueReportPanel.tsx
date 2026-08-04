import { AdminPanel, AdminTable, MetricCard } from '../../admin-shell/components/AdminDashboardParts';
import type { RevenueReport } from '../types';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export default function RevenueReportPanel({ report }: { report: RevenueReport }) {
  const summary = report.summary;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Doanh thu ròng" value={currency.format(Number(summary.netRevenue))} tone="emerald" />
        <MetricCard label="Doanh thu gộp" value={currency.format(Number(summary.grossRevenue))} tone="sky" />
        <MetricCard label="Tiền hoàn" value={currency.format(Number(summary.refundAmount))} tone="amber" />
        <MetricCard label="Đơn hoàn tất" value={String(summary.completedOrders)} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdminPanel title="Theo kênh bán">
          <AdminTable headers={['Kênh', 'Đơn hoàn tất', 'Doanh thu ròng']}>
            {report.breakdowns.channels.length === 0 ? (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-500">Không có dữ liệu kênh bán.</td></tr>
            ) : report.breakdowns.channels.map((item) => (
              <tr key={item.key}>
                <td className="px-4 py-3 font-semibold">{item.key}</td>
                <td className="px-4 py-3">{item.completedOrders}</td>
                <td className="px-4 py-3">{currency.format(Number(item.netRevenue))}</td>
              </tr>
            ))}
          </AdminTable>
        </AdminPanel>
        <AdminPanel title="Theo phương thức thanh toán">
          <AdminTable headers={['Phương thức', 'Đơn hoàn tất', 'Doanh thu ròng']}>
            {report.breakdowns.paymentMethods.length === 0 ? (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-500">Không có dữ liệu thanh toán.</td></tr>
            ) : report.breakdowns.paymentMethods.map((item) => (
              <tr key={item.key}>
                <td className="px-4 py-3 font-semibold">{item.key}</td>
                <td className="px-4 py-3">{item.completedOrders}</td>
                <td className="px-4 py-3">{currency.format(Number(item.netRevenue))}</td>
              </tr>
            ))}
          </AdminTable>
        </AdminPanel>
      </div>
    </div>
  );
}
