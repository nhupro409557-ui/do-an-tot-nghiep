import React from 'react';
import { Edit2, KeyRound, Plus, RefreshCw, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, EmptyState, Input, MetricCard, MiniMetric, Select } from '../AdminDashboardParts';

type AdminPermissionsTabProps = Record<string, any>;

export default function AdminPermissionsTab(props: AdminPermissionsTabProps) {
  const {
    addCustomerNote,
    adjustCustomerPoints,
    auditLogs,
    canManageCustomerAccess,
    canManageCustomerProfile,
    compactId,
    createStaffAccount,
    currency,
    customerActiveSection,
    customerAuditLogs,
    customerDetailBusy,
    customerDetailOpen,
    customerLoyaltyHistory,
    customerNoteDraft,
    customerNotes,
    customerOrders,
    customerPointDelta,
    customerPointReason,
    customerTagDraft,
    customerVoucherId,
    customerVoucherNote,
    editingStaffAccessId,
    issueCustomerVoucher,
    loadCustomerSection,
    openStaffPermissionEditor,
    permissions,
    permissionsByModule,
    rolePermissionEditing,
    rolePermissionMap,
    roles,
    saveCustomerTags,
    saveStaffPermissions,
    selectedCustomer,
    setCustomerActiveSection,
    setCustomerDetailOpen,
    setCustomerNoteDraft,
    setCustomerPointDelta,
    setCustomerPointReason,
    setCustomerTagDraft,
    setCustomerVoucherId,
    setCustomerVoucherNote,
    setEditingStaffAccessId,
    setRolePermissionEditing,
    setStaffForm,
    setStaffPermissionDraft,
    setStaffPermissionEditor,
    staffBasePermissionCodes,
    staffForm,
    staffPermissionDraft,
    staffPermissionEditor,
    staffUsers,
    toggleRolePermission,
    updateUserAccess,
    usePermission,
    vouchers,
  } = props;
  return (
    <>
      <AdminPanel title="Ma trận phân quyền theo vai trò" action={<RefreshCw className="h-5 w-5 text-red-600" />}>
                <div className="mb-4 flex justify-end">
                  <button type="button" onClick={() => setRolePermissionEditing((value) => !value)} className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                    {rolePermissionEditing ? <RefreshCw className="h-4 w-4" /> : <Edit2 className="h-4 w-4" />}
                    {rolePermissionEditing ? 'Khóa quyền' : 'Chỉnh sửa quyền'}
                  </button>
                </div>
                {canManageCustomerAccess && (
                  <div className="mb-6 grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
                    <form onSubmit={createStaffAccount} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-3">
                        <div className="text-sm font-black text-slate-900">Tạo tài khoản nhân viên</div>
                        <div className="mt-1 text-xs font-medium text-slate-500">Nhân viên mới chỉ nhận quyền cơ bản của Staff Admin. Quyền bổ sung được Super Admin cấp sau.</div>
                      </div>
                      <div className="grid gap-3">
                        <Input label="Họ tên nhân viên" value={staffForm.fullName} required onChange={(value) => setStaffForm({ ...staffForm, fullName: value })} />
                        <Input label="Email đăng nhập" type="email" value={staffForm.email} required onChange={(value) => setStaffForm({ ...staffForm, email: value })} />
                        <Input label="Mật khẩu tạm" type="password" value={staffForm.password} required onChange={(value) => setStaffForm({ ...staffForm, password: value })} />
                        <Input label="Số điện thoại" value={staffForm.phone} onChange={(value) => setStaffForm({ ...staffForm, phone: value })} />
                        <Select label="Trạng thái" value={staffForm.status} onChange={(value) => setStaffForm({ ...staffForm, status: value })} options={[['ACTIVE', 'ACTIVE'], ['SUSPENDED', 'SUSPENDED']]} />
                        <button type="submit" className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800">
                          <Plus className="h-4 w-4" /> Tạo nhân viên
                        </button>
                      </div>
                    </form>
                    <div className="rounded-lg border border-slate-200 bg-white p-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-black text-slate-900">Nhân viên admin</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">Staff Admin dùng quyền cơ bản và các quyền bổ sung riêng.</div>
                        </div>
                        <AdminBadge tone="blue">{staffBasePermissionCodes.length} quyền cơ bản</AdminBadge>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-left text-sm">
                          <thead>
                            <tr className="border-b border-slate-200 text-xs font-bold uppercase text-slate-500">
                              <th className="px-3 py-2">Nhân viên</th>
                              <th className="px-3 py-2">Vai trò</th>
                              <th className="px-3 py-2">Quyền bổ sung</th>
                              <th className="px-3 py-2">Trạng thái</th>
                              <th className="px-3 py-2">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {staffUsers.length === 0 ? (
                              <tr><td colSpan={5} className="px-3 py-6 text-center text-sm text-slate-500">Chưa có tài khoản nhân viên admin.</td></tr>
                            ) : staffUsers.map((staff) => {
                              const isEditingStaff = editingStaffAccessId === staff.id;
                              const isSuper = false;
                              return (
                                <tr key={staff.id}>
                                  <td className="px-3 py-3">
                                    <div className="font-semibold text-slate-900">{staff.fullName || staff.email}</div>
                                    <div className="text-xs text-slate-500">{staff.email}</div>
                                  </td>
                                  <td className="px-3 py-3"><AdminBadge tone={isSuper ? 'red' : 'slate'}>{isSuper ? 'Super Admin' : 'Staff Admin'}</AdminBadge></td>
                                  <td className="px-3 py-3">{isSuper ? 'Tất cả quyền' : `${(staff.extraPermissionCodes || []).length} quyền`}</td>
                                  <td className="px-3 py-3">
                                    {isSuper ? staff.status : (
                                      <select disabled={!isEditingStaff} value={staff.status || 'ACTIVE'} onChange={(event) => updateUserAccess(staff, { status: event.target.value })} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs font-semibold outline-none focus:border-red-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500">
                                        <option value="ACTIVE">ACTIVE</option>
                                        <option value="SUSPENDED">SUSPENDED</option>
                                      </select>
                                    )}
                                  </td>
                                  <td className="px-3 py-3">
                                    <button type="button" onClick={() => setEditingStaffAccessId(isEditingStaff ? null : staff.id)} className="mr-2 inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                                      <Edit2 className="h-4 w-4" /> {isEditingStaff ? 'Khóa lại' : 'Chỉnh sửa'}
                                    </button>
                                    <button type="button" disabled={isSuper} onClick={() => openStaffPermissionEditor(staff)} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">
                                      <KeyRound className="h-4 w-4" /> Chỉnh quyền
                                    </button>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500">
                        <th className="sticky left-0 z-10 bg-slate-50 px-4 py-3">Quyền</th>
                        {roles.filter((role) => role.code === 'STAFF_ADMIN').map((role) => (
                          <th key={role.id} className="px-4 py-3">{role.name || role.code}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {permissions.map((permission) => (
                        <tr key={permission.code} className="hover:bg-slate-50/70">
                          <td className="sticky left-0 z-10 bg-white px-4 py-3">
                            <div className="font-semibold text-slate-900">{permission.code}</div>
                            <div className="text-xs text-slate-500">{permission.description || permission.module}</div>
                          </td>
                          {roles.filter((role) => role.code === 'STAFF_ADMIN').map((role) => {
                            const checked = (rolePermissionMap[role.id] || []).includes(permission.code);
                            const locked = role.code === 'SUPER_ADMIN';
                            return (
                              <td key={`${role.id}-${permission.code}`} className="px-4 py-3">
                                <input
                                  type="checkbox"
                                  checked={checked || locked}
                                  disabled={locked || !rolePermissionEditing}
                                  onChange={(event) => toggleRolePermission(role.id, permission.code, event.target.checked)}
                                  className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                                />
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 text-sm font-bold text-slate-900">Nhật ký đổi quyền gần đây</div>
                  <div className="space-y-2">
                    {auditLogs
                      .filter((log) => ['admin_user_access_updated', 'admin_role_permissions_updated'].includes(log.eventType))
                      .slice(0, 8)
                      .map((log) => (
                        <div key={log.id} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold text-slate-900">{log.eventType === 'admin_user_access_updated' ? 'Đổi vai trò / trạng thái user' : 'Cập nhật ma trận quyền'}</span>
                            <span className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</span>
                          </div>
                          <div className="mt-1 text-xs text-slate-600">
                            {log.eventType === 'admin_user_access_updated'
                              ? `User: ${log.metadata?.targetUserId || '-'} | Vai trò mới: ${log.metadata?.after?.role || '-'} | Trạng thái mới: ${log.metadata?.after?.status || '-'}`
                              : `Role: ${log.metadata?.roleCode || '-'} | Số user bị ảnh hưởng: ${log.metadata?.affectedUsers || 0}`}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </AdminPanel>
            {staffPermissionEditor && (
              <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
                  <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-950">Chỉnh quyền nhân viên</h3>
                      <p className="mt-1 text-sm text-slate-500">{staffPermissionEditor.fullName || staffPermissionEditor.email} đang có quyền cơ bản của Staff Admin. Các ô mở là quyền bổ sung riêng.</p>
                    </div>
                    <button type="button" onClick={() => setStaffPermissionEditor(null)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="max-h-[70vh] overflow-y-auto p-5">
                    <div className="mb-4 grid gap-3 md:grid-cols-3">
                      <MiniMetric label="Quyền cơ bản" value={staffBasePermissionCodes.length} helper="Từ vai trò Staff Admin" />
                      <MiniMetric label="Quyền bổ sung" value={staffPermissionDraft.length} helper="Cấp riêng cho nhân viên này" />
                      <MiniMetric label="Tổng hiệu lực" value={new Set([...staffBasePermissionCodes, ...staffPermissionDraft]).size} helper="Cơ bản + bổ sung" />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      {Object.entries(permissionsByModule).map(([moduleName, modulePermissions]) => (
                        <div key={moduleName} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                          <div className="mb-3 text-sm font-black uppercase text-slate-700">{moduleName}</div>
                          <div className="space-y-2">
                            {(modulePermissions as any[]).map((permission) => {
                              const baseLocked = staffBasePermissionCodes.includes(permission.code);
                              const checked = baseLocked || staffPermissionDraft.includes(permission.code);
                              return (
                                <label key={permission.code} className={`flex items-start gap-3 rounded-md border px-3 py-2 ${baseLocked ? 'border-slate-200 bg-white/70 opacity-75' : 'border-slate-200 bg-white'}`}>
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    disabled={baseLocked}
                                    onChange={(event) => {
                                      setStaffPermissionDraft((prev) => event.target.checked
                                        ? [...new Set([...prev, permission.code])]
                                        : prev.filter((code) => code !== permission.code));
                                    }}
                                    className="mt-1 h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                                  />
                                  <span>
                                    <span className="block text-sm font-bold text-slate-900">{permission.code}</span>
                                    <span className="block text-xs text-slate-500">{baseLocked ? 'Quyền cơ bản' : (permission.description || permission.module)}</span>
                                  </span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-4">
                    <button type="button" onClick={() => setStaffPermissionEditor(null)} className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">Hủy</button>
                    <button type="button" onClick={() => void saveStaffPermissions()} className="rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800">Lưu quyền</button>
                  </div>
                </div>
              </div>
            )}
            {customerDetailOpen && (
              <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
                  <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-950">Hồ sơ khách hàng</h3>
                      <p className="mt-1 text-sm text-slate-500">{selectedCustomer?.fullName || selectedCustomer?.email || 'Đang tải dữ liệu khách hàng'}</p>
                    </div>
                    <button type="button" onClick={() => setCustomerDetailOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">
                    {customerDetailBusy || !selectedCustomer ? (
                      <EmptyState text="Đang tải hồ sơ khách hàng..." />
                    ) : (
                      <div className="space-y-5">
                        <div className="flex flex-wrap gap-2">
                          {[
                            ['summary', 'Tổng quan'],
                            ['orders', 'Đơn hàng'],
                            ['loyalty', 'Điểm thưởng'],
                            ['notes', 'Ghi chú CSKH'],
                            ['audit', 'Nhật ký'],
                          ].map(([sectionId, label]) => (
                            <button
                              key={sectionId}
                              type="button"
                              onClick={() => sectionId === 'summary' ? setCustomerActiveSection('summary') : void loadCustomerSection(sectionId as 'orders' | 'loyalty' | 'notes' | 'audit')}
                              className={`rounded-md px-3 py-2 text-sm font-bold transition ${customerActiveSection === sectionId ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                        <div className="grid gap-3 md:grid-cols-4">
                          <MetricCard label="Tổng chi tiêu" value={currency.format(Number(selectedCustomer.totalSpent || 0))} tone="sky" />
                          <MetricCard label="Điểm hiện có" value={String(selectedCustomer.points || 0)} tone="amber" />
                          <MetricCard label="Số đơn" value={String(selectedCustomer.orderCount || 0)} tone="emerald" />
                          <MetricCard label="Voucher đã giữ" value={String(selectedCustomer.voucherCount || 0)} />
                        </div>
                        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <div className="text-sm font-bold text-slate-900">Thông tin chung</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              <div><div className="text-xs font-bold text-slate-500">Email</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.email}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Điện thoại</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.phone || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Vai trò</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.role || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Hạng thành viên</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.tier || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Trạng thái</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.status || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Ngày tạo</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.createdAt ? new Date(selectedCustomer.createdAt).toLocaleString('vi-VN') : '-'}</div></div>
                            </div>
                          </div>
                          <div className="rounded-lg border border-slate-200 bg-white p-4">
                            <div className="text-sm font-bold text-slate-900">Tag khách hàng</div>
                            <p className="mt-1 text-xs text-slate-500">Nhập tag cách nhau bởi dấu phẩy để phục vụ CSKH và phân nhóm thủ công.</p>
                            <textarea value={customerTagDraft} onChange={(event) => setCustomerTagDraft(event.target.value)} className="mt-3 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" />
                            {canManageCustomerProfile && (
                              <button type="button" onClick={() => void saveCustomerTags()} className="mt-3 rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800">Lưu tag</button>
                            )}
                          </div>
                        </div>
                        {usePermission('customer:loyalty_adjust') && (
                          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                            <div className="text-sm font-bold text-amber-900">Cộng / trừ điểm thủ công</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-[160px_1fr_auto]">
                              <Input label="Số điểm" value={customerPointDelta} onChange={setCustomerPointDelta} type="number" />
                              <Input label="Lý do" value={customerPointReason} onChange={setCustomerPointReason} />
                              <div className="flex items-end">
                                <button type="button" onClick={() => void adjustCustomerPoints()} className="inline-flex h-10 items-center justify-center rounded-md bg-amber-600 px-4 text-sm font-bold text-white transition hover:bg-amber-700">Cập nhật điểm</button>
                              </div>
                            </div>
                          </div>
                        )}
                        {usePermission('customer:issue_voucher') && (
                          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                            <div className="text-sm font-bold text-emerald-900">Gửi voucher riêng</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                              <Select label="Voucher" value={customerVoucherId} onChange={setCustomerVoucherId} options={[['', 'Chọn voucher'], ...vouchers.filter((voucher) => voucher.status === 'ACTIVE').map((voucher) => [voucher.id, `${voucher.code} - ${voucher.discountType === 'PERCENT' ? `${voucher.discountValue}%` : currency.format(Number(voucher.discountValue || 0))}`] as [string, string])]} />
                              <Input label="Ghi chú nội bộ" value={customerVoucherNote} onChange={setCustomerVoucherNote} />
                              <div className="flex items-end">
                                <button type="button" onClick={() => void issueCustomerVoucher()} className="inline-flex h-10 items-center justify-center rounded-md bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700">Gửi voucher</button>
                              </div>
                            </div>
                          </div>
                        )}
                        {customerActiveSection === 'summary' && (
                          <div className="grid gap-5 xl:grid-cols-2">
                            <AdminPanel title="Lịch sử đơn hàng">
                              <AdminTable headers={['Mã đơn', 'Trạng thái', 'Thanh toán', 'Tổng tiền', 'Ngày tạo']}>
                                {customerOrders.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có đơn hàng.</td></tr> : customerOrders.map((order) => (
                                  <tr key={order.id}>
                                    <td className="px-4 py-3 font-mono text-xs">{order.orderCode || compactId(order.id)}</td>
                                    <td className="px-4 py-3">{order.status}</td>
                                    <td className="px-4 py-3">{order.paymentStatus || order.paymentMethod || '-'}</td>
                                    <td className="px-4 py-3">{currency.format(Number(order.totalAmount || 0))}</td>
                                    <td className="px-4 py-3">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                  </tr>
                                ))}
                              </AdminTable>
                            </AdminPanel>
                            <AdminPanel title="Lịch sử điểm thưởng">
                              <AdminTable headers={['Loại', 'Điểm', 'Số dư trước/sau', 'Lý do', 'Thời gian']}>
                                {customerLoyaltyHistory.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có lịch sử điểm.</td></tr> : customerLoyaltyHistory.map((item) => (
                                  <tr key={item.id}>
                                    <td className="px-4 py-3">{item.type}</td>
                                    <td className="px-4 py-3 font-semibold">{item.metadata?.delta ?? item.points}</td>
                                    <td className="px-4 py-3">{item.balanceBefore} / {item.balanceAfter}</td>
                                    <td className="px-4 py-3 text-sm text-slate-600">{item.reason}</td>
                                    <td className="px-4 py-3">{item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                  </tr>
                                ))}
                              </AdminTable>
                            </AdminPanel>
                          </div>
                        )}
                        {customerActiveSection === 'orders' && (
                          <AdminPanel title="Lịch sử đơn hàng">
                            <AdminTable headers={['Mã đơn', 'Trạng thái', 'Thanh toán', 'Tổng tiền', 'Ngày tạo']}>
                              {customerOrders.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có đơn hàng.</td></tr> : customerOrders.map((order) => (
                                <tr key={order.id}>
                                  <td className="px-4 py-3 font-mono text-xs">{order.orderCode || compactId(order.id)}</td>
                                  <td className="px-4 py-3">{order.status}</td>
                                  <td className="px-4 py-3">{order.paymentStatus || order.paymentMethod || '-'}</td>
                                  <td className="px-4 py-3">{currency.format(Number(order.totalAmount || 0))}</td>
                                  <td className="px-4 py-3">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                </tr>
                              ))}
                            </AdminTable>
                          </AdminPanel>
                        )}
                        {customerActiveSection === 'loyalty' && (
                          <AdminPanel title="Lịch sử điểm thưởng">
                            <AdminTable headers={['Loại', 'Điểm', 'Số dư trước/sau', 'Lý do', 'Thời gian']}>
                              {customerLoyaltyHistory.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có lịch sử điểm.</td></tr> : customerLoyaltyHistory.map((item) => (
                                <tr key={item.id}>
                                  <td className="px-4 py-3">{item.type}</td>
                                  <td className="px-4 py-3 font-semibold">{item.metadata?.delta ?? item.points}</td>
                                  <td className="px-4 py-3">{item.balanceBefore} / {item.balanceAfter}</td>
                                  <td className="px-4 py-3 text-sm text-slate-600">{item.reason}</td>
                                  <td className="px-4 py-3">{item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                </tr>
                              ))}
                            </AdminTable>
                          </AdminPanel>
                        )}
                        {(customerActiveSection === 'notes' || customerActiveSection === 'audit' || customerActiveSection === 'summary') && (
                          <div className="grid gap-5 xl:grid-cols-2">
                            <AdminPanel title="Ghi chú CSKH" action={canManageCustomerProfile ? <button type="button" onClick={() => void addCustomerNote()} className="rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800">Thêm ghi chú</button> : undefined}>
                              {canManageCustomerProfile && <textarea value={customerNoteDraft} onChange={(event) => setCustomerNoteDraft(event.target.value)} placeholder="Ghi lại ngữ cảnh CSKH, lưu ý xử lý, cam kết hỗ trợ..." className="mb-4 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" />}
                              <div className="space-y-3">
                                {customerNotes.length === 0 ? <EmptyState text="Chưa có ghi chú CSKH." /> : customerNotes.map((note) => (
                                  <div key={note.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{note.authorName || note.authorId || 'Admin'}</span>
                                      <span className="text-xs text-slate-500">{note.createdAt ? new Date(note.createdAt).toLocaleString('vi-VN') : '-'}</span>
                                    </div>
                                    <div className="mt-2 text-sm leading-6 text-slate-700">{note.content}</div>
                                  </div>
                                ))}
                              </div>
                            </AdminPanel>
                            <AdminPanel title="Nhật ký thay đổi quyền và tác động">
                              <div className="space-y-3">
                                {customerAuditLogs.length === 0 ? <EmptyState text="Chưa có nhật ký liên quan khách hàng này." /> : customerAuditLogs.map((log) => (
                                  <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="font-semibold text-slate-900">{log.eventType}</span>
                                      <span className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</span>
                                    </div>
                                    <div className="mt-2 text-xs text-slate-600">{JSON.stringify(log.metadata || {})}</div>
                                  </div>
                                ))}
                              </div>
                            </AdminPanel>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
    </>
  );
}
