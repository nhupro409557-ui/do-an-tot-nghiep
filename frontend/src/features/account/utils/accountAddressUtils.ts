import type { AddressData } from '../../shipping/components/VietnamAddressSelector';

export const emptyAddress = {
  receiverName: '',
  receiverPhone: '',
  addressLine: '',
  addressData: {
    provinceId: '',
    provinceName: '',
    districtId: '',
    districtName: '',
    wardId: '',
    wardName: '',
    street: '',
  } as AddressData,
  mapQueryAddress: '',
  note: '',
  lat: undefined as number | undefined,
  lng: undefined as number | undefined,
  mapUrl: '',
};

export function getNewAddressLine(data: AddressData | undefined, fallbackAddressLine: string) {
  if (!data) return fallbackAddressLine;
  return [data.street, data.wardName, data.provinceName].filter(Boolean).join(', ');
}

export function stripAdministrativePrefix(value?: string) {
  return (value || '')
    .replace(/^(phường|phuong|xã|xa|thị trấn|thi tran)\s+/i, '')
    .replace(/^(thành phố|thanh pho|tp\.?|tỉnh|tinh)\s+/i, '')
    .trim();
}

export function getMapSearchAddress(data: AddressData | undefined, fallbackAddressLine: string) {
  if (!data) return fallbackAddressLine;
  return [
    data.street,
    stripAdministrativePrefix(data.wardName),
    stripAdministrativePrefix(data.provinceName),
  ].filter(Boolean).join(', ');
}
