import { useState, type FormEvent } from 'react';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { adminAccountPayablesApi } from '../services/adminAccountPayablesApi';

const ACCOUNT_PAYABLE_PAGE_SIZE = 50;

const initialPaymentForm = {
  amount: 0,
  paymentDate: new Date().toISOString().slice(0, 10),
  method: 'BANK_TRANSFER',
  referenceNo: '',
  note: '',
};

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
  const [selectedPayable, setSelectedPayable] = useState<any | null>(null);
  const [paymentForm, setPaymentForm] = useState(initialPaymentForm);

  async function loadAccountPayables(search = query, page = 1) {
    const [result, summary] = await Promise.all([
      adminAccountPayablesApi.adminListAccountPayables({
        search: search.trim(),
        status: accountPayableStatusFilter,
        supplierId: accountPayableSupplierFilter,
        page,
        pageSize: ACCOUNT_PAYABLE_PAGE_SIZE,
      }).catch(() => ({ items: [], total: 0, page: 1, pageSize: ACCOUNT_PAYABLE_PAGE_SIZE })),
      adminAccountPayablesApi.adminGetAccountPayableSummary().catch(() => ({})),
    ]);
    setAccountPayables(Array.isArray(result.items) ? result.items : []);
    setAccountPayablePage(Number(result.page || page));
    setAccountPayableTotal(Number(result.total || 0));
    setAccountPayableSummary(summary || {});
  }

  async function openPayableDetail(payable: any) {
    const detail = await adminAccountPayablesApi.adminGetAccountPayableDetail(payable.id);
    setSelectedPayable(detail);
    setPaymentForm({
      ...initialPaymentForm,
      amount: Number(detail.remainingAmount || 0),
    });
  }

  function closePayableDetail() {
    setSelectedPayable(null);
    setPaymentForm(initialPaymentForm);
  }

  async function submitSupplierPayment(event: FormEvent) {
    event.preventDefault();
    if (!selectedPayable) return;
    const amount = Number(paymentForm.amount || 0);
    if (!Number.isFinite(amount) || amount <= 0) {
      window.alert('Số tiền thanh toán phải lớn hơn 0.');
      return;
    }
    await adminAccountPayablesApi.adminCreateSupplierPayment(selectedPayable.id, {
      amount,
      paymentDate: paymentForm.paymentDate ? new Date(paymentForm.paymentDate).toISOString() : null,
      method: paymentForm.method,
      referenceNo: paymentForm.referenceNo.trim() || null,
      note: paymentForm.note.trim() || null,
    });
    notifyAdmin('Đã ghi nhận thanh toán công nợ nhà cung cấp.');
    closePayableDetail();
    await loadAccountPayables(query, accountPayablePage);
    await reloadCurrentTab();
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
    selectedPayable,
    setSelectedPayable,
    paymentForm,
    setPaymentForm,
    loadAccountPayables,
    openPayableDetail,
    closePayableDetail,
    submitSupplierPayment,
  };
}
