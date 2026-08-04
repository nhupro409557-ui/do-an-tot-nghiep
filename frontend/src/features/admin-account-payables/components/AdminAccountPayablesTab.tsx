import { Eye, RefreshCw } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { currency } from '../../admin-shell/components/AdminDashboardConfig';
import AccountPayableDetailDialog from './AccountPayableDetailDialog';

type AdminAccountPayablesTabProps = Record<string, any>;
type BadgeTone = 'red' | 'green' | 'blue' | 'yellow' | 'slate' | 'amber';

const statusOptions: [string, string][] = [
  ['ALL', 'Tất cả trạng thái'],
  ['OPEN', 'Chưa trả'],
  ['PARTIAL', 'Trả một phần'],
  ['OVERDUE', 'Quá hạn'],
  ['PAID', 'Đã trả đủ'],
  ['CANCELLED', 'Đã hủy'],
];

const statusLabel: Record<string, string> = {
  OPEN: 'Chưa trả', PARTIAL: 'Trả một phần', OVERDUE: 'Quá hạn', PAID: 'Đã trả đủ', CANCELLED: 'Đã hủy',
};

const statusTone: Record<string, BadgeTone> = {
  OPEN: 'amber', PARTIAL: 'blue', OVERDUE: 'red', PAID: 'green', CANCELLED: 'slate',
};

function formatDate(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleDateString('vi-VN');
}

function metric(label: string, value: string, helper: string) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-bold text-slate-950">{value}</div>
      <div className="mt-1 text-xs font-semibold text-slate-500">{helper}</div>
    </div>
  );
}

export default function AdminAccountPayablesTab(props: AdminAccountPayablesTabProps) {
  const {
    query, setQuery, suppliers = [], accountPayables = [], accountPayableSummary = {},
    accountPayablePage = 1, accountPayableTotal = 0,
    accountPayableStatusFilter, setAccountPayableStatusFilter,
    accountPayableSupplierFilter, setAccountPayableSupplierFilter,
    accountPayableLoading, accountPayableLoadError,
    loadAccountPayables, openPayableDetail,
  } = props;

  const supplierOptions: [string, string][] = [
    ['', 'Tất cả nhà cung cấp'],
    ...suppliers.map((supplier: any) => [String(supplier.id), supplier.name] as [string, string]),
  ];

  return (
    <>
      <AdminPanel
        title="Công nợ nhà cung cấp"
        action={(
          <button
            type="button"
            disabled={accountPayableLoading}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            onClick={() => void loadAccountPayables(query, accountPayablePage)}
          >
            <RefreshCw className={`h-4 w-4 ${accountPayableLoading ? 'animate-spin' : ''}`} />
            {accountPayableLoading ? 'Đang tải...' : 'Làm mới'}
          </button>
        )}
      >
        <div className="grid gap-3 md:grid-cols-4">
          {metric('Tổng còn nợ', currency.format(Number(accountPayableSummary.totalRemaining || 0)), `${Number(accountPayableSummary.openCount || 0)} khoản đang mở`)}
          {metric('Quá hạn', currency.format(Number(accountPayableSummary.overdueAmount || 0)), `${Number(accountPayableSummary.overdueCount || 0)} khoản cần xử lý`)}
          {metric('Đến hạn 7 ngày', currency.format(Number(accountPayableSummary.dueSoonAmount || 0)), 'Ưu tiên kế hoạch thanh toán')}
          {metric('Dòng công nợ', String(accountPayableTotal || 0), 'Theo phiếu nhập đã hoàn tất')}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_240px] md:items-end">
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm phiếu nhập, hóa đơn hoặc nhà cung cấp" />
          <Select
            label="Trạng thái"
            value={accountPayableStatusFilter}
            options={statusOptions}
            onChange={(value) => {
              setAccountPayableStatusFilter(value);
              void loadAccountPayables(query, 1, { status: value });
            }}
          />
          <Select
            label="Nhà cung cấp"
            value={accountPayableSupplierFilter}
            options={supplierOptions}
            onChange={(value) => {
              setAccountPayableSupplierFilter(value);
              void loadAccountPayables(query, 1, { supplierId: value });
            }}
          />
        </div>

        {accountPayableLoadError && (
          <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            Không thể tải dữ liệu công nợ: {accountPayableLoadError} Dữ liệu đang hiển thị là lần tải thành công gần nhất.
          </div>
        )}

        <div className="mt-4">
          <AdminTable
            headers={['Phiếu nhập', 'Nhà cung cấp', 'Hóa đơn', 'Ngày đến hạn', 'Tổng nợ', 'Đã trả', 'Còn nợ', 'Trạng thái', 'Thao tác']}
            currentPage={accountPayablePage}
            totalPages={Math.max(1, Math.ceil(Number(accountPayableTotal || 0) / 50))}
            totalCount={accountPayableTotal}
            itemName="khoản công nợ"
            onPageChange={(page) => void loadAccountPayables(query, page)}
          >
            {accountPayables.map((item: any) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="px-4 py-3 text-sm font-bold text-slate-900">{item.sourceReferenceCode}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{item.supplierName || '-'}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{item.invoiceNumber || '-'}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{formatDate(item.dueDate)}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{currency.format(Number(item.principalAmount || 0))}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{currency.format(Number(item.paidAmount || 0))}</td>
                <td className="px-4 py-3 text-sm font-bold text-slate-900">{currency.format(Number(item.remainingAmount || 0))}</td>
                <td className="px-4 py-3"><AdminBadge tone={statusTone[item.status] || 'slate'}>{statusLabel[item.status] || item.status}</AdminBadge></td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                    onClick={() => void openPayableDetail(item)}
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Chi tiết
                  </button>
                </td>
              </tr>
            ))}
            {!accountPayables.length && (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Chưa có công nợ nhà cung cấp.</td></tr>
            )}
          </AdminTable>
        </div>
      </AdminPanel>

      <AccountPayableDetailDialog {...props} />
    </>
  );
}
