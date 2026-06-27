import React, { useState } from 'react';
import { LocationPicker } from '../../shipping/components/LocationPicker';
import { VietnamAddressSelector } from '../../shipping/components/VietnamAddressSelector';

type NewProvince = {
  matinhBNV?: string | number;
  matinhTMS?: string | number;
  tentinhmoi: string;
  phuongxa: NewWard[];
};

type NewWard = {
  maphuongxa: string | number;
  tenphuongxa: string;
};

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

const PROVINCE_COORDINATES = [
  { name: 'Thành phố Hà Nội', lat: 21.0285, lng: 105.8542 },
  { name: 'Tỉnh Bắc Ninh', lat: 21.1861, lng: 106.0763 },
  { name: 'Tỉnh Quảng Ninh', lat: 20.9599, lng: 107.0435 },
  { name: 'Tp Hải Phòng', lat: 20.8449, lng: 106.6881 },
  { name: 'Tỉnh Hưng Yên', lat: 20.6464, lng: 106.0511 },
  { name: 'Tỉnh Ninh Bình', lat: 20.2506, lng: 105.9749 },
  { name: 'Tỉnh Cao Bằng', lat: 22.6667, lng: 106.2500 },
  { name: 'Tỉnh Tuyên Quang', lat: 21.8167, lng: 105.2167 },
  { name: 'Tỉnh Lào Cai', lat: 22.4833, lng: 103.9667 },
  { name: 'Tỉnh Thái Nguyên', lat: 21.5928, lng: 105.8442 },
  { name: 'Tỉnh Lạng Sơn', lat: 21.8500, lng: 106.7500 },
  { name: 'Tỉnh Phú Thọ', lat: 21.3200, lng: 105.2200 },
  { name: 'Tỉnh Điện Biên', lat: 21.3833, lng: 103.0167 },
  { name: 'Tỉnh Lai Châu', lat: 22.3920, lng: 103.4560 },
  { name: 'Tỉnh Sơn La', lat: 21.3300, lng: 103.9000 },
  { name: 'Tỉnh Thanh Hóa', lat: 19.8075, lng: 105.7764 },
  { name: 'Tỉnh Nghệ An', lat: 18.6734, lng: 105.6924 },
  { name: 'Tỉnh Hà Tĩnh', lat: 18.3434, lng: 105.9016 },
  { name: 'Tỉnh Quảng Trị', lat: 16.7500, lng: 107.0000 },
  { name: 'Thành phố Huế', lat: 16.4637, lng: 107.5908 },
  { name: 'Tp Đà Nẵng', lat: 16.0544, lng: 108.2022 },
  { name: 'Tỉnh Quảng Ngãi', lat: 15.1200, lng: 108.8000 },
  { name: 'Tỉnh Khánh Hòa', lat: 12.2500, lng: 109.1833 },
  { name: 'Tỉnh Gia Lai', lat: 13.9833, lng: 108.0000 },
  { name: 'Tỉnh Đắk Lắk', lat: 12.6667, lng: 108.0333 },
  { name: 'Tỉnh Lâm Đồng', lat: 11.9404, lng: 108.4583 },
  { name: 'Tỉnh Tây Ninh', lat: 11.3000, lng: 106.1000 },
  { name: 'Tỉnh Đồng Nai', lat: 10.9575, lng: 106.8427 },
  { name: 'Tp Hồ Chí Minh', lat: 10.8231, lng: 106.6297 },
  { name: 'Tỉnh Vĩnh Long', lat: 10.2500, lng: 105.9667 },
  { name: 'Tỉnh Đồng Tháp', lat: 10.4500, lng: 105.6333 },
  { name: 'Tỉnh An Giang', lat: 10.5000, lng: 105.1667 },
  { name: 'Tp Cần Thơ', lat: 10.0333, lng: 105.7833 },
  { name: 'Tỉnh Cà Mau', lat: 9.1764, lng: 105.1501 },
];

function getDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

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
  const [isLocating, setIsLocating] = useState(false);

  const handleAutoLocate = () => {
    if (!navigator.geolocation) {
      alert('Trình duyệt của bạn không hỗ trợ định vị GPS.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=jsonv2&accept-language=vi`);
          const data = await res.json();

          if (!data || !data.address) {
            alert('Không thể nhận diện địa chỉ từ vị trí hiện tại.');
            setIsLocating(false);
            return;
          }

          // Fetch danh mục xã phường để map
          const provincesRes = await fetch('https://raw.githubusercontent.com/phucanhle/vn-xaphuong-2025/main/danhmucxaphuong.json');
          const provincesData: NewProvince[] = await provincesRes.json();

          const norm = (t: string) => t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/tinh/g, '').replace(/thanh pho/g, '').replace(/quan/g, '').replace(/huyen/g, '').replace(/phuong/g, '').replace(/xa/g, '').trim();

          const addr = data.address;
          const possibleProvinceNames = [addr.city, addr.province, addr.state].filter(Boolean);
          let matchedProvince: NewProvince | null = null;
          for (const name of possibleProvinceNames) {
            const n = norm(name);
            matchedProvince = provincesData.find(p => {
              const pNorm = norm(p.tentinhmoi);
              return pNorm.includes(n) || n.includes(pNorm);
            }) || null;
            if (matchedProvince) break;
          }

          let isNearestProvinceUsed = false;
          if (!matchedProvince) {
            // Không khớp trực tiếp tên tỉnh/thành. Ta tính khoảng cách địa lý đến 34 tỉnh/thành
            let minDistance = Infinity;
            let nearestProvinceName = '';
            for (const prov of PROVINCE_COORDINATES) {
              const dist = getDistance(latitude, longitude, prov.lat, prov.lng);
              if (dist < minDistance) {
                minDistance = dist;
                nearestProvinceName = prov.name;
              }
            }

            if (nearestProvinceName) {
              matchedProvince = provincesData.find(p => p.tentinhmoi === nearestProvinceName) || null;
              if (matchedProvince) {
                isNearestProvinceUsed = true;
              }
            }
          }

          if (!matchedProvince) {
            alert('Định vị thành công nhưng không tìm thấy tỉnh/thành tương ứng trong hệ thống. Vui lòng chọn thủ công.');
            setIsLocating(false);
            return;
          }

          const possibleWardNames = [addr.suburb, addr.quarter, addr.town, addr.village, addr.commune].filter(Boolean);
          const possibleDistrictNames = [addr.city_district, addr.district, addr.county].filter(Boolean);
          let matchedWard: NewWard | null = null;

          for (const wName of possibleWardNames) {
            const wNorm = norm(wName);
            // Ưu tiên khớp cả quận/huyện
            for (const dName of possibleDistrictNames) {
              const dNorm = norm(dName);
              matchedWard = matchedProvince.phuongxa.find(w => {
                const wn = norm(w.tenphuongxa);
                return wn.includes(wNorm) && wn.includes(dNorm);
              }) || null;
              if (matchedWard) break;
            }
            if (matchedWard) break;

            // Fallback chỉ khớp phường xã
            matchedWard = matchedProvince.phuongxa.find(w => norm(w.tenphuongxa).includes(wNorm)) || null;
            if (matchedWard) break;
          }

          if (isNearestProvinceUsed) {
            if (matchedWard) {
              alert(`Hệ thống đã tự động định vị vị trí của bạn gần tỉnh/thành phố "${matchedProvince.tentinhmoi}" nhất và khớp xã/phường "${matchedWard.tenphuongxa}". Vui lòng kiểm tra lại trước khi lưu.`);
            } else {
              alert(`Hệ thống định vị vị trí của bạn gần tỉnh/thành phố "${matchedProvince.tentinhmoi}" nhất. Vui lòng chọn thủ công Phường/Xã phù hợp.`);
            }
          }

          const streetParts = [addr.house_number, addr.road].filter(Boolean);
          const street = streetParts.join(' ') || addr.amenity || addr.building || '';

          const provinceId = String(matchedProvince.matinhBNV ?? matchedProvince.matinhTMS);
          const wardId = matchedWard ? String(matchedWard.maphuongxa) : '';
          const wardName = matchedWard ? matchedWard.tenphuongxa : '';

          onUpdateAddressDraft((prev: any) => {
            const newAddressData = {
              provinceId,
              provinceName: matchedProvince!.tentinhmoi,
              districtId: '',
              districtName: '',
              wardId,
              wardName,
              street,
            };
            const mapPredictionAddress = [street, wardName, matchedProvince!.tentinhmoi].filter(Boolean).join(', ');
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapPredictionAddress)}`;

            return {
              ...prev,
              addressData: newAddressData,
              addressLine: mapPredictionAddress,
              mapQueryAddress: mapPredictionAddress,
              mapUrl,
              lat: latitude,
              lng: longitude,
            };
          });

        } catch (err) {
          console.error(err);
          alert('Có lỗi xảy ra trong quá trình nhận diện địa chỉ.');
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error(error);
        alert('Không thể lấy vị trí hiện tại. Vui lòng cấp quyền truy cập vị trí cho trình duyệt.');
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  return (
    <form onSubmit={onSubmitAddress} className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5 rounded-lg border border-slate-100 bg-slate-50 p-4">
      <input required value={addressDraft.receiverName} onChange={event => onUpdateAddressDraft({ ...addressDraft, receiverName: event.target.value })} placeholder="Họ tên người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
      <input required value={addressDraft.receiverPhone} onChange={event => onUpdateAddressDraft({ ...addressDraft, receiverPhone: event.target.value })} placeholder="Số điện thoại người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />

      <div className="md:col-span-2">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-gray-700">Địa chỉ nhận hàng</label>
          <button
            type="button"
            onClick={handleAutoLocate}
            disabled={isLocating}
            className="text-xs px-2.5 py-1.5 bg-rose-50 text-[#d70018] rounded-md hover:bg-rose-100 disabled:opacity-50 font-bold transition flex items-center gap-1 border border-rose-100"
          >
            📍 {isLocating ? 'Đang định vị...' : 'Định vị của tôi'}
          </button>
        </div>
        <VietnamAddressSelector
          value={addressDraft.addressData!}
          onChange={(data) => {
            const isComplete = Boolean(data.provinceId && data.wardId && data.street?.trim());
            const addressLine = isComplete ? [data.street, data.wardName, data.provinceName].filter(Boolean).join(', ') : '';
            const mapUrl = addressLine ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(addressLine)}` : '';
            onUpdateAddressDraft((prev: any) => ({
              ...prev,
              addressData: data,
              addressLine,
              mapQueryAddress: addressLine,
              mapUrl,
              lat: undefined,
              lng: undefined,
            }));
          }}
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
      <button type="submit" disabled={!addressDraft.addressData?.provinceId || !addressDraft.addressData?.wardId || !addressDraft.addressData?.street} className="inline-flex justify-center items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-50">
        {editingAddressId ? 'Lưu địa chỉ' : 'Thêm địa chỉ'}
      </button>
    </form>
  );
}
