import React from 'react';
import { Activity, CheckCircle2, ClipboardList, Download, Eye, FileText, Plus, ScrollText, ShoppingBag, Trash2, Truck, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, EmptyState, Input, MetricCard, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { adminOrdersApi } from '../services/adminOrdersApi';
import AdminPosModal from './AdminPosModal';

const paymentStatusLabels: Record<string, string> = {
  UNPAID: 'Chưa thanh toán',
  PAID: 'Đã thanh toán',
  FAILED: 'Thanh toán thất bại',
  PENDING: 'Đang chờ thanh toán',
  EXPIRED: 'Đã hết hạn',
  REFUNDED: 'Đã hoàn tiền',
  PENDING_PAYMENT: 'Chờ thanh toán',
};

const carrierStatusLabels: Record<string, string> = {
  PENDING: 'Chờ lấy hàng',
  HANDED_TO_CARRIER: 'Đã bàn giao vận chuyển',
  IN_TRANSIT: 'Đang vận chuyển',
  DELIVERED: 'Giao hàng thành công',
  DELIVERY_FAILED: 'Giao hàng thất bại',
  CANCELLED: 'Đã hủy',
};

type AdminOrdersTabProps = Record<string, any>;

function orderItemsOf(order: any): any[] {
  return Array.isArray(order?.items) ? order.items : [];
}

function orderItemName(item: any): string {
  return item?.productName || item?.product_name || item?.name || 'Sản phẩm chưa có tên';
}

function orderItemUnitPrice(item: any): number {
  return Number(item?.price ?? item?.unitPrice ?? item?.unit_price ?? 0);
}

function orderItemTotalPrice(item: any): number {
  return Number(item?.totalPrice ?? item?.total_price ?? orderItemUnitPrice(item) * Number(item?.quantity || 0));
}

export default function AdminOrdersTab(props: AdminOrdersTabProps) {
  const {
    cancelledOrders,
    compactId,
    currency,
    carrierQuote,
    carrierShipmentBusy,
    cancelCarrierShipment,
    createCarrierShipment,
    filteredOrders,
    inventoryLocations,
    openOrderPanel,
    orderDraft,
    orderPanelBusy,
    orderPanelOpen,
    orderSaving,
    orderStatusOptions,
    orderTransitionMap,
    orders,
    printOrderDocument,
    query,
    quoteCarrierShipment,
    refundedOrders,
    saveOrderDraft,
    selectedOrder,
    setOrderDraft,
    setOrderPanelOpen,
    setQuery,
    setTab,
    simulateCarrierEvent,
    statusLabel,
    updateOrderStatus,
    usePermission,
    setOrders,
  } = props;

  const canUpdateOrder = usePermission('order:update');
  const [showPosModal, setShowPosModal] = React.useState(false);
  const refreshOrders = async () => {
    try {
      const data = await adminOrdersApi.listOrders();
      if (typeof setOrders === 'function') {
        setOrders(data);
      }
    } catch (e) {
      console.error('Không thể reload đơn hàng', e);
    }
  };
  const activeIssueLocations = (inventoryLocations || []).filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE');
  const issueLocationOptions: [string, string][] = [
    ['', 'Chọn kệ thực tế'],
    ...activeIssueLocations.map((location: any) => [
      String(location.id),
      `${location.code} - ${location.name}${location.availableQuantity != null ? ` · còn ${location.availableQuantity}` : ''}`,
    ] as [string, string]),
  ];
  const carrierProviderOptions: [string, string][] = [
    ['MOCK_GHN', 'Giao Hàng Nhanh (GHN)'],
    ['MOCK_GHTK', 'Giao Hàng Tiết Kiệm (GHTK)'],
    ['MANUAL', 'Vận chuyển nội bộ (Shop tự giao)'],
  ];
  const carrierEventOptions: [string, string][] = [
    ['HANDED_TO_CARRIER', 'Đã bàn giao cho đơn vị vận chuyển'],
    ['IN_TRANSIT', 'Đang giao hàng'],
    ['DELIVERED', 'Giao hàng thành công'],
    ['DELIVERY_FAILED', 'Giao hàng thất bại'],
  ];

  const addIssueAllocation = (orderItemId: string, defaultQuantity: number) => {
    const currentAllocations = orderDraft.issueAllocations || [];
    setOrderDraft({
      ...orderDraft,
      issueAllocations: [...currentAllocations, { orderItemId, locationId: '', quantity: defaultQuantity }],
    });
  };

  const updateIssueAllocation = (allocationIndex: number, changes: Record<string, any>) => {
    const currentAllocations = orderDraft.issueAllocations || [];
    setOrderDraft({
      ...orderDraft,
      issueAllocations: currentAllocations.map((allocation: any, index: number) => (
        index === allocationIndex ? { ...allocation, ...changes } : allocation
      )),
    });
  };

  const removeIssueAllocation = (allocationIndex: number) => {
    const currentAllocations = orderDraft.issueAllocations || [];
    setOrderDraft({
      ...orderDraft,
      issueAllocations: currentAllocations.filter((_: any, index: number) => index !== allocationIndex),
    });
  };

  const handleSaveOrder = () => {
    if (orderDraft.status === 'SHIPPED' && selectedOrder.outboundDocument && selectedOrder.outboundDocument.status !== 'COMPLETED') {
      window.alert(`Không thể chuyển đơn hàng sang trạng thái Đang giao (SHIPPED). Phiếu xuất kho liên kết (${selectedOrder.outboundDocument.documentNo}) chưa được hoàn tất bốc hàng.`);
      return;
    }
    if (typeof saveOrderDraft === 'function') {
      saveOrderDraft();
    }
  };

  return (
    <AdminPanel
      title="Quản lý đơn hàng"
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã đơn, khách hàng, trạng thái" />}
      action={
        <button
          type="button"
          onClick={() => setShowPosModal(true)}
          className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-red-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 cursor-pointer"
        >
          <Plus className="h-4 w-4" /> Tạo đơn tại quầy
        </button>
      }
    >
      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <MetricCard label="Chờ xử lý" value={String(orders.filter((item: any) => item.status === 'PENDING').length)} tone="amber" />
        <MetricCard label="Đang giao" value={String(orders.filter((item: any) => item.status === 'SHIPPED').length)} tone="sky" />
        <MetricCard label="Đã hủy" value={String(cancelledOrders)} tone="slate" />
        <MetricCard label="Đã hoàn tiền" value={String(refundedOrders)} tone="emerald" />
      </div>

      <AdminTable headers={['Mã đơn', 'Khách hàng', 'Sản phẩm', 'Tổng tiền', 'Thanh toán', 'Trạng thái', 'Theo dõi', 'Thao tác']}>
        {filteredOrders.map((order: any) => {
          const orderItems = orderItemsOf(order);
          const visibleItems = orderItems.slice(0, 2);
          const hiddenItemCount = Math.max(orderItems.length - visibleItems.length, 0);

          return (
            <tr key={order.id}>
              <td className="px-4 py-3">
                <div className="font-mono text-xs">{order.orderCode || compactId(order.id)}</div>
                <div className="mt-1 text-xs text-slate-500">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</div>
              </td>
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900">{order.recipientName || order.userId || order.user_id || 'Khách lẻ'}</div>
                <div className="mt-1 text-xs text-slate-500">{order.recipientPhone || 'Không có số điện thoại'}</div>
              </td>
              <td className="min-w-64 px-4 py-3">
                {orderItems.length > 0 ? (
                  <div className="space-y-1">
                    {visibleItems.map((item: any) => (
                      <div key={item.id || `${order.id}-${orderItemName(item)}`} className="text-sm font-semibold text-slate-900">
                        {orderItemName(item)}
                        <span className="ml-1 whitespace-nowrap text-xs font-bold text-slate-500">x{Number(item.quantity || 0)}</span>
                      </div>
                    ))}
                    {hiddenItemCount > 0 && (
                      <div className="text-xs font-semibold text-slate-500">+{hiddenItemCount} sản phẩm khác</div>
                    )}
                  </div>
                ) : (
                  <span className="text-xs font-semibold text-amber-700">Chưa có dòng sản phẩm</span>
                )}
              </td>
              <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(order.totalAmount || order.total_amount || 0))}</td>
              <td className="px-4 py-3">
                <div>{order.paymentMethod || order.payment_method || '-'}</div>
                <div className="mt-1 text-xs text-slate-500">{paymentStatusLabels[order.paymentStatus || order.payment_status || ''] || order.paymentStatus || order.payment_status || '-'}</div>
              </td>
              <td className="px-4 py-3">
                <AdminBadge tone={order.status === 'COMPLETED' ? 'green' : order.status === 'CANCELLED' ? 'red' : 'yellow'}>
                  {statusLabel[order.status] || order.status}
                </AdminBadge>
              </td>
              <td className="px-4 py-3 text-xs">
                <div>{order.shippingProvider || 'Chưa gán đơn vị vận chuyển'}</div>
                <div className="mt-1 font-mono text-slate-500">{order.trackingCode || 'Chưa có mã vận đơn'}</div>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <button type="button" onClick={() => openOrderPanel(order.id)} className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-semibold text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
                    <Eye className="h-4 w-4" /> Chi tiết
                  </button>
                  {canUpdateOrder && (
                    <select
                      className="h-9 rounded-md border border-slate-200 px-2 text-sm outline-none"
                      value={order.status}
                      onChange={(event) => {
                        if (event.target.value === 'SHIPPED') {
                          openOrderPanel(order.id);
                          return;
                        }
                        updateOrderStatus(order.id, event.target.value);
                      }}
                    >
                      {(orderTransitionMap[order.status] || orderStatusOptions.map(([value]: [string]) => value)).map((value: string) => (
                        <option key={value} value={value}>{statusLabel[value] || value}</option>
                      ))}
                    </select>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </AdminTable>

      {orderPanelOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Chi tiết đơn hàng</h3>
                <p className="mt-1 text-sm text-slate-500">{selectedOrder?.orderCode || compactId(selectedOrder?.id)} · {selectedOrder ? (statusLabel[selectedOrder.status] || selectedOrder.status) : ''}</p>
              </div>
              <button type="button" onClick={() => setOrderPanelOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-120px)] overflow-y-auto p-5">
              {orderPanelBusy || !selectedOrder ? <EmptyState text="Đang tải chi tiết đơn hàng..." /> : (
                <div className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-4">
                    <MetricCard label="Tổng tiền" value={currency.format(Number(selectedOrder.totalAmount || 0))} tone="amber" />
                    <MetricCard label="Thanh toán" value={paymentStatusLabels[selectedOrder.paymentStatus] || selectedOrder.paymentStatus || '-'} tone="sky" />
                    <MetricCard label="Điểm cộng" value={String(selectedOrder.pointsEarned || 0)} tone="emerald" />
                    <MetricCard label="Điểm dùng" value={String(selectedOrder.pointsUsed || 0)} tone="slate" />
                  </div>

                  <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
                    <div className="space-y-5">
                      <AdminPanel title="Thông tin nhận hàng" action={<Truck className="h-5 w-5 text-red-600" />}>
                        <div className="grid gap-3 md:grid-cols-2">
                          <Input label="Người nhận" value={selectedOrder.recipientName || ''} onChange={() => { }} disabled />
                          <Input label="Số điện thoại" value={selectedOrder.recipientPhone || ''} onChange={() => { }} disabled />
                          <div className="md:col-span-2">
                            <label className="block">
                              <span className="mb-1.5 block text-xs font-bold text-slate-500">Địa chỉ</span>
                              <textarea value={selectedOrder.shippingAddress || ''} readOnly className="min-h-[92px] w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none" />
                            </label>
                          </div>
                        </div>
                      </AdminPanel>

                      <AdminPanel title="Sản phẩm trong đơn" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
                        {orderItemsOf(selectedOrder).length > 0 ? (
                          <AdminTable headers={['Sản phẩm', 'SL', 'Đơn giá', 'Thành tiền']}>
                            {orderItemsOf(selectedOrder).map((item: any) => (
                              <tr key={item.id || orderItemName(item)}>
                                <td className="px-4 py-3 font-semibold text-slate-900">{orderItemName(item)}</td>
                                <td className="px-4 py-3">{item.quantity}</td>
                                <td className="px-4 py-3">{currency.format(orderItemUnitPrice(item))}</td>
                                <td className="px-4 py-3 font-semibold text-red-600">{currency.format(orderItemTotalPrice(item))}</td>
                              </tr>
                            ))}
                          </AdminTable>
                        ) : (
                          <EmptyState text="Đơn hàng này chưa có dòng sản phẩm." />
                        )}
                      </AdminPanel>

                      {/*
                        Ẩn khối chọn kệ xuất thực tế trên đơn hàng theo quy trình WMS mới.
                        Thao tác chọn kệ, quét IMEI/Serial sẽ được xử lý tại Phiếu xuất kho.
                      */}
                      {false && canUpdateOrder && orderDraft.status === 'SHIPPED' && selectedOrder.status !== 'SHIPPED' && (
                        <AdminPanel title="Xác nhận kệ xuất thực tế" action={<ClipboardList className="h-5 w-5 text-red-600" />}>
                          <div className="space-y-3">
                            {(selectedOrder.items || []).map((item: any) => {
                              const itemAllocations = (orderDraft.issueAllocations || [])
                                .map((entry: any, allocationIndex: number) => ({ ...entry, allocationIndex }))
                                .filter((entry: any) => entry.orderItemId === String(item.id));
                              const allocatedQuantity = itemAllocations.reduce((sum: number, entry: any) => sum + Number(entry.quantity || 0), 0);
                              const requiredQuantity = Number(item.quantity || 0);
                              const isMatched = itemAllocations.length > 0 && allocatedQuantity === requiredQuantity;
                              return (
                                <div key={item.id} className="rounded-md border border-slate-200 p-3">
                                  <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                      <div className="text-sm font-bold text-slate-900">{item.productName}</div>
                                      <div className={`mt-1 text-xs font-bold ${isMatched ? 'text-emerald-700' : 'text-amber-700'}`}>
                                        Đã phân bổ {allocatedQuantity} / cần xuất {requiredQuantity}
                                      </div>
                                    </div>
                                    <button type="button" onClick={() => addIssueAllocation(String(item.id), Math.max(requiredQuantity - allocatedQuantity, 1))} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                                      <Plus className="h-4 w-4" /> Thêm kệ
                                    </button>
                                  </div>
                                  {itemAllocations.length === 0 && (
                                    <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">
                                      Chưa xác nhận kệ. Hệ thống sẽ dùng FIFO nếu giữ nguyên.
                                    </div>
                                  )}
                                  <div className="mt-3 space-y-2">
                                    {itemAllocations.map((allocation: any) => (
                                      <div key={allocation.allocationIndex} className="grid gap-2 md:grid-cols-[1fr_120px_40px]">
                                        <Select label="Kệ thực tế" value={allocation.locationId || ''} onChange={(value: any) => updateIssueAllocation(allocation.allocationIndex, { locationId: value })} options={issueLocationOptions} />
                                        <Input label="Số lượng" type="number" value={allocation.quantity} onChange={(value: any) => updateIssueAllocation(allocation.allocationIndex, { quantity: Math.max(1, Number(value || 1)) })} />
                                        <button type="button" onClick={() => removeIssueAllocation(allocation.allocationIndex)} className="mt-6 inline-flex h-10 w-10 items-center justify-center rounded-md border border-red-200 text-red-600 transition hover:bg-red-50" title="Xóa kệ">
                                          <Trash2 className="h-4 w-4" />
                                        </button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </AdminPanel>
                      )}
                    </div>

                    <div className="space-y-5">
                      {canUpdateOrder && (
                        <AdminPanel title="Tích hợp đơn vị vận chuyển" action={<Truck className="h-5 w-5 text-red-600" />}>
                          <div className="grid gap-3 md:grid-cols-2">
                            <Select label="Đơn vị vận chuyển" value={orderDraft.shippingProvider || 'MOCK_GHN'} onChange={(value: any) => setOrderDraft({ ...orderDraft, shippingProvider: value })} options={carrierProviderOptions} />
                            <Input label="Mã vận đơn" value={orderDraft.trackingCode || selectedOrder.trackingCode || ''} onChange={(value: any) => setOrderDraft({ ...orderDraft, trackingCode: value })} />
                          </div>
                          <div className="mt-3 grid gap-2 md:grid-cols-3">
                            <button type="button" onClick={() => quoteCarrierShipment(orderDraft.shippingProvider)} disabled={carrierShipmentBusy} className="inline-flex h-10 items-center justify-center rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50">Tính phí vận chuyển</button>
                            <button type="button" onClick={() => createCarrierShipment(orderDraft.shippingProvider)} disabled={carrierShipmentBusy} className="inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:opacity-50">Tạo vận đơn</button>
                            <button type="button" onClick={() => cancelCarrierShipment('Hủy vận đơn.')} disabled={carrierShipmentBusy || !(selectedOrder.trackingCode || orderDraft.trackingCode)} className="inline-flex h-10 items-center justify-center rounded-md border border-red-200 px-3 text-sm font-bold text-red-700 transition hover:bg-red-50 disabled:opacity-50">Huỷ vận đơn</button>
                          </div>
                          {carrierQuote && (
                            <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                              <div className="font-bold text-slate-900">{carrierQuote.provider} · {carrierStatusLabels[carrierQuote.carrier_status] || carrierQuote.carrier_status}</div>
                              <div className="mt-1">Phí dự kiến: {currency.format(Number(carrierQuote.shipping_fee || 0))} · {carrierQuote.estimated_days} ngày</div>
                              {carrierQuote.tracking_code && <div className="mt-1 font-mono text-xs">Tracking: {carrierQuote.tracking_code}</div>}
                              {carrierQuote.message && <div className="mt-1 text-xs text-slate-500">{carrierQuote.message}</div>}
                            </div>
                          )}
                          <div className="mt-3 grid gap-2 md:grid-cols-2">
                            {carrierEventOptions.map(([value, label]) => (
                              <button key={value} type="button" onClick={() => simulateCarrierEvent(value)} disabled={carrierShipmentBusy || !(selectedOrder.trackingCode || orderDraft.trackingCode)} className="inline-flex h-9 items-center justify-center rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50">
                                {label}
                              </button>
                            ))}
                          </div>
                          <p className="mt-3 text-xs leading-5 text-slate-500">
                            Đây là môi trường mô phỏng cho đồ án. Hệ thống không gọi GHN/GHTK thật và không phát sinh vận chuyển thật.
                          </p>
                        </AdminPanel>
                      )}

                      {canUpdateOrder && (
                        <AdminPanel title="Điều phối xử lý" action={<ClipboardList className="h-5 w-5 text-red-600" />}>
                          {selectedOrder.outboundDocument && (
                            <div className="md:col-span-2 mb-3 rounded-md bg-sky-50 border border-sky-200 p-3 text-sm text-sky-900">
                              <div className="font-bold text-sky-950">Phiếu xuất kho liên kết:</div>
                              <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
                                <div>
                                  Mã phiếu: <span className="font-mono font-bold">{selectedOrder.outboundDocument.documentNo}</span>
                                  {selectedOrder.outboundDocument.status === 'COMPLETED' ? (
                                    <span className="ml-2 inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">Hoàn tất</span>
                                  ) : (
                                    <span className="ml-2 inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800">Nháp (Chờ quét)</span>
                                  )}
                                </div>
                                <button
                                  type="button"
                                  onClick={() => {
                                    if (typeof setTab === 'function') {
                                      setTab('inventoryOutbounds');
                                    }
                                    setOrderPanelOpen(false);
                                  }}
                                  className="text-xs font-bold text-sky-700 hover:text-sky-900 underline"
                                >
                                  Đi tới phiếu xuất kho →
                                </button>
                              </div>
                            </div>
                          )}
                          <div className="grid gap-3 md:grid-cols-2">
                            <Select label="Trạng thái" value={orderDraft.status} onChange={(value: any) => setOrderDraft({ ...orderDraft, status: value })} options={(orderTransitionMap[selectedOrder.status] || [selectedOrder.status]).map((value: any) => [value, statusLabel[value] || value]) as [string, string][]} />
                            <Input label="Nhân viên xử lý" value={orderDraft.assignedStaffName} onChange={(value: any) => setOrderDraft({ ...orderDraft, assignedStaffName: value })} />
                            <Input label="Đơn vị vận chuyển" value={orderDraft.shippingProvider} onChange={(value: any) => setOrderDraft({ ...orderDraft, shippingProvider: value })} />
                            <Input label="Mã vận đơn" value={orderDraft.trackingCode} onChange={(value: any) => setOrderDraft({ ...orderDraft, trackingCode: value })} />
                            <div className="md:col-span-2">
                              <label className="block">
                                <span className="mb-1.5 block text-xs font-bold text-slate-500">Ghi chú nội bộ</span>
                                <textarea value={orderDraft.internalNote} onChange={(event) => setOrderDraft({ ...orderDraft, internalNote: event.target.value })} className="min-h-[110px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" />
                              </label>
                            </div>
                            <div className="md:col-span-2">
                              <label className="block">
                                <span className="mb-1.5 block text-xs font-bold text-slate-500">Lý do hủy</span>
                                <textarea value={orderDraft.cancellationReason} onChange={(event) => setOrderDraft({ ...orderDraft, cancellationReason: event.target.value })} placeholder="Bắt buộc khi chuyển sang trạng thái đã hủy" className="min-h-[92px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" />
                              </label>
                            </div>
                            <div className="md:col-span-2">
                              <Checkbox label="Đánh dấu hoàn tiền cho giao dịch online" checked={orderDraft.refundPayment} onChange={(checked: any) => setOrderDraft({ ...orderDraft, refundPayment: checked })} disabled={selectedOrder.paymentMethod === 'COD'} />
                            </div>
                          </div>
                          <div className="mt-4 flex flex-wrap gap-2">
                            <button type="button" onClick={handleSaveOrder} disabled={orderSaving} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 disabled:opacity-50"><CheckCircle2 className="h-4 w-4" />Lưu cập nhật</button>
                            <button type="button" onClick={() => printOrderDocument(selectedOrder, 'invoice')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" />In hóa đơn</button>
                            <button type="button" onClick={() => printOrderDocument(selectedOrder, 'delivery')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><FileText className="h-4 w-4" />In phiếu giao hàng</button>
                          </div>
                        </AdminPanel>
                      )}

                      <AdminPanel title="Dấu mốc đơn hàng" action={<Activity className="h-5 w-5 text-red-600" />}>
                        <div className="space-y-2 text-sm text-slate-600">
                          <div>Tạo đơn: {selectedOrder.createdAt ? new Date(selectedOrder.createdAt).toLocaleString('vi-VN') : '-'}</div>
                          <div>Giao vận: {selectedOrder.shippedAt ? new Date(selectedOrder.shippedAt).toLocaleString('vi-VN') : 'Chưa giao vận'}</div>
                          <div>Hoàn tất: {selectedOrder.completedAt ? new Date(selectedOrder.completedAt).toLocaleString('vi-VN') : 'Chưa hoàn tất'}</div>
                          <div>Hủy đơn: {selectedOrder.cancelledAt ? new Date(selectedOrder.cancelledAt).toLocaleString('vi-VN') : 'Không có'}</div>
                          <div>Hoàn tiền: {selectedOrder.refundedAt ? new Date(selectedOrder.refundedAt).toLocaleString('vi-VN') : 'Chưa hoàn tiền'}</div>
                          {(selectedOrder.payments || []).map((payment: any) => (
                            <div key={payment.id} className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                              <div className="font-bold">{payment.provider} Sandbox · Lần {payment.attemptNumber || 1}</div>
                              <div>Trạng thái: {paymentStatusLabels[payment.status] || payment.status}</div>
                              <div>Mã giao dịch: {payment.transactionRef || '-'}</div>
                              <div>Hết hạn: {payment.expiresAt ? new Date(payment.expiresAt).toLocaleString('vi-VN') : '-'}</div>
                              {payment.refundMode && <div>Chế độ hoàn tiền: {payment.refundMode}</div>}
                            </div>
                          ))}
                        </div>
                      </AdminPanel>

                      <AdminPanel title="Lịch sử thao tác" action={<ScrollText className="h-5 w-5 text-red-600" />}>
                        <div className="space-y-3">
                          {(selectedOrder.historyLogs || []).length === 0 && <EmptyState text="Chưa có lịch sử thao tác." />}
                          {(selectedOrder.historyLogs || []).map((log: any) => (
                            <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                              <div className="flex items-center justify-between gap-3">
                                <div className="text-sm font-bold text-slate-900">
                                  {(statusLabel[log.oldStatus] || log.oldStatus || 'Khởi tạo')} → {statusLabel[log.newStatus] || log.newStatus}
                                </div>
                                <div className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</div>
                              </div>
                              <div className="mt-1 text-xs font-semibold text-slate-500">Thực hiện bởi: {log.changedBy || 'Hệ thống'}</div>
                              {log.note && <div className="mt-2 text-sm text-slate-600">{log.note}</div>}
                            </div>
                          ))}
                        </div>
                      </AdminPanel>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      <AdminPosModal
        isOpen={showPosModal}
        onClose={() => setShowPosModal(false)}
        onSuccess={refreshOrders}
        currency={currency}
      />
    </AdminPanel>
  );
}
