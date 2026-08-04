import { AdminPagination, AdminPanel, AdminTable, MetricCard } from '../../admin-shell/components/AdminDashboardParts';
import type { OrderReport } from '../types';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export default function OrderReportPanel({
  report,
  onPageChange,
}: {
  report: OrderReport;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Tổng đơn" value={String(report.summary.totalOrders)} tone="sky" />
        <MetricCard label="Hoàn tất" value={String(report.summary.completedOrders)} tone="emerald" />
        <MetricCard label="Đã hủy" value={String(report.summary.cancelledOrders)} tone="amber" />
        <MetricCard label="Tổng giá trị" value={currency.format(Number(report.summary.totalAmount))} />
      </div>
      <AdminPanel
        title="Chi tiết đơn hàng"
        action={
          <AdminPagination
            currentPage={report.pagination.page}
            totalPages={report.pagination.totalPages}
            onPageChange={onPageChange}
          />
        }
      >
        <AdminTable headers={['Mã đơn', 'Khách hàng', 'Trạng thái', 'Kênh', 'Thanh toán', 'Giá trị']}>
          {report.items.length === 0 ? (
            <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Không có đơn hàng phù hợp.</td></tr>
          ) : report.items.map((item) => (
            <tr key={item.id}>
              <td className="px-4 py-3 font-semibold">{item.orderCode}</td>
              <td className="px-4 py-3">{item.customerName || 'Khách lẻ'}</td>
              <td className="px-4 py-3">{item.status}</td>
              <td className="px-4 py-3">{item.channel}</td>
              <td className="px-4 py-3">{item.paymentMethod}</td>
              <td className="px-4 py-3">{currency.format(Number(item.totalAmount))}</td>
            </tr>
          ))}
        </AdminTable>
      </AdminPanel>
    </div>
  );
}
