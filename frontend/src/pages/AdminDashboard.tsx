
import React, { Suspense } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { signOut } from '../services/authDb';
import { AdminEnterpriseShell } from '../components/admin/AdminEnterpriseShell';
import AdminDashboardTabContent from '../components/admin/AdminDashboardTabContent';
import { useAdminLogic } from '../components/admin/hooks/useAdminLogic';
import * as adminConfig from './AdminDashboardConfig';

const InventoryDialog = React.lazy(() => import('../components/admin/modals/InventoryDialog'));
const ProductPreviewModal = React.lazy(() => import('../components/admin/modals/ProductPreviewModal'));

export default function AdminDashboard() {
  const navigate = useNavigate();
  const admin = useAdminLogic();
  const activeTone = adminConfig.tabTone[admin.tab] || adminConfig.tabTone.overview;
  const activeTab = admin.availableTabs.find((item: any) => item.id === admin.tab);
  const sharedProps = { ...adminConfig, ...admin };

  async function handleSignOut() {
    await signOut();
    navigate('/admin/login');
  }

  if (admin.loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm font-semibold text-slate-600">Đang tải khu quản trị...</div>;
  }

  if (!admin.canAccessAdmin) {
    return <Navigate to="/admin/login" replace />;
  }

  return (
    <>
      <AdminEnterpriseShell
        tabs={admin.availableTabs.map((item: any) => ({
          id: item.id,
          label: item.label,
          group: item.group,
          icon: React.createElement(item.icon, { className: 'h-4 w-4' }),
        }))}
        activeTab={admin.tab}
        onTabChange={(tabId) => admin.setTab(tabId as adminConfig.AdminTab)}
        collapsed={!admin.sidebarOpen}
        onToggleCollapsed={() => admin.setSidebarOpen(!admin.sidebarOpen)}
        title={activeTone.title}
        description={activeTone.description}
        sectionLabel={activeTab?.group || activeTone.label}
        sectionIcon={activeTab?.icon ? React.createElement(activeTab.icon, { className: 'h-5 w-5' }) : <ShieldCheck className="h-5 w-5" />}
        query={admin.query}
        onQueryChange={admin.setQuery}
        searchPlaceholder={adminConfig.searchPlaceholderByTab[admin.tab] || 'Tìm kiếm'}
        onRefresh={() => void admin.loadData(admin.tab, { force: true })}
        onSignOut={handleSignOut}
        busy={admin.busy}
      >
        <AdminDashboardTabContent admin={admin} sharedProps={sharedProps} />
      </AdminEnterpriseShell>
      {admin.inventoryDraft && (
        <Suspense fallback={null}>
          <InventoryDialog {...sharedProps} />
        </Suspense>
      )}
      {admin.previewProduct && (
        <Suspense fallback={null}>
          <ProductPreviewModal {...sharedProps} />
        </Suspense>
      )}
    </>
  );
}
