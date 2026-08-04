import type { FormEvent } from 'react';
import type { ReportFilters as Filters, ReportView } from '../types';

const orderStatuses = [
  ['PENDING', 'Chờ xử lý'],
  ['CONFIRMED', 'Đã xác nhận'],
  ['PAID', 'Đã thanh toán'],
  ['PROCESSING', 'Đang đóng gói'],
  ['SHIPPED', 'Đang giao hàng'],
  ['COMPLETED', 'Hoàn tất'],
  ['CANCELLED', 'Đã hủy'],
  ['REFUNDED', 'Đã hoàn tiền'],
  ['PAYMENT_FAILED', 'Thanh toán thất bại'],
  ['RETURNING', 'Đang hoàn hàng'],
  ['RETURNED', 'Đã nhận lại hàng trả'],
] as const;

const paymentStatuses = [
  ['UNPAID', 'Chưa thanh toán'],
  ['PENDING', 'Đang chờ thanh toán'],
  ['PENDING_PAYMENT', 'Chờ thanh toán'],
  ['PAID', 'Đã thanh toán'],
  ['PAID_LATE', 'Thanh toán trễ cần đối soát'],
  ['FAILED', 'Thanh toán thất bại'],
  ['EXPIRED', 'Đã hết hạn'],
  ['REFUNDED', 'Đã hoàn tiền'],
] as const;

type Props = {
  activeView: ReportView;
  filters: Filters;
  onChange: (filters: Filters) => void;
  onApply: () => void;
  disabled?: boolean;
};

export default function ReportFilters({
  activeView,
  filters,
  onChange,
  onApply,
  disabled,
}: Props) {
  function submit(event: FormEvent) {
    event.preventDefault();
    onApply();
  }

  return (
    <form
      onSubmit={submit}
      className="grid grid-cols-1 gap-x-4 gap-y-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-[repeat(auto-fit,minmax(11rem,1fr))]"
      aria-label="Bộ lọc báo cáo"
    >
      {activeView !== 'inventory' ? (
        <>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Từ ngày
            <input
              type="date"
              required
              value={filters.from}
              onChange={(event) => onChange({ ...filters, from: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Đến trước ngày
            <input
              type="date"
              required
              value={filters.to}
              onChange={(event) => onChange({ ...filters, to: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
        </>
      ) : null}
      {activeView === 'revenue' || activeView === 'orders' ? (
        <>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Kênh bán
            <select
              value={filters.channel}
              onChange={(event) => onChange({ ...filters, channel: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              <option value="ONLINE">Online</option>
              <option value="POS">Tại quầy</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Phương thức thanh toán
            <select
              value={filters.paymentMethod}
              onChange={(event) => onChange({ ...filters, paymentMethod: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              <option value="NO_PAYMENT">Không yêu cầu thanh toán</option>
              <option value="COD">COD</option>
              <option value="MOMO">MoMo</option>
              <option value="ZALOPAY">ZaloPay</option>
              <option value="SEPAY">SePay</option>
            </select>
          </label>
        </>
      ) : null}
      {activeView === 'orders' ? (
        <>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Trạng thái
            <select
              value={filters.status}
              onChange={(event) => onChange({ ...filters, status: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              {orderStatuses.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Trạng thái thanh toán
            <select
              value={filters.paymentStatus}
              onChange={(event) => onChange({
                ...filters,
                paymentStatus: event.target.value,
              })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              {paymentStatuses.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Phương thức nhận hàng
            <select
              value={filters.fulfillmentMethod}
              onChange={(event) => onChange({
                ...filters,
                fulfillmentMethod: event.target.value,
              })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              <option value="DELIVERY">Giao tận nơi</option>
              <option value="STORE_PICKUP">Nhận tại cửa hàng</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Cơ sở ngày
            <select
              value={filters.dateBasis}
              onChange={(event) => onChange({
                ...filters,
                dateBasis: event.target.value as Filters['dateBasis'],
              })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="createdAt">Ngày tạo</option>
              <option value="completedAt">Ngày hoàn tất</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Tìm đơn hàng
            <input
              type="search"
              value={filters.search}
              onChange={(event) => onChange({ ...filters, search: event.target.value })}
              placeholder="Mã đơn, khách hàng"
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
        </>
      ) : activeView === 'customers' ? (
        <>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Hạng thành viên
            <select
              value={filters.tier}
              onChange={(event) => onChange({ ...filters, tier: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              <option value="MEMBER">Thành viên</option>
              <option value="SILVER">Bạc</option>
              <option value="GOLD">Vàng</option>
              <option value="DIAMOND">Kim cương</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Phân nhóm khách hàng
            <select
              value={filters.segment}
              onChange={(event) => onChange({ ...filters, segment: event.target.value })}
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Tất cả</option>
              <option value="FIRST_TIME">Mua lần đầu</option>
              <option value="RETURNING">Quay lại</option>
              <option value="NEW_NO_ORDER">Mới, chưa mua</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
            Tìm khách hàng
            <input
              type="search"
              value={filters.search}
              onChange={(event) => onChange({ ...filters, search: event.target.value })}
              placeholder="Tên hoặc email"
              className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
        </>
      ) : (
        <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold text-slate-700">
          Tìm kiếm
          <input
            type="search"
            value={filters.search}
            onChange={(event) => onChange({ ...filters, search: event.target.value })}
            placeholder={
              activeView === 'inventory'
                ? 'Tên sản phẩm hoặc SKU'
                : activeView === 'products'
                ? 'Tên hoặc SKU'
                : 'Không bắt buộc'
            }
            className="mt-auto h-10 min-w-0 w-full rounded-md border border-slate-300 px-3 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
          />
        </label>
      )}
      <div className="flex items-end">
        <button
          type="submit"
          disabled={disabled}
          className="h-10 w-full rounded-md bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Áp dụng
        </button>
      </div>
    </form>
  );
}
