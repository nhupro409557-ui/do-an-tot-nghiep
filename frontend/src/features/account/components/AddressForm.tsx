import type React from 'react';
import { LocationPicker } from '../../shipping/components/LocationPicker';
import { VietnamAddressSelector } from '../../shipping/components/VietnamAddressSelector';

type AddressFormProps = {
  addressDraft: any;
  editingAddressId: string | null;
  mapPredictionAddress: string;
  emptyAddress: any;
  onSubmitAddress: (event: React.FormEvent) => void;
  onUpdateAddressDraft: React.Dispatch<React.SetStateAction<any>>;
  onSetAddressFormOpen: (isOpen: boolean) => void;
  onSetEditingAddressId: (id: string | null) => void;
};

export function AddressForm({
  addressDraft,
  editingAddressId,
  mapPredictionAddress,
  emptyAddress,
  onSubmitAddress,
  onUpdateAddressDraft,
  onSetAddressFormOpen,
  onSetEditingAddressId,
}: AddressFormProps) {
  return (
    <form onSubmit={onSubmitAddress} className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5 rounded-lg border border-slate-100 bg-slate-50 p-4">
      <input required value={addressDraft.receiverName} onChange={event => onUpdateAddressDraft({ ...addressDraft, receiverName: event.target.value })} placeholder="Họ tên người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
      <input required value={addressDraft.receiverPhone} onChange={event => onUpdateAddressDraft({ ...addressDraft, receiverPhone: event.target.value })} placeholder="Số điện thoại người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />

      <div className="md:col-span-2">
        <label className="text-sm font-semibold text-gray-700 block mb-2">Địa chỉ nhận hàng</label>
        <VietnamAddressSelector
          value={addressDraft.addressData!}
          onChange={(data) => onUpdateAddressDraft((prev: any) => ({
            ...prev,
            addressData: data,
            addressLine: [data.street, data.wardName, data.provinceName].filter(Boolean).join(', '),
            mapQueryAddress: '',
            mapUrl: '',
            lat: undefined,
            lng: undefined,
          }))}
        />
      </div>

      <input value={addressDraft.note} onChange={event => onUpdateAddressDraft({ ...addressDraft, note: event.target.value })} placeholder="Ghi chú giao hàng (không bắt buộc)" className="md:col-span-2 px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />

      <div className="md:col-span-2">
        <LocationPicker
          address={mapPredictionAddress}
          mapUrl={addressDraft.mapUrl}
          lat={addressDraft.lat}
          lng={addressDraft.lng}
          onPredict={(mapUrl, coords) => onUpdateAddressDraft((prev: any) => ({
            ...prev,
            mapUrl,
            lat: coords?.lat,
            lng: coords?.lng,
          }))}
        />
        {mapPredictionAddress && (
          <p className="mt-2 text-xs text-slate-500">
            Google Maps sẽ tìm theo địa chỉ mới: {mapPredictionAddress}
          </p>
        )}
      </div>

      <button type="button" onClick={() => { onSetAddressFormOpen(false); onSetEditingAddressId(null); onUpdateAddressDraft(emptyAddress); }} className="py-3 rounded-lg border border-gray-300 text-gray-700 font-bold hover:bg-white">Hủy</button>
      <button type="submit" disabled={!addressDraft.addressData?.provinceId || !addressDraft.addressData?.wardId || !addressDraft.addressData?.street || !addressDraft.mapUrl} className="inline-flex justify-center items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-50">
        {editingAddressId ? 'Lưu địa chỉ' : 'Thêm địa chỉ'}
      </button>
      {!addressDraft.mapUrl && (
        <p className="md:col-span-2 text-xs text-amber-600">
          Vui lòng bấm Dự đoán từ địa chỉ để ghim vị trí trên bản đồ trước khi lưu.
        </p>
      )}
    </form>
  );
}
