import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperType } from 'swiper';
import { FreeMode, Pagination, Thumbs } from 'swiper/modules';
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Gift,
  Heart,
  ListChecks,
  MessageCircle,
  Minus,
  PackageCheck,
  PlayCircle,
  Plus,
  PlusCircle,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Star,
  Truck,
  X,
  Zap,
} from 'lucide-react';
import { ProductReviews } from './ProductReviews';
import { SuggestedProducts } from './SuggestedProducts';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { apiDb } from '../../services/apiDb';
import { ImageWithFallback } from '../ui/ImageWithFallback';
import 'swiper/css';
import 'swiper/css/free-mode';
import 'swiper/css/pagination';
import 'swiper/css/thumbs';

interface ProductDetailProps {
  product?: any;
}

interface Spec {
  label: string;
  value: string;
  group?: string;
}

interface ProductMediaItem {
  key: string;
  type: 'video' | 'feature' | 'image';
  url: string;
  label: string;
  color?: string;
  poster?: string;
}

const colorFallback: Record<string, string> = {
  den: '#111827',
  'đen': '#111827',
  trang: '#f8fafc',
  'trắng': '#f8fafc',
  xanh: '#8fb7c9',
  do: '#d70018',
  'đỏ': '#d70018',
  vang: '#e7c76f',
  'vàng': '#e7c76f',
  titan: '#c8c0b5',
  bac: '#d1d5db',
  'bạc': '#d1d5db',
};

const specTranslations: Record<string, string> = {
  processor: 'Bộ vi xử lý (CPU)',
  cpu: 'Bộ vi xử lý (CPU)',
  chip: 'Bộ vi xử lý (CPU)',
  ram: 'Bộ nhớ RAM',
  storage: 'Bộ nhớ trong (ROM)',
  rom: 'Bộ nhớ trong (ROM)',
  battery: 'Dung lượng pin',
  batterycapacity: 'Dung lượng pin',
  camera: 'Camera',
  rearcamera: 'Camera sau',
  frontcamera: 'Camera trước',
  screensize: 'Kích thước màn hình',
  screenresolution: 'Độ phân giải màn hình',
  resolution: 'Độ phân giải',
  display: 'Công nghệ màn hình',
  screentype: 'Loại màn hình',
  screentechnology: 'Công nghệ màn hình',
  os: 'Hệ điều hành',
  operatingsystem: 'Hệ điều hành',
  weight: 'Trọng lượng',
  dimensions: 'Kích thước',
  dimension: 'Kích thước',
  warranty: 'Bảo hành',
  origin: 'Xuất xứ',
  material: 'Chất liệu',
  waterproof: 'Chống nước',
  waterresistance: 'Kháng nước',
  bluetooth: 'Bluetooth',
  wifi: 'Wi-Fi',
  network: 'Mạng di động',
  sim: 'Thẻ SIM',
  launchdate: 'Ngày ra mắt',
  releasedate: 'Ngày ra mắt',
  accessories: 'Phụ kiện đi kèm',
  color: 'Màu sắc',
  brand: 'Thương hiệu',
  model: 'Model (Mã máy)',
  gpu: 'Card đồ họa (GPU)',
  graphics: 'Card đồ họa',
  refreshrate: 'Tần số quét',
  chargingspeed: 'Tốc độ sạc',
  charging: 'Công nghệ sạc',
  charger: 'Công suất sạc',
  port: 'Cổng kết nối',
  ports: 'Cổng kết nối',
  jack: 'Jack tai nghe',
  sensors: 'Cảm biến',
  brightness: 'Độ sáng tối đa',
  videorecording: 'Quay video',
  connectivity: 'Kết nối khác',
  wireless: 'Kết nối không dây',
  webcam: 'Webcam',
  audio: 'Âm thanh',
  keyboard: 'Bàn phím',
  casesize: 'Kích thước mặt',
  strap: 'Dây đeo',
  sensor: 'Cảm biến',
  lens: 'Ống kính',
  zoom: 'Zoom',
  stabilization: 'Chống rung',
  fieldofview: 'Góc nhìn',
  sportsmodes: 'Chế độ luyện tập',
  accessorytype: 'Loại phụ kiện',
  compatibility: 'Tương thích',
  power: 'Công suất',
  capacity: 'Dung lượng',
  chargingstandard: 'Chuẩn sạc',
  gps: 'Định vị GPS',
  nfc: 'Kết nối NFC',
  infrared: 'Cổng hồng ngoại',
  fingerprint: 'Cảm biến vân tay',
  rearvideo: 'Quay video camera sau',
  frontvideo: 'Quay video camera trước',
  displaytype: 'Kiểu màn hình',
  displayfeatures: 'Đặc điểm màn hình',
  specialfeatures: 'Tính năng đặc biệt',
  rearcamerafeatures: 'Tính năng camera sau',
  framematerial: 'Chất liệu khung viền',
  backmaterial: 'Chất liệu mặt lưng',
  chargingport: 'Cổng sạc',
  audiocodec: 'Công nghệ âm thanh',
  noisecancellation: 'Khử tiếng ồn',
  releasetime: 'Thời gian ra mắt',
  microphone: 'Microphone',
};

function formatPrice(value?: number | null) {
  if (!value) return 'Liên hệ';
  return `${value.toLocaleString('vi-VN')}đ`;
}

function asArray(value: any) {
  return Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];
}

function normalizeImages(product: any) {
  const images = product?.images?.length ? product.images : product?.imageUrl ? [product.imageUrl] : [];
  return images.filter(Boolean);
}

function firstVariantImage(variant: any) {
  return variant?.imageUrl || variant?.image || variant?.images?.[0] || null;
}

function buildOptions(product: any, key: string, fallback: any[] = []) {
  const fromVariants = (product.variants || [])
    .map((variant: any) => variant?.specs?.[key] || (key === 'storage' ? variant?.storage : undefined))
    .filter(Boolean);
  return Array.from(new Set([...(fallback || []), ...fromVariants]));
}

function optionLabel(value: any) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') {
    return String(value.name || value.label || value.value || value.storage || value.title || '').trim();
  }
  return String(value).trim();
}

function optionKey(value: any, index: number) {
  return optionLabel(value) || (typeof value === 'object' ? value.id || value.key || value.code || `option-${index}` : `option-${index}`);
}

function normalizeOptionList(values: any[] = []) {
  const seen = new Set<string>();
  return values
    .map((value, index) => ({ raw: value, label: optionLabel(value), key: String(optionKey(value, index)) }))
    .filter((item) => {
      if (!item.label || seen.has(item.label)) return false;
      seen.add(item.label);
      return true;
    });
}

const specKeyAliases: Record<string, string> = {
  screenSize: 'screen_size',
  displayType: 'display_type',
  displayFeatures: 'display_features',
  rearVideo: 'rear_video',
  frontVideo: 'front_video',
  rearCameraFeatures: 'rear_camera_features',
  frontCameraFeatures: 'front_camera_features',
  chargingPort: 'charging_port',
  waterResistance: 'water_resistance',
  frameMaterial: 'frame_material',
  backMaterial: 'back_material',
  releaseTime: 'release_time',
  specialFeatures: 'special_features',
  memoryCard: 'memory_card',
  headphoneJack: 'headphone_jack',
  otherUtilities: 'other_utilities',
  utilityTechnology: 'utility_technology',
  tabletModel: 'tablet_model',
  noiseCancellation: 'noise_cancellation',
  caseSize: 'case_size',
  sportsModes: 'sports_modes',
  fieldOfView: 'field_of_view',
};

const specFallbackLabels: Record<string, { label: string; group: string }> = {
  screen_size: { label: 'Kích thước màn hình', group: 'Màn hình' },
  screen_technology: { label: 'Công nghệ màn hình', group: 'Màn hình' },
  display_type: { label: 'Loại màn hình', group: 'Màn hình' },
  display_features: { label: 'Tính năng màn hình', group: 'Màn hình' },
  resolution: { label: 'Độ phân giải', group: 'Màn hình' },
  refresh_rate: { label: 'Tần số quét', group: 'Màn hình' },
  brightness: { label: 'Độ sáng tối đa', group: 'Màn hình' },
  processor: { label: 'Chip xử lý', group: 'Hiệu năng' },
  cpu: { label: 'CPU', group: 'Hiệu năng' },
  gpu: { label: 'GPU', group: 'Hiệu năng' },
  graphics: { label: 'Card đồ họa', group: 'Hiệu năng' },
  ram: { label: 'RAM', group: 'Hiệu năng' },
  storage: { label: 'Bộ nhớ / lưu trữ', group: 'Hiệu năng' },
  memory_card: { label: 'Thẻ nhớ', group: 'Hiệu năng' },
  os: { label: 'Hệ điều hành', group: 'Hiệu năng' },
  rear_camera: { label: 'Camera sau', group: 'Camera' },
  front_camera: { label: 'Camera trước', group: 'Camera' },
  rear_camera_features: { label: 'Tính năng camera sau', group: 'Camera' },
  rear_video: { label: 'Quay video camera sau', group: 'Camera' },
  front_video: { label: 'Quay video camera trước', group: 'Camera' },
  video_recording: { label: 'Quay video', group: 'Camera' },
  webcam: { label: 'Webcam', group: 'Camera & âm thanh' },
  audio: { label: 'Âm thanh', group: 'Camera & âm thanh' },
  battery: { label: 'Pin', group: 'Pin & sạc' },
  charging: { label: 'Công nghệ sạc', group: 'Pin & sạc' },
  charging_standard: { label: 'Chuẩn sạc', group: 'Pin & sạc' },
  charging_port: { label: 'Cổng sạc', group: 'Pin & sạc' },
  sim: { label: 'SIM', group: 'Kết nối' },
  network: { label: 'Mạng di động', group: 'Kết nối' },
  connectivity: { label: 'Kết nối', group: 'Kết nối' },
  wifi: { label: 'Wi-Fi', group: 'Kết nối' },
  bluetooth: { label: 'Bluetooth', group: 'Kết nối' },
  nfc: { label: 'NFC', group: 'Kết nối' },
  gps: { label: 'Định vị GPS', group: 'Kết nối' },
  infrared: { label: 'Hồng ngoại', group: 'Kết nối' },
  ports: { label: 'Cổng kết nối', group: 'Kết nối' },
  wireless: { label: 'Kết nối không dây', group: 'Kết nối' },
  compatibility: { label: 'Tương thích', group: 'Kết nối' },
  sensors: { label: 'Cảm biến', group: 'Tính năng' },
  fingerprint: { label: 'Bảo mật vân tay', group: 'Tính năng' },
  special_features: { label: 'Tính năng đặc biệt', group: 'Tính năng' },
  utility_technology: { label: 'Công nghệ tiện ích', group: 'Tính năng' },
  water_resistance: { label: 'Kháng nước/bụi', group: 'Độ bền' },
  material: { label: 'Chất liệu', group: 'Thiết kế' },
  frame_material: { label: 'Chất liệu khung', group: 'Thiết kế' },
  back_material: { label: 'Chất liệu mặt lưng', group: 'Thiết kế' },
  dimensions: { label: 'Kích thước', group: 'Thiết kế' },
  weight: { label: 'Trọng lượng', group: 'Thiết kế' },
  color: { label: 'Màu sắc', group: 'Thiết kế' },
  keyboard: { label: 'Bàn phím', group: 'Thiết kế' },
  release_time: { label: 'Thời điểm ra mắt', group: 'Thông tin chung' },
  accessory_type: { label: 'Loại phụ kiện', group: 'Thông tin chung' },
  power: { label: 'Công suất', group: 'Hiệu năng' },
  capacity: { label: 'Dung lượng', group: 'Hiệu năng' },
  noise_cancellation: { label: 'Chống ồn', group: 'Tính năng' },
  microphone: { label: 'Micro', group: 'Tính năng' },
  case_size: { label: 'Kích thước mặt', group: 'Thiết kế' },
  strap: { label: 'Dây đeo', group: 'Thiết kế' },
  sports_modes: { label: 'Chế độ luyện tập', group: 'Tính năng' },
  sensor: { label: 'Cảm biến', group: 'Hình ảnh' },
  lens: { label: 'Ống kính', group: 'Hình ảnh' },
  zoom: { label: 'Zoom', group: 'Hình ảnh' },
  stabilization: { label: 'Chống rung', group: 'Video' },
  field_of_view: { label: 'Góc nhìn', group: 'Video' },
  tablet_model: { label: 'Dòng máy tính bảng', group: 'Thông tin chung' },
  headphone_jack: { label: 'Cổng tai nghe', group: 'Kết nối' },
  other_utilities: { label: 'Tiện ích khác', group: 'Tính năng' },
};

function normalizeSpecKey(key: string) {
  return specKeyAliases[key] || key;
}

function fallbackSpecMeta(key: string) {
  return specFallbackLabels[key] || {
    label: key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase()),
    group: inferSpecGroup(key),
  };
}

function inferSpecGroup(key: string) {
  const normalized = key.toLowerCase();
  if (/(screen|display|màn|man|resolution|refresh|hz|inch)/i.test(normalized)) return 'Màn hình';
  if (/(cpu|chip|processor|ram|storage|rom|gpu|hiệu năng|hieu nang)/i.test(normalized)) return 'Hiệu năng';
  if (/(camera|video|zoom)/i.test(normalized)) return 'Camera';
  if (/(battery|pin|charge|sạc|sac)/i.test(normalized)) return 'Pin & sạc';
  if (/(weight|material|dimension|design|nặng|nang|chất liệu|chat lieu)/i.test(normalized)) return 'Thiết kế';
  if (/(connect|wifi|bluetooth|sim|nfc|network)/i.test(normalized)) return 'Kết nối';
  return 'Thông số khác';
}

function formatSpecValue(value: any) {
  if (value === null || value === undefined || value === '') return '';
  if (Array.isArray(value)) return value.map(formatSpecValue).filter(Boolean).join(', ');
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${formatSpecValue(item)}`)
      .filter((item) => !item.endsWith(': '))
      .join(', ');
  }
  return String(value);
}

function buildProductSpecs(product: any): Spec[] {
  const specFieldMap = new Map(
    (product.specFields || []).map((field: any) => [
      normalizeSpecKey(field.key || field.label),
      {
        label: field.label || field.key,
        group: field.group || inferSpecGroup(normalizeSpecKey(field.key || field.label || '')),
      },
    ]),
  );

  const rawSpecs = product.specs || product.specifications || {};

  const translateLabel = (label: string) => {
    const trimmed = label.trim();
    const keyLower = trimmed.toLowerCase().replace(/_/g, '');
    if (specTranslations[keyLower]) return specTranslations[keyLower];
    return label;
  };

  if (Array.isArray(rawSpecs)) {
    const seenKeys = new Set<string>();
    return rawSpecs
      .map((item: any, index: number) => {
        const key = normalizeSpecKey(item.key || item.label || `spec-${index}`);
        if (seenKeys.has(key)) return null;
        const field = specFieldMap.get(key) as { label?: string; group?: string } | undefined;
        const fallback = fallbackSpecMeta(key);
        const value = formatSpecValue(item.value ?? item.content ?? item.text);
        const originalLabel = item.label || field?.label || fallback.label;
        if (value) seenKeys.add(key);
        return value
          ? {
              label: translateLabel(originalLabel),
              value,
              group: item.group || field?.group || fallback.group,
            }
          : null;
      })
      .filter(Boolean) as Spec[];
  }

  const seenKeys = new Set<string>();
  return Object.entries(rawSpecs)
    .map(([rawKey, value]) => [normalizeSpecKey(rawKey), value] as [string, any])
    .filter(([key, value]) => {
      if (key === '_variantSpecKeys' || seenKeys.has(key) || !formatSpecValue(value)) return false;
      seenKeys.add(key);
      return true;
    })
    .map(([key, value]) => {
      const field = specFieldMap.get(key) as { label?: string; group?: string } | undefined;
      const fallback = fallbackSpecMeta(key);
      const originalLabel = field?.label || fallback.label;
      return {
        label: translateLabel(originalLabel),
        value: formatSpecValue(value),
        group: field?.group || fallback.group,
      };
    });
}

function buildMediaItems(product: any): ProductMediaItem[] {
  const items: ProductMediaItem[] = [];
  const seen = new Set<string>();
  const poster = product?.imageUrl || product?.images?.[0] || firstVariantImage(product?.variants?.[0]);

  const add = (item: ProductMediaItem) => {
    if (!item.url || seen.has(`${item.type}:${item.url}`)) return;
    seen.add(`${item.type}:${item.url}`);
    items.push(item);
  };

  if (product?.videoUrl) {
    add({ key: `video-${product.videoUrl}`, type: 'video', url: product.videoUrl, label: 'Video sản phẩm', poster });
  }

  [
    ...asArray(product?.featureImages),
    ...asArray(product?.featuredImages),
    ...asArray(product?.highlightImages),
    ...asArray(product?.featureMedia),
    ...asArray(product?.highlightMedia),
  ].forEach((url: string, index: number) => {
    add({
      key: `feature-${index}-${url}`,
      type: 'feature',
      url,
      label: index === 0 ? 'Tính năng nổi bật' : `Tính năng ${index + 1}`,
    });
  });

  (product?.variants || []).forEach((variant: any) => {
    const image = firstVariantImage(variant);
    const color = variant?.colorName || variant?.specs?.color;
    if (image) {
      add({
        key: `variant-${variant.id || variant.sku || color || image}`,
        type: 'image',
        url: image,
        label: color ? `Màu ${color}` : 'Ảnh biến thể',
        color,
      });
    }
    asArray(variant?.images).forEach((url: string, index: number) => {
      add({
        key: `variant-gallery-${variant.id || variant.sku || color || index}-${index}-${url}`,
        type: 'image',
        url,
        label: color ? `Màu ${color} ${index + 1}` : `Ảnh biến thể ${index + 1}`,
        color,
      });
    });
  });

  normalizeImages(product).forEach((url: string, index: number) => {
    add({ key: `image-${index}-${url}`, type: 'image', url, label: index === 0 ? 'Ảnh sản phẩm' : `Ảnh ${index + 1}` });
  });

  return items;
}

function groupSpecs(specs: Spec[]) {
  return specs.reduce<{ title: string; specs: Spec[] }[]>((items, spec) => {
    const title = spec.group?.trim() || 'Thông số khác';
    const existing = items.find((item) => item.title === title);
    if (existing) existing.specs.push(spec);
    else items.push({ title, specs: [spec] });
    return items;
  }, []);
}

function SpecsPreview({ specs, onShowAll }: { specs: Spec[]; onShowAll: () => void }) {
  const previewSpecs = specs.slice(0, 6);
  if (!previewSpecs.length) return null;

  return (
    <section className="overflow-hidden rounded-2xl bg-white border border-gray-200">
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <ListChecks className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Thông số kỹ thuật</h2>
      </div>
      <div className="divide-y divide-gray-100">
        {previewSpecs.map((spec, index) => (
          <div
            key={`${spec.group || 'spec'}-${spec.label}-${index}`}
            className={`grid grid-cols-[42%_1fr] gap-3 px-4 py-3 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}
          >
            <span className="font-medium text-gray-500">{spec.label}</span>
            <span className="line-clamp-2 font-semibold leading-relaxed text-gray-800">{spec.value}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-gray-100 p-3">
        <button
          onClick={onShowAll}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary bg-white py-2.5 text-sm font-bold text-primary hover:bg-red-50"
        >
          Xem tất cả thông số
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}

function SpecsModal({
  specs,
  activeGroup,
  onSelectGroup,
  onClose,
}: {
  specs: Spec[];
  activeGroup: string;
  onSelectGroup: (group: string) => void;
  onClose: () => void;
}) {
  const groups = groupSpecs(specs);
  const visibleGroups = activeGroup === 'all' ? groups : groups.filter((group) => group.title === activeGroup);
  const hasSpecs = specs.length > 0;

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-3 py-5">
      <div className="flex max-h-[92vh] w-full max-w-[900px] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h2 className="text-xl font-bold text-gray-900">Thông số kỹ thuật</h2>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200"
            aria-label="Đóng thông số kỹ thuật"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {hasSpecs && <div className="flex gap-5 overflow-x-auto border-b border-gray-200 px-5">
          <button
            onClick={() => onSelectGroup('all')}
            className={`shrink-0 border-b-2 py-3 text-sm font-bold ${activeGroup === 'all' ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
          >
            Tất cả
          </button>
          {groups.map((group) => (
            <button
              key={group.title}
              onClick={() => onSelectGroup(group.title)}
              className={`shrink-0 border-b-2 py-3 text-sm font-bold ${activeGroup === group.title ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
            >
              {group.title}
            </button>
          ))}
        </div>}

        <div className="overflow-y-auto px-5 py-4">
          {hasSpecs ? <div className="space-y-6">
            {visibleGroups.map((group) => (
              <section key={group.title}>
                <h3 className="mb-3 text-lg font-bold text-gray-800">{group.title}</h3>
                <div className="overflow-hidden rounded-xl border border-gray-200">
                  {group.specs.map((spec, index) => (
                    <div
                      key={`${group.title}-${spec.label}-${index}`}
                      className="grid grid-cols-[34%_1fr] border-b border-gray-200 text-sm last:border-b-0 sm:text-base"
                    >
                      <div className="bg-gray-100 px-4 py-3 font-medium text-gray-700">{spec.label}</div>
                      <div className="px-4 py-3 leading-relaxed text-gray-700">{spec.value}</div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div> : (
            <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center">
              <p className="text-base font-bold text-gray-800">Đang cập nhật thông số kỹ thuật</p>
              <p className="mt-2 text-sm text-gray-500">Sản phẩm này chưa có dữ liệu thông số chi tiết.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FeatureHighlights({ product }: { product: any }) {
  const features = useMemo(() => {
    const lines = String(product.description || '')
      .split(/[.\n]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 24);

    const fromSpecs = [
      product.specs?.processor && `Hiệu năng mạnh mẽ với ${product.specs.processor}`,
      product.specs?.screenSize && `Màn hình ${product.specs.screenSize} hiển thị sắc nét`,
      product.specs?.camera && `Camera ${product.specs.camera} hỗ trợ chụp ảnh linh hoạt`,
      product.specs?.battery && `Dung lượng pin ${product.specs.battery} đáp ứng nhu cầu cả ngày`,
    ].filter(Boolean) as string[];

    return (lines.length ? lines : fromSpecs).slice(0, 5);
  }, [product]);

  if (!features.length) return null;

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
      <h2 className="mb-3.5 text-lg font-bold text-gray-900">Đặc điểm nổi bật</h2>
      <div className="space-y-2.5">
        {features.map((feature, index) => (
          <div key={feature} className="flex gap-3 text-sm leading-relaxed text-gray-700 bg-gray-50/40 p-2.5 rounded-xl border border-gray-100/50">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-primary">
              {index + 1}
            </span>
            <span>{feature}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function BundleOffers({ offers, price }: { offers?: any[]; price: number }) {
  if (!offers || offers.length === 0) return null;

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="mb-3.5 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <Gift className="h-4 w-4" />
        </span>
        <h2 className="text-base font-bold text-gray-900">Ưu đãi mua kèm</h2>
      </div>
      <div className="space-y-2.5">
        {offers.map((offer) => {
          const detail = offer.discountType === 'PERCENT'
            ? `Giảm ${offer.discountValue}% khi mua cùng sản phẩm`
            : `Giảm ${formatPrice(offer.discountValue)} khi mua cùng sản phẩm`;
          return (
            <label key={offer.productId} className="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 p-3 transition-all hover:border-red-100 hover:bg-red-50/30">
              <input type="checkbox" className="h-4 w-4 accent-primary" />
              {offer.imageUrl && (
                <img src={offer.imageUrl} alt={offer.productName} className="h-10 w-10 object-contain rounded-lg border border-gray-100 bg-white" />
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold text-gray-800">{offer.productName}</div>
                <div className="text-xs text-gray-500">{detail}</div>
                <div className="text-[11px] text-gray-400 line-through">
                  Giá gốc: {formatPrice(offer.salePrice)}
                </div>
              </div>
              <div className="text-sm font-bold text-primary">{formatPrice(offer.price)}</div>
            </label>
          );
        })}
      </div>
      <div className="mt-3 rounded-xl bg-gray-50/50 px-3 py-2.5 text-xs leading-relaxed text-gray-500 border border-gray-100">
        Có thể chọn thêm khi mua, tổng tiền sẽ được tính tại giỏ hàng. Giá sản phẩm hiện tại: <span className="font-bold text-gray-800">{formatPrice(price)}</span>
      </div>
    </section>
  );
}

const ProductDetail = ({ product: externalProduct }: ProductDetailProps) => {
  const { addToCart } = useCart();
  const [selectedMediaIndex, setSelectedMediaIndex] = useState(0);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedCapacity, setSelectedCapacity] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [liked, setLiked] = useState(false);
  const { user } = useAuth();
  const [addedToCart, setAddedToCart] = useState(false);
  const [showSpecsModal, setShowSpecsModal] = useState(false);
  const [activeSpecGroup, setActiveSpecGroup] = useState('all');
  const [showMediaViewer, setShowMediaViewer] = useState(false);
  const [mainSwiper, setMainSwiper] = useState<SwiperType | null>(null);
  const [thumbsSwiper, setThumbsSwiper] = useState<SwiperType | null>(null);
  const [isDescCollapsed, setIsDescCollapsed] = useState(true);

  const product = useMemo(() => {
    if (!externalProduct) return null;
    return {
      ...externalProduct,
      images: normalizeImages(externalProduct),
      salePrice: externalProduct.price || externalProduct.salePrice || 0,
      originalPrice: externalProduct.discountPrice || externalProduct.originalPrice || null,
      capacities: buildOptions(externalProduct, 'storage', externalProduct.capacities || []),
      colors: externalProduct.colors || [],
      promotions: externalProduct.promotions || [],
    };
  }, [externalProduct]);

  const mediaItems = useMemo(() => (product ? buildMediaItems(product) : []), [product]);

  const features = useMemo(() => {
    if (!product) return [];
    const lines = String(product.description || '')
      .split(/[.\n]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 24);

    const fromSpecs = [
      product.specs?.processor && `Hiệu năng mạnh mẽ với ${product.specs.processor}`,
      product.specs?.screenSize && `Màn hình ${product.specs.screenSize} hiển thị sắc nét`,
      product.specs?.camera && `Camera ${product.specs.camera} hỗ trợ chụp ảnh linh hoạt`,
      product.specs?.battery && `Dung lượng pin ${product.specs.battery} đáp ứng nhu cầu cả ngày`,
    ].filter(Boolean) as string[];

    return (lines.length ? lines : fromSpecs).slice(0, 5);
  }, [product]);

  useEffect(() => {
    if (!product) return;
    setSelectedMediaIndex(0);
    setSelectedImage(mediaItems.find((item) => item.type !== 'video')?.url || product.images?.[0] || null);
    setSelectedCapacity(optionLabel(product.capacities?.[0]));
    setSelectedColor(optionLabel(product.colors?.[0]));
    setQuantity(1);
    
    if (user) {
      apiDb.listFavorites().then(favs => {
        setLiked(favs.some((f: any) => f.id === product.id));
      }).catch(console.error);
    }
  }, [product, mediaItems, user]);

  if (!product) {
    return <div className="mx-auto max-w-7xl px-4 py-16 text-center text-gray-500">Không tìm thấy dữ liệu sản phẩm.</div>;
  }

  const activeVariant = product.variants?.find((variant: any) => {
    const variantSpecs = variant.specs || {};
    if (selectedCapacity && variantSpecs.storage && variantSpecs.storage !== selectedCapacity && variant.storage !== selectedCapacity) return false;
    if (selectedColor) {
      const variantColor = variant.colorName || variantSpecs.color;
      if (variantColor && String(variantColor).toLowerCase() !== selectedColor.toLowerCase()) return false;
    }
    return true;
  });

  const displayPrice = activeVariant?.salePrice || activeVariant?.price || product.salePrice;
  const displayOriginalPrice = activeVariant?.price || product.originalPrice;
  const discount =
    displayOriginalPrice && displayOriginalPrice > displayPrice
      ? Math.round(((displayOriginalPrice - displayPrice) / displayOriginalPrice) * 100)
      : 0;
  const monthlyPrice = displayPrice ? Math.ceil(displayPrice / 12 / 1000) * 1000 : 0;

  const specs = buildProductSpecs(product);
  const capacityOptions = normalizeOptionList(product.capacities);
  const colorOptions = normalizeOptionList(product.colors);

  const selectMedia = (index: number) => {
    if (!mediaItems.length) return;
    const boundedIndex = (index + mediaItems.length) % mediaItems.length;
    const item = mediaItems[boundedIndex];
    setSelectedMediaIndex(boundedIndex);
    if (item.type !== 'video') setSelectedImage(item.url);
    mainSwiper?.slideTo(boundedIndex);
    thumbsSwiper?.slideTo(Math.max(0, boundedIndex - 2));
  };

  const selectColor = (colorName: string) => {
    setSelectedColor(colorName);
    const variant = product.variants?.find((item: any) => {
      const variantColor = item?.colorName || item?.specs?.color;
      return variantColor && String(variantColor).toLowerCase() === String(colorName).toLowerCase();
    });
    const image = firstVariantImage(variant);
    if (!image) return;
    const targetIndex = mediaItems.findIndex((item) => item.url === image);
    setSelectedImage(image);
    if (targetIndex >= 0) selectMedia(targetIndex);
  };

  const closeMediaViewer = () => {
    setShowMediaViewer(false);
    document.body.style.overflow = '';
  };

  const openMediaViewer = (index: number) => {
    selectMedia(index);
    setShowMediaViewer(true);
    document.body.style.overflow = 'hidden';
  };

  const viewMedia = (index: number) => {
    selectMedia(index);
  };

  useEffect(() => {
    if (!showMediaViewer) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMediaViewer();
      if (event.key === 'ArrowLeft') viewMedia(selectedMediaIndex - 1);
      if (event.key === 'ArrowRight') viewMedia(selectedMediaIndex + 1);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [showMediaViewer, selectedMediaIndex]);

  const handleAddToCart = () => {
    addToCart({
      productId: product.id,
      name: [product.name, selectedCapacity, selectedColor].filter(Boolean).join(' - '),
      price: displayPrice,
      imageUrl: selectedImage || product.images[0],
      quantity,
      originalPrice: displayOriginalPrice,
    });
    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 1800);
  };

  const handleBuyNow = () => {
    handleAddToCart();
    window.location.href = '/checkout';
  };

  const fallbackImage = product.images?.[0] || firstVariantImage(product.variants?.[0]) || undefined;
  return (
    <div className="bg-white pb-24 md:pb-8">
      <div className="mx-auto max-w-[1200px] px-3 py-3 sm:px-4">
        <nav className="mb-3 flex items-center gap-1 overflow-hidden text-sm text-gray-500">
          <Link to="/" className="shrink-0 hover:text-primary">Trang chủ</Link>
          <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
          {product.category && (
            <>
              <Link to={`/products/${product.categorySlug || ''}`} className="shrink-0 hover:text-primary">
                {product.category}
              </Link>
              <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
            </>
          )}
          <span className="truncate font-medium text-gray-700">{product.name}</span>
        </nav>

        <div className="mb-4 border-b border-gray-150 pb-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-xl font-bold leading-snug text-gray-900 md:text-2xl">{product.name}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-gray-500">
                <span className="flex items-center gap-1 font-semibold text-amber-500">
                  {[...Array(5)].map((_, index) => (
                    <Star key={index} className={`h-4 w-4 ${index < Math.round(product.rating || 4.8) ? 'fill-amber-400' : 'text-gray-300'}`} />
                  ))}
                  <span>{product.rating || 4.8}</span>
                </span>
                <span>{product.reviewCount || 0} đánh giá</span>
                <span className="hidden text-gray-300 sm:inline">|</span>
                <span>Đã bán {product.soldCount || 128}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <button 
                onClick={() => {
                  if (!user) return alert('Vui lòng đăng nhập để lưu sản phẩm yêu thích.');
                  const nextLiked = !liked;
                  setLiked(nextLiked);
                  apiDb.toggleFavorite(product.id).catch(() => setLiked(!nextLiked));
                }} 
                className={`flex h-10 items-center gap-1.5 rounded-lg border px-3 font-bold transition-all duration-200 ${liked ? 'border-red-200 bg-red-50 text-primary' : 'border-gray-200 text-gray-700 hover:text-primary hover:border-red-200 hover:bg-red-50/30'}`}
              >
                <Heart className={`h-5 w-5 ${liked ? 'fill-primary' : ''}`} />
                <span>Yêu thích</span>
              </button>
              <a href="#product-reviews" className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-gray-700 hover:text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200">
                <MessageCircle className="h-5 w-5" />
                <span>Hỏi đáp</span>
              </a>
              <button
                onClick={() => {
                  setActiveSpecGroup('all');
                  setShowSpecsModal(true);
                }}
                className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-gray-700 hover:text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200"
              >
                <ListChecks className="h-5 w-5" />
                <span>Thông số</span>
              </button>
              <Link to={`/compare?product=${product.id}`} className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-gray-700 hover:text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200">
                <PlusCircle className="h-5 w-5" />
                <span>So sánh</span>
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[500px_1fr] lg:gap-8">
          <aside className="lg:sticky lg:top-16 lg:self-start w-full">
            <div className="space-y-3">
              <div className="group/main-media relative overflow-hidden rounded-2xl bg-white w-full border border-gray-200">
                {discount > 0 && (
                  <span className="absolute left-3 top-3 z-20 rounded-lg bg-primary px-2 py-1 text-xs font-bold text-white">
                    Giảm {discount}%
                  </span>
                )}

                {mediaItems.length > 1 && (
                  <>
                    <button onClick={() => selectMedia(selectedMediaIndex - 1)} className="absolute left-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100" aria-label="Ảnh trước">
                      <ChevronLeft className="h-5 w-5" />
                    </button>
                    <button onClick={() => selectMedia(selectedMediaIndex + 1)} className="absolute right-3 top-1/2 z-20 hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-gray-600 opacity-0 shadow-md backdrop-blur-sm transition-opacity hover:bg-white hover:text-primary lg:flex lg:group-hover/main-media:opacity-100" aria-label="Ảnh sau">
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </>
                )}

                <Swiper
                  modules={[Pagination, Thumbs]}
                  onSwiper={setMainSwiper}
                  onSlideChange={(swiper) => {
                    const item = mediaItems[swiper.activeIndex];
                    if (!item) return;
                    setSelectedMediaIndex(swiper.activeIndex);
                    if (item.type !== 'video') setSelectedImage(item.url);
                    thumbsSwiper?.slideTo(Math.max(0, swiper.activeIndex - 2));
                  }}
                  thumbs={{ swiper: thumbsSwiper && !thumbsSwiper.destroyed ? thumbsSwiper : null }}
                  pagination={{ clickable: true }}
                  className="product-main-swiper"
                >
                  {mediaItems.map((item, index) => (
                    <SwiperSlide key={item.key}>
                      <div
                        className="relative flex aspect-square cursor-pointer items-center justify-center overflow-hidden bg-white p-4"
                        onClick={() => openMediaViewer(index)}
                        onMouseEnter={() => {
                          const next = mediaItems[index + 1];
                          if (next?.type !== 'video' && next?.url) {
                            const image = new Image();
                            image.src = next.url;
                          }
                        }}
                      >
                        {item.type === 'video' ? (
                          <video
                            src={item.url}
                            poster={item.poster}
                            controls
                            preload={index === 0 ? 'metadata' : 'none'}
                            className="w-[90%] h-[90%] max-w-full max-h-full object-contain"
                            onClick={(event) => event.stopPropagation()}
                          />
                        ) : (
                          <ImageWithFallback
                            src={item.url}
                            fallbackSrc={fallbackImage}
                            alt={product.name}
                            loading={index === 0 ? 'eager' : 'lazy'}
                            decoding="async"
                            className="w-[90%] h-[90%] max-w-full max-h-full object-contain transition-transform duration-300 hover:scale-105"
                          />
                        )}
                      </div>
                    </SwiperSlide>
                  ))}
                </Swiper>
              </div>

              {mediaItems.length > 1 && (
                <div className="group relative w-full py-1.5 flex justify-center">
                  <button onClick={() => selectMedia(selectedMediaIndex - 1)} className="absolute left-1 top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-md ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex cursor-pointer" aria-label="Ảnh con trước">
                    <ChevronLeft className="h-4.5 w-4.5" />
                  </button>
                  <div className="w-full px-1">
                    <Swiper modules={[FreeMode, Thumbs]} onSwiper={setThumbsSwiper} freeMode watchSlidesProgress slidesPerView="auto" spaceBetween={8} className="product-thumbs-swiper">
                      {mediaItems.map((item, index) => (
                        <SwiperSlide key={`thumb-${item.key}`} className="!h-[74px] !w-[82px]">
                          <button
                            data-media-index={index}
                            onClick={() => selectMedia(index)}
                            className={`relative flex h-full w-full items-center justify-center overflow-hidden rounded-xl border-2 transition-all cursor-pointer ${selectedMediaIndex === index ? 'border-primary bg-white' : 'border-gray-200 bg-white opacity-70 hover:border-gray-400 hover:opacity-100'}`}
                            aria-label={item.label}
                          >
                            {item.type === 'video' ? (
                              <>
                                {item.poster ? <ImageWithFallback src={item.poster} fallbackSrc={fallbackImage} alt="" loading="lazy" className="h-full w-full object-contain opacity-80" /> : <PlayCircle className="h-8 w-8 text-primary" />}
                                <span className="absolute inset-0 flex items-center justify-center bg-black/10"><PlayCircle className="h-6 w-6 text-white drop-shadow" /></span>
                              </>
                            ) : (
                              <ImageWithFallback src={item.url} fallbackSrc={fallbackImage} alt="" loading="lazy" className="h-full w-full object-contain" />
                            )}
                          </button>
                        </SwiperSlide>
                      ))}
                    </Swiper>
                  </div>
                  <button onClick={() => selectMedia(selectedMediaIndex + 1)} className="absolute right-1 top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/95 text-gray-700 shadow-md ring-1 ring-gray-200 hover:text-primary lg:group-hover:flex cursor-pointer" aria-label="Ảnh con sau">
                    <ChevronRight className="h-4.5 w-4.5" />
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2.5 w-full">
                {[
                  [ShieldCheck, 'Máy mới 100%', 'Chính hãng, nguyên seal'],
                  [RotateCcw, 'Đổi trả 7 ngày', 'Theo chính sách cửa hàng'],
                  [Truck, 'Giao nhanh 2 giờ', 'Nội thành áp dụng'],
                  [PackageCheck, 'Bảo hành 12 tháng', 'Tại trung tâm uỷ quyền'],
                ].map(([Icon, title, desc]: any) => (
                  <div key={title} className="flex gap-2.5 rounded-xl p-3 bg-gray-50/60 border border-gray-100/50 transition-all hover:bg-gray-100/40">
                    <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                    <div>
                      <div className="font-bold text-gray-800 leading-snug">{title}</div>
                      <div className="text-[10px] sm:text-[11px] leading-normal text-gray-500 mt-0.5">{desc}</div>
                    </div>
                  </div>
                ))}
              </div>

              <SpecsPreview
                specs={specs}
                onShowAll={() => {
                  setActiveSpecGroup('all');
                  setShowSpecsModal(true);
                }}
              />
            </div>
          </aside>

          <main className="space-y-3">
            <div className="space-y-4">
              <div className="rounded-xl border border-red-100 bg-red-50/40 p-3.5">
                <div className="flex flex-wrap items-end gap-2">
                  <span className="text-3xl font-black text-primary">{formatPrice(displayPrice)}</span>
                  {displayOriginalPrice && displayOriginalPrice > displayPrice && (
                    <span className="pb-1 text-base font-medium text-gray-400 line-through">
                      {formatPrice(displayOriginalPrice)}
                    </span>
                  )}
                </div>
                <div className="mt-1.5 text-xs text-gray-500">
                  Trả góp từ <span className="font-bold text-gray-900">{formatPrice(monthlyPrice)}/tháng</span> qua thẻ hoặc công ty tài chính.
                </div>
              </div>

              {capacityOptions.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-bold text-gray-800">Phiên bản</div>
                  <div className="grid grid-cols-3 gap-2">
                    {capacityOptions.map((capacity) => {
                      const variantForCapacity = product.variants?.find((v: any) => {
                        const variantSpecs = v.specs || {};
                        return (variantSpecs.storage === capacity.label || v.storage === capacity.label);
                      });
                      const priceForCapacity = variantForCapacity ? (variantForCapacity.salePrice || variantForCapacity.price) : null;
                      return (
                        <button
                          key={capacity.key}
                          onClick={() => setSelectedCapacity(capacity.label)}
                          className={`relative flex flex-col items-center justify-center rounded-xl border px-2 py-2.5 text-center transition-all duration-200 ${selectedCapacity === capacity.label ? 'border-primary bg-red-50 text-primary ring-1 ring-primary' : 'border-gray-200 text-gray-700 hover:border-gray-300'}`}
                        >
                          <span className="text-sm font-bold">{capacity.label}</span>
                          {priceForCapacity && (
                            <span className={`text-[11px] mt-0.5 ${selectedCapacity === capacity.label ? 'text-primary font-bold' : 'text-gray-500 font-medium'}`}>
                              {formatPrice(priceForCapacity)}
                            </span>
                          )}
                          {selectedCapacity === capacity.label && <Check className="absolute right-2 top-1.5 h-3 w-3" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {colorOptions.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-bold text-gray-800">Màu sắc: <span className="font-semibold text-primary">{selectedColor}</span></div>
                  <div className="grid grid-cols-2 gap-2">
                    {colorOptions.map((color) => {
                      const colorCode = color.raw?.code || colorFallback[color.label.toLowerCase()] || '#e5e7eb';
                      const variantForColor = product.variants?.find((v: any) => {
                        const variantColor = v.colorName || v.specs?.color;
                        return variantColor && String(variantColor).toLowerCase() === String(color.label).toLowerCase();
                      });
                      const priceForColor = variantForColor ? (variantForColor.salePrice || variantForColor.price) : null;
                      return (
                        <button
                          key={color.key}
                          onClick={() => selectColor(color.label)}
                          className={`relative flex items-center gap-3 rounded-xl border px-3.5 py-3.5 text-left transition-all duration-200 ${selectedColor === color.label ? 'border-primary bg-red-50 ring-1 ring-primary' : 'border-gray-200 hover:border-gray-300'}`}
                        >
                          <span className="h-6 w-6 shrink-0 rounded-full border border-gray-200" style={{ backgroundColor: colorCode }} />
                          <div className="flex flex-col min-w-0 flex-1">
                            <span className="text-sm font-bold text-gray-800 truncate">{color.label}</span>
                            {priceForColor && (
                              <span className={`text-[11px] mt-0.5 ${selectedColor === color.label ? 'text-primary font-bold' : 'text-gray-500 font-medium'}`}>
                                {formatPrice(priceForColor)}
                              </span>
                            )}
                          </div>
                          {selectedColor === color.label && <Check className="ml-auto h-4 w-4 text-primary shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {product.promotions?.length > 0 && (
                <div className="overflow-hidden rounded-xl border border-red-200/60 bg-white">
                  <div className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 px-3.5 py-2 text-white">
                    <Gift className="h-4 w-4" />
                    <h3 className="text-sm font-bold text-white">Khuyến mãi</h3>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {product.promotions.map((promotion: string, index: number) => (
                      <div key={`${promotion}-${index}`} className="flex gap-2.5 px-3 py-2.5 text-xs text-gray-700 bg-white">
                        <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full bg-green-100 text-[10px] font-bold text-green-700">
                          {index + 1}
                        </span>
                        <span className="leading-relaxed">{promotion}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <hr className="border-gray-100 my-2" />

              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-gray-800">Số lượng</h2>
                <div className="flex overflow-hidden rounded-xl border border-gray-200">
                  <button onClick={() => setQuantity(Math.max(1, quantity - 1))} className="flex h-9 w-9 items-center justify-center text-gray-600 hover:bg-gray-50 transition-colors">
                    <Minus className="h-4 w-4" />
                  </button>
                  <div className="flex h-9 w-10 items-center justify-center border-x border-gray-200 text-sm font-bold bg-gray-50/30">{quantity}</div>
                  <button onClick={() => setQuantity(quantity + 1)} className="flex h-9 w-9 items-center justify-center text-gray-600 hover:bg-gray-50 transition-colors">
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-[1fr_58px] gap-2">
                <button onClick={handleBuyNow} className="rounded-xl bg-primary px-4 py-3 text-center text-white shadow-md hover:bg-red-700 transition-colors duration-200 cursor-pointer">
                  <span className="block text-base font-extrabold">MUA NGAY</span>
                  <span className="block text-xs font-medium opacity-90">Giao tận nơi hoặc nhận tại cửa hàng</span>
                </button>
                <button
                  onClick={handleAddToCart}
                  className={`flex items-center justify-center rounded-xl border-2 transition-all duration-200 cursor-pointer ${addedToCart ? 'border-green-500 bg-green-50 text-green-600' : 'border-primary text-primary hover:bg-red-50'}`}
                  title="Thêm vào giỏ hàng"
                >
                  {addedToCart ? <Check className="h-6 w-6" /> : <ShoppingCart className="h-6 w-6" />}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button className="flex flex-col items-center justify-center rounded-xl border border-amber-200 bg-amber-50/50 px-2 py-2 text-center transition-all hover:bg-amber-100/60 shadow-sm cursor-pointer">
                  <span className="text-xs font-bold text-amber-800">TRẢ GÓP 0%</span>
                  <span className="text-[10px] text-amber-600 font-medium mt-0.5">Duyệt hồ sơ nhanh 5 phút</span>
                </button>
                <button className="flex flex-col items-center justify-center rounded-xl border border-blue-200 bg-blue-50/50 px-2 py-2 text-center transition-all hover:bg-blue-100/60 shadow-sm cursor-pointer">
                  <span className="text-xs font-bold text-blue-800">TRẢ GÓP QUA THẺ</span>
                  <span className="text-[10px] text-blue-600 font-medium mt-0.5">Visa, Mastercard, JCB</span>
                </button>
              </div>
            </div>

            <BundleOffers offers={product.salesConfig?.accessoryOffers} price={displayPrice} />

            {(features.length > 0 || product.description) && (
              <section className="rounded-2xl border border-gray-200 bg-white p-4 space-y-4">
                {features.length > 0 && (
                  <div>
                    <h2 className="mb-3 text-base font-bold text-gray-900">Đặc điểm nổi bật</h2>
                    <div className="space-y-2">
                      {features.map((feature, index) => (
                        <div key={feature} className="flex gap-3 text-sm leading-relaxed text-gray-700 bg-gray-50/40 p-2.5 rounded-xl border border-gray-100/50">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-primary">
                            {index + 1}
                          </span>
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {features.length > 0 && product.description && <hr className="border-gray-100" />}

                {product.description && (
                  <div>
                    <h2 className="mb-3 text-base font-bold text-gray-900">Thông tin chi tiết</h2>
                    <div className="relative">
                      <div
                        className={`overflow-hidden transition-all duration-300 ${
                          isDescCollapsed ? 'max-h-[350px]' : 'max-h-none'
                        }`}
                      >
                        <p className="whitespace-pre-line text-sm leading-7 text-gray-700">{product.description}</p>
                      </div>
                      
                      {isDescCollapsed && (
                        <div className="absolute bottom-0 left-0 right-0 h-28 bg-gradient-to-t from-white via-white/80 to-transparent pointer-events-none" />
                      )}
                    </div>
                    
                    <div className="mt-4 flex justify-center">
                      <button
                        onClick={() => setIsDescCollapsed(!isDescCollapsed)}
                        className="flex items-center gap-1.5 rounded-xl border border-primary bg-white px-6 py-2.5 text-sm font-bold text-primary shadow-sm transition-all hover:bg-red-50 hover:shadow cursor-pointer"
                      >
                        <span>{isDescCollapsed ? 'Xem thêm nội dung' : 'Thu gọn nội dung'}</span>
                        <ChevronDown className={`h-4 w-4 transition-transform duration-300 ${!isDescCollapsed ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>
                )}
              </section>
            )}
          </main>
        </div>
        <SuggestedProducts currentProductId={product.id} category={product.categorySlug} />
        <div id="product-reviews">
          <ProductReviews productId={product.id} />
        </div>
      </div>

      <div className="fixed bottom-[56px] left-0 right-0 z-[49] border-t border-gray-200 bg-white p-3 shadow-[0_-4px_16px_rgba(0,0,0,0.08)] md:hidden">
        <div className="flex items-center gap-2">
          <button onClick={handleAddToCart} className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${addedToCart ? 'border-green-400 bg-green-50 text-green-600' : 'border-primary text-primary'}`}>
            {addedToCart ? <Check className="h-5 w-5" /> : <ShoppingCart className="h-5 w-5" />}
          </button>
          <button onClick={handleBuyNow} className="flex flex-1 flex-col items-center rounded-lg bg-primary py-2 text-white">
            <span className="text-sm font-extrabold">MUA NGAY</span>
            <span className="text-xs font-semibold opacity-90">{formatPrice(displayPrice)}</span>
          </button>
        </div>
      </div>

      {showSpecsModal && (
        <SpecsModal
          specs={specs}
          activeGroup={activeSpecGroup}
          onSelectGroup={setActiveSpecGroup}
          onClose={() => setShowSpecsModal(false)}
        />
      )}

      {showMediaViewer && mediaItems[selectedMediaIndex] && (
        <div className="fixed inset-0 z-[100] flex flex-col bg-black/95">
          <div className="flex h-14 items-center justify-between px-4 text-white">
            <div className="text-sm font-semibold">
              {selectedMediaIndex + 1} / {mediaItems.length}
            </div>
            <button
              onClick={closeMediaViewer}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/20"
              aria-label="Đóng xem ảnh"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 pb-5">
            {mediaItems.length > 1 && (
              <button
                onClick={() => viewMedia(selectedMediaIndex - 1)}
                className="absolute left-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh trước"
              >
                <ChevronLeft className="h-7 w-7" />
              </button>
            )}

            {mediaItems[selectedMediaIndex].type === 'video' ? (
              <video
                src={mediaItems[selectedMediaIndex].url}
                poster={mediaItems[selectedMediaIndex].poster}
                controls
                autoPlay
                className="max-h-[82vh] max-w-full bg-black object-contain"
              />
            ) : (
              <ImageWithFallback
                src={mediaItems[selectedMediaIndex].url}
                fallbackSrc={fallbackImage}
                alt={product.name}
                className="max-h-[82vh] max-w-full object-contain"
              />
            )}

            {mediaItems.length > 1 && (
              <button
                onClick={() => viewMedia(selectedMediaIndex + 1)}
                className="absolute right-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh sau"
              >
                <ChevronRight className="h-7 w-7" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductDetail;
