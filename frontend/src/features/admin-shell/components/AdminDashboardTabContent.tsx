import React, { Suspense } from 'react';
import { Boxes, Building2, ClipboardList, Package, ShieldCheck } from 'lucide-react';
import type { AdminTab } from './AdminDashboardConfig';
import {
  compactCurrency,
  currency,
  percent,
} from './AdminDashboardConfig';

const AdminAuditTab = React.lazy(() => import('../../admin-audit/components/AdminAuditTab'));
const AdminBannersTab = React.lazy(() => import('../../admin-content/components/AdminBannersTab'));
const AdminBrandsTab = React.lazy(() => import('../../admin-brands/components/AdminBrandsTab'));
const AdminCategoriesTab = React.lazy(() => import('../../admin-categories/components/AdminCategoriesTab'));
const AdminContentTab = React.lazy(() => import('../../admin-content/components/AdminContentTab'));
const AdminCustomersTab = React.lazy(() => import('../../admin-customers/components/AdminCustomersTab'));
const AdminFlashSalesTab = React.lazy(() => import('../../admin-flash-sales/components/AdminFlashSalesTab'));
const AdminInventoryReceiptsTab = React.lazy(() => import('../../admin-inventory/components/AdminInventoryReceiptsTab'));
const AdminAccountPayablesTab = React.lazy(() => import('../../admin-account-payables/components/AdminAccountPayablesTab'));
const AdminInventoryTab = React.lazy(() => import('../../admin-inventory/components/AdminInventoryTab'));
const AdminInventoryOutboundsTab = React.lazy(() => import('../../admin-inventory/components/AdminInventoryOutboundsTab'));
const AdminProductInteractionsTab = React.lazy(() => import('../../admin-interactions/components/AdminProductInteractionsTab'));
const AdminOrdersTab = React.lazy(() => import('../../admin-orders/components/AdminOrdersTab'));
const AdminOverviewTab = React.lazy(() => import('../../admin-overview/components/AdminOverviewTab'));
const AdminReportsTab = React.lazy(() => import('../../admin-reports/components/AdminReportsTab'));
const AdminPermissionsTab = React.lazy(() => import('../../admin-permissions/components/AdminPermissionsTab'));
const AdminProductsTab = React.lazy(() => import('../../admin-products/components/AdminProductsTab'));
const AdminUsedProductsTab = React.lazy(() => import('../../admin-used-products/components/AdminUsedProductsTab'));
const AdminReviewsTab = React.lazy(() => import('../../admin-reviews/components/AdminReviewsTab'));
const AdminServicesTab = React.lazy(() => import('../../admin-services/components/AdminServicesTab'));
const AdminSuppliersTab = React.lazy(() => import('../../admin-suppliers/components/AdminSuppliersTab'));
const AdminVouchersTab = React.lazy(() => import('../../admin-vouchers/components/AdminVouchersTab'));
const AdminAfterSalesTab = React.lazy(() => import('../../admin-after-sales/components/AdminAfterSalesTab'));
const AdminAiCatalogIndexTab = React.lazy(() => import('../../admin-ai-catalog/components/AdminAiCatalogIndexTab'));
const AdminPaymentMethodsTab = React.lazy(() => import('../../admin-payment-methods/components/AdminPaymentMethodsTab'));
const AdminStoreInfoTab = React.lazy(() => import('../../admin-store-info/components/AdminStoreInfoTab'));

type AdminDashboardTabContentProps = {
  admin: any;
  sharedProps: Record<string, any>;
};

function AdminTabFallback() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">
      Đang tải phân hệ quản trị...
    </div>
  );
}

export function buildOverviewStats(admin: any) {
  const stats = [
    {
      label: 'Doanh thu ròng',
      value: compactCurrency.format(admin.overview?.revenue || 0),
      caption: 'Đơn hoàn tất trừ tiền hoàn thực tế',
      icon: ClipboardList,
      tone: 'emerald',
    },
    ...(admin.usePermission?.('report:profit_read') ? [{
      label: 'Giá vốn hàng bán',
      value: compactCurrency.format(admin.overview?.costOfGoodsSold || 0),
      caption: 'Giá vốn lô đã xuất trừ hàng nhập trả',
      icon: Boxes,
      tone: 'amber',
    }, {
      label: 'Lợi nhuận gộp',
      value: compactCurrency.format(admin.overview?.grossProfit || 0),
      caption: 'Doanh thu ròng trừ giá vốn hàng bán',
      icon: ClipboardList,
      tone: 'emerald',
    }] : []),
    {
      label: 'Sản phẩm',
      value: admin.overview?.products?.total ?? admin.products.length,
      caption: 'Sản phẩm đang có trong catalog',
      icon: Package,
      tone: 'red',
    },
    {
      label: 'Đơn hàng',
      value: admin.orders.length || admin.overview?.orders?.total || 0,
      caption: 'Đơn hàng trong vùng dữ liệu hiện tại',
      icon: Boxes,
      tone: 'sky',
    },
    {
      label: 'Khách hàng',
      value: admin.customers.length || admin.overview?.customers?.total || 0,
      caption: 'Hồ sơ khách hàng đang quản lý',
      icon: Building2,
      tone: 'amber',
    },
  ];
  return stats;
}

export function buildRoleDashboards(admin: any) {
  return [
    { role: 'Quản trị', metric: `${admin.availableTabs.length} phân hệ`, helper: 'Các mục đang được cấp quyền truy cập', icon: ShieldCheck },
    { role: 'Kinh doanh', metric: `${admin.orders.length || admin.overview?.orders?.total || 0} đơn`, helper: 'Theo dõi xử lý và hậu mãi', icon: ClipboardList },
    { role: 'Danh mục hàng', metric: `${admin.overview?.products?.total ?? admin.products.length} sản phẩm`, helper: 'Quản lý sản phẩm, danh mục và thương hiệu', icon: Package },
  ];
}

function renderTab(tab: AdminTab, admin: any, sharedProps: Record<string, any>) {
  switch (tab) {
    case 'overview':
      return (
        <AdminOverviewTab
          stats={buildOverviewStats(admin)}
          overview={admin.overview}
          roleDashboards={buildRoleDashboards(admin)}
          currency={currency}
          compactCurrency={compactCurrency}
          percent={percent}
          setTab={admin.setTab}
        />
      );
    case 'reports':
      return <AdminReportsTab reportAccess={admin.reportAccess} />;
    case 'products':
      return <AdminProductsTab {...sharedProps} />;
    case 'usedProducts':
      return <AdminUsedProductsTab {...sharedProps} />;
    case 'flashSales':
      return <AdminFlashSalesTab {...sharedProps} />;
    case 'categories':
      return <AdminCategoriesTab {...sharedProps} />;
    case 'brands':
      return <AdminBrandsTab {...sharedProps} />;
    case 'suppliers':
      return <AdminSuppliersTab {...sharedProps} />;
    case 'services':
      return <AdminServicesTab {...sharedProps} />;
    case 'orders':
      return <AdminOrdersTab {...sharedProps} />;
    case 'afterSales':
      return <AdminAfterSalesTab query={admin.query} setTab={admin.setTab} setQuery={admin.setQuery} />;
    case 'vouchers':
      return <AdminVouchersTab {...sharedProps} />;
    case 'customers':
      return <AdminCustomersTab {...sharedProps} />;
    case 'inventoryReceipts':
      return <AdminInventoryReceiptsTab {...sharedProps} />;
    case 'accountPayables':
      return <AdminAccountPayablesTab {...sharedProps} />;
    case 'inventory':
      return <AdminInventoryTab {...sharedProps} />;
    case 'inventoryOutbounds':
      return <AdminInventoryOutboundsTab {...sharedProps} />;
    case 'reviews':
      return <AdminReviewsTab {...sharedProps} />;
    case 'interactions':
      return <AdminProductInteractionsTab {...sharedProps} />;
    case 'content':
      return <AdminContentTab {...sharedProps} />;
    case 'banners':
      return <AdminBannersTab {...sharedProps} />;
    case 'audit':
      return <AdminAuditTab {...sharedProps} />;
    case 'aiCatalogIndex':
      return <AdminAiCatalogIndexTab {...sharedProps} />;
    case 'permissions':
      return <AdminPermissionsTab {...sharedProps} />;
    case 'paymentMethods':
      return <AdminPaymentMethodsTab {...sharedProps} />;
    case 'storeInfo':
      return <AdminStoreInfoTab {...sharedProps} />;
    default:
      return (
        <AdminOverviewTab
          stats={buildOverviewStats(admin)}
          overview={admin.overview}
          roleDashboards={buildRoleDashboards(admin)}
          currency={currency}
          compactCurrency={compactCurrency}
          percent={percent}
        />
      );
  }
}

export default function AdminDashboardTabContent({ admin, sharedProps }: AdminDashboardTabContentProps) {
  return (
    <Suspense fallback={<AdminTabFallback />}>
      {renderTab(admin.tab, admin, sharedProps)}
    </Suspense>
  );
}
