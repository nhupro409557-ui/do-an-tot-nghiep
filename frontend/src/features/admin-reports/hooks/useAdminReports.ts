import { useEffect, useState } from 'react';
import { adminInventoryApi } from '../../admin-inventory/services/adminInventoryApi';
import { adminReportsApi } from '../services/adminReportsApi';
import type {
  CustomerReport,
  CustomerRetentionReport,
  InventoryAgingReport,
  InventoryReconciliationReport,
  OrderReport,
  ProductReport,
  ReportFilters,
  ReportView,
  RevenueReport,
} from '../types';

export function useAdminReports(
  activeView: ReportView,
  filters: ReportFilters,
  page: number,
  refreshKey: number,
  inventoryAgingPage: number,
  inventoryReconciliationPage: number,
) {
  const [revenue, setRevenue] = useState<RevenueReport | null>(null);
  const [orders, setOrders] = useState<OrderReport | null>(null);
  const [products, setProducts] = useState<ProductReport | null>(null);
  const [customers, setCustomers] = useState<CustomerReport | null>(null);
  const [customerRetention, setCustomerRetention] =
    useState<CustomerRetentionReport | null>(null);
  const [inventoryAging, setInventoryAging] = useState<InventoryAgingReport | null>(null);
  const [inventoryReconciliation, setInventoryReconciliation] =
    useState<InventoryReconciliationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');

    const load = async () => {
      if (activeView === 'revenue') {
        setRevenue(await adminReportsApi.getRevenue(filters, controller.signal));
      } else if (activeView === 'orders') {
        setOrders(await adminReportsApi.getOrders(filters, page, controller.signal));
      } else if (activeView === 'products') {
        setProducts(await adminReportsApi.getProducts(filters, page, controller.signal));
      } else if (activeView === 'customers') {
        const [customerReport, retentionReport] = await Promise.all([
          adminReportsApi.getCustomers(filters, page, controller.signal),
          adminReportsApi.getCustomerRetention(controller.signal),
        ]);
        setCustomers(customerReport);
        setCustomerRetention(retentionReport);
      } else {
        const [aging, reconciliation] = await Promise.all([
          adminInventoryApi.adminGetInventoryAgingReport(
            filters.search,
            '',
            inventoryAgingPage,
            50,
          ),
          adminInventoryApi.adminGetInventoryReconciliationReport(
            filters.search,
            '',
            inventoryReconciliationPage,
            50,
          ),
        ]);
        if (controller.signal.aborted) return;
        setInventoryAging(aging);
        setInventoryReconciliation(reconciliation);
      }
    };

    void load()
      .catch((requestError) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') return;
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Không thể tải báo cáo.',
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [
    activeView,
    filters,
    inventoryAgingPage,
    inventoryReconciliationPage,
    page,
    refreshKey,
  ]);

  return {
    revenue,
    orders,
    products,
    customers,
    customerRetention,
    inventoryAging,
    inventoryReconciliation,
    loading,
    error,
  };
}
