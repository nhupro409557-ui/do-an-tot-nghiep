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
  returnSource: string;
  returnReason: string;
  returnTrackingCode: string;
  returnReceivedCondition: string;
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
  returnSource: '',
  returnReason: '',
  returnTrackingCode: '',
  returnReceivedCondition: '',
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
  const [carrierFeedback, setCarrierFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [orderDraft, setOrderDraft] = useState<OrderDraft>(initialOrderDraft);

  function syncOrderDraft(order: any) {
    setOrderDraft({
      status: order.status || 'PENDING',
      assignedStaffName: order.assignedStaffName || '',
      internalNote: order.internalNote || '',
      cancellationReason: order.cancellationReason || '',
      shippingProvider: order.shippingProvider || '',
      trackingCode: order.trackingCode || '',
      returnSource: order.returnSource || '',
      returnReason: order.returnReason || '',
      returnTrackingCode: order.returnTrackingCode || '',
      returnReceivedCondition: order.returnReceivedCondition || '',
      refundPayment: false,
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

  async function updateOrderStatus(id: string, status: string, customerReceiptConfirmed = false) {
    await adminOrdersApi.updateOrderStatus(id, status, customerReceiptConfirmed);
    const detail = await adminOrdersApi.getOrderDetail(id);
    mergeOrderListItem(detail);
  }

  async function saveOrderDraft(statusOverride?: string, customerReceiptConfirmed = false) {
    if (!selectedOrder) return;
    setOrderSaving(true);
    try {
      await adminOrdersApi.adminUpdateOrder(selectedOrder.id, {
        status: statusOverride || orderDraft.status,
        assigned_staff_name: orderDraft.assignedStaffName || null,
        internal_note: orderDraft.internalNote || null,
        cancellation_reason: orderDraft.cancellationReason || null,
        shipping_provider: orderDraft.shippingProvider || null,
        tracking_code: orderDraft.trackingCode || null,
        return_source: orderDraft.returnSource || null,
        return_reason: orderDraft.returnReason || null,
        return_tracking_code: orderDraft.returnTrackingCode || null,
        return_received_condition: orderDraft.returnReceivedCondition || null,
        refund_payment: orderDraft.refundPayment,
        issue_allocations: [],
        customer_receipt_confirmed: customerReceiptConfirmed,
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
    setCarrierFeedback(null);
    try {
      const quote = await adminOrdersApi.quoteCarrierShipment(selectedOrder.id, {
        provider: provider || orderDraft.shippingProvider || 'MOCK_GHN',
      });
      setCarrierQuote(quote);
      setOrderDraft((draft) => ({ ...draft, shippingProvider: quote.provider || draft.shippingProvider }));
      setCarrierFeedback({ type: 'success', message: 'Đã tính phí vận chuyển thành công.' });
    } catch (error: any) {
      setCarrierFeedback({ type: 'error', message: error?.message || 'Không thể tính phí vận chuyển.' });
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function createCarrierShipment(provider?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    setCarrierFeedback(null);
    try {
      const result = await adminOrdersApi.createCarrierShipment(selectedOrder.id, {
        provider: provider || orderDraft.shippingProvider || 'MOCK_GHN',
      });
      setCarrierQuote(result);
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
      setCarrierFeedback({ type: 'success', message: 'Đã tạo vận đơn thành công.' });
    } catch (error: any) {
      setCarrierFeedback({ type: 'error', message: error?.message || 'Không thể tạo vận đơn.' });
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function cancelCarrierShipment(reason?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    setCarrierFeedback(null);
    try {
      const result = await adminOrdersApi.cancelCarrierShipment(selectedOrder.id, { reason });
      setCarrierQuote(result);
      const detail = await adminOrdersApi.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
      setCarrierFeedback({ type: 'success', message: 'Đã hủy vận đơn thành công.' });
    } catch (error: any) {
      setCarrierFeedback({ type: 'error', message: error?.message || 'Không thể hủy vận đơn.' });
    } finally {
      setCarrierShipmentBusy(false);
    }
  }

  async function simulateCarrierEvent(eventCode: string, note?: string) {
    if (!selectedOrder) return;
    setCarrierShipmentBusy(true);
    setCarrierFeedback(null);
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
      setCarrierFeedback({ type: 'success', message: result?.message || 'Đã cập nhật trạng thái vận chuyển.' });
    } catch (error: any) {
      setCarrierFeedback({ type: 'error', message: error?.message || 'Không thể cập nhật trạng thái vận chuyển.' });
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
    carrierFeedback,
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
