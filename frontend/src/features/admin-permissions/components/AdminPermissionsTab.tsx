import React from 'react';
import { Edit2, KeyRound, Plus, X } from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable, EmptyState, Input, MetricCard, MiniMetric, Select } from '../../admin-shell/components/AdminDashboardParts';

type AdminPermissionsTabProps = Record<string, any>;

const orderStatusLabels: Record<string, string> = {
  PENDING: 'Chờ xử lý',
  PROCESSING: 'Đang đóng gói',
  SHIPPED: 'Đang giao',
  COMPLETED: 'Đã giao',
  CANCELLED: 'Đã hủy',
  REFUNDED: 'Đã hoàn tiền',
  PAYMENT_FAILED: 'Thanh toán thất bại',
  RETURNING: 'Đang hoàn hàng',
  RETURNED: 'Đã nhận hàng hoàn',
};

const paymentStatusLabels: Record<string, string> = {
  UNPAID: 'Chưa thanh toán',
  PAID: 'Đã thanh toán',
  FAILED: 'Thanh toán thất bại',
  PENDING: 'Đang chờ thanh toán',
  EXPIRED: 'Đã hết hạn',
  REFUNDED: 'Đã hoàn tiền',
  PENDING_PAYMENT: 'Chờ thanh toán',
};

const paymentMethodLabels: Record<string, string> = {
  COD: 'COD',
  MOMO: 'MoMo',
  ZALOPAY: 'ZaloPay',
  SEPAY: 'SePay',
  VNPAY: 'VNPAY',
};

const moduleLabels: Record<string, string> = {
  overview: 'Tổng quan hệ thống',
  product: 'Quản lý sản phẩm',
  category: 'Quản lý danh mục',
  brand: 'Quản lý thương hiệu',
  order: 'Quản lý đơn hàng',
  voucher: 'Quản lý khuyến mãi / Voucher',
  customer: 'Quản lý khách hàng',
  inventory: 'Quản lý kho / Tồn kho',
  review: 'Quản lý đánh giá',
  content: 'Quản lý nội dung / truyền thông',
  audit: 'Nhật ký bảo mật',
  sys: 'Cấu hình hệ thống',
  supplier: 'Quản lý nhà cung cấp',
  payment_method: 'Phương thức thanh toán',
  used_product: 'Thu mua máy cũ',
  service: 'Quản lý dịch vụ đi kèm',
  flash_sale: 'Quản lý flash sale',
};

const permissionLabels: Record<string, { title: string; description: string }> = {
  'overview:read': {
    title: 'Xem tổng quan',
    description: 'Xem các thông số tổng quan và biểu đồ thống kê kinh doanh',
  },
  'product:read': {
    title: 'Xem sản phẩm',
    description: 'Xem danh sách và chi tiết thông tin sản phẩm',
  },
  'product:create': {
    title: 'Thêm sản phẩm',
    description: 'Tạo mới sản phẩm và các phiên bản sản phẩm',
  },
  'product:update': {
    title: 'Cập nhật sản phẩm',
    description: 'Sửa thông tin sản phẩm, cập nhật giá bán, hình ảnh',
  },
  'product:delete': {
    title: 'Xóa / Ẩn sản phẩm',
    description: 'Ẩn sản phẩm khỏi cửa hàng hoặc chuyển vào lưu trữ',
  },
  'category:read': {
    title: 'Xem danh mục',
    description: 'Xem cấu trúc và danh sách danh mục sản phẩm',
  },
  'category:create': {
    title: 'Thêm danh mục',
    description: 'Tạo mới danh mục sản phẩm',
  },
  'category:update': {
    title: 'Cập nhật danh mục',
    description: 'Thay đổi thông tin, vị trí hoặc cấp cha-con của danh mục',
  },
  'category:delete': {
    title: 'Xóa / Ẩn danh mục',
    description: 'Xóa danh mục không hoạt động hoặc ẩn danh mục',
  },
  'brand:read': {
    title: 'Xem thương hiệu',
    description: 'Xem danh sách các thương hiệu/nhãn hàng',
  },
  'brand:create': {
    title: 'Thêm thương hiệu',
    description: 'Tạo mới thương hiệu',
  },
  'brand:update': {
    title: 'Cập nhật thương hiệu',
    description: 'Thay đổi thông tin thương hiệu',
  },
  'brand:delete': {
    title: 'Xóa / Ẩn thương hiệu',
    description: 'Xóa thương hiệu không hoạt động hoặc ẩn thương hiệu',
  },
  'order:read': {
    title: 'Xem đơn hàng',
    description: 'Xem danh sách đơn hàng và trạng thái chi tiết',
  },
  'order:update': {
    title: 'Cập nhật đơn hàng',
    description: 'Xác nhận đơn, chuyển trạng thái giao hàng, xử lý hủy/hoàn đơn',
  },
  'voucher:read': {
    title: 'Xem khuyến mãi',
    description: 'Xem danh sách mã giảm giá, chương trình khuyến mãi',
  },
  'voucher:create': {
    title: 'Thêm khuyến mãi',
    description: 'Tạo mới mã giảm giá, thiết lập điều kiện khuyến mãi',
  },
  'voucher:update': {
    title: 'Cập nhật khuyến mãi',
    description: 'Thay đổi thông tin hoặc sửa điều kiện của voucher',
  },
  'voucher:delete': {
    title: 'Tắt khuyến mãi',
    description: 'Tạm dừng hoặc hủy kích hoạt mã giảm giá trước hạn',
  },
  'customer:read': {
    title: 'Xem khách hàng',
    description: 'Xem danh sách tài khoản khách hàng và hồ sơ khách hàng',
  },
  'customer:update': {
    title: 'Cập nhật thông tin khách hàng',
    description: 'Thay đổi nhãn (tag), ghi chú hỗ trợ chăm sóc khách hàng',
  },
  'customer:loyalty_adjust': {
    title: 'Điều chỉnh điểm tích lũy',
    description: 'Cộng hoặc trừ điểm thưởng thủ công cho khách hàng',
  },
  'customer:issue_voucher': {
    title: 'Tặng voucher riêng',
    description: 'Gửi mã giảm giá tri ân riêng cho từng khách hàng',
  },
  'inventory:read': {
    title: 'Xem kho hàng',
    description: 'Xem lượng tồn kho thực tế, lịch sử xuất nhập kho',
  },
  'inventory:adjust': {
    title: 'Điều chỉnh tồn kho',
    description: 'Điều chỉnh số lượng tồn kho thủ công hoặc tạo yêu cầu điều chỉnh',
  },
  'inventory:approve': {
    title: 'Duyệt phiếu kho',
    description: 'Duyệt các phiếu nhập/xuất hoặc phiếu điều chỉnh tồn kho',
  },
  'inventory:count': {
    title: 'Kiểm kê kho',
    description: 'Tạo và đối soát kết quả kiểm kê kho định kỳ',
  },
  'inventory:reserve': {
    title: 'Quản lý giữ hàng',
    description: 'Giữ trước số lượng tồn kho phục vụ đơn hàng chờ thanh toán',
  },
  'review:read': {
    title: 'Xem đánh giá',
    description: 'Xem các nhận xét, đánh giá sản phẩm của khách hàng',
  },
  'review:update': {
    title: 'Duyệt đánh giá',
    description: 'Duyệt hiển thị hoặc ẩn các đánh giá không phù hợp',
  },
  'review:delete': {
    title: 'Xóa đánh giá',
    description: 'Xóa vĩnh viễn đánh giá/bình luận của khách hàng',
  },
  'content:read': {
    title: 'Xem nội dung',
    description: 'Xem thông tin các trang tĩnh, banner, bài viết',
  },
  'content:create': {
    title: 'Tạo nội dung',
    description: 'Đăng bài viết mới, tải lên video giới thiệu hoặc tạo banner quảng cáo',
  },
  'content:update': {
    title: 'Sửa nội dung',
    description: 'Thay đổi banner, chỉnh sửa bài viết tin tức và nội dung giới thiệu',
  },
  'content:delete': {
    title: 'Xóa nội dung',
    description: 'Xóa banner hoặc ẩn bài viết tin tức',
  },
  'audit:read': {
    title: 'Xem nhật ký bảo mật',
    description: 'Xem lịch sử thao tác của các tài khoản nhân viên khác',
  },
  'sys:manage_users': {
    title: 'Quản lý nhân viên',
    description: 'Tạo tài khoản nhân viên, đổi trạng thái hoạt động tài khoản',
  },
  'sys:manage_roles': {
    title: 'Quản lý phân quyền',
    description: 'Chỉnh sửa ma trận quyền hạn cho các vai trò trong hệ thống',
  },
  'supplier:read': {
    title: 'Xem nhà cung cấp',
    description: 'Xem danh sách và chi tiết thông tin nhà cung cấp hàng hóa',
  },
  'supplier:create': {
    title: 'Thêm nhà cung cấp',
    description: 'Tạo mới hồ sơ nhà cung cấp',
  },
  'supplier:update': {
    title: 'Cập nhật nhà cung cấp',
    description: 'Cập nhật thông tin liên hệ, hợp đồng nhà cung cấp',
  },
  'supplier:delete': {
    title: 'Xóa nhà cung cấp',
    description: 'Ngừng hợp tác hoặc ẩn thông tin nhà cung cấp',
  },
  'payment_method:read': {
    title: 'Xem cấu hình thanh toán',
    description: 'Xem thông tin kết nối các cổng thanh toán online (MoMo, ZaloPay, SePay...)',
  },
  'payment_method:update': {
    title: 'Cấu hình thanh toán',
    description: 'Bật/tắt hoặc cấu hình tham số, trạng thái bảo trì cổng thanh toán',
  },
  'used_product:read': {
    title: 'Xem yêu cầu thu mua',
    description: 'Xem danh sách khách hàng đăng ký bán lại máy cũ',
  },
  'used_product:manage': {
    title: 'Thẩm định máy cũ',
    description: 'Nhận máy, chạy kiểm tra và định giá sơ bộ thiết bị cũ',
  },
  'used_product:approve': {
    title: 'Duyệt thu mua máy cũ',
    description: 'Duyệt quyết định thu mua và xác nhận mức giá giao dịch cuối cùng',
  },
};

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
    setStaffForm,
    setStaffPermissionDraft,
    setStaffPermissionDenyDraft,
    setStaffPermissionEditor,
    staffBasePermissionCodes,
    staffForm,
    staffPermissionDraft,
    staffPermissionDenyDraft,
    staffPermissionEditor,
    staffUsers,
    updateUserAccess,
    usePermission,
    vouchers,
  } = props;
  const canAdjustCustomerLoyalty = usePermission('customer:loyalty_adjust');
  const canIssueCustomerVoucher = usePermission('customer:issue_voucher');
  return (
    <>
      <AdminPanel title="Phân quyền từng nhân viên" action={<KeyRound className="h-5 w-5 text-red-600" />}>
                <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                  Staff Admin chỉ là loại tài khoản nhân viên. Mỗi nhân viên mặc định chưa có quyền nghiệp vụ; Super Admin cấp quyền riêng bằng nút "Chỉnh quyền" trên từng tài khoản.
                </div>
                {canManageCustomerAccess && (
                  <div className="mb-6 grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
                    <form onSubmit={createStaffAccount} autoComplete="off" className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-3">
                        <div className="text-sm font-black text-slate-900">Tạo tài khoản nhân viên</div>
                        <div className="mt-1 text-xs font-medium text-slate-500">Nhân viên mới chưa có quyền nghiệp vụ. Super Admin cấp quyền theo đúng chức năng của từng tài khoản sau khi tạo.</div>
                      </div>
                      <div className="grid gap-3">
                        <Input label="Họ tên nhân viên" name="new-staff-full-name" autoComplete="off" value={staffForm.fullName} required onChange={(value) => setStaffForm({ ...staffForm, fullName: value })} />
                        <Input label="Email đăng nhập" name="new-staff-email" autoComplete="off" type="email" value={staffForm.email} required onChange={(value) => setStaffForm({ ...staffForm, email: value })} />
                        <Input label="Mật khẩu tạm" name="new-staff-password" autoComplete="new-password" type="password" value={staffForm.password} required onChange={(value) => setStaffForm({ ...staffForm, password: value })} />
                        <Input label="Số điện thoại" name="new-staff-phone" autoComplete="off" value={staffForm.phone} onChange={(value) => setStaffForm({ ...staffForm, phone: value })} />
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
                          <div className="mt-1 text-xs font-medium text-slate-500">Mỗi Staff Admin dùng bộ quyền riêng được cấp trực tiếp trên tài khoản.</div>
                        </div>
                        <AdminBadge tone="blue">{staffBasePermissionCodes.length} quyền chung</AdminBadge>
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
                                        <option value="ACTIVE">Đang hoạt động</option>
                                        <option value="SUSPENDED">Tạm khóa</option>
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
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="text-sm font-bold text-slate-900">Danh mục quyền có thể cấp riêng</div>
                  <div className="mt-1 text-xs font-medium text-slate-500">
                    Hệ thống có {permissions.length} quyền thuộc {Object.keys(permissionsByModule).length} nhóm chức năng. Các quyền này chỉ có hiệu lực với nhân viên khi Super Admin cấp trực tiếp cho tài khoản đó.
                  </div>
                </div>
                <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 text-sm font-bold text-slate-900">Nhật ký đổi quyền gần đây</div>
                  <div className="space-y-2">
                    {auditLogs
                      .filter((log: any) => ['admin_user_access_updated', 'admin_role_permissions_updated'].includes(log.eventType))
                      .slice(0, 8)
                      .map((log: any) => (
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
                      <p className="mt-1 text-sm text-slate-500">{staffPermissionEditor.fullName || staffPermissionEditor.email} chỉ có các quyền được cấp riêng trong màn hình này.</p>
                    </div>
                    <button type="button" onClick={() => setStaffPermissionEditor(null)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="max-h-[70vh] overflow-y-auto p-5">
                    <div className="mb-4 grid gap-3 md:grid-cols-3">
                      <MiniMetric label="Quyền chung" value={staffBasePermissionCodes.length} helper="Luôn là 0 với Staff Admin" />
                      <MiniMetric label="Quyền riêng" value={staffPermissionDraft.length} helper="Cấp trực tiếp cho nhân viên này" />
                      <MiniMetric label="Quyền từ chối" value={staffPermissionDenyDraft.length} helper="Luôn ưu tiên cao nhất" />
                      <MiniMetric label="Tổng hiệu lực" value={[...new Set([...staffBasePermissionCodes, ...staffPermissionDraft])].filter((code) => !staffPermissionDenyDraft.includes(code)).length} helper="Sau khi loại quyền từ chối" />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      {Object.entries(permissionsByModule).map(([moduleName, modulePermissions]) => (
                        <div key={moduleName} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                          <div className="mb-3 text-sm font-black uppercase text-slate-700">
                            {moduleLabels[moduleName] || moduleName}
                          </div>
                          <div className="space-y-2">
                            {(modulePermissions as any[]).map((permission) => {
                              const baseLocked = staffBasePermissionCodes.includes(permission.code);
                              const denied = staffPermissionDenyDraft.includes(permission.code);
                              const checked = !denied && (baseLocked || staffPermissionDraft.includes(permission.code));
                              const labelData = permissionLabels[permission.code];
                              return (
                                <label key={permission.code} className={`flex items-start gap-3 rounded-md border px-3 py-2.5 transition-all hover:bg-slate-50/50 ${baseLocked ? 'border-slate-200 bg-white/70 opacity-75' : 'border-slate-200 bg-white'}`}>
                                  <div className="mt-0.5 flex shrink-0 flex-col gap-2">
                                    <label className="flex items-center gap-1 text-[11px] font-bold text-emerald-700">
                                      <input type="checkbox" checked={checked} disabled={baseLocked || denied} onChange={(event) => setStaffPermissionDraft((prev) => event.target.checked ? [...new Set([...prev, permission.code])] : prev.filter((code) => code !== permission.code))} /> Cấp
                                    </label>
                                    <label className="flex items-center gap-1 text-[11px] font-bold text-red-700">
                                      <input type="checkbox" checked={denied} onChange={(event) => {
                                        setStaffPermissionDenyDraft((prev) => event.target.checked ? [...new Set([...prev, permission.code])] : prev.filter((code) => code !== permission.code));
                                        if (event.target.checked) setStaffPermissionDraft((prev) => prev.filter((code) => code !== permission.code));
                                      }} /> Từ chối
                                    </label>
                                  </div>
                                  <span className="flex-1">
                                    <span className="block text-sm font-bold text-slate-900">
                                      {labelData?.title || permission.code}
                                    </span>
                                    <span className="block text-xs text-slate-500 mt-0.5">
                                      {baseLocked ? 'Quyền mặc định của nhân viên' : (labelData?.description || permission.description || permission.module)}
                                    </span>
                                    <span className="inline-block text-[10px] font-mono bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded mt-1.5 select-all">
                                      {permission.code}
                                    </span>
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
                        {canAdjustCustomerLoyalty && (
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
                        {canIssueCustomerVoucher && (
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
                                    <td className="px-4 py-3">{orderStatusLabels[order.status] || order.status}</td>
                                    <td className="px-4 py-3">{paymentStatusLabels[order.paymentStatus || ''] || paymentMethodLabels[order.paymentMethod || ''] || order.paymentStatus || order.paymentMethod || '-'}</td>
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
                                  <td className="px-4 py-3">{orderStatusLabels[order.status] || order.status}</td>
                                  <td className="px-4 py-3">{paymentStatusLabels[order.paymentStatus || ''] || paymentMethodLabels[order.paymentMethod || ''] || order.paymentStatus || order.paymentMethod || '-'}</td>
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
