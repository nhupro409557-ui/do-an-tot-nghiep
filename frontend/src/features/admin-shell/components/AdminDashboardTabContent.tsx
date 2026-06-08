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
const AdminInventoryTab = React.lazy(() => import('../../admin-inventory/components/AdminInventoryTab'));
const AdminProductInteractionsTab = React.lazy(() => import('../../admin-interactions/components/AdminProductInteractionsTab'));
const AdminOrdersTab = React.lazy(() => import('../../admin-orders/components/AdminOrdersTab'));
const AdminOverviewTab = React.lazy(() => import('../../admin-overview/components/AdminOverviewTab'));
const AdminPermissionsTab = React.lazy(() => import('../../admin-permissions/components/AdminPermissionsTab'));
const AdminProductsTab = React.lazy(() => import('../../admin-products/components/AdminProductsTab'));
const AdminReviewsTab = React.lazy(() => import('../../admin-reviews/components/AdminReviewsTab'));
const AdminServicesTab = React.lazy(() => import('../../admin-services/components/AdminServicesTab'));
const AdminVouchersTab = React.lazy(() => import('../../admin-vouchers/components/AdminVouchersTab'));

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
  return [
    {
      label: 'Doanh thu',
      value: compactCurrency.format(admin.revenue || admin.overview?.revenue?.total || 0),
      caption: 'Tổng doanh thu từ đơn hàng đã tải',
      icon: ClipboardList,
      tone: 'emerald',
    },
    {
      label: 'Sản phẩm',
      value: admin.products.length,
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
}

export function buildRoleDashboards(admin: any) {
  return [
    { role: 'Quản trị', metric: `${admin.availableTabs.length} phân hệ`, helper: 'Các mục đang được cấp quyền truy cập', icon: ShieldCheck },
    { role: 'Kinh doanh', metric: `${admin.orders.length} đơn`, helper: 'Theo dõi xử lý và hậu mãi', icon: ClipboardList },
    { role: 'Catalog', metric: `${admin.products.length} sản phẩm`, helper: 'Quản lý sản phẩm, danh mục và thương hiệu', icon: Package },
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
    case 'products':
      return <AdminProductsTab {...sharedProps} />;
    case 'flashSales':
      return <AdminFlashSalesTab {...sharedProps} />;
    case 'categories':
      return <AdminCategoriesTab {...sharedProps} />;
    case 'brands':
      return <AdminBrandsTab {...sharedProps} />;
    case 'services':
      return <AdminServicesTab {...sharedProps} />;
    case 'orders':
      return <AdminOrdersTab {...sharedProps} />;
    case 'vouchers':
      return <AdminVouchersTab {...sharedProps} />;
    case 'customers':
      return <AdminCustomersTab {...sharedProps} />;
    case 'inventory':
      return <AdminInventoryTab {...sharedProps} />;
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
    case 'permissions':
      return <AdminPermissionsTab {...sharedProps} />;
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
