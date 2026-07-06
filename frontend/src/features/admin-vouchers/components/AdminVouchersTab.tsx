import React, { useMemo, useState } from 'react';
import { AdminBadge, AdminPanel, AdminTable, Checkbox, CollapsibleSection, Input, RowActions, SearchBox, Select, SubmitButtons, VoucherConditions } from '../../admin-shell/components/AdminDashboardParts';
import { voucherCampaignOptions, voucherAudienceOptions, voucherTierOptions } from '../../admin-shell/pages/AdminDashboardConfig';
import { adminVouchersApi } from '../services/adminVouchersApi';

const voucherStatusLabels: Record<string, string> = {
  ACTIVE: 'Đang chạy',
  INACTIVE: 'Tạm dừng',
  EXPIRED: 'Hết hạn',
};

const voucherStatusTones: Record<string, 'green' | 'slate' | 'red'> = {
  ACTIVE: 'green',
  INACTIVE: 'slate',
  EXPIRED: 'red',
};

type AdminVouchersTabProps = Record<string, any>;

type PickListItem = {
  id: string;
  label: string;
  helper?: string;
};

const voucherAudienceTabs = [
  { value: '', label: 'Tất cả' },
  { value: 'PUBLIC', label: 'Công khai' },
  { value: 'NEW_CUSTOMER', label: 'Khách mới' },
  { value: 'MEMBER_TIER', label: 'Theo hạng' },
  { value: 'SPECIFIC_USER', label: 'Cấp riêng' },
  { value: 'HIDDEN', label: 'Mã ẩn' },
  { value: 'ABANDONED_CART', label: 'Giỏ bỏ quên' },
];

const voucherPaymentOptions = [
  { id: 'COD', label: 'COD', helper: 'Thanh toán khi nhận hàng' },
  { id: 'MOMO', label: 'MoMo', helper: 'Ví MoMo' },
  { id: 'ZALOPAY', label: 'ZaloPay', helper: 'Ví ZaloPay' },
  { id: 'VNPAY', label: 'VNPAY', helper: 'Cổng VNPAY' },
  { id: 'CREDIT_CARD', label: 'Thẻ tín dụng', helper: 'Credit card' },
];

function MultiPickList({
  label,
  items,
  selected,
  onChange,
  emptyText,
}: {
  label: string;
  items: PickListItem[];
  selected: string[];
  onChange: (value: string[]) => void;
  emptyText: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-bold uppercase text-slate-500">{label}</div>
        <span className="text-xs font-semibold text-slate-400">{selected.length} đã chọn</span>
      </div>
      <div className="max-h-48 space-y-1 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="rounded-md bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">{emptyText}</div>
        ) : items.map((item) => {
          const checked = selected.includes(item.id);
          return (
            <label key={item.id} className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${checked ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-700'}`}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => onChange(event.target.checked ? [...new Set([...selected, item.id])] : selected.filter((id) => id !== item.id))}
                className="mt-0.5 h-4 w-4 accent-red-600"
              />
              <span className="min-w-0">
                <span className="block truncate font-bold">{item.label}</span>
                {item.helper && <span className="block truncate text-slate-500">{item.helper}</span>}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function normalizeText(value: unknown) {
  return String(value || '').trim().toLowerCase();
}

function getProductCategoryId(product: any) {
  return String(product.categoryId || product.category_id || product.category?.id || '');
}

function getProductBrandId(product: any) {
  return String(product.brandId || product.brand_id || product.brand?.id || '');
}

function getProductStatus(product: any) {
  return String(product.status || product.productStatus || '').toUpperCase();
}

function getCustomerLabel(customer: any) {
  return customer.fullName || customer.full_name || customer.name || customer.email || String(customer.id);
}

function PaymentMethodPicker({
  value,
  onChange,
}: {
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-bold uppercase text-slate-500">Phương thức thanh toán</div>
        <span className="text-xs font-semibold text-slate-400">{value.length} đã chọn</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {voucherPaymentOptions.map((item) => {
          const active = value.includes(item.id);
          const nextValue = active ? value.filter((id) => id !== item.id) : [...value, item.id];
          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(nextValue)}
              className={`flex min-h-16 items-start gap-2 rounded-md border px-3 py-2 text-left text-xs transition ${
                active ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] font-black ${active ? 'border-red-600 bg-red-600 text-white' : 'border-slate-400 bg-white text-transparent'}`}>
                ✓
              </span>
              <span className="min-w-0">
                <span className="block truncate font-bold">{item.label}</span>
                <span className="block truncate text-slate-500">{item.helper}</span>
              </span>
            </button>
          );
        })}
      </div>
      <div className="mt-2 text-xs font-semibold text-slate-500">Bỏ chọn tất cả nếu voucher không giới hạn phương thức thanh toán.</div>
    </div>
  );
}

export default function AdminVouchersTab(props: AdminVouchersTabProps) {
  const {
    brands,
    categories,
    confirmDelete,
    currency,
    customers,
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
    products,
    usePermission,
  } = props;
  const [productPickSearch, setProductPickSearch] = useState('');
  const [productPickCategory, setProductPickCategory] = useState('');
  const [productPickBrand, setProductPickBrand] = useState('');
  const [productPickStatus, setProductPickStatus] = useState('');
  const [assignedCustomerSearch, setAssignedCustomerSearch] = useState('');
  const [voucherAudienceFilter, setVoucherAudienceFilter] = useState('');
  const canCreateVoucher = usePermission('voucher:create');
  const canUpdateVoucher = usePermission('voucher:update');
  const canDeleteVoucher = usePermission('voucher:delete');
  const categoryOptions = (categories || []).map((category: any) => ({
    id: String(category.id),
    label: category.name || category.label || category.slug || String(category.id),
    helper: category.slug || category.parentName || undefined,
  }));
  const brandOptions = (brands || []).map((brand: any) => ({
    id: String(brand.id),
    label: brand.name || brand.code || String(brand.id),
    helper: brand.code || undefined,
  }));
  const productOptions = useMemo(() => {
    const search = normalizeText(productPickSearch);
    return (products || [])
      .filter((product: any) => {
        const searchSource = normalizeText([
          product.name,
          product.sku,
          product.brand,
          product.brandName,
          product.category,
          product.categoryName,
        ].filter(Boolean).join(' '));
        const matchesSearch = !search || searchSource.includes(search);
        const matchesCategory = !productPickCategory || getProductCategoryId(product) === productPickCategory;
        const matchesBrand = !productPickBrand || getProductBrandId(product) === productPickBrand;
        const matchesStatus = !productPickStatus || getProductStatus(product) === productPickStatus;
        return matchesSearch && matchesCategory && matchesBrand && matchesStatus;
      })
      .slice(0, 200)
      .map((product: any) => ({
        id: String(product.id),
        label: product.name || product.sku || String(product.id),
        helper: [product.sku, product.brandName || product.brand, product.categoryName || product.category].filter(Boolean).join(' · '),
      }));
  }, [productPickBrand, productPickCategory, productPickSearch, productPickStatus, products]);

  const selectedAssignedUserIds = Array.isArray(voucherForm.assignedUserIds)
    ? voucherForm.assignedUserIds
    : (voucherForm.assignedUserId ? [voucherForm.assignedUserId] : []);
  const selectedPaymentMethods = Array.isArray(voucherForm.applicablePaymentMethods) ? voucherForm.applicablePaymentMethods : [];

  const customerOptions = useMemo(() => {
    const search = normalizeText(assignedCustomerSearch);
    return (customers || [])
      .filter((customer: any) => {
        const searchSource = normalizeText([
          customer.fullName,
          customer.full_name,
          customer.name,
          customer.email,
          customer.phone,
          customer.tier,
          customer.loyaltyTier,
        ].filter(Boolean).join(' '));
        return !search || searchSource.includes(search);
      })
      .slice(0, 200)
      .map((customer: any) => ({
        id: String(customer.id),
        label: getCustomerLabel(customer),
        helper: [customer.email, customer.phone, customer.tier || customer.loyaltyTier].filter(Boolean).join(' · '),
      }));
  }, [assignedCustomerSearch, customers]);

  const updateAssignedUserIds = (value: string[]) => {
    setVoucherForm({
      ...voucherForm,
      assignedUserIds: value,
      assignedUserId: value.length === 1 ? value[0] : '',
      audienceType: value.length ? 'SPECIFIC_USER' : voucherForm.audienceType,
    });
  };

  const visibleVouchers = useMemo(() => {
    if (!voucherAudienceFilter) return filteredVouchers;
    return filteredVouchers.filter((voucher: any) => voucher.audienceType === voucherAudienceFilter);
  }, [filteredVouchers, voucherAudienceFilter]);

  const voucherAudienceFilters = (
    <>
      <SearchBox value={query} onChange={setQuery} placeholder="Tìm mã voucher, loại, trạng thái" />
      <div className="flex flex-wrap gap-2">
        {voucherAudienceTabs.map((tab) => {
          const active = voucherAudienceFilter === tab.value;
          return (
            <button
              key={tab.value || 'all'}
              type="button"
              onClick={() => setVoucherAudienceFilter(tab.value)}
              className={`h-10 rounded-xl border px-3 text-sm font-bold transition ${active ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'}`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </>
  );

  const productFilterBar = (
    <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 md:col-span-6 md:grid-cols-4">
      <div className="block w-full sm:w-auto">
        <span className="mb-1.5 block text-xs font-bold text-slate-500">Sản phẩm</span>
        <SearchBox value={productPickSearch} onChange={setProductPickSearch} placeholder="Tìm tên, SKU, thương hiệu" />
      </div>
      <Select label="Danh mục" value={productPickCategory} onChange={setProductPickCategory} options={[['', 'Tất cả danh mục'], ...categoryOptions.map((item) => [item.id, item.label])]} />
      <Select label="Thương hiệu" value={productPickBrand} onChange={setProductPickBrand} options={[['', 'Tất cả thương hiệu'], ...brandOptions.map((item) => [item.id, item.label])]} />
      <Select label="Trạng thái" value={productPickStatus} onChange={setProductPickStatus} options={[['', 'Tất cả trạng thái'], ['ACTIVE', 'Đang bán'], ['INACTIVE', 'Tạm dừng'], ['DRAFT', 'Nháp'], ['ARCHIVED', 'Đã lưu trữ']]} />
    </div>
  );

  return (
    <AdminPanel
      title="Quản lý voucher"
      filters={voucherAudienceFilters}
    >
      {(canCreateVoucher || canUpdateVoucher) && <CollapsibleSection title={editingVoucherId ? 'Đang chỉnh sửa voucher' : 'Thêm voucher mới'} description="Mở khi cần thiết lập mã giảm giá, điều kiện đơn tối thiểu và giới hạn sử dụng." defaultOpen={false} forceOpen={Boolean(editingVoucherId)} forceOpenKey={editingVoucherId} closeSignal={voucherCloseSignal} onClose={resetVoucherForm}>
        <form onSubmit={handleVoucherSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-6">
          <Input label="Mã voucher" value={voucherForm.code} required onChange={(value) => setVoucherForm({ ...voucherForm, code: value.toUpperCase() })} />
          <Select label="Mục tiêu" value={voucherForm.campaignType} onChange={(value) => setVoucherForm({ ...voucherForm, campaignType: value })} options={voucherCampaignOptions} />
          <Select label="Đối tượng" value={voucherForm.audienceType} onChange={(value) => setVoucherForm({ ...voucherForm, audienceType: value, firstOrderOnly: value === 'NEW_CUSTOMER' || voucherForm.firstOrderOnly, hiddenCode: value === 'HIDDEN' || voucherForm.hiddenCode, abandonedCartOnly: value === 'ABANDONED_CART' || voucherForm.abandonedCartOnly })} options={voucherAudienceOptions} />
          <Select label="Loại giảm" value={voucherForm.discountType} onChange={(value) => setVoucherForm({ ...voucherForm, discountType: value })} options={[['FIXED', 'Số tiền'], ['PERCENT', 'Phần trăm']]} />
          <Input label="Giá trị" type="number" min={1} max={voucherForm.discountType === 'PERCENT' ? 100 : undefined} value={voucherForm.discountAmount} onChange={(value) => setVoucherForm({ ...voucherForm, discountAmount: Number(value) })} />
          <Input label="Đơn tối thiểu" type="number" min={0} value={voucherForm.minOrderValue} onChange={(value) => setVoucherForm({ ...voucherForm, minOrderValue: Number(value) })} />
          <Input label="Giảm tối đa" type="number" min={0} value={voucherForm.maxDiscount} onChange={(value) => setVoucherForm({ ...voucherForm, maxDiscount: Number(value) })} />
          <Input label="Tổng lượt dùng" type="number" min={0} value={voucherForm.usageLimit} onChange={(value) => setVoucherForm({ ...voucherForm, usageLimit: Number(value) })} />
          <Input label="Ngân sách tối đa" type="number" min={0} value={voucherForm.totalBudgetCap} onChange={(value) => setVoucherForm({ ...voucherForm, totalBudgetCap: Number(value) })} />
          <Input label="Lượt/user" type="number" min={0} value={voucherForm.perUserLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perUserLimit: Number(value) })} />
          <Input label="Lượt/thiết bị" type="number" min={0} value={voucherForm.perDeviceLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perDeviceLimit: Number(value) })} />
          <Input label="Lượt/IP" type="number" min={0} value={voucherForm.perIpLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perIpLimit: Number(value) })} />
          <Input label="Bắt đầu" type="datetime-local" value={voucherForm.startsAt} onChange={(value) => setVoucherForm({ ...voucherForm, startsAt: value })} />
          <Input label="Kết thúc" type="datetime-local" value={voucherForm.endsAt} onChange={(value) => setVoucherForm({ ...voucherForm, endsAt: value })} />
          <Input label="Hạn sau khi lưu (ngày)" type="number" min={0} value={voucherForm.validityDaysAfterClaim} onChange={(value) => setVoucherForm({ ...voucherForm, validityDaysAfterClaim: Number(value) })} />
          <Input label="User đăng ký sau" type="datetime-local" value={voucherForm.eligibleUserRegisteredAfter} onChange={(value) => setVoucherForm({ ...voucherForm, eligibleUserRegisteredAfter: value })} />
          <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
            <div>
              <span className="mb-1.5 block text-xs font-bold text-slate-500">Tài khoản nhận voucher</span>
              <SearchBox value={assignedCustomerSearch} onChange={setAssignedCustomerSearch} placeholder="Tìm tên, email, số điện thoại" />
              {voucherForm.audienceType === 'SPECIFIC_USER' && <div className="mt-1 text-xs font-semibold text-slate-500">Voucher này chỉ cấp cho các tài khoản đã chọn.</div>}
            </div>
            <MultiPickList label="Danh sách tài khoản được cấp" items={customerOptions} selected={selectedAssignedUserIds} onChange={updateAssignedUserIds} emptyText="Không có tài khoản phù hợp bộ lọc." />
          </div>
          <Select label="Trạng thái" value={voucherForm.status} onChange={(value) => setVoucherForm({ ...voucherForm, status: value })} options={[['ACTIVE', 'Đang chạy'], ['INACTIVE', 'Tạm dừng'], ['EXPIRED', 'Hết hạn']]} />
          <Select label="Hoàn voucher" value={voucherForm.refundPolicy} onChange={(value) => setVoucherForm({ ...voucherForm, refundPolicy: value })} options={[['NEVER', 'Không hoàn'], ['SHOP_FAULT_ONLY', 'Hoàn khi lỗi shop'], ['ALWAYS', 'Luôn hoàn khi hủy']]} />
          <PaymentMethodPicker value={selectedPaymentMethods} onChange={(value) => setVoucherForm({ ...voucherForm, applicablePaymentMethods: value })} />
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
            <div className="mb-2 text-xs font-bold text-slate-500">Hạng thành viên áp dụng</div>
            <div className="flex flex-wrap gap-2">
              {voucherTierOptions.map((tier) => (
                <label key={tier} className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-bold ${voucherForm.eligibleTiers.includes(tier) ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600'}`}>
                  <input type="checkbox" checked={voucherForm.eligibleTiers.includes(tier)} onChange={(event) => setVoucherForm({ ...voucherForm.eligibleTiers, tier: event.target.checked ? [...voucherForm.eligibleTiers, tier] : voucherForm.eligibleTiers.filter((item: string) => item !== tier), audienceType: event.target.checked ? 'MEMBER_TIER' : voucherForm.audienceType })} className="h-4 w-4 accent-red-600" />
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
          <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-6">
            <div className="mb-3 text-xs font-bold uppercase text-slate-500">Phạm vi áp dụng</div>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className={`rounded-md border px-3 py-2 text-sm font-bold ${voucherForm.scopeType === 'ALL' ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 text-slate-700'}`}>
                <input type="radio" checked={voucherForm.scopeType === 'ALL'} onChange={() => setVoucherForm({ ...voucherForm, scopeType: 'ALL' })} className="mr-2 accent-red-600" />
                Áp dụng tất cả, trừ mục loại trừ
              </label>
              <label className={`rounded-md border px-3 py-2 text-sm font-bold ${voucherForm.scopeType === 'INCLUDE_SELECTED' ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 text-slate-700'}`}>
                <input type="radio" checked={voucherForm.scopeType === 'INCLUDE_SELECTED'} onChange={() => setVoucherForm({ ...voucherForm, scopeType: 'INCLUDE_SELECTED' })} className="mr-2 accent-red-600" />
                Chỉ áp dụng mục được chọn
              </label>
            </div>
          </div>
          {productFilterBar}
          {voucherForm.scopeType === 'INCLUDE_SELECTED' && (
            <div className="grid gap-3 md:col-span-6 lg:grid-cols-3">
              <MultiPickList label="Danh mục áp dụng" items={categoryOptions} selected={voucherForm.includeCategoryIds} onChange={(value) => setVoucherForm({ ...voucherForm, includeCategoryIds: value })} emptyText="Chưa có danh mục để chọn." />
              <MultiPickList label="Thương hiệu áp dụng" items={brandOptions} selected={voucherForm.includeBrandIds} onChange={(value) => setVoucherForm({ ...voucherForm, includeBrandIds: value })} emptyText="Chưa có thương hiệu để chọn." />
              <MultiPickList label="Sản phẩm áp dụng" items={productOptions} selected={voucherForm.includeProductIds} onChange={(value) => setVoucherForm({ ...voucherForm, includeProductIds: value })} emptyText="Không có sản phẩm phù hợp bộ lọc." />
            </div>
          )}
          <div className="grid gap-3 md:col-span-6 lg:grid-cols-3">
            <MultiPickList label="Danh mục loại trừ" items={categoryOptions} selected={voucherForm.excludeCategoryIds} onChange={(value) => setVoucherForm({ ...voucherForm, excludeCategoryIds: value })} emptyText="Chưa có danh mục để chọn." />
            <MultiPickList label="Thương hiệu loại trừ" items={brandOptions} selected={voucherForm.excludeBrandIds} onChange={(value) => setVoucherForm({ ...voucherForm, excludeBrandIds: value })} emptyText="Chưa có thương hiệu để chọn." />
            <MultiPickList label="Sản phẩm loại trừ" items={productOptions} selected={voucherForm.excludeProductIds} onChange={(value) => setVoucherForm({ ...voucherForm, excludeProductIds: value })} emptyText="Không có sản phẩm phù hợp bộ lọc." />
          </div>
          <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:col-span-6 md:grid-cols-2">
            <Input label="Tiêu đề hiển thị" value={voucherForm.displayTitle} placeholder="Ví dụ: Giảm 10% cho thành viên Gold" onChange={(value) => setVoucherForm({ ...voucherForm, displayTitle: value })} />
            <Input label="Mô tả ngắn" value={voucherForm.displayDescription} placeholder="Tóm tắt điều kiện khách hàng sẽ thấy" onChange={(value) => setVoucherForm({ ...voucherForm, displayDescription: value })} />
            <textarea className="min-h-24 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-2" placeholder="Điều khoản công khai: thời hạn, kênh áp dụng, không dùng chung khuyến mãi khác..." value={voucherForm.publicTerms} onChange={(event) => setVoucherForm({ ...voucherForm, publicTerms: event.target.value })} />
          </div>
          <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-5" placeholder="Ghi chú nội bộ: lý do tạo, khách hàng được cấp, kênh gửi..." value={voucherForm.internalNote} onChange={(event) => setVoucherForm({ ...voucherForm, internalNote: event.target.value })} />
          <SubmitButtons editing={Boolean(editingVoucherId)} onCancel={resetVoucherForm} />
        </form>
      </CollapsibleSection>}
      <AdminTable headers={['Mã', 'Chiến dịch', 'Đối tượng', 'Giá trị', 'Điều kiện', 'Lượt dùng', 'Trạng thái', 'Thao tác']}>
        {visibleVouchers.map((voucher: any) => (
          <tr key={voucher.id}>
            <td className="px-4 py-3"><div className="font-mono font-bold text-slate-900">{voucher.code}</div>{voucher.hiddenCode && <div className="mt-1 text-xs font-bold text-amber-600">Mã ẩn</div>}</td>
            <td className="px-4 py-3">{voucherCampaignOptions.find(([value]) => value === voucher.campaignType)?.[1] || voucher.campaignType || '-'}</td>
            <td className="px-4 py-3">{voucherAudienceOptions.find(([value]) => value === voucher.audienceType)?.[1] || voucher.audienceType || '-'}</td>
            <td className="px-4 py-3 font-semibold">{voucher.discountType === 'PERCENT' ? `${voucher.discountAmount}%` : currency.format(Number(voucher.discountAmount || 0))}</td>
            <td className="px-4 py-3"><VoucherConditions voucher={voucher} /></td>
            <td className="px-4 py-3">{voucher.usedCount || 0}/{voucher.usageLimit || '∞'}<div className="text-xs text-slate-500">/user: {voucher.perUserLimit || '∞'}</div>{voucher.totalBudgetCap ? <div className="text-xs text-slate-500">NS: {currency.format(Number(voucher.totalDiscountUsed || 0))}/{currency.format(Number(voucher.totalBudgetCap || 0))}</div> : null}</td>
            <td className="px-4 py-3"><AdminBadge tone={voucherStatusTones[voucher.status] || 'slate'}>{voucherStatusLabels[voucher.status] || voucher.status}</AdminBadge></td>
            <td className="px-4 py-3"><RowActions onEdit={canUpdateVoucher ? () => editVoucher(voucher) : undefined} onDelete={canDeleteVoucher ? () => confirmDelete(voucher.code, () => adminVouchersApi.adminDeleteVoucher(voucher.id)) : undefined} /></td>
          </tr>
        ))}
      </AdminTable>
    </AdminPanel>
  );
}
