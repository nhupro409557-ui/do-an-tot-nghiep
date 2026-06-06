import { AddressCard } from './AddressCard';
import type { AccountAddress } from '../types/accountDashboardTypes';

type AddressListProps = {
  addresses: AccountAddress[];
  onOpenEditAddressForm: (address: AccountAddress) => void;
  onUpdateAddresses: (addresses: AccountAddress[]) => void;
  onVerifyAddressOnMap: (address: AccountAddress) => void;
};

export function AddressList({
  addresses,
  onOpenEditAddressForm,
  onUpdateAddresses,
  onVerifyAddressOnMap,
}: AddressListProps) {
  return (
    <div className="space-y-3">
      {addresses.map(address => (
        <AddressCard
          key={address.id}
          address={address}
          onEdit={onOpenEditAddressForm}
          onVerifyOnMap={onVerifyAddressOnMap}
          onSetDefault={(addressId) => onUpdateAddresses(addresses.map(item => ({ ...item, isDefault: item.id === addressId })))}
          onDelete={(addressId) => onUpdateAddresses(addresses.filter(item => item.id !== addressId))}
        />
      ))}
      {addresses.length === 0 && <p className="text-sm text-gray-500">Chưa có địa chỉ nào. Bấm thêm địa chỉ để nhập thông tin nhận hàng.</p>}
    </div>
  );
}
