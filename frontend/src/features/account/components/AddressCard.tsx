import { CheckCircle2, Pencil, Trash2 } from 'lucide-react';
import type { AccountAddress } from '../types/accountDashboardTypes';

type AddressCardProps = {
  address: AccountAddress;
  onEdit: (address: AccountAddress) => void;
  onSetDefault: (addressId: string) => void;
  onDelete: (addressId: string) => void;
  onVerifyOnMap: (address: AccountAddress) => void;
};

export function AddressCard({ address, onEdit, onSetDefault, onDelete, onVerifyOnMap }: AddressCardProps) {
  return (
    <div className="border border-gray-100 rounded-lg p-4">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <p className="font-bold text-gray-800">{address.receiverName}</p>
            {address.isDefault && <span className="text-[11px] bg-red-50 text-[#d70018] px-2 py-1 rounded">Mặc định</span>}
            {address.isMapVerified && <span className="inline-flex items-center gap-1 text-[11px] bg-green-50 text-green-700 px-2 py-1 rounded"><CheckCircle2 className="w-3 h-3" /> Đã xác minh</span>}
          </div>
          <p className="text-sm text-gray-600">{address.receiverPhone}</p>
          <p className="text-sm text-gray-600 mt-1">{address.addressLine}</p>
          {address.note && <p className="text-xs text-gray-400 mt-1">{address.note}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => onEdit(address)} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50"><Pencil className="w-4 h-4" /> Chỉnh sửa</button>
          <button type="button" onClick={() => onVerifyOnMap(address)} className="px-3 py-2 rounded-lg border border-blue-200 text-blue-700 text-sm font-semibold hover:bg-blue-50">Xác minh Google Maps</button>
          <button type="button" onClick={() => onSetDefault(address.id)} className="px-3 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50">Đặt mặc định</button>
          <button type="button" onClick={() => onDelete(address.id)} className="px-3 py-2 rounded-lg border border-red-100 text-red-600 text-sm font-semibold hover:bg-red-50"><Trash2 className="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  );
}
