import { CreditCard, Eye, RefreshCw } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, Input, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { currency } from '../../admin-shell/components/AdminDashboardConfig';

type AdminAccountPayablesTabProps = Record<string, any>;

const statusOptions: [string, string][] = [
  ['ALL', 'Tất cả trạng thái'],
  ['OPEN', 'Chưa trả'],
  ['PARTIAL', 'Trả một phần'],
  ['OVERDUE', 'Quá hạn'],
  ['PAID', 'Đã trả đủ'],
  ['CANCELLED', 'Đã hủy'],
];

const statusLabel: Record<string, string> = {
  OPEN: 'Chưa trả',
  PARTIAL: 'Trả một phần',
  OVERDUE: 'Quá hạn',
  PAID: 'Đã trả đủ',
  CANCELLED: 'Đã hủy',
};

type BadgeTone = 'red' | 'green' | 'blue' | 'yellow' | 'slate' | 'amber';

const statusTone: Record<string, BadgeTone> = {
  OPEN: 'amber',
  PARTIAL: 'blue',
  OVERDUE: 'red',
  PAID: 'green',
  CANCELLED: 'slate',
};

const paymentMethodOptions: [string, string][] = [
  ['BANK_TRANSFER', 'Chuyển khoản'],
  ['CASH', 'Tiền mặt'],
  ['OTHER', 'Khác'],
];

function formatDate(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('vi-VN');
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
    query,
    setQuery,
    suppliers = [],
    accountPayables = [],
    accountPayableSummary = {},
    accountPayablePage = 1,
    accountPayableTotal = 0,
    accountPayableStatusFilter,
    setAccountPayableStatusFilter,
    accountPayableSupplierFilter,
    setAccountPayableSupplierFilter,
    selectedPayable,
    paymentForm,
    setPaymentForm,
    loadAccountPayables,
    openPayableDetail,
    closePayableDetail,
    submitSupplierPayment,
    canRecordSupplierPayment,
  } = props;
  const selectedPayments = Array.isArray(selectedPayable?.payments) ? selectedPayable.payments : [];
  const canSubmitPayment = Boolean(canRecordSupplierPayment)
    && Number(selectedPayable?.remainingAmount || 0) > 0
    && !['PAID', 'CANCELLED'].includes(String(selectedPayable?.status || ''));

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
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
            onClick={() => void loadAccountPayables(query, accountPayablePage)}
          >
            <RefreshCw className="h-4 w-4" />
            Làm mới
          </button>
        )}
      >
        <div className="grid gap-3 md:grid-cols-4">
          {metric('Tổng còn nợ', currency.format(Number(accountPayableSummary.totalRemaining || 0)), `${Number(accountPayableSummary.openCount || 0)} khoản đang mở`)}
          {metric('Quá hạn', currency.format(Number(accountPayableSummary.overdueAmount || 0)), `${Number(accountPayableSummary.overdueCount || 0)} khoản cần xử lý`)}
          {metric('Đến hạn 7 ngày', currency.format(Number(accountPayableSummary.dueSoonAmount || 0)), 'Ưu tiên kế hoạch thanh toán')}
          {metric('Dòng công nợ', String(accountPayableTotal || 0), 'Theo phiếu nhập đã hoàn tất')}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_240px]">
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm phiếu nhập, hóa đơn hoặc nhà cung cấp" />
          <Select
            label="Trạng thái"
            value={accountPayableStatusFilter}
            options={statusOptions}
            onChange={(value) => {
              setAccountPayableStatusFilter(value);
              void loadAccountPayables(query, 1);
            }}
          />
          <Select
            label="Nhà cung cấp"
            value={accountPayableSupplierFilter}
            options={supplierOptions}
            onChange={(value) => {
              setAccountPayableSupplierFilter(value);
              void loadAccountPayables(query, 1);
            }}
          />
        </div>

        <div className="mt-4">
          <AdminTable headers={['Phiếu nhập', 'Nhà cung cấp', 'Hóa đơn', 'Ngày đến hạn', 'Tổng nợ', 'Đã trả', 'Còn nợ', 'Trạng thái', 'Thao tác']}>
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
              <tr>
                <td colSpan={9} className="px-4 py-6 text-center text-sm font-semibold text-slate-500">Chưa có công nợ nhà cung cấp.</td>
              </tr>
            )}
          </AdminTable>
        </div>
      </AdminPanel>

      {selectedPayable && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/40 p-4 sm:items-center">
          <div className="max-h-[calc(100vh-2rem)] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Chi tiết công nợ</h3>
                <p className="text-sm font-semibold text-slate-500">{selectedPayable.sourceReferenceCode} - {selectedPayable.supplierName || '-'}</p>
              </div>
              <button type="button" className="rounded-md px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-100" onClick={closePayableDetail}>Đóng</button>
            </div>
            <div className="grid gap-4 p-5 md:grid-cols-3">
              {metric('Tổng nợ', currency.format(Number(selectedPayable.principalAmount || 0)), `Hạn: ${formatDate(selectedPayable.dueDate)}`)}
              {metric('Đã trả', currency.format(Number(selectedPayable.paidAmount || 0)), selectedPayable.invoiceNumber ? `HĐ: ${selectedPayable.invoiceNumber}` : 'Chưa có số hóa đơn')}
              {metric('Còn nợ', currency.format(Number(selectedPayable.remainingAmount || 0)), statusLabel[selectedPayable.status] || selectedPayable.status)}
            </div>
            <div className="border-t border-slate-200 p-5">
              <div className="mb-3 text-sm font-bold text-slate-800">Lịch sử thanh toán</div>
              {selectedPayments.length ? (
                <div className="overflow-x-auto rounded-md border border-slate-200">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                      <tr>
                        <th className="px-3 py-2">Ngày</th>
                        <th className="px-3 py-2">Số tiền</th>
                        <th className="px-3 py-2">Phương thức</th>
                        <th className="px-3 py-2">Mã tham chiếu</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {selectedPayments.map((payment: any) => (
                        <tr key={payment.id}>
                          <td className="px-3 py-2 text-slate-600">{formatDate(payment.paymentDate)}</td>
                          <td className="px-3 py-2 font-bold text-slate-900">{currency.format(Number(payment.amount || 0))}</td>
                          <td className="px-3 py-2 text-slate-600">{paymentMethodOptions.find(([value]) => value === payment.method)?.[1] || payment.method || '-'}</td>
                          <td className="px-3 py-2 text-slate-600">{payment.referenceNo || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-slate-200 px-4 py-3 text-sm font-semibold text-slate-500">Chưa có thanh toán nào được ghi nhận.</div>
              )}
            </div>
            {canSubmitPayment ? (
              <form className="border-t border-slate-200 p-5" onSubmit={submitSupplierPayment}>
                <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-800">
                  <CreditCard className="h-4 w-4" />
                  Ghi nhận thanh toán
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input label="Số tiền" type="number" value={paymentForm.amount} onChange={(value) => setPaymentForm({ ...paymentForm, amount: Number(value || 0) })} />
                  <Input label="Ngày thanh toán" type="date" value={paymentForm.paymentDate} onChange={(value) => setPaymentForm({ ...paymentForm, paymentDate: value })} />
                  <Select label="Phương thức" value={paymentForm.method} options={paymentMethodOptions} onChange={(value) => setPaymentForm({ ...paymentForm, method: value })} />
                  <Input label="Mã tham chiếu" value={paymentForm.referenceNo} onChange={(value) => setPaymentForm({ ...paymentForm, referenceNo: value })} />
                  <div className="md:col-span-2">
                    <Input label="Ghi chú" value={paymentForm.note} onChange={(value) => setPaymentForm({ ...paymentForm, note: value })} />
                  </div>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="rounded-md border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700" onClick={closePayableDetail}>Hủy</button>
                  <button type="submit" className="rounded-md bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700">Lưu thanh toán</button>
                </div>
              </form>
            ) : (
              <div className="border-t border-slate-200 p-5">
                <div className="rounded-md bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
                  Tài khoản hiện tại chỉ được xem công nợ hoặc khoản này không còn số dư cần thanh toán.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
