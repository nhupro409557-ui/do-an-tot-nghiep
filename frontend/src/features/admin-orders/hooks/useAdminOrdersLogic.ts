import { useState } from 'react';
import { adminOrdersApi } from '../services/adminOrdersApi';
import { compactId, currency, statusLabel } from '../../admin-shell/components/AdminDashboardConfig';
import { printOrderDocument as printOrderDocumentPopup } from '../utils/adminDashboardPrint';

export type OrderDraft = {
  status: string;
  assignedStaffName: string;
  internalNote: string;
  cancellationReason: string;
  shippingProvider: string;
  trackingCode: string;
  refundPayment: boolean;
};

const initialOrderDraft: OrderDraft = {
  status: 'PENDING',
  assignedStaffName: '',
  internalNote: '',
  cancellationReason: '',
  shippingProvider: '',
  trackingCode: '',
  refundPayment: false,
};

type UseAdminOrdersLogicParams = {
  setOrders: React.Dispatch<React.SetStateAction<any[]>>;
};

export function useAdminOrdersLogic({ setOrders }: UseAdminOrdersLogicParams) {
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null);
  const [orderPanelOpen, setOrderPanelOpen] = useState(false);
  const [orderPanelBusy, setOrderPanelBusy] = useState(false);
  const [orderSaving, setOrderSaving] = useState(false);
  const [orderDraft, setOrderDraft] = useState<OrderDraft>(initialOrderDraft);

  function syncOrderDraft(order: any) {
    setOrderDraft({
      status: order.status || 'PENDING',
      assignedStaffName: order.assignedStaffName || '',
      internalNote: order.internalNote || '',
      cancellationReason: order.cancellationReason || '',
      shippingProvider: order.shippingProvider || '',
      trackingCode: order.trackingCode || '',
      refundPayment: order.paymentMethod && order.paymentMethod !== 'COD' && ['PAID', 'PENDING'].includes(order.paymentStatus || ''),
    });
  }

  async function openOrderPanel(orderId: string) {
    setOrderPanelOpen(true);
    setOrderPanelBusy(true);
    try {
      const detail = await adminOrdersApi.getOrderDetail(orderId);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
    } finally {
      setOrderPanelBusy(false);
    }
  }

  function mergeOrderListItem(detail: any) {
    setOrders((items) => items.map((item) => (item.id === detail.id ? { ...item, ...detail } : item)));
  }

  async function updateOrderStatus(id: string, status: string) {
    await adminOrdersApi.updateOrderStatus(id, status);
    setOrders((items) => items.map((item) => (item.id === id ? { ...item, status } : item)));
  }

  async function saveOrderDraft() {
    if (!selectedOrder) return;
    setOrderSaving(true);
    try {
      await adminOrdersApi.adminUpdateOrder(selectedOrder.id, {
        status: orderDraft.status,
        assigned_staff_name: orderDraft.assignedStaffName || null,
        internal_note: orderDraft.internalNote || null,
        cancellation_reason: orderDraft.cancellationReason || null,
        shipping_provider: orderDraft.shippingProvider || null,
        tracking_code: orderDraft.trackingCode || null,
        refund_payment: orderDraft.refundPayment,
      });
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
    } finally {
      setOrderSaving(false);
    }
  }

  function printOrderDocument(order: any, mode: 'invoice' | 'delivery') {
    printOrderDocumentPopup(order, mode, { currency, compactId, statusLabel });
  }

  return {
    selectedOrder,
    setSelectedOrder,
    orderPanelOpen,
    setOrderPanelOpen,
    orderPanelBusy,
    setOrderPanelBusy,
    orderSaving,
    setOrderSaving,
    orderDraft,
    setOrderDraft,
    openOrderPanel,
    updateOrderStatus,
    saveOrderDraft,
    syncOrderDraft,
    mergeOrderListItem,
    printOrderDocument,
  };
}
