import React, { useEffect, useEffectEvent, useMemo, useState, useRef } from 'react';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Thiết lập marker icon mặc định cho Leaflet để tránh lỗi đường dẫn ảnh trong Vite
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface LocationPickerProps {
  address: string;
  mapUrl?: string;
  lat?: number;
  lng?: number;
  onPredict: (mapUrl: string, coords?: { lat: number; lng: number }) => void;
}

function googleMapsUrl(lat: number, lng: number) {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
}

async function geocodeAddress(address: string, signal: AbortSignal) {
  const url = new URL('https://nominatim.openstreetmap.org/search');
  url.searchParams.set('format', 'jsonv2');
  url.searchParams.set('limit', '1');
  url.searchParams.set('countrycodes', 'vn');
  url.searchParams.set('q', address);

  try {
    const response = await fetch(url.toString(), {
      headers: { Accept: 'application/json' },
      signal,
    });
    const results = await response.json();
    const first = Array.isArray(results) ? results[0] : null;
    if (!first?.lat || !first?.lon) return null;
    return { lat: Number(first.lat), lng: Number(first.lon) };
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return null;
    console.error('Geocoding error', error);
    return null;
  }
}

export function LocationPicker({ address, mapUrl, lat, lng, onPredict }: LocationPickerProps) {
  const trimmedAddress = address.trim();
  const [locatingAddress, setLocatingAddress] = useState('');
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const isFirstRender = useRef(true);
  const predictLocation = useEffectEvent(onPredict);
  const isLocating = Boolean(trimmedAddress) && locatingAddress === trimmedAddress;

  // Tạo mapUrl dựa trên tọa độ hiện tại (fallback về query text nếu không có tọa độ)
  const mapsUrl = useMemo(() => {
    if (typeof lat === 'number' && typeof lng === 'number') {
      return googleMapsUrl(lat, lng);
    }
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(trimmedAddress)}`;
  }, [lat, lng, trimmedAddress]);

  // Khởi tạo map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const initialLat = typeof lat === 'number' ? lat : 10.762622;
    const initialLng = typeof lng === 'number' ? lng : 106.660172;

    const map = L.map(mapContainerRef.current).setView([initialLat, initialLng], 16);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    const marker = L.marker([initialLat, initialLng], {
      draggable: true
    }).addTo(map);

    // Kéo thả marker cập nhật tọa độ
    marker.on('dragend', () => {
      const position = marker.getLatLng();
      const updatedLat = position.lat;
      const updatedLng = position.lng;
      const newMapUrl = googleMapsUrl(updatedLat, updatedLng);
      predictLocation(newMapUrl, { lat: updatedLat, lng: updatedLng });
    });

    // Click lên bản đồ để dời marker và cập nhật tọa độ
    map.on('click', (e) => {
      const { lat: clickedLat, lng: clickedLng } = e.latlng;
      marker.setLatLng([clickedLat, clickedLng]);
      const newMapUrl = googleMapsUrl(clickedLat, clickedLng);
      predictLocation(newMapUrl, { lat: clickedLat, lng: clickedLng });
    });

    mapRef.current = map;
    markerRef.current = marker;

    // Trigger invalidateSize để fix lỗi hiển thị các mảnh tile của Leaflet
    const resizeTimer = window.setTimeout(() => {
      map.invalidateSize();
    }, 100);

    return () => {
      window.clearTimeout(resizeTimer);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markerRef.current = null;
      }
    };
  }, []);

  // Đồng bộ lat/lng từ props vào Map (khi coordinates thay đổi từ bên ngoài như gõ thủ công hoặc auto geocode)
  useEffect(() => {
    if (!mapRef.current || !markerRef.current) return;
    if (typeof lat !== 'number' || typeof lng !== 'number') return;

    const map = mapRef.current;
    const marker = markerRef.current;
    const markerPos = marker.getLatLng();

    const diffLat = Math.abs(markerPos.lat - lat);
    const diffLng = Math.abs(markerPos.lng - lng);

    // Chỉ cập nhật nếu tọa độ thực sự lệch quá 0.00001 (khoảng 1m)
    if (diffLat > 0.00001 || diffLng > 0.00001) {
      marker.setLatLng([lat, lng]);
      map.setView([lat, lng], map.getZoom());
    }
  }, [lat, lng]);

  // Tự động geocode khi address thay đổi
  useEffect(() => {
    if (!trimmedAddress) return;

    // Bỏ qua lần tự động geocode đầu tiên khi mount nếu đã có sẵn tọa độ từ database
    if (isFirstRender.current) {
      isFirstRender.current = false;
      if (typeof lat === 'number' && typeof lng === 'number') {
        return;
      }
    }

    const controller = new AbortController();
    let isActive = true;
    setLocatingAddress(trimmedAddress);
    const timer = window.setTimeout(async () => {
      try {
        const nextCoords = await geocodeAddress(trimmedAddress, controller.signal);
        if (isActive && nextCoords) {
          const nextMapUrl = googleMapsUrl(nextCoords.lat, nextCoords.lng);
          predictLocation(nextMapUrl, nextCoords);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isActive) {
          setLocatingAddress((current) => current === trimmedAddress ? '' : current);
        }
      }
    }, 1200);

    return () => {
      isActive = false;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [lat, lng, trimmedAddress]);

  const hasCoords = typeof lat === 'number' && typeof lng === 'number';

  return (
    <div className="flex flex-col gap-3 mt-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <span className="text-sm font-bold text-slate-700">Xem trước vị trí trên Google Maps</span>
        <div className="flex flex-wrap gap-2">
          <a
            href={mapsUrl}
            target="_blank"
            rel="noreferrer"
            className="text-xs px-3 py-1.5 border border-slate-200 text-slate-700 bg-white rounded-md hover:bg-slate-50 font-bold transition shadow-sm"
          >
            Mở Google Maps
          </a>
        </div>
      </div>

      {/* Bản đồ Leaflet tương tác */}
      <div
        ref={mapContainerRef}
        className="h-[300px] w-full rounded-lg overflow-hidden border border-slate-200 bg-slate-50 shadow-inner z-10"
      />

      <p className={`text-xs ${hasCoords ? 'text-green-600 font-semibold' : 'text-slate-500'}`}>
        {isLocating
          ? '📍 Đang tự động xác định tọa độ GPS từ địa chỉ...'
          : hasCoords
            ? `📍 Vị trí bản đồ: ${lat.toFixed(6)}, ${lng.toFixed(6)}. Bạn có thể di chuyển Marker hoặc click lên bản đồ để tinh chỉnh.`
            : 'Nhập địa chỉ để tự động xác định tọa độ và hiển thị bản đồ.'}
      </p>
    </div>
  );
}
