import type {
  InventoryAgingReport,
  InventoryReconciliationReport,
} from '../types';
import { AdminPagination } from '../../admin-shell/components/AdminDashboardParts';

const currency = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

type Props = {
  aging: InventoryAgingReport;
  reconciliation: InventoryReconciliationReport;
  onAgingPageChange: (page: number) => void;
  onReconciliationPageChange: (page: number) => void;
};

export default function InventoryReportPanel({
  aging,
  reconciliation,
  onAgingPageChange,
  onReconciliationPageChange,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Dữ liệu tồn kho là ảnh chụp tại thời điểm{' '}
        <strong>{new Date(aging.asOf).toLocaleString('vi-VN')}</strong>, không áp dụng khoảng ngày.
      </div>

      <section aria-labelledby="inventory-aging-title" className="space-y-3">
        <div>
          <h3 id="inventory-aging-title" className="text-lg font-bold text-slate-950">
            Tuổi tồn kho
          </h3>
          <p className="text-sm text-slate-600">
            Tổng {aging.totalQuantity.toLocaleString('vi-VN')} sản phẩm, trị giá{' '}
            {currency.format(aging.totalCost)} trên {aging.pagination.total.toLocaleString('vi-VN')} dòng.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {aging.buckets.map((bucket) => (
            <article key={bucket.bucket} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase text-slate-500">{bucket.label}</p>
              <p className="mt-2 text-2xl font-black text-slate-950">
                {bucket.quantity.toLocaleString('vi-VN')}
              </p>
              <p className="mt-1 text-xs font-semibold text-slate-600">
                {bucket.skuCount} dòng · {currency.format(bucket.totalCost)}
              </p>
            </article>
          ))}
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
              <tr>
                <th className="px-4 py-3">Nhóm tuổi</th>
                <th className="px-4 py-3">Sản phẩm</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Kệ</th>
                <th className="px-4 py-3 text-right">Tuổi cao nhất</th>
                <th className="px-4 py-3 text-right">Số lượng</th>
                <th className="px-4 py-3 text-right">Giá trị vốn</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {aging.items.map((item) => (
                <tr key={`${item.bucket}-${item.productId}-${item.variantId || 'base'}-${item.locationCode || 'none'}`}>
                  <td className="px-4 py-3 font-semibold text-slate-700">{item.bucketLabel}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">{item.productName}</td>
                  <td className="px-4 py-3 font-mono text-xs">{item.variantSku || item.productSku || '-'}</td>
                  <td className="px-4 py-3">{item.locationCode || '-'}</td>
                  <td className="px-4 py-3 text-right font-semibold">{item.maxAgeDays} ngày</td>
                  <td className="px-4 py-3 text-right">{item.quantity.toLocaleString('vi-VN')}</td>
                  <td className="px-4 py-3 text-right">{currency.format(item.totalCost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <AdminPagination
          currentPage={aging.pagination.page}
          totalPages={aging.pagination.totalPages}
          onPageChange={onAgingPageChange}
        />
      </section>

      <section aria-labelledby="inventory-reconciliation-title" className="space-y-3">
        <div>
          <h3 id="inventory-reconciliation-title" className="text-lg font-bold text-slate-950">
            Đối soát tồn kho
          </h3>
          <p className="text-sm text-slate-600">
            Phát hiện {reconciliation.totalIssues.toLocaleString('vi-VN')} sai lệch cần kiểm tra.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {reconciliation.summary.map((item) => (
            <article key={item.issueType} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase text-slate-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-black ${item.count ? 'text-rose-700' : 'text-emerald-700'}`}>
                {item.count.toLocaleString('vi-VN')}
              </p>
            </article>
          ))}
        </div>
        {reconciliation.items.length ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
                <tr>
                  <th className="px-4 py-3">Loại sai lệch</th>
                  <th className="px-4 py-3">Sản phẩm</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Kệ</th>
                  <th className="px-4 py-3">Ghi chú</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reconciliation.items.map((item, index) => (
                  <tr key={`${item.issueType}-${item.productId || index}-${item.locationCode || 'none'}`}>
                    <td className="px-4 py-3 font-semibold text-rose-700">
                      {reconciliation.summary.find((entry) => entry.issueType === item.issueType)?.label
                        || item.issueType}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-950">{item.productName || '-'}</td>
                    <td className="px-4 py-3 font-mono text-xs">{item.variantSku || item.productSku || '-'}</td>
                    <td className="px-4 py-3">{item.locationCode || '-'}</td>
                    <td className="px-4 py-3 text-slate-600">{item.message || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">
            Chưa phát hiện sai lệch tồn kho theo bộ lọc hiện tại.
          </div>
        )}
        <AdminPagination
          currentPage={reconciliation.pagination.page}
          totalPages={reconciliation.pagination.totalPages}
          onPageChange={onReconciliationPageChange}
        />
      </section>
    </div>
  );
}
