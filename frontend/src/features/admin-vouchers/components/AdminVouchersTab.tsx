import React from 'react';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, CollapsibleSection, Input, RowActions, SearchBox, Select, SubmitButtons, VoucherConditions } from '../../admin-shell/components/AdminDashboardParts';
import { voucherCampaignOptions, voucherAudienceOptions, voucherTierOptions } from '../../admin-shell/pages/AdminDashboardConfig';
import { adminVouchersApi } from '../services/adminVouchersApi';

type AdminVouchersTabProps = Record<string, any>;

export default function AdminVouchersTab(props: AdminVouchersTabProps) {
  const {
    confirmDelete,
    currency,
    editVoucher,
    editingVoucherId,
    filteredVouchers,
    handleVoucherSubmit,
    query,
    resetVoucherForm,
    setQuery,
    setVoucherForm,
    voucherCloseSignal,
    voucherForm,
    usePermission,
  } = props;
  const canCreateVoucher = usePermission('voucher:create');
  const canUpdateVoucher = usePermission('voucher:update');
  const canDeleteVoucher = usePermission('voucher:delete');

  return (
    <AdminPanel 
      title="Quản lý voucher" 
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã voucher, loại, trạng thái" />}
    >
      {(canCreateVoucher || canUpdateVoucher) && <CollapsibleSection title={editingVoucherId ? 'Đang chỉnh sửa voucher' : 'Thêm voucher mới'} description="Mở khi cần thiết lập mã giảm giá, điều kiện đơn tối thiểu và giới hạn sử dụng." defaultOpen={false} forceOpen={Boolean(editingVoucherId)} forceOpenKey={editingVoucherId} closeSignal={voucherCloseSignal} onClose={resetVoucherForm}>
        <form onSubmit={handleVoucherSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-6">
          <Input label="Mã voucher" value={voucherForm.code} required onChange={(value) => setVoucherForm({ ...voucherForm, code: value.toUpperCase() })} />
          <Select label="Mục tiêu" value={voucherForm.campaignType} onChange={(value) => setVoucherForm({ ...voucherForm, campaignType: value })} options={voucherCampaignOptions} />
          <Select label="Đối tượng" value={voucherForm.audienceType} onChange={(value) => setVoucherForm({ ...voucherForm, audienceType: value, firstOrderOnly: value === 'NEW_CUSTOMER' || voucherForm.firstOrderOnly, hiddenCode: value === 'HIDDEN' || voucherForm.hiddenCode, abandonedCartOnly: value === 'ABANDONED_CART' || voucherForm.abandonedCartOnly })} options={voucherAudienceOptions} />
          <Select label="Loại giảm" value={voucherForm.discountType} onChange={(value) => setVoucherForm({ ...voucherForm, discountType: value })} options={[['FIXED', 'Số tiền'], ['PERCENT', 'Phần trăm']]} />
          <Input label="Giá trị" type="number" value={voucherForm.discountAmount} onChange={(value) => setVoucherForm({ ...voucherForm, discountAmount: Number(value) })} />
          <Input label="Đơn tối thiểu" type="number" value={voucherForm.minOrderValue} onChange={(value) => setVoucherForm({ ...voucherForm, minOrderValue: Number(value) })} />
          <Input label="Giảm tối đa" type="number" value={voucherForm.maxDiscount} onChange={(value) => setVoucherForm({ ...voucherForm, maxDiscount: Number(value) })} />
          <Input label="Tổng lượt dùng" type="number" value={voucherForm.usageLimit} onChange={(value) => setVoucherForm({ ...voucherForm, usageLimit: Number(value) })} />
          <Input label="Ngân sách tối đa" type="number" value={voucherForm.totalBudgetCap} onChange={(value) => setVoucherForm({ ...voucherForm, totalBudgetCap: Number(value) })} />
          <Input label="Lượt/user" type="number" value={voucherForm.perUserLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perUserLimit: Number(value) })} />
          <Input label="Lượt/thiết bị" type="number" value={voucherForm.perDeviceLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perDeviceLimit: Number(value) })} />
          <Input label="Lượt/IP" type="number" value={voucherForm.perIpLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perIpLimit: Number(value) })} />
          <Input label="Bắt đầu" type="datetime-local" value={voucherForm.startsAt} onChange={(value) => setVoucherForm({ ...voucherForm, startsAt: value })} />
          <Input label="Kết thúc" type="datetime-local" value={voucherForm.endsAt} onChange={(value) => setVoucherForm({ ...voucherForm, endsAt: value })} />
          <Input label="Hạn sau khi lưu (ngày)" type="number" value={voucherForm.validityDaysAfterClaim} onChange={(value) => setVoucherForm({ ...voucherForm, validityDaysAfterClaim: Number(value) })} />
          <Input label="User đăng ký sau" type="datetime-local" value={voucherForm.eligibleUserRegisteredAfter} onChange={(value) => setVoucherForm({ ...voucherForm, eligibleUserRegisteredAfter: value })} />
          <Input label="User ID riêng" value={voucherForm.assignedUserId} onChange={(value) => setVoucherForm({ ...voucherForm, assignedUserId: value, audienceType: value ? 'SPECIFIC_USER' : voucherForm.audienceType })} />
          <Select label="Trạng thái" value={voucherForm.status} onChange={(value) => setVoucherForm({ ...voucherForm, status: value })} options={[['ACTIVE', 'Đang chạy'], ['INACTIVE', 'Tạm dừng'], ['EXPIRED', 'Hết hạn']]} />
          <Select label="Hoàn voucher" value={voucherForm.refundPolicy} onChange={(value) => setVoucherForm({ ...voucherForm, refundPolicy: value })} options={[['NEVER', 'Không hoàn'], ['SHOP_FAULT_ONLY', 'Hoàn khi lỗi shop'], ['ALWAYS', 'Luôn hoàn khi hủy']]} />
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
            <div className="mb-2 text-xs font-bold text-slate-500">Hạng thành viên áp dụng</div>
            <div className="flex flex-wrap gap-2">
              {voucherTierOptions.map((tier) => (
                <label key={tier} className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-bold ${voucherForm.eligibleTiers.includes(tier) ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600'}`}>
                  <input type="checkbox" checked={voucherForm.eligibleTiers.includes(tier)} onChange={(event) => setVoucherForm({ ...voucherForm, eligibleTiers: event.target.checked ? [...voucherForm.eligibleTiers, tier] : voucherForm.eligibleTiers.filter((item: string) => item !== tier), audienceType: event.target.checked ? 'MEMBER_TIER' : voucherForm.audienceType })} className="h-4 w-4 accent-red-600" />
                  {tier}
                </label>
              ))}
            </div>
          </div>
          <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 md:col-span-3 sm:grid-cols-3">
            <Checkbox label="Cộng dồn" checked={voucherForm.stackable} onChange={(checked) => setVoucherForm({ ...voucherForm, stackable: checked })} />
            <Checkbox label="Đơn đầu tiên" checked={voucherForm.firstOrderOnly} onChange={(checked) => setVoucherForm({ ...voucherForm, firstOrderOnly: checked })} />
            <Checkbox label="Mã ẩn" checked={voucherForm.hiddenCode} onChange={(checked) => setVoucherForm({ ...voucherForm, hiddenCode: checked })} />
            <Checkbox label="Giỏ bỏ quên" checked={voucherForm.abandonedCartOnly} onChange={(checked) => setVoucherForm({ ...voucherForm, abandonedCartOnly: checked })} />
          </div>
          <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Product IDs áp dụng, cách nhau bằng dấu phẩy" value={voucherForm.includeProductIds} onChange={(event) => setVoucherForm({ ...voucherForm, includeProductIds: event.target.value })} />
          <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Product IDs loại trừ" value={voucherForm.excludeProductIds} onChange={(event) => setVoucherForm({ ...voucherForm, excludeProductIds: event.target.value })} />
          <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Category IDs áp dụng" value={voucherForm.includeCategoryIds} onChange={(event) => setVoucherForm({ ...voucherForm, includeCategoryIds: event.target.value })} />
          <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Category IDs loại trừ" value={voucherForm.excludeCategoryIds} onChange={(event) => setVoucherForm({ ...voucherForm, excludeCategoryIds: event.target.value })} />
          <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-5" placeholder="Ghi chú nội bộ: lý do tạo, khách hàng được cấp, kênh gửi..." value={voucherForm.internalNote} onChange={(event) => setVoucherForm({ ...voucherForm, internalNote: event.target.value })} />
          <SubmitButtons editing={Boolean(editingVoucherId)} onCancel={resetVoucherForm} />
        </form>
      </CollapsibleSection>}
      <AdminTable headers={['Mã', 'Chiến dịch', 'Đối tượng', 'Giá trị', 'Điều kiện', 'Lượt dùng', 'Trạng thái', 'Thao tác']}>
        {filteredVouchers.map((voucher: any) => (
          <tr key={voucher.id}>
            <td className="px-4 py-3"><div className="font-mono font-bold text-slate-900">{voucher.code}</div>{voucher.hiddenCode && <div className="mt-1 text-xs font-bold text-amber-600">Mã ẩn</div>}</td>
            <td className="px-4 py-3">{voucherCampaignOptions.find(([value]) => value === voucher.campaignType)?.[1] || voucher.campaignType || '-'}</td>
            <td className="px-4 py-3">{voucherAudienceOptions.find(([value]) => value === voucher.audienceType)?.[1] || voucher.audienceType || '-'}</td>
            <td className="px-4 py-3 font-semibold">{voucher.discountType === 'PERCENT' ? `${voucher.discountAmount}%` : currency.format(Number(voucher.discountAmount || 0))}</td>
            <td className="px-4 py-3"><VoucherConditions voucher={voucher} /></td>
            <td className="px-4 py-3">{voucher.usedCount || 0}/{voucher.usageLimit || '∞'}<div className="text-xs text-slate-500">/user: {voucher.perUserLimit || '∞'}</div>{voucher.totalBudgetCap ? <div className="text-xs text-slate-500">NS: {currency.format(Number(voucher.totalDiscountUsed || 0))}/{currency.format(Number(voucher.totalBudgetCap || 0))}</div> : null}</td>
            <td className="px-4 py-3"><AdminBadge tone={voucher.status === 'ACTIVE' ? 'green' : 'slate'}>{voucher.status === 'ACTIVE' ? 'Đang chạy' : 'Tạm dừng'}</AdminBadge></td>
            <td className="px-4 py-3"><RowActions onEdit={canUpdateVoucher ? () => editVoucher(voucher) : undefined} onDelete={canDeleteVoucher ? () => confirmDelete(voucher.code, () => adminVouchersApi.adminDeleteVoucher(voucher.id)) : undefined} /></td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
