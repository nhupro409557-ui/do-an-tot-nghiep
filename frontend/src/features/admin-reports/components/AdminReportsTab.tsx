import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Boxes,
  ClipboardList,
  Download,
  Package,
  RefreshCw,
  Users,
} from 'lucide-react';
import { EmptyState } from '../../admin-shell/components/AdminDashboardParts';
import { adminInventoryApi } from '../../admin-inventory/services/adminInventoryApi';
import { useAdminReports } from '../hooks/useAdminReports';
import { adminReportsApi } from '../services/adminReportsApi';
import type { ReportFilters, ReportView } from '../types';
import OrderReportPanel from './OrderReportPanel';
import CustomerReportPanel from './CustomerReportPanel';
import InventoryReportPanel from './InventoryReportPanel';
import ProductReportPanel from './ProductReportPanel';
import ReportFiltersPanel from './ReportFilters';
import RevenueReportPanel from './RevenueReportPanel';

function dateInputValue(value: Date) {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
}

function initialFilters(): ReportFilters {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 29);
  const to = new Date(today);
  to.setDate(today.getDate() + 1);
  return {
    from: dateInputValue(from),
    to: dateInputValue(to),
    channel: '',
    paymentMethod: '',
    paymentStatus: '',
    fulfillmentMethod: '',
    status: '',
    dateBasis: 'createdAt',
    tier: '',
    segment: '',
    search: '',
  };
}

const views: Array<{ id: ReportView; label: string; icon: typeof BarChart3 }> = [
  { id: 'revenue', label: 'Doanh thu', icon: BarChart3 },
  { id: 'orders', label: 'Đơn hàng', icon: ClipboardList },
  { id: 'products', label: 'Sản phẩm', icon: Package },
  { id: 'customers', label: 'Khách hàng', icon: Users },
  { id: 'inventory', label: 'Tồn kho', icon: Boxes },
];

type ReportAccess = Record<ReportView, boolean>;

export default function AdminReportsTab({
  reportAccess,
}: {
  reportAccess: ReportAccess;
}) {
  const defaults = useMemo(initialFilters, []);
  const accessibleViews = useMemo(
    () => views.filter((view) => reportAccess[view.id]),
    [reportAccess],
  );
  const [activeView, setActiveView] = useState<ReportView>(
    () => accessibleViews[0]?.id || 'revenue',
  );
  const currentView = reportAccess[activeView]
    ? activeView
    : accessibleViews[0]?.id || 'revenue';
  const [draftFilters, setDraftFilters] = useState(defaults);
  const [filters, setFilters] = useState(defaults);
  const [page, setPage] = useState(1);
  const [inventoryAgingPage, setInventoryAgingPage] = useState(1);
  const [inventoryReconciliationPage, setInventoryReconciliationPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const {
    revenue,
    orders,
    products,
    customers,
    customerRetention,
    inventoryAging,
    inventoryReconciliation,
    loading,
    error,
  } = useAdminReports(
    currentView,
    filters,
    page,
    refreshKey,
    inventoryAgingPage,
    inventoryReconciliationPage,
  );

  useEffect(() => {
    if (currentView !== activeView) {
      setActiveView(currentView);
      setPage(1);
      setInventoryAgingPage(1);
      setInventoryReconciliationPage(1);
    }
  }, [activeView, currentView]);

  function changeView(view: ReportView) {
    setActiveView(view);
    setPage(1);
    setInventoryAgingPage(1);
    setInventoryReconciliationPage(1);
  }

  function applyFilters() {
    setFilters({ ...draftFilters });
    setPage(1);
    setInventoryAgingPage(1);
    setInventoryReconciliationPage(1);
  }

  async function exportCurrentReport() {
    setExporting(true);
    setExportError('');
    try {
      const blob = currentView === 'inventory'
        ? await adminInventoryApi.adminExportInventory(filters.search)
        : await adminReportsApi.exportReport(
          currentView as 'revenue' | 'orders' | 'customers',
          filters,
        );
      const filename = currentView === 'inventory'
        ? 'bao-cao-ton-kho.csv'
        : `bao-cao-${currentView}-${filters.from}-${filters.to}.csv`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setExportError(
        requestError instanceof Error
          ? requestError.message
          : 'Không thể xuất báo cáo.',
      );
    } finally {
      setExporting(false);
    }
  }

  const canExport = currentView !== 'products';

  const hasData =
    (currentView === 'revenue' && revenue)
    || (currentView === 'orders' && orders)
    || (currentView === 'products' && products)
    || (currentView === 'customers' && customers)
    || (currentView === 'inventory' && inventoryAging && inventoryReconciliation);

  return (
    <section aria-labelledby="admin-reports-title" className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id="admin-reports-title" className="text-xl font-bold text-slate-950">
            Báo cáo tổng hợp
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Phân tích theo kỳ; ngày kết thúc là biên loại trừ để không trùng số liệu.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canExport ? (
            <button
              type="button"
              onClick={() => void exportCurrentReport()}
              disabled={exporting || loading}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-bold text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              {exporting ? 'Đang xuất...' : 'Xuất CSV'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setRefreshKey((value) => value + 1)}
            disabled={loading}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 px-4 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className="h-4 w-4" /> Làm mới
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto" role="tablist" aria-label="Loại báo cáo">
        {accessibleViews.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={currentView === id}
            onClick={() => changeView(id)}
            className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-md px-4 text-sm font-bold ${
              currentView === id
                ? 'bg-rose-700 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      <ReportFiltersPanel
        activeView={currentView}
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={applyFilters}
        disabled={loading}
      />

      {exportError ? (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          {exportError}
        </div>
      ) : null}

      {loading && !hasData ? (
        <div className="space-y-3" aria-busy="true" aria-label="Đang tải báo cáo">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-20 animate-pulse rounded-lg bg-slate-100" />
          ))}
        </div>
      ) : error ? (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          {error}
        </div>
      ) : currentView === 'revenue' && revenue ? (
        <RevenueReportPanel report={revenue} />
      ) : currentView === 'orders' && orders ? (
        <OrderReportPanel report={orders} onPageChange={setPage} />
      ) : currentView === 'products' && products ? (
        <ProductReportPanel report={products} onPageChange={setPage} />
      ) : currentView === 'customers' && customers ? (
        <CustomerReportPanel
          report={customers}
          retention={customerRetention}
          onPageChange={setPage}
        />
      ) : currentView === 'inventory' && inventoryAging && inventoryReconciliation ? (
        <InventoryReportPanel
          aging={inventoryAging}
          reconciliation={inventoryReconciliation}
          onAgingPageChange={setInventoryAgingPage}
          onReconciliationPageChange={setInventoryReconciliationPage}
        />
      ) : (
        <EmptyState text="Không có dữ liệu trong kỳ đã chọn." />
      )}
    </section>
  );
}
