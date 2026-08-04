import { useRef, useState, type FormEvent } from 'react';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { adminAccountPayablesApi } from '../services/adminAccountPayablesApi';

const ACCOUNT_PAYABLE_PAGE_SIZE = 50;

const initialPaymentForm = {
  amount: '',
  paymentDate: new Date().toISOString().slice(0, 10),
  method: 'BANK_TRANSFER',
  referenceNo: '',
  note: '',
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Hệ thống chưa thể xử lý yêu cầu.';
}

type UseAdminAccountPayablesLogicParams = {
  query: string;
  reloadCurrentTab: () => Promise<void>;
};

export function useAdminAccountPayablesLogic({ query, reloadCurrentTab }: UseAdminAccountPayablesLogicParams) {
  const [accountPayables, setAccountPayables] = useState<any[]>([]);
  const [accountPayableSummary, setAccountPayableSummary] = useState<any>({});
  const [accountPayablePage, setAccountPayablePage] = useState(1);
  const [accountPayableTotal, setAccountPayableTotal] = useState(0);
  const [accountPayableStatusFilter, setAccountPayableStatusFilter] = useState('ALL');
  const [accountPayableSupplierFilter, setAccountPayableSupplierFilter] = useState('');
  const [accountPayableLoading, setAccountPayableLoading] = useState(false);
  const [accountPayableLoadError, setAccountPayableLoadError] = useState('');
  const accountPayableRequestSequence = useRef(0);
  const [selectedPayable, setSelectedPayable] = useState<any | null>(null);
  const [paymentForm, setPaymentForm] = useState(initialPaymentForm);
  const [paymentRequestKey, setPaymentRequestKey] = useState(() => crypto.randomUUID());
  const [paymentSubmitting, setPaymentSubmitting] = useState(false);
  const [adjustmentForm, setAdjustmentForm] = useState({ type: 'DEBIT' as 'DEBIT' | 'CREDIT', amount: '', reason: '' });
  const [adjustmentSubmitting, setAdjustmentSubmitting] = useState(false);
  const [reversalSubmittingId, setReversalSubmittingId] = useState('');

  async function loadAccountPayables(
    search = query,
    page = 1,
    filters?: { status?: string; supplierId?: string },
  ) {
    const requestSequence = ++accountPayableRequestSequence.current;
    setAccountPayableLoading(true);
    setAccountPayableLoadError('');
    try {
      const [result, summary] = await Promise.all([
        adminAccountPayablesApi.adminListAccountPayables({
          search: search.trim(),
          status: filters?.status ?? accountPayableStatusFilter,
          supplierId: filters?.supplierId ?? accountPayableSupplierFilter,
          page,
          pageSize: ACCOUNT_PAYABLE_PAGE_SIZE,
        }),
        adminAccountPayablesApi.adminGetAccountPayableSummary(),
      ]);
      if (requestSequence !== accountPayableRequestSequence.current) return;
      setAccountPayables(Array.isArray(result.items) ? result.items : []);
      setAccountPayablePage(Number(result.page || page));
      setAccountPayableTotal(Number(result.total || 0));
      setAccountPayableSummary(summary || {});
    } catch (error) {
      if (requestSequence !== accountPayableRequestSequence.current) return;
      setAccountPayableLoadError(errorMessage(error));
    } finally {
      if (requestSequence === accountPayableRequestSequence.current) {
        setAccountPayableLoading(false);
      }
    }
  }

  async function openPayableDetail(payable: any) {
    try {
      const detail = await adminAccountPayablesApi.adminGetAccountPayableDetail(payable.id);
      setSelectedPayable(detail);
      setPaymentForm({
        ...initialPaymentForm,
        amount: String(detail.remainingAmount || ''),
      });
      setPaymentRequestKey(crypto.randomUUID());
    } catch (error) {
      notifyAdmin(errorMessage(error), 'error', 'Không thể tải chi tiết công nợ');
    }
  }

  function closePayableDetail() {
    setSelectedPayable(null);
    setPaymentForm(initialPaymentForm);
  }

  async function submitSupplierPayment(event: FormEvent) {
    event.preventDefault();
    if (!selectedPayable || paymentSubmitting) return;
    const amount = Number(paymentForm.amount || 0);
    if (!Number.isFinite(amount) || amount <= 0) {
      window.alert('Số tiền thanh toán phải lớn hơn 0.');
      return;
    }
    setPaymentSubmitting(true);
    try {
      await adminAccountPayablesApi.adminCreateSupplierPayment(selectedPayable.id, {
        amount: paymentForm.amount,
        paymentDate: paymentForm.paymentDate ? new Date(paymentForm.paymentDate).toISOString() : null,
        method: paymentForm.method,
        referenceNo: paymentForm.referenceNo.trim() || null,
        note: paymentForm.note.trim() || null,
      }, paymentRequestKey);
      notifyAdmin('Đã ghi nhận thanh toán công nợ nhà cung cấp.');
      setPaymentRequestKey(crypto.randomUUID());
      closePayableDetail();
    } catch (error) {
      notifyAdmin(errorMessage(error), 'error', 'Không thể ghi nhận thanh toán');
      return;
    } finally {
      setPaymentSubmitting(false);
    }
    await loadAccountPayables(query, accountPayablePage);
    await reloadCurrentTab().catch((error) => {
      notifyAdmin(errorMessage(error), 'error', 'Đã thanh toán nhưng chưa làm mới được dữ liệu liên quan');
    });
  }

  async function reverseSupplierPayment(paymentId: string) {
    if (!selectedPayable || reversalSubmittingId) return;
    const reason = window.prompt('Nhập lý do đảo thanh toán:')?.trim() || '';
    if (reason.length < 3) return;
    setReversalSubmittingId(paymentId);
    try {
      await adminAccountPayablesApi.adminReverseSupplierPayment(selectedPayable.id, paymentId, reason);
      notifyAdmin('Đã đảo thanh toán và tính lại số dư công nợ.');
    } catch (error) {
      notifyAdmin(errorMessage(error), 'error', 'Không thể đảo thanh toán');
      return;
    } finally {
      setReversalSubmittingId('');
    }
    await openPayableDetail(selectedPayable);
    await loadAccountPayables(query, accountPayablePage);
  }

  async function submitAccountPayableAdjustment(event: FormEvent) {
    event.preventDefault();
    if (!selectedPayable || adjustmentSubmitting) return;
    const amount = Number(adjustmentForm.amount || 0);
    const reason = adjustmentForm.reason.trim();
    if (!Number.isFinite(amount) || amount <= 0 || reason.length < 3) {
      window.alert('Vui lòng nhập số tiền dương và lý do có ít nhất 3 ký tự.');
      return;
    }
    setAdjustmentSubmitting(true);
    try {
      await adminAccountPayablesApi.adminCreateAccountPayableAdjustment(selectedPayable.id, {
        type: adjustmentForm.type,
        amount: adjustmentForm.amount,
        reason,
      });
      notifyAdmin('Đã ghi nhận điều chỉnh công nợ nhà cung cấp.');
      setAdjustmentForm({ type: 'DEBIT', amount: '', reason: '' });
    } catch (error) {
      notifyAdmin(errorMessage(error), 'error', 'Không thể điều chỉnh công nợ');
      return;
    } finally {
      setAdjustmentSubmitting(false);
    }
    await openPayableDetail(selectedPayable);
    await loadAccountPayables(query, accountPayablePage);
  }

  return {
    accountPayables,
    accountPayableSummary,
    accountPayablePage,
    accountPayableTotal,
    accountPayableStatusFilter,
    setAccountPayableStatusFilter,
    accountPayableSupplierFilter,
    setAccountPayableSupplierFilter,
    accountPayableLoading,
    accountPayableLoadError,
    selectedPayable,
    setSelectedPayable,
    paymentForm,
    setPaymentForm,
    paymentSubmitting,
    adjustmentForm,
    setAdjustmentForm,
    adjustmentSubmitting,
    reversalSubmittingId,
    loadAccountPayables,
    openPayableDetail,
    closePayableDetail,
    submitSupplierPayment,
    reverseSupplierPayment,
    submitAccountPayableAdjustment,
  };
}
