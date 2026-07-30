import React, { Suspense } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { signOut } from '../../../services/authDb';
import { AdminEnterpriseShell } from '../components/AdminEnterpriseShell';
import AdminDashboardTabContent from '../components/AdminDashboardTabContent';
import { useAdminLogic } from '../hooks/useAdminLogic';
import { AdminNoticeHost } from '../parts/AdminNoticeHost';
import * as adminConfig from './AdminDashboardConfig';

const InventoryDialog = React.lazy(() => import('../modals/InventoryDialog'));
const ProductPreviewModal = React.lazy(() => import('../modals/ProductPreviewModal'));
const InfoViewModal = React.lazy(() => import('../modals/InfoViewModal'));
const CustomerDetailModal = React.lazy(() => import('../../admin-customers/components/CustomerDetailModal'));

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

  if (admin.availableTabs.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
          <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
          <h1 className="mt-4 text-lg font-bold text-slate-950">Chưa được cấp quyền chức năng</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Tài khoản nhân viên này có thể đăng nhập khu vực quản trị, nhưng hiện chưa được Super Admin cấp quyền sử dụng phân hệ nào.
          </p>
          <button
            type="button"
            onClick={handleSignOut}
            className="mt-5 rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800"
          >
            Đăng xuất
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <AdminNoticeHost />
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
      {admin.infoView && (
        <Suspense fallback={null}>
          <InfoViewModal infoView={admin.infoView} setInfoView={admin.setInfoView} />
        </Suspense>
      )}
      {admin.customerDetailOpen && (
        <Suspense fallback={null}>
          <CustomerDetailModal
            customer={admin.selectedCustomer}
            busy={admin.customerDetailBusy}
            error={admin.customerDetailError}
            activeSection={admin.customerActiveSection}
            orders={admin.customerOrders}
            loyaltyHistory={admin.customerLoyaltyHistory}
            loyaltyPage={admin.customerLoyaltyPage}
            loyaltyTotal={admin.customerLoyaltyTotal}
            onLoyaltyPageChange={(page) => void admin.loadCustomerLoyaltyPage(page)}
            notes={admin.customerNotes}
            auditLogs={admin.customerAuditLogs}
            profileDraft={admin.customerProfileDraft}
            pointDelta={admin.customerPointDelta}
            pointReason={admin.customerPointReason}
            canAdjustPoints={admin.canAdjustCustomerPoints}
            canUpdateProfile={admin.canUpdateCustomerProfile}
            onProfileDraftChange={admin.setCustomerProfileDraft}
            onSaveProfile={() => void admin.saveCustomerProfile()}
            onPointDeltaChange={admin.setCustomerPointDelta}
            onPointReasonChange={admin.setCustomerPointReason}
            onAdjustPoints={() => void admin.adjustCustomerPoints()}
            currency={adminConfig.currency}
            tagDraft={admin.customerTagDraft}
            onTagDraftChange={admin.setCustomerTagDraft}
            onSaveTags={() => void admin.saveCustomerTags()}
            noteDraft={admin.customerNoteDraft}
            onNoteDraftChange={admin.setCustomerNoteDraft}
            onAddNote={() => void admin.addCustomerNote()}
            voucherId={admin.customerVoucherId}
            voucherNote={admin.customerVoucherNote}
            onVoucherIdChange={admin.setCustomerVoucherId}
            onVoucherNoteChange={admin.setCustomerVoucherNote}
            onIssueVoucher={() => void admin.issueCustomerVoucher()}
            canIssueVoucher={admin.canIssueCustomerVoucher}
            onSectionChange={(section) => {
              if (section === 'summary') admin.setCustomerActiveSection('summary');
              else void admin.loadCustomerSection(section);
            }}
            onClose={() => {
              admin.setCustomerDetailOpen(false);
              admin.setSelectedCustomer(null);
              admin.setCustomerDetailError('');
            }}
          />
        </Suspense>
      )}
    </>
  );
}
