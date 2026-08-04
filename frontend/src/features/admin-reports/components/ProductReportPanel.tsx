import { AdminPagination, AdminPanel, AdminTable, MetricCard } from '../../admin-shell/components/AdminDashboardParts';
import type { ProductReport } from '../types';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

export default function ProductReportPanel({
  report,
  onPageChange,
}: {
  report: ProductReport;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Sản phẩm/SKU" value={String(report.summary.totalProducts)} tone="sky" />
        <MetricCard label="Số lượng bán" value={String(report.summary.unitsSold)} tone="emerald" />
        <MetricCard label="Tiền hoàn" value={currency.format(Number(report.summary.refundAmount))} tone="amber" />
        <MetricCard label="Doanh thu ròng" value={currency.format(Number(report.summary.netRevenue))} />
      </div>
      <AdminPanel
        title="Hiệu quả sản phẩm"
        action={
          <AdminPagination
            currentPage={report.pagination.page}
            totalPages={report.pagination.totalPages}
            onPageChange={onPageChange}
          />
        }
      >
        <AdminTable headers={['SKU', 'Sản phẩm', 'Đã bán', 'Số đơn', 'Hoàn tiền', 'Doanh thu ròng']}>
          {report.items.length === 0 ? (
            <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Không có sản phẩm phù hợp.</td></tr>
          ) : report.items.map((item) => (
            <tr key={`${item.productId || 'used'}-${item.variantId || item.sku}`}>
              <td className="px-4 py-3 font-mono text-xs">{item.sku}</td>
              <td className="px-4 py-3 font-semibold">{item.productName}</td>
              <td className="px-4 py-3">{item.unitsSold}</td>
              <td className="px-4 py-3">{item.orderCount}</td>
              <td className="px-4 py-3">{currency.format(Number(item.refundAmount))}</td>
              <td className="px-4 py-3">{currency.format(Number(item.netRevenue))}</td>
            </tr>
          ))}
        </AdminTable>
      </AdminPanel>
    </div>
  );
}
