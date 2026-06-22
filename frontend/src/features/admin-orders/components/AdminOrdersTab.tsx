import React from 'react';
import { Activity, CheckCircle2, ClipboardList, Download, Eye, FileText, Plus, ScrollText, ShoppingBag, Trash2, Truck, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, EmptyState, Input, MetricCard, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';

type AdminOrdersTabProps = Record<string, any>;

export default function AdminOrdersTab(props: AdminOrdersTabProps) {
  const {
    cancelledOrders,
    compactId,
    currency,
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
    refundedOrders,
    saveOrderDraft,
    selectedOrder,
    setOrderDraft,
    setOrderPanelOpen,
    setQuery,
    statusLabel,
    updateOrderStatus,
    usePermission,
  } = props;
  const canUpdateOrder = usePermission('order:update');
  const activeIssueLocations = (inventoryLocations || []).filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE');
  const issueLocationOptions: [string, string][] = [
    ['', 'Chọn kệ thực tế'],
    ...activeIssueLocations.map((location: any) => [String(location.id), `${location.code} - ${location.name}${location.availableQuantity != null ? ` · còn ${location.availableQuantity}` : ''}`] as [string, string]),
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
  return (
    <AdminPanel 
      title="Quản lý đơn hàng" 
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã đơn, khách hàng, trạng thái" />}
    >
                <div className="mb-4 grid gap-3 md:grid-cols-4">
                  <MetricCard label="Chờ xử lý" value={String(orders.filter((item: any) => item.status === 'PENDING').length)} tone="amber" />
                  <MetricCard label="Đang giao" value={String(orders.filter((item: any) => item.status === 'SHIPPED').length)} tone="sky" />
                  <MetricCard label="Đã hủy" value={String(cancelledOrders)} tone="slate" />
                  <MetricCard label="Đã hoàn tiền" value={String(refundedOrders)} tone="emerald" />
                </div>
                <AdminTable headers={['Mã đơn', 'Khách hàng', 'Tổng tiền', 'Thanh toán', 'Trạng thái', 'Theo dõi', 'Thao tác']}>
                  {filteredOrders.map((order: any) => (
                    <tr key={order.id}>
                      <td className="px-4 py-3">
                        <div className="font-mono text-xs">{order.orderCode || compactId(order.id)}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{order.recipientName || order.userId || order.user_id || 'Khách lẻ'}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.recipientPhone || 'Không có số điện thoại'}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(order.totalAmount || order.total_amount || 0))}</td>
                      <td className="px-4 py-3">
                        <div>{order.paymentMethod || order.payment_method || '-'}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.paymentStatus || order.payment_status || '-'}</div>
                      </td>
                      <td className="px-4 py-3"><AdminBadge tone={order.status === 'COMPLETED' ? 'green' : order.status === 'CANCELLED' ? 'red' : 'yellow'}>{statusLabel[order.status] || order.status}</AdminBadge></td>
                      <td className="px-4 py-3 text-xs">
                        <div>{order.shippingProvider || 'Chưa gán đơn vị vận chuyển'}</div>
                        <div className="mt-1 font-mono text-slate-500">{order.trackingCode || 'Chưa có mã vận đơn'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => openOrderPanel(order.id)} className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-semibold text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
                            <Eye className="h-4 w-4" /> Chi tiết
                          </button>
                          {canUpdateOrder && <select className="h-9 rounded-md border border-slate-200 px-2 text-sm outline-none" value={order.status} onChange={(event) => {
                            if (event.target.value === 'SHIPPED') {
                              openOrderPanel(order.id);
                              return;
                            }
                            updateOrderStatus(order.id, event.target.value);
                          }}>
                            {(orderTransitionMap[order.status] || orderStatusOptions.map(([value]: [string]) => value)).map((value: string) => <option key={value} value={value}>{statusLabel[value] || value}</option>)}
                          </select>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
                {orderPanelOpen && (
                  <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                    <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
                      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
                        <div>
                          <h3 className="text-lg font-bold text-slate-950">Chi tiết đơn hàng</h3>
                          <p className="mt-1 text-sm text-slate-500">{selectedOrder?.orderCode || compactId(selectedOrder?.id)} · {selectedOrder ? (statusLabel[selectedOrder.status] || selectedOrder.status) : ''}</p>
                        </div>
                        <button type="button" onClick={() => setOrderPanelOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50"><X className="h-4 w-4" /></button>
                      </div>
                      <div className="max-h-[calc(100vh-120px)] overflow-y-auto p-5">
                        {orderPanelBusy || !selectedOrder ? <EmptyState text="Đang tải chi tiết đơn hàng..." /> : (
                          <div className="space-y-5">
                            <div className="grid gap-4 md:grid-cols-4">
                              <MetricCard label="Tổng tiền" value={currency.format(Number(selectedOrder.totalAmount || 0))} tone="amber" />
                              <MetricCard label="Thanh toán" value={selectedOrder.paymentStatus || '-'} tone="sky" />
                              <MetricCard label="Điểm cộng" value={String(selectedOrder.pointsEarned || 0)} tone="emerald" />
                              <MetricCard label="Điểm dùng" value={String(selectedOrder.pointsUsed || 0)} tone="slate" />
                            </div>
                            <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
                              <div className="space-y-5">
                                <AdminPanel title="Thông tin nhận hàng" action={<Truck className="h-5 w-5 text-red-600" />}>
                                  <div className="grid gap-3 md:grid-cols-2">
                                    <Input label="Người nhận" value={selectedOrder.recipientName || ''} onChange={() => { }} disabled />
                                    <Input label="Số điện thoại" value={selectedOrder.recipientPhone || ''} onChange={() => { }} disabled />
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Địa chỉ</span><textarea value={selectedOrder.shippingAddress || ''} readOnly className="min-h-[92px] w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none" /></label></div>
                                  </div>
                                </AdminPanel>
                                <AdminPanel title="Sản phẩm trong đơn" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
                                  <AdminTable headers={['Sản phẩm', 'SL', 'Đơn giá', 'Thành tiền']}>
                                    {(selectedOrder.items || []).map((item: any) => (
                                      <tr key={item.id}>
                                        <td className="px-4 py-3 font-semibold text-slate-900">{item.productName}</td>
                                        <td className="px-4 py-3">{item.quantity}</td>
                                        <td className="px-4 py-3">{currency.format(Number(item.price || 0))}</td>
                                        <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(item.totalPrice || 0))}</td>
                                      </tr>
                                    ))}
                                  </AdminTable>
                                </AdminPanel>
                                {canUpdateOrder && orderDraft.status === 'SHIPPED' && selectedOrder.status !== 'SHIPPED' && (
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
                                              <button
                                                type="button"
                                                onClick={() => addIssueAllocation(String(item.id), Math.max(requiredQuantity - allocatedQuantity, 1))}
                                                className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
                                              >
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
                                                  <Select
                                                    label="Kệ thực tế"
                                                    value={allocation.locationId || ''}
                                                    onChange={(value: any) => updateIssueAllocation(allocation.allocationIndex, { locationId: value })}
                                                    options={issueLocationOptions}
                                                  />
                                                  <Input
                                                    label="Số lượng"
                                                    type="number"
                                                    value={allocation.quantity}
                                                    onChange={(value: any) => updateIssueAllocation(allocation.allocationIndex, { quantity: Math.max(1, Number(value || 1)) })}
                                                  />
                                                  <button
                                                    type="button"
                                                    onClick={() => removeIssueAllocation(allocation.allocationIndex)}
                                                    className="mt-6 inline-flex h-10 w-10 items-center justify-center rounded-md border border-red-200 text-red-600 transition hover:bg-red-50"
                                                    title="Xóa kệ"
                                                  >
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
                                {canUpdateOrder && <AdminPanel title="Điều phối xử lý" action={<ClipboardList className="h-5 w-5 text-red-600" />}>
                                  <div className="grid gap-3 md:grid-cols-2">
                                    <Select label="Trạng thái" value={orderDraft.status} onChange={(value: any) => setOrderDraft({ ...orderDraft, status: value })} options={(orderTransitionMap[selectedOrder.status] || [selectedOrder.status]).map((value: any) => [value, statusLabel[value] || value]) as [string, string][]} />
                                    <Input label="Nhân viên xử lý" value={orderDraft.assignedStaffName} onChange={(value: any) => setOrderDraft({ ...orderDraft, assignedStaffName: value })} />
                                    <Input label="Đơn vị vận chuyển" value={orderDraft.shippingProvider} onChange={(value: any) => setOrderDraft({ ...orderDraft, shippingProvider: value })} />
                                    <Input label="Mã vận đơn" value={orderDraft.trackingCode} onChange={(value: any) => setOrderDraft({ ...orderDraft, trackingCode: value })} />
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Ghi chú nội bộ</span><textarea value={orderDraft.internalNote} onChange={(event) => setOrderDraft({ ...orderDraft, internalNote: event.target.value })} className="min-h-[110px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" /></label></div>
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Lý do hủy</span><textarea value={orderDraft.cancellationReason} onChange={(event) => setOrderDraft({ ...orderDraft, cancellationReason: event.target.value })} placeholder="Bắt buộc khi chuyển sang trạng thái đã hủy" className="min-h-[92px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" /></label></div>
                                    <div className="md:col-span-2"><Checkbox label="Đánh dấu hoàn tiền cho giao dịch online" checked={orderDraft.refundPayment} onChange={(checked: any) => setOrderDraft({ ...orderDraft, refundPayment: checked })} disabled={selectedOrder.paymentMethod === 'COD'} /></div>
                                  </div>
                                  <div className="mt-4 flex flex-wrap gap-2">
                                    <button type="button" onClick={() => saveOrderDraft()} disabled={orderSaving} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 disabled:opacity-50"><CheckCircle2 className="h-4 w-4" />Lưu cập nhật</button>
                                    <button type="button" onClick={() => printOrderDocument(selectedOrder, 'invoice')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" />In hóa đơn</button>
                                    <button type="button" onClick={() => printOrderDocument(selectedOrder, 'delivery')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><FileText className="h-4 w-4" />In phiếu giao hàng</button>
                                  </div>
                                </AdminPanel>}
                                <AdminPanel title="Dấu mốc đơn hàng" action={<Activity className="h-5 w-5 text-red-600" />}>
                                  <div className="space-y-2 text-sm text-slate-600">
                                    <div>Tạo đơn: {selectedOrder.createdAt ? new Date(selectedOrder.createdAt).toLocaleString('vi-VN') : '-'}</div>
                                    <div>Giao vận: {selectedOrder.shippedAt ? new Date(selectedOrder.shippedAt).toLocaleString('vi-VN') : 'Chưa giao vận'}</div>
                                    <div>Hoàn tất: {selectedOrder.completedAt ? new Date(selectedOrder.completedAt).toLocaleString('vi-VN') : 'Chưa hoàn tất'}</div>
                                    <div>Hủy đơn: {selectedOrder.cancelledAt ? new Date(selectedOrder.cancelledAt).toLocaleString('vi-VN') : 'Không có'}</div>
                                    <div>Hoàn tiền: {selectedOrder.refundedAt ? new Date(selectedOrder.refundedAt).toLocaleString('vi-VN') : 'Chưa hoàn tiền'}</div>
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
              </AdminPanel>
  );
}
