import React, { useEffect, useState } from 'react';
import { Store, Phone, Mail, MapPin, Info, Save, Edit, X } from 'lucide-react';
import { storeInfoApi, type StoreInfo } from '../../../services/storeInfoApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';
import { LocationPicker } from '../../shipping/components/LocationPicker';

export default function AdminStoreInfoTab() {
  const [storeInfo, setStoreInfo] = useState<StoreInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [hotline, setHotline] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [description, setDescription] = useState('');
  const [lat, setLat] = useState<number | undefined>(undefined);
  const [lng, setLng] = useState<number | undefined>(undefined);
  const [mapUrl, setMapUrl] = useState('');
  const [isLocating, setIsLocating] = useState(false);

  const handleAutoLocate = () => {
    if (!navigator.geolocation) {
      notifyAdmin('Trình duyệt của bạn không hỗ trợ định vị GPS.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=jsonv2&accept-language=vi`);
          const data = await res.json();

          if (!data || !data.display_name) {
            notifyAdmin('Không thể nhận diện địa chỉ từ vị trí hiện tại.');
            return;
          }

          const cleanAddress = data.display_name;
          setAddress(cleanAddress);
          setLat(latitude);
          setLng(longitude);

          const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(cleanAddress)}`;
          setMapUrl(mapsUrl);

          notifyAdmin('Đã tự động xác định vị trí cửa hàng của bạn!');
        } catch (err) {
          console.error(err);
          notifyAdmin('Có lỗi xảy ra khi nhận diện địa chỉ.');
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error(error);
        notifyAdmin('Không thể lấy vị trí hiện tại. Vui lòng cấp quyền vị trí cho trình duyệt.');
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await storeInfoApi.getStoreInfo();
      setStoreInfo(data);
      setName(data.name || '');
      setHotline(data.hotline || '');
      setEmail(data.email || '');
      setAddress(data.address || '');
      setDescription(data.description || '');
      setLat(data.lat);
      setLng(data.lng);
    } catch (err) {
      console.error(err);
      notifyAdmin('Không thể tải thông tin cấu hình cửa hàng.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleCancel = () => {
    if (storeInfo) {
      setName(storeInfo.name || '');
      setHotline(storeInfo.hotline || '');
      setEmail(storeInfo.email || '');
      setAddress(storeInfo.address || '');
      setDescription(storeInfo.description || '');
      setLat(storeInfo.lat);
      setLng(storeInfo.lng);
    }
    setIsEditing(false);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !hotline.trim() || !email.trim() || !address.trim() || !description.trim()) {
      notifyAdmin('Vui lòng điền đầy đủ tất cả các trường.');
      return;
    }

    setSaving(true);
    try {
      await storeInfoApi.adminUpdateStoreInfo({
        name: name.trim(),
        hotline: hotline.trim(),
        email: email.trim(),
        address: address.trim(),
        description: description.trim(),
        lat: lat,
        lng: lng,
      });
      notifyAdmin('Đã cập nhật thông tin cửa hàng thành công.');
      setIsEditing(false);
      void loadData();
    } catch (err) {
      console.error(err);
      notifyAdmin('Có lỗi xảy ra khi lưu thông tin cửa hàng.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="text-sm font-semibold text-slate-500">Đang tải dữ liệu cấu hình cửa hàng...</span>
      </div>
    );
  }

  // Read-only Table view mode
  if (!isEditing) {
    return (
      <div className="max-w-3xl space-y-6">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-[#d70018]">
                <Store className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">Thông tin cửa hàng</h3>
                <p className="text-xs text-slate-500">Thông tin liên hệ chính thức và cấu hình vị trí của hệ thống.</p>
              </div>
            </div>
            <button
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 transition shadow-sm hover:text-[#d70018]"
            >
              <Edit className="h-4 w-4" />
              Chỉnh sửa
            </button>
          </div>
          <table className="w-full border-collapse text-left text-sm text-slate-600">
            <tbody>
              <tr className="border-b border-slate-100">
                <td className="px-6 py-4 font-bold text-slate-900 w-1/3 bg-slate-50/20">Tên cửa hàng</td>
                <td className="px-6 py-4 text-slate-800">{name}</td>
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-6 py-4 font-bold text-slate-900 bg-slate-50/20">Hotline liên hệ</td>
                <td className="px-6 py-4 font-bold text-slate-900">{hotline}</td>
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-6 py-4 font-bold text-slate-900 bg-slate-50/20">Email hỗ trợ</td>
                <td className="px-6 py-4 text-slate-800">{email}</td>
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-6 py-4 font-bold text-slate-900 bg-slate-50/20">Địa chỉ văn phòng</td>
                <td className="px-6 py-4 text-slate-800 leading-relaxed">{address}</td>
              </tr>
              <tr className="border-b border-slate-100">
                <td className="px-6 py-4 font-bold text-slate-900 bg-slate-50/20">Tọa độ GPS</td>
                <td className="px-6 py-4">
                  {lat && lng ? (
                    <span className="rounded bg-green-50 px-2 py-1 text-xs font-bold text-green-700 border border-green-100">
                      {lat.toFixed(6)}, {lng.toFixed(6)}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Chưa xác định tọa độ</span>
                  )}
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 font-bold text-slate-900 bg-slate-50/20">Giới thiệu / Slogan</td>
                <td className="px-6 py-4 whitespace-pre-line text-slate-500 leading-relaxed">{description}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Static Map View */}
        {lat && lng && (
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
            <h4 className="text-sm font-bold text-slate-900">Vị trí ghim trên bản đồ</h4>
            <div className="h-[280px] w-full rounded-lg overflow-hidden border border-slate-200">
              <iframe
                title="Store map location"
                src={`https://maps.google.com/maps?output=embed&q=${lat},${lng}&z=17`}
                className="w-full h-full border-0"
                loading="lazy"
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  // Editable Form mode
  return (
    <div className="max-w-3xl space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-3 border-b border-slate-100 pb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-[#d70018]">
            <Store className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#d70018]">Chỉnh sửa thông tin cửa hàng</h2>
            <p className="text-xs text-slate-500">
              Chỉnh sửa thông tin liên hệ và vị trí định vị. Nhấn lưu để áp dụng thay đổi.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Store Name */}
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
              Tên cửa hàng
            </label>
            <input
              type="text"
              disabled
              placeholder="Ví dụ: ElectroMart Vietnam"
              value={name}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none text-sm text-slate-500 cursor-not-allowed"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {/* Hotline */}
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                <Phone className="h-4 w-4 text-slate-400" />
                Hotline chăm sóc khách hàng
              </label>
              <input
                type="text"
                required
                maxLength={50}
                placeholder="Ví dụ: 1800.2097"
                value={hotline}
                onChange={(e) => setHotline(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none transition focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] text-sm"
              />
            </div>

            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                <Mail className="h-4 w-4 text-slate-400" />
                Email hỗ trợ
              </label>
              <input
                type="email"
                required
                maxLength={100}
                placeholder="Ví dụ: support@electromart.vn"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none transition focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] text-sm"
              />
            </div>
          </div>

          {/* Address */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                <MapPin className="h-4 w-4 text-slate-400" />
                Địa chỉ trụ sở chính / Văn phòng
              </label>
              <button
                type="button"
                onClick={handleAutoLocate}
                disabled={isLocating}
                className="text-xs px-2.5 py-1.5 bg-rose-50 text-[#d70018] rounded-md hover:bg-rose-100 disabled:opacity-50 font-bold transition flex items-center gap-1 border border-rose-100"
              >
                📍 {isLocating ? 'Đang định vị...' : 'Định vị của tôi'}
              </button>
            </div>
            <input
              type="text"
              required
              maxLength={500}
              placeholder="Nhập địa chỉ của cửa hàng"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none transition focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] text-sm"
            />
            <LocationPicker
              address={address}
              mapUrl={mapUrl}
              lat={lat}
              lng={lng}
              onPredict={(predictedMapUrl, coords) => {
                setMapUrl(predictedMapUrl);
                if (coords) {
                  setLat(coords.lat);
                  setLng(coords.lng);
                }
              }}
            />
            <div className="grid gap-4 grid-cols-2 mt-3 pt-3 border-t border-slate-100">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500">Vĩ độ (Latitude) điều chỉnh thủ công</label>
                <input
                  type="number"
                  step="any"
                  placeholder="Ví dụ: 10.762622"
                  value={lat !== undefined ? lat : ''}
                  onChange={(e) => setLat(e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 outline-none text-xs focus:border-[#d70018] bg-slate-50 focus:bg-white"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500">Kinh độ (Longitude) điều chỉnh thủ công</label>
                <input
                  type="number"
                  step="any"
                  placeholder="Ví dụ: 106.660172"
                  value={lng !== undefined ? lng : ''}
                  onChange={(e) => setLng(e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 outline-none text-xs focus:border-[#d70018] bg-slate-50 focus:bg-white"
                />
              </div>
            </div>
          </div>


          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
              <Info className="h-4 w-4 text-slate-400" />
              Mô tả ngắn / Slogan cửa hàng
            </label>
            <textarea
              required
              rows={4}
              placeholder="Nhập đoạn mô tả ngắn giới thiệu về hoạt động của cửa hàng..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none transition focus:border-[#d70018] focus:ring-1 focus:ring-[#d70018] text-sm resize-none"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50 transition shadow-sm"
            >
              <X className="h-4 w-4" />
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-lg bg-[#d70018] px-5 py-2.5 text-sm font-bold text-white shadow-md transition hover:bg-[#c00015] disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Đang lưu...' : 'Lưu thiết lập'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
