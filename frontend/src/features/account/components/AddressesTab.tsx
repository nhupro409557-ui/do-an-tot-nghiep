import type React from 'react';
import { MapPin, Plus } from 'lucide-react';
import { AddressForm } from './AddressForm';
import { AddressList } from './AddressList';
import type { AccountAddress } from '../types/accountDashboardTypes';

type AddressesTabProps = {
  addresses: AccountAddress[];
  addressDraft: any;
  editingAddressId: string | null;
  isAddressFormOpen: boolean;
  mapPredictionAddress: string;
  emptyAddress: any;
  onOpenNewAddressForm: () => void;
  onOpenEditAddressForm: (address: AccountAddress) => void;
  onSubmitAddress: (event: React.FormEvent) => void;
  onUpdateAddressDraft: React.Dispatch<React.SetStateAction<any>>;
  onSetAddressFormOpen: (isOpen: boolean) => void;
  onSetEditingAddressId: (id: string | null) => void;
  onUpdateAddresses: (addresses: AccountAddress[]) => void;
  onVerifyAddressOnMap: (address: AccountAddress) => void;
};

export function AddressesTab({
  addresses,
  addressDraft,
  editingAddressId,
  isAddressFormOpen,
  mapPredictionAddress,
  emptyAddress,
  onOpenNewAddressForm,
  onOpenEditAddressForm,
  onSubmitAddress,
  onUpdateAddressDraft,
  onSetAddressFormOpen,
  onSetEditingAddressId,
  onUpdateAddresses,
  onVerifyAddressOnMap,
}: AddressesTabProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <MapPin className="w-6 h-6 text-[#d70018]" />
          <h3 className="font-bold text-gray-800">Địa chỉ nhận hàng</h3>
        </div>
        <button type="button" onClick={onOpenNewAddressForm} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[#d70018] text-white text-sm font-bold hover:bg-red-700">
          <Plus className="w-4 h-4" /> Thêm địa chỉ
        </button>
      </div>

      {isAddressFormOpen && (
        <AddressForm
          addressDraft={addressDraft}
          editingAddressId={editingAddressId}
          mapPredictionAddress={mapPredictionAddress}
          emptyAddress={emptyAddress}
          onSubmitAddress={onSubmitAddress}
          onUpdateAddressDraft={onUpdateAddressDraft}
          onSetAddressFormOpen={onSetAddressFormOpen}
          onSetEditingAddressId={onSetEditingAddressId}
        />
      )}

      <AddressList
        addresses={addresses}
        onOpenEditAddressForm={onOpenEditAddressForm}
        onUpdateAddresses={onUpdateAddresses}
        onVerifyAddressOnMap={onVerifyAddressOnMap}
      />
    </section>
  );
}
