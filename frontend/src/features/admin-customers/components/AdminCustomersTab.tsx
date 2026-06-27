import { Eye } from 'lucide-react';
import { AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';

type AdminCustomersTabProps = Record<string, any>;

export default function AdminCustomersTab(props: AdminCustomersTabProps) {
  const {
    bulkApplyCustomerTags,
    bulkSuspendCustomers,
    canManageCustomerAccess,
    canManageCustomerProfile,
    currency,
    customerPage,
    customerTotal,
    filteredCustomers,
    openCustomerDetail,
    query,
    selectedCustomerIds,
    setCustomerPage,
    setQuery,
    setSelectedCustomerIds,
    updateUserAccess,
  } = props;
  const confirmBulkSuspend = () => {
    if (!window.confirm(`Xác nhận khóa ${selectedCustomerIds.length} khách hàng đã chọn?`)) return;
    void bulkSuspendCustomers();
  };

  return (
    <AdminPanel
      title={(canManageCustomerAccess || canManageCustomerProfile) ? 'Quản lý tài khoản khách hàng' : 'Tra cứu khách hàng'}
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm khách hàng, email, hạng" />}
    >
      {(canManageCustomerAccess || canManageCustomerProfile) && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button type="button" disabled={!selectedCustomerIds.length || !canManageCustomerAccess} onClick={confirmBulkSuspend} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800 disabled:cursor-not-allowed disabled:opacity-50">Khóa hàng loạt</button>
          <button type="button" disabled={!selectedCustomerIds.length || !canManageCustomerProfile} onClick={() => void bulkApplyCustomerTags()} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-800 disabled:cursor-not-allowed disabled:opacity-50">Gán tag hàng loạt</button>
          <span className="text-xs font-semibold text-slate-500">Đã chọn: {selectedCustomerIds.length} / Tổng: {customerTotal}</span>
        </div>
      )}
      <AdminTable
        headers={['Chọn', 'Khách hàng', 'Email', 'Hạng', 'Điểm', 'Số đơn', 'Đã chi tiêu', 'Trạng thái', 'Chi tiết']}
        currentPage={customerPage}
        totalPages={Math.max(1, Math.ceil(customerTotal / 20))}
        onPageChange={setCustomerPage}
        totalCount={customerTotal}
        itemName="khách hàng"
      >
        {filteredCustomers.length === 0 ? (
          <tr><td colSpan={9} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy khách hàng phù hợp.</td></tr>
        ) : filteredCustomers.map((item: any) => (
          <tr key={item.id}>
            <td className="px-4 py-3">
              <input type="checkbox" checked={selectedCustomerIds.includes(item.id)} onChange={(event) => setSelectedCustomerIds((prev: string[]) => event.target.checked ? [...new Set([...prev, item.id])] : prev.filter((id) => id !== item.id))} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" />
            </td>
            <td className="px-4 py-3 font-semibold text-slate-900">{item.fullName || item.email}</td>
            <td className="px-4 py-3">{item.email}</td>
            <td className="px-4 py-3">{item.tier}</td>
            <td className="px-4 py-3">{item.points ?? 0}</td>
            <td className="px-4 py-3">{item.orderCount || 0} đơn</td>
            <td className="px-4 py-3">{currency.format(Number(item.totalSpent || 0))}</td>
            <td className="px-4 py-3">
              {canManageCustomerAccess ? (
                <select value={item.status || 'ACTIVE'} onChange={(event) => updateUserAccess(item, { status: event.target.value })} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs font-semibold outline-none focus:border-red-500">
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="SUSPENDED">SUSPENDED</option>
                </select>
              ) : item.status}
            </td>
            <td className="px-4 py-3">
              <button type="button" onClick={() => openCustomerDetail(item)} className="inline-flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-800 transition hover:bg-sky-100">
                <Eye className="h-4 w-4" /> Xem hồ sơ
              </button>
            </td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
