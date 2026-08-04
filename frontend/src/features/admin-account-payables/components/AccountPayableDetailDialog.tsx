import { CreditCard } from 'lucide-react';
import { Input, Select } from '../../admin-shell/components/AdminDashboardParts';
import { currency } from '../../admin-shell/components/AdminDashboardConfig';

type AccountPayableDetailDialogProps = Record<string, any>;

const statusLabel: Record<string, string> = {
  OPEN: 'Chưa trả', PARTIAL: 'Trả một phần', OVERDUE: 'Quá hạn', PAID: 'Đã trả đủ', CANCELLED: 'Đã hủy',
};

const paymentMethodOptions: [string, string][] = [
  ['BANK_TRANSFER', 'Chuyển khoản'],
  ['CASH', 'Tiền mặt'],
  ['OTHER', 'Khác'],
];

const adjustmentTypeOptions: [string, string][] = [
  ['DEBIT', 'Tăng công nợ'],
  ['CREDIT', 'Giảm công nợ'],
];

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

export default function AccountPayableDetailDialog(props: AccountPayableDetailDialogProps) {
  const {
    selectedPayable, paymentForm, setPaymentForm, paymentSubmitting,
    adjustmentForm, setAdjustmentForm, adjustmentSubmitting,
    reversalSubmittingId,
    closePayableDetail, submitSupplierPayment, reverseSupplierPayment,
    submitAccountPayableAdjustment, canRecordSupplierPayment,
  } = props;
  if (!selectedPayable) return null;

  const payments = Array.isArray(selectedPayable.payments) ? selectedPayable.payments : [];
  const adjustments = Array.isArray(selectedPayable.adjustments) ? selectedPayable.adjustments : [];
  const canSubmitPayment = Boolean(canRecordSupplierPayment)
    && Number(selectedPayable.remainingAmount || 0) > 0
    && !['PAID', 'CANCELLED'].includes(String(selectedPayable.status || ''));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/40 p-4 sm:items-center">
      <div role="dialog" aria-modal="true" aria-labelledby="account-payable-dialog-title" className="max-h-[calc(100vh-2rem)] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 id="account-payable-dialog-title" className="text-lg font-bold text-slate-950">Chi tiết công nợ</h3>
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
          {payments.length ? (
            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Ngày</th><th className="px-3 py-2">Số tiền</th>
                    <th className="px-3 py-2">Phương thức</th><th className="px-3 py-2">Mã tham chiếu</th>
                    <th className="px-3 py-2">Trạng thái</th><th className="px-3 py-2">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {payments.map((payment: any) => (
                    <tr key={payment.id}>
                      <td className="px-3 py-2 text-slate-600">{formatDate(payment.paymentDate)}</td>
                      <td className="px-3 py-2 font-bold text-slate-900">{currency.format(Number(payment.amount || 0))}</td>
                      <td className="px-3 py-2 text-slate-600">{paymentMethodOptions.find(([value]) => value === payment.method)?.[1] || payment.method || '-'}</td>
                      <td className="px-3 py-2 text-slate-600">{payment.referenceNo || '-'}</td>
                      <td className="px-3 py-2 text-slate-600">
                        <div>{payment.status === 'REVERSED' ? 'Đã đảo' : 'Đã ghi sổ'}</div>
                        {payment.reversalReason && <div className="mt-1 text-xs text-red-600">{payment.reversalReason}</div>}
                      </td>
                      <td className="px-3 py-2">
                        {canRecordSupplierPayment && payment.status !== 'REVERSED' ? (
                          <button
                            type="button"
                            disabled={Boolean(reversalSubmittingId)}
                            className="text-xs font-bold text-red-600 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                            onClick={() => void reverseSupplierPayment(payment.id)}
                          >
                            {reversalSubmittingId === payment.id ? 'Đang đảo...' : 'Đảo thanh toán'}
                          </button>
                        ) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="rounded-md border border-dashed border-slate-200 px-4 py-3 text-sm font-semibold text-slate-500">Chưa có thanh toán nào được ghi nhận.</div>}
        </div>

        <div className="border-t border-slate-200 p-5">
          <div className="mb-3 text-sm font-bold text-slate-800">Lịch sử điều chỉnh</div>
          {adjustments.length ? (
            <div className="space-y-2">
              {adjustments.map((adjustment: any) => (
                <div key={adjustment.id} className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <div>
                    <div className="font-bold text-slate-800">{adjustment.type === 'DEBIT' ? 'Tăng công nợ' : 'Giảm công nợ'} · {adjustment.adjustmentCode}</div>
                    <div className="text-xs text-slate-500">{adjustment.reason} · {formatDate(adjustment.createdAt)}</div>
                  </div>
                  <div className={adjustment.type === 'DEBIT' ? 'shrink-0 font-bold text-red-600' : 'shrink-0 font-bold text-emerald-600'}>
                    {adjustment.type === 'DEBIT' ? '+' : '-'}{currency.format(Number(adjustment.amount || 0))}
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="rounded-md border border-dashed border-slate-200 px-4 py-3 text-sm font-semibold text-slate-500">Chưa có điều chỉnh công nợ.</div>}
        </div>

        {canSubmitPayment ? (
          <form className="border-t border-slate-200 p-5" onSubmit={submitSupplierPayment}>
            <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-800"><CreditCard className="h-4 w-4" />Ghi nhận thanh toán</div>
            <div className="grid gap-3 md:grid-cols-2">
              <Input label="Số tiền" type="number" min="0.01" value={paymentForm.amount} onChange={(value) => setPaymentForm({ ...paymentForm, amount: value })} />
              <Input label="Ngày thanh toán" type="date" value={paymentForm.paymentDate} onChange={(value) => setPaymentForm({ ...paymentForm, paymentDate: value })} />
              <Select label="Phương thức" value={paymentForm.method} options={paymentMethodOptions} onChange={(value) => setPaymentForm({ ...paymentForm, method: value })} />
              <Input label="Mã tham chiếu" value={paymentForm.referenceNo} onChange={(value) => setPaymentForm({ ...paymentForm, referenceNo: value })} />
              <div className="md:col-span-2"><Input label="Ghi chú" value={paymentForm.note} onChange={(value) => setPaymentForm({ ...paymentForm, note: value })} /></div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded-md border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700" onClick={closePayableDetail}>Hủy</button>
              <button type="submit" disabled={paymentSubmitting} className="rounded-md bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60">{paymentSubmitting ? 'Đang lưu...' : 'Lưu thanh toán'}</button>
            </div>
          </form>
        ) : (
          <div className="border-t border-slate-200 p-5"><div className="rounded-md bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">Tài khoản hiện tại chỉ được xem công nợ hoặc khoản này không còn số dư cần thanh toán.</div></div>
        )}

        {canRecordSupplierPayment && selectedPayable.status !== 'CANCELLED' && (
          <form className="border-t border-slate-200 p-5" onSubmit={submitAccountPayableAdjustment}>
            <div className="mb-3 text-sm font-bold text-slate-800">Điều chỉnh công nợ</div>
            <div className="grid gap-3 md:grid-cols-3">
              <Select label="Loại điều chỉnh" value={adjustmentForm.type} options={adjustmentTypeOptions} onChange={(value) => setAdjustmentForm({ ...adjustmentForm, type: value as 'DEBIT' | 'CREDIT' })} />
              <Input label="Số tiền" type="number" min="0.01" value={adjustmentForm.amount} onChange={(value) => setAdjustmentForm({ ...adjustmentForm, amount: value })} />
              <Input label="Lý do" value={adjustmentForm.reason} onChange={(value) => setAdjustmentForm({ ...adjustmentForm, reason: value })} />
            </div>
            <div className="mt-4 flex justify-end">
              <button type="submit" disabled={adjustmentSubmitting} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">{adjustmentSubmitting ? 'Đang lưu...' : 'Lưu điều chỉnh'}</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
