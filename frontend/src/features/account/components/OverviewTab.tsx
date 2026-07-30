import { ArrowRight, Gift, MapPin, Phone, ShieldCheck } from 'lucide-react';
import { AccountOrdersList } from './AccountOrdersList';

type OverviewAddress = {
  id: string;
  receiverName: string;
  receiverPhone: string;
  addressLine: string;
  isDefault: boolean;
  isMapVerified: boolean;
};

type OverviewTabProps = {
  addresses: OverviewAddress[];
  orders: any[];
  ordersLoading: boolean;
  onOpenAddresses: () => void;
  onOpenLoyalty: () => void;
};

export function OverviewTab({ addresses, orders, ordersLoading, onOpenAddresses, onOpenLoyalty }: OverviewTabProps) {
  return (
    <>
      <div className="flex items-center gap-3 rounded-2xl border border-blue-100 bg-blue-50/80 px-4 py-3.5 text-sm text-blue-900 sm:px-5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-700"><ShieldCheck className="h-5 w-5" /></span>
        <span className="font-medium">Nâng cấp hạng thành viên để nhận thêm ưu đãi sinh nhật.</span>
      </div>

      <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Giao nhận</p><h2 className="mt-1 text-lg font-bold text-slate-900">Địa chỉ giao hàng</h2></div>
          <button type="button" onClick={onOpenAddresses} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-[#d70018] transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-200">Quản lý <ArrowRight className="h-4 w-4" /></button>
        </div>
        {addresses.length === 0 ? (
          <p className="text-sm text-gray-500">Bạn chưa có địa chỉ. Thêm địa chỉ để hỗ trợ thanh toán và tích hợp đơn vị vận chuyển.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {addresses.slice(0, 2).map(address => (
              <div key={address.id} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition hover:border-slate-300 hover:bg-white">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="font-bold text-sm text-gray-800">{address.receiverName}</p>
                  {address.isDefault && <span className="text-[11px] bg-red-50 text-[#d70018] px-2 py-1 rounded">Mặc định</span>}
                </div>
                <p className="text-sm text-gray-600 flex items-center gap-2"><Phone className="w-4 h-4" /> {address.receiverPhone}</p>
                <p className="text-sm text-gray-600 mt-2 flex gap-2"><MapPin className="w-4 h-4 shrink-0 mt-0.5" /> {address.addressLine}</p>
                <p className={`text-xs mt-3 font-semibold ${address.isMapVerified ? 'text-green-600' : 'text-amber-600'}`}>
                  {address.isMapVerified ? 'Đã xác minh trên Google Maps' : 'Chưa xác minh bản đồ'}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Hoạt động</p>
          <h2 className="mb-4 mt-1 text-lg font-bold text-slate-900">Đơn hàng gần đây</h2>
          {ordersLoading ? (
            <p className="py-5 text-sm font-medium text-slate-500">Đang tải đơn hàng gần đây...</p>
          ) : (
            <AccountOrdersList orders={orders} limit={3} />
          )}
        </section>

        <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Thành viên</p>
          <h2 className="mb-4 mt-1 text-lg font-bold text-slate-900">Ưu đãi và phần thưởng</h2>
          <button type="button" onClick={onOpenLoyalty} className="flex min-h-20 w-full items-center gap-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-left transition hover:border-red-200 hover:bg-red-50/40 focus:outline-none focus:ring-2 focus:ring-red-200">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#d70018] text-white"><Gift className="h-6 w-6" /></div>
            <div className="min-w-0 flex-1">
              <h3 className="mb-1 font-bold text-slate-900">Đổi điểm nhận ưu đãi</h3>
              <p className="text-sm text-slate-500">Sử dụng điểm thành viên để đổi mã giảm giá.</p>
            </div>
            <ArrowRight className="h-5 w-5 shrink-0 text-slate-400" />
          </button>
        </section>
      </div>
    </>
  );
}
