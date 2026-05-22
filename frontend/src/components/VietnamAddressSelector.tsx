import React, { useEffect, useRef, useState } from 'react';

export interface AddressData {
  provinceId: string;
  provinceName: string;
  districtId: string;
  districtName: string;
  wardId: string;
  wardName: string;
  street: string;
}

interface Props {
  value: AddressData;
  onChange: (data: AddressData) => void;
  disabled?: boolean;
}

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

const NEW_ADDRESS_DATA_URL = 'https://raw.githubusercontent.com/phucanhle/vn-xaphuong-2025/main/danhmucxaphuong.json';

export function VietnamAddressSelector({ value, onChange, disabled }: Props) {
  const [provinces, setProvinces] = useState<NewProvince[]>([]);
  const [wards, setWards] = useState<NewWard[]>([]);
  const [wardSearch, setWardSearch] = useState('');
  const [isWardOpen, setIsWardOpen] = useState(false);
  const wardDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(NEW_ADDRESS_DATA_URL)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setProvinces(data);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!value.provinceId) {
      setWards([]);
      return;
    }

    const province = provinces.find(item => String(item.matinhBNV ?? item.matinhTMS) === value.provinceId);
    setWards(province?.phuongxa || []);
  }, [provinces, value.provinceId]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wardDropdownRef.current && !wardDropdownRef.current.contains(event.target as Node)) {
        setIsWardOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const update = (field: keyof AddressData, fieldValue: string, nameField?: keyof AddressData, nameValue?: string) => {
    const nextData = { ...value, [field]: fieldValue };
    if (nameField && nameValue) nextData[nameField] = nameValue;

    if (field === 'provinceId') {
      nextData.districtId = '';
      nextData.districtName = '';
      nextData.wardId = '';
      nextData.wardName = '';
      setWardSearch('');
      setIsWardOpen(false);
    }

    if (field === 'wardId') {
      const ward = wards.find(item => String(item.maphuongxa) === fieldValue);
      nextData.districtId = '';
      nextData.districtName = '';
      nextData.wardName = ward?.tenphuongxa || nameValue || '';
    }

    onChange(nextData);
  };

  const normalizeText = (text: string) =>
    text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd');

  const filteredWards = wardSearch.trim()
    ? wards.filter(ward => normalizeText(ward.tenphuongxa).includes(normalizeText(wardSearch.trim())))
    : wards;

  const canChooseWard = !disabled && Boolean(value.provinceId) && wards.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <select
          disabled={disabled || provinces.length === 0}
          value={value.provinceId}
          onChange={(event) => {
            const option = event.target.options[event.target.selectedIndex];
            update('provinceId', event.target.value, 'provinceName', option.text);
          }}
          className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500"
        >
          <option value="">Tinh/Thanh pho</option>
          {provinces.map(province => {
            const id = String(province.matinhBNV ?? province.matinhTMS);
            return <option key={id} value={id}>{province.tentinhmoi}</option>;
          })}
        </select>

        <div className="relative" ref={wardDropdownRef}>
          <button
            type="button"
            disabled={!canChooseWard}
            onClick={() => {
              setIsWardOpen(value => !value);
              setWardSearch('');
            }}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500 text-left flex items-center justify-between gap-3"
          >
            <span className={value.wardName ? 'text-gray-900' : 'text-gray-500'}>
              {value.wardName || 'Phuong/Xa'}
            </span>
            <span className="text-gray-400 text-xs">▼</span>
          </button>

          {isWardOpen && canChooseWard && (
            <div className="absolute z-50 mt-2 w-full rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden">
              <div className="p-2 border-b border-gray-100">
                <input
                  autoFocus
                  value={wardSearch}
                  onChange={(event) => setWardSearch(event.target.value)}
                  placeholder="Tim nhanh phuong/xa"
                  className="w-full px-3 py-2 border border-gray-200 rounded-md outline-none focus:border-[#d70018] text-sm"
                />
              </div>
              <div className="max-h-60 overflow-y-auto">
                {filteredWards.length > 0 ? (
                  filteredWards.map(ward => (
                    <button
                      key={ward.maphuongxa}
                      type="button"
                      onClick={() => {
                        update('wardId', String(ward.maphuongxa), 'wardName', ward.tenphuongxa);
                        setIsWardOpen(false);
                        setWardSearch('');
                      }}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-red-50 hover:text-[#d70018] ${String(ward.maphuongxa) === value.wardId ? 'bg-red-50 text-[#d70018] font-semibold' : 'text-gray-700'}`}
                    >
                      {ward.tenphuongxa}
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-3 text-sm text-gray-500">Khong tim thay phuong/xa phu hop.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <input
        disabled={disabled}
        required
        value={value.street}
        onChange={(event) => update('street', event.target.value)}
        placeholder="So nha, ten duong (vi du: 123 Le Loi)"
        className="w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500"
      />
    </div>
  );
}
