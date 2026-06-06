import React, { useEffect, useMemo, useState } from 'react';

interface LocationPickerProps {
  address: string;
  mapUrl?: string;
  lat?: number;
  lng?: number;
  onPredict: (mapUrl: string, coords?: { lat: number; lng: number }) => void;
}

function googleMapsUrl(address: string, coords?: { lat: number; lng: number }) {
  const query = coords ? `${coords.lat},${coords.lng}` : address.trim();
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function googleEmbedUrl(address: string, coords?: { lat: number; lng: number }) {
  const query = coords ? `${coords.lat},${coords.lng}` : address.trim();
  return `https://maps.google.com/maps?output=embed&q=${encodeURIComponent(query)}&z=17`;
}

async function geocodeAddress(address: string) {
  const url = new URL('https://nominatim.openstreetmap.org/search');
  url.searchParams.set('format', 'jsonv2');
  url.searchParams.set('limit', '1');
  url.searchParams.set('countrycodes', 'vn');
  url.searchParams.set('q', address);

  try {
    const response = await fetch(url.toString(), { headers: { Accept: 'application/json' } });
    const results = await response.json();
    const first = Array.isArray(results) ? results[0] : null;
    if (!first?.lat || !first?.lon) return null;
    return { lat: Number(first.lat), lng: Number(first.lon) };
  } catch (error) {
    console.error("Geocoding error", error);
    return null;
  }
}

export function LocationPicker({ address, mapUrl, lat, lng, onPredict }: LocationPickerProps) {
  const [isPredicted, setIsPredicted] = useState(Boolean(mapUrl));
  const [isLocating, setIsLocating] = useState(false);
  const coords = typeof lat === 'number' && typeof lng === 'number' ? { lat, lng } : undefined;
  const embedUrl = useMemo(() => googleEmbedUrl(address, coords), [address, lat, lng]);
  const mapsUrl = useMemo(() => googleMapsUrl(address, coords), [address, lat, lng]);

  useEffect(() => {
    setIsPredicted(Boolean(mapUrl));
  }, [address, mapUrl]);

  const predictLocation = async () => {
    if (!address.trim()) return;
    setIsLocating(true);
    try {
      const nextCoords = await geocodeAddress(address.trim());
      const nextMapUrl = googleMapsUrl(address, nextCoords || undefined);
      setIsPredicted(true);
      onPredict(nextMapUrl, nextCoords || undefined);
      if (!nextCoords) {
        alert('Không thể dự đoán tọa độ chính xác, bản đồ sẽ hiển thị vị trí gần đúng.');
      }
    } finally {
      setIsLocating(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 mt-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <label className="text-sm font-semibold text-gray-700">Dự đoán vị trí bằng Google Maps</label>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={predictLocation}
            disabled={!address.trim() || isLocating}
            className="text-sm px-3 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 disabled:opacity-50 font-semibold"
          >
            {isLocating ? 'Đang định vị...' : 'Dự đoán từ địa chỉ'}
          </button>
          <a
            href={mapsUrl}
            target="_blank"
            rel="noreferrer"
            className="text-sm px-3 py-2 border border-blue-200 text-blue-700 rounded-md hover:bg-blue-50 font-semibold"
          >
            Mở Google Maps
          </a>
        </div>
      </div>

      <div className="h-[300px] w-full rounded-lg overflow-hidden border border-gray-300 bg-gray-50">
        {address.trim() ? (
          <iframe
            title="Google Maps preview"
            src={embedUrl}
            className="w-full h-full border-0"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-gray-500 px-4 text-center">
            Chọn tỉnh/thành phố, xã/phường và nhập địa chỉ nhà để xem bản đồ.
          </div>
        )}
      </div>

      <p className={`text-xs ${isPredicted || mapUrl ? 'text-green-600' : 'text-gray-500'}`}>
        {isPredicted || mapUrl
          ? coords
            ? `Đã lưu tọa độ: ${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}.`
            : 'Đã lưu vị trí theo truy vấn địa chỉ.'
          : 'Bấm dự đoán để lấy tọa độ và lưu vị trí Google Maps.'}
      </p>
    </div>
  );
}
