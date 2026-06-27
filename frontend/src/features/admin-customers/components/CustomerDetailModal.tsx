import { X } from 'lucide-react';

type CustomerSection = 'summary' | 'orders' | 'loyalty' | 'notes' | 'audit';

type CustomerDetailModalProps = {
  customer: any | null;
  busy: boolean;
  error: string;
  activeSection: CustomerSection;
  orders: any[];
  loyaltyHistory: any[];
  notes: any[];
  auditLogs: any[];
  profileDraft: { fullName: string; phone: string; tier: string; walletStatus: string };
  pointDelta: string;
  pointReason: string;
  canAdjustPoints: boolean;
  canUpdateProfile: boolean;
  onProfileDraftChange: (value: { fullName: string; phone: string; tier: string; walletStatus: string }) => void;
  onSaveProfile: () => void;
  onPointDeltaChange: (value: string) => void;
  onPointReasonChange: (value: string) => void;
  onAdjustPoints: () => void;
  onSectionChange: (section: CustomerSection) => void;
  onClose: () => void;
  currency: Intl.NumberFormat;
};

function formatDate(value: unknown) {
  if (!value) return '-';
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('vi-VN');
}

function EmptyRow({ colSpan, text }: { colSpan: number; text: string }) {
  return <tr><td colSpan={colSpan} className="px-4 py-8 text-center text-sm text-slate-500">{text}</td></tr>;
}

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50"><tr>{headers.map((header) => <th key={header} className="px-4 py-3 text-left text-xs font-bold uppercase text-slate-500">{header}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100 bg-white">{children}</tbody>
      </table>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="text-xs font-bold uppercase text-slate-500">{label}</div><div className="mt-2 text-xl font-bold text-slate-950">{value}</div></div>;
}

export default function CustomerDetailModal(props: CustomerDetailModalProps) {
  const {
    customer,
    busy,
    error,
    activeSection,
    orders,
    loyaltyHistory,
    notes,
    auditLogs,
    profileDraft,
    pointDelta,
    pointReason,
    canAdjustPoints,
    canUpdateProfile,
    onProfileDraftChange,
    onSaveProfile,
    onPointDeltaChange,
    onPointReasonChange,
    onAdjustPoints,
    onSectionChange,
    onClose,
    currency,
  } = props;
  const tabs: [CustomerSection, string][] = [['summary', 'Tổng quan'], ['orders', 'Đơn hàng'], ['loyalty', 'Điểm thưởng'], ['notes', 'Ghi chú CSKH'], ['audit', 'Nhật ký']];
  const deltaValue = Number(pointDelta || 0);
  const currentPoints = Number(customer?.points || 0);
  const balanceAfter = currentPoints + (Number.isFinite(deltaValue) ? deltaValue : 0);
  const canSubmitAdjustment = canAdjustPoints && Boolean(customer?.id) && Number.isInteger(deltaValue) && Boolean(deltaValue) && pointReason.trim().length >= 3 && balanceAfter >= 0;
  const needsAdjustmentConfirm = deltaValue < 0 || Math.abs(deltaValue) >= 1000;

  function submitPointAdjustment() {
    if (needsAdjustmentConfirm && !window.confirm(`Xác nhận điều chỉnh ${deltaValue} điểm cho khách hàng này?`)) return;
    onAdjustPoints();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div><h3 className="text-lg font-bold text-slate-950">Hồ sơ khách hàng</h3><p className="mt-1 text-sm text-slate-500">{customer?.fullName || customer?.email || 'Đang tải dữ liệu khách hàng...'}</p></div>
          <button type="button" onClick={onClose} title="Đóng" className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"><X className="h-4 w-4" /></button>
        </div>

        <div className="max-h-[calc(100vh-120px)] overflow-y-auto p-5">
          {busy && <div className="py-12 text-center text-sm font-semibold text-slate-500">Đang tải thông tin khách hàng...</div>}
          {!busy && error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
          {!busy && !error && customer && (
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2">
                {tabs.map(([id, label]) => <button key={id} type="button" onClick={() => onSectionChange(id)} className={`rounded-md px-3 py-2 text-sm font-bold ${activeSection === id ? 'bg-slate-950 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50'}`}>{label}</button>)}
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Tổng chi tiêu" value={currency.format(Number(customer.totalSpent || 0))} />
                <Metric label="Điểm hiện có" value={String(customer.points || 0)} />
                <Metric label="Số đơn" value={String(customer.orderCount || 0)} />
                <Metric label="Voucher đã giữ" value={String(customer.voucherCount || 0)} />
              </div>

              {activeSection === 'summary' && (
                <div className="grid gap-5 lg:grid-cols-2">
                  <section className="rounded-lg border border-slate-200 p-4">
                    <h4 className="text-sm font-bold text-slate-900">Thông tin tài khoản</h4>
                    <dl className="mt-4 grid gap-4 md:grid-cols-2">
                      {[['Họ và tên', customer.fullName], ['Email', customer.email], ['Điện thoại', customer.phone], ['Vai trò', customer.role], ['Trạng thái', customer.status], ['Hạng thành viên', customer.tier], ['Trạng thái ví điểm', customer.walletStatus], ['Ngày tạo', formatDate(customer.createdAt)], ['Cập nhật gần nhất', formatDate(customer.updatedAt)], ['Tổng điểm đã nhận', customer.totalPointsEarned ?? 0], ['Tổng điểm đã dùng', customer.totalPointsUsed ?? 0], ['Số ghi chú', customer.noteCount ?? 0]].map(([label, value]) => <div key={String(label)}><dt className="text-xs font-bold uppercase text-slate-400">{label}</dt><dd className="mt-1 break-words text-sm font-semibold text-slate-800">{value === null || value === undefined || value === '' ? '-' : String(value)}</dd></div>)}
                    </dl>
                  </section>
                  <section className="rounded-lg border border-slate-200 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="text-sm font-bold text-slate-900">Cập nhật thông tin cơ bản</h4>
                      {!canUpdateProfile && <span className="text-xs font-semibold text-slate-400">Chỉ xem</span>}
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <label className="block">
                        <span className="text-xs font-bold uppercase text-slate-500">Họ và tên</span>
                        <input disabled={!canUpdateProfile} value={profileDraft.fullName} onChange={(event) => onProfileDraftChange({ ...profileDraft, fullName: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-slate-500 disabled:bg-slate-100" />
                      </label>
                      <label className="block">
                        <span className="text-xs font-bold uppercase text-slate-500">Điện thoại</span>
                        <input disabled={!canUpdateProfile} value={profileDraft.phone} onChange={(event) => onProfileDraftChange({ ...profileDraft, phone: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-slate-500 disabled:bg-slate-100" />
                      </label>
                      <label className="block">
                        <span className="text-xs font-bold uppercase text-slate-500">Hạng thành viên</span>
                        <input disabled={!canUpdateProfile} value={profileDraft.tier} onChange={(event) => onProfileDraftChange({ ...profileDraft, tier: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-slate-500 disabled:bg-slate-100" />
                      </label>
                      <label className="block">
                        <span className="text-xs font-bold uppercase text-slate-500">Trạng thái ví điểm</span>
                        <select disabled={!canUpdateProfile} value={profileDraft.walletStatus} onChange={(event) => onProfileDraftChange({ ...profileDraft, walletStatus: event.target.value })} className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-500 disabled:bg-slate-100">
                          <option value="ACTIVE">ACTIVE</option>
                          <option value="SUSPENDED">SUSPENDED</option>
                          <option value="CLOSED">CLOSED</option>
                        </select>
                      </label>
                    </div>
                    {canUpdateProfile && (
                      <button type="button" disabled={!profileDraft.fullName.trim() || !profileDraft.tier.trim()} onClick={onSaveProfile} className="mt-4 rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300">Lưu thông tin</button>
                    )}
                  </section>
                  <section className="rounded-lg border border-slate-200 p-4 lg:col-span-2">
                    <h4 className="text-sm font-bold text-slate-900">Phân nhóm chăm sóc khách hàng</h4>
                    <div className="mt-3 flex flex-wrap gap-2">{Array.isArray(customer.tags) && customer.tags.length ? customer.tags.map((tag: string) => <span key={tag} className="rounded-full bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">{tag}</span>) : <span className="text-sm text-slate-500">Chưa có tag khách hàng.</span>}</div>
                    <div className="mt-5 text-xs font-bold uppercase text-slate-400">Ghi chú gần nhất</div>
                    <div className="mt-1 text-sm font-semibold text-slate-700">{formatDate(customer.lastNoteAt)}</div>
                  </section>
                </div>
              )}

              {activeSection === 'orders' && <Table headers={['Mã đơn', 'Trạng thái', 'Thanh toán', 'Tổng tiền', 'Điểm nhận/dùng', 'Ngày tạo']}>{orders.length === 0 ? <EmptyRow colSpan={6} text="Chưa có đơn hàng." /> : orders.map((order) => <tr key={order.id}><td className="px-4 py-3 font-mono text-xs">{order.orderCode}</td><td className="px-4 py-3">{order.status}</td><td className="px-4 py-3">{order.paymentStatus || order.paymentMethod || '-'}</td><td className="px-4 py-3 font-semibold">{currency.format(Number(order.totalAmount || 0))}</td><td className="px-4 py-3">{order.pointsEarned || 0} / {order.pointsUsed || 0}</td><td className="px-4 py-3">{formatDate(order.createdAt)}</td></tr>)}</Table>}

              {activeSection === 'loyalty' && (
                <div className="space-y-4">
                  {canAdjustPoints && (
                    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h4 className="text-sm font-bold text-amber-950">Điều chỉnh điểm thủ công</h4>
                          <p className="mt-1 text-xs leading-5 text-amber-800">Dùng khi điểm bị cộng/trừ sai. Nhập số dương để cộng điểm, số âm để trừ điểm; hệ thống sẽ lưu lịch sử và nhật ký quản trị.</p>
                        </div>
                        <div className="text-sm font-bold text-amber-950">Số dư sau điều chỉnh: {Number.isFinite(balanceAfter) ? balanceAfter : currentPoints}</div>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-[160px_1fr_auto]">
                        <label className="block">
                          <span className="text-xs font-bold uppercase text-amber-900">Số điểm</span>
                          <input type="number" step={1} value={pointDelta} onChange={(event) => onPointDeltaChange(event.target.value)} className="mt-1 h-10 w-full rounded-md border border-amber-200 bg-white px-3 text-sm outline-none focus:border-amber-500" />
                        </label>
                        <label className="block">
                          <span className="text-xs font-bold uppercase text-amber-900">Lý do</span>
                          <input value={pointReason} onChange={(event) => onPointReasonChange(event.target.value)} placeholder="Ví dụ: Hoàn điểm do đơn hàng bị tính sai" className="mt-1 h-10 w-full rounded-md border border-amber-200 bg-white px-3 text-sm outline-none focus:border-amber-500" />
                        </label>
                        <div className="flex items-end">
                          <button type="button" disabled={!canSubmitAdjustment} onClick={submitPointAdjustment} className="inline-flex h-10 items-center justify-center rounded-md bg-amber-600 px-4 text-sm font-bold text-white transition hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-amber-300">Cập nhật điểm</button>
                        </div>
                      </div>
                      {Number.isFinite(deltaValue) && !Number.isInteger(deltaValue) && <p className="mt-2 text-xs font-semibold text-red-600">Số điểm điều chỉnh phải là số nguyên.</p>}
                      {balanceAfter < 0 && <p className="mt-2 text-xs font-semibold text-red-600">Không thể trừ quá số điểm hiện có của khách hàng.</p>}
                    </section>
                  )}
                  <Table headers={['Loại', 'Điểm', 'Số dư trước', 'Số dư sau', 'Lý do', 'Người thao tác', 'Thời gian']}>{loyaltyHistory.length === 0 ? <EmptyRow colSpan={7} text="Chưa có lịch sử điểm thưởng." /> : loyaltyHistory.map((item) => {
                    const delta = Number(item.metadata?.delta ?? item.points ?? 0);
                    const isNegative = delta < 0;
                    const actor = item.actorName || item.actorEmail || (item.metadata?.source === 'admin_manual_adjustment' ? item.metadata?.adjustedBy : 'Hệ thống');
                    return <tr key={item.id}><td className="px-4 py-3">{item.type}</td><td className={`px-4 py-3 font-bold ${isNegative ? 'text-red-600' : 'text-emerald-700'}`}>{delta > 0 ? `+${delta}` : delta}</td><td className="px-4 py-3">{item.balanceBefore}</td><td className="px-4 py-3">{item.balanceAfter}</td><td className="px-4 py-3">{item.reason || '-'}</td><td className="px-4 py-3">{actor || '-'}</td><td className="px-4 py-3">{formatDate(item.createdAt)}</td></tr>;
                  })}</Table>
                </div>
              )}

              {activeSection === 'notes' && <div className="space-y-3">{notes.length === 0 ? <div className="rounded-lg border border-slate-200 p-8 text-center text-sm text-slate-500">Chưa có ghi chú CSKH.</div> : notes.map((note) => <div key={note.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="flex justify-between gap-3 text-xs text-slate-500"><strong>{note.authorName || 'Quản trị viên'}</strong><span>{formatDate(note.createdAt)}</span></div><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{note.content}</p></div>)}</div>}

              {activeSection === 'audit' && <div className="space-y-3">{auditLogs.length === 0 ? <div className="rounded-lg border border-slate-200 p-8 text-center text-sm text-slate-500">Chưa có nhật ký liên quan.</div> : auditLogs.map((log) => <div key={log.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="flex justify-between gap-3"><strong className="text-sm text-slate-900">{log.eventType}</strong><span className="text-xs text-slate-500">{formatDate(log.createdAt)}</span></div><pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(log.metadata || {}, null, 2)}</pre></div>)}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
