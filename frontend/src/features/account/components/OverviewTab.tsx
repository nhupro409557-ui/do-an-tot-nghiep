import { Gift, MapPin, Phone, ShieldCheck } from 'lucide-react';
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
  onOpenAddresses: () => void;
  onOpenLoyalty: () => void;
};

export function OverviewTab({ addresses, orders, onOpenAddresses, onOpenLoyalty }: OverviewTabProps) {
  return (
    <>
      <div className="bg-blue-50 text-blue-900 px-6 py-4 rounded-xl flex items-center gap-3 text-sm border border-blue-100">
        <ShieldCheck className="w-5 h-5 shrink-0" />
        <span>Nâng cấp hạng thành viên để nhận ngay voucher 500k sinh nhật!</span>
      </div>

      <section className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <h3 className="font-bold text-gray-800">Địa chỉ giao hàng</h3>
          <button type="button" onClick={onOpenAddresses} className="text-sm font-semibold text-[#d70018]">Quản lý địa chỉ</button>
        </div>
        {addresses.length === 0 ? (
          <p className="text-sm text-gray-500">Bạn chưa có địa chỉ. Thêm địa chỉ để hỗ trợ thanh toán và tích hợp đơn vị vận chuyển.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {addresses.slice(0, 2).map(address => (
              <div key={address.id} className="border border-gray-100 rounded-lg p-4">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-bold text-gray-800 mb-4">Đơn hàng gần đây</h3>
          <AccountOrdersList orders={orders} limit={3} />
        </section>

        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-bold text-gray-800 mb-4">Ưu đãi / Nhiệm vụ</h3>
          <button type="button" onClick={onOpenLoyalty} className="w-full flex gap-4 items-center border border-gray-100 rounded-lg p-4 hover:border-red-100 transition-colors text-left">
            <div className="w-12 h-12 bg-[#d70018] text-white rounded-lg flex items-center justify-center shadow-sm"><Gift className="w-6 h-6" /></div>
            <div>
              <h4 className="font-bold text-sm text-gray-800 mb-1">Cửa hàng quy đổi loyalty</h4>
              <p className="text-blue-600 font-semibold text-xs mb-1">Dùng điểm đổi mã giảm giá</p>
            </div>
          </button>
        </section>
      </div>
    </>
  );
}
