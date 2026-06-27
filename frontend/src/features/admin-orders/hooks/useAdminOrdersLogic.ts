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
  issueAllocations: { orderItemId: string; locationId: string; quantity: number }[];
};

const initialOrderDraft: OrderDraft = {
  status: 'PENDING',
  assignedStaffName: '',
  internalNote: '',
  cancellationReason: '',
  shippingProvider: '',
  trackingCode: '',
  refundPayment: false,
  issueAllocations: [],
};

type UseAdminOrdersLogicParams = {
  setOrders: React.Dispatch<React.SetStateAction<any[]>>;
};

export function useAdminOrdersLogic({ setOrders }: UseAdminOrdersLogicParams) {
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null);
  const [orderPanelOpen, setOrderPanelOpen] = useState(false);
  const [orderPanelBusy, setOrderPanelBusy] = useState(false);
  const [orderSaving, setOrderSaving] = useState(false);
  const [carrierShipmentBusy, setCarrierShipmentBusy] = useState(false);
  const [carrierQuote, setCarrierQuote] = useState<any | null>(null);
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
      issueAllocations: [],
    });
  }

  async function openOrderPanel(orderId: string) {
    setOrderPanelOpen(true);
    setOrderPanelBusy(true);
    setCarrierQuote(null);
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
        issue_allocations: [],
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

  async function quoteCarrierShipment(provider?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    try {
      const quote = await adminOrdersApi.quoteCarrierShipment(selectedOrder.id, {
        provider: provider || orderDraft.shippingProvider || 'MOCK_GHN',
      });
      setCarrierQuote(quote);
      setOrderDraft((draft) => ({ ...draft, shippingProvider: quote.provider || draft.shippingProvider }));
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function createCarrierShipment(provider?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    try {
      const result = await adminOrdersApi.createCarrierShipment(selectedOrder.id, {
        provider: provider || orderDraft.shippingProvider || 'MOCK_GHN',
      });
      setCarrierQuote(result);
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function cancelCarrierShipment(reason?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    try {
      const result = await adminOrdersApi.cancelCarrierShipment(selectedOrder.id, { reason });
      setCarrierQuote(result);
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function simulateCarrierEvent(eventCode: string, note?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    try {
      const result = await adminOrdersApi.updateCarrierEvent(selectedOrder.id, {
        event_code: eventCode,
        note,
      });
      setCarrierQuote(result);
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
    } finally {
      setCarrierShipmentBusy(false);
    }
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
    carrierShipmentBusy,
    carrierQuote,
    setCarrierQuote,
    orderDraft,
    setOrderDraft,
    openOrderPanel,
    updateOrderStatus,
    saveOrderDraft,
    syncOrderDraft,
    mergeOrderListItem,
    printOrderDocument,
    quoteCarrierShipment,
    createCarrierShipment,
    cancelCarrierShipment,
    simulateCarrierEvent,
  };
}
